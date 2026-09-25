"""EAR Teacher Portal. Run behind an HTTPS reverse proxy for school use.
No external Python dependencies. Never commit the private data directory.
"""
import argparse, contextlib, getpass, hashlib, hmac, json, math, os, secrets, sqlite3, time, uuid
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
DATA = Path(os.environ.get('EAR_DATA_DIR', str(ROOT / '.ear-data')))
ORIGIN = os.environ.get('EAR_ORIGIN', 'http://localhost:8000').rstrip('/')
COOKIE = 'ear_session'
SESSION_SECONDS = 8 * 60 * 60

def password_hash(password, salt):
    return hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()

@contextlib.contextmanager
def db():
    DATA.mkdir(mode=0o700, parents=True, exist_ok=True)
    c = sqlite3.connect(DATA / 'portal.sqlite3', timeout=10)
    c.row_factory = sqlite3.Row
    c.execute('PRAGMA foreign_keys=ON')
    try:
        yield c
        c.commit()
    except Exception:
        c.rollback()
        raise
    finally:
        c.close()

def initialize():
    with db() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS teachers(id TEXT PRIMARY KEY,email TEXT NOT NULL UNIQUE,name TEXT NOT NULL,salt TEXT NOT NULL,password_hash TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY,owner_id TEXT NOT NULL REFERENCES teachers(id),expires INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS reports(id TEXT PRIMARY KEY,owner_id TEXT NOT NULL REFERENCES teachers(id),data TEXT NOT NULL,revision INTEGER NOT NULL DEFAULT 0,deleted INTEGER NOT NULL DEFAULT 0,updated INTEGER NOT NULL);
        CREATE INDEX IF NOT EXISTS reports_owner_active ON reports(owner_id,deleted);
        CREATE TABLE IF NOT EXISTS login_attempts(key TEXT PRIMARY KEY,count INTEGER NOT NULL,started INTEGER NOT NULL);
        ''')

def validate(raw):
    if not isinstance(raw, dict):
        raise ValueError('Invalid report.')
    r = {}
    for key, limit in [('name',100),('className',30),('subject',80)]:
        v = raw.get(key)
        if not isinstance(v,str) or not v.strip() or len(v)>limit:
            raise ValueError('Complete the student name, class, and subject.')
        r[key] = v.strip()
    status = raw.get('status')
    if type(status) is not int or status not in range(4):
        raise ValueError('Choose a valid student status.')
    r.update(status=status, grade=None, absences=None, total=None)
    if status < 2:
        grade = raw.get('grade')
        if type(grade) not in (int,float) or not math.isfinite(grade) or not 0<=grade<=100:
            raise ValueError('Grade must be between 0 and 100.')
        r['grade'] = grade
    else:
        total, missed = raw.get('total'), raw.get('absences')
        if type(total) is not int or type(missed) is not int or not 1<=total<=10000 or not 0<=missed<=total:
            raise ValueError('Missed classes must be whole numbers no greater than total classes.')
        r.update(total=total, absences=missed)
    return r

def public_report(row):
    return dict(json.loads(row['data']),id=row['id'],owner_id=row['owner_id'],revision=row['revision'])

class Handler(BaseHTTPRequestHandler):
    server_version = 'EARPortal'
    def log_message(self, *args):
        pass  # Avoid recording teacher or student data in HTTP logs.
    def reply(self, status, data, cookie=None, html=False):
        payload = data if html else json.dumps(data,allow_nan=False).encode()
        self.send_response(status)
        self.send_header('Content-Type','text/html; charset=utf-8' if html else 'application/json; charset=utf-8')
        self.send_header('Content-Length',str(len(payload)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','same-origin')
        self.send_header('X-Frame-Options','DENY')
        if html:
            # Single-file source has inline CSS/JS; hash only the shipped script.
            import re, base64
            script=re.search(rb'<script>(.*?)</script>',payload,re.S).group(1)
            digest=base64.b64encode(hashlib.sha256(script).digest()).decode()
            self.send_header('Content-Security-Policy',f"default-src 'self'; script-src 'sha256-{digest}'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        if ORIGIN.startswith('https://'):
            self.send_header('Strict-Transport-Security','max-age=31536000')
        if cookie:
            self.send_header('Set-Cookie',cookie)
        self.end_headers()
        self.wfile.write(payload)
    def session_cookie(self, token, age=SESSION_SECONDS):
        return f'{COOKIE}={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age={age}' + ('; Secure' if ORIGIN.startswith('https://') else '')
    def session(self,c):
        try:
            cookies=SimpleCookie(); cookies.load(self.headers.get('Cookie',''))
            token=cookies[COOKIE].value
        except (KeyError,ValueError):
            return None,None
        hashed=hashlib.sha256(token.encode()).hexdigest()
        u=c.execute('SELECT t.id,t.name,t.email FROM sessions s JOIN teachers t ON t.id=s.owner_id WHERE s.token_hash=? AND s.expires>?',(hashed,int(time.time()))).fetchone()
        return u,hashed
    def body(self):
        n=int(self.headers.get('Content-Length','0'))
        if n<1 or n>16384:
            raise ValueError('Invalid request size.')
        if self.headers.get('Content-Type','').split(';')[0]!='application/json':
            raise ValueError('Use JSON for this request.')
        result=json.loads(self.rfile.read(n))
        if not isinstance(result,dict):
            raise ValueError('Invalid request body.')
        return result
    def do_GET(self): self.handle_request('GET')
    def do_POST(self): self.handle_request('POST')
    def do_PUT(self): self.handle_request('PUT')
    def do_DELETE(self): self.handle_request('DELETE')
    def handle_request(self,method):
        try:
            self.route(method)
        except (ValueError,json.JSONDecodeError):
            self.reply(400,{'error':'Invalid input. Check the report fields and try again.'})
        except Exception:
            self.reply(503,{'error':'The teacher server is unavailable. Please try again.'})
    def route(self,method):
        path=urlsplit(self.path).path
        if method=='GET' and path in ('/','/index.html'):
            return self.reply(200,(ROOT/'index.html').read_bytes(),html=True)
        if not path.startswith('/api/'):
            return self.reply(404,{'error':'Not found.'})
        if method!='GET' and self.headers.get('Origin')!=ORIGIN:
            return self.reply(403,{'error':'Invalid request origin.'})
        now=int(time.time())
        with db() as c:
            if path=='/api/login' and method=='POST':
                b=self.body(); email=b.get('email',''); pw=b.get('password','')
                if not isinstance(email,str) or not isinstance(pw,str) or len(email)>254 or len(pw)>256:
                    raise ValueError('Invalid login.')
                email=email.strip().lower()
                # Rate limit both remote address and account; never trust forwarded headers.
                keys=['ip:'+self.client_address[0],'email:'+email]
                c.execute('DELETE FROM login_attempts WHERE started<?',(now-900,))
                for key in keys:
                    row=c.execute('SELECT count FROM login_attempts WHERE key=?',(key,)).fetchone()
                    if row and row['count']>=10:
                        return self.reply(429,{'error':'Too many sign-in attempts. Try again in 15 minutes.'})
                t=c.execute('SELECT * FROM teachers WHERE email=?',(email,)).fetchone()
                salt=t['salt'] if t else '00'*16
                candidate=password_hash(pw,salt)
                if not t or not hmac.compare_digest(candidate,t['password_hash']):
                    for key in keys:
                        c.execute('INSERT INTO login_attempts(key,count,started) VALUES (?,1,?) ON CONFLICT(key) DO UPDATE SET count=count+1',(key,now))
                    return self.reply(401,{'error':'Incorrect email or password.'})
                c.execute('DELETE FROM login_attempts WHERE key=?',('email:'+email,))
                c.execute('DELETE FROM sessions WHERE expires<=?',(now,))
                _,old=self.session(c)
                if old: c.execute('DELETE FROM sessions WHERE token_hash=?',(old,))
                token=secrets.token_urlsafe(32)
                c.execute('INSERT INTO sessions VALUES (?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),t['id'],now+SESSION_SECONDS))
                return self.reply(200,{'ok':True},self.session_cookie(token))
            user,session_hash=self.session(c)
            if path=='/api/logout' and method=='POST':
                if session_hash:c.execute('DELETE FROM sessions WHERE token_hash=?',(session_hash,))
                return self.reply(200,{'ok':True},self.session_cookie('',0))
            if not user:
                return self.reply(401,{'error':'Sign in to access your reports.'})
            owner=user['id']
            if path=='/api/me' and method=='GET':
                return self.reply(200,dict(user))
            if path=='/api/reports' and method=='GET':
                rows=c.execute('SELECT * FROM reports WHERE owner_id=? AND deleted=0 ORDER BY updated DESC,id',(owner,)).fetchall()
                return self.reply(200,[public_report(r) for r in rows])
            rid=path.removeprefix('/api/reports/') if path.startswith('/api/reports/') else None
            existing=None
            if rid:
                existing=c.execute('SELECT * FROM reports WHERE id=? AND owner_id=? AND deleted=0',(rid,owner)).fetchone()
                if not existing:return self.reply(404,{'error':'Report unavailable.'})
            if rid and method=='GET':
                return self.reply(200,public_report(existing))
            if (path=='/api/reports' and method=='POST') or (rid and method in ('PUT','DELETE')):
                raw=self.body()
                if rid:
                    revision=raw.get('revision')
                    if type(revision) is not int or revision!=existing['revision']:
                        return self.reply(409,{'error':'This report changed elsewhere. Reload the page before trying again.'})
                if method=='DELETE':
                    c.execute('UPDATE reports SET deleted=1,revision=revision+1,updated=? WHERE id=? AND owner_id=? AND revision=?',(now,rid,owner,revision))
                    return self.reply(200,{'ok':True})
                report=validate(raw)
                others=c.execute('SELECT id,data FROM reports WHERE owner_id=? AND deleted=0',(owner,)).fetchall()
                if method=='POST' and len(others)>=500:
                    return self.reply(400,{'error':'Your workspace has reached 500 reports.'})
                key=lambda r: (r['name'].casefold(),r['className'].casefold(),r['subject'].casefold(),r['status']//2)
                if any(r['id']!=rid and key(json.loads(r['data']))==key(report) for r in others):
                    return self.reply(409,{'error':'You already have a report for this student, subject, and report type.'})
                # owner_id is always derived from the server session, never the submitted form.
                if rid:
                    c.execute('UPDATE reports SET data=?,revision=revision+1,updated=? WHERE id=? AND owner_id=? AND revision=?',(json.dumps(report),now,rid,owner,revision))
                else:
                    rid=str(uuid.uuid4())
                    c.execute('INSERT INTO reports(id,owner_id,data,updated) VALUES (?,?,?,?)',(rid,owner,json.dumps(report),now))
                row=c.execute('SELECT * FROM reports WHERE id=? AND owner_id=?',(rid,owner)).fetchone()
                return self.reply(200 if method=='PUT' else 201,public_report(row))
            self.reply(404,{'error':'Not found.'})

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    add=sub.add_parser('add-teacher');add.add_argument('email');add.add_argument('name')
    serve=sub.add_parser('serve');serve.add_argument('--port',type=int,default=8000);serve.add_argument('--host',default='127.0.0.1')
    args=parser.parse_args();initialize()
    if args.command=='add-teacher':
        email=args.email.strip().lower()
        if not email.endswith('@ear.com.br') or email.count('@')!=1:
            parser.error('Use an approved @ear.com.br staff email.')
        pw=getpass.getpass('New teacher password (at least 12 characters): ')
        if len(pw)<12 or len(pw)>256 or pw!=getpass.getpass('Confirm password: '):
            parser.error('Passwords must match and contain 12–256 characters.')
        salt=secrets.token_hex(16)
        try:
            with db() as c:c.execute('INSERT INTO teachers VALUES (?,?,?,?,?)',(str(uuid.uuid4()),email,args.name.strip(),salt,password_hash(pw,salt)))
        except sqlite3.IntegrityError:
            parser.error('This teacher already exists. No account was changed.')
        print('Teacher account created. Share the credentials privately.')
    else:
        if not ORIGIN.startswith('https://') and urlsplit(ORIGIN).hostname not in ('localhost','127.0.0.1'):
            parser.error('Set EAR_ORIGIN to the HTTPS origin of the portal.')
        if args.host not in ('127.0.0.1','localhost') and not ORIGIN.startswith('https://'):
            parser.error('Non-local servers require an HTTPS EAR_ORIGIN and a reverse proxy.')
        HTTPServer((args.host,args.port),Handler).serve_forever()
if __name__=='__main__':main()
