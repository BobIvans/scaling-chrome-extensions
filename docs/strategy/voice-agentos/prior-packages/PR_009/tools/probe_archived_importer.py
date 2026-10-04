"""Reproduce gaps in the preserved historical importer using inert synthetic files."""
from pathlib import Path
import importlib.util, json, sqlite3, tempfile


def probe(root):
    root=Path(root)
    source=root/'sources/archived_sce/content-lab/content_lab.py'
    spec=importlib.util.spec_from_file_location('pr009_archived_content_lab',source)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    fixture=root/'fixtures/import_fidelity_golden'
    original=module.parse_chatgpt_export(fixture/'raw/F01.json','selected')
    metadata=module.parse_chatgpt_export(fixture/'raw/F06.json','selected')
    original_ids={i['message_id']:i['id'] for i in original['items']}
    changed_ids={i['message_id']:i['id'] for i in metadata['items']}
    assert original_ids==changed_ids
    with tempfile.TemporaryDirectory(prefix='pr009-archived-probe-') as tmp:
        store=Path(tmp)
        first=module.import_chatgpt_export(store,fixture/'raw/F01.json','selected')
        second=module.import_chatgpt_export(store,fixture/'raw/F07.json','selected')
        db=sqlite3.connect(store/'content.sqlite3')
        a_missing=db.execute("SELECT count(*) FROM sync_heads WHERE namespace='chatgpt:selected' AND source_key LIKE 'chatgpt/conv-a/%' AND present=0").fetchone()[0]
        tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        db.close()
        assert a_missing==4 and second['removed_attachments']==3
        assert 'import_raw_blobs' not in tables
    return {'scope':'PRESERVED_HISTORICAL_SOURCE_DIAGNOSTIC_ONLY','historical_commit':'da6abf4c006e4e7d26fe45ef30fa9d07a356f396',
            'synthetic_nodes_in_original':9,'legacy_text_items':len(original['items']),
            'legacy_attachment_metadata':len(original['attachments']),
            'metadata_only_edit_keeps_text_item_ids':True,'original_blob_table_present':False,
            'selected_B_marks_A_text_heads_absent':a_missing,'selected_B_marks_A_attachments_absent':second['removed_attachments'],
            'network_fetches':first['network_fetches']+second['network_fetches'],
            'current_head_verified':False,'pr009_application_tests':'NOT_RUN'}


if __name__=='__main__':
    print(json.dumps(probe(Path(__file__).resolve().parents[1]),ensure_ascii=False,indent=2))
