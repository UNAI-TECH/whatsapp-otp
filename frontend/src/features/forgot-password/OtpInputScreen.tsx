import React, { useState, useRef } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  ActivityIndicator,
  StyleSheet,
  Alert,
} from 'react-native';
import { useOtpVerify } from './hooks/useOtpVerify';
import { useOtpRequest } from './hooks/useOtpRequest';
import { en } from './i18n/en';
import { ta } from './i18n/ta';

export interface OtpInputScreenProps {
  supabaseClient: any;
  phone: string;
  language?: 'en' | 'ta';
  onVerified: (session: any) => void;
  onBack: () => void;
}

export const OtpInputScreen: React.FC<OtpInputScreenProps> = ({
  supabaseClient,
  phone,
  language = 'en',
  onVerified,
  onBack,
}) => {
  const strings = language === 'ta' ? ta : en;
  const [digits, setDigits] = useState<string[]>(['', '', '', '', '', '']);
  const inputsRef = useRef<(TextInput | null)[]>([]);

  const { verifyOtp, loading: verifying, error, attemptsRemaining } = useOtpVerify({
    supabaseClient,
    phone,
    onVerified,
  });

  const {
    requestOtp: resendOtp,
    loading: resending,
    cooldownSeconds,
  } = useOtpRequest({
    supabaseClient,
  });

  const handleDigitChange = (text: string, index: number) => {
    const cleaned = text.replace(/[^0-9]/g, '');
    const newDigits = [...digits];

    if (cleaned.length > 1) {
      // Pasted full OTP code
      const pasted = cleaned.slice(0, 6).split('');
      for (let i = 0; i < 6; i++) {
        newDigits[i] = pasted[i] || '';
      }
      setDigits(newDigits);
      inputsRef.current[Math.min(pasted.length, 5)]?.focus();
      return;
    }

    newDigits[index] = cleaned;
    setDigits(newDigits);

    // Auto advance focus
    if (cleaned && index < 5) {
      inputsRef.current[index + 1]?.focus();
    }
  };

  const handleKeyPress = (e: any, index: number) => {
    if (e.nativeEvent.key === 'Backspace' && !digits[index] && index > 0) {
      inputsRef.current[index - 1]?.focus();
    }
  };

  const handleVerify = async () => {
    const otp = digits.join('');
    if (otp.length < 6 || verifying) return;
    await verifyOtp(otp);
  };

  const handleResend = async () => {
    if (cooldownSeconds > 0 || resending) return;
    await resendOtp(phone);
  };

  const handleBackPress = () => {
    Alert.alert(
      strings.confirmLeaveTitle,
      strings.confirmLeaveMessage,
      [
        { text: strings.stay, style: 'cancel' },
        { text: strings.leave, style: 'destructive', onPress: onBack },
      ]
    );
  };

  const otpComplete = digits.join('').length === 6;

  return (
    <View style={styles.container}>
      <View style={styles.card}>
        <Text style={styles.title}>{strings.enterOtp}</Text>
        <Text style={styles.subtitle}>
          {phone.length >= 4 ? `+91 **** ${phone.slice(-4)}` : phone}
        </Text>

        <View style={styles.otpRow}>
          {digits.map((digit, index) => (
            <TextInput
              key={index}
              ref={(ref) => (inputsRef.current[index] = ref)}
              style={[styles.otpCell, digit ? styles.otpCellFilled : null]}
              value={digit}
              onChangeText={(text) => handleDigitChange(text, index)}
              onKeyPress={(e) => handleKeyPress(e, index)}
              keyboardType="number-pad"
              maxLength={index === 0 ? 6 : 1}
              autoFocus={index === 0}
              selectTextOnFocus
              editable={!verifying}
            />
          ))}
        </View>

        {error === 'WRONG_OTP' && (
          <Text style={styles.errorText}>
            {strings.wrongOtp.replace(
              '{{n}}',
              (attemptsRemaining ?? 2).toString()
            )}
          </Text>
        )}
        {error === 'OTP_EXPIRED' && (
          <Text style={styles.errorText}>{strings.otpExpired}</Text>
        )}
        {error === 'SESSION_PHONE_MISMATCH' && (
          <Text style={styles.errorText}>{strings.sessionExpired}</Text>
        )}
        {error === 'NETWORK_ERROR' && (
          <Text style={styles.errorText}>{strings.networkError}</Text>
        )}

        <TouchableOpacity
          style={[
            styles.primaryButton,
            (!otpComplete || verifying) && styles.disabledButton,
          ]}
          onPress={handleVerify}
          disabled={!otpComplete || verifying}
        >
          {verifying ? (
            <ActivityIndicator color="#FFFFFF" />
          ) : (
            <Text style={styles.primaryButtonText}>{strings.verify}</Text>
          )}
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.resendButton}
          onPress={handleResend}
          disabled={cooldownSeconds > 0 || resending}
        >
          <Text
            style={[
              styles.resendButtonText,
              cooldownSeconds > 0 && styles.disabledResendText,
            ]}
          >
            {cooldownSeconds > 0
              ? strings.resendIn.replace('{{s}}', cooldownSeconds.toString())
              : strings.resend}
          </Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.backButton} onPress={handleBackPress}>
          <Text style={styles.backButtonText}>{strings.backToLogin}</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 16,
    backgroundColor: '#F8FAFC',
  },
  card: {
    width: '100%',
    maxWidth: 420,
    backgroundColor: '#FFFFFF',
    borderRadius: 16,
    padding: 24,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.08,
    shadowRadius: 12,
    elevation: 3,
  },
  title: {
    fontSize: 22,
    fontWeight: '700',
    color: '#0F172A',
    marginBottom: 8,
    textAlign: 'center',
  },
  subtitle: {
    fontSize: 14,
    color: '#64748B',
    marginBottom: 24,
    textAlign: 'center',
  },
  otpRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 20,
  },
  otpCell: {
    width: 48,
    height: 52,
    borderWidth: 1.5,
    borderColor: '#CBD5E1',
    borderRadius: 8,
    textAlign: 'center',
    fontSize: 22,
    fontWeight: '600',
    color: '#0F172A',
    backgroundColor: '#FFFFFF',
  },
  otpCellFilled: {
    borderColor: '#2563EB',
    backgroundColor: '#EFF6FF',
  },
  primaryButton: {
    height: 48,
    backgroundColor: '#2563EB',
    borderRadius: 8,
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 8,
  },
  disabledButton: {
    backgroundColor: '#94A3B8',
  },
  primaryButtonText: {
    color: '#FFFFFF',
    fontSize: 15,
    fontWeight: '600',
  },
  resendButton: {
    marginTop: 16,
    alignItems: 'center',
  },
  resendButtonText: {
    color: '#2563EB',
    fontSize: 14,
    fontWeight: '600',
  },
  disabledResendText: {
    color: '#94A3B8',
    fontWeight: '400',
  },
  errorText: {
    color: '#DC2626',
    fontSize: 13,
    marginBottom: 12,
    textAlign: 'center',
  },
  backButton: {
    marginTop: 16,
    alignItems: 'center',
  },
  backButtonText: {
    color: '#64748B',
    fontSize: 14,
  },
});
