import json,tempfile,unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from windows_uia import WindowsUIBroker,WindowsUIError

class Runner:
    def __init__(self,rows):self.rows=rows;self.calls=[]
    def __call__(self,argv,**kwargs):
        self.calls.append(argv);mode=argv[argv.index('-Mode')+1]
        class R:pass
        r=R();r.returncode=0;r.stderr=''
        if mode=='Inventory':payload={'ok':True,'hwnd':10,'elements':self.rows}
        else:payload={'ok':True,'state':'WINDOWS_UI_INVOKE_INVOKED','desired_outcome_verified':False}
        r.stdout=json.dumps(payload);return r

def row(name='Show more'):
    return {'runtime_id':'1.2','hwnd':10,'process_id':1,'control_type':'ControlType.Button','name':name,'automation_id':'a','class_name':'Button','enabled':True,'offscreen':False,'is_password':False,'rect':{'x':1,'y':2,'width':3,'height':4},'patterns':['Invoke'],'value':'','text':''}

class UIATests(unittest.TestCase):
    def broker(self,rows):
        td=tempfile.TemporaryDirectory();self.addCleanup(td.cleanup);p=Path(td.name)/'x.ps1';p.write_text('x')
        runner=Runner(rows);return WindowsUIBroker(p,runner=runner),runner
    def test_read_nav_invoke_revalidates(self):
        b,r=self.broker([row()]);s=b.inventory();e=s['elements'][0]
        out=b.act({'snapshot_id':s['snapshot_id'],'element_id':e['element_id'],'expected_fingerprint':e['fingerprint'],'action':'invoke','effect_class':'WINDOWS_WRITE'})
        self.assertEqual(out['state'],'WINDOWS_UI_INVOKE_INVOKED')
    def test_dangerous_generic_invoke_blocked(self):
        b,_=self.broker([row('Delete account')]);s=b.inventory();e=s['elements'][0]
        with self.assertRaisesRegex(WindowsUIError,'QUALIFIED_ADAPTER'):
            b.act({'snapshot_id':s['snapshot_id'],'element_id':e['element_id'],'expected_fingerprint':e['fingerprint'],'action':'invoke','effect_class':'WINDOWS_WRITE'})
if __name__=='__main__':unittest.main()
