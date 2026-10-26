# 02 — Supabase Project A Setup (Production ERP)

**Scope:** Supabase Project A holds the live production database and authentication for My Vidyon ERP. **No DDL or schema alterations are applied to Project A.**

---

## 1. Webhook Configuration Steps

1. Log in to the [Supabase Dashboard](https://supabase.com/dashboard).
2. Select **Project A**.
3. Navigate to **Authentication** → **Hooks**.
4. Locate the **Send SMS Hook** section.
5. Configure the hook:
   - **Type:** HTTP POST
   - **URL:** `https://vidyon-otp-service.onrender.com/hooks/send-message`
   - **Timeout:** 5000 ms (default)
6. Copy the generated **Secret Key** (`v1,whsec_...`).
7. Paste this secret into Render as the environment variable `SEND_SMS_HOOK_SECRET`.

---

## 2. Inbound Webhook Payload Format

Supabase Auth dispatches the following JSON payload:
```json
{
  "user": {
    "id": "uuid-here",
    "phone": "+919876543210"
  },
  "sms": {
    "otp": "123456"
  }
}
```

The Python service returns `200 {}` on successful handover to WhatsApp Cloud API.
