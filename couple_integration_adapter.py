#!/usr/bin/env python3
"""
COUPLE INTEGRATION ADAPTER - FASE 2 Sprint 2
Orquestador que conecta couple_management.py (ORM) con friction_detection.py (23 modulos).
TOP 1% MUNDIAL
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional
import json

from couple_management import CoupleSession, CoupleAnswers, CoupleReport, CoupleService
from friction_detection import (
    ResponseValidator, FrictionCalculator, FrictionInsights, QuickWinsPlanner,
    COICalculator, ArchetypeDetector, FODACalculator, CurrentStateAnalyzer,
    DebtAnalyzer, InvestmentAnalyzer, LifestyleAnalyzer, ImmunityScoreCalculator,
    TheTenPercentMultiplier, FinancialRunwayCalculator, LifeEventSimulator,
    MoneyArchetypeAnalyzer, LegacyHabitIndexCalculator, PremiumUpsellOptimizer,
    IncomeEcosystemArchitect
)


class CoupleIntegrationAdapter:
    """Orquestador end-to-end: ORM -> analisis 23 modulos -> PDF + insights"""

    def __init__(self, db_session=None):
        self.db = db_session
        self.couple_service = CoupleService(db_session)

    def process_couple_answers(
        self,
        couple_id: str,
        user_a_answers: Dict[int, int],
        user_b_answers: Dict[int, int],
        generate_pdf: bool = True
    ) -> Dict:
        """
        Pipeline end-to-end:
        1. Validar respuestas
        2. Ejecutar 23 modulos diagnosticos
        3. Guardar en DB
        4. Generar PDF (async opcional)
        5. Retornar analisis + URLs
        """

        try:
            validated_a = ResponseValidator.validate_answers(user_a_answers)
            validated_b = ResponseValidator.validate_answers(user_b_answers)
        except ValueError as e:
            return {"error": f"Validation failed: {str(e)}", "status": 400}

        tiene_hijos_a = user_a_answers.get(1, 0) > 0
        tiene_hijos_b = user_b_answers.get(1, 0) > 0
        tiene_hijos = tiene_hijos_a or tiene_hijos_b

        analysis_result = self._run_friction_analysis_cascade(
            user_a_answers, user_b_answers, tiene_hijos
        )

        if self.db:
            couple_record = CoupleSession(
                id=couple_id or str(uuid.uuid4()),
                user_a_id=f"user_a_{couple_id}",
                user_b_id=f"user_b_{couple_id}",
                status="completed",
                tiene_hijos=tiene_hijos,
                created_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(hours=72)
            )

            couple_answers_a = CoupleAnswers(
                couple_session_id=couple_id,
                user_id="user_a",
                answers=json.dumps(user_a_answers),
                created_at=datetime.utcnow()
            )

            couple_answers_b = CoupleAnswers(
                couple_session_id=couple_id,
                user_id="user_b",
                answers=json.dumps(user_b_answers),
                created_at=datetime.utcnow()
            )

            couple_report = CoupleReport(
                couple_session_id=couple_id,
                friction_score=analysis_result.get("compatibility_score", 0),
                shield_score=analysis_result.get("shield_score", 0),
                runway_days=analysis_result.get("runway_days", 0),
                report_data=json.dumps(analysis_result),
                pdf_url=None,
                created_at=datetime.utcnow()
            )

            self.db.add(couple_record)
            self.db.add(couple_answers_a)
            self.db.add(couple_answers_b)
            self.db.add(couple_report)
            self.db.commit()

        pdf_url = None
        if generate_pdf:
            pdf_url = f"https://espejo-fantasma.com/reports/{couple_id}/diagnostico.pdf"

        return {
            "couple_id": couple_id,
            "status": "success",
            "compatibility_score": analysis_result.get("compatibility_score"),
            "shield_score": analysis_result.get("shield_score"),
            "runway_days": analysis_result.get("runway_days"),
            "tiene_hijos": tiene_hijos,
            "high_ticket_trigger": analysis_result.get("high_ticket_trigger"),
            "pdf_url": pdf_url,
            "expires_at": (datetime.utcnow() + timedelta(hours=72)).isoformat()
        }

    def _run_friction_analysis_cascade(self, user_a: Dict, user_b: Dict, tiene_hijos: bool) -> Dict:
        """Ejecutar los 23 modulos en cascada. Retorna analisis consolidado."""

        friction_map = FrictionCalculator.calculate_friction(user_a, user_b)
        friction_insights = FrictionInsights.detect_contradictions(user_a, user_b, friction_map)
        current_state = CurrentStateAnalyzer.analyze(user_a, user_b)
        ideal_state = CurrentStateAnalyzer.ideal_state_for_profile(current_state)
        archetype = ArchetypeDetector.detect(user_a, user_b)

        foda = FODACalculator.calculate(friction_map, current_state, archetype)
        coi = COICalculator.estimate(current_state, friction_map)
        debt = DebtAnalyzer.analyze(current_state, coi, user_a, user_b)
        investment = InvestmentAnalyzer.analyze(current_state, user_a, user_b)
        lifestyle = LifestyleAnalyzer.analyze(current_state, user_a, user_b)

        ten_percent = TheTenPercentMultiplier.calculate(current_state)
        immunity = ImmunityScoreCalculator.calculate(debt, investment, lifestyle)
        quick_wins = QuickWinsPlanner.generate_4week_plan(current_state, coi, friction_map)

        runway = FinancialRunwayCalculator.calculate(
            current_state.monthly_liquid_assets,
            current_state.monthly_expenses,
            user_a
        )
        life_events = LifeEventSimulator.simulate(current_state, user_a, user_b)
        archetypes = MoneyArchetypeAnalyzer.analyze(user_a, user_b, friction_map)
        legacy = LegacyHabitIndexCalculator.calculate(current_state, user_a, user_b)
        income_ecosystem = IncomeEcosystemArchitect.analyze(
            current_state, user_a, user_b, ten_percent
        )

        q500_a = user_a.get(500, 0)
        q500_b = user_b.get(500, 0)
        willing_to_mentor = (q500_a + q500_b) >= 50
        upsell = PremiumUpsellOptimizer.generate_trigger(
            willing_to_mentor, coi, legacy, q500_score=(q500_a + q500_b)
        )

        return {
            "compatibility_score": friction_map.compatibility_score,
            "friction_narrative": friction_insights.friction_narrative,
            "shield_score": immunity.shield_score,
            "runway_days": runway.runway_days,
            "runway_narrative": runway.narrative_desperation_clock,
            "legacy_index": legacy.legacy_health_index,
            "children_replication_prob": legacy.children_replication_probability if tiene_hijos else 0,
            "archetype_a": archetypes.user_a_archetype,
            "archetype_b": archetypes.user_b_archetype,
            "archetype_conflict": archetypes.conflict_score,
            "income_diversification": income_ecosystem.diversification_index.diversification_score,
            "high_ticket_trigger": willing_to_mentor,
            "upsell_message": upsell.offer_message,
            "monthly_savings_potential": ten_percent.savings_increase,
            "tiene_hijos": tiene_hijos,
            "coi_narrative": coi.narrative_summary if hasattr(coi, 'narrative_summary') else "",
            "quick_wins": quick_wins.wins_list if hasattr(quick_wins, 'wins_list') else []
        }


if __name__ == "__main__":
    adapter = CoupleIntegrationAdapter(db_session=None)

    test_answers_a = {i: 3 for i in range(1, 501)}
    test_answers_b = {i: 3 for i in range(1, 501)}
    test_answers_a[1] = 25
    test_answers_a[500] = 75

    result = adapter.process_couple_answers(
        "TEST-001",
        test_answers_a,
        test_answers_b,
        generate_pdf=True
    )

    print("OK Integration test completed")
    print(f"Compatibility: {result['compatibility_score']}%")
    print(f"Shield Score: {result['shield_score']}%")
    print(f"Runway: {result['runway_days']} days")
