"""Fictional webhook receiver for the guide's fifth-round pictures. Listens on 127.0.0.1:8099 /events,
reads and discards POST bodies, answers 200 while /state/mode holds 'accept', else 503. Logs nothing."""
from http.server import BaseHTTPRequestHandler, HTTPServer


class H(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != '/events':
            self.send_response(404); self.end_headers(); return
        n = int(self.headers.get('Content-Length') or 0)
        if n:
            self.rfile.read(n)
        try:
            mode = open('/state/mode').read().strip()
        except OSError:
            mode = 'accept'
        ok = mode == 'accept'
        body = b'{"guide":"accepted"}' if ok else b'{"guide":"receiver temporarily unavailable"}'
        self.send_response(200 if ok else 503)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


HTTPServer(('127.0.0.1', 8099), H).serve_forever()
