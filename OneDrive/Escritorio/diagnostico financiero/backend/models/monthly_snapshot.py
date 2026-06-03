"""
Monthly Snapshot Model — User Progress Tracking & GDPR Art. 5.1.e Retention
Tracks user diagnostic results monthly for progress visualization and compliance audit.
"""

from enum import Enum
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, Text, JSON, Index, ForeignKey
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func
import uuid
import json

Base = declarative_base()


class FinancialProfile(str, Enum):
    """User's financial risk profile — determined from diagnostic."""
    CONSERVADOR = "Conservador"
    MODERADO = "Moderado"
    AGRESIVO = "Agresivo"


class ConsentStatus(str, Enum):
    """Snapshot consent verification status."""
    VERIFIED = "VERIFIED"  # User's consent confirmed at snapshot time
    PENDING = "PENDING"  # Consent check pending
    REVOKED = "REVOKED"  # User withdrew consent; snapshot should be deleted


class MonthlySnapshot(Base):
    """
    GDPR Art. 5.1.e — Storage Limitation
    Track user's diagnostic progress monthly, auto-delete after 12 months.
    Used for:
    - User dashboard: 6-month trend chart
    - Progress tracking: score over time
    - Gamification: certificate generation (highest monthly score)
    - GDPR audit: demonstrate data lifecycle management
    """
    __tablename__ = "monthly_snapshots"

    # Primary & Foreign Keys
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(255), nullable=False, index=True)  # FK to User (not stored in this table; join in query)

    # Snapshot metadata
    snapshot_date = Column(DateTime(timezone=True), nullable=False, index=True)  # Always 1st of month, 00:00 UTC

    # Diagnostic results (atomic snapshot)
    diagnosis_score = Column(Integer, nullable=False)  # 0-100, user's financial awareness score
    profile = Column(String(20), nullable=False)  # Conservador/Moderado/Agresivo

    # Top 3 recommendations — JSON array of recommendation dicts
    # Format: [
    #   {"title": "Recomendación 1", "description": "...", "category": "ahorro|inversión|protección"},
    #   ...
    # ]
    top_3_recommendations = Column(JSON, nullable=False)  # Immutable snapshot of advice given

    # Quiz engagement metric
    quiz_completion_percent = Column(Integer, nullable=False)  # 0-100, % of diagnostic completed

    # GDPR consent verification at snapshot time
    consent_status = Column(String(20), nullable=False, default="VERIFIED")  # VERIFIED/PENDING/REVOKED

    # Audit & Lifecycle
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)  # Scheduled deletion date (now + 365 days)

    # Compliance & Auditing
    # audit_log is a JSON field tracking snapshot lifecycle: [
    #   {"event": "CREATED", "timestamp": "2025-05-01T00:00:00Z"},
    #   {"event": "CONSENT_VERIFIED", "timestamp": "2025-05-01T08:30:00Z"},
    #   {"event": "SCHEDULED_DELETION", "timestamp": "2026-05-01T00:00:00Z"}
    # ]
    audit_log = Column(JSON, nullable=False, default=list)

    __table_args__ = (
        Index("idx_user_snapshots", "user_id", "snapshot_date"),
        Index("idx_expiry", "expires_at"),
        Index("idx_consent_revoked", "user_id", "consent_status"),
        Index("idx_created", "created_at"),
    )

    def __repr__(self):
        return (
            f"<MonthlySnapshot(user_id={self.user_id}, date={self.snapshot_date.strftime('%Y-%m-%d')}, "
            f"score={self.diagnosis_score}, profile={self.profile})>"
        )

    def to_dict(self):
        """Export snapshot to dict for JSON serialization."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "snapshot_date": self.snapshot_date.isoformat() if self.snapshot_date else None,
            "diagnosis_score": self.diagnosis_score,
            "profile": self.profile,
            "top_3_recommendations": self.top_3_recommendations or [],
            "quiz_completion_percent": self.quiz_completion_percent,
            "consent_status": self.consent_status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "audit_log": self.audit_log or []
        }

    @staticmethod
    def create_from_diagnostic(
        user_id: str,
        diagnosis_score: int,
        profile: str,
        top_3_recommendations: list,
        quiz_completion_percent: int,
        snapshot_date: datetime,
        consent_status: str = "VERIFIED"
    ) -> "MonthlySnapshot":
        """
        Factory method: create new snapshot from diagnostic result.

        Args:
            user_id: UUID of user
            diagnosis_score: 0-100 score
            profile: "Conservador", "Moderado", or "Agresivo"
            top_3_recommendations: List of 3 recommendation dicts
            quiz_completion_percent: 0-100
            snapshot_date: Timestamp (typically first of month UTC)
            consent_status: "VERIFIED" (default), "PENDING", or "REVOKED"

        Returns:
            MonthlySnapshot instance
        """
        from datetime import timedelta

        # Initialize audit log
        audit_log = [
            {
                "event": "CREATED",
                "timestamp": datetime.utcnow().isoformat(),
                "source": "diagnostic_completion"
            }
        ]

        # Calculate expiry: snapshot_date + 365 days
        expires_at = snapshot_date + timedelta(days=365)

        snapshot = MonthlySnapshot(
            user_id=user_id,
            snapshot_date=snapshot_date,
            diagnosis_score=diagnosis_score,
            profile=profile,
            top_3_recommendations=top_3_recommendations or [],
            quiz_completion_percent=quiz_completion_percent,
            consent_status=consent_status,
            expires_at=expires_at,
            audit_log=audit_log
        )

        return snapshot

    def add_audit_event(self, event: str, details: dict = None):
        """Append event to audit log (immutable proof)."""
        if not self.audit_log:
            self.audit_log = []

        log_entry = {
            "event": event,
            "timestamp": datetime.utcnow().isoformat(),
        }
        if details:
            log_entry.update(details)

        self.audit_log.append(log_entry)
