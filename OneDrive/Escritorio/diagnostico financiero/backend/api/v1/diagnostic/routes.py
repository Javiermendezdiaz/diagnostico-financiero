"""
Diagnostic API Routes

Endpoints para:
1. Obtener cuestionario
2. Guardar respuestas de secciones
3. FINALIZAR quiz → auto-otorgar 200 créditos → retornar diagnostic_id para loading sequence
4. Obtener diagnóstico completo
5. Acceder a estado de créditos (para LoadingSequence)
"""

import time
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session

from backend.api.v1.diagnostic.quiz_completion import (
    complete_quiz_and_award_credits,
    get_user_credit_status,
    QuizCompletionError
)
from backend.schemas.diagnostic import (
    QuizResponseRequest,
    DiagnosticSummaryResponse,
    CreditStatusResponse
)
from backend.schemas.payment import CreditStatusResponse as PaymentCreditStatusResponse
from backend.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/diagnostics", tags=["diagnostics"])


@router.get("/questionnaire")
async def get_questionnaire() -> Dict[str, Any]:
    """
    Retorna el cuestionario completo (100 preguntas en 4 secciones).

    Response:
    {
        "sections": [
            {
                "id": "perfil_personal",
                "title": "Perfil Personal",
                "description": "Contexto sociodemográfico y financiero",
                "questions": [
                    {
                        "id": "edad",
                        "type": "numeric",
                        "label": "¿Cuál es tu edad?",
                        "required": true,
                        "constraints": {"min": 18, "max": 120}
                    },
                    ...
                ]
            },
            ...
        ]
    }

    Estructura de questionnaire está hardcoded aquí (o cargable desde BD).
    """
    return {
        "sections": [
            {
                "id": "perfil_personal",
                "title": "Perfil Personal",
                "description": "Contexto sociodemográfico y financiero",
                "questions": [
                    {
                        "id": "edad",
                        "type": "numeric",
                        "label": "¿Cuál es tu edad?",
                        "required": True,
                        "constraints": {"min": 18, "max": 120}
                    },
                    {
                        "id": "estado_civil",
                        "type": "select",
                        "label": "Estado civil",
                        "required": True,
                        "options": ["Soltero/a", "Pareja de hecho", "Casado/a", "Divorciado/a", "Viudo/a"]
                    },
                    {
                        "id": "dependientes",
                        "type": "numeric",
                        "label": "Número de dependientes",
                        "required": True,
                        "constraints": {"min": 0, "max": 10}
                    },
                    {
                        "id": "aversion_riesgo",
                        "type": "likert",
                        "label": "¿Cuál es tu aversión al riesgo financiero?",
                        "required": True,
                        "scale": "emoji"  # Emoji scale: 😟😐😊😄😁
                    }
                ]
            },
            {
                "id": "ingresos",
                "title": "Ingresos",
                "description": "Fuentes de ingresos y estabilidad laboral",
                "questions": [
                    {
                        "id": "annual_income",
                        "type": "numeric",
                        "label": "¿Cuál es tu ingreso anual neto aproximado (en €)?",
                        "required": True,
                        "constraints": {"min": 0, "max": 500000}
                    },
                    {
                        "id": "variable_income",
                        "type": "numeric",
                        "label": "¿Cuál es tu ingreso variable anual aproximado (bonificaciones, comisiones)?",
                        "required": True,
                        "constraints": {"min": 0, "max": 500000}
                    },
                    {
                        "id": "job_stability",
                        "type": "likert",
                        "label": "Nivel de estabilidad laboral",
                        "required": True,
                        "scale": "emoji"
                    }
                ]
            },
            {
                "id": "patrimonio_neto",
                "title": "Patrimonio Neto",
                "description": "Activos, pasivos, deuda",
                "questions": [
                    {
                        "id": "liquid_assets",
                        "type": "numeric",
                        "label": "Activos líquidos (efectivo, depósitos, bolsa) en €",
                        "required": True,
                        "constraints": {"min": 0, "max": 5000000}
                    },
                    {
                        "id": "real_estate_value",
                        "type": "numeric",
                        "label": "Valor de inmuebles (propiedad) en €",
                        "required": True,
                        "constraints": {"min": 0, "max": 5000000}
                    },
                    {
                        "id": "total_liabilities",
                        "type": "numeric",
                        "label": "Total de deudas (hipoteca, créditos, tarjetas) en €",
                        "required": True,
                        "constraints": {"min": 0, "max": 5000000}
                    },
                    {
                        "id": "abusive_debt",
                        "type": "numeric",
                        "label": "Deuda en condiciones abusivas (interés > 20%) en €",
                        "required": True,
                        "constraints": {"min": 0, "max": 1000000}
                    }
                ]
            },
            {
                "id": "gastos_compromiso",
                "title": "Gastos & Compromisos",
                "description": "Gastos mensuales, ahorros, compromisos futuros",
                "questions": [
                    {
                        "id": "monthly_expenses",
                        "type": "numeric",
                        "label": "¿Cuál es tu gasto mensual aproximado en €?",
                        "required": True,
                        "constraints": {"min": 0, "max": 20000}
                    },
                    {
                        "id": "monthly_savings",
                        "type": "numeric",
                        "label": "¿Cuánto ahorras mensualmente (en €)?",
                        "required": True,
                        "constraints": {"min": 0, "max": 20000}
                    },
                    {
                        "id": "future_commitments",
                        "type": "likert",
                        "label": "Nivel de compromisos futuros (educación hijos, herencias, ayuda familiar)",
                        "required": True,
                        "scale": "emoji"
                    }
                ]
            }
        ]
    }


@router.post("/complete")
async def complete_quiz(
    request: QuizResponseRequest,
    db: Session = Depends(get_db)
) -> DiagnosticSummaryResponse:
    """
    Finaliza el cuestionario y otorga automáticamente 200 créditos.

    POST /api/v1/diagnostics/complete
    {
        "user_id": "550e8400-e29b-41d4-a716-446655440000",
        "session_type": "individual",
        "answers": {
            "Perfil Personal": {
                "edad": 42,
                "estado_civil": "Casado/a",
                "dependientes": 2,
                "aversion_riesgo": 3
            },
            "Ingresos": {
                "annual_income": 85000,
                "variable_income": 0,
                "job_stability": 4
            },
            "Patrimonio Neto": {
                "liquid_assets": 120000,
                "real_estate_value": 300000,
                "total_liabilities": 180000,
                "abusive_debt": 5000
            },
            "Gastos & Compromiso": {
                "monthly_expenses": 3500,
                "monthly_savings": 1200,
                "future_commitments": 2
            }
        },
        "completion_time_seconds": 487
    }

    Response:
    {
        "diagnostic_id": "a1b2c3d4-e5f6-47a8-b9c0-d1e2f3a4b5c6",
        "health_score": 67.4,
        "debt_score": 42,
        "liquidity_months": 3.4,
        "evaporated_amount": 142500,
        "evaporated_percentage": 16.8,
        "friction_zones": [],
        "credits_awarded": 200,
        "credits_available": 200
    }

    Flujo:
    1. Validar respuestas completas
    2. Calcular diagnóstico (debt_score, liquidity, retrospective effect)
    3. Auto-otorgar 200 créditos (+ transacción)
    4. Retornar diagnostic_id para acceder a LoadingSequence
    5. Frontend redirige a LoadingSequence con diagnostic_id

    Args:
        request.user_id: UUID del usuario
        request.session_type: "individual" o "couple"
        request.answers: respuestas del quiz (validadas en schemas)
        request.completion_time_seconds: tiempo de completitud

    Returns:
        DiagnosticSummaryResponse con diagnostic_id + métricas + créditos otorgados

    Raises:
        HTTPException 400: respuestas inválidas
        HTTPException 500: error calculando diagnóstico
    """

    try:
        # Medir tiempo de procesamiento
        start_time = time.time()

        # Flujo principal: validar, calcular, otorgar créditos
        summary, credits_awarded = complete_quiz_and_award_credits(
            db=db,
            user_id=request.user_id,
            session_type=request.session_type,
            answers=request.answers,
            completion_time_seconds=request.completion_time_seconds
        )

        # Obtener saldo actual de créditos
        credit_status = get_user_credit_status(db, request.user_id)

        processing_time = time.time() - start_time
        logger.info(
            f"Quiz completed: user={request.user_id} "
            f"diagnostic_id={summary['diagnostic_id']} "
            f"health_score={summary['health_score']} "
            f"credits_awarded={credits_awarded} "
            f"processing_time={processing_time:.2f}s"
        )

        # Response completa para frontend
        return DiagnosticSummaryResponse(
            diagnostic_id=summary['diagnostic_id'],
            health_score=summary['health_score'],
            debt_score=summary['debt_score'],
            liquidity_months=summary['liquidity_months'],
            evaporated_amount=summary['evaporated_amount'],
            evaporated_percentage=summary['evaporated_percentage'],
            friction_zones=summary['friction_zones'],
            credits_awarded=credits_awarded,
            credits_available=credit_status['available_credits'],
            credits_needed_for_pdf=credit_status['credits_needed_to_redeem']
        )

    except QuizCompletionError as e:
        logger.warning(f"Quiz validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error completing quiz: {str(e)}")
        raise HTTPException(status_code=500, detail="Error finalizando quiz")


@router.get("/credit-status/{user_id}")
async def get_user_credit_status_endpoint(
    user_id: str,
    db: Session = Depends(get_db)
) -> PaymentCreditStatusResponse:
    """
    Obtiene estado actual de créditos del usuario.

    Usado por:
    - LoadingSequence (para mostrar "200/500 créditos")
    - Botón de pago (para habilitar/deshabilitar)
    - Dashboard de perfil

    GET /api/v1/diagnostics/credit-status/{user_id}

    Response:
    {
        "available_credits": 200,
        "total_earned": 200,
        "pdf_cost": 500,
        "can_redeem": false,
        "credits_needed_to_redeem": 300
    }

    Args:
        user_id: UUID del usuario

    Returns:
        PaymentCreditStatusResponse con estado de créditos
    """
    credit_status = get_user_credit_status(db, user_id)
    return PaymentCreditStatusResponse(**credit_status)


@router.get("/{diagnostic_id}")
async def get_diagnostic_detail(
    diagnostic_id: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Obtiene diagnóstico completo (todos los datos calculados).

    GET /api/v1/diagnostics/{diagnostic_id}

    Usado por:
    - LoadingSequence (para mostrar animación con datos personalizados)
    - PDF generation (para popular todas las secciones)
    - Dashboard usuario

    Response incluye:
    - Diagnóstico base (health_score, debt_score, etc.)
    - Secciones de análisis profundo
    - Recomendaciones personalizadas
    - Datos de retrospectiva (Efecto Retrovisor)

    Args:
        diagnostic_id: UUID del diagnóstico

    Returns:
        Objeto diagnóstico completo

    Raises:
        HTTPException 404: diagnostic_id no encontrado
    """
    # TODO: Implementar búsqueda en BD cuando DiagnosticResult esté full definido
    raise HTTPException(
        status_code=501,
        detail="Endpoint en desarrollo - esperar integración DiagnosticResult model"
    )
