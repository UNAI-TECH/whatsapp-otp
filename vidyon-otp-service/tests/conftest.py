import base64
import os
from datetime import datetime, timezone
from typing import Union
import pytest
import pytest_asyncio
import httpx
from fastapi.testclient import TestClient
from standardwebhooks import Webhook

# Set environment variables for tests before importing app config
TEST_SECRET_RAW = b"01234567890123456789012345678901"
TEST_SECRET = "whsec_" + base64.b64encode(TEST_SECRET_RAW).decode("utf-8")

os.environ["ENVIRONMENT"] = "development"
os.environ["PROVIDER"] = "mock"
os.environ["MOCK_MODE"] = "success"
os.environ["SEND_SMS_HOOK_SECRET"] = TEST_SECRET
os.environ["WHATSAPP_ACCESS_TOKEN"] = "test-whatsapp-token"
os.environ["WHATSAPP_PHONE_NUMBER_ID"] = "123456789012345"

from app.config import settings  # noqa: E402
from app.main import app  # noqa: E402
from app.webhook_verification import reset_replay_cache  # noqa: E402


@pytest.fixture(autouse=True)
def clean_environment():
    """Reset settings and replay cache before each test."""
    settings.send_sms_hook_secret = TEST_SECRET
    settings.provider = "mock"
    settings.mock_mode = "success"
    reset_replay_cache()
    yield
    reset_replay_cache()


@pytest.fixture
def test_webhook_secret() -> str:
    return TEST_SECRET


@pytest.fixture
def webhook_signer(test_webhook_secret):
    wh = Webhook(test_webhook_secret)

    def _sign(payload: str, msg_id: str, timestamp: Union[datetime, int, float]) -> dict:
        if isinstance(timestamp, (int, float)):
            dt = datetime.fromtimestamp(timestamp, timezone.utc)
            ts_str = str(int(timestamp))
        else:
            dt = timestamp
            ts_str = str(int(dt.timestamp()))

        signature = wh.sign(msg_id, dt, payload)
        return {
            "webhook-id": msg_id,
            "webhook-timestamp": ts_str,
            "webhook-signature": signature,
            "content-type": "application/json",
        }

    return _sign


@pytest.fixture
def client():
    return TestClient(app)


@pytest_asyncio.fixture
async def async_client():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
