"""Vercel cron endpoint — runs the full publisher intel pipeline directly."""

from http.server import BaseHTTPRequestHandler
import json
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

from app.config import get_settings
from app.scheduler import run_daily_job


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        settings = get_settings()

        if not all([settings.slack_webhook_url, settings.gemini_api_key, settings.tavily_api_key]):
            self._respond(503, {"error": "Missing required API keys"})
            return

        try:
            result = run_daily_job(settings)
            self._respond(200, result)
        except Exception as e:
            logging.getLogger(__name__).exception("Cron job failed")
            self._respond(500, {"error": str(e)})

    def _respond(self, status: int, body: dict):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())
