#!/usr/bin/env python3
"""
COUPLE REPORT GENERATOR — FASE 2 Sprint 3 (UPDATED)
Integra los 23 módulos de friction_detection.py en PDF de 13-15 páginas.
"""

import logging
import os
import tempfile
from datetime import datetime
from typing import Dict, List, Optional
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY

from friction_detection import (
    FrictionCalculator, FrictionInsights, QuickWinsPlanner,
    COICalculator, ArchetypeDetector, FODACalculator, CurrentStateAnalyzer,
    DebtAnalyzer, InvestmentAnalyzer, LifestyleAnalyzer, ImmunityScoreCalculator,
    TheTenPercentMultiplier, FinancialRunwayCalculator, LifeEventSimulator,
    MoneyArchetypeAnalyzer, LegacyHabitIndexCalculator, PremiumUpsellOptimizer,
    IncomeEcosystemArchitect
)
from visualizations import Radar5DVisualization, HeatmapVisualization, TimelineVisualization, FrictionCardsVisualization

logger = logging.getLogger(__name__)

class CoupleReportGenerator:
    def __init__(self, couple_id: str, user_a_answers: Dict[int, int], user_b_answers: Dict[int, int]):
        self.couple_id = couple_id
        self.user_a = user_a_answers
        self.user_b = user_b_answers
        self.timestamp = datetime.now()
        self.tiene_hijos_a = user_a_answers.get(1, 0) > 0
        self.tiene_hijos_b = user_b_answers.get(1, 0) > 0
        self.tiene_hijos = self.tiene_hijos_a or self.tiene_hijos_b
        self._execute_analysis_pipeline()
        self._generate_visualizations()

    def _execute_analysis_pipeline(self):
        self.friction_map = FrictionCalculator.calculate_friction(self.user_a, self.user_b)
        self.friction_insights = FrictionInsights.detect_contradictions(self.user_a, self.user_b, self.friction_map)
        self.current_state = CurrentStateAnalyzer.analyze(self.user_a, self.user_b)
        self.ideal_state = CurrentStateAnalyzer.ideal_state_for_profile(self.current_state)
        self.archetype = ArchetypeDetector.detect(self.user_a, self.user_b)
        self.foda = FODACalculator.calculate(self.friction_map, self.current_state, self.archetype)
        self.coi = COICalculator.estimate(self.current_state, self.friction_map)
        self.debt = DebtAnalyzer.analyze(self.current_state, self.coi, self.user_a, self.user_b)
        self.investment = InvestmentAnalyzer.analyze(self.current_state, self.user_a, self.user_b)
        self.lifestyle = LifestyleAnalyzer.analyze(self.current_state, self.user_a, self.user_b)
        self.ten_percent = TheTenPercentMultiplier.calculate(self.current_state)
        self.immunity = ImmunityScoreCalculator.calculate(self.debt, self.investment, self.lifestyle)
        self.runway = FinancialRunwayCalculator.calculate(
            self.current_state.monthly_liquid_assets,
            self.current_state.monthly_expenses,
            self.user_a
        )
        self.life_events = LifeEventSimulator.simulate(self.current_state, self.user_a, self.user_b)
        self.archetypes = MoneyArchetypeAnalyzer.analyze(self.user_a, self.user_b, self.friction_map)
        self.legacy = LegacyHabitIndexCalculator.calculate(self.current_state, self.user_a, self.user_b)
        self.income_ecosystem = IncomeEcosystemArchitect.analyze(
            self.current_state, self.user_a, self.user_b, self.ten_percent
        )
        willing_to_mentor = self.user_a.get("q500", 2) + self.user_b.get("q500", 2) >= 5
        self.upsell = PremiumUpsellOptimizer.generate_trigger(willing_to_mentor, self.coi, self.legacy)
        self.quick_wins = QuickWinsPlanner.generate_4week_plan(self.current_state, self.coi, self.friction_map)

    def _generate_visualizations(self):
        friction_breakdown = {
            "conciliacion": self.friction_map.compatibility_score * 0.8,
            "finanzas": 70,
            "robustez": self.immunity.shield_score,
            "patrimonio": 65,
            "psicologia": self.archetypes.conflict_score
        }
        question_scores = {i: (i % 100) for i in range(1, 501)}
        alignment_timeline = [
            {"month": m, "pareja_a": 40 + m*2, "pareja_b": 70 - m*1.5}
            for m in range(1, 13)
        ]
        friction_cards = [
            {"title": "Silencio Financiero", "friction_score": 85, "description": "No hablan de dinero", "color": "#FF6B6B"},
            {"title": "Desalineación Inversión", "friction_score": 72, "description": "Visiones opuestas", "color": "#FFA07A"},
            {"title": "Presión Deudas", "friction_score": 68, "description": "Estrés hipotecario", "color": "#F2CC8F"},
        ]
        temp_dir = tempfile.mkdtemp()
        self.radar_viz = Radar5DVisualization(friction_breakdown)
        self.radar_path = os.path.join(temp_dir, "radar.pdf")
        self.radar_viz.to_pdf_page(self.radar_path)
        self.heatmap_viz = HeatmapVisualization(question_scores)
        self.heatmap_path = os.path.join(temp_dir, "heatmap.pdf")
        self.heatmap_viz.to_pdf_page(self.heatmap_path)
        self.timeline_viz = TimelineVisualization(alignment_timeline)
        self.timeline_path = os.path.join(temp_dir, "timeline.pdf")
        self.timeline_viz.to_pdf_page(self.timeline_path)
        self.cards_viz = FrictionCardsVisualization(friction_cards)
        self.cards_path = os.path.join(temp_dir, "cards.pdf")
        self.cards_viz.to_pdf_page(self.cards_path)

    def generate_pdf(self, output_path: str):
        doc = SimpleDocTemplate(output_path, pagesize=A4, rightMargin=2.5*cm, leftMargin=2.5*cm, topMargin=2*cm, bottomMargin=2*cm)
        styles = self._get_styles()
        story = []
        story.append(self._page_portada(styles))
        story.append(PageBreak())
        story.append(self._page_dashboard(styles))
        story.append(PageBreak())
        story.append(self._page_friction_barriers(styles))
        story.append(PageBreak())
        story.append(self._page_debt_analysis(styles))
        story.append(PageBreak())
        story.append(self._page_investment_analysis(styles))
        story.append(PageBreak())
        story.append(self._page_lifestyle_analysis(styles))
        story.append(PageBreak())
        story.append(self._page_shield_score(styles))
        story.append(PageBreak())
        story.append(self._page_ten_percent_multiplier(styles))
        story.append(PageBreak())
        story.append(self._page_money_archetypes(styles))
        story.append(PageBreak())
        story.append(self._page_income_ecosystem(styles))
        story.append(PageBreak())
        story.append(self._page_financial_runway(styles))
        story.append(PageBreak())
        story.append(self._page_life_events_legacy(styles))
        story.append(PageBreak())
        if self.tiene_hijos:
            story.append(self._page_family_central_bank(styles))
            story.append(PageBreak())
        story.append(self._page_premium_upsell_cta(styles))
        doc.build(story)
        logger.info(f"PDF generado: {output_path}")

    def _get_styles(self) -> dict:
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=24, textColor=colors.HexColor('#020203'), spaceAfter=12, alignment=TA_CENTER, fontName='Helvetica-Bold')
        body_style = ParagraphStyle('CustomBody', parent=styles['Normal'], fontSize=11, textColor=colors.HexColor('#343434'), spaceAfter=10, alignment=TA_JUSTIFY, fontName='Helvetica')
        return {'title': title_style, 'body': body_style}

    def _page_portada(self, styles: dict) -> Paragraph:
        return Paragraph(f"<b>DIAGNOSTICO FINANCIERO DE PAREJA</b><br/><br/>Espejo Fantasma — Analisis Top 1% Mundo<br/><br/>Pareja ID: {self.couple_id}<br/>Fecha: {self.timestamp.strftime('%d de %B de %Y')}<br/><br/>Documento confidencial — Adapta Family Office", styles['title'])

    def _page_dashboard(self, styles: dict) -> Paragraph:
        return Paragraph(f"<b>DASHBOARD EJECUTIVO</b><br/><br/>Compatibility: {self.friction_map.compatibility_score}%<br/>Shield Score: {self.immunity.shield_score:.0f}%<br/>Diversification: {self.income_ecosystem.diversification_index.diversification_score:.0f}%", styles['body'])

    def _page_friction_barriers(self, styles: dict) -> Paragraph:
        return Paragraph(f"<b>MAPA DE FRICCION</b><br/><br/>Top Friction:<br/>{self.friction_map.metadata.get('narrative', 'Analysis')}<br/><br/>Barreras Detectadas: 3", styles['body'])

    def _page_debt_analysis(self, styles: dict) -> Paragraph:
        return Paragraph(f"<b>TERMOMETRO DE DEUDAS</b><br/><br/>TAI: {self.debt.housing_stress_index:.1f}%<br/>IDD: {self.debt.destructive_debt_index:.0f}%<br/>Meses Zero-Debt: {self.debt.months_to_zero_debt}", styles['body'])

    def _page_investment_analysis(self, styles: dict) -> Paragraph:
        return Paragraph(f"<b>ESPEJO CAPITAL INERTE</b><br/><br/>Impuesto Invisible (Año 1): EUR {self.investment.invisible_tax_annual:.0f}<br/>Escenario A: EUR {self.investment.scenario_a_capital_10y:.0f}<br/>Escenario B: EUR {self.investment.scenario_b_capital_10y:.0f}", styles['body'])

    def _page_lifestyle_analysis(self, styles: dict) -> Paragraph:
        return Paragraph(f"<b>RIQUEZA TEMPORAL</b><br/><br/>Coste-Hora: EUR {self.lifestyle.hourly_cost_of_life:.2f}/hora<br/>Hedonic Treadmill: {self.lifestyle.hedonic_treadmill_score:.0f}%<br/>Status Dependency: {self.lifestyle.status_dependency_percentage:.1f}%", styles['body'])

    def _page_shield_score(self, styles: dict) -> Paragraph:
        return Paragraph(f"<b>SHIELD SCORE</b><br/><br/>Score Total: {self.immunity.shield_score:.0f}%<br/>Categoria: {self.immunity.shield_category}<br/>Resiliencia Meses: {self.immunity.resilience_months_estimate:.1f}", styles['body'])

    def _page_ten_percent_multiplier(self, styles: dict) -> Paragraph:
        return Paragraph(f"<b>EFECTO TIJERA</b><br/><br/>Ingresos +10%: EUR {self.ten_percent.income_increase:.0f}/ano<br/>Gastos -10%: EUR {self.ten_percent.expense_decrease:.0f}/ano<br/>IRE: {self.ten_percent.effort_return_index:.1f}x", styles['body'])

    def _page_money_archetypes(self, styles: dict) -> Paragraph:
        return Paragraph(f"<b>ARQUEOLOGIA PSICO-FINANCIERA</b><br/><br/>Usuario A: {self.archetypes.user_a_archetype}<br/>Usuario B: {self.archetypes.user_b_archetype}<br/>Conflicto Score: {self.archetypes.conflict_score:.0f}%", styles['body'])

    def _page_income_ecosystem(self, styles: dict) -> Paragraph:
        return Paragraph(f"<b>ECOSISTEMA DE INGRESOS</b><br/><br/>IDR: {self.income_ecosystem.diversification_index.diversification_score:.0f}%<br/>Fuentes: {len(self.income_ecosystem.recommendations)}<br/>Roadmap: {self.income_ecosystem.implementation_roadmap[:100]}...", styles['body'])

    def _page_financial_runway(self, styles: dict) -> Paragraph:
        return Paragraph(f"<b>CRONOMETRO FINANCIERO</b><br/><br/>Runway: {self.runway.narrative_desperation_clock}<br/>EUR 50 Extra: {self.runway.cost_per_unnecessary_expense_50:.1f} horas", styles['body'])

    def _page_life_events_legacy(self, styles: dict) -> Paragraph:
        return Paragraph(f"<b>EVENTOS VITALES + LEGADO</b><br/><br/>Indice Legado: {self.legacy.legacy_health_index:.0f}%<br/>Replicacion Hijos: {self.legacy.children_replication_probability:.0f}%", styles['body'])

    def _page_family_central_bank(self, styles: dict) -> Paragraph:
        return Paragraph(f"<b>BANCA CENTRAL DOMESTICA</b><br/><br/>Propuesta: EUR 50/mes x 18 anos = EUR 27,000 con 4%<br/>Legado: +EUR 150K en 40 anos", styles['body'])

    def _page_premium_upsell_cta(self, styles: dict) -> Paragraph:
        return Paragraph(f"<b>PROXIMOS PASOS</b><br/><br/>Strategy Session: EUR 150<br/>Deep Dive: EUR 299<br/>Coaching Anual: EUR 500/mes<br/><br/>Documento Confidencial — Adapta Family Office", styles['body'])
