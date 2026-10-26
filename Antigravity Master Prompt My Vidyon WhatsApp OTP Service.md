# Antigravity Master Prompt: My Vidyon WhatsApp OTP Service

Prepared by Claude · October 24, 2026 · Project ID MYV-SMS-OTP · Replaces the SMS/DLT version of the specification

## How to use this document

1. Create an Antigravity workspace named vidyon-sms-service and start the agent in planning mode.
2. Copy everything between BEGIN PROMPT and END PROMPT into the agent.
3. Attach the companion document, Supabase SQL and Configuration Reference, as reference material.
4. Never paste real secrets into the agent chat. The agent only creates .env.example placeholders. You set real values yourself in Render and Supabase.
5. The prompt has approval gates (G0 to G8). The agent must stop at each gate and wait for your written approval.

Decisions you still owe the agent. If they are missing, the agent logs them in OPEN\_QUESTIONS.md and continues with the parts that do not depend on them:

- Phone-number model for shared parent numbers: (a) parent accounts only, (b) own number per student, or (c) admin-assisted student resets.
- Whether a staging Supabase project exists. Suggested: use Project B as staging, with test users only.
- Meta business verification status, sending number and template names.

## BEGIN PROMPT

### 1. Role and mission

You are a senior backend engineer, security reviewer and technical writer. Build a reusable WhatsApp OTP delivery service for the My Vidyon school ERP, together with the full documentation package, tests and deployment files.

Supabase Auth generates and verifies every OTP. Your Python service only receives Supabase’s Send SMS Auth Hook request and delivers the supplied OTP through the official WhatsApp Cloud API. You never generate, store or verify an OTP, and you never issue sessions.

### 2. Context

- ERP: My Vidyon, React with Expo (Android) and Electron (Windows). Users are students and parents of schools in Tamil Nadu, India. Initial scale is about 2,000 students and about 1,000 parent phone numbers, roughly two students per parent.
- Project A: the existing production Supabase project and the only authentication authority. Treat it as read-only. Do not connect to it.
- Project B: optional. Its intended use is a staging Auth project containing test users only, never production data.
- Hosting: a Render web service in the Singapore region, because Render has no India region. The free plan is for development only, because free services sleep and the hook allows only about 5 seconds. Production needs an always-on plan.
- Delivery: the official WhatsApp Business Platform Cloud API, called directly. No DLT, no Business Solution Provider, and no unofficial WhatsApp libraries or WhatsApp Web automation.
- The earlier specification used SMS and DLT. Replace all SMS-gateway and DLT content with the WhatsApp equivalents. Keep the ten-document structure, and rename document 05 to WHATSAPP\_PROVIDER\_CONFIGURATION.md.

### 3. Facts already verified

Treat these as true, and re-check them against the official docs before any deployment.

- The Send SMS hook is available on Free and Pro plans. The payload has a user object and an sms object, and sms.otp holds the code. An empty response with status 200 means success.
- A hook error is a JSON object named error, with http\_code (default 500 if absent) and a required message.
- HTTP hooks should complete within about 5 seconds. Postgres hooks get about 2 seconds.
- Default Auth limits: 30 SMS per hour per project, a 60 second resend window per user, 30 verification requests per 5 minutes per IP, and 30 sign-in or OTP requests per 5 minutes per IP. These are adjustable under Authentication, Rate Limits.
- The Before User Created hook is available on Free and Pro. Its payload has metadata and user. It returns an empty object to allow, or an error object to reject.
- WhatsApp authentication templates have a fixed body (“{{1}} is your verification code.”), an optional security line, an optional expiry line of 1 to 90 minutes, and exactly one OTP button. The code is passed in both the body parameter and the button parameter. Messages go to the user’s primary device only. Creating these templates requires a verified Meta Business Portfolio.
- India authentication messages cost about ₹0.115 per delivered message. The authentication-international rate is about ₹2.50, so only +91 numbers are allowed.

### 4. Facts you must verify before coding

Do not guess. Fetch the official documentation and record the exact finding, the source URL and the date in docs/04 and docs/05.

1. The Standard Webhooks headers Supabase sends and the secret format shown in the dashboard. Believed: webhook-id, webhook-timestamp and webhook-signature, with a secret of the form v1,whsec\_ followed by base64. Also confirm how the standardwebhooks Python library expects the secret to be passed.
2. How an HTTP hook must return an error: which HTTP status and which body.
3. Whether user.phone in the payload carries a leading plus sign.
4. The exact Cloud API request for sending an authentication template, including the button component’s sub\_type and index (Meta’s own example and third-party wrappers appear to differ), and the current Graph API version.
5. Template language codes for English and Tamil, and how a language is chosen per message.
6. The Supabase OTP expiry and OTP length settings, and the Management API key names for them.

If you cannot verify something, write the assumption in OPEN\_QUESTIONS.md, mark it UNVERIFIED in the docs, and make it configurable.

### 5. Hard rules

1. No production access. Never connect to Project A, never use a service-role key, and never modify production authentication settings.
2. No secrets in chat, source code, logs, docs or frontend variables. Use placeholders only.
3. Never log OTP values, passwords, tokens, raw webhook bodies, signature headers, message bodies or provider credentials. Log phone numbers only masked to the last four digits.
4. Do not create a second OTP, an OTP table, a user table, or a duplicate Auth user anywhere.
5. Do not invent payload fields, header names or API parameters. Verify them or mark them UNVERIFIED.
6. Never fabricate test results. Any test that has not run is marked NOT RUN, with the reason.
7. Use only the official WhatsApp Cloud API.
8. Do not change unrelated ERP screens or behaviour.
9. Stop at every gate (G0 to G8) and wait for written approval.
10. Prefer a small set of pinned dependencies. Explain each dependency you add.
11. Anything you cannot decide goes into OPEN\_QUESTIONS.md, not into a guess.

### 6. Service requirements

Stack: Python 3.12, FastAPI, uvicorn, pydantic v2 with pydantic-settings, httpx (async), the standardwebhooks library, pytest with pytest-asyncio and respx, and ruff. Pin versions in requirements.txt.

**Endpoints**

- POST /hooks/send-message receives the Auth Hook request. Every other method returns 405.
- GET /health returns only {“status”: “ok”}. It does not call Meta or Supabase and exposes no configuration.
- Disable the interactive API docs and OpenAPI routes when ENVIRONMENT is production.
- Reject request bodies over 16 KB.

**Request handling order**

1. Read the raw body bytes before any JSON parsing.
2. Verify the signature and timestamp with the standardwebhooks library, using the raw body and the headers. On failure return 401 with a generic body and log only a reason code.
3. Parse the payload with pydantic and reject malformed input with 400.
4. Normalise the phone number and require the +91 pattern for a mobile number (6 to 9 as the first digit, then nine digits). Reject anything else with a hook error.
5. Validate that the OTP is digits only, with a length from 4 to 10.
6. Call the provider with a total time budget of 4 seconds, wrapped in an asyncio timeout.
7. On success return 200 with an empty JSON object. On failure return the hook error object with a generic message and the verified status code. Never return provider details, and never return success when the provider rejected or timed out.

**Replay protection**

- Rely on the library’s timestamp tolerance.
- Add a best-effort in-memory cache of recent webhook-id values with a short time-to-live. Document that it does not survive restarts and does not span multiple instances.

**Provider interface**

- In providers/base.py define send\_otp(phone\_e164, otp, language) returning a ProviderResult with an accepted flag and a provider message id.
- Define exceptions ProviderRejected, ProviderTimeout, ProviderUnavailable and ProviderConfigError.
- The mock provider supports modes success, reject, timeout and error through configuration, so every failure path can be tested.
- The whatsapp\_cloud provider calls the Graph API messages endpoint for the configured phone number ID with a bearer token. It sends a template message with the body and button parameters, using the shapes you verified in step 4.
- Use a connect timeout of about 1 second and a read timeout of about 2.5 seconds. Send exactly once and do not retry automatically, because a retry could deliver two codes.
- Treat the message as accepted only when Meta returns a 2xx response with a message id. Map Meta error codes to the exceptions above, and log only the Meta error code and the message id.

**Defence in depth**

- An optional in-memory per-phone limiter (configurable, default five per ten minutes) that logs a hash of the phone number, never the number. Supabase limits remain the primary control.
- Structured JSON logging with a request id and a redaction filter. Add a test that captures logs and asserts that no OTP, no full phone number and no signature header appears.

**Configuration (environment variables, placeholders only in .env.example)**

ENVIRONMENT, LOG\_LEVEL, PROVIDER (mock or whatsapp\_cloud), SEND\_SMS\_HOOK\_SECRET, PROVIDER\_TIMEOUT\_SECONDS, ALLOWED\_COUNTRY\_PREFIX (default +91), WHATSAPP\_ACCESS\_TOKEN, WHATSAPP\_PHONE\_NUMBER\_ID, WHATSAPP\_GRAPH\_API\_VERSION, WHATSAPP\_TEMPLATE\_NAME\_EN, WHATSAPP\_TEMPLATE\_NAME\_TA, WHATSAPP\_TEMPLATE\_LANGUAGE\_EN, WHATSAPP\_TEMPLATE\_LANGUAGE\_TA, PER\_PHONE\_LIMIT\_ENABLED.

Do not add any Supabase service-role key or database URL to this service.

### 7. Repository structure

```
vidyon-sms-service/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── schemas.py
│   ├── phone.py
│   ├── webhook_verification.py
│   ├── logging_utils.py
│   ├── health.py
│   └── providers/
│       ├── __init__.py
│       ├── base.py
│       ├── mock.py
│       └── whatsapp_cloud.py
├── tests/
│   ├── test_webhook_verification.py
│   ├── test_phone.py
│   ├── test_provider_mock.py
│   ├── test_provider_whatsapp_cloud.py
│   ├── test_send_message.py
│   └── test_logging_redaction.py
├── docs/   (the ten documents, plus OPEN_QUESTIONS.md and CHANGE_IMPACT_REPORT.md)
├── .github/workflows/ci.yml
├── render.yaml
├── Dockerfile
├── .dockerignore
├── .env.example
├── .gitignore
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

### 8. Tests you must write and actually run

- Webhook verification: valid signature, wrong secret, tampered body, missing headers, expired timestamp, future timestamp, replayed webhook-id.
- Payload: malformed JSON, missing fields, non-digit OTP, wrong length, empty phone.
- Phone: valid +91 mobile, non-India number, landline-like number, number without plus, number with spaces.
- Provider (mocked HTTP): accepted, Meta rejection, template not approved, invalid token, rate limited by Meta, timeout, network error, and no automatic retry.
- Endpoint: success returns an empty 200, provider failure never returns success, total time stays under the budget, and a wrong method returns 405.
- Logging: no OTP, full phone, signature header or raw body in any captured log line.
- Report exact commands and real outputs. Anything needing live Meta, Render or Supabase access is NOT RUN until the owner runs it.

### 9. Documentation (create under docs/)

Write the ten documents with the content listed in the original specification, adjusted for WhatsApp:

- 01 SYSTEM\_ARCHITECTURE, 02 SUPABASE\_PROJECT\_A\_SETUP, 03 PROJECT\_B\_CONFIGURATION, 04 PYTHON\_SMS\_SERVICE (rename to PYTHON\_OTP\_SERVICE), 05 WHATSAPP\_PROVIDER\_CONFIGURATION, 06 RENDER\_DEPLOYMENT, 07 ERP\_FRONTEND\_INTEGRATION, 08 SECURITY\_AND\_THREAT\_MODEL, 09 TEST\_PLAN\_AND\_TEST\_REPORT, 10 PRODUCTION\_DEPLOYMENT\_AND\_ROLLBACK.
- Document 02 must reference the Supabase SQL and Configuration Reference and state clearly that Supabase Auth’s own tables update normally during OTP use, while no ERP table in the public schema is modified.
- Document 03 records Project B as optional and as the staging project, with no production data and no duplicate users.
- Document 05 covers Meta business verification, the WhatsApp Business Account, the sending number, template creation and approval, English and Tamil templates, expiry text matching the Supabase OTP expiry, +91 enforcement and cost, token rotation, quality rating and messaging limits, and troubleshooting.
- Document 06 must explain the free plan sleep problem, the Singapore region, an always-on production plan, health checks, environment separation and rollback.
- Document 08 must cover the known risks: the hook affects the whole project, the phone-OTP session is a full session, the global SMS quota can be exhausted by an attacker, shared school IP addresses share rate limits, and account enumeration is only partly preventable.
- Document 09 contains real results only.

### 10. Phases and gates

- **Phase 0, Discovery (G0, G1).** Read the ERP authentication code and the Supabase configuration plan. Run only the read-only queries from the SQL reference when the owner supplies the results. Produce CHANGE\_IMPACT\_REPORT.md. Stop for approval.
- **Phase 1, Service and mock (G2).** Scaffold the repository, implement the service and mock provider, write the tests, run them, and report real results.
- **Phase 2, Local integration.** Send signed test requests to the running service and exercise every failure path.
- **Phase 3, WhatsApp adapter (G3).** Implement the Cloud API adapter against mocked HTTP. The owner then runs one live test with their own test number and credentials set outside the chat.
- **Phase 4, Render development deploy (G4).** Provide render.yaml and the Docker setup. The owner creates the private GitHub repository and the Render service.
- **Phase 5, Supabase staging (G5).** The owner configures the hook in the staging project only. Verify real delivery and Auth behaviour.
- **Phase 6, ERP frontend (G6).** Follow section 11. Deliver as a reviewable change, not a silent edit.
- **Phase 7, Regression and security tests (G7).** Expiry, wrong codes, resend limits, replay, account isolation, session handling and password change on Android and Windows.
- **Phase 8, Production (G8).** Only after the written words APPROVED FOR PRODUCTION, a staging acceptance record and a reviewed rollback plan.

### 11. ERP frontend requirements

- Reuse the existing Project A Supabase client. Do not create a second client or a second Auth flow.
- Call signInWithOtp with the phone number and shouldCreateUser set to false. Do not pass a channel option unless verification shows it is needed for the hook.
- Always show the same generic message after a request, whether or not the account exists.
- Validate the +91 format before sending. Enforce a 60 second resend cooldown that survives screen changes and app restarts.
- Verify the code with verifyOtp using the phone, the token and type sms.
- After verification, confirm that the session’s user matches the intended account and phone. If it does not, sign out and show an error.
- Update the password with the existing Supabase Auth call, apply the existing password policy, then sign the user out and return to the login screen.
- Handle network loss, app restart in the middle of the flow, and expired or wrong codes with clear messages.
- Provide English and Tamil text, accessible labels, keyboard and screen-reader support, and responsive layouts for Android and the Electron window.
- Hide the Forgot Password entry behind a feature flag until the owner enables it.
- Do not change the existing login, roles or any unrelated screen.
- The chosen shared-number model (a, b or c) decides who sees this flow. Until the owner decides, build nothing beyond the design in OPEN\_QUESTIONS.md.

### 12. Acceptance criteria

- OTP generation and verification stay in Project A.
- The service accepts only validly signed hook requests.
- Provider failures never produce a success response.
- No OTP, credential or full phone number appears in any log.
- Unknown or ineligible accounts cannot create users through the reset flow.
- A verified OTP cannot reset a different account.
- Existing ERP login, roles and data are unaffected.
- Android and Windows tests pass, or are clearly marked NOT RUN.
- Every failure and unexecuted test is documented, and the rollback plan has been reviewed.

### 13. Final report format

End with exactly these seven sections: 1. Documents created. 2. Files implemented. 3. Tests actually executed and their real results. 4. Configuration still required from the owner. 5. Deployment status. 6. Known risks and unresolved issues. 7. Exact next steps before production release.

## END PROMPT

## Notes for the project owner

- Start Meta business verification now. It is the longest wait and replaces what DLT would have been.
- You, not the agent, create the GitHub repository, the Render service, the Meta app and the Supabase settings. The agent prepares files and instructions.
- Free Render is fine for steps up to staging tests, but a first request after sleep will exceed the hook’s time limit. Use an always-on plan for production.
- If the agent proposes anything that touches Project A directly, reject it and point it back to hard rule 1.
