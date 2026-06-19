from typing import Optional

import phonenumbers


def normalize_phone(phone: str, default_region: str = "IN") -> Optional[str]:
    """Normalize a phone number to E.164 format."""
    try:
        parsed = phonenumbers.parse(phone, default_region)
        if phonenumbers.is_valid_number(parsed):
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except phonenumbers.NumberParseException:
        pass
    return None


def is_valid_phone(phone: str, default_region: str = "IN") -> bool:
    try:
        parsed = phonenumbers.parse(phone, default_region)
        return phonenumbers.is_valid_number(parsed)
    except phonenumbers.NumberParseException:
        return False


def get_country_code(phone: str) -> Optional[str]:
    try:
        parsed = phonenumbers.parse(phone, None)
        return phonenumbers.region_code_for_number(parsed)
    except phonenumbers.NumberParseException:
        return None
