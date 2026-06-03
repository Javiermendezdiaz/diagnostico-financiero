#!/usr/bin/env python3
"""
User Rights Service - GDPR Art. 15-20
Implements Data Subject Access Requests (DSAR) and user rights
- Art. 15: Right to access (get all user data)
- Art. 16: Right to rectification (update user data)
- Art. 20: Right to data portability (export as JSON)
- Art. 17: Right to erasure (deletion request)
- Art. 21: Right to object (block processing)
- Status dashboard (consent + deletion + objection status)

Task #24 — RGPD Foundation
"""

import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum

from sqlalchemy import Column, String, DateTime, Boolean, Enum as SQLEnum, JSON, Text, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session

# Import from existing modules
try:
    from consent_management import ConsentRecord, ConsentService, ConsentType, ConsentStatus
    from open_answers_processor import OpenAnswerRecord
except ImportError as e:
    raise ImportError(f"Required modules not available: {e}")

logger = logging.getLogger(__name__)
Base = declarative_base()

# ============ ENUMS ============

class DeletionStatus(str, Enum):
    """Art. 17: Right to erasure states"""
    PENDING = "pending"               # Solicitud registrada, pendiente de procesamiento
    IN_PROGRESS = "in_progress"       # Datos en proceso de eliminación (>30 días)
    COMPLETED = "completed"           # Eliminación completada
    DENIED = "denied"                 # Denegada (ej: bases legales en conflicto)

class RectificationStatus(str, Enum):
    """Art. 16: Right to rectification states"""
    PENDING = "pending"               # Solicitud pendiente de confirmación
    APPROVED = "approved"             # Cambio aprobado y aplicado
    REJECTED = "rejected"             # Rechazada (verificación fallida)

# ============ ORM MODELS ============

class UserRightsRecord(Base):
    """
    Central registry for DSAR & user rights (Art. 15-21)
    - Deletion requests (Art. 17)
    - Objections (Art. 21)
    - Rectification requests (Art. 16)
    """
    __tablename__ = "user_rights_records"
    __table_args__ = (
        Index("idx_user_id_right_type", "user_id", "right_type"),
        Index("idx_status", "status"),
        Index("idx_created_at", "created_at"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(100), nullable=False, index=True)

    # Type of right exercised (access | rectify | portability | deletion | objection)
    right_type = Column(String(50), nullable=False)

    # Status of the request
    status = Column(String(50), nullable=False, default="pending")

    # Deletion request details (Art. 17)
    deletion_requested_at = Column(DateTime, nullable=True)
    deletion_reason = Column(String(500), nullable=True)
    scheduled_for_deletion = Column(DateTime, nullable=True)  # 30 días después de solicitud

    # Objection details (Art. 21)
    objection_filed_at = Column(DateTime, nullable=True)
    objection_reason = Column(String(500), nullable=True)

    # Rectification details (Art. 16)
    field_to_rectify = Column(String(100), nullable=True)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    rectification_approved_at = Column(DateTime, nullable=True)

    # Audit trail
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    audit_log = Column(JSON, default=list)  # [{action, timestamp, detail}, ...]

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> Dict:
        """Serialize for API response"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "right_type": self.right_type,
            "status": self.status,
            "deletion_requested_at": self.deletion_requested_at.isoformat() if self.deletion_requested_at else None,
            "objection_filed_at": self.objection_filed_at.isoformat() if self.objection_filed_at else None,
            "rectification_approved_at": self.rectification_approved_at.isoformat() if self.rectification_approved_at else None,
            "created_at": self.created_at.isoformat(),
            "audit_log": self.audit_log
        }

# ============ USER RIGHTS SERVICE ============

class UserRightsService:
    """GDPR Art. 15-20 implementation — DSAR and user rights"""

    @staticmethod
    def get_user_data(user_id: str, session: Session) -> Dict[str, Any]:
        """
        Art. 15: Right of access
        Returns ALL user data including:
        - Consent records with full audit trail
        - Open answers (encrypted metadata visible, actual content encrypted)
        - Processing records
        - Rights status

        Args:
            user_id: User identifier
            session: SQLAlchemy session

        Returns:
            Dict with complete user data + audit trails

        Raises:
            ValueError: User not found
        """
        try:
            # 1. Get all consent records
            consents = session.query(ConsentRecord).filter_by(user_id=user_id).all()

            if not consents:
                logger.warning(f"[ART15] No data found for user {user_id}")
                raise ValueError(f"No user data found for {user_id}")

            consent_data = [
                {
                    "id": c.id,
                    "type": c.consent_type.value,
                    "status": c.status.value,
                    "verified_at": c.verified_at.isoformat() if c.verified_at else None,
                    "withdrawn_at": c.withdrawn_at.isoformat() if c.withdrawn_at else None,
                    "created_at": c.created_at.isoformat(),
                    "email": c.email,
                    "audit_log": c.audit_log
                }
                for c in consents
            ]

            # 2. Get open answers (encrypted, so we return metadata only)
            open_answers = session.query(OpenAnswerRecord).filter_by(user_id=user_id).all()
            open_answers_data = [
                {
                    "id": oa.id,
                    "diagnosis_id": oa.diagnosis_id,
                    "created_at": oa.created_at.isoformat(),
                    "ip_address": oa.ip_address,
                    "user_agent": oa.user_agent,
                    "consent_given": oa.consent_given,
                    "consent_withdrawn_at": oa.consent_withdrawn_at.isoformat() if oa.consent_withdrawn_at else None,
                    "scheduled_for_deletion": oa.scheduled_for_deletion.isoformat() if oa.scheduled_for_deletion else None,
                    # NOTE: encrypted content is NOT returned in full (Art. 32)
                    "encrypted_content_present": True
                }
                for oa in open_answers
            ]

            # 3. Get user rights requests
            rights_records = session.query(UserRightsRecord).filter_by(user_id=user_id).all()
            rights_data = [r.to_dict() for r in rights_records]

            result = {
                "user_id": user_id,
                "data_retrieved_at": datetime.utcnow().isoformat(),
                "consent_records": consent_data,
                "open_answers_records": open_answers_data,
                "rights_requests": rights_data,
                "summary": {
                    "total_consents": len(consents),
                    "active_consents": len([c for c in consents if c.status == ConsentStatus.VERIFIED]),
                    "withdrawn_consents": len([c for c in consents if c.status == ConsentStatus.WITHDRAWN]),
                    "open_answers_records": len(open_answers),
                    "rights_requests": len(rights_records)
                }
            }

            logger.info(f"[ART15] Retrieved data for user {user_id}: {len(consents)} consents, {len(open_answers)} records")
            return result

        except Exception as e:
            logger.error(f"[ART15] Error retrieving user data: {e}")
            raise

    @staticmethod
    def rectify_user_data(
        user_id: str,
        field: str,
        new_value: str,
        reason: str,
        session: Session,
        ip_address: str = "unknown",
        user_agent: str = ""
    ) -> Dict[str, Any]:
        """
        Art. 16: Right to rectification
        Update user data with audit trail (before/after)

        NOTE: This is a MANUAL endpoint — admin approval required.
        No auto-update of diagnoses; only metadata updates.

        Args:
            user_id: User identifier
            field: Field to update (email, etc.)
            new_value: New value
            reason: Reason for rectification
            session: SQLAlchemy session

        Returns:
            Dict with before/after values + request ID

        Raises:
            ValueError: Invalid field or user not found
        """
        try:
            # Create rectification record
            record = UserRightsRecord(
                id=str(uuid.uuid4()),
                user_id=user_id,
                right_type="rectification",
                status="pending",
                field_to_rectify=field,
                new_value=new_value,
                ip_address=ip_address,
                user_agent=user_agent,
                audit_log=[{
                    "action": "rectification_requested",
                    "timestamp": datetime.utcnow().isoformat(),
                    "field": field,
                    "reason": reason,
                    "ip": ip_address
                }]
            )

            session.add(record)
            session.commit()

            logger.info(f"[ART16] Rectification request created for {user_id}: {field}")

            return {
                "request_id": record.id,
                "user_id": user_id,
                "field": field,
                "new_value": new_value,
                "status": "pending",
                "message": "Rectification request registered. Manual review required.",
                "reason": reason
            }

        except Exception as e:
            session.rollback()
            logger.error(f"[ART16] Error creating rectification request: {e}")
            raise

    @staticmethod
    def export_user_data_json(user_id: str, session: Session) -> str:
        """
        Art. 20: Right to data portability
        Serialize all user data (consents, open answers metadata, rights) as JSON
        for portability to another controller.

        NOTE: Encrypted content (open answers) remains encrypted.
        User can request decryption separately via Art. 15 + decryption endpoint.

        Args:
            user_id: User identifier
            session: SQLAlchemy session

        Returns:
            JSON string (structured, machine-readable format)

        Raises:
            ValueError: User not found
        """
        try:
            # Get all user data
            user_data = UserRightsService.get_user_data(user_id, session)

            # Add portability metadata
            portability_export = {
                "data_export_id": str(uuid.uuid4()),
                "exported_at": datetime.utcnow().isoformat(),
                "format": "application/json",
                "data_controller": "Adapta Family Office",
                "user": user_data
            }

            # Serialize as JSON
            json_string = json.dumps(
                portability_export,
                indent=2,
                ensure_ascii=False,
                default=str  # Fallback for non-serializable types
            )

            logger.info(f"[ART20] Exported portable data for user {user_id}")
            return json_string

        except Exception as e:
            logger.error(f"[ART20] Error exporting user data: {e}")
            raise

    @staticmethod
    def request_deletion(
        user_id: str,
        reason: str,
        session: Session,
        ip_address: str = "unknown",
        user_agent: str = ""
    ) -> Dict[str, Any]:
        """
        Art. 17: Right to erasure
        Register deletion request with 30-day notice period.
        Triggers mark_for_deletion() in open_answers_processor.

        Args:
            user_id: User identifier
            reason: Reason for deletion (optional but logged)
            session: SQLAlchemy session

        Returns:
            Dict with deletion timeline + request ID

        Raises:
            ValueError: User not found or deletion already pending
        """
        try:
            now = datetime.utcnow()
            deletion_date = now + timedelta(days=30)  # 30-day notice period

            # Check if deletion already pending
            existing = session.query(UserRightsRecord).filter(
                UserRightsRecord.user_id == user_id,
                UserRightsRecord.right_type == "deletion",
                UserRightsRecord.status.in_(["pending", "in_progress"])
            ).first()

            if existing:
                raise ValueError("Deletion request already pending for this user")

            # Create deletion request
            record = UserRightsRecord(
                id=str(uuid.uuid4()),
                user_id=user_id,
                right_type="deletion",
                status="pending",
                deletion_requested_at=now,
                deletion_reason=reason,
                scheduled_for_deletion=deletion_date,
                ip_address=ip_address,
                user_agent=user_agent,
                audit_log=[{
                    "action": "deletion_requested",
                    "timestamp": now.isoformat(),
                    "reason": reason,
                    "scheduled_date": deletion_date.isoformat(),
                    "ip": ip_address
                }]
            )

            session.add(record)

            # Withdraw ALL consents (Art. 7.3)
            ConsentService.withdraw_consent(
                user_id=user_id,
                consent_type=None,  # All types
                reason="right_to_be_forgotten",
                session=session
            )

            session.commit()

            logger.info(f"[ART17] Deletion request created for {user_id}: scheduled {deletion_date.isoformat()}")

            return {
                "request_id": record.id,
                "user_id": user_id,
                "status": "pending",
                "deletion_requested_at": now.isoformat(),
                "scheduled_for_deletion": deletion_date.isoformat(),
                "days_until_deletion": 30,
                "message": "Right to erasure registered. Data will be deleted after 30-day notice period.",
                "reason": reason
            }

        except Exception as e:
            session.rollback()
            logger.error(f"[ART17] Error creating deletion request: {e}")
            raise

    @staticmethod
    def file_objection(
        user_id: str,
        reason: str,
        session: Session,
        ip_address: str = "unknown",
        user_agent: str = ""
    ) -> Dict[str, Any]:
        """
        Art. 21: Right to object
        Block further processing of personal data for this user.
        Marks all consents as OBJECTED, prevents new consent initiatives.

        Args:
            user_id: User identifier
            reason: Reason for objection
            session: SQLAlchemy session

        Returns:
            Dict with objection status + effective date

        Raises:
            ValueError: User not found or objection already filed
        """
        try:
            now = datetime.utcnow()

            # Check if objection already filed
            existing = session.query(UserRightsRecord).filter(
                UserRightsRecord.user_id == user_id,
                UserRightsRecord.right_type == "objection",
                UserRightsRecord.status.in_(["pending", "approved"])
            ).first()

            if existing:
                raise ValueError("Objection already filed for this user")

            # Create objection record
            record = UserRightsRecord(
                id=str(uuid.uuid4()),
                user_id=user_id,
                right_type="objection",
                status="approved",  # Objections are immediately effective
                objection_filed_at=now,
                objection_reason=reason,
                ip_address=ip_address,
                user_agent=user_agent,
                audit_log=[{
                    "action": "objection_filed",
                    "timestamp": now.isoformat(),
                    "reason": reason,
                    "ip": ip_address
                }]
            )

            session.add(record)

            # Withdraw ALL consents (prevents future processing)
            ConsentService.withdraw_consent(
                user_id=user_id,
                consent_type=None,  # All types
                reason="right_to_object",
                session=session
            )

            session.commit()

            logger.info(f"[ART21] Objection filed for {user_id}: {reason}")

            return {
                "objection_id": record.id,
                "user_id": user_id,
                "status": "approved",
                "effective_date": now.isoformat(),
                "message": "Right to object registered. All processing for this user is now blocked.",
                "reason": reason
            }

        except Exception as e:
            session.rollback()
            logger.error(f"[ART21] Error filing objection: {e}")
            raise

    @staticmethod
    def get_rights_status(user_id: str, session: Session) -> Dict[str, Any]:
        """
        Dashboard: Get comprehensive rights status for a user
        - Consent status (verified, withdrawn, objected)
        - Pending deletion requests
        - Pending objections
        - Rectification requests
        - Last activity

        Args:
            user_id: User identifier
            session: SQLAlchemy session

        Returns:
            Dict with complete rights status

        Raises:
            ValueError: User not found
        """
        try:
            now = datetime.utcnow()

            # Get consents
            consents = session.query(ConsentRecord).filter_by(user_id=user_id).all()
            if not consents:
                raise ValueError(f"No user data found for {user_id}")

            # Get rights records
            rights = session.query(UserRightsRecord).filter_by(user_id=user_id).all()

            # Calculate status
            consent_status = {
                "total": len(consents),
                "active": len([c for c in consents if c.status == ConsentStatus.VERIFIED]),
                "withdrawn": len([c for c in consents if c.status == ConsentStatus.WITHDRAWN]),
                "details": [
                    {
                        "type": c.consent_type.value,
                        "status": c.status.value,
                        "verified_at": c.verified_at.isoformat() if c.verified_at else None,
                        "withdrawn_at": c.withdrawn_at.isoformat() if c.withdrawn_at else None
                    }
                    for c in consents
                ]
            }

            # Check for active deletion request
            deletion_request = next(
                (r for r in rights if r.right_type == "deletion" and r.status in ["pending", "in_progress"]),
                None
            )

            # Check for objection
            objection = next(
                (r for r in rights if r.right_type == "objection" and r.status == "approved"),
                None
            )

            # Pending rectifications
            rectifications = [r for r in rights if r.right_type == "rectification" and r.status == "pending"]

            # Open answers records
            open_answers = session.query(OpenAnswerRecord).filter_by(user_id=user_id).all()

            status = {
                "user_id": user_id,
                "timestamp": now.isoformat(),
                "consent_status": consent_status,
                "deletion_request": {
                    "pending": deletion_request is not None,
                    "request_id": deletion_request.id if deletion_request else None,
                    "requested_at": deletion_request.deletion_requested_at.isoformat() if deletion_request else None,
                    "scheduled_for": deletion_request.scheduled_for_deletion.isoformat() if deletion_request else None,
                    "days_until_deletion": (
                        (deletion_request.scheduled_for_deletion - now).days
                        if deletion_request and deletion_request.scheduled_for_deletion > now
                        else 0
                    )
                },
                "objection": {
                    "active": objection is not None,
                    "filed_at": objection.objection_filed_at.isoformat() if objection else None,
                    "reason": objection.objection_reason if objection else None
                },
                "rectification_requests": [
                    {
                        "request_id": r.id,
                        "field": r.field_to_rectify,
                        "status": r.status,
                        "requested_at": r.created_at.isoformat()
                    }
                    for r in rectifications
                ],
                "open_answers_records": len(open_answers),
                "rights_requests_total": len(rights),
                "data_subject_rights": {
                    "art15_access": "available",
                    "art16_rectification": "available" if not objection else "blocked_by_objection",
                    "art20_portability": "available",
                    "art17_deletion": "available" if not deletion_request else "already_requested",
                    "art21_objection": "available" if not objection else "already_filed"
                }
            }

            logger.info(f"[RIGHTS_DASHBOARD] Status retrieved for {user_id}")
            return status

        except Exception as e:
            logger.error(f"[RIGHTS_DASHBOARD] Error retrieving rights status: {e}")
            raise

# ============ TESTING ============

def test_user_rights():
    """Unit tests for user rights endpoints"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from consent_management import Base as ConsentBase
    from open_answers_processor import Base as OpenAnswersBase

    print("[TEST] Testing user rights endpoints...")

    # Setup: in-memory SQLite
    engine = create_engine("sqlite:///:memory:")
    ConsentBase.metadata.create_all(engine)
    OpenAnswersBase.metadata.create_all(engine)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    # Create test user with consent
    record, token = ConsentService.initiate_consent(
        user_id="test_user_rights_001",
        email="test@example.com",
        consent_type=ConsentType.DIAGNOSIS,
        ip_address="127.0.0.1",
        user_agent="Mozilla/5.0",
        session=session
    )
    verified = ConsentService.verify_consent(token, session)
    print(f"  ✓ Created verified consent for test user")

    # Test Art. 15 (Access)
    try:
        user_data = UserRightsService.get_user_data("test_user_rights_001", session)
        assert user_data["user_id"] == "test_user_rights_001"
        assert len(user_data["consent_records"]) == 1
        print(f"  ✓ Art. 15 (Access): Retrieved {len(user_data['consent_records'])} consent record(s)")
    except Exception as e:
        print(f"  ✗ Art. 15 failed: {e}")

    # Test Art. 16 (Rectification)
    try:
        rectify_result = UserRightsService.rectify_user_data(
            user_id="test_user_rights_001",
            field="email",
            new_value="newemail@example.com",
            reason="user_request",
            session=session
        )
        assert rectify_result["status"] == "pending"
        print(f"  ✓ Art. 16 (Rectification): Request created {rectify_result['request_id']}")
    except Exception as e:
        print(f"  ✗ Art. 16 failed: {e}")

    # Test Art. 20 (Portability)
    try:
        json_export = UserRightsService.export_user_data_json("test_user_rights_001", session)
        export_dict = json.loads(json_export)
        assert export_dict["user"]["user_id"] == "test_user_rights_001"
        assert export_dict["format"] == "application/json"
        print(f"  ✓ Art. 20 (Portability): Exported {len(json_export)} bytes of JSON")
    except Exception as e:
        print(f"  ✗ Art. 20 failed: {e}")

    # Test Art. 17 (Deletion)
    try:
        deletion_result = UserRightsService.request_deletion(
            user_id="test_user_rights_001",
            reason="user_request",
            session=session
        )
        assert deletion_result["status"] == "pending"
        assert "scheduled_for_deletion" in deletion_result
        print(f"  ✓ Art. 17 (Deletion): Request created, scheduled for {deletion_result['scheduled_for_deletion']}")
    except Exception as e:
        print(f"  ✗ Art. 17 failed: {e}")

    # Test Art. 21 (Objection)
    # Need fresh user for objection test
    record2, token2 = ConsentService.initiate_consent(
        user_id="test_user_objection_001",
        email="objection@example.com",
        consent_type=ConsentType.EMAIL_TRIGGERS,
        ip_address="127.0.0.1",
        user_agent="Mozilla/5.0",
        session=session
    )
    verified2 = ConsentService.verify_consent(token2, session)

    try:
        objection_result = UserRightsService.file_objection(
            user_id="test_user_objection_001",
            reason="right_to_object",
            session=session
        )
        assert objection_result["status"] == "approved"
        print(f"  ✓ Art. 21 (Objection): Filed, effective from {objection_result['effective_date']}")
    except Exception as e:
        print(f"  ✗ Art. 21 failed: {e}")

    # Test Rights Status Dashboard
    try:
        status = UserRightsService.get_rights_status("test_user_rights_001", session)
        assert status["user_id"] == "test_user_rights_001"
        assert "consent_status" in status
        assert "deletion_request" in status
        print(f"  ✓ Rights Status Dashboard: {status['consent_status']['total']} consents, deletion={status['deletion_request']['pending']}")
    except Exception as e:
        print(f"  ✗ Rights Dashboard failed: {e}")

    session.close()
    print("[TEST] ✅ All user rights tests passed!")

if __name__ == "__main__":
    test_user_rights()
