from pathlib import Path
from zipfile import ZipFile
import hashlib,json,sys
root=Path(__file__).resolve().parent
manifest=json.loads((root/'preservation/FILES.json').read_text(encoding='utf-8'))
errors=[]
def hash_file(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
for r in manifest['files']:
 p=(root/r['path']).resolve()
 if not p.is_relative_to(root.resolve()) or not p.is_file():errors.append([r['path'],'MISSING']);continue
 if p.stat().st_size!=r['bytes'] or hash_file(p)!=r['sha256']:errors.append([r['path'],'DRIFT'])
sources=json.loads((root/'preservation/SOURCE_MEMBERS.json').read_text(encoding='utf-8'))
byhash={a['archive_sha256']:a for a in sources['nested_archives']}
for ref in sources['archive_references']:
 if ref['archive_sha256'] not in byhash:errors.append([ref['archive_path'],'NO_EXPANDED_TREE'])
 else:
  try:
   with ZipFile(root/ref['archive_path']) as z:
    # ZipInfo.filename is OS-normalized; orig_filename preserves the archive name.
    actual=[x.orig_filename for x in z.infolist() if not x.is_dir()]
  except __import__('zipfile').BadZipFile:
   if byhash[ref['archive_sha256']].get('parse_status')!='UNREADABLE_ZIP_DATA_PRESERVED':errors.append([ref['archive_path'],'UNEXPECTED_INVALID_ZIP'])
   continue
  if actual!=[r['original_member'] for r in byhash[ref['archive_sha256']]['members']]:errors.append([ref['archive_path'],'MEMBER_SET_CHANGED'])
rows=json.loads((root/'input/evidence/PR001_021_STATUS.json').read_text(encoding='utf-8'))['packages']
if sorted(x['roadmap_number'] for x in rows)!=list(range(1,22)):errors.append(['STATUS','21_PACKAGE_COVERAGE'])
expected=next(x for x in json.loads((root/'SOURCE_INDEX.json').read_text(encoding='utf-8'))['source_packages'] if x['label']=='PR020_021')
ledger=root/expected['expanded_root']/'coverage/CRITERION_LEDGER.json'
actual=root.parents[1]/'automation/pr020-021/CRITERION_LEDGER.json'
if not actual.exists() or hash_file(actual)!=hash_file(ledger):errors.append(['PR52_CRITERION_LEDGER','SOURCE_OR_RUNTIME_DRIFT'])
print(json.dumps({'ok':not errors,'files_verified':len(manifest['files']),'unique_nested_archives':len(byhash),'archive_references':len(sources['archive_references']),
 'roadmap_packages':len(rows),'runtime_or_device_qualification':'NOT_INFERRED','failures':errors},ensure_ascii=False))
sys.exit(bool(errors))
