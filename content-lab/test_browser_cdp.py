"""Adapter admission tests. Transport double does not qualify actual Grok UI."""
import copy
import hashlib
from pathlib import Path
import unittest
from automation_core import digest
from browser_cdp import BrowserAdapter,CDP


class Transport:
    def __init__(self):
        self.version={'Browser':'Fixture/1','Protocol-Version':'1.3','webSocketDebuggerUrl':'ws://127.0.0.1:1/session1'}
        self.expression=None;self.value=None
    def get(self,path):return self.version
    def evaluate(self,handle,expression):self.expression=expression;return self.value


class BrowserTests(unittest.TestCase):
    def setUp(self):
        self.transport=Transport()
        self.config={'endpoint':'http://127.0.0.1:9222','origin':'https://fixture.invalid',
                     'selectors':{k:'[data-fixture="'+k+'"]' for k in ['account','workspace','composer','send','outgoing','response']},'max_text_bytes':1000}
        self.adapter=BrowserAdapter(self.config,self.transport)

    def receipt(self):
        import browser_cdp
        self.config['qualification']={'scope':'SELECTED_UI','status':'PASS','adapter_version':self.adapter.version,
              'code_digest':hashlib.sha256(Path(browser_cdp.__file__).read_bytes()).hexdigest(),
              'contract_digest':self.adapter.contract_digest,'environment_digest':self.adapter.environment_digest(),
              'evidence_refs':['fixture:synthetic-receipt-not-production']}

    def test_local_endpoint_and_origin_are_explicit(self):
        for endpoint in ['https://127.0.0.1:9222','http://localhost:9222','http://remote.invalid:9222','http://127.0.0.1:9222/proxy','http://user@127.0.0.1:9222']:
            with self.subTest(endpoint=endpoint),self.assertRaises(ValueError):CDP(endpoint)
        CDP('http://127.0.0.1:9222')

    def test_receipt_requires_code_contract_and_browser_version(self):
        with self.assertRaises(ValueError):self.adapter.require_qualified()
        self.receipt();self.adapter.require_qualified()
        self.transport.version['webSocketDebuggerUrl']='ws://127.0.0.1:1/session2'
        self.adapter.require_qualified()
        self.transport.version['Browser']='Fixture/2'
        with self.assertRaisesRegex(ValueError,'QUALIFICATION'):self.adapter.require_qualified()
        self.transport.version['Browser']='Fixture/1';self.config['qualification']['code_digest']='wrong'
        with self.assertRaisesRegex(ValueError,'QUALIFICATION'):self.adapter.require_qualified()

    def test_wrong_origin_blocks_binding_and_prompt_is_quoted_data(self):
        self.transport.value={'origin':'https://wrong.invalid'}
        with self.assertRaisesRegex(ValueError,'ORIGIN'):self.adapter.observe('selected-tab')
        self.receipt();self.transport.value={'state':'DRAFT_ATTACHED'}
        prompt={'text':'"); globalThis.injection = true; //\nПривет'}
        self.adapter.prepare('selected-tab',prompt)
        self.assertIn('\\\"',self.transport.expression)
        self.assertNotIn('eval(',self.transport.expression)
        with self.assertRaisesRegex(ValueError,'PART_LIMIT'):self.adapter.prepare('selected-tab',{'text':'x'*2000})


if __name__=='__main__':unittest.main()
