import logging
import io
from app.logging_utils import RedactionFilter, JsonFormatter


def test_redaction_filter_scrubs_phone():
    log_filter = RedactionFilter()
    raw_message = "User phone is +919876543210 ready for dispatch"
    redacted = log_filter.redact(raw_message)
    assert "+919876543210" not in redacted
    assert "****3210" in redacted


def test_redaction_filter_scrubs_otp():
    log_filter = RedactionFilter()
    raw_message = 'Dispatching message with otp="849201" to user'
    redacted = log_filter.redact(raw_message)
    assert "849201" not in redacted
    assert "[REDACTED]" in redacted


def test_redaction_filter_scrubs_secrets():
    log_filter = RedactionFilter()
    raw_message = "Webhook signed with whsec_52968393847291048291048291048291 and token Bearer mysecrettoken123456789"
    redacted = log_filter.redact(raw_message)
    assert "whsec_52968393847291048291048291048291" not in redacted
    assert "mysecrettoken123456789" not in redacted


def test_logger_stream_redaction():
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(RedactionFilter())

    test_logger = logging.getLogger("test_redaction")
    test_logger.handlers = [handler]
    test_logger.propagate = False
    test_logger.setLevel(logging.INFO)

    test_logger.info("Delivering otp: 948192 to +919123456789 with sig whsec_testsecret12345")

    output = stream.getvalue()
    assert "948192" not in output
    assert "+919123456789" not in output
    assert "****6789" in output
    assert "whsec_testsecret12345" not in output
