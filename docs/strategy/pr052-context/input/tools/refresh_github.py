"""Read-only GitHub refresh; no push, merge, dispatch or branch mutation."""
import argparse,json,os,re,shutil,subprocess,urllib.request
from datetime import datetime,timezone
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--repo',default='BobIvans/scaling-chrome-extensions');p.add_argument('--output',required=True);a=p.parse_args()
if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',a.repo):raise SystemExit('Invalid repository')
out=Path(a.output).resolve()
if out.exists() and any(out.iterdir()):raise SystemExit('Choose a new or empty output directory')
out.mkdir(parents=True,exist_ok=True)
def get(endpoint):
    if shutil.which('gh'):
        r=subprocess.run(['gh','api',endpoint],capture_output=True,text=True)
        if r.returncode==0:return json.loads(r.stdout)
    headers={'Accept':'application/vnd.github+json','User-Agent':'sce-roadmap-audit'}
    token=os.environ.get('GITHUB_TOKEN')
    if token:headers['Authorization']='Bearer '+token
    req=urllib.request.Request('https://api.github.com/'+endpoint,headers=headers)
    with urllib.request.urlopen(req,timeout=30) as r:return json.load(r)
prs=[];page=1
while True:
    batch=get(f'repos/{a.repo}/pulls?state=all&per_page=100&page={page}')
    prs.extend(batch)
    if len(batch)<100:break
    page+=1
branch=get(f'repos/{a.repo}/branches/main')
record={'observed_at':datetime.now(timezone.utc).isoformat(),'repository':a.repo,'main':branch,'pull_requests':prs,
        'note':'Read-only observation. Non-null merge_commit_sha on an OPEN PR is not proof of merge; use merged_at and Git ancestry.'}
(out/'GITHUB_REFRESH.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
merges=sorted((x for x in prs if x.get('merged_at')),key=lambda x:x['merged_at'])
print(json.dumps({'main_sha':branch['commit']['sha'],'merged_order':[x['number'] for x in merges],'open':[x['number'] for x in prs if x['state']=='open']},ensure_ascii=False))
