# 03 — Supabase Project B Configuration (Staging)

Project B serves as the staging and testing environment for My Vidyon ERP.

---

## 1. Staging Setup

1. Configure the Send SMS Auth hook in Project B to point to the staging instance or local dev tunnel (e.g. `ngrok` or Render staging service).
2. Set `PROVIDER=mock` and `MOCK_MODE=success` in the service environment during staging tests to avoid incurring Meta API costs.
3. Test end-to-end user experience without sending live WhatsApp messages.
