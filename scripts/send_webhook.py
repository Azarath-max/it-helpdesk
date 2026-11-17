"""Send a signed demo ticket to the inbound webhook.

Usage:
    python scripts/send_webhook.py --url http://127.0.0.1:8000/api/webhooks/tickets
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import argparse
import hashlib
import hmac
import json
import time
import urllib.request
import uuid

from app.core.config import get_settings


def main() -> None:
    parser = argparse.ArgumentParser(description="Send a signed demo webhook.")
    parser.add_argument("--url", default="http://127.0.0.1:8000/api/webhooks/tickets")
    parser.add_argument("--secret", default=None)
    args = parser.parse_args()

    settings = get_settings()
    secret = args.secret or settings.webhook_secret
    payload = {
        "schemaVersion": 1,
        "source": "demo-script",
        "externalId": f"demo-{uuid.uuid4().hex[:8]}",
        "title": "Laptop will not boot",
        "description": "Pressed power, fan spins, no display.",
        "requester": {"email": "demo.requester@example.com", "name": "Demo Requester"},
        "priority": "HIGH",
        "category": "hardware",
        "metadata": {"demo": True},
    }
    raw = json.dumps(payload).encode("utf-8")
    timestamp = str(int(time.time()))
    signature = "sha256=" + hmac.new(
        secret.encode("utf-8"), f"{timestamp}.".encode("utf-8") + raw, hashlib.sha256
    ).hexdigest()

    request = urllib.request.Request(
        args.url,
        data=raw,
        headers={
            "Content-Type": "application/json",
            "X-Webhook-Id": f"demo-{uuid.uuid4().hex[:8]}",
            "X-Webhook-Timestamp": timestamp,
            "X-Webhook-Signature": signature,
            "X-Webhook-Schema-Version": "1",
        },
        method="POST",
    )
    with urllib.request.urlopen(request) as response:
        print(response.status, response.read().decode("utf-8"))


if __name__ == "__main__":
    main()
