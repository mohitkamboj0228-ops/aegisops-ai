import importlib.util, json, tempfile, threading, unittest, sys
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
sys.path.insert(0,str(Path(__file__).parents[1]))
spec=importlib.util.spec_from_file_location('server',Path(__file__).parents[1]/'server.py')
server=importlib.util.module_from_spec(spec);spec.loader.exec_module(server)

class PolicyTests(unittest.TestCase):
    def test_insecure_container(self):
        result=server.analyze({'Dockerfile':'FROM python:latest\nCMD ["python"]'})
        self.assertEqual(result['status'],'blocked')
        self.assertEqual({f['rule'] for f in result['findings']},{'CTR-001','CTR-002','CTR-003'})
    def test_hardened_container(self):
        result=server.analyze({'Dockerfile':'FROM python:3.12-slim\nUSER 10001\nHEALTHCHECK CMD true'})
        self.assertEqual(result['findings'],[])
    def test_kubernetes_and_terraform(self):
        result=server.analyze({'deploy.yaml':'kind: Pod\nprivileged: true\nhostNetwork: true','main.tf':'cidr = "0.0.0.0/0"\nencrypted = false\nacl = "public-read"'})
        self.assertEqual(len(result['findings']),8)
        self.assertEqual(result['status'],'blocked')
    def test_secret_detection(self):
        self.assertEqual(server.analyze({'Dockerfile':'# AKIA'+'X'*16})['findings'][0]['rule'],'SEC-001')

class APITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();server.DB=str(Path(cls.tmp.name)/'test.db');server.init_db()
        cls.http=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
        cls.base='http://127.0.0.1:'+str(cls.http.server_port)
        cls.thread=threading.Thread(target=cls.http.serve_forever,daemon=True);cls.thread.start()
    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown();cls.http.server_close();cls.tmp.cleanup()
    def request(self,path,data=None,headers=None):
        req=Request(self.base+path,data=json.dumps(data).encode() if data is not None else None,headers=headers or {'Content-Type':'application/json'})
        try:
            with urlopen(req) as r:return r.status,json.load(r)
        except HTTPError as e:return e.code,json.load(e)
    def test_lifecycle_and_persistence(self):
        status,p=self.request('/api/projects',{'name':'API test','url':'https://github.com/example/repo'})
        self.assertEqual(status,201)
        status,scan=self.request('/api/scans',{'project_id':p['id'],'files':{'Dockerfile':'FROM python:latest'}})
        self.assertEqual(status,201);self.assertEqual(scan['status'],'blocked')
        state=self.request('/api/state')[1]; incident=next(i for i in state['incidents'] if i['scan_id']==scan['id'])
        self.assertEqual(self.request('/api/incidents/status',{'id':incident['id'],'status':'resolved'})[0],200)
        with server.connect() as c:
            self.assertEqual(c.execute('SELECT status FROM incidents WHERE id=?',(incident['id'],)).fetchone()[0],'resolved')
        self.assertEqual(self.request('/api/state')[1]['scans'][0]['id'],scan['id'])
    def test_invalid_input(self):
        for body in [{'name':''},{'name':'x','url':'http://169.254.169.254/latest/meta-data/'}]:
            self.assertEqual(self.request('/api/projects',body)[0],400)
        self.assertEqual(self.request('/api/scans',{'project_id':'missing','files':{}})[0],400)
        self.assertEqual(self.request('/api/projects',[])[0],400)
    def test_cross_origin_and_host_rejected(self):
        self.assertEqual(self.request('/api/projects',{'name':'bad'},{'Content-Type':'application/json','Origin':'https://evil.example'})[0],403)
        self.assertEqual(self.request('/api/projects',{'name':'bad'},{'Content-Type':'application/json','Host':'evil.example'})[0],403)
    def test_health_and_unsupported_media(self):
        self.assertEqual(self.request('/api/health')[1]['status'],'ok')
        self.assertEqual(self.request('/api/projects',{'name':'x'},{'Content-Type':'text/plain'})[0],415)

if __name__=='__main__':unittest.main()
