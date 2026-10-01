"""Build a deterministic Chrome package with an installed-tree identity."""
import hashlib
import json
import pathlib
import sys
import zipfile

IDENTITY_SCHEMA = "occ.extension-package-identity.v1"
TREE_ALGORITHM = "sha256-length-prefixed-path-bytes-v1"


def _tree_digest(entries):
    digest = hashlib.sha256()
    for name, data in sorted(entries.items()):
        encoded = name.encode("utf-8")
        digest.update(len(encoded).to_bytes(4, "big"))
        digest.update(encoded)
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return digest.hexdigest()


def build(output, extension=None):
    extension = extension or pathlib.Path(__file__).resolve().parents[1]
    extension = pathlib.Path(extension).resolve()
    output = pathlib.Path(output).resolve()
    version = json.loads((extension / "manifest.json").read_text(
        encoding="utf-8-sig"))["version"]
    output.mkdir(parents=True, exist_ok=True)
    archive = output / f"ONE_CLICK_CONTEXT_CHROME_READY_{version}.zip"
    files = [
        "manifest.json", "background.js", "artifact-inventory.js",
        "capture-regions.js", "content.js", "offscreen.html", "offscreen.js",
        "viewer.html", "viewer.js", "viewer.css", "library.html", "README.md",
        "INSTALL_RU.txt", "qualification.html", "qualification.mjs",
    ]
    for folder in ["library", "vendor"]:
        files.extend(str(item.relative_to(extension)).replace("\\", "/")
                     for item in (extension / folder).rglob("*") if item.is_file())
    entries = {name: (extension / name).read_bytes() for name in sorted(files)}
    entries["LICENSE"] = (extension.parent / "LICENSE").read_bytes()
    tree_sha256 = _tree_digest(entries)
    identity = {
        "schema": IDENTITY_SCHEMA,
        "version": version,
        "algorithm": TREE_ALGORITHM,
        "package_tree_sha256": tree_sha256,
        "files": [
            {"path": name, "bytes": len(data),
             "sha256": hashlib.sha256(data).hexdigest()}
            for name, data in sorted(entries.items())
        ],
    }
    identity_bytes = json.dumps(identity, sort_keys=True, separators=(",", ":"),
                                ensure_ascii=False).encode("utf-8")
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as package:
        for name, data in sorted({**entries,
                                  "PACKAGE_IDENTITY.json": identity_bytes}.items()):
            entry = zipfile.ZipInfo(name, (2026, 9, 9, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            package.writestr(entry, data)
    with zipfile.ZipFile(archive) as package:
        assert package.testzip() is None
        assert "manifest.json" in package.namelist()
        assert "INSTALL_RU.txt" in package.namelist()
        assert "PACKAGE_IDENTITY.json" in package.namelist()
        assert json.loads(package.read("manifest.json"))["version"] == version
        assert json.loads(package.read("PACKAGE_IDENTITY.json")) == identity
    return {
        "archive": archive,
        "version": version,
        "files": len(entries) + 1,
        "package_tree_sha256": tree_sha256,
        "zip_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
    }


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    extension = pathlib.Path(__file__).resolve().parents[1]
    output = pathlib.Path(argv[0]).resolve() if argv else extension.parent / "dist"
    result = build(output, extension)
    print(f"VERIFIED {result['files']} files; root manifest and identity; "
          f"version {result['version']}")
    print(result["archive"])
    print("TREE_SHA256", result["package_tree_sha256"])
    print("ZIP_SHA256", result["zip_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
