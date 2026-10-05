import base64,hashlib,json,tempfile,unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from capability_candidate import CapabilityCandidatePipeline,CandidateError

class Bridge:
    def __init__(self,files):self.files=files
    def codex_artifacts(self,job_id):
        return {'artifacts':[{'id':k,'name':name} for k,name in enumerate(self.files)]}
    def codex_artifact(self,job_id,artifact_id):
        name=list(self.files)[int(artifact_id)];raw=self.files[name]
        return {'bytes_base64':base64.b64encode(raw).decode(),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}

class CandidateTests(unittest.TestCase):
    def test_manifest_rejects_candidate_commands_and_path_escape(self):
        with tempfile.TemporaryDirectory() as td:
            manifest={'schema':'voice-agentos.capability-candidate.v1','skill_id':'x','version':'1','kind':'repo_patch',
                'repo_profile':'r','base_commit':'a'*40,'summary':'x','effect_class':'LOCAL_WRITE','required_test_profile':'unit',
                'expected_files':['../bad'],'verifier':'tests'}
            files={'CAPABILITY_MANIFEST.json':json.dumps(manifest).encode(),'PATCH.diff':b'x'}
            p=CapabilityCandidatePipeline(Bridge(files),{'enabled':True,'repo_profiles':{}},td)
            with self.assertRaisesRegex(CandidateError,'EXPECTED_FILES'):p.qualify_job('j')
    def test_artifact_hash_is_verified(self):
        class Bad(Bridge):
            def codex_artifact(self,job_id,artifact_id):
                value=super().codex_artifact(job_id,artifact_id);value['sha256']='0'*64;return value
        with tempfile.TemporaryDirectory() as td:
            p=CapabilityCandidatePipeline(Bad({'CAPABILITY_MANIFEST.json':b'{}'}),{'enabled':True,'repo_profiles':{}},td)
            with self.assertRaisesRegex(CandidateError,'HASH'):p.qualify_job('j')
if __name__=='__main__':unittest.main()
