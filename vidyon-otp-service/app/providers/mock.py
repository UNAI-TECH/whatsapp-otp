import asyncio
from app.config import settings
from app.providers.base import (
    ProviderResult,
    ProviderRejected,
    ProviderTimeout,
    ProviderUnavailable,
)


async def send_otp(phone_e164: str, otp: str, language: str) -> ProviderResult:
    """Mock OTP provider supporting configurable success and error simulation modes."""
    mode = getattr(settings, "mock_mode", "success")
    if mode == "success":
        return ProviderResult(accepted=True, provider_message_id="mock-msg-id-001")
    if mode == "reject":
        raise ProviderRejected("Mock rejection")
    if mode == "timeout":
        # Sleep slightly if needed or immediately raise ProviderTimeout for deterministic tests
        await asyncio.sleep(0.01)
        raise ProviderTimeout("Mock timeout")
    raise ProviderUnavailable("Mock unavailable")
