from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv


def compute_signature(channel_secret: str, body: bytes) -> str:
    mac = hmac.new(channel_secret.encode(), body, hashlib.sha256)
    return base64.b64encode(mac.digest()).decode()


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    load_dotenv(project_root / ".env", override=False)

    webhook_url = os.getenv("LINE_WEBHOOK_URL", "http://localhost:8000/webhooks/line")
    channel_secret = os.getenv("LINE_CHANNEL_SECRET")
    signature_enabled = bool(channel_secret)

    payload = {
        "events": [
            {
                "type": "message",
                "replyToken": "dev-test-token",
                "message": {"id": "m-local", "type": "text", "text": "ping from tool"},
                "source": {"type": "user", "userId": "local-user"},
            }
        ]
    }
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
    headers = {"content-type": "application/json"}
    if signature_enabled:
        headers["X-Line-Signature"] = compute_signature(channel_secret, body)

    print(f"POST {webhook_url}")
    print(f"Signature attached: {signature_enabled}")

    response = httpx.post(webhook_url, content=body, headers=headers, timeout=10.0)

    print(f"Status: {response.status_code}")
    try:
        print(f"Body: {response.json()}")
    except Exception:
        print(f"Raw body: {response.text}")


if __name__ == "__main__":
    main()
