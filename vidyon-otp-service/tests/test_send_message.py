import json
import time
import pytest
from app.config import settings


@pytest.mark.asyncio
async def test_send_message_success(async_client, webhook_signer):
    payload = json.dumps({
        "user": {"phone": "+919876543210"},
        "sms": {"otp": "123456"}
    })
    headers = webhook_signer(payload, "msg_success_01", int(time.time()))

    resp = await async_client.post(
        "/hooks/send-message",
        content=payload,
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json() == {}


@pytest.mark.asyncio
async def test_send_message_provider_rejected(async_client, webhook_signer):
    settings.mock_mode = "reject"
    payload = json.dumps({
        "user": {"phone": "+919876543210"},
        "sms": {"otp": "123456"}
    })
    headers = webhook_signer(payload, "msg_reject_01", int(time.time()))

    resp = await async_client.post(
        "/hooks/send-message",
        content=payload,
        headers=headers,
    )
    assert resp.status_code == 400
    data = resp.json()
    assert data["error"]["http_code"] == 400
    assert data["error"]["message"] == "Delivery failed"


@pytest.mark.asyncio
async def test_send_message_provider_timeout(async_client, webhook_signer):
    settings.mock_mode = "timeout"
    payload = json.dumps({
        "user": {"phone": "+919876543210"},
        "sms": {"otp": "123456"}
    })
    headers = webhook_signer(payload, "msg_timeout_01", int(time.time()))

    resp = await async_client.post(
        "/hooks/send-message",
        content=payload,
        headers=headers,
    )
    assert resp.status_code == 504
    data = resp.json()
    assert data["error"]["http_code"] == 504
    assert data["error"]["message"] == "Delivery timeout"


@pytest.mark.asyncio
async def test_send_message_provider_unavailable(async_client, webhook_signer):
    settings.mock_mode = "unavailable"
    payload = json.dumps({
        "user": {"phone": "+919876543210"},
        "sms": {"otp": "123456"}
    })
    headers = webhook_signer(payload, "msg_unavail_01", int(time.time()))

    resp = await async_client.post(
        "/hooks/send-message",
        content=payload,
        headers=headers,
    )
    assert resp.status_code == 502
    data = resp.json()
    assert data["error"]["http_code"] == 502
    assert data["error"]["message"] == "Provider unavailable"


@pytest.mark.asyncio
async def test_wrong_http_method(async_client):
    for method in ["get", "put", "delete", "patch"]:
        caller = getattr(async_client, method)
        resp = await caller("/hooks/send-message")
        assert resp.status_code == 405


@pytest.mark.asyncio
async def test_payload_exceeding_16kb_rejected(async_client, webhook_signer):
    huge_data = {"user": {"phone": "+919876543210"}, "sms": {"otp": "123456"}, "padding": "x" * 20000}
    payload = json.dumps(huge_data)
    headers = webhook_signer(payload, "msg_huge_01", int(time.time()))

    resp = await async_client.post(
        "/hooks/send-message",
        content=payload,
        headers=headers,
    )
    assert resp.status_code == 413
    assert resp.json()["error"]["http_code"] == 413
