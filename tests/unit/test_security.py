"""Unit tests for JWT and password hashing utilities."""

import time

import pytest
from jose import JWTError

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


class TestPasswordHashing:
    def test_hash_is_not_plain(self):
        hashed = hash_password("mysecret")
        assert hashed != "mysecret"

    def test_verify_correct_password(self):
        hashed = hash_password("mysecret")
        assert verify_password("mysecret", hashed) is True

    def test_verify_wrong_password(self):
        hashed = hash_password("mysecret")
        assert verify_password("wrongpassword", hashed) is False

    def test_two_hashes_of_same_password_differ(self):
        """bcrypt uses random salt — same input produces different hashes."""
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2


class TestJWT:
    def test_access_token_decodes_correctly(self):
        token, jti = create_access_token("user-123")
        payload = decode_token(token)
        assert payload["sub"] == "user-123"
        assert payload["type"] == "access"
        assert payload["jti"] == jti

    def test_refresh_token_has_correct_type(self):
        token, _ = create_refresh_token("user-456")
        payload = decode_token(token)
        assert payload["type"] == "refresh"

    def test_tampered_token_raises_error(self):
        token, _ = create_access_token("user-123")
        tampered = token[:-5] + "XXXXX"
        with pytest.raises(JWTError):
            decode_token(tampered)

    def test_access_and_refresh_tokens_have_different_jtis(self):
        _, jti_access = create_access_token("user-123")
        _, jti_refresh = create_refresh_token("user-123")
        assert jti_access != jti_refresh
