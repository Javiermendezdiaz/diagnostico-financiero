#!/usr/bin/env python3
"""
APP COUPLE ENDPOINTS — FASE 2 Sprint 3
FastAPI endpoint orquestador para Espejo Fantasma.
TOP 1% MUNDIAL — INSTITUTIONAL GRADE
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from typing import Dict, Optional, List, Any
from datetime import datetime, timedelta
import uuid
import json
import logging
# import stripe
import os
import hmac
import hashlib

# SPRINT 7 + SPRINT 9 + SPRINT 11 imports
from psychology_backend_service import PsychologyBackendService
from analytics_events_service import AnalyticsEventsService
from sprint9_ab_testing_adapter import ABTestingAdapter
from couple_management import CoupleService, get_db_session

logger = logging.getLogger(__name__)

# ============================================================================
# GLOBAL INSTANCES — DB SESSION + COUPLE SERVICE
# ============================================================================
# CRITICAL: Inicializar en startup para inyección de dependencias
_db_session = None
_couple_service = None

@app.on_event("startup")
async def startup_services():
    """Inicializa servicios globales al arrancar FastAPI"""
    global _db_session, _couple_service
    try:
        _db_session = get_db_session()
        _couple_service = CoupleService(session=_db_session)
        logger.info("✅ DB Session + CoupleService inicializados correctamente")
    except Exception as e:
        logger.error(f"❌ Error al inicializar servicios: {e}")

def get_couple_service():
    """Dependency injection para endpoints"""
    return _couple_service

def get_db():
    """Dependency injection para BD"""
    return _db_session

# ============================================================================
# SCHEMAS
# ============================================================================

class AnswerSubmission(BaseModel):
    """Modelo para envío de respuestas pareadas"""
    couple_id: str = Field(..., description="ID único de pareja")
    user_a_answers: Dict[int, int] = Field(..., description="500 respuestas usuario A (q1-q500)")
    user_b_answers: Dict[int, int] = Field(..., description="500 respuestas usuario B (q1-q500)")
    token_a: str = Field(..., description="Magic token validación usuario A")
    token_b: str = Field(..., description="Magic token validación usuario B")


class DiagnosticResponse(BaseModel):
    """Respuesta del endpoint de diagnóstico"""
    status: str
    couple_id: str
    compatibility_score: float
    shield_score: float
    runway_days: int
    tiene_hijos: bool
    high_ticket_trigger: bool
    pdf_url: Optional[str] = None
    expires_at: str
    compatibility_narrative: str
    upsell_message: str


class PingResponse(BaseModel):
    """Health check"""
    status: str
    timestamp: str


class ScoringPayload(BaseModel):
    """Payload para extracción de insight asimétrico"""
    answers: Dict[str, Any]


# ============================================================================
# FASTAPI APP
# ============================================================================

app = FastAPI(
    title="Adapta Family Office - Simulador de Exposición Patrimonial",
    description="Diagnóstico Financiero de Pareja — TOP 1% MUNDIAL",
    version="3.0.0-institutional"
)

# ============================================================================
# CORS CONFIGURATION - Blindaje Absoluto
# ============================================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.get("/ping", response_model=PingResponse, tags=["Health"])
async def ping():
    """Health check endpoint"""
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "environment": "institutional_production"
    }


# ============================================================================
# PASO 3: Endpoint de Espejo Estricto (Insight de Alta Dirección)
# ============================================================================

@app.post("/api/v1/ux/extract-key-insight", tags=["UX"])
async def extract_key_insight(payload: ScoringPayload):
    """
    Extrae el insight asimétrico basado en el peor dolor del usuario.
    PIVOTE ESTRATÉGICO 1% TOP: Habla al miedo REAL según el perfil.
    """
    answers = payload.answers
    ingresos = float(answers.get("ingresos", 0))
    colchon = answers.get("colchon_emergencia")
    seguros = answers.get("seguro_vida")
    estructura = answers.get("estructura_legal")
    sucesion = answers.get("sucesion")

    # ========================================================================
    # PIVOTE CRÍTICO: Ingresos moderados (≤€50k) + sin colchón + sin seguros
    # = URGENCIA LABORAL INMEDIATA (miedo real, ahora mismo)
    # ========================================================================
    if ingresos <= 50000 and colchon == "NO" and seguros == "NO":
        riesgo_mensual = int(ingresos / 12)
        return {
            "critical_insight": f"Atención: Exposición crítica sin cobertura de contingencia. Si pierdes tu capacidad de trabajo, tu familia tiene 0 meses de fondo de reserva. Una baja de 6 meses = pérdida de €{riesgo_mensual * 6:,.0f} de ingresos = endeudamiento total.",
            "target_area": "urgencia_laboral",
            "severity": "critical",
            "riesgo_mensual": riesgo_mensual,
            "cta_text": "🚨 Desbloquear Plan de Contingencia Inmediata"
        }

    # ========================================================================
    # INGRESOS ALTOS (>€80k) + SIN ESTRUCTURA = IRPF asimétrico
    # ========================================================================
    if estructura == "NO_SL" and ingresos > 80000:
        ahorro_anual = int(ingresos * 0.15)
        return {
            "critical_insight": f"Alerta de Eficiencia Fiscal: Sus ingresos (€{int(ingresos):,.0f}/año) están siendo tributados al máximo nivel de IRPF sin estructura societaria. Potencial ahorro anual: €{ahorro_anual:,.0f}.",
            "target_area": "estructura",
            "severity": "high",
            "ahorro_potencial": ahorro_anual,
            "cta_text": "✨ Acceder a la Optimización Fiscal Latente"
        }

    # ========================================================================
    # SIN PLAN DE SUCESIÓN + PATRIMONIO CONSOLIDADO (>€80k ingresos)
    # ========================================================================
    if sucesion == "NO" and ingresos > 80000:
        return {
            "critical_insight": "Vulnerabilidad Sucesoria: Sin protocolo de transmisión blindado, sus herederos enfrentarán tributación completa del Impuesto de Sucesiones. Exposición potencial: 15-30% del patrimonio.",
            "target_area": "sucesion",
            "severity": "high",
            "cta_text": "✨ Desbloquear Arquitectura Sucesoria Premium"
        }

    # ========================================================================
    # CONTINGENCIA LABORAL sin seguros (cualquier nivel de ingresos)
    # ========================================================================
    if seguros == "NO":
        return {
            "critical_insight": "Vulnerabilidad de Liquidez: Ausencia de cobertura de contingencia laboral. Ante enfermedad o accidente, no hay mecanismo automático de protección de ingresos familiares.",
            "target_area": "seguros",
            "severity": "high",
            "cta_text": "✨ Estructurar Cobertura de Seguros"
        }

    # ========================================================================
    # SIN COLCHÓN de emergencia (cualquier nivel)
    # ========================================================================
    if colchon == "NO":
        return {
            "critical_insight": "Exposición de Tesorería: Carencia de fondo de reserva estratégico. Cualquier gasto imprevisto forzará endeudamiento de corto plazo.",
            "target_area": "tesoreria",
            "severity": "medium",
            "cta_text": "✨ Desbloquear Informe y Agendar Validación"
        }

    # ========================================================================
    # TODO BLINDADO - Estructura óptima
    # ========================================================================
    return {
        "critical_insight": "Análisis completado. Su estructura patrimonial está blindada en los aspectos críticos. Se recomienda revisión anual para optimizaciones menores.",
        "target_area": "general",
        "severity": "low",
        "cta_text": "✨ Desbloquear Informe y Agendar Validación"
    }


# ============================================================================
# SPRINT 7: PSYCHOLOGY ENDPOINTS
# ============================================================================

@app.get("/api/v1/sessions/{session_id}/urgency", tags=["Psychology"])
async def get_urgency_state(session_id: str, couple_service: CoupleService = Depends(get_couple_service), db_session = Depends(get_db)):
    """
    Retorna estado actual del timer urgency (SPRINT 7 + SPRINT 9).
    Frontend llama cada segundo para actualizar countdown.
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

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.get("/api/v1/sessions/{session_id}/social-proof", tags=["Psychology"])
async def get_social_proof(session_id: str, couple_service: CoupleService = Depends(get_couple_service), db_session = Depends(get_db)):
    """
    Retorna ciudad asignada para este session (SPRINT 7 + SPRINT 9).
    Social proof: "X usuarios en [Ciudad] completaron el análisis esta semana".
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

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.get("/api/v1/sessions/{session_id}/fomo-badges", tags=["Psychology"])
async def get_fomo_badges(session_id: str, couple_service: CoupleService = Depends(get_couple_service), db_session = Depends(get_db)):
    """
    Retorna spots disponibles por tier (SPRINT 7 + SPRINT 9).
    FOMO badge: "Solo 2 spots disponibles en el plan Básico".
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

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.post("/api/v1/tiers/{tier}/click", tags=["Psychology"])
async def on_tier_clicked(tier: str, session_id: str, couple_service: CoupleService = Depends(get_couple_service), db_session = Depends(get_db)):
    """
    Cuando usuario hace click en tier (SPRINT 7 + SPRINT 9).
    Decrementa FOMO spot + log event para analytics.
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


@app.post("/api/v1/sessions/create", tags=["Sessions"])
async def create_session_with_psychology(couple_id: str, user_a_id: str, user_b_id: str, couple_service: CoupleService = Depends(get_couple_service), db_session = Depends(get_db)):
    """
    SPRINT 7 + SPRINT 9 + SPRINT 11 versión completa (FASE 2).
    Crea sesión + inicia psychology mechanics + asigna A/B cohort (50/50).

    INTEGRACIÓN CRÍTICA:
    1. Crear sesión en BD
    2. Asignar cohort A/B (50/50)
    3. Inicializar psychology (timer, social proof, FOMO)
    4. Retornar config combinada con feature flags
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

@app.get("/api/v1/ab-test/cohort/{session_id}", tags=["A/B Testing"])
async def get_ab_cohort_config(session_id: str, couple_service: CoupleService = Depends(get_couple_service)):
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

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.post("/api/v1/ab-test/log-payment", tags=["A/B Testing"])
async def log_payment_metric(session_id: str, plan: str, success: bool, time_seconds: float, couple_service: CoupleService = Depends(get_couple_service), db_session = Depends(get_db)):
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
# SERVIR HTML DIRECTAMENTE (Elimina erro de file://)
# ============================================================================

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def serve_portal():
    """Inyecta el HTML institucional directamente desde FastAPI"""
    try:
        with open("frontend_couple_interface_STRIPE_SUPREMO.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>Error 404: Portal no disponible</h1>"


# ============================================================================
# STRIPE INITIALIZATION
# ============================================================================

# stripe.api_key = os.getenv("STRIPE_API_KEY", os.getenv("STRIPE_API_KEY_PROD", "sk_live_test_placeholder"))
# STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "whsec_test_placeholder")


if __name__ == "__main__":
    import uvicorn
    # Lee el puerto dinámico de Render o usa el 8000 en local
    port = int(os.environ.get("PORT", 8000))
    # Usa 0.0.0.0 para producción o 127.0.0.1 en local
    host = "0.0.0.0" if os.environ.get("PORT") else "127.0.0.1"
    uvicorn.run(app, host=host, port=port, log_level="info")
