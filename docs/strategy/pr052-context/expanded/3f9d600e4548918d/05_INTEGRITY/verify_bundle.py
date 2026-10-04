"""Read-only archive/context integrity check. Does not run packaged applications."""
from pathlib import Path
import hashlib, json, zipfile, sys

ROOT=Path(__file__).resolve().parents[1]
def sha(data):return hashlib.sha256(data).hexdigest()
def read(path):return json.loads((ROOT/path).read_text(encoding='utf-8'))
def pointer(obj,path):
    for component in path.strip('/').split('/'):
        key=component.replace('~1','/').replace('~0','~')
        obj=obj[int(key)] if isinstance(obj,list) else obj[key]
    return obj

def verify(check_manifest=True):
    checks=[]
    def ok(name,details):checks.append({'check':name,'result':'PASS','details':details})
    if check_manifest:
        manifest=read('05_INTEGRITY/FILE_MANIFEST.json')
        expected={x['path'] for x in manifest['files']}
        actual={p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file()
                and '__pycache__' not in p.parts and p.relative_to(ROOT).as_posix()!='05_INTEGRITY/FILE_MANIFEST.json'}
        assert expected==actual,('file inventory', sorted(expected-actual),sorted(actual-expected))
        for f in manifest['files']:
            data=(ROOT/f['path']).read_bytes()
            assert len(data)==f['bytes'] and sha(data)==f['sha256'],f['path']
        ok('all_manifest_file_hashes',len(expected))
    preserved=read('05_INTEGRITY/ORIGINAL_PACKAGE_PRESERVATION.json')
    files_checked=0
    for source in preserved['packages']:
        data=(ROOT/source['archive_path']).read_bytes()
        assert sha(data)==source['archive_sha256'],source['archive_path']
        with zipfile.ZipFile(ROOT/source['archive_path']) as z:
            assert z.testzip() is None
            for rec in source['files']:
                raw=z.read(z.infolist()[rec['archive_ordinal']])
                assert sha(raw)==rec['sha256']
                assert (ROOT/rec['expanded_path']).read_bytes()==raw,rec['expanded_path']
                files_checked+=1
    ok('original_archives_and_all_expanded_member_bytes',files_checked)
    messages={m['id']:m for m in map(json.loads,(ROOT/'01_YOUR_WORDS/MESSAGES.jsonl').read_text().splitlines())}
    for msg in messages.values():
        data=(ROOT/msg['text_file']).read_bytes()
        assert data.decode('utf-8')==msg['text'] and sha(data)==msg['sha256'],msg['id']
    ok('literal_message_copies_and_hashes',len(messages))
    ideas=read('02_STRATEGY/USER_IDEAS_WITH_QUOTES.json')
    for idea in ideas:
        msg=messages[idea['message_id']];s=idea['span']
        assert msg['role']=='user'
        assert msg['text'][s['start']:s['end']]==idea['quote'],idea['id']
        assert msg['sha256']==idea['source_sha256']
    assert {x['message_id'] for x in ideas}=={m['id'] for m in messages.values() if m['role']=='user'}
    ok('all_user_message_coverage_and_exact_quote_spans',len(ideas))
    catalogs=[('03_CATALOGS/MASTER_FUNCTION_CATALOG.json','functions'),
              ('03_CATALOGS/MASTER_WORKFLOW_CATALOG.json','workflows'),
              ('03_CATALOGS/RELATED_REQUIREMENTS_PRESERVED.json',None),
              ('03_CATALOGS/PREVIOUS_DEVELOPMENT_TASKS.json',None),
              ('03_CATALOGS/STRUCTURED_RND_CARDS.json',None)]
    pointer_count=0
    for path,key in catalogs:
        obj=read(path);rows=obj[key] if key else obj
        assert len({x['key'] for x in rows})==len(rows),path
        for row in rows:
            assert (ROOT/row['source_path']).is_file(),row['source_path']
            if 'json_pointer' in row:
                assert pointer(read(row['source_path']),row['json_pointer'])==row['original_record'],row['key']
                pointer_count+=1
    functions=read('03_CATALOGS/MASTER_FUNCTION_CATALOG.json')['functions']
    keys={x['key'] for x in functions}
    for idea in ideas:assert set(idea['function_refs'])<=keys,idea['id']
    for row in read('02_STRATEGY/ASSISTANT_RND_PROPOSALS.json'):assert set(row['functions'])<=keys,row['id']
    ok('catalog_records_and_function_references',pointer_count)
    text=(ROOT/'ALL_CONTEXT.txt').read_bytes();idx=read('ALL_CONTEXT_INDEX.json')
    assert sha(text)==idx['combined_text_sha256']
    for blob in idx['unique_text_blocks']:
        raw=text[blob['content_start_byte']:blob['content_end_byte']]
        assert len(raw)==blob['text_bytes'] and sha(raw)==blob['text_sha256']
        raw.decode('utf-8')
    assert not idx['errors'],idx['errors']
    ok('all_exported_text_blocks_and_source_error_ledger',len(idx['unique_text_blocks']))
    parts=read('ALL_CONTEXT_PARTS/index.json');offset=0;digest=hashlib.sha256()
    for part in parts['parts']:
        raw=(ROOT/part['path']).read_bytes();raw.decode('utf-8')
        assert part['start_byte']==offset
        assert raw==text[part['start_byte']:part['end_byte']]
        assert sha(raw)==part['sha256'];offset=part['end_byte'];digest.update(raw)
    assert offset==len(text) and digest.hexdigest()==sha(text)
    ok('multipart_reconstructs_entire_text_without_loss',len(parts['parts']))
    return {'schema':'continuation.bundle-validation.v3','result':'PASS','date':'2026-10-03',
        'scope':'Archive preservation, literal text, source pointers, catalogs and multipart integrity only.',
        'checks':checks,'runtime_changed':False,'runtime_retested_in_v3':False,
        'windows_device_tests':'NOT_RUN','laya_asr_grok_browser_integration_tests':'NOT_RUN',
        'actual_bot_qualification':'NOT_RUN','all_account_history_complete':'NOT_ESTABLISHED',
        'source_wording_vs_actual_original_platform_export':'Only available messages/captures; see source classes.'}

if __name__=='__main__':
    try:
        result=verify();print(json.dumps(result,ensure_ascii=False,indent=2))
    except Exception as exc:
        print(json.dumps({'result':'FAIL','error':str(exc)},ensure_ascii=False));sys.exit(1)
