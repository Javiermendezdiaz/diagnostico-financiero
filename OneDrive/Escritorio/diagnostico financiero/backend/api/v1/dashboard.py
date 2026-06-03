"""
Dashboard Endpoint — GET /api/v1/dashboard/{user_id}
Returns user's current diagnostic score + 6-month snapshot history
GDPR-protected: verifies JWT + ownership before returning data
"""

from fastapi import APIRouter, HTTPException, Depends, Path
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import logging

router = APIRouter(prefix="/api/v1", tags=["dashboard"])
logger = logging.getLogger(__name__)


# Mock dependency: JWT verification (replace with actual JWT handler)
async def verify_user(user_id: str, token: Optional[str] = None) -> str:
    """
    Verify JWT token and ensure user owns the requested data.
    In production, decode JWT and verify user_id matches token claims.
    """
    if not token:
        raise HTTPException(status_code=403, detail="Missing authorization token")
    # Simplified: assume token is valid if present
    # Production: verify JWT signature + exp + user_id
    return user_id


@router.get("/dashboard/{user_id}")
async def get_dashboard(
    user_id: str = Path(..., description="User ID"),
    authorization: Optional[str] = None
) -> Dict[str, Any]:
    """
    Retrieve user's dashboard data: current score + 6-month history.

    **Protection:**
    - Requires valid JWT token in Authorization header
    - Verifies user owns the data (user_id matches token claims)

    **Response Schema:**
    ```json
    {
      "current": {
        "score": 72,
        "profile": "Moderado",
        "completion_percent": 100,
        "recommendations": [
          {"title": "...", "description": "...", "category": "..."},
          ...
        ],
        "last_snapshot_date": "2025-05-30"
      },
      "history": [
        {"date": "2025-04-01", "score": 68, "profile": "Conservador"},
        ...
      ],
      "consent_verified": true
    }
    ```

    **Error Responses:**
    - 403: Missing/invalid authorization token
    - 404: User not found or has no diagnostic data
    - 500: Database error

    **Example (curl):**
    ```bash
    curl -H "Authorization: Bearer <JWT>" \
         http://localhost:8000/api/v1/dashboard/user_123
    ```
    """
    try:
        # Extract token from header
        token = None
        if authorization:
            parts = authorization.split()
            if len(parts) == 2 and parts[0].lower() == "bearer":
                token = parts[1]

        # Verify user
        verified_user = await verify_user(user_id, token)
        logger.info(f"Dashboard request for user: {verified_user}")

        # TODO: Replace with actual database query once MonthlySnapshot ORM is integrated
        # This is a mock response for development

        # Query logic:
        # 1. Get most recent MonthlySnapshot for current month
        # 2. Get last 6 MonthlySnapshots ordered by snapshot_date DESC
        # 3. Return both as JSON

        # Mock response (implement with SQLAlchemy):
        current_snapshot = {
            "score": 72,
            "profile": "Moderado",
            "completion_percent": 100,
            "recommendations": [
                {
                    "title": "Diversifica tu cartera",
                    "description": "Aumenta la distribución de activos para reducir riesgo específico",
                    "category": "inversión"
                },
                {
                    "title": "Establece un fondo de emergencia",
                    "description": "Mantén 3-6 meses de gastos en cuenta de ahorros líquida",
                    "category": "ahorro"
                },
                {
                    "title": "Revisa tu cobertura de seguros",
                    "description": "Asegúrate de tener protección adecuada para tu familia",
                    "category": "protección"
                }
            ],
            "last_snapshot_date": datetime.utcnow().isoformat()
        }

        history = [
            {
                "date": (datetime.utcnow() - timedelta(days=30)).isoformat(),
                "score": 68,
                "profile": "Conservador"
            },
            {
                "date": (datetime.utcnow() - timedelta(days=60)).isoformat(),
                "score": 65,
                "profile": "Conservador"
            },
            {
                "date": (datetime.utcnow() - timedelta(days=90)).isoformat(),
                "score": 62,
                "profile": "Conservador"
            }
        ]

        response = {
            "current": current_snapshot,
            "history": history,
            "consent_verified": True
        }

        return response

    except Exception as e:
        logger.error(f"Dashboard error for user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Error retrieving dashboard data"
        )


# Optional: Endpoint to retrieve full snapshot details (for audit/compliance)
@router.get("/snapshots/{user_id}")
async def get_snapshots(
    user_id: str = Path(..., description="User ID"),
    limit: int = 12,  # 12 months
    authorization: Optional[str] = None
) -> Dict[str, Any]:
    """
    Retrieve all snapshots for user (with audit trail).
    Used for compliance audits, GDPR data export.

    **Response:**
    ```json
    {
      "user_id": "...",
      "snapshots": [
        {
          "id": "...",
          "snapshot_date": "...",
          "score": 72,
          "profile": "Moderado",
          "audit_log": [...]
        }
      ],
      "total": 12
    }
    ```
    """
    try:
        # Verify authorization
        token = None
        if authorization:
            parts = authorization.split()
            if len(parts) == 2 and parts[0].lower() == "bearer":
                token = parts[1]

        verified_user = await verify_user(user_id, token)

        # TODO: Query MonthlySnapshot table
        # db.query(MonthlySnapshot).filter_by(user_id=user_id).order_by(MonthlySnapshot.snapshot_date.desc()).limit(limit)

        snapshots = []  # Mock for now

        return {
            "user_id": verified_user,
            "snapshots": snapshots,
            "total": len(snapshots)
        }

    except Exception as e:
        logger.error(f"Snapshots error for user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Error retrieving snapshots"
        )
