"""
Quiz Completion Handler

Gestiona la lógica de finalización de cuestionario:
1. Valida respuestas
2. Calcula diagnóstico (secciones de análisis)
3. AUTO-OTORGA 200 créditos de auditoría
4. Registra timestamp de completitud
5. Retorna diagnostic_id para acceso a loading sequence

Punto crítico: Este es el trigger donde el usuario se da cuenta de que
tiene "200 tokens gratis" — psicología de sunk cost comienza aquí.
"""

import uuid
from datetime import datetime
from typing import Dict, Any, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from backend.models.diagnostic import DiagnosticSession, DiagnosticResult
from backend.models.credit_system import UserCreditAccount, CreditTransactionType
from backend.schemas.diagnostic import QuizCompletionRequest, DiagnosticSummary


class QuizCompletionError(Exception):
    """Errores durante finalización de quiz"""
    pass


def validate_answers(answers: Dict[str, Any], sections: Dict[str, int]) -> bool:
    """
    Valida que todas las secciones requeridas tengan respuestas.

    Args:
        answers: dict de respuestas por sección
        sections: dict mapping {section_name: expected_question_count}

    Returns:
        True si todas las secciones están completas

    Raises:
        QuizCompletionError si faltan respuestas
    """
    for section, expected_count in sections.items():
        if section not in answers:
            raise QuizCompletionError(f"Sección '{section}' sin respuestas")

        section_answers = answers[section]
        if not isinstance(section_answers, dict):
            raise QuizCompletionError(f"Respuestas de '{section}' no son dict")

        if len(section_answers) < expected_count:
            raise QuizCompletionError(
                f"Sección '{section}': esperadas {expected_count} respuestas, "
                f"recibidas {len(section_answers)}"
            )

    return True


def calculate_diagnostics(
    user_id: str,
    session_type: str,
    answers: Dict[str, Any],
    completion_time_seconds: int
) -> Tuple[DiagnosticResult, Dict[str, Any]]:
    """
    Calcula métricas de diagnóstico a partir de respuestas del quiz.

    Secciones procesadas:
    - Perfil Personal: edad, estado civil, dependientes, aversión al riesgo
    - Ingresos: salario base, ingresos variables, estabilidad laboral
    - Patrimonio Neto: activos, pasivos, deuda (especialmente "deuda abusiva")
    - Gastos & Compromiso: gastos mensuales, ahorros, compromisos futuros

    Calcula:
    - debt_score (0-100): nivel crítico de deuda
    - liquidity_ratio: activos_líquidos / gastos_mensuales (meses de cobertura)
    - efecto_retrovisor: dinero "evaporado" en últimos 10 años
    - friction_zones (couple): áreas de fricción financiera (para sesiones pareja)

    Returns:
        Tuple[DiagnosticResult, diagnostic_summary_dict]

    """
    # Extraer datos por sección
    perfil = answers.get("Perfil Personal", {})
    ingresos = answers.get("Ingresos", {})
    patrimonio = answers.get("Patrimonio Neto", {})
    gastos = answers.get("Gastos & Compromiso", {})

    # 1. DEBT SCORE (0-100)
    deuda_total = patrimonio.get("total_liabilities", 0)
    ingresos_anuales = ingresos.get("annual_income", 0)

    if ingresos_anuales == 0:
        debt_score = 0
    else:
        debt_to_income = deuda_total / ingresos_anuales
        # Escala: 0% = 0 pts, 30% = 25 pts, 60% = 50 pts, 100%+ = 100 pts
        debt_score = min(100, int((debt_to_income / 1.5) * 100))

    # 2. LIQUIDITY RATIO (meses de cobertura)
    activos_liquidos = patrimonio.get("liquid_assets", 0)
    gastos_mensuales = gastos.get("monthly_expenses", 1)  # Evitar división por 0

    liquidity_ratio = activos_liquidos / gastos_mensuales if gastos_mensuales > 0 else 0
    liquidity_months = min(24, liquidity_ratio)  # Cap a 24 meses

    # 3. EFECTO RETROVISOR (dinero evaporado en 10 años)
    patrimonio_neto_actual = patrimonio.get("net_worth", 0)
    ingresos_acumulados_10y = ingresos_anuales * 10

    dinero_evaporado = max(0, ingresos_acumulados_10y - patrimonio_neto_actual)
    evaporated_percentage = (dinero_evaporado / ingresos_acumulados_10y * 100) if ingresos_acumulados_10y > 0 else 0

    # 4. FRICTION ZONES (para sesiones pareja - ahora solo individual)
    friction_zones = []
    if debt_score > 50:
        friction_zones.append("debt_management")
    if liquidity_months < 3:
        friction_zones.append("cash_flow_emergency")
    if evaporated_percentage > 50:
        friction_zones.append("wealth_erosion")

    # 5. SCORE COMPOSITE (0-100)
    # Ponderación: 40% deuda, 30% liquidez, 30% efecto retrovisor
    health_score = (
        (100 - debt_score) * 0.4 +  # Menos deuda = mejor
        min(100, liquidity_months * 10) * 0.3 +  # Más meses de cobertura = mejor
        (100 - evaporated_percentage) * 0.3  # Menos dinero evaporado = mejor
    )
    health_score = max(0, min(100, health_score))

    # 6. CREAR OBJETO DiagnosticResult
    diagnostic_result = DiagnosticResult(
        id=str(uuid.uuid4()),
        user_id=user_id,
        session_type=session_type,
        debt_score=debt_score,
        liquidity_months=liquidity_months,
        evaporated_amount_10y=dinero_evaporado,
        evaporated_percentage=evaporated_percentage,
        friction_zones=friction_zones,
        health_score=health_score,
        completion_time_seconds=completion_time_seconds,
        completed_at=datetime.utcnow()
    )

    # Summary para respuesta API
    summary = {
        "diagnostic_id": diagnostic_result.id,
        "health_score": round(health_score, 1),
        "debt_score": debt_score,
        "liquidity_months": round(liquidity_months, 1),
        "evaporated_amount": dinero_evaporado,
        "evaporated_percentage": round(evaporated_percentage, 1),
        "friction_zones": friction_zones,
        "completion_time_seconds": completion_time_seconds,
    }

    return diagnostic_result, summary


def complete_quiz_and_award_credits(
    db: Session,
    user_id: str,
    session_type: str,
    answers: Dict[str, Any],
    completion_time_seconds: int
) -> Tuple[DiagnosticSummary, int]:
    """
    Flujo completo: valida, calcula diagnóstico, otorga créditos, registra transacción.

    Pasos:
    1. Validar respuestas
    2. Calcular diagnóstico
    3. Obtener/crear UserCreditAccount
    4. Otorgar 200 créditos
    5. Registrar transacción
    6. Retornar diagnostic_id + credits_awarded

    Args:
        db: SQLAlchemy session
        user_id: UUID del usuario
        session_type: "individual" o "couple"
        answers: respuestas del quiz
        completion_time_seconds: tiempo de completitud en segundos

    Returns:
        Tuple[summary, credits_awarded]

    Raises:
        QuizCompletionError: si validación o cálculo falla
        IntegrityError: si hay conflicto en BD
    """

    # Paso 1: Validar
    expected_sections = {
        "Perfil Personal": 4,
        "Ingresos": 3,
        "Patrimonio Neto": 4,
        "Gastos & Compromiso": 3
    }
    validate_answers(answers, expected_sections)

    # Paso 2: Calcular diagnóstico
    diagnostic_result, summary = calculate_diagnostics(
        user_id=user_id,
        session_type=session_type,
        answers=answers,
        completion_time_seconds=completion_time_seconds
    )

    try:
        # Guardar diagnóstico en BD
        db.add(diagnostic_result)
        db.flush()  # Asegurar que se genera el ID

        # Paso 3: Obtener/crear cuenta de créditos
        credit_account = db.query(UserCreditAccount).filter_by(user_id=user_id).first()

        if not credit_account:
            # Primera vez: crear cuenta
            credit_account = UserCreditAccount(
                id=str(uuid.uuid4()),
                user_id=user_id,
                available_credits=0,
                total_credits_earned=0,
                total_credits_spent=0
            )
            db.add(credit_account)
            db.flush()

        # Paso 4 & 5: Otorgar 200 créditos y registrar transacción
        credits_awarded = 200
        transaction = credit_account.add_credits(
            amount=credits_awarded,
            transaction_type=CreditTransactionType.QUIZ_COMPLETION,
            description=f"Quiz completado - {session_type} - Score {summary['health_score']}",
            metadata={
                "diagnostic_id": diagnostic_result.id,
                "session_type": session_type,
                "health_score": summary['health_score'],
                "debt_score": summary['debt_score'],
                "completion_time_seconds": completion_time_seconds
            }
        )

        # Guardar transacción
        db.add(transaction)

        # Commit de todo (diagnóstico + créditos + transacción)
        db.commit()

        return summary, credits_awarded

    except IntegrityError as e:
        db.rollback()
        raise QuizCompletionError(f"Error de integridad BD durante finalización: {str(e)}")
    except Exception as e:
        db.rollback()
        raise QuizCompletionError(f"Error inesperado completando quiz: {str(e)}")


def get_user_credit_status(db: Session, user_id: str) -> Dict[str, Any]:
    """
    Obtiene estado actual de créditos del usuario (usado por LoadingSequence).

    Returns dict con:
    - available_credits: saldo actual
    - total_earned: total ganado (histórico)
    - pdf_cost: costo en créditos para PDF (500)
    - can_redeem: boolean si tiene suficientes
    - credits_needed_to_redeem: si no tiene suficientes, cuántos le faltan
    """
    account = db.query(UserCreditAccount).filter_by(user_id=user_id).first()

    if not account:
        return {
            "available_credits": 0,
            "total_earned": 0,
            "pdf_cost": 500,
            "can_redeem": False,
            "credits_needed_to_redeem": 500
        }

    pdf_cost = 500
    can_redeem = account.available_credits >= pdf_cost

    return {
        "available_credits": account.available_credits,
        "total_earned": account.total_credits_earned,
        "pdf_cost": pdf_cost,
        "can_redeem": can_redeem,
        "credits_needed_to_redeem": max(0, pdf_cost - account.available_credits)
    }
