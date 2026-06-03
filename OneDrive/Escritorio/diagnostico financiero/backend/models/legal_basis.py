"""
Legal Basis & Data Processing Record Models
GDPR Art. 30 — Records of Processing Activities
Immutable audit trail for RGPD España compliance
"""

from enum import Enum
from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, String, DateTime, Text, Integer, Boolean, Enum as SQLEnum, Index, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
import uuid

Base = declarative_base()


class LegalBasis(str, Enum):
    """
    GDPR Art. 6 — Legal bases for processing.
    Used in DataProcessingRecord to document why we process personal data.
    """
    CONSENT = "CONSENT"  # Art. 6(1)(a) — explicit user consent
    CONTRACT = "CONTRACT"  # Art. 6(1)(b) — necessary for contract execution
    LEGAL_OBLIGATION = "LEGAL_OBLIGATION"  # Art. 6(1)(c) — legal obligation (e.g., AML/KYC)
    VITAL_INTERESTS = "VITAL_INTERESTS"  # Art. 6(1)(d) — vital interests
    PUBLIC_TASK = "PUBLIC_TASK"  # Art. 6(1)(e) — public authority task
    LEGITIMATE_INTEREST = "LEGITIMATE_INTEREST"  # Art. 6(1)(f) — legitimate interest (risk analysis required)


class DataProcessingRecord(Base):
    """
    GDPR Art. 30 — Record of Processing Activities.
    Immutable, indexed log of what data is processed, why, how, who accesses, and retention.

    Every call to process PII must create a record here for compliance audit.
    Indexes on (user_id, processor_system, legal_basis) for quick retrieval in data subject access requests.
    """
    __tablename__ = "data_processing_records"

    # Primary key & identifiers
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(255), nullable=False, index=True)  # ForeignKey to User if exists
    processor_system = Column(String(100), nullable=False, index=True)  # e.g., "pdf_generation", "consent_management", "breach_notification"

    # Legal basis (GDPR Art. 6)
    legal_basis = Column(SQLEnum(LegalBasis), nullable=False, index=True)
    legal_basis_justification = Column(Text, nullable=True)  # e.g., "Consent ID: xyz123", "Contract ID: contract_456"

    # Data being processed
    data_categories = Column(Text, nullable=False)  # JSON list: ["email", "phone", "income", "assets", "debt"]
    purpose = Column(Text, nullable=False)  # Why we process: "Financial diagnosis scoring", "PDF report generation"
    retention_period_days = Column(Integer, nullable=True)  # How long we keep it (from retention policy)

    # Processing details
    processing_type = Column(String(50), nullable=False)  # "COLLECTION", "ANALYSIS", "STORAGE", "DELETION", "EXPORT"
    processing_method = Column(String(100), nullable=True)  # e.g., "AES-256 encryption", "PDF generation", "S3 upload"
    third_party_involved = Column(String(255), nullable=True)  # e.g., "Payloadez", "SendGrid", "AWS S3"
    dpa_reference = Column(String(100), nullable=True)  # Reference to DPA with processor (if applicable)

    # Audit trail
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6 for request origin
    user_agent = Column(String(500), nullable=True)  # Browser/client info for forensics
    request_id = Column(String(36), nullable=True, unique=True)  # Trace ID for debugging (matches API logs)

    # GDPR Art. 17 (Right to erasure) state
    deletion_requested = Column(Boolean, default=False, index=True)
    deletion_timestamp = Column(DateTime(timezone=True), nullable=True)
    anonymized = Column(Boolean, default=False)  # Set to True when user data is anonymized post-deletion

    # Notes
    notes = Column(Text, nullable=True)  # Additional context (e.g., "User withdraws consent", "Breach mitigation")

    # Immutability enforcement
    __table_args__ = (
        Index("idx_user_processor_legal", "user_id", "processor_system", "legal_basis"),
        Index("idx_timestamp_deletion", "timestamp", "deletion_requested"),
    )

    def __repr__(self):
        return f"<DataProcessingRecord(user_id={self.user_id}, processor={self.processor_system}, legal_basis={self.legal_basis.value}, ts={self.timestamp})>"


class DataRetentionPolicy(Base):
    """
    GDPR Art. 5(1)(e) — Data Retention Policy
    Defines how long each data category is retained, and cleanup triggers.
    """
    __tablename__ = "data_retention_policies"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    data_category = Column(String(100), nullable=False, unique=True, index=True)  # e.g., "diagnostic_results", "financial_data", "consent_records"
    retention_days = Column(Integer, nullable=False)  # Days from creation before auto-delete
    legal_basis = Column(SQLEnum(LegalBasis), nullable=False)  # Why we retain (e.g., CONTRACT, LEGAL_OBLIGATION)
    description = Column(Text, nullable=True)  # Human-readable explanation
    cleanup_method = Column(String(50), nullable=False)  # "DELETE" or "ANONYMIZE"

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# Defaults matching Spanish data protection regulations
DEFAULT_RETENTION_POLICIES = {
    "diagnostic_results": (730, "CONTRACT"),  # 2 years for contract performance
    "financial_data": (2555, "LEGAL_OBLIGATION"),  # 7 years per Spanish tax law
    "consent_records": (2555, "CONSENT"),  # 7 years per GDPR
    "transaction_logs": (2555, "LEGAL_OBLIGATION"),  # 7 years per payment regulations
    "breach_notifications": (2555, "LEGAL_OBLIGATION"),  # 7 years per AEPD guidance
    "audit_logs": (2555, "LEGITIMATE_INTEREST"),  # 7 years for security audit trail
    "temporary_processing": (30, "CONTRACT"),  # 30 days for ephemeral data (e.g., session tokens)
}
