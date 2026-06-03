"""
SQLAlchemy ORM Models for Diagnóstico Financiero
GDPR-compliant schema with immutable audit trails
"""

from .legal_basis import (
    Base,
    LegalBasis,
    DataProcessingRecord,
    DataRetentionPolicy,
    DEFAULT_RETENTION_POLICIES,
)

from .consent import (
    ConsentType,
    ConsentStatus,
    UserConsent,
    ConsentAuditLog,
)

__all__ = [
    "Base",
    "LegalBasis",
    "DataProcessingRecord",
    "DataRetentionPolicy",
    "DEFAULT_RETENTION_POLICIES",
    "ConsentType",
    "ConsentStatus",
    "UserConsent",
    "ConsentAuditLog",
]
