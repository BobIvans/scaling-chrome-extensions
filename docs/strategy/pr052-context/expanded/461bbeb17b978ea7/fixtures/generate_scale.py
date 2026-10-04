import argparse, json, pathlib, hashlib, zipfile
p=argparse.ArgumentParser(description='Generate synthetic scale inputs; never run app or scanned code')
p.add_argument('--output',required=True)
p.add_argument('--count',type=int,default=1001)
p.add_argument('--cycle',type=int,default=41)
p.add_argument('--large-source-bytes',type=int,default=3*1024*1024)
p.add_argument('--archive-members',type=int,default=100)
p.add_argument('--archive-member-bytes',type=int,default=1024*1024)
a=p.parse_args()
if min(a.count,a.cycle,a.large_source_bytes,a.archive_members,a.archive_member_bytes)<1: p.error('positive sizes required')
root=pathlib.Path(a.output)
root.mkdir(parents=True,exist_ok=True)
if any(root.iterdir()):p.error('output must be empty to avoid replacing user files')
folder=root/'folder';folder.mkdir()
manifest=root/'ENTRIES.jsonl'
with manifest.open('w',encoding='utf8') as f:
 for i in range(a.count):
  data=('fixture phrase '+str(i)+'\r\n').encode()
  path=folder/f'{i:09d}.txt';path.write_bytes(data)
  f.write(json.dumps({'path':str(path.relative_to(root)),'size':len(data),'sha256':hashlib.sha256(data).hexdigest()})+'\n')
cycle=root/'cycle';cycle.mkdir()
for i in range(a.cycle):
 (cycle/f'n{i:09d}.ts').write_text(f'import "./n{(i+1)%a.cycle:09d}";\n',encoding='utf8')
large=root/'large.ts'
with large.open('wb') as f:
 f.write(b'/*')
 remaining=max(0,a.large_source_bytes-40)
 while remaining:
  take=min(remaining,65536);f.write(b'x'*take);remaining-=take
 f.write(b'*/\nimport "./cycle/n000000000";\n')
with zipfile.ZipFile(root/'expansion.zip','w',compression=zipfile.ZIP_DEFLATED) as z:
 for i in range(a.archive_members):
  with z.open(f'entry-{i:09d}.bin','w') as w:
   remaining=a.archive_member_bytes
   while remaining:
    take=min(remaining,65536);w.write(b'Z'*take);remaining-=take
summary={'schema':'sce.scale-input.v1','entries':a.count,'cycle_members':a.cycle,'large_source_bytes':large.stat().st_size,'archive_members':a.archive_members,'archive_declared_bytes':a.archive_members*a.archive_member_bytes,'runtime_status':'NOT_RUN','raw_processing_limit':'no fixed total-item cap; budgets are measured by app'}
(root/'EXPECTED.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf8')
print(json.dumps(summary))
