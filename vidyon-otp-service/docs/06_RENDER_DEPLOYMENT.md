# 06 — Render Deployment Guide

The service is configured to run in Render's **Singapore (`singapore`)** region for lowest latency to India.

---

## 1. Blueprint Deployment (`render.yaml`)

1. Connect your GitHub repository to [Render](https://render.com).
2. Create a **New Blueprint Instance** and select the repository.
3. Render automatically reads `render.yaml` and initializes the `vidyon-otp-service` web service.
4. Set the secret environment variables in the Render Dashboard:
   - `SEND_SMS_HOOK_SECRET`: Secret from Supabase Project A Send SMS hook.
   - `WHATSAPP_ACCESS_TOKEN`: Meta System User access token.
   - `WHATSAPP_PHONE_NUMBER_ID`: Meta phone number ID.
   - `OTP_PLATFORM_API_KEY`: API key generated from `issue_api_key()` in Project C.

---

## 2. Plan Recommendation

- **Development / Staging:** `free` plan is suitable for initial integration testing.
- **Production:** Upgrade to the **Starter** plan (~$7/mo). The `free` tier spins down after 15 minutes of inactivity; waking up takes 30-50 seconds, which will cause Supabase Auth's 5.0-second hook to time out.
