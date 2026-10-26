import json
import time
from datetime import datetime, timezone
import pytest
from standardwebhooks import Webhook
from app.webhook_verification import verify_signature
from fastapi import HTTPException


class DummyRequest:
    def __init__(self, headers: dict, body_bytes: bytes):
        self.headers = headers
        self._body = body_bytes

    async def body(self) -> bytes:
        return self._body


@pytest.mark.asyncio
async def test_valid_signature_succeeds(webhook_signer):
    payload = json.dumps({"user": {"phone": "+919876543210"}, "sms": {"otp": "123456"}})
    headers = webhook_signer(payload, "msg_test_01", int(time.time()))
    req = DummyRequest(headers=headers, body_bytes=payload.encode("utf-8"))

    raw = await verify_signature(req)
    assert raw == payload.encode("utf-8")


@pytest.mark.asyncio
async def test_wrong_secret_fails(test_webhook_secret):
    wrong_wh = Webhook("whsec_d3Jvbmcgc2VjcmV0IHZhbHVlIGZvciB0ZXN0aW5nIQ==")
    payload = json.dumps({"test": "data"})
    now_dt = datetime.now(timezone.utc)
    sig = wrong_wh.sign("msg_test_02", now_dt, payload)
    headers = {
        "webhook-id": "msg_test_02",
        "webhook-timestamp": str(int(now_dt.timestamp())),
        "webhook-signature": sig,
    }
    req = DummyRequest(headers=headers, body_bytes=payload.encode("utf-8"))

    with pytest.raises(HTTPException) as exc_info:
        await verify_signature(req)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_tampered_body_fails(webhook_signer):
    original_payload = json.dumps({"otp": "123456"})
    headers = webhook_signer(original_payload, "msg_test_03", int(time.time()))
    tampered_bytes = json.dumps({"otp": "654321"}).encode("utf-8")
    req = DummyRequest(headers=headers, body_bytes=tampered_bytes)

    with pytest.raises(HTTPException) as exc_info:
        await verify_signature(req)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_missing_headers_fails():
    req = DummyRequest(headers={}, body_bytes=b"{}")
    with pytest.raises(HTTPException) as exc_info:
        await verify_signature(req)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_expired_timestamp_fails(webhook_signer):
    payload = json.dumps({"otp": "123456"})
    # Timestamp older than 5 minutes (300 seconds)
    expired_time = int(time.time()) - 400
    headers = webhook_signer(payload, "msg_test_04", expired_time)
    req = DummyRequest(headers=headers, body_bytes=payload.encode("utf-8"))

    with pytest.raises(HTTPException) as exc_info:
        await verify_signature(req)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_replayed_webhook_id_fails(webhook_signer):
    payload = json.dumps({"otp": "123456"})
    headers = webhook_signer(payload, "msg_replay_999", int(time.time()))
    req = DummyRequest(headers=headers, body_bytes=payload.encode("utf-8"))

    # First call succeeds
    raw = await verify_signature(req)
    assert raw == payload.encode("utf-8")

    # Second call with the same webhook-id fails with replay detection
    with pytest.raises(HTTPException) as exc_info:
        await verify_signature(req)
    assert exc_info.value.status_code == 401
    assert "replay" in exc_info.value.detail.lower()
