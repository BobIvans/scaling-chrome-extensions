#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
EXTENSION_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
REPOSITORY_DIR="$(cd -- "$EXTENSION_DIR/.." && pwd)"
VERSION="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["version"])' "$EXTENSION_DIR/manifest.json")"
OUTPUT_DIR="${1:-$REPOSITORY_DIR/dist}"
OUTPUT_FILE="$OUTPUT_DIR/ONE_CLICK_CONTEXT_CHROME_READY_${VERSION}.zip"

command -v zip >/dev/null || { echo "Error: the zip command is required." >&2; exit 1; }
mkdir -p "$OUTPUT_DIR"
rm -f "$OUTPUT_FILE"

# -j places every installable file, including manifest.json and INSTALL_RU.txt,
# directly at the archive root. Tests and generated evidence are intentionally omitted.
files=(
  manifest.json
  background.js
  content.js
  offscreen.html
  offscreen.js
  viewer.html
  viewer.js
  viewer.css
  README.md
  INSTALL_RU.txt
)

(
  cd "$EXTENSION_DIR"
  zip -X -q -j "$OUTPUT_FILE" "${files[@]}" "$REPOSITORY_DIR/LICENSE"
)

python3 - "$OUTPUT_FILE" <<'PY'
import json
import sys
import zipfile

archive = sys.argv[1]
with zipfile.ZipFile(archive) as package:
    names = package.namelist()
    if "manifest.json" not in names or "INSTALL_RU.txt" not in names:
        raise SystemExit("Package verification failed: required root files are absent")
    if any("/" in name.rstrip("/") for name in names):
        raise SystemExit("Package verification failed: files are not at archive root")
    json.loads(package.read("manifest.json"))
    bad = package.testzip()
    if bad:
        raise SystemExit(f"Package verification failed: corrupt member {bad}")
print(f"Created and verified: {archive} ({len(names)} root files)")
PY
