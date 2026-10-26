import { useState, useCallback } from 'react';

export interface UseOtpVerifyProps {
  supabaseClient: any;
  phone: string;
  onVerified?: (session: any) => void;
}

export function useOtpVerify({ supabaseClient, phone, onVerified }: UseOtpVerifyProps) {
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [attemptsRemaining, setAttemptsRemaining] = useState<number | null>(null);

  const verifyOtp = useCallback(
    async (token: string) => {
      setError(null);
      if (!token || token.length < 4) {
        setError('INVALID_FORMAT');
        return false;
      }

      setLoading(true);
      try {
        const normalised = phone.replace(/\s+/g, '');
        const { data, error: verError } = await supabaseClient.auth.verifyOtp({
          phone: normalised,
          token: token.trim(),
          type: 'sms',
        });

        if (verError) {
          const msg = verError.message.toLowerCase();
          if (msg.includes('expired')) {
            setError('OTP_EXPIRED');
          } else {
            setError('WRONG_OTP');
            setAttemptsRemaining((prev) => (prev !== null ? Math.max(0, prev - 1) : 2));
          }
          return false;
        }

        // Strict Session Ownership Check: ensure session user phone matches requested phone
        const sessionPhone = data.session?.user?.phone ?? '';
        const barePhone = normalised.replace('+', '');
        if (sessionPhone !== normalised && sessionPhone !== barePhone) {
          await supabaseClient.auth.signOut();
          setError('SESSION_PHONE_MISMATCH');
          return false;
        }

        onVerified?.(data.session);
        return true;
      } catch (err: any) {
        setError('NETWORK_ERROR');
        return false;
      } finally {
        setLoading(false);
      }
    },
    [supabaseClient, phone, onVerified]
  );

  return {
    verifyOtp,
    loading,
    error,
    attemptsRemaining,
  };
}
