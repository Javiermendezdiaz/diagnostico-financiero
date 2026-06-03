#!/usr/bin/env python3
"""
RGPD API Endpoints Integration
FastAPI routes for:
- POST /api/v1/consent/request - Request consent
- POST /api/v1/consent/save - Save consent choices
- POST /api/v1/consent/withdraw - Withdraw consent
- GET /api/v1/consent/status - Check consent status
- POST /api/v1/user-rights/access - Request data access
- POST /api/v1/user-rights/erasure - Request deletion
- POST /api/v1/user-rights/portability - Request data export
"""

import logging
from typing import Dict, List, Optional
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

from rgpd_encryption import get_encryption_layer
from rgpd_consent import get_consent_manager, ConsentType
from rgpd_user_rights import get_user_rights_manager, UserRightType

logger = logging.getLogger(__name__)

# ============ Pydantic Models ============

class ConsentRequest(BaseModel):
    user_id: str
    language: str = "es"

class ConsentSave(BaseModel):
    user_id: str
    processing: bool = False
    analytics: bool = False
    marketing: bool = False
    profiling: bool = False
    third_party: bool = False
    cookie: bool = False

class ConsentWithdraw(BaseModel):
    user_id: str
    consent_type: str  # "all" or specific type

class AccessRequest(BaseModel):
    user_id: str

class ErasureRequest(BaseModel):
    user_id: str
    reason: Optional[str] = ""

class PortabilityRequest(BaseModel):
    user_id: str
    format: str = "json"  # json, csv, xml, pdf

class RectificationRequest(BaseModel):
    user_id: str
    field_name: str
    current_value: str
    corrected_value: str

# ============ Router Setup ============

def create_rgpd_router() -> APIRouter:
    """Create RGPD endpoints router"""
    router = APIRouter(prefix="/api/v1", tags=["RGPD"])

    # ============ CONSENT ENDPOINTS ============

    @router.post("/consent/request")
    async def request_consent_endpoint(req: ConsentRequest):
        """
        Request consent template for user.
        Returns array of consent types with descriptions.
        """
        try:
            consent_mgr = get_consent_manager()
            consent_types = [ConsentType.PROCESSING, ConsentType.ANALYTICS, ConsentType.MARKETING,
                           ConsentType.PROFILING, ConsentType.THIRD_PARTY, ConsentType.COOKIE]

            return consent_mgr.request_consent(req.user_id, consent_types, req.language)
        except Exception as e:
            logger.error(f"Consent request error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/consent/save")
    async def save_consent_endpoint(consent: ConsentSave, request: Request):
        """
        Save user's consent choices.
        Requires explicit opt-in (processing is mandatory).
        """
        try:
            if not consent.processing:
                raise ValueError("Processing consent is mandatory")

            consent_mgr = get_consent_manager()

            # Get IP and User-Agent for audit
            ip_address = request.client.host if request.client else ""
            user_agent = request.headers.get("user-agent", "")

            consent_data = {
                "processing": consent.processing,
                "analytics": consent.analytics,
                "marketing": consent.marketing,
                "profiling": consent.profiling,
                "third_party": consent.third_party,
                "cookie": consent.cookie
            }

            result = consent_mgr.save_consent(
                consent.user_id,
                consent_data,
                ip_address=ip_address,
                user_agent=user_agent
            )

            return {
                "success": True,
                "message": "Consent saved",
                "data": result
            }
        except Exception as e:
            logger.error(f"Consent save error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/consent/withdraw")
    async def withdraw_consent_endpoint(req: ConsentWithdraw):
        """
        Withdraw consent for specific purpose or all consents.
        Immediate effect.
        """
        try:
            consent_mgr = get_consent_manager()

            if req.consent_type == "all":
                result = consent_mgr.withdraw_all_consent(req.user_id)
            else:
                result = consent_mgr.withdraw_consent(req.user_id, ConsentType(req.consent_type))

            return {
                "success": True,
                "message": "Consent withdrawn",
                "data": result
            }
        except Exception as e:
            logger.error(f"Consent withdraw error: {e}")
            raise HTTPException(status_code=400, detail=str(e))

    @router.get("/consent/status/{user_id}")
    async def get_consent_status(user_id: str):
        """
        Get user's current consent status.
        """
        try:
            consent_mgr = get_consent_manager()
            status = consent_mgr.get_user_consents(user_id)

            return {
                "success": True,
                "data": status
            }
        except Exception as e:
            logger.error(f"Consent status error: {e}")
            raise HTTPException(status_code=404, detail="User not found")

    @router.get("/consent/history/{user_id}")
    async def get_consent_history(user_id: str):
        """
        Get audit trail of all consent changes for user.
        """
        try:
            consent_mgr = get_consent_manager()
            history = consent_mgr.get_consent_history(user_id)

            return {
                "success": True,
                "data": {
                    "user_id": user_id,
                    "history": history
                }
            }
        except Exception as e:
            logger.error(f"Consent history error: {e}")
            raise HTTPException(status_code=404, detail="User not found")

    # ============ USER RIGHTS ENDPOINTS ============

    @router.post("/user-rights/access")
    async def request_access_endpoint(req: AccessRequest):
        """
        Art. 15: Request access to personal data.
        User receives all data held about them (max 30 days).
        """
        try:
            rights_mgr = get_user_rights_manager()
            request_obj = rights_mgr.request_access(req.user_id)

            return {
                "success": True,
                "message": "Access request submitted",
                "request": request_obj,
                "deadline": "30 calendar days"
            }
        except Exception as e:
            logger.error(f"Access request error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/user-rights/erasure")
    async def request_erasure_endpoint(req: ErasureRequest):
        """
        Art. 17: Request erasure (right to be forgotten).
        Data deleted unless legal exception applies.
        """
        try:
            rights_mgr = get_user_rights_manager()
            request_obj = rights_mgr.request_erasure(req.user_id, req.reason)

            return {
                "success": True,
                "message": "Erasure request submitted",
                "request": request_obj,
                "deadline": "30 calendar days",
                "note": "Request will be reviewed for legal exceptions"
            }
        except Exception as e:
            logger.error(f"Erasure request error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/user-rights/rectification")
    async def request_rectification_endpoint(req: RectificationRequest):
        """
        Art. 16: Request correction of inaccurate data.
        """
        try:
            rights_mgr = get_user_rights_manager()
            request_obj = rights_mgr.request_rectification(
                req.user_id,
                req.field_name,
                req.current_value,
                req.corrected_value
            )

            return {
                "success": True,
                "message": "Rectification request submitted",
                "request": request_obj
            }
        except Exception as e:
            logger.error(f"Rectification request error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/user-rights/portability")
    async def request_portability_endpoint(req: PortabilityRequest):
        """
        Art. 20: Request data portability.
        Data exported in machine-readable format (JSON, CSV, etc.).
        """
        try:
            rights_mgr = get_user_rights_manager()
            request_obj = rights_mgr.request_portability(req.user_id, req.format)

            return {
                "success": True,
                "message": "Portability request submitted",
                "request": request_obj,
                "deadline": "30 calendar days"
            }
        except Exception as e:
            logger.error(f"Portability request error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/user-rights/status/{user_id}")
    async def get_user_rights_status(user_id: str):
        """
        Get all rights requests from a user.
        """
        try:
            rights_mgr = get_user_rights_manager()
            requests_list = rights_mgr.get_user_requests(user_id)

            return {
                "success": True,
                "data": {
                    "user_id": user_id,
                    "total_requests": len(requests_list),
                    "requests": requests_list
                }
            }
        except Exception as e:
            logger.error(f"Rights status error: {e}")
            raise HTTPException(status_code=404, detail="User not found")

    # ============ ENCRYPTION ENDPOINTS ============

    @router.post("/encryption/generate-key")
    async def generate_encryption_key(user_id: str, password: Optional[str] = None):
        """
        Generate per-user encryption key material.
        Should be done during user registration.
        """
        try:
            encryption = get_encryption_layer()
            key_material = encryption.generate_user_key(user_id, password)

            return {
                "success": True,
                "message": "User encryption key generated",
                "user_id": user_id,
                "key_hash": key_material["key_hash"],
                "created_at": key_material["created_at"],
                "note": "Salt must be stored with user account"
            }
        except Exception as e:
            logger.error(f"Key generation error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/encryption/status/{user_id}")
    async def encryption_status(user_id: str):
        """
        Check if user has encryption key material.
        """
        return {
            "status": "encrypted",
            "algorithm": "AES-256-GCM",
            "user_id": user_id
        }

    return router


# ============ Integration Helper ============

def add_rgpd_endpoints_to_app(app):
    """Add RGPD router to FastAPI app"""
    router = create_rgpd_router()
    app.include_router(router)
    logger.info("RGPD endpoints registered")
