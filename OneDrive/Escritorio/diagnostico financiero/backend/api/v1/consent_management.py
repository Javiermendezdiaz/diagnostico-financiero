"""
Consent Management API Endpoints
GDPR Art. 7 — Conditions for consent
GDPR Art. 21 — Right to object
GDPR Art. 17 — Right to erasure (triggered by consent withdrawal)
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List, Optional
import json
import logging

from backend.models import UserConsent, ConsentAuditLog, ConsentType, ConsentStatus, DataProcessingRecord, LegalBasis
from backend.database import get_db
from backend.security.auth import get_current_user_id

router = APIRouter(prefix="/user/consent", tags=["consent"])
logger = logging.getLogger(__name__)


# ============================================================================
# Schemas
# ============================================================================

class ConsentGiveRequest(BaseModel):
    """Request to grant consent."""
    consent_types: List[str] = Field(..., description="Types of consent: PRIVACY_POLICY, MARKETING, etc.")
    privacy_policy_version: str = Field(..., description="Version of privacy policy accepted (e.g., 'v2.1')")
    privacy_policy_acknowledged: bool = Field(..., description="Must be True to grant consent")
    privacy_policy_text: Optional[str] = Field(None, description="Full text of privacy policy presented to user")
    consent_mechanism: str = Field(default="EXPLICIT_BUTTON", description="How consent was obtained")

    class Config:
        example = {
            "consent_types": ["PRIVACY_POLICY", "LEAD_GENERATION"],
            "privacy_policy_version": "v2.1",
            "privacy_policy_acknowledged": True,
            "privacy_policy_text": "We process your data for [...]",
            "consent_mechanism": "EXPLICIT_BUTTON"
        }


class ConsentWithdrawRequest(BaseModel):
    """Request to withdraw consent."""
    consent_types: List[str] = Field(..., description="Which consents to withdraw")
    reason: Optional[str] = Field(None, max_length=500, description="Why user withdraws consent")

    class Config:
        example = {
            "consent_types": ["LEAD_GENERATION"],
            "reason": "Changed my mind about marketing"
        }


class ConsentStatusResponse(BaseModel):
    """Consent status for a user."""
    user_id: str
    consents: List[dict]  # {type, status, granted_at, withdrawn_at, expires_at}

    class Config:
        example = {
            "user_id": "user-uuid-123",
            "consents": [
                {
                    "type": "PRIVACY_POLICY",
                    "status": "GRANTED",
                    "granted_at": "2026-05-29T10:00:00Z",
                    "withdrawn_at": None,
                    "expires_at": None
                }
            ]
        }


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/give", status_code=201)
async def grant_consent(
    request: Request,
    body: ConsentGiveRequest,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    POST /user/consent/give
    Grant consent for one or more purposes.

    GDPR Art. 7(4) — Burden of proof on controller.
    Records:
    1. UserConsent entry (with proof of acknowledgment)
    2. DataProcessingRecord (legal basis = CONSENT)
    3. ConsentAuditLog (immutable audit trail)

    Returns:
        {success: bool, consents: List[ConsentStatus]}
    """

    # Validate privacy policy acknowledgment
    if not body.privacy_policy_acknowledged:
        raise HTTPException(
            status_code=400,
            detail="Privacy policy must be explicitly acknowledged (privacy_policy_acknowledged=true)"
        )

    # Get client IP (for forensics)
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "")

    # Parse consent types
    try:
        consent_types = [ConsentType(ct) for ct in body.consent_types]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid consent type: {e}")

    created_consents = []
    try:
        for consent_type in consent_types:
            # Check if this consent already exists
            existing = db.query(UserConsent).filter(
                UserConsent.user_id == current_user_id,
                UserConsent.consent_type == consent_type,
            ).first()

            if existing and existing.status == ConsentStatus.GRANTED:
                # Already granted, skip
                created_consents.append({
                    "type": consent_type.value,
                    "status": "ALREADY_GRANTED",
                    "granted_at": existing.granted_at.isoformat()
                })
                continue

            # Create new consent record
            consent = UserConsent(
                user_id=current_user_id,
                consent_type=consent_type,
                status=ConsentStatus.GRANTED,
                privacy_policy_version=body.privacy_policy_version,
                privacy_policy_accepted=True,
                text_presented=body.privacy_policy_text or "",
                consent_mechanism=body.consent_mechanism,
                granted_at=datetime.utcnow(),
                granted_ip=client_ip,
                granted_user_agent=user_agent,
            )
            db.add(consent)
            db.flush()  # Get ID for audit log

            # Create DataProcessingRecord (GDPR Art. 30)
            processing_record = DataProcessingRecord(
                user_id=current_user_id,
                processor_system="consent_management",
                legal_basis=LegalBasis.CONSENT,
                legal_basis_justification=f"Consent ID: {consent.id}",
                data_categories=json.dumps(["consent_preference", "ip_address", "user_agent"]),
                purpose=f"Record consent for {consent_type.value}",
                retention_period_days=2555,  # 7 years per retention policy
                processing_type="COLLECTION",
                processing_method="Database storage",
                timestamp=datetime.utcnow(),
                ip_address=client_ip,
                user_agent=user_agent,
                request_id=request.headers.get("x-request-id", ""),
            )
            db.add(processing_record)
            db.flush()

            # Create ConsentAuditLog (GDPR Art. 7(5))
            audit_log = ConsentAuditLog(
                user_id=current_user_id,
                user_consent_id=consent.id,
                event_type="GRANTED",
                event_details=json.dumps({
                    "mechanism": body.consent_mechanism,
                    "policy_version": body.privacy_policy_version,
                }),
                ip_address=client_ip,
                user_agent=user_agent,
                timestamp=datetime.utcnow(),
            )
            db.add(audit_log)

            created_consents.append({
                "type": consent_type.value,
                "status": "GRANTED",
                "granted_at": consent.granted_at.isoformat(),
                "processing_record_id": processing_record.id,
            })

            logger.info(f"Consent GRANTED: user_id={current_user_id}, type={consent_type.value}, ip={client_ip}")

        db.commit()

        return {
            "success": True,
            "message": f"Consent granted for {len(created_consents)} item(s)",
            "consents": created_consents,
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Error granting consent: {e}")
        raise HTTPException(status_code=500, detail="Failed to grant consent")


@router.post("/withdraw", status_code=200)
async def withdraw_consent(
    request: Request,
    body: ConsentWithdrawRequest,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    POST /user/consent/withdraw
    Withdraw consent for one or more purposes.

    GDPR Art. 7(3) — Withdrawal of consent is as easy as granting.
    Triggers:
    1. Stop processing under that legal basis immediately
    2. Create ConsentAuditLog entry
    3. Notify third-party processors (DPA compliance)
    4. Flag user data for potential deletion (Art. 17)

    Returns:
        {success: bool, withdrawn: List[str]}
    """

    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "")

    # Parse consent types
    try:
        consent_types = [ConsentType(ct) for ct in body.consent_types]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid consent type: {e}")

    withdrawn = []
    try:
        for consent_type in consent_types:
            # Find existing consent
            consent = db.query(UserConsent).filter(
                UserConsent.user_id == current_user_id,
                UserConsent.consent_type == consent_type,
                UserConsent.status == ConsentStatus.GRANTED,
            ).first()

            if not consent:
                # Not previously granted, skip
                logger.info(f"Consent withdrawal attempt for non-existent consent: {consent_type.value}")
                continue

            # Mark as withdrawn
            consent.status = ConsentStatus.WITHDRAWN
            consent.withdrawn_at = datetime.utcnow()
            consent.withdrawn_reason = body.reason or ""
            consent.withdrawn_ip = client_ip
            db.add(consent)
            db.flush()

            # Create ConsentAuditLog
            audit_log = ConsentAuditLog(
                user_id=current_user_id,
                user_consent_id=consent.id,
                event_type="WITHDRAWN",
                event_details=json.dumps({
                    "reason": body.reason or "Not provided",
                    "timestamp": datetime.utcnow().isoformat(),
                }),
                ip_address=client_ip,
                user_agent=user_agent,
                timestamp=datetime.utcnow(),
            )
            db.add(audit_log)

            # TODO: Notify third-party processors (DPA Art. 28)
            # - SendGrid: remove from marketing list
            # - Payloadez: stop payment processing
            # - AWS S3: flag for eventual deletion
            logger.info(f"Consent WITHDRAWN: user_id={current_user_id}, type={consent_type.value}, ip={client_ip}")

            withdrawn.append(consent_type.value)

        db.commit()

        return {
            "success": True,
            "message": f"Consent withdrawn for {len(withdrawn)} item(s)",
            "withdrawn": withdrawn,
            "note": "Your data will be processed according to GDPR Art. 17 (Right to erasure)"
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Error withdrawing consent: {e}")
        raise HTTPException(status_code=500, detail="Failed to withdraw consent")


@router.get("/status")
async def get_consent_status(
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    GET /user/consent/status
    Retrieve current consent status for user.

    GDPR Art. 15 — Right of access.
    Shows all consents (granted, withdrawn, expired).

    Returns:
        {user_id: str, consents: List[{type, status, granted_at, withdrawn_at, expires_at}]}
    """

    consents = db.query(UserConsent).filter(
        UserConsent.user_id == current_user_id
    ).order_by(UserConsent.created_at.desc()).all()

    consent_list = [
        {
            "type": c.consent_type.value,
            "status": c.status.value,
            "granted_at": c.granted_at.isoformat() if c.granted_at else None,
            "withdrawn_at": c.withdrawn_at.isoformat() if c.withdrawn_at else None,
            "expires_at": c.expires_at.isoformat() if c.expires_at else None,
        }
        for c in consents
    ]

    return {
        "user_id": current_user_id,
        "consents": consent_list,
        "total": len(consent_list),
    }
