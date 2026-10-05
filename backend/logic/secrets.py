"""Small encrypted-at-rest secret helper for provider credentials."""

from __future__ import annotations

import os

from cryptography.fernet import Fernet, InvalidToken


class SecretConfigError(RuntimeError):
    pass


def _fernet() -> Fernet:
    key = os.getenv("NEXUS_CONFIG_ENCRYPTION_KEY", "").strip()
    if not key:
        raise SecretConfigError(
            "NEXUS_CONFIG_ENCRYPTION_KEY is required to store provider keys"
        )
    try:
        return Fernet(key.encode("utf-8"))
    except (ValueError, TypeError) as exc:
        raise SecretConfigError("NEXUS_CONFIG_ENCRYPTION_KEY is not a valid Fernet key") from exc


def encrypt_secret(value: str) -> str:
    if not value:
        return ""
    token = _fernet().encrypt(value.encode("utf-8")).decode("ascii")
    return f"fernet:v1:{token}"


def decrypt_secret(value: str) -> str:
    if not value:
        return ""
    if not value.startswith("fernet:v1:"):
        # Legacy development rows may contain plaintext. They remain readable so
        # a deployment can migrate them through the admin update path.
        return value
    try:
        return _fernet().decrypt(value.removeprefix("fernet:v1:").encode("ascii")).decode(
            "utf-8"
        )
    except (InvalidToken, UnicodeDecodeError, ValueError) as exc:
        raise SecretConfigError("Stored provider key cannot be decrypted") from exc
