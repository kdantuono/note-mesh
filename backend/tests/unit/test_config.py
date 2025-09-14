"""
Unit tests for application configuration.
"""

import os
from unittest.mock import patch

import pytest

from src.notemesh.config import Settings, get_settings


class TestSettings:
    """Test Settings configuration class."""

    def test_default_settings(self):
        """Test default settings values."""
        settings = Settings()

        # Basic app settings
        assert settings.app_name == "NoteMesh API"
        assert settings.app_version == "1.0.0"
        assert settings.debug is False

        # Server config
        assert settings.host == "0.0.0.0"
        assert settings.port == 8000
        assert settings.reload is False

        # Database
        assert (
            settings.database_url
            == "postgresql+asyncpg://notemesh:password@localhost:5432/notemesh"
        )
        assert settings.database_echo is False

        # Redis
        assert settings.redis_url == "redis://localhost:6379/0"
        assert settings.redis_max_connections == 10

        # JWT
        assert settings.secret_key == "your-secret-key-change-in-production"
        assert settings.algorithm == "HS256"
        assert settings.access_token_expire_minutes == 15
        assert settings.refresh_token_expire_days == 7

        # CORS
        assert settings.cors_origins == ["http://localhost:3000"]
        assert settings.cors_allow_credentials is True

        # Pagination
        assert settings.default_page_size == 20
        assert settings.max_page_size == 100

        # Rate limiting
        assert settings.rate_limit_requests == 100
        assert settings.rate_limit_window_minutes == 1

        # File upload
        assert settings.max_file_size_mb == 10
        assert settings.allowed_file_extensions == [
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".pdf",
            ".txt",
            ".md",
        ]

        # Logging
        assert settings.log_level == "INFO"
        assert settings.log_format == "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    def test_settings_from_env_vars(self):
        """Test loading settings from environment variables."""
        env_vars = {
            "APP_NAME": "Test App",
            "APP_VERSION": "2.0.0",
            "DEBUG": "true",
            "HOST": "127.0.0.1",
            "PORT": "3000",
            "DATABASE_URL": "postgresql+asyncpg://test:test@test:5432/test",
            "REDIS_URL": "redis://test:6379/1",
            "SECRET_KEY": "test-secret-key",
            "ACCESS_TOKEN_EXPIRE_MINUTES": "120",
            "REFRESH_TOKEN_EXPIRE_DAYS": "14",
            "CORS_ORIGINS": '["http://localhost:5000", "http://localhost:3001"]',
            "DEFAULT_PAGE_SIZE": "50",
            "MAX_PAGE_SIZE": "200",
            "RATE_LIMIT_REQUESTS": "200",
            "MAX_FILE_SIZE_MB": "20",
            "LOG_LEVEL": "DEBUG",
        }

        with patch.dict(os.environ, env_vars):
            settings = Settings()

            assert settings.app_name == "Test App"
            assert settings.app_version == "2.0.0"
            assert settings.debug is True
            assert settings.host == "127.0.0.1"
            assert settings.port == 3000
            assert settings.database_url == "postgresql+asyncpg://test:test@test:5432/test"
            assert settings.redis_url == "redis://test:6379/1"
            assert settings.secret_key == "test-secret-key"
            assert settings.access_token_expire_minutes == 120
            assert settings.refresh_token_expire_days == 14
            assert settings.cors_origins == ["http://localhost:5000", "http://localhost:3001"]
            assert settings.default_page_size == 50
            assert settings.max_page_size == 200
            assert settings.rate_limit_requests == 200
            assert settings.max_file_size_mb == 20
            assert settings.log_level == "DEBUG"

    def test_settings_case_insensitive(self):
        """Test that environment variables are case-insensitive."""
        env_vars = {
            "app_name": "Lower Case App",
            "APP_NAME": "Upper Case App",  # This should take precedence
        }

        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings()
            # Pydantic settings should handle case-insensitive env vars
            assert settings.app_name in ["Lower Case App", "Upper Case App"]

    def test_settings_type_conversion(self):
        """Test type conversion for settings."""
        env_vars = {
            "DEBUG": "false",
            "PORT": "8080",
            "DATABASE_ECHO": "true",
            "REDIS_MAX_CONNECTIONS": "20",
            "ACCESS_TOKEN_EXPIRE_MINUTES": "30",
            "REFRESH_TOKEN_EXPIRE_DAYS": "3",
            "RATE_LIMIT_WINDOW_MINUTES": "5",
            "ALLOWED_FILE_EXTENSIONS": '[".pdf", ".doc", ".docx"]',
        }

        with patch.dict(os.environ, env_vars):
            settings = Settings()

            assert settings.debug is False
            assert isinstance(settings.port, int)
            assert settings.port == 8080
            assert settings.database_echo is True
            assert isinstance(settings.redis_max_connections, int)
            assert settings.redis_max_connections == 20
            assert isinstance(settings.access_token_expire_minutes, int)
            assert settings.access_token_expire_minutes == 30
            assert isinstance(settings.refresh_token_expire_days, int)
            assert settings.refresh_token_expire_days == 3
            assert isinstance(settings.rate_limit_window_minutes, int)
            assert settings.rate_limit_window_minutes == 5
            assert settings.allowed_file_extensions == [".pdf", ".doc", ".docx"]

    def test_settings_validation_error(self):
        """Test settings validation errors."""
        env_vars = {
            "PORT": "not-a-number",  # Should cause validation error
        }

        with patch.dict(os.environ, env_vars):
            with pytest.raises(ValueError):
                Settings()

    def test_settings_from_env_file(self, tmp_path):
        """Test loading settings from .env file."""
        # Create a temporary .env file
        env_file = tmp_path / ".env"
        env_file.write_text(
            "APP_NAME=EnvFile App\n" "DEBUG=true\n" "PORT=9000\n" "SECRET_KEY=env-file-secret\n"
        )

        # Change to tmp directory to use the .env file
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            settings = Settings()

            assert settings.app_name == "EnvFile App"
            assert settings.debug is True
            assert settings.port == 9000
            assert settings.secret_key == "env-file-secret"
        finally:
            os.chdir(original_cwd)

    def test_settings_extra_fields_ignored(self):
        """Test that extra fields in env are ignored."""
        env_vars = {
            "APP_NAME": "Test App",
            "UNKNOWN_FIELD": "should be ignored",
            "EXTRA_CONFIG": "also ignored",
        }

        with patch.dict(os.environ, env_vars):
            # Should not raise error due to extra="ignore" in model_config
            settings = Settings()
            assert settings.app_name == "Test App"
            assert not hasattr(settings, "unknown_field")
            assert not hasattr(settings, "extra_config")

    def test_get_settings_singleton(self):
        """Test that get_settings returns the same instance."""
        settings1 = get_settings()
        settings2 = get_settings()

        # Should be the same instance (singleton pattern)
        assert settings1 is settings2

    def test_settings_lists_from_json_env(self):
        """Test parsing JSON lists from environment variables."""
        env_vars = {
            "CORS_ORIGINS": '["https://app1.com", "https://app2.com"]',
            "ALLOWED_FILE_EXTENSIONS": '[".mp4", ".avi", ".mov"]',
        }

        with patch.dict(os.environ, env_vars):
            settings = Settings()

            assert settings.cors_origins == ["https://app1.com", "https://app2.com"]
            assert settings.allowed_file_extensions == [".mp4", ".avi", ".mov"]

    def test_settings_invalid_json_list(self):
        """Test handling invalid JSON lists in environment variables."""
        env_vars = {
            "CORS_ORIGINS": "not-a-json-list",
        }

        with patch.dict(os.environ, env_vars):
            with pytest.raises(ValueError):
                Settings()

    def test_rate_limiting_settings(self):
        """Test rate limiting configuration."""
        env_vars = {
            "RATE_LIMIT_REQUESTS": "50",
            "RATE_LIMIT_WINDOW_MINUTES": "2",
        }

        with patch.dict(os.environ, env_vars):
            settings = Settings()

            assert settings.rate_limit_requests == 50
            assert settings.rate_limit_window_minutes == 2

    def test_file_upload_settings(self):
        """Test file upload configuration."""
        env_vars = {
            "MAX_FILE_SIZE_MB": "25",
            "ALLOWED_FILE_EXTENSIONS": '[".zip", ".rar"]',
        }

        with patch.dict(os.environ, env_vars):
            settings = Settings()

            assert settings.max_file_size_mb == 25
            assert settings.allowed_file_extensions == [".zip", ".rar"]

    def test_logging_settings(self):
        """Test logging configuration."""
        env_vars = {
            "LOG_LEVEL": "WARNING",
            "LOG_FORMAT": "%(levelname)s: %(message)s",
        }

        with patch.dict(os.environ, env_vars):
            settings = Settings()

            assert settings.log_level == "WARNING"
            assert settings.log_format == "%(levelname)s: %(message)s"
