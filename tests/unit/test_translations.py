import pytest

from app.localization.translations import get_supported_locales, translate


def test_translate_english():
    result = translate("transaction_success_body", locale="en", amount="1000", recipient="John")
    assert "₹1000" in result
    assert "John" in result


def test_translate_hindi():
    result = translate("transaction_success_body", locale="hi", amount="1000", recipient="John")
    assert "₹1000" in result
    assert "John" in result


def test_translate_fallback_to_english():
    # 'fr' is not supported — should fall back to English
    result = translate("welcome_title", locale="fr")
    en_result = translate("welcome_title", locale="en")
    assert result == en_result


def test_translate_missing_key():
    # Unknown key should return the key itself
    result = translate("nonexistent_key_xyz", locale="en")
    assert result == "nonexistent_key_xyz"


def test_translate_with_missing_variable():
    # Missing variable — should return template without substitution
    result = translate("otp_body", locale="en")
    assert result  # Should not raise; returns template as-is


def test_supported_locales():
    locales = get_supported_locales()
    assert "en" in locales
    assert "hi" in locales
    assert len(locales) >= 2


def test_translate_otp_english():
    result = translate(
        "otp_body",
        locale="en",
        otp="123456",
        purpose="login",
        validity="5",
    )
    assert "123456" in result
    assert "login" in result
    assert "5" in result


def test_translate_otp_hindi():
    result = translate(
        "otp_body",
        locale="hi",
        otp="123456",
        purpose="login",
        validity="5",
    )
    assert "123456" in result


def test_all_keys_exist_in_hindi():
    from app.localization.translations import TRANSLATIONS
    en_keys = set(TRANSLATIONS["en"].keys())
    hi_keys = set(TRANSLATIONS["hi"].keys())
    missing = en_keys - hi_keys
    assert len(missing) == 0, f"Hindi translations missing keys: {missing}"
