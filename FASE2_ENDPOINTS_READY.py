#!/usr/bin/env python3
"""
FASE 2: ENDPOINTS DB INTEGRATION — SPRINT 7 + SPRINT 9 + SPRINT 11
Código LISTO para inyectar en app_couple_endpoints.py cuando Render compile.
Copy-paste directo: reemplaza los TODO stubs con esta implementación.

CRITICAL: Requiere:
  - couple_service: CoupleService instancia con DB session
  - db_session: SQLAlchemy session
"""

from fastapi import FastAPI, HTTPException
from datetime import datetime, timedelta
from psychology_backend_service import PsychologyBackendService
from analytics_events_service import AnalyticsEventsService
from sprint9_ab_testing_adapter import ABTestingAdapter

# ============================================================================
# ENDPOINT 1: GET /api/v1/sessions/{session_id}/urgency
# ============================================================================

async def get_urgency_state_IMPL(session_id: str, couple_service, db_session):
    """
    REEMPLAZAR el TODO stub en app_couple_endpoints.py con esta implementación.
    """
    try:
        session = couple_service.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Obtener estado del timer
        urgency_state = PsychologyBackendService.get_urgency_state(session)

        # Log event
        ab_cohort = getattr(session, 'ab_cohort', 'unknown')
        AnalyticsEventsService.log_timer_viewed(
            db_session,
            session_id,
            int(urgency_state["remaining_seconds"]),
            ab_cohort
        )

        return urgency_state

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


# ============================================================================
# ENDPOINT 2: GET /api/v1/sessions/{session_id}/social-proof
# ============================================================================

async def get_social_proof_IMPL(session_id: str, couple_service, db_session):
    """
    REEMPLAZAR el TODO stub.
    """
    try:
        session = couple_service.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Obtener city
        proof_data = PsychologyBackendService.get_social_proof_data(session)

        # Log event
        ab_cohort = getattr(session, 'ab_cohort', 'unknown')
        AnalyticsEventsService.log_city_viewed(
            db_session,
            session_id,
            proof_data["city"],
            ab_cohort
        )

        return proof_data

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


# ============================================================================
# ENDPOINT 3: GET /api/v1/sessions/{session_id}/fomo-badges
# ============================================================================

async def get_fomo_badges_IMPL(session_id: str, couple_service, db_session):
    """
    REEMPLAZAR el TODO stub.
    """
    try:
        session = couple_service.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Obtener badges
        badges = PsychologyBackendService.get_fomo_badges(session)

        # Log each visible badge
        ab_cohort = getattr(session, 'ab_cohort', 'unknown')
        for tier in ["basic", "professional", "pareja"]:
            key = f"{tier}_spots"
            if key in badges and badges[key] > 0:
                AnalyticsEventsService.log_badge_viewed(
                    db_session,
                    session_id,
                    tier,
                    badges[key],
                    ab_cohort
                )

        return badges

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


# ============================================================================
# ENDPOINT 4: POST /api/v1/tiers/{tier}/click
# ============================================================================

async def on_tier_clicked_IMPL(tier: str, session_id: str, couple_service, db_session):
    """
    REEMPLAZAR el TODO stub.
    Cuando usuario clickea tier: decrementa FOMO spot + log event.
    """
    try:
        session = couple_service.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Decrementa spot
        success = PsychologyBackendService.decrement_fomo_spot(session, tier, db_session)

        if not success:
            raise HTTPException(status_code=400, detail=f"No spots available for {tier}")

        # Log event
        ab_cohort = getattr(session, 'ab_cohort', 'unknown')
        AnalyticsEventsService.log_tier_clicked(db_session, session_id, tier, ab_cohort)

        # Retornar estado actualizado
        badges = PsychologyBackendService.get_fomo_badges(session)
        return {
            "status": "recorded",
            "tier": tier,
            "spots_remaining": badges.get(f"{tier}_spots", 0)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


# ============================================================================
# ENDPOINT 5: POST /api/v1/sessions/create (CON PSYCHOLOGY + A/B)
# ============================================================================

async def create_session_with_psychology_IMPL(couple_id: str, user_a_id: str,
                                              user_b_id: str, couple_service, db_session):
    """
    REEMPLAZAR el TODO stub en app_couple_endpoints.py.

    Crea sesión + inicia psychology mechanics (timer, social proof, FOMO)
    + asigna A/B cohort (50/50 SUPREMO vs CONTROL).

    INTEGRACIÓN CRÍTICA:
    1. Crear sesión en BD
    2. Asignar cohort A/B
    3. Inicializar psychology
    4. Retornar config combinada
    """
    try:
        # 1. Crear sesión en BD
        session = couple_service.create_session(couple_id, user_a_id, user_b_id)
        if not session:
            raise HTTPException(status_code=500, detail="Failed to create session")

        # 2. SPRINT 9: Asignar cohort (50/50)
        cohort = ABTestingAdapter.assign_cohort(couple_id)
        session.ab_cohort = cohort
        session.ab_assigned_at = datetime.utcnow()
        db_session.commit()

        # 3. SPRINT 7: Inicializar psychology (funciona igual para ambos cohorts)
        psychology = PsychologyBackendService.initialize_session_psychology(session, db_session)

        # 4. Obtener feature flags para frontend
        ab_flags = ABTestingAdapter.get_frontend_flags(couple_id)

        # Log session_started event
        AnalyticsEventsService.log_session_started(db_session, couple_id, cohort)

        # 5. Retornar config combinada
        return {
            "session_id": session.id,
            "status": "initialized",
            "ab_cohort": cohort,
            "ab_flags": ab_flags,
            "psychology": psychology,
            "created_at": session.created_at.isoformat(),
            "expires_at": session.expires_at.isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


# ============================================================================
# SPRINT 9: A/B TESTING ENDPOINTS
# ============================================================================

async def get_ab_cohort_config_IMPL(session_id: str, couple_service):
    """
    GET /api/v1/ab-test/cohort/{session_id}
    Retorna configuración A/B para este session (feature flags, pricing, etc.)
    """
    try:
        session = couple_service.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        ab_cohort = getattr(session, 'ab_cohort', 'control')
        flags = ABTestingAdapter.get_frontend_flags(session_id)

        return flags

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


async def log_payment_metric_IMPL(session_id: str, plan: str, success: bool,
                                  time_seconds: float, couple_service, db_session):
    """
    POST /api/v1/ab-test/log-payment
    Registra métrica de pago para A/B testing.
    """
    try:
        session = couple_service.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        ab_cohort = getattr(session, 'ab_cohort', 'unknown')

        # Log payment event
        AnalyticsEventsService.log_payment_attempt(
            db_session, session_id, plan, success, time_seconds, ab_cohort
        )

        return {"status": "logged", "session_id": session_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


# ============================================================================
# SPRINT 11: ANALYTICS ENDPOINTS (Stubs)
# ============================================================================

async def get_live_analytics_IMPL(db_session):
    """
    GET /api/v1/analytics/live
    Métricas en TIEMPO REAL (últimas 24 horas).

    TODO: Implementar cuando AnalyticsEvent esté en BD.
    Por ahora retorna mock.
    """
    return {
        "snapshot_date": datetime.utcnow().date().isoformat(),
        "sessions": {
            "total_created": 0,
            "completed": 0,
            "completion_rate": 0.0
        },
        "conversions": {
            "total": 0,
            "rate": 0.0
        },
        "ab_testing": {
            "supremo": {
                "conversions": 0,
                "conversion_rate": 0.0
            },
            "control": {
                "conversions": 0,
                "conversion_rate": 0.0
            },
            "lift": 0.0
        }
    }


# ============================================================================
# INTEGRATION SUMMARY
# ============================================================================

"""
INYECCIÓN REQUERIDA EN app_couple_endpoints.py:

1. IMPORTS (línea 24-26):
   from psychology_backend_service import PsychologyBackendService
   from analytics_events_service import AnalyticsEventsService
   from sprint9_ab_testing_adapter import ABTestingAdapter

2. INSTANCIA DE couple_service CON DB SESSION:
   from couple_management import CoupleService, get_db_session

   # Al inicio de app startup:
   db_session = get_db_session()
   couple_service = CoupleService(session=db_session)

3. REEMPLAZAR ENDPOINTS:
   - get_urgency_state() → usar get_urgency_state_IMPL()
   - get_social_proof() → usar get_social_proof_IMPL()
   - get_fomo_badges() → usar get_fomo_badges_IMPL()
   - on_tier_clicked() → usar on_tier_clicked_IMPL()
   - create_session_with_psychology() → usar create_session_with_psychology_IMPL()

4. AGREGAR ENDPOINTS A/B + ANALYTICS:
   - GET /api/v1/ab-test/cohort/{session_id} → get_ab_cohort_config_IMPL()
   - POST /api/v1/ab-test/log-payment → log_payment_metric_IMPL()
   - GET /api/v1/analytics/live → get_live_analytics_IMPL()

CRÍTICO:
- couple_service debe ser singleton para evitar múltiples conexiones DB
- db_session debe limpiarse al finalizar requests (usar FastAPI Depends)
- Migraciones de BD necesarias para nuevas columnas + AnalyticsEvent tabla
"""
