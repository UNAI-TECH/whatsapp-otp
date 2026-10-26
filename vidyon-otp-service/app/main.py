import json
import logging
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from app.config import settings
from app.schemas import HookPayload
from app.phone import validate_india_mobile, mask
from app.webhook_verification import verify_signature
from app.logging_utils import configure_logging
from app.health import router as health_router
from app.providers.base import (
    ProviderRejected,
    ProviderTimeout,
    ProviderUnavailable,
    ProviderConfigError,
)
import app.providers.mock as mock_provider
import app.providers.whatsapp_cloud as whatsapp_provider

configure_logging(settings.log_level)
log = logging.getLogger(__name__)

MAX_BODY_BYTES = 16_384


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("startup environment=%s provider=%s", settings.environment, settings.provider)
    yield


app = FastAPI(
    title="Vidyon OTP Service",
    version="1.0.0",
    docs_url=None if settings.environment == "production" else "/docs",
    openapi_url=None if settings.environment == "production" else "/openapi.json",
    lifespan=lifespan,
)

app.include_router(health_router)


@app.api_route("/hooks/send-message", methods=["POST"])
async def send_message(request: Request):
    request_id = str(uuid.uuid4())
    log.info("hook_received request_id=%s", request_id)

    # 1. Body size guard
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_BODY_BYTES:
        return JSONResponse(
            status_code=413,
            content={"error": {"http_code": 413, "message": "Request too large"}},
        )

    # 2. Signature verification
    try:
        raw = await verify_signature(request)
    except Exception:
        return JSONResponse(
            status_code=401,
            content={"error": {"http_code": 401, "message": "Unauthorised"}},
        )

    # 3. Payload size check on actual bytes
    if len(raw) > MAX_BODY_BYTES:
        return JSONResponse(
            status_code=413,
            content={"error": {"http_code": 413, "message": "Request too large"}},
        )

    # 4. Parse payload
    try:
        data = json.loads(raw.decode("utf-8"))
        payload = HookPayload.model_validate(data)
    except Exception:
        return JSONResponse(
            status_code=400,
            content={"error": {"http_code": 400, "message": "Bad request"}},
        )

    # 5. Phone validation
    try:
        phone = validate_india_mobile(payload.user.phone)
    except ValueError as exc:
        log.warning("phone_rejected request_id=%s reason=%s", request_id, str(exc))
        return JSONResponse(
            status_code=400,
            content={"error": {"http_code": 400, "message": "Invalid phone number"}},
        )

    # 6. OTP format validation
    otp = payload.sms.otp
    if not otp.isdigit() or not (4 <= len(otp) <= 10):
        return JSONResponse(
            status_code=400,
            content={"error": {"http_code": 400, "message": "Invalid OTP format"}},
        )

    log.info("delivering request_id=%s phone=%s", request_id, mask(phone))

    # 7. Deliver via selected provider
    provider = whatsapp_provider if settings.provider == "whatsapp_cloud" else mock_provider
    try:
        await provider.send_otp(phone, otp, "en")
        return Response(content="{}", media_type="application/json", status_code=200)
    except (ProviderRejected, ProviderConfigError) as exc:
        log.error("provider_rejected request_id=%s error=%s", request_id, str(exc))
        return JSONResponse(
            status_code=400,
            content={"error": {"http_code": 400, "message": "Delivery failed"}},
        )
    except ProviderTimeout:
        log.error("provider_timeout request_id=%s", request_id)
        return JSONResponse(
            status_code=504,
            content={"error": {"http_code": 504, "message": "Delivery timeout"}},
        )
    except ProviderUnavailable:
        log.error("provider_unavailable request_id=%s", request_id)
        return JSONResponse(
            status_code=502,
            content={"error": {"http_code": 502, "message": "Provider unavailable"}},
        )


@app.api_route("/hooks/send-message", methods=["GET", "PUT", "DELETE", "PATCH"])
async def send_message_wrong_method():
    return Response(status_code=405)
