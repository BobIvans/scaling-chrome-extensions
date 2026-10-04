"""Reference for fixture labels/identity only, NOT a JS/TS AST adapter."""
from __future__ import annotations

import hashlib
import json
import posixpath


def digest(value):
    raw=json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()


def logical_id(namespace,repository,source_path,ref):
    return digest(['repo-static-edge.v1',namespace,repository,source_path,
                   ref['syntax_form'],ref['specifier'],ref['occurrence']])


def resolve(case,ref):
    form=ref['syntax_form']
    spec=ref['specifier']
    if form in {'DYNAMIC_IMPORT','COMPUTED_IMPORT'}:
        return None,'DYNAMIC_IMPORT_UNRESOLVED'
    if form in {'COMMONJS_REQUIRE','IMPORT_EQUALS'}:
        return None,'COMMONJS_NOT_QUALIFIED'
    if spec is None or any(c in spec for c in ['?','#','\\','\0']) or '://' in spec:
        return None,'SPECIFIER_FORM_UNSUPPORTED'
    if not spec.startswith(('./','../')):
        return None,'NON_RELATIVE_POLICY_NOT_QUALIFIED'
    target=posixpath.normpath(posixpath.join(posixpath.dirname(case['source_path']),spec))
    if not target.startswith(case['scope_root']+'/'):
        return None,'SOURCE_SCOPE_ESCAPE'
    extension=posixpath.splitext(target)[1]
    if not extension:
        return None,'EXTENSION_RULE_NOT_QUALIFIED'
    if extension not in {'.js','.mjs','.jsx','.cjs','.ts','.tsx','.mts','.cts'}:
        return None,'TARGET_EXTENSION_UNSUPPORTED'
    if case['source_path'].endswith(('.ts','.tsx','.mts','.cts')) and extension in {'.js','.jsx','.mjs','.cjs'}:
        return None,'TYPE_RESOLUTION_POLICY_REQUIRED'
    candidates=[e for e in case['manifest'] if e['path']==target]
    if not candidates:
        return None,'TARGET_MISSING'
    if len(candidates)!=1:
        return None,'TARGET_AMBIGUOUS'
    if not candidates[0]['analysis_eligible']:
        return None,'TARGET_NOT_ELIGIBLE'
    return candidates[0],None


def relation(case,ref,interpretation_digest,snapshot_id='a'*64):
    target,reason=resolve(case,ref)
    edge_id=logical_id('code','sce',case['source_path'],ref)
    status='UNRESOLVED' if reason else 'LOCAL_STATIC_EXACT_PATH'
    target_hash=target['raw_sha256'] if target else None
    revision=digest([edge_id,snapshot_id,case['raw_sha256'],target_hash,ref['byte_start'],ref['byte_end'],
                     ref['range_sha256'],interpretation_digest,status,reason])
    return {'schema':'occ.repo-static-relation.v1','edge_id':edge_id,'revision':revision,
            'snapshot_id':snapshot_id,'namespace':'code','repository':'sce',
            'source_path':case['source_path'],'source_sha256':case['raw_sha256'],
            'byte_start':ref['byte_start'],'byte_end':ref['byte_end'],'range_sha256':ref['range_sha256'],
            'syntax_form':ref['syntax_form'],'specifier':ref['specifier'],'occurrence':ref['occurrence'],
            'dependency_kind':ref['dependency_kind'],'target_path':target['path'] if target else None,
            'target_sha256':target_hash,'resolution_status':status,'reason':reason,
            'resolution_scope':'MANIFEST_SOURCE_PATH_ONLY','symbol_binding':'NOT_TYPECHECKED',
            'evidence_class':'JS_TS_STATIC_SYNTAX','interpretation_digest':interpretation_digest}
