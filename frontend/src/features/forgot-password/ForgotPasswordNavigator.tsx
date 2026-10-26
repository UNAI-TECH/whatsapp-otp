import React, { useState } from 'react';
import { View, StyleSheet } from 'react-native';
import { PhoneInputScreen } from './PhoneInputScreen';
import { OtpInputScreen } from './OtpInputScreen';
import { NewPasswordScreen } from './NewPasswordScreen';

export const ENABLE_FORGOT_PASSWORD =
  process.env.EXPO_PUBLIC_ENABLE_FORGOT_PASSWORD === 'true';

export type ForgotPasswordStep = 'phone' | 'otp' | 'new_password';

export interface ForgotPasswordNavigatorProps {
  supabaseClient: any;
  language?: 'en' | 'ta';
  onComplete: () => void;
  onCancel: () => void;
}

export const ForgotPasswordNavigator: React.FC<ForgotPasswordNavigatorProps> = ({
  supabaseClient,
  language = 'en',
  onComplete,
  onCancel,
}) => {
  // If feature flag is disabled, return null or abort
  if (!ENABLE_FORGOT_PASSWORD && process.env.NODE_ENV === 'production') {
    return null;
  }

  const [step, setStep] = useState<ForgotPasswordStep>('phone');
  const [phone, setPhone] = useState<string>('');

  const handleOtpSent = (submittedPhone: string) => {
    setPhone(submittedPhone);
    setStep('otp');
  };

  const handleVerified = (_session: any) => {
    setStep('new_password');
  };

  return (
    <View style={styles.container}>
      {step === 'phone' && (
        <PhoneInputScreen
          supabaseClient={supabaseClient}
          language={language}
          onOtpSent={handleOtpSent}
          onBackToLogin={onCancel}
        />
      )}

      {step === 'otp' && (
        <OtpInputScreen
          supabaseClient={supabaseClient}
          phone={phone}
          language={language}
          onVerified={handleVerified}
          onBack={onCancel}
        />
      )}

      {step === 'new_password' && (
        <NewPasswordScreen
          supabaseClient={supabaseClient}
          language={language}
          onPasswordResetComplete={onComplete}
        />
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    width: '100%',
    height: '100%',
  },
});
