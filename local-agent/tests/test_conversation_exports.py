import json,tempfile,unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from conversation_exports import extract_conversations

class ConversationTests(unittest.TestCase):
    def test_chatgpt_mapping_export(self):
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/'conversations.json'
            src.write_text(json.dumps([{'id':'c1','title':'Bot work','mapping':{
                'a':{'message':{'author':{'role':'user'},'create_time':1,'content':{'parts':['hello']}}},
                'b':{'message':{'author':{'role':'assistant'},'create_time':2,'content':{'parts':['world']}}}
            }}]))
            rows=extract_conversations(src,Path(td)/'out');self.assertEqual(len(rows),1)
            text=Path(rows[0]['path']).read_text();self.assertIn('[USER]\nhello',text);self.assertIn('[ASSISTANT]\nworld',text)
    def test_generic_messages_export(self):
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/'other.json';src.write_text(json.dumps({'conversation_id':'x','messages':[{'role':'user','content':'a'},{'role':'assistant','content':'b'}]}))
            rows=extract_conversations(src,Path(td)/'out');self.assertEqual(rows[0]['messages'],2)
if __name__=='__main__':unittest.main()
