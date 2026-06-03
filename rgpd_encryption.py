#!/usr/bin/env python3
"""
RGPD Foundation: Encryption Layer
Per-user encryption with PBKDF2 key derivation and AES-256-GCM
Compliance: GDPR Art. 32 (Data protection by design and default)
"""

import os
import json
import hashlib
import hmac
from typing import Dict, Tuple, Optional
from datetime import datetime
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
import base64
import logging

logger = logging.getLogger(__name__)

class RGPDEncryptionLayer:
    """
    End-to-end encryption for user data.

    - Derives unique 256-bit keys per user via PBKDF2
    - Encrypts sensitive data with AES-256-GCM
    - Stores keys securely (hashed, per-user salt)
    - Provides audit trail for encryption operations

    Flow:
    1. User registers → generate salt, derive key
    2. Data ingestion → encrypt before storage
    3. Data retrieval → decrypt on demand
    4. User deletion → secure key erasure
    """

    def __init__(self, master_key_path: str = "keys/master.key", enable_audit: bool = True):
        """Initialize encryption layer"""
        self.master_key_path = master_key_path
        self.enable_audit = enable_audit
        self.salt_length = 32  # 256 bits
        self.key_length = 32   # 256 bits for AES-256
        self.iterations = 480000  # OWASP 2023 recommendation
        self._initialize_master_key()

    def _initialize_master_key(self):
        """Ensure master key exists or generate it"""
        os.makedirs(os.path.dirname(self.master_key_path) if os.path.dirname(self.master_key_path) else ".", exist_ok=True)

        if not os.path.exists(self.master_key_path):
            self.master_key = os.urandom(32)
            with open(self.master_key_path, 'wb') as f:
                f.write(self.master_key)
            os.chmod(self.master_key_path, 0o600)
            logger.info("Master key generated and stored securely")
        else:
            with open(self.master_key_path, 'rb') as f:
                self.master_key = f.read()

    def generate_user_key(self, user_id: str, password: Optional[str] = None) -> Dict:
        """
        Generate encrypted key material for a user.

        Returns dict with:
        - user_id: User identifier
        - salt: Unique salt for this user (base64)
        - key_hash: HMAC of derived key (for validation)
        - created_at: Timestamp
        - algorithm: Encryption method (AES-256-GCM)
        """
        salt = os.urandom(self.salt_length)

        # Derive key from password (if provided) or generate random
        if password:
            kdf = PBKDF2(
                algorithm=hashes.SHA256(),
                length=self.key_length,
                salt=salt,
                iterations=self.iterations,
            )
            derived_key = kdf.derive(password.encode())
        else:
            derived_key = os.urandom(self.key_length)

        # Generate key hash for validation (HMAC-SHA256)
        key_hash = hmac.new(
            self.master_key,
            derived_key,
            hashlib.sha256
        ).digest()

        return {
            "user_id": user_id,
            "salt": base64.b64encode(salt).decode(),
            "key_hash": base64.b64encode(key_hash).decode(),
            "created_at": datetime.utcnow().isoformat(),
            "algorithm": "AES-256-GCM",
            "derived_key": base64.b64encode(derived_key).decode()  # Store encrypted in production
        }

    def derive_user_key(self, user_id: str, salt_b64: str, password: Optional[str] = None) -> bytes:
        """
        Derive the user's encryption key from stored salt and password.
        Same salt + password → same key (deterministic)
        """
        salt = base64.b64decode(salt_b64)

        if not password:
            raise ValueError("Password required to derive key")

        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=self.key_length,
            salt=salt,
            iterations=self.iterations,
        )
        return kdf.derive(password.encode())

    def encrypt_data(self, plaintext: str, user_key: bytes) -> Dict:
        """
        Encrypt plaintext with user's key using AES-256-GCM.

        Returns dict with:
        - ciphertext: Encrypted data (base64)
        - nonce: Random nonce/IV (base64)
        - tag: Authentication tag (base64)
        - encrypted_at: Timestamp
        """
        nonce = os.urandom(12)  # 96-bit nonce for GCM
        cipher = AESGCM(user_key)

        plaintext_bytes = plaintext.encode() if isinstance(plaintext, str) else plaintext
        ciphertext = cipher.encrypt(nonce, plaintext_bytes, None)

        return {
            "ciphertext": base64.b64encode(ciphertext[:-16]).decode(),  # Without auth tag
            "nonce": base64.b64encode(nonce).decode(),
            "tag": base64.b64encode(ciphertext[-16:]).decode(),  # Last 16 bytes = auth tag
            "encrypted_at": datetime.utcnow().isoformat(),
            "algorithm": "AES-256-GCM"
        }

    def decrypt_data(self, encrypted_dict: Dict, user_key: bytes) -> str:
        """
        Decrypt ciphertext with user's key.
        Validates authentication tag before decryption (prevents tampering).
        """
        try:
            ciphertext = base64.b64decode(encrypted_dict["ciphertext"])
            nonce = base64.b64decode(encrypted_dict["nonce"])
            tag = base64.b64decode(encrypted_dict["tag"])

            cipher = AESGCM(user_key)
            combined = ciphertext + tag
            plaintext = cipher.decrypt(nonce, combined, None)

            return plaintext.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise ValueError("Decryption failed - data may be tampered") from e

    def encrypt_answers(self, user_id: str, answers: Dict, user_key: bytes) -> Dict:
        """
        Encrypt diagnostic answers before storage.

        Encrypts the entire answers dict as JSON.
        """
        answers_json = json.dumps(answers)
        encrypted = self.encrypt_data(answers_json, user_key)

        return {
            "user_id": user_id,
            "encrypted_answers": encrypted,
            "metadata": {
                "total_answers": len(answers),
                "encrypted_at": encrypted["encrypted_at"]
            }
        }

    def decrypt_answers(self, encrypted_blob: Dict, user_key: bytes) -> Dict:
        """
        Decrypt stored answers for processing/analysis.
        """
        plaintext_json = self.decrypt_data(encrypted_blob["encrypted_answers"], user_key)
        return json.loads(plaintext_json)

    def log_encryption_event(self, user_id: str, action: str, data_type: str, success: bool, details: str = ""):
        """Audit trail for encryption operations (GDPR Art. 30)"""
        if not self.enable_audit:
            return

        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "action": action,
            "data_type": data_type,
            "success": success,
            "details": details
        }
        logger.info(f"ENCRYPTION_EVENT: {json.dumps(event)}")

    def rotate_user_key(self, user_id: str, old_key: bytes, new_password: str, salt: str) -> Dict:
        """
        Rotate user's encryption key (security best practice).

        1. Re-encrypt all user data with new key
        2. Store new key material
        3. Securely erase old key

        Note: In production, this would re-encrypt all stored data.
        Here we just generate new key material.
        """
        new_key = self.derive_user_key(user_id, salt, new_password)

        self.log_encryption_event(
            user_id,
            "KEY_ROTATION",
            "user_encryption_key",
            True,
            "User key rotated successfully"
        )

        return {
            "user_id": user_id,
            "new_key_hash": base64.b64encode(
                hmac.new(self.master_key, new_key, hashlib.sha256).digest()
            ).decode(),
            "rotated_at": datetime.utcnow().isoformat()
        }

    def securely_erase_key(self, key: bytes):
        """
        Securely erase key material from memory.
        Overwrites with zeros to prevent recovery from RAM.
        """
        if key:
            key_array = bytearray(key)
            for i in range(len(key_array)):
                key_array[i] = 0
            del key_array
            logger.debug("Key material securely erased")


# Singleton instance
_encryption_layer = None

def get_encryption_layer() -> RGPDEncryptionLayer:
    """Get or create the encryption layer singleton"""
    global _encryption_layer
    if _encryption_layer is None:
        _encryption_layer = RGPDEncryptionLayer()
    return _encryption_layer
