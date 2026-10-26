# 07 — ERP Frontend Integration

**Target Environments:** React Native / Expo (Android) + Electron (Windows).

---

## 1. Feature Flag Configuration

The flow is strictly isolated behind:
```env
EXPO_PUBLIC_ENABLE_FORGOT_PASSWORD=true
```
If disabled or unset in production, the Forgot Password button remains hidden.

---

## 2. Integration Checklist

1. Copy `frontend/src/features/forgot-password/` into your ERP client repository at `src/features/forgot-password/`.
2. Ensure `@react-native-async-storage/async-storage` is present in the React Native project (automatic fallback to `localStorage` for Electron/Web).
3. Connect your Supabase client instance to `ForgotPasswordNavigator`.
4. Configure English (`en`) or Tamil (`ta`) language selection based on active app locale.
