#!/usr/bin/env python3
"""
APP COUPLE ENDPOINTS — FASE 2 Sprint 3
FastAPI endpoint orquestador para Espejo Fantasma.
POST /couple/{id}/answers → análisis 23 módulos + PDF async
TOP 1% MUNDIAL
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel, Field
from typing import Dict, Optional
from datetime import datetime, timedelta
import uuid
import json
import logging
import stripe
import os
import hmac
import hashlib

from couple_integration_adapter import CoupleIntegrationAdapter
from couple_report_generator import CoupleReportGenerator
from questionnaire_blind_ui import BlindQuestionnaireSession, MagicToken
from stripe_integration_adapter import StripePaymentAdapter, PsychologicalPricingEngine

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


# ============================================================================
# FASTAPI APP
# ============================================================================

app = FastAPI(
    title="Espejo Fantasma API",
    description="Diagnóstico Financiero de Pareja — TOP 1% MUNDIAL",
    version="2.5.0"
)

# Mock DB (en producción: PostgreSQL)
couples_db: Dict[str, dict] = {}
blind_sessions: Dict[str, BlindQuestionnaireSession] = {}


# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.get("/ping", response_model=PingResponse, tags=["Health"])
async def ping():
    """Health check endpoint"""
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat()
    }


# ============================================================================
# BLIND QUESTIONNAIRE — INITIATE SESSION
# ============================================================================

@app.post("/blind-session/init", tags=["Questionnaire"])
async def init_blind_session(couple_id: str, client_ip: str, client_ua: str):
    """
    Iniciar sesión ciega para pareja.
    Retorna 2 magic tokens (72h TTL) para usuario A y B.

    Request:
    - couple_id: UUID de pareja
    - client_ip: IP del cliente (anti-fraud)
    - client_ua: User-Agent (device fingerprint)

    Response:
    - token_a: Magic token para usuario A
    - token_b: Magic token para usuario B
    - expires_at: Expiración de sesión (72h)
    """
    couple_id = couple_id or str(uuid.uuid4())

    session = BlindQuestionnaireSession(couple_id)
    token_a = session.generate_magic_token("user_a", client_ip, client_ua)
    token_b = session.generate_magic_token("user_b", client_ip, client_ua)

    blind_sessions[couple_id] = session

    return {
        "couple_id": couple_id,
        "token_a": token_a.to_string(),
        "token_b": token_b.to_string(),
        "expires_at": session.session_expires_at.isoformat()
    }


# ============================================================================
# COUPLE ANSWERS SUBMISSION — ORQUESTADOR
# ============================================================================

@app.post("/couple/{couple_id}/answers", response_model=DiagnosticResponse, tags=["Diagnostic"])
async def submit_couple_answers(
    couple_id: str,
    submission: AnswerSubmission,
    background_tasks: BackgroundTasks
):
    """
    Endpoint orquestador: recibe 500q × 2 usuarios → análisis 23 módulos → PDF async

    Pipeline:
    1. Validar magic tokens (72h TTL)
    2. Ejecutar cascada 23 módulos (2-3s)
    3. Guardar en DB (CoupleSession, CoupleAnswers, CoupleReport)
    4. Disparar PDF async (background)
    5. Retornar análisis + expires_at

    Response:
    - compatibility_score: 0-100% (fricción pareja)
    - shield_score: 0-100% (resiliencia financiera)
    - runway_days: días de solvencia
    - tiene_hijos: activó Family Central Bank module
    - high_ticket_trigger: €500+ consulting eligible
    - pdf_url: URL de descarga (72h expiration)
    - expires_at: TTL ISO 8601
    """

    # PASO 1: Validar tokens
    session = blind_sessions.get(couple_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found. Init /blind-session/init first.")

    token_a_valid = session.submit_answers(submission.token_a, submission.user_a_answers)
    token_b_valid = session.submit_answers(submission.token_b, submission.user_b_answers)

    if not (token_a_valid and token_b_valid):
        raise HTTPException(status_code=401, detail="Invalid or expired tokens. Tokens must be valid within 72h.")

    # PASO 2: Ejecutar pipeline (23 módulos)
    try:
        adapter = CoupleIntegrationAdapter(db_session=None)
        result = adapter.process_couple_answers(
            couple_id,
            submission.user_a_answers,
            submission.user_b_answers,
            generate_pdf=True
        )
    except Exception as e:
        logger.error(f"Pipeline error for {couple_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis pipeline failed: {str(e)}")

    # PASO 3: Guardar en DB (mock)
    couples_db[couple_id] = {
        "couple_id": couple_id,
        "created_at": datetime.utcnow().isoformat(),
        "result": result,
        "expires_at": (datetime.utcnow() + timedelta(hours=72)).isoformat()
    }

    # PASO 4: Disparar PDF async
    background_tasks.add_task(
        _generate_pdf_async,
        couple_id,
        submission.user_a_answers,
        submission.user_b_answers
    )

    # PASO 5: Retornar respuesta
    return DiagnosticResponse(
        status="success",
        couple_id=couple_id,
        compatibility_score=result.get("compatibility_score", 0),
        shield_score=result.get("shield_score", 0),
        runway_days=result.get("runway_days", 0),
        tiene_hijos=result.get("tiene_hijos", False),
        high_ticket_trigger=result.get("high_ticket_trigger", False),
        pdf_url=result.get("pdf_url"),
        expires_at=(datetime.utcnow() + timedelta(hours=72)).isoformat(),
        compatibility_narrative=result.get("friction_narrative", ""),
        upsell_message=result.get("upsell_message", "")
    )


# ============================================================================
# BACKGROUND TASK: PDF GENERATION
# ============================================================================

async def _generate_pdf_async(couple_id: str, user_a_answers: Dict, user_b_answers: Dict):
    """
    Generar PDF de 13-15 páginas en background.
    En producción: usar Celery + Redis, no async de FastAPI.
    """
    try:
        generator = CoupleReportGenerator(couple_id, user_a_answers, user_b_answers)
        pdf_path = f"/tmp/diagnostico_{couple_id}.pdf"
        generator.generate_pdf(pdf_path)
        logger.info(f"PDF generated: {pdf_path}")

        # Actualizar DB con URL
        if couple_id in couples_db:
            couples_db[couple_id]["pdf_url"] = f"https://espejo-fantasma.com/reports/{couple_id}/diagnostico.pdf"
    except Exception as e:
        logger.error(f"PDF generation error for {couple_id}: {str(e)}")


# ============================================================================
# RESULT RETRIEVAL
# ============================================================================

@app.get("/couple/{couple_id}/result", tags=["Diagnostic"])
async def get_couple_result(couple_id: str):
    """
    Obtener resultado de análisis (con PDF si ya fue generado).
    TTL 72h desde submisión de respuestas.
    """
    result = couples_db.get(couple_id)
    if not result:
        raise HTTPException(status_code=404, detail="Result not found.")

    expires_at = datetime.fromisoformat(result["expires_at"])
    if datetime.utcnow() > expires_at:
        raise HTTPException(status_code=410, detail="Result expired (72h TTL).")

    return result


# ============================================================================
# STRIPE INITIALIZATION
# ============================================================================

stripe.api_key = os.getenv("STRIPE_API_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")


# ============================================================================
# STRIPE PAYMENT ENDPOINTS (SPRINT 8)
# ===========================================