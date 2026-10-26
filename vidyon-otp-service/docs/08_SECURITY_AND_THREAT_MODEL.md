# 08 — Security and Threat Model

**System:** My Vidyon WhatsApp OTP (`MYV-SMS-OTP`)

---

## 1. Threat Mitigations

| Threat Vector | Mitigation Strategy |
|---|---|
| **Account Enumeration** | The frontend and backend return identical generic responses regardless of whether the phone exists in the user database. |
| **Replay Attacks** | In-memory cache checks `webhook-id` against a 300s TTL cache. Replayed IDs are immediately rejected with HTTP 401. |
| **Brute-Force OTP Guessing** | Project C limits attempts to 3 per OTP. Upon 3 failed attempts, status is marked `expired`. |
| **SMS/WhatsApp Flooding** | Rolling rate limiting per `(app_id, phone_hash)` allows a maximum of 5 OTP requests per 10-minute window. |
| **Session Hijacking / Misattribution** | Frontend `useOtpVerify` asserts `session.user.phone === requestedPhone`. Mismatched sessions trigger immediate `signOut()`. |
| **Data Leakage in Logs** | Custom `RedactionFilter` scrubs all phone numbers, OTP codes, bearer tokens, and webhook secrets from logs before output. |
| **Database Compromise** | OTPs are hashed using SHA-256 with 16-byte cryptographically secure random salts. Plaintext OTPs never touch disk. |
