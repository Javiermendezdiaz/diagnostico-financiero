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

logger = logging.getLogger(__name__)

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
