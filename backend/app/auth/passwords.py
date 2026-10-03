"""Password hashing with Argon2id (BACKEND.md § 8.3)."""

from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

PASSWORD_MIN = 8
PASSWORD_MAX = 128

hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """Return an encoded Argon2id hash. The salt and parameters travel inside it."""
    return hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    """Whether *password* matches *password_hash*. Malformed hashes never match."""
    try:
        return hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False
