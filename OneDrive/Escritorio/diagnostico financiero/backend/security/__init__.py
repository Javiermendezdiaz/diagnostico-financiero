"""
Security module — Encryption, breach management, key handling
GDPR Art. 32 — Encryption and pseudonymization
GDPR Art. 33-34 — Breach notification
"""

from .encryption import (
    DataEncryption,
    EncryptedString,
    set_encryption_context,
    clear_encryption_context,
)

__all__ = [
    "DataEncryption",
    "EncryptedString",
    "set_encryption_context",
    "clear_encryption_context",
]
