# My Vidyon WhatsApp OTP (`MYV-SMS-OTP`)

Central WhatsApp OTP integration for My Vidyon School ERP. Coordinates between Supabase Auth (Project A), Python Service (Render Singapore), Supabase Dedicated OTP Platform (Project C), and the ERP Client (React Native/Expo + Electron).

---

## Workspace Structure

- [`vidyon-otp-service/`](vidyon-otp-service/):
  - **`app/`**: FastAPI backend service for the Supabase Auth Send SMS hook.
  - **`tests/`**: Automated test suite (33 tests, 100% passing).
  - **`supabase/`**:
    - `master_otp_schema.sql`: Dedicated SQL engine for Supabase Project C.
    - `functions/`: Edge Functions (`otp-generate`, `otp-verify`).
  - **`docs/`**: Architecture, setup, security, and deployment guides (01 through 10).
  - **`Dockerfile` & `render.yaml`**: Singapore region production deployment specifications.
- [`frontend/`](frontend/):
  - **`src/features/forgot-password/`**: Feature-flagged forgot password screens (`PhoneInputScreen`, `OtpInputScreen`, `NewPasswordScreen`), hooks, English and Tamil i18n, and persistent cooldown storage.

---

## Quick Verification

```bash
cd vidyon-otp-service
.\.venv\Scripts\pytest -v tests
```
Output:
```
33 passed in ~3s
All checks passed!
```
