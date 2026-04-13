"""Schedule info endpoint — shows today's publisher rotation."""

from http.server import BaseHTTPRequestHandler
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.scheduler import get_todays_publishers


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
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
