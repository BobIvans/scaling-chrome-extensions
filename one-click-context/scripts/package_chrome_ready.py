"""Portable Chrome package. Generated archives remain outside the Git diff."""
import hashlib, json, pathlib, sys, zipfile
extension=pathlib.Path(__file__).resolve().parents[1]
output=pathlib.Path(sys.argv[1]).resolve() if len(sys.argv)>1 else extension.parent/'dist'
version=json.loads((extension/'manifest.json').read_text(encoding='utf-8-sig'))['version']
output.mkdir(parents=True,exist_ok=True)
archive=output/f'ONE_CLICK_CONTEXT_CHROME_READY_{version}.zip'
files=['manifest.json','background.js','artifact-inventory.js','capture-regions.js','content.js','offscreen.html','offscreen.js','viewer.html','viewer.js','viewer.css','library.html','README.md','INSTALL_RU.txt']
for folder in ['library','vendor']:
 files.extend(str(f.relative_to(extension)).replace('\\','/') for f in (extension/folder).rglob('*') if f.is_file())
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for name in sorted(files):
  entry=zipfile.ZipInfo(name,(2026,9,9,0,0,0));entry.compress_type=zipfile.ZIP_DEFLATED
  z.writestr(entry,(extension/name).read_bytes())
 z.writestr('LICENSE',(extension.parent/'LICENSE').read_bytes())
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None
 assert 'manifest.json' in z.namelist() and 'INSTALL_RU.txt' in z.namelist()
 assert json.loads(z.read('manifest.json'))['version']==version
 print(f'VERIFIED {len(z.namelist())} files; root manifest; version {version}')
print(archive)
print('SHA256',hashlib.sha256(archive.read_bytes()).hexdigest())
