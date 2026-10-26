/**
 * Validates Indian mobile numbers (+91 followed by 10 digits starting with 6, 7, 8, or 9).
 */
export function isValidIndiaMobile(phone: string): boolean {
  const cleaned = phone.replace(/\s+/g, '').replace(/-/g, '');
  return /^\+91[6-9]\d{9}$/.test(cleaned);
}

/**
 * Normalises raw user input to standard +91 E.164 format.
 */
export function normalisePhone(phone: string): string {
  let cleaned = phone.trim().replace(/\s+/g, '').replace(/-/g, '').replace(/[()]/g, '');
  if (cleaned.startsWith('0') && cleaned.length === 11 && '6789'.includes(cleaned[1])) {
    return '+91' + cleaned.substring(1);
  }
  if (cleaned.length === 10 && '6789'.includes(cleaned[0])) {
    return '+91' + cleaned;
  }
  if (cleaned.startsWith('91') && cleaned.length === 12 && '6789'.includes(cleaned[2])) {
    return '+' + cleaned;
  }
  if (!cleaned.startsWith('+')) {
    cleaned = '+' + cleaned;
  }
  return cleaned;
}
