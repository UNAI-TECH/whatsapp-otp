# Open Questions and Verification Items

The following items are marked for confirmation prior to live production sign-off (Gate G8):

1. **Meta WhatsApp Authentication Template Button Format**:
   - In `app/providers/whatsapp_cloud.py`, the button parameter is currently configured as `sub_type: "url"`.
   - **Action Required:** Verify the button type of your registered WhatsApp Business Manager template (whether it is registered as an authentication URL button or a `copy_code` button) and adjust `sub_type` accordingly if using `copy_code`.

2. **Supabase Auth Hook `user.phone` Format**:
   - In test fixtures, `+919876543210` is passed with leading plus.
   - `app/phone.py` normalisation safely handles both with and without leading `+` (e.g. `9876543210` or `919876543210` or `+919876543210`).
   - **Status:** Verified resilient to both formats.
