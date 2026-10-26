import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  ActivityIndicator,
  StyleSheet,
} from 'react-native';
import { en } from './i18n/en';
import { ta } from './i18n/ta';

export interface NewPasswordScreenProps {
  supabaseClient: any;
  language?: 'en' | 'ta';
  onPasswordResetComplete: () => void;
}

export const NewPasswordScreen: React.FC<NewPasswordScreenProps> = ({
  supabaseClient,
  language = 'en',
  onPasswordResetComplete,
}) => {
  const strings = language === 'ta' ? ta : en;
  const [password, setPassword] = useState<string>('');
  const [confirmPassword, setConfirmPassword] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<boolean>(false);

  const validatePassword = (pwd: string): boolean => {
    // ERP password policy: >= 8 characters, at least 1 uppercase, at least 1 digit
    return pwd.length >= 8 && /[A-Z]/.test(pwd) && /[0-9]/.test(pwd);
  };

  const handleUpdatePassword = async () => {
    setError(null);

    if (!validatePassword(password)) {
      setError(strings.passwordTooShort);
      return;
    }

    if (password !== confirmPassword) {
      setError(strings.passwordsDoNotMatch);
      return;
    }

    setLoading(true);
    try {
      const { error: updateError } = await supabaseClient.auth.updateUser({
        password: password,
      });

      if (updateError) {
        if (updateError.message.toLowerCase().includes('session')) {
          setError(strings.sessionExpired);
        } else {
          setError(updateError.message);
        }
        return;
      }

      // Security requirement: sign out immediately so user must authenticate with new password
      await supabaseClient.auth.signOut();
      setSuccess(true);

      setTimeout(() => {
        onPasswordResetComplete();
      }, 1500);
    } catch {
      setError(strings.networkError);
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <View style={styles.card}>
        <Text style={styles.title}>{strings.newPassword}</Text>
        <Text style={styles.subtitle}>{strings.passwordRules}</Text>

        <Text style={styles.label}>{strings.newPassword}</Text>
        <TextInput
          style={styles.input}
          placeholder="••••••••"
          placeholderTextColor="#94A3B8"
          value={password}
          onChangeText={setPassword}
          secureTextEntry
          autoCapitalize="none"
          autoCorrect={false}
          editable={!loading && !success}
        />

        <Text style={styles.label}>{strings.confirmPassword}</Text>
        <TextInput
          style={styles.input}
          placeholder="••••••••"
          placeholderTextColor="#94A3B8"
          value={confirmPassword}
          onChangeText={setConfirmPassword}
          secureTextEntry
          autoCapitalize="none"
          autoCorrect={false}
          editable={!loading && !success}
        />

        {error && <Text style={styles.errorText}>{error}</Text>}
        {success && <Text style={styles.successText}>{strings.successMessage}</Text>}

        <TouchableOpacity
          style={[styles.primaryButton, (loading || success) && styles.disabledButton]}
          onPress={handleUpdatePassword}
          disabled={loading || success}
        >
          {loading ? (
            <ActivityIndicator color="#FFFFFF" />
          ) : (
            <Text style={styles.primaryButtonText}>{strings.updatePassword}</Text>
          )}
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
    fontSize: 13,
    color: '#64748B',
    marginBottom: 20,
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
    marginBottom: 16,
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
    marginBottom: 12,
  },
  successText: {
    color: '#16A34A',
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 12,
    textAlign: 'center',
  },
});
