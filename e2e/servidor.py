"""Serve o front e repassa /api/* para a API local (imita o nginx do deploy). Uso: python e2e/servidor.py"""
import http.server, urllib.request, urllib.error, sys, os
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend")
API = "http://127.0.0.1:8000"
class H(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k): super().__init__(*a, directory=ROOT, **k)
    def _proxy(self):
        n = int(self.headers.get("content-length") or 0)
        body = self.rfile.read(n) if n else None
        req = urllib.request.Request(API + self.path, data=body, method=self.command)
        for k in ("content-type", "authorization"):
            if self.headers.get(k): req.add_header(k, self.headers[k])
        try:
            r = urllib.request.urlopen(req, timeout=60); code, data, ct = r.status, r.read(), r.headers.get("content-type")
        except urllib.error.HTTPError as e:
            code, data, ct = e.code, e.read(), e.headers.get("content-type")
        self.send_response(code); self.send_header("content-type", ct or "application/json")
        self.send_header("content-length", str(len(data))); self.end_headers(); self.wfile.write(data)
    def do_GET(self):
        return self._proxy() if self.path.startswith("/api/") else super().do_GET()
    do_POST = do_PUT = do_DELETE = lambda self: self._proxy()
    def log_message(self, *a): pass
http.server.ThreadingHTTPServer(("127.0.0.1", 8080), H).serve_forever()
