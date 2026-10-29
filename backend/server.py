"""AegisOps local MVP. Standard-library API, SQLite and explainable policy checks."""
import json, os, re, sqlite3, threading, uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
try:
    from . import ai, remediation
except ImportError:
    import ai
    import remediation

DB = os.getenv('AEGIS_DB', 'data/aegis.db')
DIST = Path(os.getenv('AEGIS_DIST', 'frontend/dist')).resolve()
LOCK = threading.Lock()

def now():
    return datetime.now(timezone.utc).isoformat()

def connect():
    Path(DB).parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB)
    connection.row_factory = sqlite3.Row
    return connection

def init_db():
    with connect() as c:
        c.executescript('''CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY,name TEXT NOT NULL,url TEXT,created TEXT);
        CREATE TABLE IF NOT EXISTS scans(id TEXT PRIMARY KEY,project_id TEXT,created TEXT,payload TEXT);
        CREATE TABLE IF NOT EXISTS incidents(id TEXT PRIMARY KEY,scan_id TEXT,project_id TEXT,severity TEXT,title TEXT,status TEXT,created TEXT);
        CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY,created TEXT,message TEXT);
        CREATE TABLE IF NOT EXISTS sources(scan_id TEXT PRIMARY KEY,payload TEXT);
        CREATE TABLE IF NOT EXISTS plans(id TEXT PRIMARY KEY,scan_id TEXT,created TEXT,status TEXT,payload TEXT);
        CREATE TABLE IF NOT EXISTS analyses(id TEXT PRIMARY KEY,scan_id TEXT,created TEXT,payload TEXT);''')

def save_scan(c, project, files):
    result = analyze(files)
    sid = uuid.uuid4().hex
    created = now()
    c.execute('INSERT INTO scans VALUES(?,?,?,?)', (sid, project, created, json.dumps(result)))
    # Keep source snapshots for local remediation, except detected credentials.
    if not any(f['rule'] == 'SEC-001' for f in result['findings']):
        c.execute('INSERT INTO sources VALUES(?,?)', (sid, json.dumps(files)))
    for f in result['findings']:
        c.execute('INSERT INTO incidents VALUES(?,?,?,?,?,?,?)',
            (uuid.uuid4().hex, sid, project, f['severity'], f['title'], 'open', created))
    return dict(result, id=sid, created=created, project_id=project)

def audit(c, message):
    c.execute('INSERT INTO events VALUES(?,?,?)', (uuid.uuid4().hex, now(), message))

def analyze(files):
    """Conservative text-based checks, not a vulnerability/compliance certification."""
    findings = []
    def add(path, rule, severity, title, fix):
        findings.append(dict(path=path,rule=rule,severity=severity,title=title,remediation=fix))
    for path, text in files.items():
        if re.search(r'AKIA[0-9A-Z]{16}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----', text):
            add(path,'SEC-001','critical','Potential committed credential','Revoke the exposed credential, remove it from history, and use a secret manager.')
        if path.lower().endswith('dockerfile'):
            if not re.search(r'^\s*USER\s+(?!root\b|0\b)\S+',text,re.M|re.I):
                add(path,'CTR-001','high','Non-root container user not declared','Declare USER with a dedicated non-root UID in the final image stage.')
            if re.search(r'^\s*FROM\s+\S+:latest\b',text,re.M|re.I):
                add(path,'CTR-002','medium','Mutable latest image tag','Pin a reviewed image version and preferably its digest.')
            if not re.search(r'^\s*HEALTHCHECK\s+',text,re.M|re.I):
                add(path,'CTR-003','low','Container health check missing','Add a HEALTHCHECK that verifies the application health endpoint.')
        if path.endswith(('.yaml','.yml')) and re.search(r'kind:\s*(Deployment|Pod|StatefulSet)',text):
            for pattern, rule, severity, title, fix in [
                (r'privileged:\s*true','K8S-001','critical','Privileged container enabled','Set privileged: false and drop unneeded capabilities.'),
                (r'hostNetwork:\s*true','K8S-002','high','Host network enabled','Remove hostNetwork unless there is a documented need.')]:
                if re.search(pattern,text,re.I): add(path,rule,severity,title,fix)
            if not re.search(r'runAsNonRoot:\s*true',text,re.I):
                add(path,'K8S-003','high','Non-root policy missing','Set securityContext.runAsNonRoot: true with an appropriate user.')
            if not re.search(r'limits\s*:',text):
                add(path,'K8S-004','medium','Resource limits missing','Set CPU and memory requests and limits for each container.')
            if not re.search(r'readinessProbe\s*:',text):
                add(path,'K8S-005','medium','Readiness probe missing','Configure a readiness probe before routing traffic to the pod.')
        if path.endswith('.tf'):
            if '0.0.0.0/0' in text or '::/0' in text:
                add(path,'IAC-001','high','Internet-wide network range detected','Review the rule direction and port; restrict inbound access to approved CIDRs.')
            if re.search(r'encrypted\s*=\s*false',text):
                add(path,'IAC-002','high','Encryption explicitly disabled','Enable storage encryption using a suitable KMS key.')
            if re.search(r'public-read(?:-write)?',text):
                add(path,'IAC-003','critical','Public storage ACL detected','Use private ACLs and enable public access blocking.')
    # Score is a local heuristic; never a security certification.
    penalty = sum({'critical':30,'high':15,'medium':7,'low':3}[f['severity']] for f in findings)
    return dict(findings=findings, score=max(0,100-penalty),
                status='blocked' if any(f['severity'] in ('critical','high') for f in findings) else 'passed',
                summary=f'Checked {len(files)} file(s); found {len(findings)} policy issue(s).',
                engine='deterministic-policy-v1', files_checked=len(files))

class Handler(BaseHTTPRequestHandler):
    server_version = 'AegisOps/2.0'
    def send_json(self, status, data):
        raw = json.dumps(data).encode()
        self.send_response(status); self.send_header('Content-Type','application/json')
        self.send_header('Cache-Control','no-store'); self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Length',str(len(raw))); self.end_headers(); self.wfile.write(raw)
    def do_GET(self):
        path = self.path.split('?')[0]
        if path == '/api/health': return self.send_json(200,dict(status='ok',engine='deterministic-policy-v1'))
        if path == '/api/state':
            if self.headers.get('Host','').split(':')[0] not in ('localhost','127.0.0.1'):
                return self.send_json(403,dict(error='Use localhost'))
            with connect() as c:
                projects=[dict(x) for x in c.execute('SELECT * FROM projects ORDER BY created DESC')]
                scans=[dict(json.loads(x['payload']),id=x['id'],project_id=x['project_id'],created=x['created']) for x in c.execute('SELECT * FROM scans ORDER BY created DESC LIMIT 100')]
                incidents=[dict(x) for x in c.execute('SELECT * FROM incidents ORDER BY created DESC LIMIT 500')]
                plans=[dict(x) for x in c.execute('SELECT id,scan_id,created,status FROM plans ORDER BY created DESC LIMIT 100')]
                events=[dict(x) for x in c.execute('SELECT * FROM events ORDER BY created DESC LIMIT 100')]
            return self.send_json(200,dict(projects=projects,scans=scans,incidents=incidents,plans=plans,events=events,ai=ai.configuration()))
        if path.startswith('/api/'): return self.send_json(404,dict(error='Endpoint not found'))
        target=(DIST/path.lstrip('/')).resolve()
        if not target.is_relative_to(DIST): return self.send_json(403,dict(error='Forbidden'))
        if not target.is_file(): target=DIST/'index.html'
        if not target.exists(): return self.send_json(503,dict(error='Frontend not built. Run npm ci && npm run build in frontend.'))
        import mimetypes
        raw=target.read_bytes(); self.send_response(200)
        self.send_header('Content-Type',mimetypes.guess_type(str(target))[0] or 'application/octet-stream')
        self.send_header('X-Content-Type-Options','nosniff'); self.send_header('Content-Length',str(len(raw)))
        self.end_headers(); self.wfile.write(raw)
    def do_POST(self):
        # Local-only application: reject cross-origin browser mutations and DNS rebinding.
        host=self.headers.get('Host','').split(':')[0]
        if host not in ('localhost','127.0.0.1','[','testserver'):
            return self.send_json(403,dict(error='Use localhost; this MVP is not a public multi-user service.'))
        origin=self.headers.get('Origin')
        if origin and origin not in ('http://'+self.headers.get('Host',''),'http://localhost:5173','http://127.0.0.1:5173'):
            return self.send_json(403,dict(error='Origin rejected'))
        try:
            length=int(self.headers.get('Content-Length','0'))
            if length < 1 or length > 262144: return self.send_json(413,dict(error='Request must be between 1 byte and 256 KiB'))
            if self.headers.get('Content-Type','').split(';')[0] != 'application/json': return self.send_json(415,dict(error='Use application/json'))
            data=json.loads(self.rfile.read(length))
            if not isinstance(data,dict): raise ValueError('Expected an object')
            path=self.path
            if path == '/api/ai/analyze':
                if not isinstance(data.get('scan_id'),str): raise ValueError('Choose a scan first')
                with connect() as c:
                    row=c.execute('SELECT payload FROM scans WHERE id=?',(data['scan_id'],)).fetchone()
                if not row: return self.send_json(404,dict(error='Scan not found'))
                try:
                    result=ai.explain(json.loads(row['payload'])['findings'])
                except ai.ProviderError as e:
                    return self.send_json(503,dict(error=str(e)))
                with LOCK, connect() as c:
                    c.execute('INSERT INTO analyses VALUES(?,?,?,?)',(uuid.uuid4().hex,data['scan_id'],now(),json.dumps(result)))
                    audit(c,'AI analysis completed for scan '+data['scan_id'])
                return self.send_json(200,result)
            with LOCK, connect() as c:
                if path == '/api/remediation/preview':
                    sid=data.get('scan_id')
                    if not isinstance(sid,str): raise ValueError('Choose a scan first')
                    row=c.execute('SELECT payload FROM sources WHERE scan_id=?',(sid,)).fetchone()
                    if not row: return self.send_json(409,dict(error='Source snapshot unavailable. Rescan a file without detected credentials.'))
                    before=json.loads(row['payload']); plan=remediation.propose(before)
                    if not plan['changes']: return self.send_json(409,dict(error='No allowlisted automatic fixes apply. Follow the manual guidance for the remaining findings.'))
                    pid=uuid.uuid4().hex
                    c.execute('INSERT INTO plans VALUES(?,?,?,?,?)',(pid,sid,now(),'pending',json.dumps(dict(plan,before=before))))
                    audit(c,'Remediation proposed: '+pid); c.commit()
                    return self.send_json(201,dict(plan,id=pid,status='pending'))
                if path in ('/api/remediation/apply','/api/remediation/rollback'):
                    pid=data.get('plan_id')
                    if not isinstance(pid,str) or data.get('approved') is not True: raise ValueError('A reviewed plan_id and approved: true are required')
                    row=c.execute('SELECT * FROM plans WHERE id=?',(pid,)).fetchone()
                    if not row: return self.send_json(404,dict(error='Plan not found'))
                    rollback=path.endswith('rollback')
                    expected='applied' if rollback else 'pending'
                    if row['status'] != expected: return self.send_json(409,dict(error='Plan state changed. Refresh before continuing.'))
                    plan=json.loads(row['payload'])
                    scan=c.execute('SELECT project_id FROM scans WHERE id=?',(row['scan_id'],)).fetchone()
                    files=plan['before'] if rollback else plan['files']
                    result=save_scan(c,scan['project_id'],files)
                    status='rolled_back' if rollback else 'applied'
                    c.execute('UPDATE plans SET status=? WHERE id=?',(status,pid))
                    audit(c,'Workspace remediation '+status+': '+pid+'; verification scan '+result['id']); c.commit()
                    return self.send_json(200,dict(id=pid,status=status,scan=result,files=files,scope=plan['scope']))
                if path == '/api/projects':
                    name=data.get('name',''); url=data.get('url','')
                    if not isinstance(name,str) or not 1 <= len(name.strip()) <= 100: raise ValueError('Project name must be 1–100 characters')
                    if not isinstance(url,str) or len(url)>500: raise ValueError('Invalid URL')
                    if url and not re.fullmatch(r'https://github\.com/[\w.-]+/[\w.-]+/?',url): raise ValueError('Use an HTTPS GitHub repository URL')
                    item=dict(id=uuid.uuid4().hex,name=name.strip(),url=url,created=now())
                    c.execute('INSERT INTO projects VALUES(:id,:name,:url,:created)',item)
                    c.commit()
                    return self.send_json(201,item)
                if path == '/api/scans':
                    project=data.get('project_id'); files=data.get('files')
                    if not isinstance(project,str) or not c.execute('SELECT id FROM projects WHERE id=?',(project,)).fetchone(): raise ValueError('Project not found')
                    if not isinstance(files,dict) or not 1<=len(files)<=20: raise ValueError('Provide 1–20 text files')
                    if any(not isinstance(k,str) or not 1<=len(k)<=200 or not isinstance(v,str) or len(v)>100000 for k,v in files.items()): raise ValueError('Invalid file name or content')
                    if any(not (k.lower().endswith('dockerfile') or k.endswith(('.yaml','.yml','.tf'))) for k in files): raise ValueError('Supported files: Dockerfile, YAML, Terraform')
                    result=save_scan(c,project,files)
                    c.commit()
                    return self.send_json(201,result)
                if path == '/api/incidents/status':
                    status=data.get('status'); iid=data.get('id')
                    if status not in ('open','acknowledged','resolved') or not isinstance(iid,str): raise ValueError('Invalid incident or status')
                    if not c.execute('UPDATE incidents SET status=? WHERE id=?',(status,iid)).rowcount: return self.send_json(404,dict(error='Incident not found'))
                    c.commit()
                    return self.send_json(200,dict(id=iid,status=status))
            return self.send_json(404,dict(error='Endpoint not found'))
        except (ValueError, TypeError, json.JSONDecodeError) as e: return self.send_json(400,dict(error=str(e)))
        except Exception:
            import traceback; traceback.print_exc(); self.log_error('Request failed'); return self.send_json(500,dict(error='Internal server error'))

if __name__ == '__main__':
    init_db()
    ThreadingHTTPServer((os.getenv('AEGIS_HOST','127.0.0.1'),int(os.getenv('PORT','8080'))),Handler).serve_forever()
