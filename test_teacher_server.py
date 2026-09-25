"""Security integration checks using only fictional temporary data."""
import http.client, json, tempfile, threading, unittest
from pathlib import Path
import teacher_server as app

class OwnershipTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory(); app.DATA=Path(cls.tmp.name); app.initialize()
        with app.db() as c:
            for ident in ('math','science'):
                salt='01'*16
                c.execute('INSERT INTO teachers VALUES (?,?,?,?,?)',(ident,ident+'@ear.com.br',ident,salt,app.password_hash('fictional-password-123',salt)))
        cls.server=app.HTTPServer(('127.0.0.1',0),app.Handler)
        cls.port=cls.server.server_address[1];app.ORIGIN='http://127.0.0.1:'+str(cls.port)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.tmp.cleanup()
    def request(self,method,path,body=None,cookie=None,origin=None):
        h={'Origin':origin or app.ORIGIN}
        if body is not None:h['Content-Type']='application/json'
        if cookie:h['Cookie']=cookie
        conn=http.client.HTTPConnection('127.0.0.1',self.port)
        conn.request(method,'/api/'+path,json.dumps(body) if body is not None else None,h)
        r=conn.getresponse();status=r.status;headers=dict(r.getheaders());data=json.loads(r.read());conn.close()
        return status,data,headers
    def login(self,name):
        status,_,h=self.request('POST','login',{'email':name+'@ear.com.br','password':'fictional-password-123'})
        self.assertEqual(status,200);self.assertIn('HttpOnly',h['Set-Cookie']);return h['Set-Cookie'].split(';')[0]
    def test_private_crud(self):
        self.assertEqual(self.request('GET','reports')[0],401)
        math=self.login('math'); science=self.login('science')
        report={'name':'Fictional Student','className':'10A','subject':'Math','status':0,'grade':55,'absences':999,'total':999,'owner_id':'science'}
        status,created,_=self.request('POST','reports',report,math)
        self.assertEqual(status,201);self.assertEqual(created['owner_id'],'math');self.assertIsNone(created['absences']);self.assertIsNone(created['total'])
        path='reports/'+created['id']
        self.assertEqual(len(self.request('GET','reports',cookie=math)[1]),1)
        self.assertEqual(self.request('GET','reports',cookie=science)[1],[])
        self.assertEqual(self.request('GET',path,cookie=science)[0],404)
        self.assertEqual(self.request('PUT',path,{**report,'revision':0},science)[0],404)
        self.assertEqual(self.request('DELETE',path,{'revision':0},science)[0],404)
        self.assertEqual(self.request('PUT',path,{**report,'revision':0},math,'https://untrusted.example')[0],403)
        status,updated,_=self.request('PUT',path,{**report,'status':2,'total':60,'absences':18,'revision':0},math)
        self.assertEqual(status,200);self.assertIsNone(updated['grade']);self.assertEqual(updated['revision'],1)
        self.assertEqual(self.request('PUT',path,{**report,'revision':0},math)[0],409)
        self.assertEqual(self.request('DELETE',path,{'revision':0},math)[0],409)
        self.assertEqual(self.request('POST','reports',{**report,'status':3,'total':5,'absences':6},math)[0],400)
        self.assertEqual(self.request('DELETE',path,{'revision':1},math)[0],200)
        self.assertEqual(self.request('GET','reports',cookie=math)[1],[])
        self.assertEqual(self.request('GET',path,cookie=math)[0],404)
        self.assertEqual(self.request('POST','logout',{},math)[0],200)
        self.assertEqual(self.request('GET','reports',cookie=math)[0],401)
    def test_validation(self):
        base={'name':'Fake','className':'10A','subject':'Biology','status':3,'absences':3,'total':10}
        self.assertEqual(app.validate(base)['grade'],None)
        for changes in ({'status':True},{'status':4},{'total':0},{'absences':-1},{'absences':11},{'absences':2.5},{'name':''}):
            with self.assertRaises(ValueError):app.validate({**base,**changes})
        with self.assertRaises(ValueError):app.validate({**base,'status':0,'grade':float('nan')})
        with self.assertRaises(ValueError):app.validate({**base,'status':0,'grade':101})
        self.assertEqual(app.validate({**base,'status':1,'grade':65})['absences'],None)
if __name__=='__main__':unittest.main()
