# 04 — Python OTP Service

The Python service is built with **FastAPI**, **Pydantic v2**, and **httpx** running on Python 3.12 (in Docker).

---

## 1. Endpoints

- `GET /health`
  - Liveness check for Render.
  - Returns: `{"status": "ok", "environment": "...", "provider": "..."}`.

- `POST /hooks/send-message`
  - Handles the Supabase Auth Send SMS hook.
  - Verifies `standardwebhooks` HMAC signature.
  - Enforces in-memory replay attack protection (5-minute TTL).
  - Validates +91 phone numbers and OTP digit format.
  - Dispatches message via Meta WhatsApp Cloud API.
  - Returns `200 {}` on success.

---

## 2. Error Response Codes

| Status Code | Meaning | Reason |
|---|---|---|
| `400` | Bad Request / Delivery Failed | Invalid body, invalid phone (+91 required), or provider rejected |
| `401` | Unauthorized | Webhook signature invalid, expired timestamp, or replayed webhook ID |
| `405` | Method Not Allowed | Non-POST request to `/hooks/send-message` |
| `413` | Payload Too Large | Request body exceeds 16,384 bytes |
| `502` | Provider Unavailable | WhatsApp Cloud API returned 5xx or connection failed |
| `504` | Delivery Timeout | WhatsApp Cloud API did not respond within 4.0 seconds |
