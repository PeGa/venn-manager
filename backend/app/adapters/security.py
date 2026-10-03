"""Password hashing and session tokens (BACKEND.md § 8.3, § 8.5)."""

from __future__ import annotations

import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError


class Argon2Hasher:
    """`PasswordHasher` port with Argon2id. Salt and parameters live in each hash."""

    def __init__(self, hasher: PasswordHasher | None = None) -> None:
        self.hasher = hasher or PasswordHasher()

    def hash(self, password: str) -> str:
        return self.hasher.hash(password)

    def verify(self, password_hash: str, password: str) -> bool:
        try:
            return self.hasher.verify(password_hash, password)
        except (VerificationError, InvalidHashError):
            return False


class SecretTokens:
    """`TokenGenerator` port: 32 random bytes, stored as a SHA-256 digest."""

    def new_token(self) -> str:
        return secrets.token_urlsafe(32)

    def digest(self, token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()
