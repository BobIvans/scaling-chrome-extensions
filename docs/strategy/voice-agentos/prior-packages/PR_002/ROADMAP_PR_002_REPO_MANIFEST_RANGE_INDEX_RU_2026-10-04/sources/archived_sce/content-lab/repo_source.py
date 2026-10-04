"""Static source parsing and byte partitions; no imports of scanned code."""
import ast
from bisect import bisect_right
from collections import defaultdict
import hashlib
import json
import re

from automation_core import digest

CHUNK_BYTES = 4096


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def analyze(path, raw):
    result = {'parser': 'TEXT_ONLY', 'symbols': [], 'imports': [], 'dynamic_imports': [], 'findings': []}
    try:
        text = raw.decode('utf-8')
    except UnicodeDecodeError:
        result['parser'] = 'BINARY_OR_NON_UTF8'
        return result, []
    if not path.endswith(('.py', '.pyi')):
        if path.endswith(('.js', '.mjs', '.cjs', '.ts', '.tsx', '.jsx')):
            result['parser'] = 'JS_TEXT_ONLY_NO_SYNTAX_CLAIM'
        return result, []
    try:
        tree = ast.parse(text.removeprefix('\ufeff'))
    except (SyntaxError, ValueError, RecursionError):
        result['parser'] = 'PYTHON_PARSE_FAILED'
        result['findings'] = [{'id': digest([path, 'PARSE']), 'classification': 'STATIC_CANDIDATE', 'criterion': 'Review Python parse failure', 'line': 1}]
        return result, []
    result['parser'] = 'PYTHON_AST'
    boundaries = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            line = min([node.lineno] + [d.lineno for d in node.decorator_list])
            result['symbols'].append({'name': node.name, 'start_line': line, 'end_line': node.end_lineno})
            if node.end_lineno - line > 60:
                result['findings'].append({'id': digest([path, node.name, 'LENGTH']), 'classification': 'STATIC_CANDIDATE', 'criterion': 'Review cohesion of ' + node.name, 'line': line})
        elif isinstance(node, ast.Import):
            result['imports'].extend({'module': n.name, 'level': 0, 'names': [], 'line': node.lineno} for n in node.names)
        elif isinstance(node, ast.ImportFrom):
            result['imports'].append({'module': node.module or '', 'level': node.level, 'names': [n.name for n in node.names], 'line': node.lineno})
        elif isinstance(node, ast.Call) and (isinstance(node.func, ast.Name) and node.func.id == '__import__'
                or isinstance(node.func, ast.Attribute) and node.func.attr == 'import_module'):
            result['dynamic_imports'].append({'status': 'DYNAMIC_UNRESOLVED', 'line': node.lineno})
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            boundaries.append((min([node.lineno] + [d.lineno for d in node.decorator_list]), node.name))
    return result, boundaries


def partition(alias, path, raw, file_hash, boundaries=()):
    """Every byte belongs to one fragment; IDs omit revision/volume ordinals."""
    lines = re.findall(rb'[^\r\n]*(?:\r\n|\r|\n|$)', raw)[:-1]
    offsets, total = [0], 0
    for line in lines:
        total += len(line)
        offsets.append(total)
    starts = {0: 'preamble'}
    for line, name in boundaries:
        if line - 1 < len(offsets):
            starts[offsets[line - 1]] = name
    points = sorted(starts) + [len(raw)]
    try:
        raw.decode('utf-8')
        utf8 = True
    except UnicodeDecodeError:
        utf8 = False
    occurrences = defaultdict(int)
    out = []
    for a, b in zip(points, points[1:]):
        name = starts[a]
        occurrence = occurrences[name]
        occurrences[name] += 1
        part, start = 0, a
        while start < b or not raw and not out:
            end = min(start + CHUNK_BYTES, b)
            # A UTF-8 code point is kept intact when this section is UTF-8.
            if utf8:
                while end > start and end < b and raw[end] & 0xc0 == 0x80:
                    end -= 1
            piece = raw[start:end]
            logical = digest([alias, path, name, occurrence, part])
            revision = digest([logical, file_hash, sha(piece), start, end])
            start_line = bisect_right(offsets, start) if raw else 0
            end_line = bisect_right(offsets, max(start, end - 1)) if raw else 0
            out.append({'logical_id': logical, 'revision': revision, 'byte_start': start, 'byte_end': end,
                        'start_line': start_line, 'end_line': end_line, 'fragment': part,
                        'oversized_fragment': b - a > CHUNK_BYTES, 'raw': piece})
            if end == b:
                break
            start, part = end, part + 1
    assert b''.join(c['raw'] for c in out) == raw
    return out


def import_graph(rows, roots):
    modules = defaultdict(set)
    info = {}
    for row in rows:
        path = row['path']
        if not path.endswith(('.py', '.pyi')):
            continue
        for root in roots:
            prefix = '' if root == '.' else root + '/'
            if path.startswith(prefix):
                module = path[len(prefix):].rsplit('.', 1)[0].replace('/', '.')
                if module.endswith('.__init__'):
                    module = module[:-9]
                modules[module].add(path)
                info.setdefault(path, []).append(module)
    edges, unresolved = [], []
    for row in rows:
        analysis = json.loads(row['analysis'] or '{}')
        for imp in analysis.get('imports', []):
            names = []
            if imp['level']:
                for own in info.get(row['path'], []):
                    package = own if row['path'].endswith('/__init__.py') else own.rpartition('.')[0]
                    parts = package.split('.') if package else []
                    if imp['level'] <= len(parts):
                        names.append('.'.join(parts[:len(parts) - imp['level'] + 1] + ([imp['module']] if imp['module'] else [])))
            else:
                names = [imp['module']]
            resolved, ambiguous = set(), False
            for name in names:
                candidates = modules.get(name, set())
                if len(candidates) > 1:
                    ambiguous = True
                else:
                    resolved.update(candidates)
                for child in imp['names']:
                    children = modules.get(name + '.' + child, set())
                    if len(children) > 1:
                        ambiguous = True
                    else:
                        resolved.update(children)
            if resolved and not ambiguous:
                edges.extend({'from': row['path'], 'to': path, 'status': 'LOCAL_STATIC', 'line': imp['line']} for path in sorted(resolved))
            else:
                unresolved.append({'from': row['path'], 'module': imp['module'], 'status': 'AMBIGUOUS' if ambiguous else 'EXTERNAL_OR_UNRESOLVED', 'line': imp['line']})
        unresolved.extend(dict(x, **{'from': row['path']}) for x in analysis.get('dynamic_imports', []))
        if analysis.get('parser') == 'JS_TEXT_ONLY_NO_SYNTAX_CLAIM':
            unresolved.append({'from': row['path'], 'status': 'JS_DEPENDENCIES_NOT_PARSED'})
    return edges, unresolved


def components(nodes, edges):
    """Iterative Kosaraju: finish each DFS child before marking its siblings."""
    adjacency = {n: [] for n in nodes}
    reverse = {n: [] for n in nodes}
    for edge in edges:
        if edge['from'] in adjacency and edge['to'] in adjacency:
            adjacency[edge['from']].append(edge['to'])
            reverse[edge['to']].append(edge['from'])
    visited, order = set(), []
    for node in nodes:
        if node in visited:
            continue
        visited.add(node)
        stack = [(node, iter(adjacency[node]))]
        while stack:
            current, children = stack[-1]
            child = next(children, None)
            if child is None:
                order.append(current)
                stack.pop()
            elif child not in visited:
                visited.add(child)
                stack.append((child, iter(adjacency[child])))
    visited, groups = set(), []
    for node in reversed(order):
        if node in visited:
            continue
        group, stack = [], [node]
        visited.add(node)
        while stack:
            current = stack.pop()
            group.append(current)
            for child in reverse[current]:
                if child not in visited:
                    visited.add(child)
                    stack.append(child)
        groups.append(sorted(group))
    return groups

