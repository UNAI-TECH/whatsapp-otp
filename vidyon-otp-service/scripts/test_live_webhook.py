import sys
import json
import uuid
from datetime import datetime, timezone
import httpx
from standardwebhooks import Webhook

# Configuration
SERVICE_URL = "https://whatsapp-otp-0ozl.onrender.com/hooks/send-message"
SECRET_RAW = "v1,whsec_xQ1qKaC3mlKXayXTRTVrFru9nTPkjzc0v0hBHOfh7gA="

# standardwebhooks requires stripping 'v1,' if present
CLEAN_SECRET = SECRET_RAW[3:] if SECRET_RAW.startswith("v1,") else SECRET_RAW


def send_test_otp(phone: str, otp: str = "482910"):
    print(f"\n=======================================================")
    print(f"Testing live WhatsApp OTP delivery to: {phone}")
    print(f"Target URL: {SERVICE_URL}")
    print(f"OTP code:   {otp}")
    print(f"=======================================================\n")

    payload = json.dumps({
        "user": {
            "id": str(uuid.uuid4()),
            "phone": phone
        },
        "sms": {
            "otp": otp
        }
    })

    msg_id = f"msg_{uuid.uuid4().hex[:16]}"
    now_dt = datetime.now(timezone.utc)
    ts_str = str(int(now_dt.timestamp()))

    wh = Webhook(CLEAN_SECRET)
    signature = wh.sign(msg_id, now_dt, payload)

    headers = {
        "webhook-id": msg_id,
        "webhook-timestamp": ts_str,
        "webhook-signature": signature,
        "content-type": "application/json"
    }

    print("1. Dispatching signed webhook to Render service...")
    try:
        resp = httpx.post(SERVICE_URL, content=payload, headers=headers, timeout=10.0)
        print(f"Status Code: {resp.status_code}")
        print(f"Response:    {resp.text}")

        if resp.status_code == 200:
            print("\n[SUCCESS] Delivery accepted by Render and handed to WhatsApp Cloud API!")
            print(f"Check WhatsApp on {phone} now for your verification message.")
        else:
            print("\n[ERROR] Service returned an error. Check logs on Render dashboard.")
    except Exception as exc:
        print(f"\n[NETWORK ERROR] Failed to connect: {exc}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        target_phone = sys.argv[1].strip()
    else:
        target_phone = input("Enter your WhatsApp mobile number (+91XXXXXXXXXX): ").strip()

    if not target_phone.startswith("+"):
        target_phone = "+" + target_phone

    send_test_otp(target_phone)
