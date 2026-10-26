import asyncio
import logging
from typing import Dict, Any
import httpx
from app.config import settings
from app.providers.base import (
    ProviderResult,
    ProviderRejected,
    ProviderTimeout,
    ProviderUnavailable,
    ProviderConfigError,
)

log = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.facebook.com"


def _build_payload(phone: str, otp: str, template: str, lang: str) -> Dict[str, Any]:
    return {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "template",
        "template": {
            "name": template,
            "language": {"code": lang},
            "components": [
                {"type": "body", "parameters": [{"type": "text", "text": otp}]},
                {
                    "type": "button",
                    # UNVERIFIED: Meta Cloud API authentication templates use "url" or "copy_code".
                    # Verify against Meta docs for your specific registered template before production.
                    "sub_type": "url",
                    "index": "0",
                    "parameters": [{"type": "text", "text": otp}],
                },
            ],
        },
    }


async def send_otp(phone_e164: str, otp: str, language: str = "en") -> ProviderResult:
    """Delivers OTP to WhatsApp Cloud API without automatic retry."""
    if not settings.whatsapp_access_token or settings.whatsapp_access_token == "PLACEHOLDER":
        raise ProviderConfigError("WHATSAPP_ACCESS_TOKEN not configured")
    if not settings.whatsapp_phone_number_id or settings.whatsapp_phone_number_id == "PLACEHOLDER":
        raise ProviderConfigError("WHATSAPP_PHONE_NUMBER_ID not configured")

    template = (
        settings.whatsapp_template_name_ta
        if language == "ta"
        else settings.whatsapp_template_name_en
    )
    lang_code = (
        settings.whatsapp_template_language_ta
        if language == "ta"
        else settings.whatsapp_template_language_en
    )

    url = (
        f"{GRAPH_BASE}/{settings.whatsapp_graph_api_version}"
        f"/{settings.whatsapp_phone_number_id}/messages"
    )

    try:
        async with asyncio.timeout(settings.provider_timeout_seconds):
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(connect=1.0, read=2.5, write=2.5, pool=1.0)
            ) as client:
                resp = await client.post(
                    url,
                    headers={"Authorization": f"Bearer {settings.whatsapp_access_token}"},
                    json=_build_payload(phone_e164, otp, template, lang_code),
                )

        if resp.status_code == 200:
            data = resp.json()
            messages = data.get("messages", [])
            msg_id = messages[0].get("id") if messages else None
            log.info("whatsapp_accepted message_id=%s", msg_id)
            return ProviderResult(accepted=True, provider_message_id=msg_id)

        try:
            error_data = resp.json().get("error", {})
            error_code = error_data.get("code")
            error_msg = error_data.get("message", "Unknown error")
        except Exception:
            error_code = None
            error_msg = resp.text

        log.warning("whatsapp_rejected status=%d error_code=%s", resp.status_code, error_code)

        if resp.status_code in (401, 403):
            raise ProviderRejected(f"Meta auth error code={error_code}: {error_msg}")
        if resp.status_code == 429:
            raise ProviderRejected(f"Meta rate limited code={error_code}: {error_msg}")
        raise ProviderUnavailable(f"Meta error status={resp.status_code} code={error_code}: {error_msg}")

    except (asyncio.TimeoutError, httpx.TimeoutException):
        raise ProviderTimeout("WhatsApp API timed out")
    except httpx.ConnectError as exc:
        raise ProviderUnavailable(f"Connection failed: {exc}")
