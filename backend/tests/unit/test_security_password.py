"""
Unit tests for password hashing utilities.
"""

import pytest

from src.notemesh.security.password import hash_password, needs_update, verify_password


class TestPasswordUtils:
    """Test password hashing and verification."""

    def test_hash_password(self):
        """Test password hashing."""
        password = "TestPassword123!"
        hashed = hash_password(password)

        # Hash should be different from plain password
        assert hashed != password

        # Hash should be a non-empty string
        assert isinstance(hashed, str)
        assert len(hashed) > 0

        # Hashing same password twice should give different results (due to salt)
        hashed2 = hash_password(password)
        assert hashed != hashed2

    def test_verify_password_correct(self):
        """Test verifying correct password."""
        password = "TestPassword123!"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test verifying incorrect password."""
        password = "TestPassword123!"
        wrong_password = "WrongPassword123!"
        hashed = hash_password(password)

        assert verify_password(wrong_password, hashed) is False

    def test_verify_password_empty(self):
        """Test verifying empty password."""
        password = "TestPassword123!"
        hashed = hash_password(password)

        assert verify_password("", hashed) is False

    def test_hash_empty_password(self):
        """Test hashing empty password."""
        # Should still work but not recommended in practice
        hashed = hash_password("")
        assert isinstance(hashed, str)
        assert verify_password("", hashed) is True

    def test_unicode_password(self):
        """Test hashing and verifying unicode passwords."""
        password = "Test密码123!🔐"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True
        assert verify_password("Test密码123!🔓", hashed) is False

    def test_long_password(self):
        """Test hashing very long passwords."""
        password = "a" * 1000  # 1000 character password
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True
        assert verify_password(password[:-1], hashed) is False

    def test_needs_update(self):
        """Test checking if password hash needs update."""
        password = "TestPassword123!"
        hashed = hash_password(password)

        # Fresh bcrypt hash should not need update
        assert needs_update(hashed) is False

        # Note: Testing with an old/weak hash would require creating
        # a hash with different settings, which is complex to mock

    def test_special_characters_password(self):
        """Test passwords with special characters."""
        passwords = [
            "Test@#$%^&*()123",
            "Test\n\r\t123",
            "Test'\"\\123",
            "Test<>?/|123",
        ]

        for password in passwords:
            hashed = hash_password(password)
            assert verify_password(password, hashed) is True
            assert verify_password(password + "x", hashed) is False
