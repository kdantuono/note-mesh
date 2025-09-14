"""Password hashing utilities."""

from passlib.context import CryptContext

# Password hashing context
# Use bcrypt_sha256 to avoid bcrypt's 72-byte truncation issue on long passwords
# This pre-hashes with SHA-256 before applying bcrypt.
pwd_context = CryptContext(schemes=["bcrypt_sha256"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def needs_update(hashed_password: str) -> bool:
    """Check if password hash needs updating."""
    return pwd_context.needs_update(hashed_password)
