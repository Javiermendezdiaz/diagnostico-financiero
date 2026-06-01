#!/usr/bin/env python3
"""
RGPD Foundation: Consent Management
Tracks user consents, withdrawals, and consent history
Compliance: GDPR Art. 7 (Conditions for consent)
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)

class ConsentType(str, Enum):
    """GDPR consent categories"""
    PROCESSING = "processing"  # Process diagnostic answers
    ANALYTICS = "analytics"    # Analytics and aggregate insights
    MARKETING = "marketing"    # Marketing communications
    PROFILING = "profiling"    # Automated profiling/recommendations
    THIRD_PARTY = "third_party"  # Share with third parties
    COOKIE = "cookie"          # Cookie/tracking technologies


class ConsentManager:
    """
    Manage user consents in compliance with GDPR Art. 7.

    - Explicit opt-in (no pre-ticked boxes)
    - Granular consents per purpose
    - Audit trail of all consent changes
    - Easy withdrawal (one click)
    - Proof of consent (timestamp + fingerprint)

    Storage: In production, store in database with encryption.
    Here: In-memory dict (demo).
    """

    def __init__(self):
        self.consents = {}  # {user_id: {consent_type: {...}}}
        self.consent_history = {}  # {user_id: [{...}, ...]}

    def request_consent(
        self,
        user_id: str,
        consent_types: List[ConsentType],
        language: str = "es"
    ) -> Dict:
        """
        Generate consent request with descriptions.
        Returns HTML/text for display to user.
        """
        descriptions = {
            ConsentType.PROCESSING: {
                "es": "Procesar tus respuestas para generar diagnóstico",
                "en": "Process your answers to generate diagnostic"
            },
            ConsentType.ANALYTICS: {
                "es": "Analizar datos agregados para mejorar el servicio",
                "en": "Analyze aggregated data to improve service"
            },
            ConsentType.MARKETING: {
                "es": "Enviar información sobre productos y servicios",
                "en": "Send information about products and services"
            },
            ConsentType.PROFILING: {
                "es": "Crear perfil automático basado en respuestas",
                "en": "Create automatic profile based on answers"
            },
            ConsentType.THIRD_PARTY: {
                "es": "Compartir datos con terceros de confianza",
                "en": "Share data with trusted third parties"
            },
            ConsentType.COOKIE: {
                "es": "Usar cookies para mejorar experiencia",
                "en": "Use cookies to improve experience"
            }
        }

        request = {
            "user_id": user_id,
            "consents": []
        }

        for consent_type in consent_types:
            request["consents"].append({
                "type": consent_type.value,
                "description": descriptions.get(consent_type, {}).get(language, ""),
                "required": consent_type == ConsentType.PROCESSING,  # Only processing is mandatory
                "opted_in": False  # Default: no consent
            })

        return request

    def save_consent(
        self,
        user_id: str,
        consent_data: Dict,
        ip_address: str = "",
        user_agent: str = ""
    ) -> Dict:
        """
        Record user's consent choices with audit trail.

        consent_data format:
        {
            "processing": true,
            "analytics": false,
            "marketing": false,
            ...
        }
        """
        if user_id not in self.consents:
            self.consents[user_id] = {}
            self.consent_history[user_id] = []

        timestamp = datetime.utcnow().isoformat()

        # Store current consents
        for consent_type, value in consent_data.items():
            self.consents[user_id][consent_type] = {
                "value": value,
                "recorded_at": timestamp,
                "ip_address": ip_address[-8:] if ip_address else "",  # Last octet only (privacy)
                "user_agent_hash": hash(user_agent) if user_agent else ""  # Hash, not full UA
            }

        # Log to history
        self.consent_history[user_id].append({
            "action": "CONSENT_GIVEN",
            "timestamp": timestamp,
            "consents": consent_data.copy(),
            "ip_address": ip_address[-8:] if ip_address else "",
            "user_agent_hash": hash(user_agent) if user_agent else ""
        })

        logger.info(f"Consent saved for user {user_id}: {consent_data}")

        return {
            "user_id": user_id,
            "recorded_at": timestamp,
            "consents": self.consents[user_id]
        }

    def withdraw_consent(self, user_id: str, consent_type: ConsentType) -> Dict:
        """
        Withdraw consent for a specific purpose.
        Immediate effect - no further processing for withdrawn consent.
        """
        if user_id not in self.consents:
            raise ValueError(f"No consent record for user {user_id}")

        timestamp = datetime.utcnow().isoformat()

        # Remove consent
        if consent_type.value in self.consents[user_id]:
            del self.consents[user_id][consent_type.value]

        # Log withdrawal
        self.consent_history[user_id].append({
            "action": "CONSENT_WITHDRAWN",
            "timestamp": timestamp,
            "consent_type": consent_type.value
        })

        logger.info(f"Consent withdrawn for user {user_id}: {consent_type.value}")

        return {
            "user_id": user_id,
            "withdrawn_at": timestamp,
            "consent_type": consent_type.value
        }

    def withdraw_all_consent(self, user_id: str) -> Dict:
        """
        Withdraw all consents (GDPR right to withdraw).
        """
        if user_id not in self.consents:
            raise ValueError(f"No consent record for user {user_id}")

        timestamp = datetime.utcnow().isoformat()

        # Clear all consents
        self.consents[user_id] = {}

        # Log full withdrawal
        self.consent_history[user_id].append({
            "action": "ALL_CONSENT_WITHDRAWN",
            "timestamp": timestamp
        })

        logger.info(f"All consent withdrawn for user {user_id}")

        return {
            "user_id": user_id,
            "withdrawn_at": timestamp,
            "all_consent_revoked": True
        }

    def has_consent(self, user_id: str, consent_type: ConsentType) -> bool:
        """Check if user has given consent for specific purpose"""
        if user_id not in self.consents:
            return False

        consent_value = self.consents[user_id].get(consent_type.value, {})
        return consent_value.get("value", False) if isinstance(consent_value, dict) else consent_value

    def get_user_consents(self, user_id: str) -> Dict:
        """Return user's current consent status"""
        if user_id not in self.consents:
            return {"user_id": user_id, "consents": {}}

        return {
            "user_id": user_id,
            "consents": self.consents.get(user_id, {}),
            "last_updated": self.consent_history[user_id][-1]["timestamp"] if self.consent_history.get(user_id) else ""
        }

    def get_consent_history(self, user_id: str) -> List[Dict]:
        """Return audit trail of all consent changes"""
        return self.consent_history.get(user_id, [])

    def export_consent_proof(self, user_id: str) -> Dict:
        """
        Export proof of consent for compliance/legal purposes.
        Can be presented to regulators/courts.
        """
        if user_id not in self.consents:
            raise ValueError(f"No consent record for user {user_id}")

        return {
            "user_id": user_id,
            "current_consents": self.consents[user_id],
            "history": self.consent_history[user_id],
            "exported_at": datetime.utcnow().isoformat(),
            "legal_note": "This document proves consent was obtained in compliance with GDPR Art. 7"
        }


# Singleton instance
_consent_manager = None

def get_consent_manager() -> ConsentManager:
    """Get or create the consent manager singleton"""
    global _consent_manager
    if _consent_manager is None:
        _consent_manager = ConsentManager()
    return _consent_manager
