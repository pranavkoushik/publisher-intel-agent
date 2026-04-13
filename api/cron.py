import os
import requests


RENDER_URL = os.environ.get("RENDER_URL", "")


def handler(request):
    if not RENDER_URL:
        return {"statusCode": 500, "body": "RENDER_URL not set"}

    try:
        resp = requests.post(f"{RENDER_URL}/run-job", timeout=120)
        return {
            "statusCode": resp.status_code,
            "body": resp.json(),
        }
    except Exception as e:
        return {"statusCode": 500, "body": str(e)}
