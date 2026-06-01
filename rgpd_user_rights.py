#!/usr/bin/env python3
"""
RGPD Foundation: User Rights Management
GDPR Arts. 15-20: Access, Rectification, Erasure, Restriction, Portability, Objection
"""

import json
import logging
from datetime import datetime
from typing import Dict, Optional, List
from enum import Enum

logger = logging.getLogger(__name__)

class UserRightType(str, Enum):
    """GDPR User Rights"""
    ACCESS = "access"              # Art. 15: Right to access
    RECTIFICATION = "rectification"  # Art. 16: Right to correct data
    ERASURE = "erasure"            # Art. 17: Right to be forgotten
    RESTRICTION = "restriction"    # Art. 18: Right to restrict processing
    PORTABILITY = "portability"    # Art. 20: Right to data portability
    OBJECTION = "objection"        # Art. 21: Right to object


class UserRightsManager:
    """
    Handle GDPR user rights requests with audit trail.

    - User can request access to their data
    - User can request correction of inaccurate data
    - User can request deletion (right to be forgotten)
    - User can restrict processing
    - User can download data (portability)
    - User can object to processing

    All requests logged with timestamps and compliance notes.
    """

    def __init__(self):
        self.requests = {}  # {user_id: [{...}, ...]}
        self.request_queue = []  # For processing by compliance team

    def request_access(self, user_id: str) -> Dict:
        """
        Art. 15: Right to access personal data.
        User receives all data held about them.
        """
        request_id = f"AR-{user_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        request = {
            "request_id": request_id,
            "user_id": user_id,
            "type": UserRightType.ACCESS.value,
            "status": "pending",  # pending → processing → completed
            "requested_at": datetime.utcnow().isoformat(),
            "deadline": "30 days from request",  # GDPR: 30 days to respond
            "legal_basis": "GDPR Art. 15 - Right of access by the data subject"
        }

        if user_id not in self.requests:
            self.requests[user_id] = []

        self.requests[user_id].append(request)
        self.request_queue.append(request)

        logger.info(f"Access request {request_id} from {user_id}")

        return request

    def request_rectification(self, user_id: str, field_name: str, current_value: str, corrected_value: str) -> Dict:
        """
        Art. 16: Right to rectification (correct inaccurate data).
        """
        request_id = f"REC-{user_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        request = {
            "request_id": request_id,
            "user_id": user_id,
            "type": UserRightType.RECTIFICATION.value,
            "status": "pending",
            "requested_at": datetime.utcnow().isoformat(),
            "field_name": field_name,
            "current_value": current_value,
            "corrected_value": corrected_value,
            "legal_basis": "GDPR Art. 16 - Right to rectification"
        }

        if user_id not in self.requests:
            self.requests[user_id] = []

        self.requests[user_id].append(request)
        self.request_queue.append(request)

        logger.info(f"Rectification request {request_id} from {user_id}")

        return request

    def request_erasure(self, user_id: str, reason: str = "") -> Dict:
        """
        Art. 17: Right to erasure (right to be forgotten).
        Must be granted unless:
        - Data still needed for original purpose
        - Legal obligation to keep data
        - Legitimate interest in keeping data (can be overridden)
        """
        request_id = f"DEL-{user_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        request = {
            "request_id": request_id,
            "user_id": user_id,
            "type": UserRightType.ERASURE.value,
            "status": "pending",
            "requested_at": datetime.utcnow().isoformat(),
            "reason": reason,
            "deadline": "30 days from request",
            "legal_basis": "GDPR Art. 17 - Right to erasure (right to be forgotten)",
            "exceptions": [
                "Data still needed for original purpose",
                "Legal obligation to retain data",
                "Legitimate interest (can be overridden by user rights)",
                "Public interest in archival/historical research"
            ]
        }

        if user_id not in self.requests:
            self.requests[user_id] = []

        self.requests[user_id].append(request)
        self.request_queue.append(request)

        logger.warning(f"Erasure request {request_id} from {user_id} - CRITICAL: Review exceptions")

        return request

    def request_restriction(self, user_id: str, processing_purpose: str, reason: str = "") -> Dict:
        """
        Art. 18: Right to restrict processing.
        Data can still be stored but not processed.
        """
        request_id = f"RES-{user_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        request = {
            "request_id": request_id,
            "user_id": user_id,
            "type": UserRightType.RESTRICTION.value,
            "status": "pending",
            "requested_at": datetime.utcnow().isoformat(),
            "processing_purpose": processing_purpose,
            "reason": reason,
            "deadline": "30 days from request",
            "legal_basis": "GDPR Art. 18 - Right to restrict processing",
            "effect": "Data marked as restricted; processing stopped except with user consent or legal obligation"
        }

        if user_id not in self.requests:
            self.requests[user_id] = []

        self.requests[user_id].append(request)
        self.request_queue.append(request)

        logger.info(f"Restriction request {request_id} from {user_id}")

        return request

    def request_portability(self, user_id: str, format: str = "json") -> Dict:
        """
        Art. 20: Right to data portability.
        User receives data in structured, commonly used, machine-readable format.
        """
        request_id = f"PORT-{user_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        request = {
            "request_id": request_id,
            "user_id": user_id,
            "type": UserRightType.PORTABILITY.value,
            "status": "pending",
            "requested_at": datetime.utcnow().isoformat(),
            "format": format,  # json, csv, xml, pdf
            "deadline": "30 days from request",
            "legal_basis": "GDPR Art. 20 - Right to data portability",
            "note": "Data must be in structured, commonly used, machine-readable format (JSON, CSV, etc.)"
        }

        if user_id not in self.requests:
            self.requests[user_id] = []

        self.requests[user_id].append(request)
        self.request_queue.append(request)

        logger.info(f"Portability request {request_id} from {user_id} - Format: {format}")

        return request

    def request_objection(self, user_id: str, processing_purpose: str, reason: str = "") -> Dict:
        """
        Art. 21: Right to object.
        User can object to processing for marketing, automated decision-making, etc.
        """
        request_id = f"OBJ-{user_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        request = {
            "request_id": request_id,
            "user_id": user_id,
            "type": UserRightType.OBJECTION.value,
            "status": "pending",
            "requested_at": datetime.utcnow().isoformat(),
            "processing_purpose": processing_purpose,
            "reason": reason,
            "deadline": "30 days to respond",
            "legal_basis": "GDPR Art. 21 - Right to object",
            "types": [
                "Direct marketing",
                "Automated decision-making with legal effect",
                "Scientific/historical research",
                "Statistical purposes"
            ]
        }

        if user_id not in self.requests:
            self.requests[user_id] = []

        self.requests[user_id].append(request)
        self.request_queue.append(request)

        logger.info(f"Objection request {request_id} from {user_id}")

        return request

    def get_user_requests(self, user_id: str) -> List[Dict]:
        """Get all rights requests from a user"""
        return self.requests.get(user_id, [])

    def get_pending_requests(self) -> List[Dict]:
        """Get all pending requests for compliance team review"""
        return [r for r in self.request_queue if r["status"] == "pending"]

    def fulfill_request(self, request_id: str, data: Optional[Dict] = None) -> Dict:
        """
        Mark request as fulfilled and provide data if applicable.
        """
        # Find request
        request = None
        for user_requests in self.requests.values():
            for r in user_requests:
                if r["request_id"] == request_id:
                    request = r
                    break

        if not request:
            raise ValueError(f"Request {request_id} not found")

        request["status"] = "completed"
        request["fulfilled_at"] = datetime.utcnow().isoformat()

        if data:
            request["data"] = data

        logger.info(f"Request {request_id} fulfilled at {request['fulfilled_at']}")

        return request

    def deny_request(self, request_id: str, reason: str) -> Dict:
        """
        Deny a user rights request with explanation.
        Must cite legal exception.
        """
        # Find request
        request = None
        for user_requests in self.requests.values():
            for r in user_requests:
                if r["request_id"] == request_id:
                    request = r
                    break

        if not request:
            raise ValueError(f"Request {request_id} not found")

        request["status"] = "denied"
        request["denied_at"] = datetime.utcnow().isoformat()
        request["denial_reason"] = reason

        logger.warning(f"Request {request_id} denied: {reason}")

        return request

    def export_request_log(self, user_id: str) -> Dict:
        """Export all requests from a user (for transparency/audit)"""
        return {
            "user_id": user_id,
            "total_requests": len(self.requests.get(user_id, [])),
            "requests": self.requests.get(user_id, []),
            "exported_at": datetime.utcnow().isoformat()
        }


# Singleton instance
_user_rights_manager = None

def get_user_rights_manager() -> UserRightsManager:
    """Get or create the user rights manager singleton"""
    global _user_rights_manager
    if _user_rights_manager is None:
        _user_rights_manager = UserRightsManager()
    return _user_rights_manager
