from __future__ import annotations
import contextlib,hashlib,hmac,http.client,json,secrets,ssl,time
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

GET_ALLOWED={"/","/worker","/planning","/applications","/connections","/api/worker","/api/planning","/api/v1/applications","/api/v1/connector-status"}
POST_ALLOWED={"/api/planning","/api/worker/storage","/api/worker/passphrase","/api/worker/link","/api/worker/stop-job","/api/worker/discord-join","/api/v1/applications/submit","/api/v1/pairings","/gateway/v1/pairings/redeem"}
MAX_REQUEST=1_000_000
MAX_RESPONSE=2_000_000

def create_server(config_path,port=19402):
    config_path=Path(config_path)
    port=int(port)
    origins={f"http://127.0.0.1:{port}",f"http://localhost:{port}"}
    def exchange(method,path,payload=b"",ctype=""):
        cfg=json.loads(config_path.read_text(encoding="utf-8-sig"))
        wid=str(cfg.get("worker_id") or "").strip()
        secret=str(cfg.get("shared_secret") or "").strip()
        if not wid or not secret:raise RuntimeError("Identite WORKER non encore disponible")
        public=str(cfg.get("controller_url") or "").rstrip("/")
        u=urlsplit(public)
        if u.scheme!="https" or not u.hostname:raise RuntimeError("Adresse du CONTROLLER non valide")
        pin=str(cfg.get("pinned_tls_sha256") or "").replace(":","").upper()
        if len(pin)!=64 or any(ch not in "0123456789ABCDEF" for ch in pin):
            raise RuntimeError("Empreinte TLS du CONTROLLER absente")
        conn=http.client.HTTPSConnection(u.hostname,u.port or 443,timeout=9,context=ssl._create_unverified_context())
        try:
            conn.connect()
            cert=conn.sock.getpeercert(binary_form=True)
            if not cert or not hmac.compare_digest(hashlib.sha256(cert).hexdigest().upper(),pin):
                raise RuntimeError("Empreinte TLS du CONTROLLER invalide")
            issued=str(int(time.time()))
            nonce=secrets.token_urlsafe(24).replace("=","")
            msg="\n".join(("CASSANDRE-WORKER-ASSERTION/1",wid,issued,nonce)).encode("utf-8")
            signature=hmac.new(secret.encode("utf-8"),msg,hashlib.sha256).hexdigest().upper()
            assertion="|".join((wid,issued,nonce,signature))
            target=u.path.rstrip("/")+(path if path.startswith("/") else "/"+path)
            headers={"User-Agent":"Cassandre-Worker-UI/1.1","Accept":"*/*","X-Cassandre-Worker-Assertion":assertion}
            if payload:headers["Content-Type"]=ctype or "application/json"
            conn.request(method,target,body=payload or None,headers=headers)
            response=conn.getresponse()
            raw=response.read(MAX_RESPONSE+1)
            if len(raw)>MAX_RESPONSE:raise RuntimeError("Reponse trop volumineuse")
            return response.status,raw,response.getheader("Content-Type") or "application/octet-stream"
        finally:
            with contextlib.suppress(Exception):conn.close()
    class Handler(BaseHTTPRequestHandler):
        server_version="CassandreWorkerLocalUI/1.1"
        def log_message(self,*args):return
        def send(self,status,body=b"",ctype="application/json; charset=utf-8"):
            self.send_response(int(status))
            for k,v in (("Cache-Control","no-store"),("X-Content-Type-Options","nosniff"),("Content-Security-Policy","default-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'"),("Content-Type",ctype),("Content-Length",str(len(body)))):
                self.send_header(k,v)
            self.end_headers()
            self.wfile.write(body)
        def local_only(self):
            host=str(self.headers.get("Host") or "").lower()
            return self.client_address[0]=="127.0.0.1" and host in {f"127.0.0.1:{port}",f"localhost:{port}"}
        def urlpath(self):return urlsplit(self.path).path.rstrip("/") or "/"
        def do_OPTIONS(self):self.send(403,b'{"Status":"FAILED"}')
        def do_GET(self):
            route=self.urlpath()
            if not self.local_only() or route not in GET_ALLOWED:
                self.send(404,b'{"Status":"FAILED"}');return
            try:
                code,body,ctype=exchange("GET",self.path)
                self.send(code,body,ctype)
            except Exception:
                self.send(503,b'{"Status":"FAILED","Error":"Connexion WORKER au CONTROLLER indisponible"}')
        def do_POST(self):
            route=self.urlpath()
            try:length=int(self.headers.get("Content-Length","0") or 0)
            except (ValueError,TypeError):self.send(400,b'{"Status":"FAILED"}');return
            if length<0 or length>MAX_REQUEST:self.send(413,b'{"Status":"FAILED"}');return
            origin=str(self.headers.get("Origin") or "").rstrip("/")
            referer=str(self.headers.get("Referer") or "")
            valid_origin=origin in origins or (not origin and any(referer==o or referer.startswith(o+"/") for o in origins))
            allowed=route in POST_ALLOWED or (route.startswith("/api/v1/applications/") and len(route.split("/"))==6)
            if not self.local_only() or not valid_origin or not allowed:
                if length:self.rfile.read(length)
                self.send(403,b'{"Status":"FAILED"}');return
            ctype=str(self.headers.get("Content-Type") or "")
            if not ctype.lower().startswith("application/json"):
                if length:self.rfile.read(length)
                self.send(415,b'{"Status":"FAILED"}');return
            body=self.rfile.read(length) if length else b"{}"
            try:
                code,raw,out_type=exchange("POST",self.path,body,ctype)
                self.send(code,raw,out_type)
            except Exception:
                self.send(503,b'{"Status":"FAILED","Error":"Connexion WORKER au CONTROLLER indisponible"}')
    class Server(ThreadingHTTPServer):
        daemon_threads=True
        allow_reuse_address=True
    return Server(("127.0.0.1",port),Handler)

def serve(config_path,port=19402):
    with create_server(config_path,port) as server:
        server.serve_forever(poll_interval=0.5)
