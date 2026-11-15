"""Read-only loopback bridge for the HDT overlay plugin."""
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = 27183


class Bridge:
    def __init__(self, port=PORT):
        self.lock = threading.Lock()
        self.value = {'version':1,'active':False}
        self.last_seen = 0.
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                # Do not accept DNS-rebound hostnames, proxy requests, file
                # paths, commands, settings writes or raw log downloads.
                expected = f'127.0.0.1:{self.server.server_port}'
                if self.headers.get('Host')!=expected:
                    self.send_error(403)
                    return
                if self.path!='/state':
                    self.send_error(404)
                    return
                with owner.lock:
                    owner.last_seen = time.monotonic()
                    body = json.dumps(owner.value,ensure_ascii=False).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type','application/json; charset=utf-8')
                self.send_header('Cache-Control','no-store')
                self.send_header('Content-Length',str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self,*args):
                pass

        self.server = ThreadingHTTPServer(('127.0.0.1',port),Handler)
        self.server.daemon_threads = True
        self.thread = threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()

    def publish(self, value):
        with self.lock:
            self.value = value

    def close(self):
        self.server.shutdown()
        self.server.server_close()
