"""
Consent Management Models
GDPR Art. 7 — Conditions for consent (freely given, specific, informed, unambiguous)
GDPR Art. 17 — Right to erasure triggered by consent withdrawal
"""

from enum import Enum
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Boolean, Enum as SQLEnum, Index, ForeignKey
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func
import uuid

Base = declarative_base()


class ConsentType(str, Enum):
    """Types of consent we manage."""
    PRIVACY_POLICY = "PRIVACY_POLICY"  # Art. 13-14 transparency
    MARKETING = "MARKETING"  # Marketing communications
    THIRD_PARTY_SHARING = "THIRD_PARTY_SHARING"  # Share with processors/brokers
    DATA_ANALYTICS = "DATA_ANALYTICS"  # Analytics & aggregation
    LEAD_GENERATION = "LEAD_GENERATION"  # Anonymized lead gen (if user opts in)


class ConsentStatus(str, Enum):
    """Consent lifecycle."""
    PENDING = "PENDING"  # Shown but not responded
    GRANTED = "GRANTED"  # User explicitly granted
    WITHDRAWN = "WITHDRAWN"  # User explicitly withdrew
    EXPIRED = "EXPIRED"  # Consent period expired (if applicable)


class UserConsent(Base):
    """
    GDPR Art. 7 — Record of Consent
    Every consent grant/withdrawal is logged with proof.
    """
    __tablename__ = "user_consents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(255), nullable=False, index=True)

    # What are we asking consent for?
    consent_type = Column(SQLEnum(ConsentType), nullable=False, index=True)
    status = Column(SQLEnum(ConsentStatus), nullable=False, index=True, default=ConsentStatus.PENDING)

    # Proof of consent (GDPR Art. 7(4) — burden of proof on controller)
    privacy_policy_version = Column(String(20), nullable=True)  # e.g., "v2.1", "2026-05-29"
    privacy_policy_accepted = Column(Boolean, nullable=False, default=False)  # Must acknowledge privacy policy
    privacy_policy_url = Column(String(500), nullable=True)  # Link to version they accepted

    # GDPR transparency requirements (Art. 13-14)
    text_presented = Column(Text, nullable=False)  # Exact text shown to user (for dispute resolution)
    consent_mechanism = Column(String(50), nullable=False)  # "CHECKBOX", "EXPLICIT_BUTTON", "CONSENT_FORM"

    # Audit trail
    granted_at = Column(DateTime(timezone=True), nullable=True)  # When consent was given
    granted_ip = Column(String(45), nullable=True)  # IPv4/IPv6 for forensics
    granted_user_agent = Column(String(500), nullable=True)  # Browser/client

    withdrawn_at = Column(DateTime(timezone=True), nullable=True)  # When withdrawn
    withdrawn_reason = Column(String(200), nullable=True)  # Why user withdrew (optional explanation)
    withdrawn_ip = Column(String(45), nullable=True)

    # Automatic expiration (optional, per data category retention policy)
    expires_at = Column(DateTime(timezone=True), nullable=True)  # When consent auto-expires
    is_expired = Column(Boolean, default=False, index=True)

    # Notes
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_user_consent_status", "user_id", "consent_type", "status"),
        Index("idx_user_consent_grants", "user_id", "status", "granted_at"),
    )

    def __repr__(self):
        return f"<UserConsent(user_id={self.user_id}, type={self.consent_type.value}, status={self.status.value})>"


class ConsentAuditLog(Base):
    """
    GDPR Art. 7(5) + Recital 32 — Demonstrable, auditable consent
    Immutable log of ALL consent events (grants, withdrawals, disputes, reminders).
    """
    __tablename__ = "consent_audit_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(255), nullable=False, index=True)
    user_consent_id = Column(String(36), ForeignKey("user_consents.id"), nullable=False)

    # What happened?
    event_type = Column(String(50), nullable=False, index=True)  # "GRANTED", "WITHDRAWN", "EXPIRED", "DISPUTED", "REMINDER_SENT"
    event_details = Column(Text, nullable=False)  # JSON with context (e.g., "{\"reason\": \"Exercise Art. 17 right\"}")

    # Proof
    ip_address = Column(String(45), nullable=False)
    user_agent = Column(String(500), nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    # For disputes: was the event contested?
    disputed = Column(Boolean, default=False)
    dispute_reason = Column(Text, nullable=True)

    __table_args__ = (
        Index("idx_user_consent_timeline", "user_id", "user_consent_id", "timestamp"),
    )
