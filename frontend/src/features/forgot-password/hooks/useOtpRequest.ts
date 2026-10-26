import { useState, useEffect, useCallback } from 'react';
import { saveCooldownStart, getRemainingCooldown } from '../utils/cooldownStorage';
import { normalisePhone, isValidIndiaMobile } from '../utils/phoneValidation';

export interface UseOtpRequestProps {
  supabaseClient: any;
  onSuccess?: () => void;
}

export function useOtpRequest({ supabaseClient, onSuccess }: UseOtpRequestProps) {
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [cooldownSeconds, setCooldownSeconds] = useState<number>(0);

  // Check stored cooldown on mount
  useEffect(() => {
    let mounted = true;
    getRemainingCooldown().then((rem) => {
      if (mounted) setCooldownSeconds(rem);
    });
    return () => {
      mounted = false;
    };
  }, []);

  // Tick cooldown every second
  useEffect(() => {
    if (cooldownSeconds <= 0) return;
    const interval = setInterval(() => {
      setCooldownSeconds((prev) => Math.max(0, prev - 1));
    }, 1000);
    return () => clearInterval(interval);
  }, [cooldownSeconds]);

  const requestOtp = useCallback(
    async (rawPhone: string) => {
      setError(null);
      const normalised = normalisePhone(rawPhone);

      if (!isValidIndiaMobile(normalised)) {
        setError('INVALID_PHONE');
        return false;
      }

      if (cooldownSeconds > 0) {
        return false;
      }

      setLoading(true);
      try {
        const { error: reqError } = await supabaseClient.auth.signInWithOtp({
          phone: normalised,
          options: {
            shouldCreateUser: false, // Critical: never create users during password recovery
          },
        });

        // Even if an error occurred (e.g. user not found), we treat as success to prevent account enumeration
        if (reqError) {
          console.warn('signInWithOtp error:', reqError.message);
        }

        await saveCooldownStart();
        setCooldownSeconds(60);
        onSuccess?.();
        return true;
      } catch (err: any) {
        setError('NETWORK_ERROR');
        return false;
      } finally {
        setLoading(false);
      }
    },
    [supabaseClient, cooldownSeconds, onSuccess]
  );

  return {
    requestOtp,
    loading,
    error,
    cooldownSeconds,
  };
}
