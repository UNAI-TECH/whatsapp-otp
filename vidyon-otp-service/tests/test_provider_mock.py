import pytest
from app.config import settings
import app.providers.mock as mock_provider
from app.providers.base import (
    ProviderResult,
    ProviderRejected,
    ProviderTimeout,
    ProviderUnavailable,
)


@pytest.mark.asyncio
async def test_mock_success():
    settings.mock_mode = "success"
    result = await mock_provider.send_otp("+919876543210", "123456", "en")
    assert isinstance(result, ProviderResult)
    assert result.accepted is True
    assert result.provider_message_id is not None


@pytest.mark.asyncio
async def test_mock_reject():
    settings.mock_mode = "reject"
    with pytest.raises(ProviderRejected):
        await mock_provider.send_otp("+919876543210", "123456", "en")


@pytest.mark.asyncio
async def test_mock_timeout():
    settings.mock_mode = "timeout"
    with pytest.raises(ProviderTimeout):
        await mock_provider.send_otp("+919876543210", "123456", "en")


@pytest.mark.asyncio
async def test_mock_unavailable():
    settings.mock_mode = "unavailable"
    with pytest.raises(ProviderUnavailable):
        await mock_provider.send_otp("+919876543210", "123456", "en")
