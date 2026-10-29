import importlib.util, io, json, os, sys, tempfile, threading, unittest
from pathlib import Path
from unittest.mock import patch
from urllib.request import Request, urlopen
from urllib.error import HTTPError
sys.path.insert(0,str(Path(__file__).parents[1]))
import ai, remediation
spec=importlib.util.spec_from_file_location('integration_server',Path(__file__).parents[1]/'server.py')
server=importlib.util.module_from_spec(spec);spec.loader.exec_module(server)

class AITransportTests(unittest.TestCase):
    def test_disabled_requires_configuration(self):
        with patch.dict(os.environ,{},clear=True):
            self.assertFalse(ai.configuration()['configured'])
            with self.assertRaises(ai.ProviderError):ai.explain([])
    def test_anthropic_request_redacts_source_and_paths(self):
        finding={'rule':'CTR-001','severity':'high','title':'Non-root user missing','remediation':'Set USER',
                 'path':'PRIVATE_FILENAME','source':'PRIVATE_SOURCE'}
        response=io.BytesIO(json.dumps({'content':[{'type':'text','text':'Use a dedicated runtime user.'}]}).encode())
        with patch.dict(os.environ,{'AEGIS_AI_PROVIDER':'anthropic','AEGIS_AI_MODEL':'configured-model','ANTHROPIC_API_KEY':'test-only'},clear=True):
            with patch('ai.urllib.request.urlopen',return_value=response) as transport:
                result=ai.explain([finding])
        payload=transport.call_args.args[0].data.decode()
        self.assertNotIn('PRIVATE_FILENAME',payload);self.assertNotIn('PRIVATE_SOURCE',payload)
        self.assertTrue(result['advisory']);self.assertIn('runtime user',result['text'])
    def test_failure_does_not_expose_credentials(self):
        with patch.dict(os.environ,{'AEGIS_AI_PROVIDER':'anthropic','AEGIS_AI_MODEL':'test','ANTHROPIC_API_KEY':'private-key'},clear=True):
            with patch('ai.urllib.request.urlopen',side_effect=RuntimeError('private-key should not leak')):
                with self.assertRaises(ai.ProviderError) as error:ai.explain([])
        self.assertNotIn('private-key',str(error.exception))
    def test_bedrock_adapter(self):
        from types import SimpleNamespace
        client=unittest.mock.Mock()
        client.converse.return_value={'output':{'message':{'content':[{'text':'Review encryption settings.'}]}}}
        fake_boto=SimpleNamespace(client=unittest.mock.Mock(return_value=client))
        modules={'boto3':fake_boto,'botocore.config':SimpleNamespace(Config=lambda **kw:kw)}
        with patch.dict(os.environ,{'AEGIS_AI_PROVIDER':'bedrock','AEGIS_AI_MODEL':'model-arn','AWS_REGION':'ap-south-1'},clear=True),patch.dict(sys.modules,modules):
            result=ai.explain([])
        self.assertEqual(result['provider'],'bedrock');self.assertEqual(client.converse.call_args.kwargs['modelId'],'model-arn')

class RemediationTests(unittest.TestCase):
    def test_allowlist_and_no_invented_settings(self):
        files={'Dockerfile':'FROM python:latest\nUSER root',
               'main.tf':'encrypted = false\nacl = "public-read"\ncidr = "0.0.0.0/0"\n',
               'pod.yaml':'kind: Pod\nprivileged: true\nhostNetwork: true\n'}
        plan=remediation.propose(files)
        self.assertEqual(plan['files']['Dockerfile'],files['Dockerfile'])
        self.assertIn('0.0.0.0/0',plan['files']['main.tf'])
        self.assertIn('encrypted = true',plan['files']['main.tf'])
        self.assertIn('privileged: false',plan['files']['pod.yaml'])
        self.assertEqual(len(plan['changes']),2)
        self.assertEqual(remediation.propose(plan['files'])['changes'],[])

class RemediationAPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();server.DB=str(Path(cls.tmp.name)/'state.db');server.init_db()
        cls.http=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
        cls.base='http://127.0.0.1:'+str(cls.http.server_port)
        threading.Thread(target=cls.http.serve_forever,daemon=True).start()
    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown();cls.http.server_close();cls.tmp.cleanup()
    def request(self,path,data=None):
        req=Request(self.base+path,data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json'})
        try:
            with urlopen(req) as r:return r.status,json.load(r)
        except HTTPError as e:return e.code,json.load(e)
    def create_scan(self,files):
        p=self.request('/api/projects',{'name':'Integration project'})[1]
        return self.request('/api/scans',{'project_id':p['id'],'files':files})[1]
    def test_preview_apply_idempotency_rollback_and_audit(self):
        original='encrypted = false\nacl = "public-read"\n'
        scan=self.create_scan({'main.tf':original})
        status,plan=self.request('/api/remediation/preview',{'scan_id':scan['id']})
        self.assertEqual(status,201);self.assertIn('+encrypted = true',plan['changes'][0]['diff'])
        self.assertEqual(self.request('/api/remediation/apply',{'plan_id':plan['id'],'approved':False})[0],400)
        status,result=self.request('/api/remediation/apply',{'plan_id':plan['id'],'approved':True})
        self.assertEqual(status,200);self.assertEqual(result['scan']['findings'],[])
        self.assertEqual(self.request('/api/remediation/apply',{'plan_id':plan['id'],'approved':True})[0],409)
        status,restored=self.request('/api/remediation/rollback',{'plan_id':plan['id'],'approved':True})
        self.assertEqual(status,200);self.assertEqual(restored['files']['main.tf'],original)
        self.assertEqual(restored['scan']['score'],scan['score'])
        state=self.request('/api/state')[1]
        self.assertTrue(any(p['status']=='rolled_back' for p in state['plans']))
        self.assertGreaterEqual(len(state['events']),3)
        with server.connect() as c:
            self.assertEqual(json.loads(c.execute('SELECT payload FROM sources WHERE scan_id=?',(scan['id'],)).fetchone()[0])['main.tf'],original)
    def test_detected_credentials_not_saved_or_remediated(self):
        scan=self.create_scan({'main.tf':'# AKIA'+'X'*16+'\nencrypted = false'})
        with server.connect() as c:self.assertIsNone(c.execute('SELECT scan_id FROM sources WHERE scan_id=?',(scan['id'],)).fetchone())
        self.assertEqual(self.request('/api/remediation/preview',{'scan_id':scan['id']})[0],409)
    def test_no_fix_fails_honestly(self):
        scan=self.create_scan({'Dockerfile':'FROM python:latest'})
        self.assertEqual(self.request('/api/remediation/preview',{'scan_id':scan['id']})[0],409)
    def test_ai_endpoint_success_and_provider_failure(self):
        scan=self.create_scan({'Dockerfile':'FROM python:latest'})
        with patch.object(server.ai,'explain',return_value={'text':'Advisory','provider':'mock','model':'mock','advisory':True}):
            status,result=self.request('/api/ai/analyze',{'scan_id':scan['id']})
            self.assertEqual(status,200);self.assertTrue(result['advisory'])
        with patch.object(server.ai,'explain',side_effect=ai.ProviderError('Not configured')):
            self.assertEqual(self.request('/api/ai/analyze',{'scan_id':scan['id']})[0],503)
        self.assertEqual(self.request('/api/ai/analyze',{'scan_id':'missing'})[0],404)

if __name__=='__main__':unittest.main()
