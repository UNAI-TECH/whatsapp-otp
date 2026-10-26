# 05 — WhatsApp Cloud API Provider Configuration

The service interfaces directly with Meta's Graph API (`https://graph.facebook.com/v19.0/{phone_number_id}/messages`).

---

## 1. Prerequisites

1. Meta Business Account with registered WhatsApp Business App.
2. Verified phone number registered under WhatsApp Cloud API.
3. Approved authentication / OTP message templates:
   - English template name: `otp_en` (Language code: `en`)
   - Tamil template name: `otp_ta` (Language code: `ta`)
4. Permanent System User Access Token with `whatsapp_business_messaging` permissions.

---

## 2. Template Payload Structure

```json
{
  "messaging_product": "whatsapp",
  "to": "+919876543210",
  "type": "template",
  "template": {
    "name": "otp_en",
    "language": { "code": "en" },
    "components": [
      {
        "type": "body",
        "parameters": [{ "type": "text", "text": "123456" }]
      },
      {
        "type": "button",
        "sub_type": "url",
        "index": "0",
        "parameters": [{ "type": "text", "text": "123456" }]
      }
    ]
  }
}
```

> [!NOTE]
> Ensure the button `sub_type` matches the exact template format configured in Meta WhatsApp Manager (e.g. `url` or `copy_code`).
