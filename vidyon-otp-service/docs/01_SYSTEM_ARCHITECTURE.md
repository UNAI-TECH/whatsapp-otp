# 01 — System Architecture

**Project:** My Vidyon WhatsApp OTP (`MYV-SMS-OTP`)

---

## 1. High-Level Architecture

The system coordinates between three primary tiers:
1. **Supabase Project A (Production ERP Auth)**: Manages users and triggers the `send-message` webhook on password reset.
2. **Python OTP Service (Render, Singapore)**: Receives webhooks, verifies signatures, and dispatches OTPs via WhatsApp Cloud API.
3. **Supabase Project C (Dedicated OTP Platform Engine)**: Houses the central OTP token generator, verifier, rate limiter, and audit logger with strict RLS and SHA-256 salted hashes.

```
┌─────────────────────────────────────────────────────────────┐
│                 SUPABASE PROJECT C (Platform)               │
│                                                             │
│   master_otp_schema.sql applied                             │
│   ├── Edge Function: /otp-generate                          │
│   └── Edge Function: /otp-verify                            │
└──────────────────────────────┬──────────────────────────────┘
                               │ X-OTP-API-Key
                               ▼
┌─────────────────────────────────────────────────────────────┐
│         PYTHON SERVICE (Render - Singapore Region)          │
│                                                             │
│   POST /hooks/send-message ◄── Supabase Auth (Project A)    │
│   GET  /health                                              │
│                                                             │
│   1. StandardWebhooks signature verification                │
│   2. +91 Indian mobile normalisation & validation           │
│   3. Meta WhatsApp Cloud API template delivery              │
│   4. PII redaction and structured JSON logging              │
└──────────────────────────────┬──────────────────────────────┘
                               │ WhatsApp Message
                               ▼
┌─────────────────────────────────────────────────────────────┐
│        ERP FRONTEND (React/Expo Android + Electron Win)     │
│                                                             │
│   Forgot Password flow (behind ENABLE_FORGOT_PASSWORD)      │
│   ├── PhoneInputScreen  (Anti-enumeration response)         │
│   ├── OtpInputScreen    (6-cell auto-advance, cooldown)     │
│   └── NewPasswordScreen (Password policy + signout)         │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Core Security Invariants

- **No Plaintext OTPs**: OTPs are never stored in plaintext anywhere. Only SHA-256(otp + salt) is kept in the database.
- **Zero Production Database Coupling**: The Python service never connects directly to Project A database (`DATABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are prohibited).
- **Masked PII**: Full phone numbers and OTP digits are filtered and masked from all application log output (`****3210`).
- **Strict Network Timeouts**: 4.0-second total provider timeout prevents exceeding Supabase Auth's 5.0-second webhook ceiling.
