from __future__ import annotations
import importlib.util
import hashlib
import hmac
import http.client
import json
import socket
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

MODULE_FILE = Path(__file__).with_name("user_browser_bridge.py")
spec=importlib.util.spec_from_file_location("cassandre_user_browser_bridge_for_test",MODULE_FILE)
bridge=importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)

SAMPLE_CERT=b"cassandre test certificate, not production"
ID="WORKER-TEST-UNIQUE-123456"
SECRET="unit-test-secret-not-production"

class FakeTLSResponse:
    status=200
    def read(self,limit):
        return b'{"Status":"OK","Worker":{"hostname":"TEST"}}'
    def getheader(self,key):
        return "application/json; charset=utf-8"

class FakeSocket:
    def getpeercert(self,binary_form=False):
        assert binary_form
        return SAMPLE_CERT

class FakeTLSConnection:
    seen=[]
    def __init__(self,host,port,timeout,context):
        assert host=="controller.example.invalid"
        assert port==9000
        self.sock=None
    def connect(self):
        self.sock=FakeSocket()
    def request(self,method,target,body=None,headers=None):
        assert method in {"GET","POST"}
        proof=headers["X-Cassandre-Worker-Assertion"]
        parts=proof.split("|")
        assert len(parts)==4
        wid,issued,nonce,signature=parts
        assert wid==ID
        assert abs(int(time.time())-int(issued))<60
        assert len(nonce)>=16
        msg="\n".join(("CASSANDRE-WORKER-ASSERTION/1",wid,issued,nonce)).encode()
        expected=hmac.new(SECRET.encode(),msg,hashlib.sha256).hexdigest().upper()
        assert hmac.compare_digest(signature,expected)
        self.seen.append((method,target))
    def getresponse(self):
        return FakeTLSResponse()
    def close(self):
        pass

class BridgeTests(unittest.TestCase):
    def setUp(self):
        FakeTLSConnection.seen.clear()
        self.dir=tempfile.TemporaryDirectory(prefix="cassandre-bridge-regression-")
        self.config=Path(self.dir.name)/"worker.json"
        self.config.write_text(json.dumps({
            "worker_id":ID,
            "shared_secret":SECRET,
            "controller_url":"https://controller.example.invalid:9000",
            "pinned_tls_sha256":hashlib.sha256(SAMPLE_CERT).hexdigest()
        }))
        s=socket.socket()
        s.bind(("127.0.0.1",0))
        port=s.getsockname()[1]
        s.close()
        self.port=port
        self.server=bridge.create_server(self.config,port)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
        self.patcher=patch.object(bridge.http.client,"HTTPSConnection",FakeTLSConnection)
        self.patcher.start()
    def tearDown(self):
        self.patcher.stop()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)
        self.dir.cleanup()
    def request(self,method,path,body=None,headers=None):
        c=http.client.HTTPConnection("127.0.0.1",self.port,timeout=4)
        try:
            c.request(method,path,body=body,headers=headers or {})
            r=c.getresponse()
            return r.status,r.read()
        finally:
            c.close()
    def test_authenticated_get_routes(self):
        for route in ["/worker","/planning","/applications","/connections",
                      "/api/worker","/api/planning","/api/v1/applications",
                      "/api/v1/connector-status"]:
            with self.subTest(route=route):
                status,body=self.request("GET",route)
                self.assertEqual(status,200)
                self.assertIn(b'"Status":"OK"',body)
        self.assertEqual(len(FakeTLSConnection.seen),8)
    def test_nonexistent_private_route_is_not_proxied(self):
        for route in ["/directory","/directory/v1/workers","/admin","/api/secret"]:
            with self.subTest(route=route):
                code,_=self.request("GET",route)
                self.assertEqual(code,404)
    def test_post_requires_same_origin(self):
        route="/api/worker/storage"
        for headers in [{},{"Origin":"https://bad.example"},{"Origin":"null"}]:
            headers={**headers,"Content-Type":"application/json"}
            code,_=self.request("POST",route,b"{}",headers)
            self.assertEqual(code,403)
        code,_=self.request("POST",route,b"{}",{
          "Origin":f"http://127.0.0.1:{self.port}",
          "Content-Type":"application/json"})
        self.assertEqual(code,200)
        self.assertIn(("POST",route),FakeTLSConnection.seen)
    def test_wrong_host_does_not_proxy(self):
        c=http.client.HTTPConnection("127.0.0.1",self.port,timeout=4)
        try:
            c.putrequest("GET","/worker",skip_host=True)
            c.putheader("Host","attacker.example")
            c.endheaders()
            r=c.getresponse()
            self.assertEqual(r.status,404)
            r.read()
        finally:
            c.close()
    def test_bad_tls_pin_fails_closed(self):
        conf=json.loads(self.config.read_text())
        conf["pinned_tls_sha256"]="0"*64
        self.config.write_text(json.dumps(conf))
        code,body=self.request("GET","/worker")
        self.assertEqual(code,503)
        self.assertNotIn(SECRET.encode(),body)

if __name__=="__main__":
    unittest.main(verbosity=2)
