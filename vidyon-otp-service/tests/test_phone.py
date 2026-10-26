import pytest
from app.phone import validate_india_mobile, normalise, mask


def test_valid_e164_indian_mobile():
    phone = "+919876543210"
    assert validate_india_mobile(phone) == "+919876543210"


def test_normalise_direct_call():
    assert normalise(" 9876543210 ") == "+919876543210"
    assert normalise("09876543210") == "+919876543210"


def test_us_phone_rejected():
    phone = "+14155552671"
    with pytest.raises(ValueError):
        validate_india_mobile(phone)


def test_landline_rejected():
    phone = "04422345678"
    with pytest.raises(ValueError):
        validate_india_mobile(phone)


def test_bare_10_digits_autofixed():
    phone = "9876543210"
    assert validate_india_mobile(phone) == "+919876543210"


def test_spaces_and_dashes_normalised():
    phone = "+91 98765 43210"
    assert validate_india_mobile(phone) == "+919876543210"

    phone2 = "+91-98765-43210"
    assert validate_india_mobile(phone2) == "+919876543210"


def test_phone_masking():
    assert mask("+919876543210") == "****3210"
    assert mask("9876543210") == "****3210"
    assert mask("12") == "****"
