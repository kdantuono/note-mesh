"""Unit tests for security/password.py"""

from src.notemesh.security.password import hash_password, verify_password, needs_update


def test_hash_and_verify_roundtrip():
    pwd = "StrongPassw0rd!"
    h = hash_password(pwd)
    assert h != pwd
    assert verify_password(pwd, h) is True
    assert verify_password("wrong", h) is False


def test_needs_update_returns_bool():
    pwd = "AnotherPass123!"
    h = hash_password(pwd)
    assert isinstance(needs_update(h), bool)
