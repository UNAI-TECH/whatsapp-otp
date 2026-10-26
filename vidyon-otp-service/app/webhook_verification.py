import time
from typing import Dict
from standardwebhooks import Webhook
from fastapi import Request, HTTPException
from app.config import settings

# Replay protection cache: webhook_id -> timestamp (in-memory)
_REPLAY_CACHE: Dict[str, float] = {}
_REPLAY_TTL_SECONDS = 300.0


def _purge_expired_replay_ids(now: float) -> None:
    """Removes webhook IDs older than TTL from the in-memory cache."""
    expired = [wid for wid, ts in _REPLAY_CACHE.items() if (now - ts) > _REPLAY_TTL_SECONDS]
    for wid in expired:
        del _REPLAY_CACHE[wid]


def reset_replay_cache() -> None:
    """Helper for testing to clear replay state."""
    _REPLAY_CACHE.clear()


async def verify_signature(request: Request) -> bytes:
    """
    Read raw request body, verify standardwebhooks signature and check for replay attacks.
    Returns raw body bytes on success.
    Raises HTTP 401 on any failure.
    """
    now = time.time()
    _purge_expired_replay_ids(now)

    webhook_id = request.headers.get("webhook-id") or request.headers.get("x-webhook-id")
    if webhook_id and webhook_id in _REPLAY_CACHE:
        raise HTTPException(status_code=401, detail="Webhook replay detected")

    raw = await request.body()
    secret = settings.send_sms_hook_secret.strip()
    if secret.startswith("v1,"):
        secret = secret[3:]

    try:
        wh = Webhook(secret)
        wh.verify(raw, dict(request.headers))
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Webhook signature invalid: {exc}")

    if webhook_id:
        _REPLAY_CACHE[webhook_id] = now

    return raw
