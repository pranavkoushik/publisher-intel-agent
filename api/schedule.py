"""Schedule info endpoint — shows today's publisher rotation."""

from http.server import BaseHTTPRequestHandler
import json
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        from app.scheduler import get_todays_publishers

        label, publishers, coverage, next_label = get_todays_publishers()

        if publishers is None:
            body = {"today": "weekend", "publishers": [], "next": None}
        else:
            body = {
                "today": label,
                "publisher_count": len(publishers),
                "publishers": publishers,
                "coverage": coverage,
                "next": next_label,
            }

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())
