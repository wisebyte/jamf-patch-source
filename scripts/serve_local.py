#!/usr/bin/env python3
"""Local TEST server only: serves _site/ with application/json, and answers arbitrary
/software/<ids> orders dynamically so you can compare against the static files."""
import http.server, json, pathlib, sys
SITE = pathlib.Path(__file__).resolve().parent.parent / "_site"
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        p = self.path.split("?")[0].strip("/")
        f = SITE / p
        if p == "software": f = SITE / "software.html"
        if p.startswith("software/") and not f.is_file():
            allt = {t["id"]: t for t in json.loads((SITE / "software.html").read_text())}
            body = json.dumps([allt[i] for i in p[9:].split(",") if i in allt]).encode()
        elif f.is_file(): body = f.read_bytes()
        else: return self.send_error(404)
        self.send_response(200); self.send_header("Content-Type", "application/json")
        self.end_headers(); self.wfile.write(body)
        sys.stderr.write(f"GET /{p}\n")
http.server.ThreadingHTTPServer(("0.0.0.0", int(sys.argv[1]) if len(sys.argv) > 1 else 8000), H).serve_forever()
