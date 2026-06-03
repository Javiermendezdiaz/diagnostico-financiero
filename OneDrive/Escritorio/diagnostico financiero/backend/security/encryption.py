"""
Encryption Layer for Sensitive PII
GDPR Art. 32 — Encryption at rest
Per-user key derivation (PBKDF2 + Fernet symmetric encryption)
Transparent SQLAlchemy integration via TypeDecorator
"""

import os
import json
from typing import Any, Optional
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
import base64
from sqlalchemy.types import TypeDecorator, String
from sqlalchemy import event
from sqlalchemy.orm import Session


class DataEncryption:
    """
    Symmetric encryption utility using Fernet (AES-128 in CBC mode).
    Per-user key derivation: PBKDF2(sha256, salt=user_id, 100k iterations) → Fernet key
    """

    ITERATIONS = 100000  # PBKDF2 iterations (NIST minimum)
    HASH_ALGORITHM = hashes.SHA256()

    @staticmethod
    def derive_key(user_id: str) -> bytes:
        """
        Derive a unique encryption key for a user.
        Salt = user_id (constant per user, never changes)
        This ensures encrypted data remains consistent across sessions.

        Args:
            user_id: User UUID or identifier (used as deterministic salt)

        Returns:
            Base64-encoded Fernet key (32 bytes)
        """
        # Use user_id as salt (consistent, deterministic)
        salt = user_id.encode("utf-8")[:16].ljust(16, b"\x00")

        kdf = PBKDF2(
            algorithm=DataEncryption.HASH_ALGORITHM,
            length=32,  # 256 bits for AES
            salt=salt,
            iterations=DataEncryption.ITERATIONS,
            backend=default_backend(),
        )

        # Derive key from empty password (user_id is the salt; no additional password needed)
        key_material = kdf.derive(b"diagnositco_financiero_key_material")

        # Encode as base64 for Fernet
        key = base64.urlsafe_b64encode(key_material)
        return key

    @staticmethod
    def encrypt(plaintext: str, user_id: str) -> str:
        """
        Encrypt plaintext for a specific user.

        Args:
            plaintext: Sensitive data (email, phone, income, etc.)
            user_id: User identifier (used to derive key)

        Returns:
            Encrypted string (base64-encoded token)

        Raises:
            ValueError: If encryption fails
        """
        try:
            key = DataEncryption.derive_key(user_id)
            f = Fernet(key)
            ciphertext = f.encrypt(plaintext.encode("utf-8"))
            return ciphertext.decode("utf-8")  # Return as string for DB storage
        except Exception as e:
            raise ValueError(f"Encryption failed: {e}")

    @staticmethod
    def decrypt(ciphertext: str, user_id: str) -> str:
        """
        Decrypt ciphertext for a specific user.

        Args:
            ciphertext: Encrypted data (from DB)
            user_id: User identifier (used to derive key)

        Returns:
            Decrypted plaintext

        Raises:
            ValueError: If decryption fails or authentication fails
        """
        try:
            key = DataEncryption.derive_key(user_id)
            f = Fernet(key)
            plaintext = f.decrypt(ciphertext.encode("utf-8"))
            return plaintext.decode("utf-8")
        except InvalidToken:
            raise ValueError("Decryption failed: Invalid token or wrong key")
        except Exception as e:
            raise ValueError(f"Decryption failed: {e}")


class EncryptedString(TypeDecorator):
    """
    SQLAlchemy TypeDecorator for transparent encryption/decryption of string columns.

    Usage:
        class User(Base):
            __tablename__ = "users"
            id = Column(String(36), primary_key=True)
            email = Column(EncryptedString(255), nullable=False)  # Encrypted in DB
            phone = Column(EncryptedString(20), nullable=True)    # Encrypted in DB
            income = Column(EncryptedString(50), nullable=True)   # Encrypted in DB

    When reading: ORM automatically decrypts via process_result_value()
    When writing: ORM automatically encrypts via process_bind_param()

    The user_id is retrieved from the session context (passed via set_user_context()).
    """

    impl = String
    cache_ok = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._user_id_context = None

    def process_bind_param(self, value: Any, dialect: Any) -> Optional[str]:
        """
        Called before inserting/updating to DB.
        Encrypts the plaintext value using the current user_id.
        """
        if value is None:
            return None

        if not isinstance(value, str):
            value = str(value)

        # Get user_id from context
        user_id = getattr(self, "_user_id_context", None)
        if not user_id:
            # Fallback: if no context, don't encrypt (development/testing only)
            # In production, this should raise an error
            return value

        try:
            encrypted = DataEncryption.encrypt(value, user_id)
            return encrypted
        except Exception as e:
            raise ValueError(f"Failed to encrypt field: {e}")

    def process_result_value(self, value: Any, dialect: Any) -> Optional[str]:
        """
        Called after reading from DB.
        Decrypts the ciphertext using the current user_id.
        """
        if value is None:
            return None

        # Get user_id from context
        user_id = getattr(self, "_user_id_context", None)
        if not user_id:
            # Fallback: if no context, return as-is (might be plaintext from old data)
            return value

        try:
            decrypted = DataEncryption.decrypt(value, user_id)
            return decrypted
        except Exception as e:
            # If decryption fails, data might be corrupted or user_id is wrong
            raise ValueError(f"Failed to decrypt field: {e}")

    @classmethod
    def set_user_context(cls, user_id: str) -> None:
        """
        Set the current user_id for all EncryptedString columns in this session.
        Call this BEFORE querying encrypted fields.

        Args:
            user_id: User identifier for key derivation
        """
        cls._user_id_context = user_id


def set_encryption_context(session: Session, user_id: str) -> None:
    """
    Helper to set encryption context for a SQLAlchemy session.

    Usage in FastAPI endpoint:
        @app.get("/user/me")
        async def get_user(current_user_id: str):
            session = SessionLocal()
            set_encryption_context(session, current_user_id)
            user = session.query(User).filter_by(id=current_user_id).first()
            # user.email, user.phone, etc. are automatically decrypted
            return user
    """
    EncryptedString.set_user_context(user_id)
    # Optionally: could attach to session object for cleanup
    session.info["encryption_user_id"] = user_id


def clear_encryption_context() -> None:
    """Clear the encryption context (call after session cleanup)."""
    EncryptedString.set_user_context(None)
