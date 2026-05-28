"""
DIAGNOSTIC ENGINE v1.0 — TOP 1% IMPLEMENTATION
Financial Brutal Honesty Diagnostic System

Architecture:
1. ScoringEngine — response processing + cross-layer weighting
2. ProfilingSystem — score → categories + alerts
3. BenchmarkEngine — percentiles + comparative positioning
4. RecommendationEngine — priority-based action items
5. DiagnosticReport — complete output schema
"""

import json
import statistics
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import numpy as np


class DiagnosticCategory(Enum):
    """Score → Category mapping"""
    CRITICO = "crítico"        # 0-20: Urgent intervention needed
    DEBIL = "débil"            # 20-40: Significant weakness
    NORMAL = "normal"          # 40-60: Acceptable baseline
    FUERTE = "fuerte"          # 60-80: Solid position
    EXCELENTE = "excelente"    # 80-100: Top tier


@dataclass
class CapaScore:
    """Score result for single capa"""
    capa: str
    score: float
    category: str
    percentile: Optional[float] = None
    rank: Optional[int] = None


@dataclass
class Alert:
    """Critical issue detection"""
    capa: str
    severity: str  # "crítico", "alerta", "atención"
    message: str
    impact: str
    action: str


@dataclass
class Recommendation:
    """Prioritized action item"""
    priority: int  # 1=highest
    capa: str
    issue: str
    action: str
    impact: str  # "impacto alto" / "impacto medio"
    effort: str  # "esfuerzo bajo" / "esfuerzo medio" / "esfuerzo alto"
    resources: List[str]  # links, herramientas
    timeline: str  # "inmediato" / "próximos 30 días" / "próximos 90 días"


@dataclass
class DiagnosticResult:
    """Complete diagnostic output"""
    user_id: Optional[str]
    timestamp: str
    total_questions_answered: int
    capa_scores: Dict[str, float]
    capa_categories: Dict[str, str]
    capa_percentiles: Dict[str, float]
    overall_score: float
    alerts: List[Alert]
    recommendations: List[Recommendation]
    profile: Dict  # persona + debilidades + fortalezas
    benchmark: Dict  # posicionamiento


class ScoringEngine:
    """Core scoring algorithm"""
    
    def __init__(self, schema_path: str):
        """Load schema with question definitions"""
        with open(schema_path, 'r', encoding='utf-8') as f:
            self.schema = json.load(f)
        
        self.capas = self.schema['capas']
        self.questions_by_id = self._build_question_index()
        self.population_distribution = self._init_population()
    
    def _build_question_index(self) -> Dict:
        """Map question_id → question object + capa"""
        index = {}
        for capa_name, capa_obj in self.capas.items():
            for q in capa_obj['preguntas']:
                index[q['id']] = {'question': q, 'capa': capa_name}
        return index
    
    def _init_population(self) -> Dict:
        """Initialize population distribution (for benchmarking)
        Later: load from real data. For now: synthetic distribution"""
        return {
            capa: {
                'mean': np.random.normal(55, 15),
                'std': np.random.normal(18, 3),
                'samples': 10000
            }
            for capa in self.capas.keys()
        }
    
    def score_responses(self, responses: Dict[str, int]) -> Dict[str, float]:
        """
        Process user responses → capa scores (0-100)
        
        Args:
            responses: {question_id: answer_index (0-3)}
        
        Returns:
            {capa_name: score (0-100)}
        """
        capa_scores = {capa: [] for capa in self.capas.keys()}
        capa_weights = {capa: [] for capa in self.capas.keys()}
        
        # Process each response
        for q_id, answer_idx in responses.items():
            if q_id not in self.questions_by_id:
                continue
            
            q_data = self.questions_by_id[q_id]
            question = q_data['question']
            primary_capa = q_data['capa']
            
            # Get score from answer
            if 0 <= answer_idx < len(question['respuestas']):
                response_score = question['respuestas'][answer_idx]['score']
            else:
                continue
            
            # Apply cross-layer weighting
            pesos = question['pesos']
            for capa, weight in pesos.items():
                if capa in capa_scores:
                    capa_scores[capa].append(response_score)
                    capa_weights[capa].append(weight)
        
        # Calculate weighted averages
        final_scores = {}
        for capa in self.capas.keys():
            if capa_scores[capa]:
                # Weighted average
                weighted_sum = sum(
                    score * weight 
                    for score, weight in zip(capa_scores[capa], capa_weights[capa])
                )
                weight_sum = sum(capa_weights[capa])
                final_scores[capa] = weighted_sum / weight_sum if weight_sum > 0 else 50
            else:
                final_scores[capa] = 50  # default
        
        return {k: max(0, min(100, v)) for k, v in final_scores.items()}
    
    def calculate_percentiles(self, scores: Dict[str, float]) -> Dict[str, float]:
        """Position scores within population distribution"""
        percentiles = {}
        for capa, score in scores.items():
            dist = self.population_distribution[capa]
            # Z-score → percentile
            z = (score - dist['mean']) / dist['std'] if dist['std'] > 0 else 0
            percentile = 100 * (1 / (1 + np.exp(-z * 0.75)))  # sigmoid approximation
            percentiles[capa] = max(0, min(100, percentile))
        return percentiles


class ProfilingSystem:
    """Map scores → categories + personas"""
    
    @staticmethod
    def score_to_category(score: float) -> str:
        """Score (0-100) → DiagnosticCategory"""
        if score < 20:
            return DiagnosticCategory.CRITICO.value
        elif score < 40:
            return DiagnosticCategory.DEBIL.value
        elif score < 60:
            return DiagnosticCategory.NORMAL.value
        elif score < 80:
            return DiagnosticCategory.FUERTE.value
        else:
            return DiagnosticCategory.EXCELENTE.value
    
    @staticmethod
    def detect_alerts(scores: Dict[str, float], percentiles: Dict[str, float]) -> List[Alert]:
        """Identify critical issues"""
        alerts = []
        
        # Pattern detection
        lowest_capas = sorted(scores.items(), key=lambda x: x[1])[:2]
        
        for capa, score in lowest_capas:
            if score < 30:
                alerts.append(Alert(
                    capa=capa,
                    severity="crítico",
                    message=f"{capa}: Score {score:.0f} (bottom {100-percentiles[capa]:.0f}%)",
                    impact="Riesgo inminente de crisis en esta dimensión",
                    action=f"Intervención inmediata en {capa} requerida"
                ))
            elif score < 45:
                alerts.append(Alert(
                    capa=capa,
                    severity="alerta",
                    message=f"{capa}: Score {score:.0f} (debajo de media poblacional)",
                    impact="Debilidad significativa",
                    action=f"Plan de mejora de 30 días en {capa}"
                ))
        
        # Debt resilience check
        if scores.get('resiliencia_deuda', 50) < 35 and scores.get('flujo_caja', 50) < 40:
            alerts.append(Alert(
                capa="resiliencia_deuda + flujo_caja",
                severity="crítico",
                message="Deuda y flujo simultáneamente débiles = riesgo de insolvencia",
                impact="Crisis inminente probable ante cualquier choque",
                action="Reestructuración de deuda + aumento inmediato de colchón"
            ))
        
        # Burnout + HHI check
        if scores.get('burnout', 50) < 30 and scores.get('hhi_ingresos', 50) > 70:
            alerts.append(Alert(
                capa="burnout + hhi_ingresos",
                severity="alerta",
                message="Alto burnout + ingresos concentrados = riesgo de colapso dual",
                impact="Salud mental + estabilidad financiera ambas comprometidas",
                action="Diversificación de ingresos + intervención de salud mental"
            ))
        
        return alerts
    
    @staticmethod
    def build_profile(scores: Dict[str, float], percentiles: Dict[str, float]) -> Dict:
        """Create narrative profile"""
        sorted_capas = sorted(scores.items(), key=lambda x: x[1])
        
        return {
            'fortalezas': [capa for capa, score in sorted_capas[-3:] if score > 60],
            'debilidades': [capa for capa, score in sorted_capas[:3] if score < 50],
            'balance': {
                'ofensiva': scores.get('numero_fi', 50),
                'defensa': scores.get('blindaje_legal', 50),
                'operación': scores.get('flujo_caja', 50),
                'riesgo': scores.get('antifragilidad', 50)
            },
            'persona_label': ProfilingSystem._classify_persona(scores),
            'urgency': 'inminente' if any(s < 30 for s in scores.values()) else 'alta' if any(s < 45 for s in scores.values()) else 'normal'
        }
    
    @staticmethod
    def _classify_persona(scores: Dict[str, float]) -> str:
        """User archetype"""
        avg = statistics.mean(scores.values())
        debt_risk = scores.get('resiliencia_deuda', 50)
        income_stability = 100 - scores.get('hhi_ingresos', 50)
        
        if avg < 35:
            return "Freefall — Necesita intervención urgente"
        elif avg < 50 and debt_risk < 40:
            return "Overextended — Apalancado + vulnerable"
        elif income_stability > 70 and scores.get('flujo_caja', 50) > 70:
            return "Prudent — Estructurado, defensivo"
        elif avg > 70:
            return "Affluent — Posición fuerte, optimizable"
        else:
            return "Precarious — Stable pero frágil ante shocks"


class RecommendationEngine:
    """Generate prioritized action items"""
    
    RECOMMENDATION_MATRIX = {
        'burnout': [
            {
                'issue': 'Hoy: Burnout elevado → Quieres: Libertad laboral',
                'action': 'Paso 1: Mapea opciones de salida (freelance, emprendimiento, cambio sector)',
                'impact': 'alto',
                'effort': 'bajo',
                'timeline': 'exploración',
                'resources': ['análisis de oportunidades', 'networking en tu sector']
            },
            {
                'issue': 'Requisito para cambio: colchón financiero',
                'action': 'Paso 2: Construye 6-12 meses de gastos fijos en efectivo/depósito',
                'impact': 'alto',
                'effort': 'medio',
                'timeline': 'fase progresiva',
                'resources': ['reducción de gastos discrecionales', 'ingresos secundarios']
            },
            {
                'issue': 'Sin colchón: riesgo de fracaso en salida',
                'action': 'Paso 3: Consolida ingresos alternativos (al alcanzar colchón, ya tienes fuentes)',
                'impact': 'alto',
                'effort': 'alto',
                'timeline': 'paralelo',
                'resources': ['plataformas freelance', 'análisis de activos alternativos']
            }
        ],
        'numero_fi': [
            {
                'issue': 'Hoy: Ignoras tu número FI → Quieres: Independencia financiera',
                'action': 'Paso 1: Calcula tu número FI realista (gastos anuales × 25)',
                'impact': 'alto',
                'effort': 'bajo',
                'timeline': 'inmediato',
                'resources': ['firecalc.com', 'hoja cálculo FI']
            },
            {
                'issue': 'Sin meta clara: no sabes cuánto ahorrar',
                'action': 'Paso 2: Define trayecto progresivo (dónde estás, dónde quieres estar)',
                'impact': 'alto',
                'effort': 'bajo',
                'timeline': 'inmediato',
                'resources': ['modelo de tasa de ahorro', 'scenario modeling']
            }
        ],
        'resiliencia_deuda': [
            {
                'issue': 'Hoy: Deuda te limita → Quieres: Control financiero',
                'action': 'Paso 1: Audita toda deuda (importe, tasa, vencimiento, cobertor)',
                'impact': 'alto',
                'effort': 'bajo',
                'timeline': 'inmediato',
                'resources': ['extractos de banco', 'checklist de deuda']
            },
            {
                'issue': 'Sin visibilidad: no sabes riesgo real',
                'action': 'Paso 2: Optimiza pagos (refinancia si mejora tasa, acelera si intereses altos)',
                'impact': 'medio',
                'effort': 'medio',
                'timeline': 'fase táctica',
                'resources': ['comparador hipotecario', 'asesor financiero']
            }
        ],
        'flujo_caja': [
            {
                'issue': 'Hoy: Sin visibilidad de dinero → Quieres: Control total',
                'action': 'Paso 1: Proyecta 12 meses de flujo (ingresos, gastos fijos, variables)',
                'impact': 'medio',
                'effort': 'bajo',
                'timeline': 'inmediato',
                'resources': ['extractos últimos 6 meses', 'hoja cálculo flujo']
            },
            {
                'issue': 'Sin proyección: gastos sorpresa destruyen planes',
                'action': 'Paso 2: Identifica gastos estacionales y discrecionales a controlar',
                'impact': 'medio',
                'effort': 'bajo',
                'timeline': 'fase análisis',
                'resources': ['categorización de gastos', 'herramienta presupuesto']
            }
        ],
        'antifragilidad': [
            {
                'issue': 'Hoy: Un ingreso = riesgo máximo → Quieres: Múltiples flujos',
                'action': 'Paso 1: Diagnostica opciones de diversificación (freelance, negocio, activos)',
                'impact': 'alto',
                'effort': 'bajo',
                'timeline': 'exploración',
                'resources': ['análisis de habilidades monetizables', 'trends en tu sector']
            },
            {
                'issue': 'Sin opción B: pérdida de empleo = crisis',
                'action': 'Paso 2: Desarrolla primera fuente alternativa en paralelo a empleo actual',
                'impact': 'alto',
                'effort': 'medio',
                'timeline': 'fase constructiva',
                'resources': ['plataformas (Upwork, Fiverr)', 'network profesional']
            }
        ],
        'lifestyle_creep': [
            {
                'issue': 'Hoy: Gastos sin control → Quieres: Decisiones conscientes',
                'action': 'Paso 1: Categoriza 90 días de gastos (fijos, variables, discrecionales)',
                'impact': 'medio',
                'effort': 'bajo',
                'timeline': 'inmediato',
                'resources': ['extractos de tarjeta/banco', 'herramienta análisis']
            },
            {
                'issue': 'Sin techo: gastos crecen sin límite',
                'action': 'Paso 2: Fija presupuesto por categoría basado en tus prioridades reales',
                'impact': 'medio',
                'effort': 'bajo',
                'timeline': 'fase de implementación',
                'resources': ['apps presupuesto (YNAB, Notion)', 'disciplina automática']
            }
        ],
        'blindaje_legal': [
            {
                'issue': 'Hoy: Sin blindaje legal → Quieres: Patrimonio protegido',
                'action': 'Paso 1: Audita estructura actual (propiedades, cuentas, régimen matrimonial)',
                'impact': 'alto',
                'effort': 'bajo',
                'timeline': 'inmediato',
                'resources': ['notas simples', 'certificado matrimonial', 'gestoría']
            },
            {
                'issue': 'Sin protección: activos expuestos a acreedores',
                'action': 'Paso 2: Implementa blindaje apropiado a tu situación (cambio régimen, SL, fondos)',
                'impact': 'alto',
                'effort': 'alto',
                'timeline': 'fase estratégica',
                'resources': ['asesor legal', 'gestor fiscal']
            }
        ]
    }
    
    @staticmethod
    def generate_recommendations(
        scores: Dict[str, float],
        percentiles: Dict[str, float],
        alerts: List[Alert]
    ) -> List[Recommendation]:
        """Priority-based action items"""
        
        recommendations = []
        priority = 1
        
        # Rank capas by need (lowest scores first)
        ranked = sorted(scores.items(), key=lambda x: x[1])
        
        for capa, score in ranked:
            if capa not in RecommendationEngine.RECOMMENDATION_MATRIX:
                continue
            
            # Skip high-scoring capas (already good)
            if score > 70:
                continue
            
            matrix = RecommendationEngine.RECOMMENDATION_MATRIX[capa]
            
            for rec_template in matrix:
                recommendations.append(Recommendation(
                    priority=priority,
                    capa=capa,
                    issue=rec_template['issue'],
                    action=rec_template['action'],
                    impact=f"impacto {rec_template['impact']}",
                    effort=f"esfuerzo {rec_template['effort']}",
                    resources=rec_template['resources'],
                    timeline=rec_template['timeline']
                ))
                priority += 1
                
                if priority > 10:  # Cap at 10 recommendations
                    break
            
            if priority > 10:
                break
        
        return recommendations[:10]


class DiagnosticEngine:
    """Main orchestrator"""
    
    def __init__(self, schema_path: str):
        self.scoring = ScoringEngine(schema_path)
        self.profiling = ProfilingSystem()
        self.recommendations = RecommendationEngine()
    
    def diagnose(
        self,
        responses: Dict[str, int],
        user_id: Optional[str] = None
    ) -> DiagnosticResult:
        """
        Run complete diagnostic
        
        Args:
            responses: {question_id: answer_index (0-3)}
            user_id: Optional user identifier
        
        Returns:
            DiagnosticResult with scores, categories, alerts, recommendations
        """
        from datetime import datetime
        
        # Scoring
        capa_scores = self.scoring.score_responses(responses)
        capa_percentiles = self.scoring.calculate_percentiles(capa_scores)
        
        # Categorization
        capa_categories = {
            capa: self.profiling.score_to_category(score)
            for capa, score in capa_scores.items()
        }
        
        # Alerts
        alerts = self.profiling.detect_alerts(capa_scores, capa_percentiles)
        
        # Recommendations
        recommendations = self.recommendations.generate_recommendations(
            capa_scores, capa_percentiles, alerts
        )
        
        # Profile
        profile = self.profiling.build_profile(capa_scores, capa_percentiles)
        
        # Overall score
        overall = statistics.mean(capa_scores.values())
        
        # Benchmark
        benchmark = {
            'user_percentile': statistics.mean(capa_percentiles.values()),
            'distribution': capa_percentiles,
            'vs_average': {
                capa: score - 55
                for capa, score in capa_scores.items()
            }
        }
        
        return DiagnosticResult(
            user_id=user_id,
            timestamp=datetime.now().isoformat(),
            total_questions_answered=len(responses),
            capa_scores=capa_scores,
            capa_categories=capa_categories,
            capa_percentiles=capa_percentiles,
            overall_score=overall,
            alerts=alerts,
            recommendations=recommendations,
            profile=profile,
            benchmark=benchmark
        )
    
    def export_json(self, result: DiagnosticResult) -> Dict:
        """Export result as JSON-serializable dict"""
        return {
            'metadata': {
                'user_id': result.user_id,
                'timestamp': result.timestamp,
                'questions_answered': result.total_questions_answered
            },
            'scores': result.capa_scores,
            'categories': result.capa_categories,
            'percentiles': result.capa_percentiles,
            'overall_score': round(result.overall_score, 1),
            'alerts': [
                {
                    'capa': a.capa,
                    'severity': a.severity,
                    'message': a.message,
                    'impact': a.impact,
                    'action': a.action
                }
                for a in result.alerts
            ],
            'recommendations': [
                {
                    'priority': r.priority,
                    'capa': r.capa,
                    'issue': r.issue,
                    'action': r.action,
                    'impact': r.impact,
                    'effort': r.effort,
                    'timeline': r.timeline,
                    'resources': r.resources
                }
                for r in result.recommendations
            ],
            'profile': result.profile,
            'benchmark': result.benchmark
        }


# ===== TEST =====
if __name__ == '__main__':
    schema_path = '/sessions/ecstatic-hopeful-ptolemy/mnt/diagnostico financiero/data-schema-500.json'
    
    # Initialize
    engine = DiagnosticEngine(schema_path)
    print("✓ Engine initialized")
    
    # Simulate responses (random user profile)
    import random
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema = json.load(f)
    
    all_q_ids = []
    for capa_obj in schema['capas'].values():
        all_q_ids.extend([q['id'] for q in capa_obj['preguntas']])
    
    # Scenario 1: Struggling user (low scores across board)
    responses_struggling = {
        q_id: random.choice([0, 1])  # mostly low answers
        for q_id in all_q_ids[:250]  # 50% of questions
    }
    
    result = engine.diagnose(responses_struggling, user_id='user_struggling')
    
    print("\n" + "=" * 60)
    print("DIAGNOSTIC RESULT — STRUGGLING USER")
    print("=" * 60)
    print(f"Overall Score: {result.overall_score:.1f}/100")
    print(f"Personas: {result.profile['persona_label']}")
    print(f"Urgency: {result.profile['urgency']}")
    print(f"\nCapas Scores:")
    for capa in sorted(result.capa_scores.keys()):
        score = result.capa_scores[capa]
        category = result.capa_categories[capa]
        pct = result.capa_percentiles[capa]
        print(f"  {capa:20s}: {score:6.1f} ({category:10s}) — {pct:.0f}th percentile")
    
    if result.alerts:
        print(f"\nAlerts ({len(result.alerts)}):")
        for a in result.alerts[:3]:
            print(f"  [{a.severity.upper()}] {a.capa}: {a.message}")
            print(f"    → {a.action}")
    
    if result.recommendations:
        print(f"\nTop Recommendations:")
        for r in result.recommendations[:3]:
            print(f"  {r.priority}. [{r.capa}] {r.action}")
            print(f"     Impact: {r.impact} | Effort: {r.effort} | Timeline: {r.timeline}")
    
    # Export JSON
    result_json = engine.export_json(result)
    print(f"\n✓ Export ready: {len(json.dumps(result_json))} bytes")
    
    print("\n✅ DIAGNOSTIC ENGINE OPERATIONAL")

