"""Create a NEW synthetic Git repository without checking out its tree.

Fixture generation and codec verification are NOT SCE inventory qualification.
No network, arbitrary repo, hooks, source imports or production DB operations.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

from inventory_fixture_oracle import summary


def blocks(path):
    with path.open('rb') as f:
        while data := f.read(65536):
            yield data


def build(output, count):
    output = output.absolute()
    if output.exists() or count < 1 or count > 500000:
        raise ValueError('NEW_FIXTURE_DIRECTORY_AND_1_TO_500000_ENTRIES_REQUIRED')
    output.mkdir(parents=True,exist_ok=False)
    env={k:v for k,v in os.environ.items() if k in {'PATH','SystemRoot','SYSTEMROOT','WINDIR','TEMP','TMP'}}
    env.update(GIT_CONFIG_NOSYSTEM='1',GIT_CONFIG_GLOBAL=os.devnull,GIT_NO_REPLACE_OBJECTS='1',
               GIT_NO_LAZY_FETCH='1',GIT_OPTIONAL_LOCKS='0',LC_ALL='C',
               GIT_AUTHOR_NAME='Synthetic Fixture',GIT_AUTHOR_EMAIL='fixture@invalid',
               GIT_COMMITTER_NAME='Synthetic Fixture',GIT_COMMITTER_EMAIL='fixture@invalid',
               GIT_AUTHOR_DATE='2026-10-04T00:00:00+0000',GIT_COMMITTER_DATE='2026-10-04T00:00:00+0000')
    base=['git','-c','core.hooksPath='+os.devnull,'-c','core.fsmonitor=false','-C',str(output)]

    def small(*args, data=None, infile=None, stdout=None):
        # Small commands emit one identifier. ls-tree writes the large output to disk.
        with tempfile.TemporaryFile() as errors:
            r=subprocess.run([*base,*args],input=data,stdin=infile,stdout=stdout or subprocess.PIPE,
                             stderr=errors,env=env,shell=False,timeout=120)
            errors.seek(0)
            diag=errors.read(65537)
            if r.returncode or len(diag)>65536 or (r.stdout is not None and len(r.stdout)>65536):
                raise ValueError('SYNTHETIC_GIT_COMMAND_FAILED')
            return r.stdout or b''

    small('init','-q','--initial-branch=fixture')
    oid=small('hash-object','-w','--stdin',data=b'x').strip()
    with tempfile.TemporaryFile() as tree_input:
        for i in range(count):
            name=f'f{i:08d}_'.encode()+b'x'*210+b'.py'
            tree_input.write(b'100644 blob '+oid+b'\t'+name+b'\0')
        tree_input.seek(0)
        tree=small('mktree','-z',infile=tree_input).strip()
    head=small('commit-tree',tree.decode(),data=b'Synthetic inventory fixture\n').strip()
    small('update-ref','refs/heads/fixture',head.decode())
    raw=output/'LS_TREE_OUTPUT.fixture.bin'
    with raw.open('wb') as f:
        small('ls-tree','-r','-z','-l','--full-tree',head.decode(),stdout=f)
    result=summary(blocks(raw))
    digest=hashlib.sha256()
    for b in blocks(raw):
        digest.update(b)
    if result['entries']!=count or result['last']['path']!=f'f{count-1:08d}_'+'x'*210+'.py':
        raise ValueError('FIXTURE_TAIL_OR_COUNT_MISMATCH')
    result.update({'schema':'roadmap.large-git-fixture-receipt.v1','count_requested':count,
                   'repo_head':head.decode(),'tree':tree.decode(),'stdout_bytes':raw.stat().st_size,
                   'stdout_sha256':digest.hexdigest(),'above_legacy_32_mib':raw.stat().st_size>33554432,
                   'worktree_checkout_performed':False,'application_runtime_executed':False,
                   'git_version':small('--version').decode().strip()})
    (output/'FIXTURE_RECEIPT.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--entries',type=int,default=160000)
    args=parser.parse_args()
    print(json.dumps(build(args.output,args.entries),ensure_ascii=False,indent=2))
