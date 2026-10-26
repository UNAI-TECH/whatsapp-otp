# My Vidyon ERP — Forgot Password Frontend Integration

This module contains the complete **Forgot Password Flow** for the My Vidyon ERP application (React Native / Expo Android + Electron Windows).

---

## 1. File Structure

```
frontend/src/features/forgot-password/
├── ForgotPasswordNavigator.tsx   # Stack coordinator (feature-flagged)
├── PhoneInputScreen.tsx          # Step 1: WhatsApp phone entry (+91)
├── OtpInputScreen.tsx            # Step 2: 6-digit OTP input + resend cooldown
├── NewPasswordScreen.tsx         # Step 3: Password policy check + sign-out
├── hooks/
│   ├── useOtpRequest.ts          # signInWithOtp wrapper + cooldown
│   └── useOtpVerify.ts           # verifyOtp wrapper + session ownership check
├── i18n/
│   ├── en.ts                     # English UI strings
│   └── ta.ts                     # Tamil UI strings
└── utils/
    ├── phoneValidation.ts        # +91 validation & normalisation
    └── cooldownStorage.ts        # Persistent 60s cooldown timer
```

---

## 2. Feature Flag

The entire flow is protected behind the environment variable:
```env
EXPO_PUBLIC_ENABLE_FORGOT_PASSWORD=true
```

In your existing `LoginScreen.tsx`:
```tsx
import { ENABLE_FORGOT_PASSWORD } from './features/forgot-password/ForgotPasswordNavigator';

// Render the Forgot Password link only when the feature flag is enabled:
{ENABLE_FORGOT_PASSWORD && (
  <TouchableOpacity onPress={() => navigation.navigate('ForgotPassword')}>
    <Text style={styles.forgotPasswordLink}>Forgot Password?</Text>
  </TouchableOpacity>
)}
```

---

## 3. Navigation Wiring

Add `ForgotPasswordNavigator` to your app's Auth stack:

```tsx
import { ForgotPasswordNavigator } from './features/forgot-password/ForgotPasswordNavigator';
import { supabase } from './lib/supabaseClient';

<Stack.Screen name="ForgotPassword" options={{ headerShown: false }}>
  {(props) => (
    <ForgotPasswordNavigator
      supabaseClient={supabase}
      language="en" // or 'ta' based on user preference
      onComplete={() => props.navigation.navigate('Login')}
      onCancel={() => props.navigation.navigate('Login')}
    />
  )}
</Stack.Screen>
```

---

## 4. Key Security Features

1. **Anti-Account Enumeration**: When a user enters their phone number, the UI displays:
   > *"If an account exists, you will receive a WhatsApp message."*
   The response is identical whether the user exists or not.
2. **Session Ownership Verification**: In `useOtpVerify.ts`, after Supabase verifies the OTP, it asserts that `session.user.phone` matches the phone number entered. If a mismatch is detected, the session is purged immediately.
3. **Session Invalidation on Reset**: In `NewPasswordScreen.tsx`, after `updateUser({ password })` succeeds, `supabase.auth.signOut()` is called immediately to force the user to log in with their new credentials.
4. **Persistent Cooldown**: 60-second cooldown is stored in persistent storage to prevent spamming across app refreshes.
