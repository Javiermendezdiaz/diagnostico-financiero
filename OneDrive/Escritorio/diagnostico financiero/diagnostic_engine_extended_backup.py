"""
Diagnostic Engine Extended - Adaptive phase question generation
Wraps existing DiagnosticEngine with adaptive Phase 2 and Phase 3 question selection
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from diagnostic_engine import DiagnosticEngine

logger = logging.getLogger(__name__)


class DiagnosticEngineExtended:
    """
    Extended diagnostic engine with adaptive question generation for:
    - Phase 2: Personalized questions based on detected financial profile
    - Phase 3: Psychology/behavior questions based on stress and control indicators
    """

    # Phase 2 question bank by profile
    FASE2_QUESTIONS_BY_PROFILE = {
        'endeudado_critico': [
            {'id': 'q_2_1', 'type': 'slider', 'title': '¿Cuál es tu deuda total aproximada?', 'min': 0, 'max': 500000, 'step': 5000, 'suffix': '€'},
            {'id': 'q_2_2', 'type': 'scale', 'title': '¿Qué tan urgente es resolver tu deuda?', 'min': 1, 'max': 10, 'minLabel': 'Puede esperar', 'maxLabel': 'Urgencia crítica'},
            {'id': 'q_2_3', 'type': 'toggle', 'title': '¿Has considerado negociar con acreedores?', 'options': ['No', 'Sí, una vez', 'Sí, múltiples veces'], 'multiple': False},
            {'id': 'q_2_4', 'type': 'slider', 'title': '¿Cuántos acreedores tienes?', 'min': 1, 'max': 20, 'step': 1, 'suffix': 'acreedores'},
            {'id': 'q_2_5', 'type': 'scale', 'title': '¿Cómo es el servicio de tu deuda vs ingresos?', 'min': 1, 'max': 10, 'minLabel': 'Bajo (< 30%)', 'maxLabel': 'Crítico (> 70%)'},
            {'id': 'q_2_6', 'type': 'toggle', 'title': '¿Has recibido ofertas de consolidación?', 'options': ['No', 'Sí, pero rechazé', 'Sí, estoy estudiando'], 'multiple': False},
            {'id': 'q_2_7', 'type': 'slider', 'title': '¿Cuál es tu tasa de interés promedio?', 'min': 0, 'max': 25, 'step': 0.5, 'suffix': '%'},
            {'id': 'q_2_8', 'type': 'comparative', 'title': '¿Tienes avales o co-deudores?', 'leftLabel': 'No', 'rightLabel': 'Sí'},
            {'id': 'q_2_9', 'type': 'toggle', 'title': '¿Parte de tu deuda es por gastos de emergencia?', 'options': ['Sí, toda', 'Parcialmente', 'No, por consumo'], 'multiple': False},
            {'id': 'q_2_10', 'type': 'scale', 'title': '¿Confías en poder salir de esta situación?', 'min': 1, 'max': 10, 'minLabel': 'Nada seguro', 'maxLabel': 'Muy confiado'},
        ],
        'endeudado_moderado': [
            {'id': 'q_2_1', 'type': 'slider', 'title': '¿Cuál es tu ratio deuda/ingresos?', 'min': 0, 'max': 5, 'step': 0.1, 'suffix': 'x'},
            {'id': 'q_2_2', 'type': 'toggle', 'title': '¿Tu deuda está principalmente en hipoteca o tarjetas?', 'options': ['Hipoteca', 'Tarjetas', 'Ambas por igual'], 'multiple': False},
            {'id': 'q_2_3', 'type': 'scale', 'title': '¿Qué tan importante es refinanciar?', 'min': 1, 'max': 10, 'minLabel': 'Baja prioridad', 'maxLabel': 'Muy importante'},
            {'id': 'q_2_4', 'type': 'slider', 'title': '¿Cuántos meses podrías aguantar sin ingresos?', 'min': 0, 'max': 36, 'step': 1, 'suffix': 'meses'},
            {'id': 'q_2_5', 'type': 'toggle', 'title': '¿Has optimizado ya tus pagos?', 'options': ['No sé cómo', 'Parcialmente', 'Sí, completamente'], 'multiple': False},
            {'id': 'q_2_6', 'type': 'scale', 'title': '¿Qué tan cómodo te sientes con tu endeudamiento?', 'min': 1, 'max': 10, 'minLabel': 'Incómodo', 'maxLabel': 'Totalmente cómodo'},
            {'id': 'q_2_7', 'type': 'toggle', 'title': '¿Has considerado un plan de amortización más agresivo?', 'options': ['No', 'Pensando en ello', 'Sí, activamente'], 'multiple': False},
            {'id': 'q_2_8', 'type': 'comparative', 'title': '¿Tienes acceso a crédito adicional si lo necesitas?', 'leftLabel': 'No', 'rightLabel': 'Sí'},
            {'id': 'q_2_9', 'type': 'slider', 'title': '¿Cuál sería tu objetivo de deuda en 5 años?', 'min': 0, 'max': 100, 'step': 5, 'suffix': '% de la actual'},
            {'id': 'q_2_10', 'type': 'scale', 'title': '¿Qué tan cómodo estás con tu estrategia actual?', 'min': 1, 'max': 10, 'minLabel': 'Nada seguro', 'maxLabel': 'Muy confiado'},
        ],
        'estancado': [
            {'id': 'q_2_1', 'type': 'toggle', 'title': '¿Qué te impide avanzar financieramente?', 'options': ['Falta de ingresos', 'Gastos fijos altos', 'Deuda anterior', 'Ambición poco clara'], 'multiple': True},
            {'id': 'q_2_2', 'type': 'scale', 'title': '¿Cuál es tu mayor frustración financiera?', 'min': 1, 'max': 10, 'minLabel': 'Leve', 'maxLabel': 'Extrema'},
            {'id': 'q_2_3', 'type': 'slider', 'title': '¿En cuánto podrías reducir tus gastos?', 'min': 0, 'max': 50, 'step': 5, 'suffix': '%'},
            {'id': 'q_2_4', 'type': 'toggle', 'title': '¿Has considerado un cambio de carrera o ingresos?', 'options': ['No', 'Pensando', 'Sí, activamente'], 'multiple': False},
            {'id': 'q_2_5', 'type': 'scale', 'title': '¿Qué tan satisfecho estás con tu trabajo?', 'min': 1, 'max': 10, 'minLabel': 'Muy insatisfecho', 'maxLabel': 'Muy satisfecho'},
            {'id': 'q_2_6', 'type': 'toggle', 'title': '¿Tienes skills para mejorar ingresos?', 'options': ['No clara', 'Algo de potencial', 'Muy desarrollados'], 'multiple': False},
            {'id': 'q_2_7', 'type': 'slider', 'title': '¿Cuál sería tu meta mensual realista?', 'min': 0, 'max': 10000, 'step': 100, 'suffix': '€'},
            {'id': 'q_2_8', 'type': 'comparative', 'title': '¿Crees que tu situación puede mejorar?', 'leftLabel': 'Difícil', 'rightLabel': 'Posible'},
            {'id': 'q_2_9', 'type': 'scale', 'title': '¿Qué tan flexible eres para cambios?', 'min': 1, 'max': 10, 'minLabel': 'Muy rígido', 'maxLabel': 'Muy flexible'},
            {'id': 'q_2_10', 'type': 'toggle', 'title': '¿Necesitas ayuda específicamente en?', 'options': ['Ingresos', 'Gastos', 'Ambos'], 'multiple': False},
        ],
        'estable': [
            {'id': 'q_2_1', 'type': 'toggle', 'title': '¿Cuál es tu siguiente objetivo financiero?', 'options': ['Más ahorros', 'Invertir', 'Propiedades', 'Educación'], 'multiple': True},
            {'id': 'q_2_2', 'type': 'slider', 'title': '¿Cuánto puedes ahorrar mensualmente?', 'min': 0, 'max': 5000, 'step': 100, 'suffix': '€'},
            {'id': 'q_2_3', 'type': 'scale', 'title': '¿Qué tan interesado estás en invertir?', 'min': 1, 'max': 10, 'minLabel': 'Nada interesado', 'maxLabel': 'Muy interesado'},
            {'id': 'q_2_4', 'type': 'toggle', 'title': '¿Tienes experiencia en inversiones?', 'options': ['No', 'Algo básico', 'Experiencia considerable'], 'multiple': False},
            {'id': 'q_2_5', 'type': 'slider', 'title': '¿Cuál es tu plazo de inversión?', 'min': 1, 'max': 40, 'step': 1, 'suffix': 'años'},
            {'id': 'q_2_6', 'type': 'scale', 'title': '¿Cómo fue tu experiencia con inversiones pasadas?', 'min': 1, 'max': 10, 'minLabel': 'Muy negativa', 'maxLabel': 'Muy positiva'},
            {'id': 'q_2_7', 'type': 'toggle', 'title': '¿Interés en diversificación?', 'options': ['No sé qué es', 'Alguno', 'Mucho interés'], 'multiple': False},
            {'id': 'q_2_8', 'type': 'comparative', 'title': '¿Prefieres seguridad o rentabilidad?', 'leftLabel': 'Seguridad', 'rightLabel': 'Rentabilidad'},
            {'id': 'q_2_9', 'type': 'slider', 'title': '¿En qué plazo necesitarás el dinero?', 'min': 0, 'max': 30, 'step': 1, 'suffix': 'años'},
            {'id': 'q_2_10', 'type': 'scale', 'title': '¿Confianza en tu plan de largo plazo?', 'min': 1, 'max': 10, 'minLabel': 'Nada seguro', 'maxLabel': 'Muy confiado'},
        ],
        'conservador': [
            {'id': 'q_2_1', 'type': 'scale', 'title': '¿Qué importancia tiene el capital seguro?', 'min': 1, 'max': 10, 'minLabel': 'Baja', 'maxLabel': 'Máxima'},
            {'id': 'q_2_2', 'type': 'slider', 'title': '¿Cuál es tu tasa mínima aceptable?', 'min': 0, 'max': 5, 'step': 0.1, 'suffix': '%'},
            {'id': 'q_2_3', 'type': 'toggle', 'title': '¿Has experimentado pérdidas financieras?', 'options': ['No', 'Sí, pequeñas', 'Sí, significativas'], 'multiple': False},
            {'id': 'q_2_4', 'type': 'scale', 'title': '¿Nivel de confianza en mercados?', 'min': 1, 'max': 10, 'minLabel': 'Muy desconfiado', 'maxLabel': 'Muy confiado'},
            {'id': 'q_2_5', 'type': 'toggle', 'title': '¿Interés en productos garantizados?', 'options': ['No', 'Alguno', 'Máximo interés'], 'multiple': False},
            {'id': 'q_2_6', 'type': 'slider', 'title': '¿Qué % en inversiones de bajo riesgo?', 'min': 0, 'max': 100, 'step': 5, 'suffix': '%'},
            {'id': 'q_2_7', 'type': 'scale', 'title': '¿Duración que necesitas mantener inversión?', 'min': 1, 'max': 10, 'minLabel': 'Muy corto plazo', 'maxLabel': 'Muy largo plazo'},
            {'id': 'q_2_8', 'type': 'comparative', 'title': '¿Acceso a asesoría financiera?', 'leftLabel': 'No', 'rightLabel': 'Sí'},
            {'id': 'q_2_9', 'type': 'toggle', 'title': '¿Has considerado seguros especiales?', 'options': ['No', 'Un poco', 'Sí, me interesa'], 'multiple': False},
            {'id': 'q_2_10', 'type': 'scale', 'title': '¿Qué tan satisfecho estás con ahorros actuales?', 'min': 1, 'max': 10, 'minLabel': 'Nada satisfecho', 'maxLabel': 'Muy satisfecho'},
        ],
        'emprendedor': [
            {'id': 'q_2_1', 'type': 'toggle', 'title': '¿En qué fase está tu negocio?', 'options': ['Idea', 'Lanzamiento', 'Crecimiento', 'Consolidado'], 'multiple': False},
            {'id': 'q_2_2', 'type': 'slider', 'title': '¿Cuánto inviertes anualmente en crecimiento?', 'min': 0, 'max': 100000, 'step': 5000, 'suffix': '€'},
            {'id': 'q_2_3', 'type': 'scale', 'title': '¿Qué tan crítico es el capital de trabajo?', 'min': 1, 'max': 10, 'minLabel': 'No importante', 'maxLabel': 'Crítico'},
            {'id': 'q_2_4', 'type': 'toggle', 'title': '¿Necesitas financiación externa?', 'options': ['No', 'Quizás', 'Sí, urgente'], 'multiple': False},
            {'id': 'q_2_5', 'type': 'slider', 'title': '¿Cuál es tu margen operativo?', 'min': -50, 'max': 100, 'step': 5, 'suffix': '%'},
            {'id': 'q_2_6', 'type': 'scale', 'title': '¿Diversificación de ingresos en negocio?', 'min': 1, 'max': 10, 'minLabel': 'Una sola fuente', 'maxLabel': 'Múltiples fuentes'},
            {'id': 'q_2_7', 'type': 'toggle', 'title': '¿Riesgo operativo controlado?', 'options': ['No, elevado', 'Parcialmente', 'Sí, controlado'], 'multiple': False},
            {'id': 'q_2_8', 'type': 'comparative', 'title': '¿Planes de salida o escalabilidad?', 'leftLabel': 'No claro', 'rightLabel': 'Sí, claro'},
            {'id': 'q_2_9', 'type': 'slider', 'title': '¿Proyección de crecimiento anual?', 'min': -50, 'max': 200, 'step': 10, 'suffix': '%'},
            {'id': 'q_2_10', 'type': 'scale', 'title': '¿Confianza en viabilidad del negocio?', 'min': 1, 'max': 10, 'minLabel': 'Baja confianza', 'maxLabel': 'Alta confianza'},
        ],
        'patrimonial': [
            {'id': 'q_2_1', 'type': 'slider', 'title': '¿Cuál es tu patrimonio neto?', 'min': 500000, 'max': 50000000, 'step': 100000, 'suffix': '€'},
            {'id': 'q_2_2', 'type': 'toggle', 'title': '¿Tipo de activos principales?', 'options': ['Inmuebles', 'Valores', 'Negocios', 'Mixto'], 'multiple': True},
            {'id': 'q_2_3', 'type': 'scale', 'title': '¿Nivel de diversificación actual?', 'min': 1, 'max': 10, 'minLabel': 'Muy concentrado', 'maxLabel': 'Altamente diversificado'},
            {'id': 'q_2_4', 'type': 'toggle', 'title': '¿Necesidad de planificación sucesoria?', 'options': ['No', 'Sí, alguna', 'Sí, urgente'], 'multiple': False},
            {'id': 'q_2_5', 'type': 'slider', 'title': '¿Qué % de patrimonio en inversiones?', 'min': 0, 'max': 100, 'step': 5, 'suffix': '%'},
            {'id': 'q_2_6', 'type': 'scale', 'title': '¿Optimización fiscal implementada?', 'min': 1, 'max': 10, 'minLabel': 'Ninguna', 'maxLabel': 'Máxima'},
            {'id': 'q_2_7', 'type': 'toggle', 'title': '¿Interés en family office?', 'options': ['No', 'Considerando', 'Sí, activamente'], 'multiple': False},
            {'id': 'q_2_8', 'type': 'comparative', 'title': '¿Asesoría especializada?', 'leftLabel': 'No', 'rightLabel': 'Sí'},
            {'id': 'q_2_9', 'type': 'slider', 'title': '¿Objetivo de rendimiento anual?', 'min': 0, 'max': 15, 'step': 0.5, 'suffix': '%'},
            {'id': 'q_2_10', 'type': 'scale', 'title': '¿Confianza en estrategia patrimonial?', 'min': 1, 'max': 10, 'minLabel': 'Nada seguro', 'maxLabel': 'Muy confiado'},
        ],
    }

    # Phase 3 questions based on stress levels
    FASE3_QUESTIONS_BASE = [
        {'id': 'q_3_1', 'type': 'scale', 'title': '¿Cuánto control tienes sobre tus emociones financieras?', 'min': 1, 'max': 10, 'minLabel': 'Ninguno', 'maxLabel': 'Total control'},
        {'id': 'q_3_2', 'type': 'toggle', 'title': '¿Sueles tomar decisiones impulsivas con dinero?', 'options': ['Raramente', 'A veces', 'Frecuentemente'], 'multiple': False},
        {'id': 'q_3_3', 'type': 'comparative', 'title': '¿Compras para sentirte mejor emocionalmente?', 'leftLabel': 'Nunca', 'rightLabel': 'Frecuentemente'},
        {'id': 'q_3_4', 'type': 'scale', 'title': '¿Qué tan realista es tu visión financiera?', 'min': 1, 'max': 10, 'minLabel': 'Muy optimista', 'maxLabel': 'Muy pesimista'},
        {'id': 'q_3_5', 'type': 'toggle', 'title': '¿Hablas de dinero con tu pareja/familia?', 'options': ['Evito el tema', 'A veces', 'Regularmente'], 'multiple': False},
        {'id': 'q_3_6', 'type': 'scale', 'title': '¿Cuánta culpa sientes por decisiones pasadas?', 'min': 1, 'max': 10, 'minLabel': 'Ninguna', 'maxLabel': 'Mucha culpa'},
        {'id': 'q_3_7', 'type': 'comparative', 'title': '¿Tu dinero controla tu vida?', 'leftLabel': 'Yo controlo', 'rightLabel': 'Me controla'},
        {'id': 'q_3_8', 'type': 'toggle', 'title': '¿Has experimentado ansiedad por dinero?', 'options': ['Nunca', 'Ocasionalmente', 'Frecuentemente'], 'multiple': False},
        {'id': 'q_3_9', 'type': 'scale', 'title': '¿Cuánta confianza tienes en tu futuro?', 'min': 1, 'max': 10, 'minLabel': 'Ninguna confianza', 'maxLabel': 'Total confianza'},
        {'id': 'q_3_10', 'type': 'toggle', 'title': '¿Qué creencia sobre dinero define tu vida?', 'options': ['Es malo', 'Es herramienta', 'Es libertad'], 'multiple': False},
    ]

    def __init__(self, schema_path: str):
        """Initialize extended engine with schema path"""
        self.schema_path = Path(schema_path)
        self.base_engine = DiagnosticEngine(schema_path)
        logger.info(f"DiagnosticEngineExtended initialized with schema: {schema_path}")

    def generate_fase2_questions(self, respuestas: Dict[str, Any], perfil: str) -> List[Dict[str, Any]]:
        """
        Generate Phase 2 questions based on detected financial profile.
        Returns 10-15 personalized questions based on perfil classification.
        """
        if perfil not in self.FASE2_QUESTIONS_BY_PROFILE:
            logger.warning(f"Unknown profile: {perfil}. Using 'estable' as default.")
            perfil = 'estable'

        questions = self.FASE2_QUESTIONS_BY_PROFILE.get(perfil, [])
        logger.info(f"Generated {len(questions)} Phase 2 questions for profile: {perfil}")

        return questions

    def generate_fase3_questions(self, respuestas: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate Phase 3 psychology questions.
        Returns 8-10 questions with stress-level adaptation.
        """
        stress_level = respuestas.get('stress_nivel', 5)

        # Reorder questions based on stress level
        # High stress → more emotional/coping questions first
        # Low stress → more behavioral/pattern questions first
        if stress_level >= 7:
            # High stress: prioritize emotional support and coping
            ordered = [
                self.FASE3_QUESTIONS_BASE[6],  # Control life
                self.FASE3_QUESTIONS_BASE[8],  # Future confidence
                self.FASE3_QUESTIONS_BASE[4],  # Talk about money
                self.FASE3_QUESTIONS_BASE[7],  # Anxiety experience
                self.FASE3_QUESTIONS_BASE[0],  # Emotional control
                self.FASE3_QUESTIONS_BASE[2],  # Emotional purchasing
                self.FASE3_QUESTIONS_BASE[5],  # Guilt
                self.FASE3_QUESTIONS_BASE[1],  # Impulsive decisions
                self.FASE3_QUESTIONS_BASE[3],  # Financial vision realism
                self.FASE3_QUESTIONS_BASE[9],  # Money belief
            ]
        else:
            # Normal stress: balanced approach
            ordered = self.FASE3_QUESTIONS_BASE

        logger.info(f"Generated {len(ordered)} Phase 3 questions (stress={stress_level})")
        return ordered

    def generate_perfil(self, respuestas: Dict[str, Any]) -> str:
        """
        Detect financial profile from Phase 1 responses.
        Classification into 7 profiles based on debt, savings, and stress.
        """
        try:
