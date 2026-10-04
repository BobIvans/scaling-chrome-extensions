#!/usr/bin/env python3
"""Read-only Python source inventory and STATIC_CANDIDATE findings. Stdlib only."""
from __future__ import annotations

import argparse
import ast
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import tempfile
import tokenize
from datetime import datetime, timezone


VERSION = "1.0.0"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def span(node: ast.AST) -> dict:
    return {"start_line": getattr(node, "lineno", None),
            "end_line": getattr(node, "end_lineno", getattr(node, "lineno", None)),
            "start_column": getattr(node, "col_offset", None),
            "end_column": getattr(node, "end_col_offset", None)}


def stable_id(value: object) -> str:
    return digest(json.dumps(value, ensure_ascii=True, sort_keys=True).encode("utf-8"))[:24]


def candidate(rule: str, evidence: list[dict], explanation: str, **extra) -> dict:
    result = {"rule": rule, "status": "STATIC_CANDIDATE", "requires_review": True,
              "explanation": explanation, "evidence": evidence, **extra}
    result["id"] = stable_id(result)
    return result


def evidence(record: dict, node: ast.AST) -> dict:
    return {"path": record["path"], "absolute_path": record["absolute_path"],
            "source_sha256": record["sha256"], **span(node)}


def is_link_or_reparse(path: Path) -> bool:
    info = path.stat(follow_symlinks=False)
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


def inventory(root: Path):
    """Walk without following links/junctions; no document or file-count limit."""
    pending = [root]
    while pending:
        directory = pending.pop()
        try:
            with os.scandir(directory) as iterator:
                children = sorted(iterator, key=lambda x: x.name)
        except OSError as exc:
            yield directory, "LIST_ERROR", str(exc)
            continue
        for item in children:
            path = Path(item.path)
            try:
                if item.is_symlink() or is_link_or_reparse(path):
                    yield path, "SKIPPED_SYMLINK_OR_JUNCTION", None
                elif item.is_dir(follow_symlinks=False):
                    pending.append(path)
                elif item.is_file(follow_symlinks=False) and path.suffix.lower() == ".py":
                    yield path, "PYTHON_SOURCE", None
                elif path.suffix.lower() == ".py":
                    yield path, "SKIPPED_NONREGULAR", None
            except OSError as exc:
                yield path, "STAT_ERROR", str(exc)


def read_source(path: Path, record: dict):
    """Detect source encoding using Python's coding-cookie rules. Never imports it."""
    try:
        before = path.stat(follow_symlinks=False)
        if not stat.S_ISREG(before.st_mode):
            record["status"] = "SKIPPED_NONREGULAR"
            return None
        # O_NOFOLLOW is available on Unix; lstat/fstat identity checks also detect a
        # replacement race. Windows junctions are skipped during the inventory.
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(path, flags)
        with os.fdopen(fd, "rb") as handle:
            opened = os.fstat(handle.fileno())
            if not stat.S_ISREG(opened.st_mode):
                record["status"] = "SKIPPED_NONREGULAR"
                return None
            raw = handle.read()
            after_handle = os.fstat(handle.fileno())
        after_path = path.stat(follow_symlinks=False)
    except OSError as exc:
        record.update(status="READ_ERROR", error=str(exc))
        return None
    record.update(sha256=digest(raw), byte_count=len(raw), mtime_ns=opened.st_mtime_ns)
    def identity(value):
        return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns
    if not (identity(before) == identity(opened) == identity(after_handle) == identity(after_path)):
        record.update(status="SOURCE_CHANGED_DURING_READ", error="Retry from an immutable checkout.")
        return None
    if b"\x00" in raw:
        record.update(status="BINARY", error="NUL bytes are not valid Python source.")
        return None
    try:
        encoding, _ = tokenize.detect_encoding(io.BytesIO(raw).readline)
        text = raw.decode(encoding)
        record["encoding"] = encoding
    except (SyntaxError, UnicodeError, LookupError) as exc:
        record.update(status="DECODE_ERROR", error=str(exc))
        return None
    try:
        tree = ast.parse(text, filename=str(path))
    except (SyntaxError, ValueError, RecursionError) as exc:
        record.update(status="SYNTAX_ERROR", error=str(exc),
                      error_line=getattr(exc, "lineno", None),
                      error_column=getattr(exc, "offset", None))
        return None
    record.update(status="PARSED", line_count=len(text.splitlines()))
    return tree


def qualified_name(node: ast.AST, parents: dict) -> str:
    parts = [node.name]
    current = parents.get(node)
    while current is not None:
        if isinstance(current, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            parts.append(current.name)
        current = parents.get(current)
    return ".".join(reversed(parts))


def inspect_tree(tree: ast.AST, record: dict, threshold: int, duplicates: dict,
                 findings: list, imports: list, dynamic: list):
    nodes = list(ast.walk(tree))
    parents = {child: node for node in nodes for child in ast.iter_child_nodes(node)}
    importlib_names = {"importlib"}
    import_module_names = set()
    for node in nodes:
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "importlib":
                    importlib_names.add(alias.asname or "importlib")
        if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module == "importlib":
            import_module_names.update(alias.asname or alias.name for alias in node.names
                                       if alias.name == "import_module")
    for node in nodes:
        ev = evidence(record, node)
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in {"eval", "exec"}:
                findings.append(candidate("EVAL_OR_EXEC", [ev],
                    "Вызов с именем eval/exec; переопределение имени и достижимость не установлены.",
                    called_name=node.func.id))
            if any(kw.arg == "shell" and isinstance(kw.value, ast.Constant)
                   and kw.value.value is True for kw in node.keywords):
                findings.append(candidate("LITERAL_SHELL_TRUE", [ev],
                    "У вызова указан shell=True; получатель вызова и происхождение команды требуют проверки."))
            func = node.func
            dynamic_call = (isinstance(func, ast.Name) and
                            (func.id == "__import__" or func.id in import_module_names)) or (
                isinstance(func, ast.Attribute) and func.attr == "import_module" and
                isinstance(func.value, ast.Name) and func.value.id in importlib_names)
            if dynamic_call:
                literal = (node.args[0].value if node.args and isinstance(node.args[0], ast.Constant)
                           and isinstance(node.args[0].value, str) else None)
                dynamic.append({**ev, "status": "UNRESOLVED_DYNAMIC_IMPORT",
                                "literal_argument": literal,
                                "reason": "Runtime imports are not executed or included in the proven graph."})
        if isinstance(node, ast.ExceptHandler):
            if node.type is None:
                findings.append(candidate("BARE_EXCEPT", [ev],
                    "Обработчик без типа исключения; намерение и последствия требуют проверки."))
            if node.body and all(isinstance(item, ast.Pass) for item in node.body):
                findings.append(candidate("EXCEPT_PASS", [ev],
                    "Тело обработчика состоит только из pass; возможное подавление ошибки."))
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            name = qualified_name(node, parents)
            lines = node.end_lineno - node.lineno + 1
            if lines > threshold:
                findings.append(candidate("LONG_FUNCTION", [ev],
                    "Размер функции превышает настраиваемый порог; это повод для обзора, а не дефект.",
                    function=name, physical_lines=lines, configured_threshold=threshold))
            body = list(node.body)
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                body = body[1:]
            normalized = ast.dump(ast.Module(body=body, type_ignores=[]), include_attributes=False)
            duplicates.setdefault(digest(normalized.encode()), []).append({**ev, "function": name})
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            imports.append({"record": record, "node": node})


def local_modules(records: list, import_roots: list[str]):
    mapping = {}
    contexts = {}
    for record in records:
        if record["status"] != "PARSED":
            continue
        path = Path(record["path"])
        for import_root in import_roots:
            try:
                relative = path.relative_to(Path(import_root))
            except ValueError:
                continue
            parts = list(relative.with_suffix("").parts)
            is_package = parts[-1] == "__init__"
            if is_package:
                parts.pop()
            module = ".".join(parts)
            package = module if is_package else ".".join(parts[:-1])
            if module:
                mapping.setdefault(module, set()).add(record["path"])
            contexts.setdefault(record["path"], set()).add(package)
    return mapping, contexts


def resolve_imports(records: list, imports: list, import_roots: list[str]):
    mapping, contexts = local_modules(records, import_roots)
    edges, unresolved = [], []
    namespaces = {".".join(name.split(".")[:i]) for name in mapping
                  for i in range(1, len(name.split(".")))}
    def resolution(name):
        targets = mapping.get(name, set())
        if len(targets) == 1:
            return next(iter(targets)), "RESOLVED_LOCAL"
        if len(targets) > 1:
            return None, "AMBIGUOUS_LOCAL_MODULE"
        if name in namespaces:
            return None, "LOCAL_NAMESPACE_PACKAGE"
        return None, "EXTERNAL_OR_UNRESOLVED_MODULE"

    def add_module(name, record, node, required=True):
        target, status = resolution(name)
        if target:
            edges.append({"source": record["path"], "target": target,
                          "module": name, "status": "STATIC_IMPORT_EDGE",
                          "evidence": evidence(record, node)})
        elif required and status != "LOCAL_NAMESPACE_PACKAGE":
            unresolved.append({**evidence(record, node), "module": name, "status": status})
        # Importing pkg.child can also execute each resolvable parent __init__.
        for i in range(1, len(name.split("."))):
            parent_name = ".".join(name.split(".")[:i])
            parent, _ = resolution(parent_name)
            if parent:
                edges.append({"source": record["path"], "target": parent,
                              "module": parent_name, "status": "STATIC_PACKAGE_INIT_EDGE",
                              "evidence": evidence(record, node)})
        return target, status

    for item in imports:
        record, node = item["record"], item["node"]
        if isinstance(node, ast.Import):
            for alias in node.names:
                add_module(alias.name, record, node)
            continue
        bases = set()
        if node.level:
            for package in contexts.get(record["path"], set()):
                pieces = package.split(".") if package else []
                if node.level <= len(pieces):
                    head = pieces[:len(pieces) - node.level + 1]
                    bases.add(".".join(head + ([node.module] if node.module else [])))
            if len(bases) != 1:
                unresolved.append({**evidence(record, node), "module": node.module,
                                   "level": node.level, "status": "UNRESOLVED_RELATIVE_IMPORT",
                                   "reason": "Unknown or ambiguous package under configured import roots."})
                continue
        else:
            bases.add(node.module or "")
        base = next(iter(bases))
        target, base_status = add_module(base, record, node)
        for alias in node.names:
            if alias.name == "*":
                unresolved.append({**evidence(record, node), "module": base,
                                   "status": "WILDCARD_BINDINGS_UNKNOWN"})
                continue
            child = base + "." + alias.name if base else alias.name
            child_target, child_status = resolution(child)
            if child_target:
                add_module(child, record, node)
            elif target or base_status == "LOCAL_NAMESPACE_PACKAGE":
                unresolved.append({**evidence(record, node), "module": child,
                                   "status": "ATTRIBUTE_OR_SUBMODULE_UNKNOWN",
                                   "reason": "Imported attributes and runtime package exports are not evaluated."})
            elif child_status == "AMBIGUOUS_LOCAL_MODULE":
                unresolved.append({**evidence(record, node), "module": child, "status": child_status})
    # A statement can reach the same package initializer by several names.
    edges = list({stable_id(edge): edge for edge in edges}.values())
    return edges, unresolved, {key: sorted(value) for key, value in mapping.items()}


def strongly_connected(nodes, edges):
    """Iterative Kosaraju: no recursion limit or enumeration of exponential cycles."""
    forward = {node: set() for node in nodes}
    reverse = {node: set() for node in nodes}
    for edge in edges:
        forward[edge["source"]].add(edge["target"])
        reverse[edge["target"]].add(edge["source"])
    visited, order = set(), []
    for start in sorted(nodes):
        if start in visited:
            continue
        stack = [(start, False)]
        while stack:
            node, leaving = stack.pop()
            if leaving:
                order.append(node)
            elif node not in visited:
                visited.add(node)
                stack.append((node, True))
                stack.extend((neighbor, False) for neighbor in sorted(forward[node], reverse=True)
                             if neighbor not in visited)
    assigned = set()
    for start in reversed(order):
        if start in assigned:
            continue
        component, stack = [], [start]
        while stack:
            node = stack.pop()
            if node in assigned:
                continue
            assigned.add(node)
            component.append(node)
            stack.extend(reverse[node] - assigned)
        if len(component) > 1 or start in forward[start]:
            yield sorted(component)


def scan_repo(source: str | Path, *, long_function_lines: int = 80,
              import_roots: list[str] | None = None) -> dict:
    raw_root = Path(source).absolute()
    if is_link_or_reparse(raw_root):
        raise ValueError("Repository root must not be a symlink or junction.")
    root = raw_root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("Repository must be a directory.")
    if long_function_lines < 1:
        raise ValueError("long_function_lines must be positive.")
    import_roots = import_roots or ["."]
    normalized_roots = []
    for supplied in import_roots:
        path = Path(supplied)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("Import roots must be relative paths inside the repository.")
        normalized_roots.append(path.as_posix())
    records, findings, imports, dynamic, duplicates = [], [], [], [], {}
    for path, kind, error in inventory(root):
        record = {"path": path.relative_to(root).as_posix(), "absolute_path": str(path),
                  "status": kind}
        records.append(record)
        if error:
            record["error"] = error
        if kind != "PYTHON_SOURCE":
            continue
        tree = read_source(path, record)
        if tree is not None:
            inspect_tree(tree, record, long_function_lines, duplicates, findings, imports, dynamic)
    records.sort(key=lambda r: r["path"])
    for body_hash, occurrences in sorted(duplicates.items()):
        if len(occurrences) > 1:
            findings.append(candidate("DUPLICATE_FUNCTION_BODY", occurrences,
                "Совпадают AST тел функций без ведущих docstring и координат; это не доказательство одинаковой семантики.",
                normalized_body_sha256=body_hash))
    edges, unresolved, module_map = resolve_imports(records, imports, normalized_roots)
    parsed = [record["path"] for record in records if record["status"] == "PARSED"]
    for component in strongly_connected(parsed, edges):
        contained = [edge for edge in edges if edge["source"] in component and edge["target"] in component]
        findings.append(candidate("LOCAL_IMPORT_CYCLE", [edge["evidence"] for edge in contained],
            "Сильно связная компонента статических локальных импортов; условные импорты могут не выполняться вместе.",
            component=component, import_edges=contained))
    counts = {}
    for record in records:
        counts[record["status"]] = counts.get(record["status"], 0) + 1
    digest_inputs = [{key: record.get(key) for key in ("path", "status", "sha256", "byte_count")}
                     for record in records]
    return {"schema_version": 1, "scanner_version": VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(), "root": str(root),
            "scan_status": "COMPLETE_WITH_GAPS" if any(record["status"] != "PARSED" for record in records)
                           else "COMPLETE_FOR_DISCOVERED_PYTHON",
            "assessment": "STATIC_CANDIDATES_ONLY", "security_audit_pass": "NOT_RUN",
            "runtime_tests": "NOT_RUN", "live_bot_readiness": "NOT_RUN",
            "inventory_revision_sha256": digest(json.dumps(digest_inputs, ensure_ascii=True,
                                                           sort_keys=True).encode()),
            "configuration": {"long_function_lines": long_function_lines,
                              "import_roots": normalized_roots, "file_count_cap": None,
                              "source_execution": False, "symlink_following": False},
            "summary": {"files_by_status": counts, "candidate_count": len(findings),
                        "resolved_import_edges": len(edges), "unresolved_imports": len(unresolved),
                        "dynamic_imports": len(dynamic)},
            "files": records, "findings": findings,
            "imports": {"module_map": module_map, "edges": edges,
                        "unresolved": unresolved, "dynamic": dynamic},
            "limitations": [
                "Only .py files; no source code is executed and no dependencies are installed.",
                "Each source file and report are processed in RAM; memory, disk and Python parser limits still apply.",
                "Not an atomic repository snapshot; use an immutable checkout for repeatable evidence.",
                "Hashes describe observed bytes, not a Git commit or proof of correctness.",
                "Static imports may be conditional; dependency injection, runtime paths and dynamic imports remain unresolved.",
                "Eval/exec and import aliases can be rebound; other aliases and indirect calls can be missed.",
                "No cross-language, dataflow, vulnerability, profitability or live-trading assessment.",
                "Directory link replacement during traversal is not hardened against a hostile concurrent local process."]}


def write_report(report: dict, output: str | Path):
    destination = Path(output).absolute()
    root = Path(report["root"])
    resolved = destination.resolve()
    if resolved == root or root in resolved.parents:
        raise ValueError("Write reports outside the scanned repository to preserve its files.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".repo-smells-", suffix=".json", dir=destination.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(report, handle, ensure_ascii=True, indent=2)
            handle.write("\n")
        os.replace(temporary, destination)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", help="Local folder; source is never executed")
    parser.add_argument("--output", required=True, help="JSON report path OUTSIDE the repository")
    parser.add_argument("--long-function-lines", type=int, default=80)
    parser.add_argument("--import-root", action="append", help="Relative Python import root; repeatable, default '.'")
    args = parser.parse_args(argv)
    try:
        report = scan_repo(args.repo, long_function_lines=args.long_function_lines, import_roots=args.import_root)
        write_report(report, args.output)
    except (ValueError, OSError, MemoryError) as exc:
        parser.exit(2, f"Scan/report not completed: {exc}\n")
    print(json.dumps({"output": str(Path(args.output).absolute()), "scan_status": report["scan_status"],
                      "assessment": report["assessment"], **report["summary"]}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
