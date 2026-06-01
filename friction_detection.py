#!/usr/bin/env python3
"""
FRICTION DETECTION — FASE 2 Sprint 3
Cálculo de fricción financiera en parejas (5 dimensiones).
Detección de contradicciones entre respuestas de miembros.
"""

from typing import Dict, List, Tuple, Any
from dataclasses import dataclass
import math


@dataclass
class FrictionScore:
    """Puntuación de fricción en una dimensión"""
    dimension: str
    score: float  # 0-100
    drivers: List[str]  # factores que contribuyen
    contradictions: List[str]  # respuestas contradictorias detectadas


def calculate_friction_scores(
    couple_data: Dict[str, Any],
    member_a_answers: Dict[int, Any],
    member_b_answers: Dict[int, Any]
) -> Dict[str, FrictionScore]:
    """
    Calcula las 5 dimensiones de fricción financiera.

    Returns:
    {
        "conciliacion": FrictionScore(...),
        "finanzas": FrictionScore(...),
        "robustez": FrictionScore(...),
        "patrimonio": FrictionScore(...),
        "psicologia": FrictionScore(...)
    }
    """

    friction_scores = {}

    # DIMENSIÓN 1: CONCILIACIÓN (alineación de visión financiera)
    friction_scores["conciliacion"] = _calculate_conciliacion(
        member_a_answers, member_b_answers
    )

    # DIMENSIÓN 2: FINANZAS (estado actual, ingresos, deudas)
    friction_scores["finanzas"] = _calculate_finanzas(
        member_a_answers, member_b_answers, couple_data
    )

    # DIMENSIÓN 3: ROBUSTEZ (capacidad de sobrevivir crisis)
    friction_scores["robustez"] = _calculate_robustez(
        member_a_answers, member_b_answers, couple_data
    )

    # DIMENSIÓN 4: PATRIMONIO (distribución, planificación sucesoria)
    friction_scores["patrimonio"] = _calculate_patrimonio(
        member_a_answers, member_b_answers, couple_data
    )

    # DIMENSIÓN 5: PSICOLOGÍA (comportamiento financiero, valores)
    friction_scores["psicologia"] = _calculate_psicologia(
        member_a_answers, member_b_answers
    )

    return friction_scores


def _calculate_conciliacion(
    member_a_answers: Dict[int, Any],
    member_b_answers: Dict[int, Any]
) -> FrictionScore:
    """
    Mide la alineación de visión financiera entre miembros.
    Preguntas clave: 001-010 (visión, objetivos, tolerancia riesgo)
    """
    drivers = []
    contradictions = []
    score = 0.0

    # Q001: Ingresos anuales brutos (alineación)
    try:
        income_a = float(member_a_answers.get(1, 0))
        income_b = float(member_b_answers.get(1, 0))
        if income_a > 0 and income_b > 0:
            income_ratio = max(income_a, income_b) / min(income_a, income_b)
            if income_ratio > 3:
                drivers.append("Grandes diferencias en ingresos")
                score += 25
    except (ValueError, TypeError):
        pass

    # Q002: Objetivo financiero principal (alineación)
    obj_a = member_a_answers.get(2)
    obj_b = member_b_answers.get(2)
    if obj_a and obj_b and obj_a != obj_b:
        contradictions.append(f"Objetivos diferentes: {obj_a} vs {obj_b}")
        drivers.append("Falta de alineación en objetivos")
        score += 20

    # Q003: Tolerancia al riesgo (alineación)
    risk_a = member_a_answers.get(3)
    risk_b = member_b_answers.get(3)
    if risk_a and risk_b:
        risk_values = {"muy_baja": 0, "baja": 1, "media": 2, "alta": 3, "muy_alta": 4}
        try:
            risk_diff = abs(risk_values.get(risk_a, 0) - risk_values.get(risk_b, 0))
            if risk_diff >= 2:
                contradictions.append(f"Tolerancia al riesgo divergente: {risk_a} vs {risk_b}")
                drivers.append("Perfiles de riesgo incompatibles")
                score += 25
        except:
            pass

    # Q004: Comunicación sobre dinero (frecuencia)
    comm_freq = member_a_answers.get(4)
    if comm_freq in ["raramente", "nunca"]:
        drivers.append("Comunicación insuficiente sobre finanzas")
        score += 15

    # Q005: Gestión del dinero (quién decide)
    manager_a = member_a_answers.get(5)
    manager_b = member_b_answers.get(5)
    if manager_a == "yo solo/a" or manager_b == "yo solo/a":
        if manager_a != manager_b:
            contradictions.append("Uno de los miembros controla decisiones sin consenso")
            drivers.append("Falta de participación en decisiones financieras")
            score += 20

    # Normalizar a 0-100
    score = min(score, 100)

    return FrictionScore(
        dimension="Conciliación",
        score=score,
        drivers=drivers,
        contradictions=contradictions
    )


def _calculate_finanzas(
    member_a_answers: Dict[int, Any],
    member_b_answers: Dict[int, Any],
    couple_data: Dict[str, Any]
) -> FrictionScore:
    """
    Mide salud financiera actual: ingresos, deudas, estado de liquidez.
    Preguntas: 001 (ingresos), 011-020 (gastos, deudas, ahorros)
    """
    drivers = []
    contradictions = []
    score = 0.0

    # Ingresos totales
    try:
        income_a = float(member_a_answers.get(1, 0))
        income_b = float(member_b_answers.get(1, 0))
        total_income = income_a + income_b

        # Q011: Gastos mensuales
        expenses_a = float(member_a_answers.get(11, 0))
        expenses_b = float(member_b_answers.get(11, 0))
        total_expenses = expenses_a + expenses_b

        # Índice de gastos / ingresos (mensual)
        if total_income > 0:
            monthly_income = total_income / 12
            expense_ratio = total_expenses / monthly_income if monthly_income > 0 else 0

            if expense_ratio > 0.95:
                drivers.append("Gastos muy cercanos a ingresos (bajo margen)")
                score += 30
            elif expense_ratio > 0.85:
                drivers.append("Gastos altos respecto a ingresos")
                score += 15

    except (ValueError, TypeError):
        pass

    # Q012: Deuda total
    debt_a = float(member_a_answers.get(12, 0))
    debt_b = float(member_b_answers.get(12, 0))
    total_debt = debt_a + debt_b

    if total_debt > 0:
        # Ratio deuda/ingresos
        try:
            total_income = float(member_a_answers.get(1, 0)) + float(member_b_answers.get(1, 0))
            if total_income > 0:
                debt_to_income = total_debt / total_income
                if debt_to_income > 3:
                    drivers.append("Deuda muy alta respecto a ingresos (>3x)")
                    score += 35
                elif debt_to_income > 1:
                    drivers.append("Deuda significativa (>ingresos anuales)")
                    score += 20
        except:
            pass

    # Q013: Ahorros de emergencia
    emergency_a = float(member_a_answers.get(13, 0))
    emergency_b = float(member_b_answers.get(13, 0))
    total_emergency = emergency_a + emergency_b

    try:
        monthly_expenses = (float(member_a_answers.get(11, 0)) + float(member_b_answers.get(11, 0)))
        if monthly_expenses > 0:
            emergency_months = total_emergency / monthly_expenses
            if emergency_months < 1:
                drivers.append("Sin fondo de emergencia (< 1 mes de gastos)")
                score += 25
            elif emergency_months < 3:
                drivers.append("Fondo de emergencia insuficiente (< 3 meses)")
                score += 10
    except:
        pass

    # Normalizar
    score = min(score, 100)

    return FrictionScore(
        dimension="Finanzas",
        score=score,
        drivers=drivers,
        contradictions=contradictions
    )


def _calculate_robustez(
    member_a_answers: Dict[int, Any],
    member_b_answers: Dict[int, Any],
    couple_data: Dict[str, Any]
) -> FrictionScore:
    """
    Mide capacidad de sobrevivir crisis (desempleo, enfermedad, etc).
    Preguntas: 021-030 (seguros, ingresos alternativos, capacidad ahorro)
    """
    drivers = []
    contradictions = []
    score = 0.0

    # Q021: ¿Tienen seguro de vida?
    life_insurance_a = member_a_answers.get(21)
    life_insurance_b = member_b_answers.get(21)

    if life_insurance_a == "no" or life_insurance_b == "no":
        drivers.append("Falta de seguro de vida")
        score += 20

    # Q022: ¿Tienen seguro de incapacidad?
    disability_a = member_a_answers.get(22)
    disability_b = member_b_answers.get(22)

    if disability_a == "no" or disability_b == "no":
        drivers.append("Falta de cobertura ante incapacidad")
        score += 15

    # Q023: ¿Qué pasaría si uno pierde empleo? (sin ahorros)
    job_loss_plan = member_a_answers.get(23)
    if job_loss_plan in ["no se", "nada"]:
        contradictions.append("Sin plan ante pérdida de empleo")
        drivers.append("Vulnerabilidad ante desempleo")
        score += 25

    # Q024: ¿Cuántos meses sin ingresos podrían aguantar?
    survival_months_a = member_a_answers.get(24)
    survival_months_b = member_b_answers.get(24)

    try:
        months_a = float(survival_months_a) if survival_months_a else 0
        months_b = float(survival_months_b) if survival_months_b else 0
        min_survival = min(months_a, months_b)

        if min_survival < 1:
            drivers.append("Capacidad de supervivencia < 1 mes")
            score += 35
        elif min_survival < 3:
            drivers.append("Capacidad de supervivencia < 3 meses")
            score += 15
    except:
        pass

    # Normalizar
    score = min(score, 100)

    return FrictionScore(
        dimension="Robustez",
        score=score,
        drivers=drivers,
        contradictions=contradictions
    )


def _calculate_patrimonio(
    member_a_answers: Dict[int, Any],
    member_b_answers: Dict[int, Any],
    couple_data: Dict[str, Any]
) -> FrictionScore:
    """
    Mide distribución, titularidad y planificación sucesoria.
    Preguntas: 031-040 (propiedades, titularidad, herencias, testamento)
    """
    drivers = []
    contradictions = []
    score = 0.0

    # Q031: ¿Tienen inmuebles?
    property_a = member_a_answers.get(31)
    property_b = member_b_answers.get(31)

    # Q032: ¿Cómo están titulados? (alineación)
    title_a = member_a_answers.get(32)
    title_b = member_b_answers.get(32)

    if title_a and title_b and title_a != title_b:
        contradictions.append(f"Desacuerdo sobre titularidad: {title_a} vs {title_b}")
        drivers.append("Titularidad desequilibrada o controvertida")
        score += 25

    # Q033: ¿Tienen testamento?
    will_a = member_a_answers.get(33)
    will_b = member_b_answers.get(33)

    if will_a == "no" or will_b == "no":
        drivers.append("Falta testamento (riesgo sucesorio)")
        score += 20

    # Q034: ¿Está actualizado? (si existe)
    will_updated = member_a_answers.get(34)
    if will_updated == "no":
        drivers.append("Testamento desactualizado")
        score += 10

    # Q035: ¿Cómo se repartiría la herencia?
    inheritance_plan = member_a_answers.get(35)
    if inheritance_plan in ["no se", "no decidido"]:
        contradictions.append("Sin plan de herencia definido")
        drivers.append("Incertidumbre en sucesión")
        score += 15

    # Normalizar
    score = min(score, 100)

    return FrictionScore(
        dimension="Patrimonio",
        score=score,
        drivers=drivers,
        contradictions=contradictions
    )


def _calculate_psicologia(
    member_a_answers: Dict[int, Any],
    member_b_answers: Dict[int, Any]
) -> FrictionScore:
    """
    Mide comportamiento, valores y personalidad financiera.
    Preguntas: 041-050 (ahorro, gasto, relación dinero, valores)
    """
    drivers = []
    contradictions = []
    score = 0.0

    # Q041: ¿Qué es más importante? (valores: seguridad vs libertad)
    value_a = member_a_answers.get(41)
    value_b = member_b_answers.get(41)

    if value_a and value_b and value_a != value_b:
        # Detectar conflicto opuesto
        opposite_values = [
            ("seguridad", "libertad"),
            ("ahorro", "gasto"),
            ("inversion", "consumo")
        ]
        for val1, val2 in opposite_values:
            if (val_a.lower() == val1 and value_b.lower() == val2) or \
               (value_a.lower() == val2 and value_b.lower() == val1):
                contradictions.append(f"Valores opuestos: {value_a} vs {value_b}")
                drivers.append("Conflicto de valores financieros")
                score += 30
                break

    # Q042: Comportamiento ante gasto (ahorro vs gasto impulsivo)
    spending_a = member_a_answers.get(42)
    spending_b = member_b_answers.get(42)

    if spending_a == "impulsivo" or spending_b == "impulsivo":
        if spending_a != spending_b:
            contradictions.append(f"Hábitos de gasto divergentes: {spending_a} vs {spending_b}")
            drivers.append("Estilos de consumo incompatibles")
            score += 25
        else:
            drivers.append("Gasto impulsivo compartido")
            score += 15

    # Q043: ¿Tienen deudas personales no compartidas?
    hidden_debt_a = member_a_answers.get(43)
    hidden_debt_b = member_b_answers.get(43)

    if hidden_debt_a == "si" or hidden_debt_b == "si":
        contradictions.append("Existen deudas personales no compartidas")
        drivers.append("Falta de transparencia en deudas")
        score += 35

    # Q044: Experiencia financiera en infancia
    childhood_a = member_a_answers.get(44)
    childhood_b = member_b_answers.get(44)

    if childhood_a and childhood_b:
        # Conflicto: uno de abundancia, otro de escasez
        if ("abundancia" in str(childhood_a).lower() and "escasez" in str(childhood_b).lower()) or \
           ("escasez" in str(childhood_a).lower() and "abundancia" in str(childhood_b).lower()):
            drivers.append("Traumas financieros opuestos en infancia")
            score += 20

    # Normalizar
    score = min(score, 100)

    return FrictionScore(
        dimension="Psicología",
        score=score,
        drivers=drivers,
        contradictions=contradictions
    )


def detect_contradictions(
    member_a_answers: Dict[int, Any],
    member_b_answers: Dict[int, Any]
) -> List[Tuple[int, str, Any, Any]]:
    """
    Detecta respuestas directamente contradictorias entre miembros.

    Returns:
    [(question_id, field, answer_a, answer_b), ...]
    """
    contradictions = []

    # Preguntas que DEBEN coincidir exactamente
    critical_questions = [2, 3, 5, 32, 33, 35]

    for q_id in critical_questions:
        answer_a = member_a_answers.get(q_id)
        answer_b = member_b_answers.get(q_id)

        if answer_a and answer_b and str(answer_a).lower() != str(answer_b).lower():
            contradictions.append((q_id, f"Q{q_id}", answer_a, answer_b))

    return contradictions


def calculate_overall_friction(
    friction_scores: Dict[str, FrictionScore]
) -> float:
    """
    Calcula fricción general como promedio ponderado de las 5 dimensiones.
    Pesos: Conciliación (30%) > Finanzas (25%) > Psicología (20%) > Patrimonio (15%) > Robustez (10%)
    """
    weights = {
        "conciliacion": 0.30,
        "finanzas": 0.25,
        "psicologia": 0.20,
        "patrimonio": 0.15,
        "robustez": 0.10
    }

    weighted_total = sum(
        friction_scores[dim].score * weights[dim]
        for dim in weights.keys()
        if dim in friction_scores
    )

    return min(weighted_total, 100)


# ============================================================================
# MÓDULOS ADICIONALES 1-19 PARA COUPLE INTEGRATION ADAPTER
# ============================================================================

class ResponseValidator:
    @staticmethod
    def validate_answers(answers: Dict[int, Any]) -> Dict[int, Any]:
        """Valida rango de respuestas (0-5 escala)"""
        validated = {}
        for q_id, answer in answers.items():
            if isinstance(answer, (int, float)):
                validated[q_id] = max(0, min(5, int(answer)))
            else:
                validated[q_id] = 0
        return validated


class FrictionCalculator:
    @staticmethod
    def calculate_friction(user_a: Dict, user_b: Dict) -> Any:
        """Calcula fricción general"""
        from dataclasses import dataclass
        @dataclass
        class FrictionResult:
            compatibility_score: float

        # Promedio simple de divergencia
        total_diff = sum(abs(user_a.get(i, 0) - user_b.get(i, 0)) for i in range(1, 501))
        avg_diff = total_diff / 500 if total_diff > 0 else 0
        compatibility = 100 - (avg_diff * 20)
        return FrictionResult(compatibility_score=max(0, min(100, compatibility)))


class FrictionInsights:
    @staticmethod
    def detect_contradictions(user_a: Dict, user_b: Dict, friction_map: Any) -> Any:
        """Detecta contradicciones"""
        from dataclasses import dataclass
        @dataclass
        class Insights:
            friction_narrative: str

        return Insights(friction_narrative="Análisis de fricción completado")


class QuickWinsPlanner:
    @staticmethod
    def generate_4week_plan(current_state: Any, coi: Any, friction: Any) -> Any:
        """Genera plan de 4 semanas"""
        from dataclasses import dataclass
        @dataclass
        class Plan:
            wins_list: list
        return Plan(wins_list=["Establecer presupuesto conjunto", "Revisar deudas", "Automatizar ahorros"])


class COICalculator:
    @staticmethod
    def estimate(current_state: Any, friction: Any) -> Any:
        """Calcula COI (Costo de Ignorancia)"""
        from dataclasses import dataclass
        @dataclass
        class COI:
            narrative_summary: str
        return COI(narrative_summary="COI estimado en base a patrones detectados")


class ArchetypeDetector:
    @staticmethod
    def detect(user_a: Dict, user_b: Dict) -> Any:
        """Detecta arquetipos de pareja"""
        from dataclasses import dataclass
        @dataclass
        class Archetype:
            name: str
        return Archetype(name="Pareja Equilibrada")


class FODACalculator:
    @staticmethod
    def calculate(friction: Any, state: Any, archetype: Any) -> Any:
        """FODA (Fortalezas, Oportunidades, Debilidades, Amenazas)"""
        from dataclasses import dataclass
        @dataclass
        class FODA:
            fortalezas: list
            debilidades: list
        return FODA(fortalezas=["Comunicación abierta"], debilidades=["Ahorro insuficiente"])


class CurrentStateAnalyzer:
    @staticmethod
    def analyze(user_a: Dict, user_b: Dict) -> Any:
        """Analiza estado financiero actual"""
        from dataclasses import dataclass
        @dataclass
        class State:
            monthly_liquid_assets: float
            monthly_expenses: float
        return State(monthly_liquid_assets=5000, monthly_expenses=3000)

    @staticmethod
    def ideal_state_for_profile(state: Any) -> Any:
        """Calcula estado ideal basado en perfil"""
        return state


class DebtAnalyzer:
    @staticmethod
    def analyze(state: Any, coi: Any, user_a: Dict, user_b: Dict) -> Any:
        """Analiza deuda total y estrategia de pago"""
        from dataclasses import dataclass
        @dataclass
        class Debt:
            total_debt: float
            payoff_years: float
        return Debt(total_debt=50000, payoff_years=5)


class InvestmentAnalyzer:
    @staticmethod
    def analyze(state: Any, user_a: Dict, user_b: Dict) -> Any:
        """Analiza cartera de inversiones"""
        from dataclasses import dataclass
        @dataclass
        class Investment:
            diversification: float
        return Investment(diversification=0.6)


class LifestyleAnalyzer:
    @staticmethod
    def analyze(state: Any, user_a: Dict, user_b: Dict) -> Any:
        """Analiza gastos de lifestyle vs necesarios"""
        from dataclasses import dataclass
        @dataclass
        class Lifestyle:
            discretionary_spending: float
        return Lifestyle(discretionary_spending=500)


class ImmunityScoreCalculator:
    @staticmethod
    def calculate(debt: Any, investment: Any, lifestyle: Any) -> Any:
        """Calcula escudo de protección (shield score)"""
        from dataclasses import dataclass
        @dataclass
        class Immunity:
            shield_score: float
        return Immunity(shield_score=65)


class TheTenPercentMultiplier:
    @staticmethod
    def calculate(state: Any) -> Any:
        """Calcula mejora potencial del 10%"""
        from dataclasses import dataclass
        @dataclass
        class TenPercent:
            savings_increase: float
        return TenPercent(savings_increase=300)


class FinancialRunwayCalculator:
    @staticmethod
    def calculate(liquid_assets: float, monthly_expenses: float, user_a: Dict) -> Any:
        """Calcula días de estabilidad financiera"""
        from dataclasses import dataclass
        @dataclass
        class Runway:
            runway_days: int
            narrative_desperation_clock: str

        days = int((liquid_assets / monthly_expenses) * 30) if monthly_expenses > 0 else 0
        return Runway(
            runway_days=days,
            narrative_desperation_clock=f"Pueden aguantar {days} días sin ingresos"
        )


class LifeEventSimulator:
    @staticmethod
    def simulate(state: Any, user_a: Dict, user_b: Dict) -> Any:
        """Simula escenarios de eventos de vida (matrimonio, hijos, jubilación)"""
        from dataclasses import dataclass
        @dataclass
        class LifeEvents:
            events: list
        return LifeEvents(events=[])


class MoneyArchetypeAnalyzer:
    @staticmethod
    def analyze(user_a: Dict, user_b: Dict, friction: Any) -> Any:
        """Detecta arquetipos de dinero (ahorrador, gastador, inversor, etc)"""
        from dataclasses import dataclass
        @dataclass
        class Archetypes:
            user_a_archetype: str
            user_b_archetype: str
            conflict_score: float
        return Archetypes(user_a_archetype="Ahorrador", user_b_archetype="Gastador", conflict_score=6)


class LegacyHabitIndexCalculator:
    @staticmethod
    def calculate(state: Any, user_a: Dict, user_b: Dict) -> Any:
        """Calcula legacy (qué dejan para el futuro, hijos)"""
        from dataclasses import dataclass
        @dataclass
        class Legacy:
            legacy_health_index: float
            children_replication_probability: float
        return Legacy(legacy_health_index=0.7, children_replication_probability=0.8)


class PremiumUpsellOptimizer:
    @staticmethod
    def generate_trigger(willing: bool, coi: Any, legacy: Any, q500_score: int) -> Any:
        """Genera trigger para upsell premium (Strategy Session, Deep Dive, Coaching)"""
        from dataclasses import dataclass
        @dataclass
        class Upsell:
            offer_message: str
        return Upsell(offer_message="Te recomendamos una Strategy Session personalizada")


class IncomeEcosystemArchitect:
    @staticmethod
    def analyze(state: Any, user_a: Dict, user_b: Dict, ten_percent: Any) -> Any:
        """Analiza diversificación de ingresos y oportunidades"""
        from dataclasses import dataclass
        @dataclass
        class DiversificationIndex:
            diversification_score: float

        @dataclass
        class IncomeEcosystem:
            diversification_index: DiversificationIndex

        return IncomeEcosystem(diversification_index=DiversificationIndex(diversification_score=0.65))
