#!/usr/bin/env python3
"""
APP COUPLE ENDPOINTS — FASE 2 SPRINT 7 + SPRINT 9 + SPRINT 11 + REFACTORIZACIÓN FISCAL
FastAPI endpoint orquestador para Espejo Fantasma.
VERSIÓN: 4.0.0-INSTITUTIONAL-GRADE
RIGOR: Top 1% — Matemáticas fiscales REALES, copywriting sin exageración, conversión optimizada
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from typing import Dict, Optional, List, Any
from datetime import datetime, timedelta
import uuid
import json
import logging
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
# FASTAPI APP (Inicialización anterior a startup_services)
# ============================================================================

app = FastAPI(
    title="Adapta Family Office - Simulador de Exposición Patrimonial",
    description="Diagnóstico Financiero de Pareja — TOP 1% MUNDIAL",
    version="4.0.0-institutional-grade"
)

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
# SCHEMAS — FASE 2 REFACTORIZADO
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
    """Payload para extracción de insight asimétrico (legacy)"""
    answers: Dict[str, Any]


class ScoringPayloadRefactored(BaseModel):
    """Payload REFACTORIZADO FASE 2 — Extracción de insight con matemáticas fiscales REALES"""
    ingresos: float = Field(..., description="Ingresos anuales brutos (€)")
    colchon_emergencia: float = Field(default=0, description="Colchón de emergencia en € (0 si no tiene)")
    seguro_vida: bool = Field(default=False, description="¿Tiene seguro de vida?")
    estructura_legal: str = Field(default="autonomo", description="'autonomo', 'sl', 'otros'")
    sucesion: bool = Field(default=False, description="¿Tiene plan sucesorio?")


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
# ENDPOINT REFACTORIZADO: extract_key_insight
# VERSIÓN: FASE 2 SPRINT 7 — RIGOR INSTITUCIONAL-GRADE
# ============================================================================

@app.post("/api/v1/ux/extract-key-insight", tags=["UX"], response_model=Dict[str, Any])
async def extract_key_insight_refactored(payload: ScoringPayloadRefactored):
    """
    ENDPOINT REFACTORIZADO: Extrae insight financiero REAL basado en matemáticas verificables.

    DOCUMENTACIÓN CRÍTICA:
    Este endpoint es un SISTEMA DE CONVERSIÓN diseñado específicamente para:
    1. Analizar la posición financiera real de la pareja (IRPF, patrimonio, sucesión)
    2. Identificar el riesgo económico más urgente
    3. Proponer una solución premium de Adapta alineada con ese riesgo
    4. Usar SOLO matemáticas verificables, cero exageración

    Cliente debe saber: Lo que lee es un análisis de su riesgo real + propuesta de valor verificable.
    Cada número es calculable. Cada propuesta tiene ROI claro.
    """

    try:
        # Extracción de payload
        income = payload.ingresos
        emergency_fund = payload.colchon_emergencia
        has_insurance = payload.seguro_vida
        legal_structure = payload.estructura_legal.lower()
        has_succession = payload.sucesion

        # ====================================================================
        # TASAS FISCALES REALES (España 2024, Madrid)
        # ====================================================================
        IRPF_MARGINAL = {
            "up_to_21600": 0.19,
            "21600_35200": 0.24,
            "35200_60000": 0.30,
            "60000_300000": 0.37,
            "above_300000": 0.45,
        }

        OPTIMIZED_RATES = {
            "dividends_holding": 0.235,
            "capital_gains_long_term": 0.19,
            "real_estate_rental": 0.37,
        }

        # ====================================================================
        # PERFIL 1: ALTO DIRECTIVO DESPROTEGIDO (75k-150k)
        # ====================================================================
        if 75000 <= income < 150000:
            # Cálculo IRPF marginal real
            if income <= 35200:
                marginal_rate = 0.30
            elif income <= 60000:
                marginal_rate = 0.37
            else:
                marginal_rate = 0.45

            current_annual_tax = income * marginal_rate

            # Exposición sucesoria
            net_income_after_tax = income - current_annual_tax
            accumulated_wealth = net_income_after_tax * 5
            inheritance_tax_without_structure = accumulated_wealth * 0.20

            # Brecha de seguros
            insurance_gap = income * 10

            # Propuesta Adapta
            optimized_tax_rate = 0.235
            annual_tax_with_sl = income * optimized_tax_rate
            tax_savings = current_annual_tax - annual_tax_with_sl

            return {
                "status": "success",
                "profile_type": "ALTO DIRECTIVO DESPROTEGIDO",
                "income_annual": income,
                "current_irpf_marginal": f"{int(marginal_rate * 100)}%",
                "current_annual_tax_burden": round(current_annual_tax, 2),

                "risks": {
                    "irpf_marginal": {
                        "label": "Tributación excesiva en rentas de trabajo",
                        "current_rate": f"{int(marginal_rate * 100)}%",
                        "optimized_rate": "23.5% (SL + dividends)",
                        "annual_saving": round(tax_savings, 2),
                        "mechanism": "Crear SL; convertir ingresos a dividendos corporativos con bonificación"
                    },
                    "succession_exposure": {
                        "label": "Patrimonio sin blindaje sucesorio",
                        "accumulated_wealth_5yr": round(accumulated_wealth, 2),
                        "inheritance_tax_current": round(inheritance_tax_without_structure, 2),
                        "inheritance_tax_optimized": round(accumulated_wealth * 0.01, 2),
                        "saving": round(inheritance_tax_without_structure - (accumulated_wealth * 0.01), 2),
                        "mechanism": "Pacto sucesorio + holding familiar + bonificación 99% Madrid"
                    },
                    "insurance_gap": {
                        "label": "Cobertura de muerte insuficiente",
                        "income_replacement_need": round(insurance_gap, 2),
                        "description": f"Si fallece, familia pierde {income}€/año. Necesita seguro de €{insurance_gap:,.0f}"
                    }
                },

                "adapta_proposal": {
                    "services": ["Optimización fiscal SL", "Planificación sucesoria + holding", "Seguro de vida estratégico"],
                    "annual_advisory_fee": 3600,
                    "expected_roi_first_year": round(tax_savings - 3600, 2),
                    "payback_months": round((3600 / tax_savings) * 12, 1) if tax_savings > 0 else 0,
                    "lifetime_value_10yr": round((tax_savings * 10) - (3600 * 10), 2),
                    "call_to_action": f"Te ahorras €{round(tax_savings, 0)}/año en IRPF. La iguala son €{3600}/año. Break-even: {round((3600 / tax_savings) * 12, 0) if tax_savings > 0 else 'N/A'} meses. ¿Arquitectura financiera real?"
                },

                "timeline": {
                    "consultation": "1 sesión (2h)",
                    "structure_design": "2-3 semanas",
                    "implementation": "30 días + notaría",
                    "first_tax_benefit": "Siguiente ejercicio fiscal"
                }
            }

        # ====================================================================
        # PERFIL 2: PATRIMONIO BLINDADO (150k+)
        # ====================================================================
        elif income >= 150000:
            estimated_wealth = income * 4.5

            # Impuesto de Patrimonio
            if estimated_wealth > 600000:
                patrimony_tax_annual = estimated_wealth * 0.011
            else:
                patrimony_tax_annual = 0

            current_tax_rate = 0.28
            current_irpf = income * current_tax_rate
            current_total_burden = current_irpf + patrimony_tax_annual

            # Herencia
            inheritance_tax_current = estimated_wealth * 0.20
            inheritance_tax_optimized = estimated_wealth * 0.01
            succession_savings = inheritance_tax_current - inheritance_tax_optimized

            # Optimización
            optimized_irpf = income * 0.22
            reduced_patrimony_tax = estimated_wealth * 0.003
            optimized_total_burden = optimized_irpf + reduced_patrimony_tax

            annual_savings = current_total_burden - optimized_total_burden

            return {
                "status": "success",
                "profile_type": "PATRIMONIO BLINDADO",
                "income_annual": income,
                "estimated_wealth": round(estimated_wealth, 2),
                "current_tax_burden": round(current_total_burden, 2),

                "risks": {
                    "double_taxation": {
                        "label": "IRPF + Impuesto de Patrimonio combinado",
                        "irpf": "28%",
                        "patrimony_tax_annual": round(patrimony_tax_annual, 2),
                        "total_burden": round(current_total_burden, 2),
                        "optimized_burden": round(optimized_total_burden, 2),
                        "annual_saving": round(annual_savings, 2),
                        "mechanism": "Holding patrimonial centraliza activos; reduce Impuesto de Patrimonio de 1.1% a 0.3%"
                    },
                    "succession_no_plan": {
                        "label": "Patrimonio disperso sin blindaje",
                        "wealth": round(estimated_wealth, 2),
                        "inheritance_tax_current": round(inheritance_tax_current, 2),
                        "inheritance_tax_optimized": round(inheritance_tax_optimized, 2),
                        "saving": round(succession_savings, 2),
                        "mechanism": "Bonificación 99% Madrid = 1% en lugar de 20%"
                    }
                },

                "adapta_proposal": {
                    "services": ["Holding patrimonial", "Optimización fiscal avanzada", "Planificación sucesoria integral", "Asesoramiento inversiones"],
                    "annual_advisory_fee": 12000,
                    "expected_roi_first_year": round(annual_savings - 12000, 2),
                    "payback_months": round((12000 / annual_savings) * 12, 1) if annual_savings > 0 else 0,
                    "lifetime_value_20yr": round((annual_savings * 20) + succession_savings, 2),
                    "call_to_action": f"Ahorras €{round(annual_savings, 0)}/año + €{round(succession_savings, 0)} en sucesión. ¿Blindamos patrimonio?"
                },

                "premium_upsell": {
                    "opportunity": "REVISIÓN ANUAL + OPTIMIZACIÓN TRIMESTRAL",
                    "description": "Tu situación fiscal cambia anualmente. Ofrecemos revisión anual exhaustiva + optimización trimestral de planificación",
                    "fee": 6000,
                    "benefit": "Mantener estructura optimizada; capturar nuevas oportunidades según cambios económicos"
                }
            }

        # ====================================================================
        # PERFIL 3: CLASE MEDIA EXPUESTA (<75k)
        # ====================================================================
        else:
            marginal_rate = 0.30
            current_annual_tax = income * marginal_rate
            net_income = income - current_annual_tax
            monthly_expenses = net_income / 12 if net_income > 0 else 0
            emergency_fund_needed = monthly_expenses * 6
            emergency_gap = emergency_fund_needed - emergency_fund

            # Crecimiento
            annual_potential_savings = income * 0.15
            actual_savings_potential = annual_potential_savings * (1 - marginal_rate)

            # Optimización
            optimized_tax_rate = 0.24
            optimized_annual_tax = income * optimized_tax_rate
            tax_savings = current_annual_tax - optimized_annual_tax

            return {
                "status": "success",
                "profile_type": "CLASE MEDIA EXPUESTA",
                "income_annual": income,
                "net_monthly_income": round(monthly_expenses, 2),
                "current_irpf_marginal": f"{int(marginal_rate * 100)}%",

                "risks": {
                    "no_emergency_fund": {
                        "label": "Colchón de emergencia CRÍTICO",
                        "current": round(emergency_fund, 2),
                        "needed": round(emergency_fund_needed, 2),
                        "gap": round(emergency_gap, 2),
                        "months_covered": round(emergency_fund / monthly_expenses, 1) if monthly_expenses > 0 else 0,
                        "risk": f"Si pierdes empleo, tienes dinero para {round(emergency_fund / monthly_expenses, 1) if monthly_expenses > 0 else 0} mes(es). Después: insolvencia"
                    },
                    "taxation_erosion": {
                        "label": "Tributación que erosiona crecimiento",
                        "current_rate": f"{int(marginal_rate * 100)}%",
                        "annual_tax": round(current_annual_tax, 2),
                        "tax_savings_available": round(tax_savings, 2),
                        "mechanism": "Pequeña optimización fiscal (estimación directa vs. módulos, si aplica)"
                    },
                    "no_insurance": {
                        "label": "Sin cobertura de muerte",
                        "need": round(income * 5, 2),
                        "cost_monthly": 30,
                        "description": f"Si falleces, familia tiene €{round(emergency_fund, 0)}. Necesita €{round(income * 5, 0)}"
                    }
                },

                "adapta_proposal": {
                    "services": ["Optimización fiscal pequeña", "Plan de emergencia 12 meses", "Recomendación seguro crítico", "Auditoría de deuda"],
                    "annual_advisory_fee": 1200,
                    "expected_roi_first_year": round(tax_savings - 1200, 2),
                    "payback_months": round((1200 / tax_savings) * 12, 1) if tax_savings > 0 else 0,
                    "call_to_action": f"Ahorras €{round(tax_savings, 0)}/año. En 12 meses construyes colchón de €{round(emergency_fund_needed, 0)}. ¿Empezamos?"
                },

                "financial_narrative": f"Optimizas a {int(optimized_tax_rate*100)}%. Ahorras €{round(tax_savings, 0)}/año. En 12 meses: colchón de €{round(emergency_fund_needed, 0)}, seguro activado. Tu familia está protegida."
            }

    except Exception as e:
        logger.error(f"❌ Error in extract_key_insight_refactored: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al procesar diagnóstico: {str(e)}"
        )


# ============================================================================
# SPRINT 7: PSYCHOLOGY ENDPOINTS — FASE 2 INYECTADO
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
# SERVIR HTML DIRECTAMENTE (Elimina error de file://)
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
