import json
import logging
import re
import sys
from datetime import datetime, timezone
from typing import Any, Dict


# Regex patterns for redaction
RE_FULL_PHONE = re.compile(r"(\+?91[6-9]\d{5})(\d{4})\b")
RE_OTP_IN_TEXT = re.compile(r'(["\']?otp["\']?\s*[:=]\s*["\']?)(\d{4,10})(["\']?)', re.IGNORECASE)
RE_SIGNATURE = re.compile(r"(whsec_[A-Za-z0-9+/=_\-]+|v1,[A-Za-z0-9+/=_\-]+)", re.IGNORECASE)
RE_BEARER_TOKEN = re.compile(r"(Bearer\s+)[A-Za-z0-9_\-\.]{15,}", re.IGNORECASE)
RE_OTP_KEY = re.compile(r"\botp_[A-Za-z0-9_\-]{16,}\b", re.IGNORECASE)


class RedactionFilter(logging.Filter):
    """Filter that scrubs PII (full phone numbers, OTP codes, auth secrets) from log messages."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self.redact(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: (self.redact(v) if isinstance(v, str) else v) for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(self.redact(arg) if isinstance(arg, str) else arg for arg in record.args)
        return True

    @classmethod
    def redact(cls, text: str) -> str:
        # 1. Mask full Indian phone numbers: +919876543210 -> ****3210
        text = RE_FULL_PHONE.sub(r"****\2", text)
        # 2. Redact OTP digits in key-value contexts
        text = RE_OTP_IN_TEXT.sub(r"\1[REDACTED]\3", text)
        # 3. Redact webhook signatures / secrets
        text = RE_SIGNATURE.sub(r"[REDACTED_SECRET]", text)
        # 4. Redact bearer tokens
        text = RE_BEARER_TOKEN.sub(r"\1[REDACTED_TOKEN]", text)
        # 5. Redact OTP Platform API keys
        text = RE_OTP_KEY.sub(r"otp_[REDACTED]", text)
        return text


class JsonFormatter(logging.Formatter):
    """Outputs structured JSON log records for production observability."""

    def format(self, record: logging.LogRecord) -> str:
        data: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if hasattr(record, "request_id"):
            data["request_id"] = record.request_id

        if record.exc_info:
            data["exception"] = self.formatException(record.exc_info)

        return json.dumps(data)


def configure_logging(log_level: str = "INFO") -> None:
    """Configures root logger with JSON formatting and redaction filter."""
    root = logging.getLogger()
    root.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Remove existing handlers to avoid duplicates
    for handler in list(root.handlers):
        root.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(RedactionFilter())
    root.addHandler(handler)
