"""Frozen exact-retrieval oracle; synthetic data is never a product dataset."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time
sys.path.insert(0,str(Path(__file__).resolve().parent))
import context_library as lib
import context_packets as packets

RECIPE='occ.synthetic-exact-oracle.v1'
COUNT=10_000
QUERIES=[('source-00000','source-00000'),('source-00999','source-00999'),('source-09999','source-09999'),
         ('unique_quote_00017','source-00017'),('unique_quote_09876','source-09876'),('неизвестный запрос',None)]


def seed(store):
    db=packets.db_for(store);h=hashlib.sha256()
    try:
        db.execute('BEGIN IMMEDIATE')
        for i in range(COUNT):
            key=f'source-{i:05}';raw=f'Exact fact unique_quote_{i:05}\r\nВерсия {i}\n'.encode();h.update(raw)
            rev=lib.digest([RECIPE,'n',i]);db.execute('INSERT INTO context_sources VALUES (?,?,?,?,?,?,?,1)',('n',key,rev,lib.sha(raw),len(raw),'SYNTHETIC_ORACLE',i+1))
            db.execute('INSERT INTO context_source_heads VALUES (?,?,?)',('n',key,rev));db.execute('INSERT INTO context_raw_parts VALUES (?,0,0,?,?,?,NULL)',(rev,len(raw),lib.sha(raw),raw))
        # A scope trap: same quote in a different namespace must never appear.
        raw=b'unique_quote_00017 private';rev=lib.digest([RECIPE,'private'])
        db.execute('INSERT INTO context_sources VALUES (?,?,?,?,?,?,?,1)',('private','secret',rev,lib.sha(raw),len(raw),'SCOPE_TRAP',1));db.execute('INSERT INTO context_source_heads VALUES (?,?,?)',('private','secret',rev));db.execute('INSERT INTO context_raw_parts VALUES (?,0,0,?,?,?,NULL)',(rev,len(raw),lib.sha(raw),raw))
        db.commit();return h.hexdigest()
    finally:db.close()


def run(store):
    fixture_hash=seed(store);runs=[]
    for temperature in ('FIRST_QUERY_PASS','REPEATED_QUERY_PASS'):
        samples=[]
        for query,expected in QUERIES:
            started=time.perf_counter();r=lib.search_sources(store,'n',query);ms=(time.perf_counter()-started)*1000
            actual=[x['source_ref']['source_key'] for x in r['rows']]
            if actual!=([expected] if expected else []):raise AssertionError((query,actual,expected))
            samples.append({'query_sha256':lib.sha(query.encode()),'expected_keys':([expected] if expected else []),'actual_keys':actual,'elapsed_ms':round(ms,3)})
        runs.append({'temperature':temperature,'queries':samples})
    count=0;offset=0
    while True:
        page=lib.search_sources(store,'n',offset=offset,limit=100);count+=len(page['rows'])
        if page['next_offset'] is None:break
        offset=page['next_offset']
    if count!=COUNT:raise AssertionError('TRUNCATED_CORPUS')
    return {'schema':'occ.exact-retrieval-benchmark.v1','recipe':RECIPE,'count':COUNT,'fixture_sha256':fixture_hash,
            'build_digest':__import__('context_runtime').build_digest(),'platform':sys.platform,'oracle':'EXACT_KEYS_AND_SCOPE',
            'status':'PASS','rows_to_eof':count,'runs':runs,'semantic_relevance':'NOT_QUALIFIED','os_cache_flush':'NOT_PERFORMED',
            'device_performance':'NOT_RUN','production_corpus':'NOT_MEASURED'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    with tempfile.TemporaryDirectory() as t:r=run(Path(t)/'store')
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_bytes(lib.encoded(r));print(json.dumps({'status':r['status'],'rows_to_eof':r['rows_to_eof']}))
if __name__=='__main__':main()
