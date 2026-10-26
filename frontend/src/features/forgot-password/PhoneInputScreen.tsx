import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  ActivityIndicator,
  StyleSheet,
} from 'react-native';
import { useOtpRequest } from './hooks/useOtpRequest';
import { en } from './i18n/en';
import { ta } from './i18n/ta';

export interface PhoneInputScreenProps {
  supabaseClient: any;
  language?: 'en' | 'ta';
  onOtpSent: (phone: string) => void;
  onBackToLogin: () => void;
}

export const PhoneInputScreen: React.FC<PhoneInputScreenProps> = ({
  supabaseClient,
  language = 'en',
  onOtpSent,
  onBackToLogin,
}) => {
  const strings = language === 'ta' ? ta : en;
  const [phone, setPhone] = useState<string>('');
  const [feedbackMessage, setFeedbackMessage] = useState<string | null>(null);

  const { requestOtp, loading, error, cooldownSeconds } = useOtpRequest({
    supabaseClient,
    onSuccess: () => {
      setFeedbackMessage(strings.otpSentMessage);
      setTimeout(() => {
        onOtpSent(phone);
      }, 1200);
    },
  });

  const handleSubmit = async () => {
    if (loading || cooldownSeconds > 0) return;
    await requestOtp(phone);
  };

  return (
    <View style={styles.container}>
      <View style={styles.card}>
        <Text style={styles.title}>{strings.forgotPassword}</Text>
        <Text style={styles.subtitle}>{strings.phoneHint}</Text>

        <Text style={styles.label}>{strings.phoneLabel}</Text>
        <TextInput
          style={styles.input}
          placeholder={strings.phonePlaceholder}
          placeholderTextColor="#94A3B8"
          value={phone}
          onChangeText={setPhone}
          keyboardType="phone-pad"
          autoCapitalize="none"
          autoCorrect={false}
          editable={!loading}
        />

        {error === 'INVALID_PHONE' && (
          <Text style={styles.errorText}>{strings.invalidPhone}</Text>
        )}
        {error === 'NETWORK_ERROR' && (
          <Text style={styles.errorText}>{strings.networkError}</Text>
        )}
        {feedbackMessage && (
          <Text style={styles.successText}>{feedbackMessage}</Text>
        )}

        <TouchableOpacity
          style={[
            styles.primaryButton,
            (loading || cooldownSeconds > 0) && styles.disabledButton,
          ]}
          onPress={handleSubmit}
          disabled={loading || cooldownSeconds > 0}
        >
          {loading ? (
            <ActivityIndicator color="#FFFFFF" />
          ) : (
            <Text style={styles.primaryButtonText}>
              {cooldownSeconds > 0
                ? strings.resendIn.replace('{{s}}', cooldownSeconds.toString())
                : strings.sendOtp}
            </Text>
          )}
        </TouchableOpacity>

        <TouchableOpacity style={styles.backButton} onPress={onBackToLogin}>
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
  label: {
    fontSize: 13,
    fontWeight: '600',
    color: '#334155',
    marginBottom: 6,
  },
  input: {
    height: 48,
    borderWidth: 1,
    borderColor: '#CBD5E1',
    borderRadius: 8,
    paddingHorizontal: 14,
    fontSize: 15,
    color: '#0F172A',
    backgroundColor: '#FFFFFF',
    marginBottom: 12,
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
  errorText: {
    color: '#DC2626',
    fontSize: 13,
    marginBottom: 8,
  },
  successText: {
    color: '#16A34A',
    fontSize: 13,
    marginBottom: 8,
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
