import re

INDIA_MOBILE_RE = re.compile(r"^\+91[6-9]\d{9}$")


def normalise(raw: str) -> str:
    """
    Clean and normalise raw phone number to E.164 +91 format.
    Handles spaces, dashes, parentheses, leading zeros, and bare 10-digit mobiles.
    """
    cleaned = raw.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    
    # 0 followed by 10-digit Indian mobile
    if cleaned.startswith("0") and len(cleaned) == 11 and cleaned[1] in "6789":
        return "+91" + cleaned[1:]
    
    # 10 digits starting with 6-9
    if len(cleaned) == 10 and cleaned[0] in "6789":
        return "+91" + cleaned
    
    # 91 followed by 10 digits without leading +
    if cleaned.startswith("91") and len(cleaned) == 12 and cleaned[2] in "6789":
        return "+" + cleaned
        
    if not cleaned.startswith("+"):
        cleaned = "+" + cleaned
        
    return cleaned


def validate_india_mobile(phone: str) -> str:
    """Return normalised E.164 phone or raise ValueError."""
    normalised = normalise(phone)
    if not INDIA_MOBILE_RE.match(normalised):
        suffix = normalised[-4:] if len(normalised) >= 4 else "unknown"
        raise ValueError(f"Not a valid Indian mobile number: {suffix}")
    return normalised


def mask(phone: str) -> str:
    """Return last 4 digits only for safe logging (e.g. ****3210)."""
    return "****" + phone[-4:] if len(phone) >= 4 else "****"
