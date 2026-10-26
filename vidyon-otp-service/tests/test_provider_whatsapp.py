import pytest
import respx
import httpx
from app.config import settings
import app.providers.whatsapp_cloud as whatsapp_provider
from app.providers.base import (
    ProviderResult,
    ProviderRejected,
    ProviderTimeout,
    ProviderUnavailable,
)

GRAPH_URL = f"https://graph.facebook.com/v19.0/{settings.whatsapp_phone_number_id}/messages"


@pytest.mark.asyncio
@respx.mock
async def test_whatsapp_success():
    route = respx.post(GRAPH_URL).mock(
        return_value=httpx.Response(
            200,
            json={"messages": [{"id": "wamid.HBgLMTIzNDU2Nzg5MA=="}]},
        )
    )

    result = await whatsapp_provider.send_otp("+919876543210", "123456", "en")
    assert isinstance(result, ProviderResult)
    assert result.accepted is True
    assert result.provider_message_id == "wamid.HBgLMTIzNDU2Nzg5MA=="
    assert route.call_count == 1  # No double send


@pytest.mark.asyncio
@respx.mock
async def test_whatsapp_auth_error_401():
    route = respx.post(GRAPH_URL).mock(
        return_value=httpx.Response(
            401,
            json={"error": {"code": 190, "message": "Invalid OAuth access token."}},
        )
    )

    with pytest.raises(ProviderRejected) as exc:
        await whatsapp_provider.send_otp("+919876543210", "123456", "en")
    assert "code=190" in str(exc.value)
    assert route.call_count == 1


@pytest.mark.asyncio
@respx.mock
async def test_whatsapp_rate_limited_429():
    route = respx.post(GRAPH_URL).mock(
        return_value=httpx.Response(
            429,
            json={"error": {"code": 80007, "message": "Rate limit exceeded"}},
        )
    )

    with pytest.raises(ProviderRejected) as exc:
        await whatsapp_provider.send_otp("+919876543210", "123456", "en")
    assert "code=80007" in str(exc.value)
    assert route.call_count == 1


@pytest.mark.asyncio
@respx.mock
async def test_whatsapp_server_error_500():
    route = respx.post(GRAPH_URL).mock(
        return_value=httpx.Response(
            500,
            json={"error": {"code": 1, "message": "An unknown error occurred"}},
        )
    )

    with pytest.raises(ProviderUnavailable) as exc:
        await whatsapp_provider.send_otp("+919876543210", "123456", "en")
    assert "status=500" in str(exc.value)
    assert route.call_count == 1


@pytest.mark.asyncio
@respx.mock
async def test_whatsapp_connect_error():
    route = respx.post(GRAPH_URL).mock(side_effect=httpx.ConnectError("Connection refused"))

    with pytest.raises(ProviderUnavailable):
        await whatsapp_provider.send_otp("+919876543210", "123456", "en")
    assert route.call_count == 1


@pytest.mark.asyncio
@respx.mock
async def test_whatsapp_timeout():
    route = respx.post(GRAPH_URL).mock(side_effect=httpx.ReadTimeout("Timeout reached"))

    with pytest.raises(ProviderTimeout):
        await whatsapp_provider.send_otp("+919876543210", "123456", "en")
    assert route.call_count == 1
