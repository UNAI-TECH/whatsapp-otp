/**
 * Cross-platform cooldown storage surviving app restarts and reloads.
 * Supports React Native (AsyncStorage) and Web / Electron (localStorage).
 */

const COOLDOWN_KEY = 'otp_cooldown_start';
const COOLDOWN_DURATION_MS = 60_000; // 60 seconds

async function getStorageItem(key: string): Promise<string | null> {
  try {
    // If running in React Native with AsyncStorage installed
    const AsyncStorage = require('@react-native-async-storage/async-storage').default;
    return await AsyncStorage.getItem(key);
  } catch {
    // Fallback to window.localStorage (Web / Electron) or memory
    if (typeof window !== 'undefined' && window.localStorage) {
      return window.localStorage.getItem(key);
    }
    return null;
  }
}

async function setStorageItem(key: string, value: string): Promise<void> {
  try {
    const AsyncStorage = require('@react-native-async-storage/async-storage').default;
    await AsyncStorage.setItem(key, value);
  } catch {
    if (typeof window !== 'undefined' && window.localStorage) {
      window.localStorage.setItem(key, value);
    }
  }
}

export async function saveCooldownStart(): Promise<void> {
  await setStorageItem(COOLDOWN_KEY, Date.now().toString());
}

export async function getRemainingCooldown(): Promise<number> {
  const raw = await getStorageItem(COOLDOWN_KEY);
  if (!raw) return 0;
  const startTime = parseInt(raw, 10);
  if (isNaN(startTime)) return 0;

  const elapsed = Date.now() - startTime;
  const remaining = Math.ceil((COOLDOWN_DURATION_MS - elapsed) / 1000);
  return Math.max(0, remaining);
}
