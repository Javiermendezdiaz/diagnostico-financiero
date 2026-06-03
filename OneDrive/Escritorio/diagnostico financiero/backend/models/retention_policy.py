"""
Retention Policy & Auto-Cleanup Service
GDPR Art. 5.1(e) — Storage Limitation
GDPR Art. 17 — Right to Erasure
GDPR Art. 33-34 — Breach Notification

Manages data lifecycle: diagnoses retained 12 months then auto-delete if not renewed.
Consent records retained indefinitely (audit trail). Breach incidents retained 3+ years.
"""

from enum import Enum
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy import Column, String, DateTime, Text, Enum as SQLEnum, Index, JSON
from sqlalchemy.orm import Session, declarative_base
from sqlalchemy.sql import func
import uuid
import json
import logging

logger = logging.getLogger(__name__)

Base = declarative_base()


class RetentionPolicy(str, Enum):
    """Data retention schedule per GDPR Art. 5.1(e)"""
    DIAGNOSIS_12M = "DIAGNOSIS_12M"  # 12 months from creation
    OPEN_ANSWERS_12M = "OPEN_ANSWERS_12M"  # 12 months from last update
    CONSENT_INDEFINITE = "CONSENT_INDEFINITE"  # Forever (audit trail, Art. 7(5))
    BREACH_3Y = "BREACH_3Y"  # 3+ years (Art. 33-34 compliance, AEPD guidance)
    DELETION_REQUEST_30D = "DELETION_REQUEST_30D"  # 30-day grace period before purge (Art. 17 RTbF)


class RetentionSchedule(Base):
    """
    GDPR Art. 5.1(e) — Retention Schedule Record

    Tracks expiration of each entity (diagnosis, answer, breach, etc.)
    Immutable, indexed for fast cleanup queries.
    """
    __tablename__ = "retention_schedules"

    # Primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Entity reference
    entity_type = Column(String(50), nullable=False, index=True)
    # Values: 'diagnosis', 'open_answer', 'consent_record', 'breach_incident', 'deletion_request'

    entity_id = Column(String(36), nullable=False, index=True)
    user_id = Column(String(255), nullable=False, index=True)

    # Retention policy applied
    retention_policy = Column(SQLEnum(RetentionPolicy), nullable=False, index=True)

    # Timeline
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)  # Computed: created_at + policy duration

    # Soft delete state (grace period before hard delete)
    deleted_at = Column(DateTime(timezone=True), nullable=True)  # When soft-delete occurred
    deletion_executed_at = Column(DateTime(timezone=True), nullable=True)  # When hard-delete occurred (7d after deleted_at)
    hard_delete_eligible_at = Column(DateTime(timezone=True), nullable=True)  # Computed: deleted_at + 7 days

    # Audit trail: JSON array of {timestamp, action, reason, actor}
    # Example: [{"timestamp": "2026-05-30T10:00:00Z", "action": "scheduled", "reason": "new diagnosis", "actor": "system"}]
    audit_log = Column(JSON, default=list, nullable=False)

    # Notes (optional context)
    notes = Column(Text, nullable=True)

    # Indexes
    __table_args__ = (
        Index("idx_retention_expiry", "entity_type", "expires_at"),
        Index("idx_retention_deleted", "deleted_at", "hard_delete_eligible_at"),
        Index("idx_retention_user", "user_id", "entity_type"),
    )

    def __repr__(self):
        return (f"<RetentionSchedule(entity_type={self.entity_type}, entity_id={self.entity_id}, "
                f"policy={self.retention_policy.value}, expires_at={self.expires_at})>")


class RetentionService:
    """
    Service layer for data retention & auto-cleanup.
    GDPR Art. 5.1(e): Delete ASAP after expiry. No "keep just in case".
    """

    # Policy duration mappings
    POLICY_DURATIONS = {
        RetentionPolicy.DIAGNOSIS_12M: timedelta(days=365),
        RetentionPolicy.OPEN_ANSWERS_12M: timedelta(days=365),
        RetentionPolicy.CONSENT_INDEFINITE: timedelta(days=99999),  # ~273 years (never expires)
        RetentionPolicy.BREACH_3Y: timedelta(days=1095),  # 3 years
        RetentionPolicy.DELETION_REQUEST_30D: timedelta(days=30),  # 30 days (Art. 17 grace period)
    }

    # Soft delete grace period (before hard delete)
    SOFT_DELETE_GRACE_PERIOD = timedelta(days=7)

    @staticmethod
    def schedule_for_deletion(
        entity_type: str,
        entity_id: str,
        user_id: str,
        retention_policy: RetentionPolicy,
        session: Session,
        notes: Optional[str] = None
    ) -> RetentionSchedule:
        """
        Schedule an entity for future deletion per GDPR Art. 5.1(e).

        Args:
            entity_type: 'diagnosis', 'open_answer', 'consent_record', 'breach_incident', 'deletion_request'
            entity_id: UUID of the entity
            user_id: User who owns the data
            retention_policy: RetentionPolicy enum
            session: SQLAlchemy session
            notes: Optional context (e.g., "user consent renewal", "breach cleanup")

        Returns:
            RetentionSchedule record
        """
        now = datetime.utcnow()
        duration = RetentionService.POLICY_DURATIONS.get(retention_policy, timedelta(days=365))
        expires_at = now + duration

        # Initial audit log entry
        audit_entry = {
            "timestamp": now.isoformat() + "Z",
            "action": "scheduled",
            "reason": notes or f"Automatic scheduling for {entity_type}",
            "actor": "system"
        }

        schedule = RetentionSchedule(
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            retention_policy=retention_policy,
            created_at=now,
            expires_at=expires_at,
            audit_log=[audit_entry],
            notes=notes
        )

        session.add(schedule)
        session.commit()

        logger.info(
            f"Retention schedule created: {entity_type}:{entity_id} "
            f"(policy={retention_policy.value}, expires={expires_at.isoformat()})"
        )

        return schedule

    @staticmethod
    def execute_deletions(session: Session, dry_run: bool = False) -> Dict[str, Any]:
        """
        Cleanup job (Art. 5.1(e)): find expired records and delete them.
        Runs daily at 2 AM UTC (configurable via env CLEANUP_HOUR).

        Two-phase deletion:
        1. Soft delete: Set deleted_at, mark hard_delete_eligible_at (now + 7d)
        2. Hard delete: If deleted_at < now - 7d, permanently remove from DB

        Args:
            session: SQLAlchemy session
            dry_run: If True, report what would be deleted without executing

        Returns:
            Dict with stats: {soft_deleted_count, hard_deleted_count, errors}
        """
        now = datetime.utcnow()
        stats = {
            "soft_deleted_count": 0,
            "hard_deleted_count": 0,
            "errors": []
        }

        try:
            # === PHASE 1: SOFT DELETE (Expired -> Marked for deletion) ===
            # Find records that have expired but not yet soft-deleted
            soft_delete_candidates = session.query(RetentionSchedule).filter(
                RetentionSchedule.expires_at <= now,
                RetentionSchedule.deleted_at.is_(None)
            ).all()

            for schedule in soft_delete_candidates:
                if not dry_run:
                    # Soft delete: set deleted_at and compute hard_delete_eligible_at
                    schedule.deleted_at = now
                    schedule.hard_delete_eligible_at = now + RetentionService.SOFT_DELETE_GRACE_PERIOD

                    # Append to audit log
                    audit_entry = {
                        "timestamp": now.isoformat() + "Z",
                        "action": "soft_deleted",
                        "reason": f"Retention period expired ({schedule.retention_policy.value})",
                        "actor": "system"
                    }
                    schedule.audit_log = (schedule.audit_log or []) + [audit_entry]

                    session.add(schedule)

                    logger.info(
                        f"Soft deleted: {schedule.entity_type}:{schedule.entity_id} "
                        f"(grace period ends: {schedule.hard_delete_eligible_at.isoformat()})"
                    )

                stats["soft_deleted_count"] += 1

            session.commit()

            # === PHASE 2: HARD DELETE (7d grace period elapsed -> Permanent removal) ===
            # Find records that were soft-deleted > 7 days ago
            hard_delete_eligible_time = now - RetentionService.SOFT_DELETE_GRACE_PERIOD

            hard_delete_candidates = session.query(RetentionSchedule).filter(
                RetentionSchedule.deleted_at.isnot(None),
                RetentionSchedule.deleted_at <= hard_delete_eligible_time,
                RetentionSchedule.deletion_executed_at.is_(None)
            ).all()

            for schedule in hard_delete_candidates:
                if not dry_run:
                    # Log hard delete action before removal
                    audit_entry = {
                        "timestamp": now.isoformat() + "Z",
                        "action": "hard_deleted",
                        "reason": f"Grace period (7 days) elapsed",
                        "actor": "system"
                    }
                    # Update before deletion for audit trail
                    schedule.deletion_executed_at = now
                    schedule.audit_log = (schedule.audit_log or []) + [audit_entry]
                    session.add(schedule)
                    session.commit()

                    # Now delete the record
                    session.delete(schedule)

                    logger.info(
                        f"Hard deleted: {schedule.entity_type}:{schedule.entity_id}"
                    )

                stats["hard_deleted_count"] += 1

            session.commit()

            logger.info(
                f"Cleanup job completed: soft_deleted={stats['soft_deleted_count']}, "
                f"hard_deleted={stats['hard_deleted_count']}"
            )

        except Exception as e:
            logger.error(f"Cleanup job error: {e}", exc_info=True)
            stats["errors"].append(str(e))
            session.rollback()

        return stats

    @staticmethod
    def get_retention_status(entity_id: str, session: Session) -> Optional[Dict[str, Any]]:
        """
        Get retention status for an entity (show user when their data expires).

        Args:
            entity_id: UUID of the entity
            session: SQLAlchemy session

        Returns:
            Dict with {entity_id, entity_type, expires_at, days_remaining, policy, status}
            or None if not found
        """
        schedule = session.query(RetentionSchedule).filter(
            RetentionSchedule.entity_id == entity_id
        ).first()

        if not schedule:
            return None

        now = datetime.utcnow()
        days_remaining = (schedule.expires_at - now).days if schedule.expires_at > now else 0

        return {
            "entity_id": schedule.entity_id,
            "entity_type": schedule.entity_type,
            "retention_policy": schedule.retention_policy.value,
            "expires_at": schedule.expires_at.isoformat() + "Z",
            "days_remaining": max(0, days_remaining),
            "status": "active" if schedule.deleted_at is None else "soft_deleted",
            "soft_deleted_at": schedule.deleted_at.isoformat() + "Z" if schedule.deleted_at else None,
            "hard_delete_eligible_at": schedule.hard_delete_eligible_at.isoformat() + "Z" if schedule.hard_delete_eligible_at else None,
        }

    @staticmethod
    def extend_retention(
        entity_id: str,
        new_policy: RetentionPolicy,
        session: Session,
        reason: Optional[str] = None
    ) -> Optional[RetentionSchedule]:
        """
        Reset retention expiry for an entity (e.g., user renews consent, Art. 17 withdrawal cancelled).

        Args:
            entity_id: UUID of the entity
            new_policy: New RetentionPolicy to apply
            session: SQLAlchemy session
            reason: Why retention is being extended

        Returns:
            Updated RetentionSchedule or None if not found
        """
        schedule = session.query(RetentionSchedule).filter(
            RetentionSchedule.entity_id == entity_id
        ).first()

        if not schedule:
            return None

        now = datetime.utcnow()
        old_expires_at = schedule.expires_at
        duration = RetentionService.POLICY_DURATIONS.get(new_policy, timedelta(days=365))
        schedule.expires_at = now + duration
        schedule.retention_policy = new_policy

        # If previously soft-deleted, restore it
        if schedule.deleted_at is not None:
            schedule.deleted_at = None
            schedule.hard_delete_eligible_at = None

        # Audit trail
        audit_entry = {
            "timestamp": now.isoformat() + "Z",
            "action": "retention_extended",
            "reason": reason or f"Policy changed from {schedule.retention_policy.value} to {new_policy.value}",
            "old_expires_at": old_expires_at.isoformat() + "Z",
            "new_expires_at": schedule.expires_at.isoformat() + "Z",
            "actor": "system"
        }
        schedule.audit_log = (schedule.audit_log or []) + [audit_entry]

        session.add(schedule)
        session.commit()

        logger.info(
            f"Retention extended: {schedule.entity_id} "
            f"(old_expires={old_expires_at.isoformat()}, new_expires={schedule.expires_at.isoformat()})"
        )

        return schedule

    @staticmethod
    def request_immediate_deletion(
        entity_id: str,
        session: Session,
        reason: str = "User exercise of Art. 17 right to erasure"
    ) -> Optional[RetentionSchedule]:
        """
        Process Art. 17 (Right to Erasure) request: immediate deletion scheduling.

        Sets retention_policy = DELETION_REQUEST_30D and expires_at = now + 30 days
        (grace period for verification + backup cleanup before hard delete).

        Args:
            entity_id: UUID of the entity
            session: SQLAlchemy session
            reason: Deletion reason

        Returns:
            Updated RetentionSchedule or None if not found
        """
        schedule = session.query(RetentionSchedule).filter(
            RetentionSchedule.entity_id == entity_id
        ).first()

        if not schedule:
            return None

        now = datetime.utcnow()
        schedule.retention_policy = RetentionPolicy.DELETION_REQUEST_30D
        schedule.expires_at = now + timedelta(days=30)

        audit_entry = {
            "timestamp": now.isoformat() + "Z",
            "action": "deletion_requested",
            "reason": reason,
            "actor": "system"
        }
        schedule.audit_log = (schedule.audit_log or []) + [audit_entry]

        session.add(schedule)
        session.commit()

        logger.info(
            f"Deletion requested (Art. 17): {schedule.entity_id} "
            f"(will delete in 30 days: {schedule.expires_at.isoformat()})"
        )

        return schedule
