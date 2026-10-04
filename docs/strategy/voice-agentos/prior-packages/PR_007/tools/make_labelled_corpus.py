"""Generate synthetic labels; never parse/execute JS or claim AST qualification."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write(name,value):
    p=ROOT/name
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')


def build():
    families=[
      ('ESM_DEFAULT','.mjs','import run from TOKEN;','./util.js','ESM_IMPORT','VALUE_OR_MIXED','util.js'),
      ('ESM_NAMED_PARENT','.js','import { run } from TOKEN;','../util.mjs','ESM_IMPORT','VALUE_OR_MIXED','../util.mjs'),
      ('ESM_SIDE_EFFECT_JSX','.jsx','import TOKEN;','./util.js','ESM_SIDE_EFFECT','VALUE_OR_MIXED','util.js'),
      ('REEXPORT_NAMED','.mjs','export { run } from TOKEN;','./util.mjs','ESM_REEXPORT','VALUE_OR_MIXED','util.mjs'),
      ('REEXPORT_STAR_TS','.ts','export * from TOKEN;','./util.ts','ESM_REEXPORT','VALUE_OR_MIXED','util.ts'),
      ('IMPORT_TYPE','.ts','import type { Shape } from TOKEN;','./types.ts','TS_IMPORT_TYPE','TYPE_ONLY','types.ts'),
      ('EXPORT_TYPE','.ts','export type { Shape } from TOKEN;','./types.ts','TS_EXPORT_TYPE','TYPE_ONLY','types.ts'),
      ('TS_RUNTIME_EXTENSION','.ts','import { run } from TOKEN;','./util.js','ESM_IMPORT','VALUE_OR_MIXED','util.js'),
      ('COMMONJS_REQUIRE','.cjs','const run = require(TOKEN);','./util.cjs','COMMONJS_REQUIRE','DYNAMIC_OR_UNKNOWN','util.cjs'),
      ('DYNAMIC_LITERAL','.js','const pending = import(TOKEN);','./util.js','DYNAMIC_IMPORT','DYNAMIC_OR_UNKNOWN','util.js'),
      ('DYNAMIC_COMPUTED','.js','const pending = import(TOKEN);',None,'COMPUTED_IMPORT','DYNAMIC_OR_UNKNOWN','util.js'),
      ('ALIAS_TSX','.tsx','import { run } from TOKEN;','@app/util','ESM_IMPORT','VALUE_OR_MIXED','util.ts'),
      ('WORKSPACE_PACKAGE','.mjs','import { run } from TOKEN;','@pkg/shared','ESM_IMPORT','VALUE_OR_MIXED','util.ts'),
      ('EXTENSIONLESS','.ts','import { run } from TOKEN;','./util','ESM_IMPORT','VALUE_OR_MIXED','util.ts'),
      ('ASSET_JSON','.js','import payload from TOKEN;','./asset.json','ESM_IMPORT','VALUE_OR_MIXED','asset.json'),
      ('SCOPE_ESCAPE','.js','import { run } from TOKEN;','../../../../outside.js','ESM_IMPORT','VALUE_OR_MIXED','util.js'),
      ('TARGET_INELIGIBLE','.mjs','import { run } from TOKEN;','./util.js','ESM_IMPORT','VALUE_OR_MIXED','util.js'),
      ('COMMENT_FAKE','.js','// import run from "./util.js";',None,None,None,'util.js'),
      ('STRING_FAKE','.js','const note = "export { run } from \'./util.js\'";',None,None,None,'util.js'),
      ('SYNTAX_ERROR','.ts','import { from "./util.ts";',None,None,None,'util.ts')]
    cases=[]
    for family_index,(family,ext,template,spec,form,kind,target) in enumerate(families):
      for variant in range(10):
        case_id=f'JS007-{family_index*10+variant+1:03d}'
        scope=f'fixture/{case_id}'
        source_path=scope+('/src/sub/main' if family=='ESM_NAMED_PARENT' else '/src/main')+ext
        directory=source_path.rsplit('/',1)[0]
        target_path=(scope+'/src/util.mjs' if family=='ESM_NAMED_PARENT' else directory+'/'+target)
        module_spec=spec
        temp=template
        target_eligible=family!='TARGET_INELIGIBLE'
        omit_target=False
        if family=='ESM_DEFAULT' and variant==8:
            omit_target=True
        if family=='ESM_DEFAULT' and variant==9:
            module_spec='./Util.js'  # Manifest contains lowercase util.js only.
        if family=='ESM_SIDE_EFFECT_JSX' and variant==8:
            module_spec='./util.js?raw'
        if family=='ESM_SIDE_EFFECT_JSX' and variant==9:
            module_spec='https://not.example/util.js'
        if family=='COMMONJS_REQUIRE' and variant==8:
            temp='function caller(require) { return require(TOKEN); }'
        if family=='REEXPORT_STAR_TS' and variant==9:
            temp+='\nexport * from TOKEN;'
        if module_spec is None:
            token=('`./${choice}.js`' if variant==8 else "choice + ''" if variant==9 else 'choice')
        else:
            token=json.dumps(module_spec,ensure_ascii=False)
            if variant==7:
                token=token.replace('.',r'\u002e',1)
        prefixes=['','// RU: Я и связь\n','const emoji = "🧪";\n','\ufeff',
                  '// CRLF\r\n','\ufeff// BOM + Я\r\n','\t// fake: import x from "./wrong.js"\n',
                  '// escaped module literal\n','// '+'x'*8192+'\n','// tail variant\n']
        prefix=prefixes[variant]
        newline='\r\n' if variant in {4,5} else '\n'
        body=temp.replace('TOKEN',token)
        declaration='export function caller() { return 1; }'
        symbol_kind,symbol_name='FUNCTION_DECLARATION','caller'
        if family in {'ESM_SIDE_EFFECT_JSX','ALIAS_TSX'}:
            declaration='export function caller() { return <div/>; }'
        if family=='EXPORT_TYPE':
            declaration='export class Caller { run() { return 1; } }'
            symbol_kind,symbol_name='CLASS_DECLARATION','Caller'
        if family=='COMMONJS_REQUIRE' and variant==8:
            declaration=body
        elif family=='SYNTAX_ERROR':
            declaration='export function caller() {'
            body+='\n'+declaration
        else:
            body+='\n'+declaration
        if newline=='\r\n':
            body=body.replace('\n','\r\n')
        raw=(prefix+body+newline).encode('utf-8')
        path=ROOT/'fixtures/corpus'/case_id/('source'+ext)
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(raw)
        target_raw=b'export const run = () => 1;\nexport type Shape = { x: number };\n' if target.endswith(('.ts','.tsx','.mts','.cts')) else b'export const run = () => 1;\n'
        if target.endswith('.json'):
            target_raw=b'{"example":true}\n'
        target_file=ROOT/'fixtures/corpus'/case_id/'target.data'
        target_file.write_bytes(target_raw)
        manifest=[{'path':source_path,'raw_sha256':sha(raw),'analysis_eligible':True}]
        if not omit_target:
            manifest.append({'path':target_path,'raw_sha256':sha(target_raw),'analysis_eligible':target_eligible})
        if family=='TS_RUNTIME_EXTENSION':
            manifest.append({'path':directory+'/util.ts','raw_sha256':sha(target_raw),'analysis_eligible':True})
        refs=[]
        if form:
            start=0
            while True:
                pos=body.find(token,start)
                if pos<0:
                    break
                byte_start=len(prefix.encode('utf-8'))+len(body[:pos].encode('utf-8'))
                byte_end=byte_start+len(token.encode('utf-8'))
                reason=None
                status='LOCAL_STATIC_EXACT_PATH'
                resolved=target_path
                if form in {'DYNAMIC_IMPORT','COMPUTED_IMPORT'}:reason='DYNAMIC_IMPORT_UNRESOLVED'
                elif form=='COMMONJS_REQUIRE':reason='COMMONJS_NOT_QUALIFIED'
                elif family=='TS_RUNTIME_EXTENSION':reason='TYPE_RESOLUTION_POLICY_REQUIRED'
                elif family in {'ALIAS_TSX','WORKSPACE_PACKAGE'}:reason='NON_RELATIVE_POLICY_NOT_QUALIFIED'
                elif family=='EXTENSIONLESS':reason='EXTENSION_RULE_NOT_QUALIFIED'
                elif family=='ASSET_JSON':reason='TARGET_EXTENSION_UNSUPPORTED'
                elif family=='SCOPE_ESCAPE':reason='SOURCE_SCOPE_ESCAPE'
                elif family=='TARGET_INELIGIBLE':reason='TARGET_NOT_ELIGIBLE'
                elif omit_target or (family=='ESM_DEFAULT' and variant==9):reason='TARGET_MISSING'
                elif family=='ESM_SIDE_EFFECT_JSX' and variant in {8,9}:reason='SPECIFIER_FORM_UNSUPPORTED'
                if reason:
                    status,resolved='UNRESOLVED',None
                refs.append({'syntax_form':form,'specifier':module_spec,'dependency_kind':kind,
                             'occurrence':len(refs),'byte_start':byte_start,'byte_end':byte_end,
                             'range_sha256':sha(raw[byte_start:byte_end]),'literal_or_expression':token,
                             'resolution_status':status,'reason':reason,'target_path':resolved,
                             'target_sha256':sha(target_raw) if resolved else None})
                start=pos+len(token)
        symbols=[]
        if family!='SYNTAX_ERROR':
            begin=body.index(declaration)
            a=len(prefix.encode('utf-8'))+len(body[:begin].encode('utf-8'))
            b=a+len(declaration.encode('utf-8'))
            symbols=[{'name':symbol_name,'kind':symbol_kind,'byte_start':a,'byte_end':b,
                      'range_sha256':sha(raw[a:b])}]
        cases.append({'case_id':case_id,'family_id':family,'variant':variant,'synthetic':True,
                      'source_path':source_path,'scope_root':scope,'raw_file':path.relative_to(ROOT).as_posix(),
                      'raw_sha256':sha(raw),'raw_bytes':len(raw),'target_fixture':target_file.relative_to(ROOT).as_posix(),
                      'manifest':manifest,'expected_analysis':'PARSER_FAILED' if family=='SYNTAX_ERROR' else 'AST_SYNTAX_ONLY',
                      'expected_refs':refs,'expected_symbols':symbols,'ast_adapter_executed':False})
    write('fixtures/LABELLED_CORPUS.json',{'schema':'roadmap.js-ts-corpus-labels.v1','synthetic':True,
      'count':len(cases),'family_count':20,'variants_per_family':10,'independent_holdout':False,
      'label_method':'Explicit source templates + independently recorded literal/expression raw byte ranges; not AST outputs',
      'cases':cases})
    write('fixtures/CORPUS_SUMMARY.json',{'schema':'roadmap.corpus-summary.v1','count':200,'families':20,
      'variants_per_family':10,'raw_bytes':sum(c['raw_bytes'] for c in cases),
      'expected_refs':sum(len(c['expected_refs']) for c in cases),
      'expected_local_static':sum(r['resolution_status']=='LOCAL_STATIC_EXACT_PATH' for c in cases for r in c['expected_refs']),
      'expected_unresolved':sum(r['resolution_status']=='UNRESOLVED' for c in cases for r in c['expected_refs']),
      'parser_error_files':sum(c['expected_analysis']=='PARSER_FAILED' for c in cases),
      'fake_syntax_no_reference_files':sum(c['family_id'] in {'COMMENT_FAKE','STRING_FAKE'} for c in cases),
      'qualifies_ast_precision':False,'parser_executed':False,'independent_holdout':False})
    p=ROOT/'fixtures/EXECUTION_CANARY.js'
    p.write_text('throw new Error("SCANNED_CODE_WAS_EXECUTED");\n',encoding='utf-8')
    return {'cases':len(cases),'families':20,'source_files':200,'target_data_files':200,'application_runtime_executed':False}


if __name__=='__main__':
    print(json.dumps(build(),indent=2))
