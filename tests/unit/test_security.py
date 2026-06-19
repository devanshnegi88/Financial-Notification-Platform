from uuid import uuid4

import pytest

from app.core.constants import UserRole
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    is_token_expired,
    verify_password,
)


def test_password_hash_and_verify():
    password = "SecurePass123!"
    hashed = get_password_hash(password)
    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("WrongPass", hashed)


def test_create_access_token():
    user_id = uuid4()
    token = create_access_token(user_id, UserRole.USER)
    payload = decode_token(token)
    assert payload["sub"] == str(user_id)
    assert payload["role"] == UserRole.USER
    assert payload["type"] == "access"


def test_create_refresh_token():
    user_id = uuid4()
    token = create_refresh_token(user_id, UserRole.ADMIN)
    payload = decode_token(token)
    assert payload["sub"] == str(user_id)
    assert payload["type"] == "refresh"


def test_decode_invalid_token():
    with pytest.raises(ValueError):
        decode_token("invalid.token.here")


def test_token_not_expired():
    user_id = uuid4()
    token = create_access_token(user_id, UserRole.USER)
    payload = decode_token(token)
    assert not is_token_expired(payload)


def test_token_expired_payload():
    expired_payload = {"exp": 0}
    assert is_token_expired(expired_payload)


def test_token_missing_exp():
    payload = {}
    assert is_token_expired(payload)
