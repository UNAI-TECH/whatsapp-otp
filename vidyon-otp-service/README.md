# Vidyon WhatsApp OTP Service

[![Tests](https://img.shields.io/badge/tests-33%20passed-brightgreen.svg)](#testing)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.5-009688.svg)](https://fastapi.tiangolo.com/)
[![Pydantic](https://img.shields.io/badge/pydantic-2.10.6-E92063.svg)](https://docs.pydantic.dev/)

Dedicated microservice for authenticating, formatting, and dispatching WhatsApp OTP messages triggered by Supabase Auth Send SMS hooks for My Vidyon ERP (`MYV-SMS-OTP`).

---

## Architecture Overview

- **Supabase Project A:** Existing production ERP database & Supabase Auth. Triggers Send SMS hook on password recovery.
- **Python Service (this repo):** Hosted on Render (Singapore). Validates webhooks, normalises +91 phone numbers, logs securely with PII redaction, and delivers messages via WhatsApp Cloud API.
- **Supabase Project C:** Dedicated multi-tenant OTP Platform. Houses `master_otp_schema.sql` and Edge Functions `otp-generate` / `otp-verify`.

---

## Directory Layout

```
vidyon-otp-service/
├── app/
│   ├── main.py                  # FastAPI application factory & endpoint routing
│   ├── config.py                # Environment configuration via pydantic-settings
│   ├── schemas.py               # Pydantic v2 models for Supabase Auth payloads
│   ├── phone.py                 # E.164 +91 normalisation, validation & masking
│   ├── webhook_verification.py  # standardwebhooks HMAC verification & replay cache
│   ├── logging_utils.py         # JSON formatter with automated PII & secret redaction
│   ├── health.py                # Health check endpoint
│   └── providers/
│       ├── base.py              # ProviderResult and exception hierarchy
│       ├── mock.py              # Mock delivery adapter (success/reject/timeout/error)
│       └── whatsapp_cloud.py    # Meta Graph API adapter
├── tests/                       # 33 comprehensive automated tests
├── supabase/
│   ├── master_otp_schema.sql    # Standalone master SQL for Project C
│   └── functions/
│       ├── otp-generate/index.ts
│       └── otp-verify/index.ts
├── docs/                        # Complete 10-part documentation suite
├── Dockerfile                   # Python 3.12-slim production container
├── render.yaml                  # Render deployment blueprint (Singapore region)
├── requirements.txt             # Pinned production dependencies
└── requirements-dev.txt         # Testing and development dependencies
```

---

## Getting Started

### 1. Local Setup

```bash
# Clone and navigate to service
cd vidyon-otp-service

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate       # On Linux/macOS
.\.venv\Scripts\activate        # On Windows

# Install dependencies
pip install -r requirements.txt -r requirements-dev.txt

# Copy environment variables
cp .env.example .env
```

### 2. Running Locally

```bash
uvicorn app.main:app --reload --port 8000
```

Check health:
```bash
curl http://localhost:8000/health
# {"status":"ok","environment":"development","provider":"mock"}
```

### 3. Testing

Run the automated test suite:
```bash
pytest -v tests
# 33 passed in 3.10s
```

Run linter:
```bash
ruff check app tests
# All checks passed!
```
