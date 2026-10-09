"""Local preview server.

The page fetches its data over HTTP, so opening index.html straight from disk
will not work — browsers block those requests. Run this instead:

    python3 tools/serve.py        # then open http://127.0.0.1:8777
"""
import os, sys, http.server, socketserver

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "public")
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8777
os.chdir(ROOT)

socketserver.TCPServer.allow_reuse_address = True
with socketserver.TCPServer(("127.0.0.1", PORT), http.server.SimpleHTTPRequestHandler) as httpd:
    print(f"serving {ROOT}\n  http://127.0.0.1:{PORT}", flush=True)
    httpd.serve_forever()
