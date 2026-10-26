# 10 — Production Deployment and Rollback Guide

**Gate G8 Checklist:** Requires explicit written phrase `"APPROVED FOR PRODUCTION"` before cutting live traffic.

---

## 1. Production Deployment Steps

1. **Supabase Project C (OTP Platform)**:
   - Run `master_otp_schema.sql` in the Supabase SQL editor.
   - Note the returned `my_vidyon_app_id` UUID.
   - Issue an API key using:
     ```sql
     SELECT public.issue_api_key(
       '<my_vidyon_app_id>'::UUID,
       'my_vidyon_production',
       TRUE, TRUE, FALSE, NULL
     );
     ```
   - Store the returned `api_key` securely as `OTP_PLATFORM_API_KEY`.
   - Deploy Edge Functions:
     ```bash
     supabase functions deploy otp-generate --project-ref <project-c-ref>
     supabase functions deploy otp-verify   --project-ref <project-c-ref>
     ```

2. **Render Service**:
   - Upgrade plan to **Starter** (always-on).
   - Set `PROVIDER=whatsapp_cloud`.
   - Fill in `SEND_SMS_HOOK_SECRET`, `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `OTP_PLATFORM_API_KEY`.
   - Verify health: `curl https://vidyon-otp-service.onrender.com/health`.

3. **Supabase Project A (Production ERP)**:
   - In Dashboard → Authentication → Hooks → Send SMS Hook:
     - URL: `https://vidyon-otp-service.onrender.com/hooks/send-message`
     - Save and verify webhook secret matches `SEND_SMS_HOOK_SECRET`.

4. **Frontend ERP**:
   - Set `EXPO_PUBLIC_ENABLE_FORGOT_PASSWORD=true` in production environment build.

---

## 2. Emergency Rollback Plan (< 5 minutes)

If an issue occurs in production:
1. **Instant Cut-off:** In Supabase Project A Dashboard → Authentication → Hooks, disable or delete the **Send SMS Hook**. Supabase Auth immediately stops calling the Python service.
2. **Frontend Kill-switch:** Deploy frontend with `EXPO_PUBLIC_ENABLE_FORGOT_PASSWORD=false` to immediately hide the Forgot Password link on Android and Windows clients.
3. **Database Rollback:** If Project C needs cleanup, run the commented rollback block at the bottom of `master_otp_schema.sql`.
