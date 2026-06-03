#!/usr/bin/env python3
"""Extended diagnostic engine with Phase 1 profile detection and adaptive questioning."""

import logging
from typing import Dict, Any, List
from diagnostic_engine import DiagnosticEngine

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)


class DiagnosticEngineExtended:
    """Extended engine wrapping DiagnosticEngine with profile detection and adaptive questions."""

    def __init__(self, schema_path: str):
        """Initialize with a DiagnosticEngine."""
        self.base_engine = DiagnosticEngine(schema_path)
        logger.info(f"DiagnosticEngineExtended initialized with schema: {schema_path}")

    def generate_perfil(self, respuestas: Dict[str, Any]) -> str:
        """Detect financial profile from Phase 1 responses."""
        try:
            # Ensure respuestas is a dictionary
            if not isinstance(respuestas, dict):
                if hasattr(respuestas, '__dict__'):
                    respuestas = respuestas.__dict__
                else:
                    logger.warning(f"respuestas is not a dict: {type(respuestas)}")
                    return 'estable'

            # Extract Phase 1 financial metrics
            ingresos_netos = respuestas.get('ingresos_netos', 0)
            gastos_totales = respuestas.get('gastos_totales', 0)
            saldo_hipoteca = respuestas.get('saldo_hipoteca', 0)
            saldo_tarjetas = respuestas.get('saldo_tarjetas', 0)
            ahorros_totales = respuestas.get('ahorros_totales', 0)
            stress_nivel = respuestas.get('stress_nivel', 5)
            control_gastos = respuestas.get('control_gastos', 5)

            # Calculate debt and savings ratios
            total_deuda = saldo_hipoteca + saldo_tarjetas
            ratio_deuda_ingresos = total_deuda / ingresos_netos if ingresos_netos > 0 else 10
            ratio_ahorros = ahorros_totales / ingresos_netos if ingresos_netos > 0 else 0
            ratio_gasto_ingreso = gastos_totales / ingresos_netos if ingresos_netos > 0 else 1

            # Profile classification logic - 7 profiles
            if ratio_deuda_ingresos > 4 or (stress_nivel >= 8 and saldo_tarjetas > 5000):
                perfil = 'endeudado_critico'
            elif ratio_deuda_ingresos > 2.5 or (saldo_tarjetas > 2000 and control_gastos < 5):
                perfil = 'endeudado_moderado'
            elif ratio_gasto_ingreso > 0.95 and ahorros_totales < 2000:
                perfil = 'estancado'
            elif ratio_ahorros > 0.5 and control_gastos >= 7:
                perfil = 'conservador'
            elif ratio_deuda_ingresos < 1.5 and ratio_ahorros > 0.2 and control_gastos >= 6:
                perfil = 'emprendedor'
            elif ahorros_totales > 50000 or ratio_ahorros > 0.8:
                perfil = 'patrimonial'
            else:
                perfil = 'estable'

            logger.info(f"Profile detected: {perfil} (deuda/ingresos={ratio_deuda_ingresos:.2f}, ahorros/ingresos={ratio_ahorros:.2f}, gasto/ingreso={ratio_gasto_ingreso:.2f})")
            return perfil
        except Exception as e:
            logger.error(f"Error detecting profile: {e}")
            return 'estable'

    def generate_fase2_questions(self, respuestas: Dict[str, Any], perfil: str) -> List[Dict[str, Any]]:
        """Generate Phase 2 questions adapted to the detected profile."""
        logger.info(f"Generating Phase 2 questions for profile: {perfil}")
        
        # Profile-specific question sets
        questions_by_profile = {
            'endeudado_critico': [
                {
                    'id': 'f2_001',
                    'type': 'multiple_choice',
                    'title': '¿Cuál es tu principal fuente de ingresos?',
                    'options': ['Empleo fijo', 'Autónomo', 'Inversiones', 'Múltiples fuentes']
                },
                {
                    'id': 'f2_002',
                    'type': 'scale',
                    'title': '¿Qué tan factible te parece aumentar tus ingresos en el próximo año?',
                    'scale': [1, 2, 3, 4, 5]
                },
                {
                    'id': 'f2_003',
                    'type': 'multiple_choice',
                    'title': '¿Tienes un fondo de emergencia?',
                    'options': ['No tengo', 'Menos de 1 mes', '1-3 meses', '3-6 meses', 'Más de 6 meses']
                }
            ],
            'endeudado_moderado': [
                {
                    'id': 'f2_004',
                    'type': 'scale',
                    'title': '¿Cuán controlado consideras tu gasto en tarjetas de crédito?',
                    'scale': [1, 2, 3, 4, 5]
                },
                {
                    'id': 'f2_005',
                    'type': 'multiple_choice',
                    'title': '¿Tienes un plan de reducción de deuda?',
                    'options': ['No', 'En mente', 'Parcialmente implementado', 'Totalmente implementado']
                }
            ],
            'estancado': [
                {
                    'id': 'f2_006',
                    'type': 'multiple_choice',
                    'title': '¿Cuáles son tus principales categorías de gasto?',
                    'options': ['Vivienda', 'Alimentación', 'Transporte', 'Ocio', 'Educación']
                },
                {
                    'id': 'f2_007',
                    'type': 'scale',
                    'title': '¿Cuán viable sería reducir tus gastos mensuales?',
                    'scale': [1, 2, 3, 4, 5]
                }
            ],
            'estable': [
                {
                    'id': 'f2_008',
                    'type': 'multiple_choice',
                    'title': '¿En qué estás pensando invertir a largo plazo?',
                    'options': ['Vivienda', 'Educación', 'Inversiones', 'Negocios', 'Jubilación']
                }
            ],
            'conservador': [
                {
                    'id': 'f2_009',
                    'type': 'scale',
                    'title': '¿Qué riesgo estás dispuesto a asumir en tus inversiones?',
                    'scale': [1, 2, 3, 4, 5]
                }
            ],
            'emprendedor': [
                {
                    'id': 'f2_010',
                    'type': 'multiple_choice',
                    'title': '¿Tienes algún proyecto empresarial en mente?',
                    'options': ['No', 'En idea', 'En desarrollo', 'Ya operativo']
                }
            ],
            'patrimonial': [
                {
                    'id': 'f2_011',
                    'type': 'multiple_choice',
                    'title': '¿Has considerado planificación sucesoria?',
                    'options': ['No', 'Levemente', 'En proceso', 'Completada']
                }
            ]
        }

        # Return questions for this profile, default to empty list if profile not found
        return questions_by_profile.get(perfil, [])

    def generate_fase3_questions(self, respuestas: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate Phase 3 psychology questions adapted to stress level."""
        logger.info(f"Generating Phase 3 psychology questions")
        
        stress_nivel = respuestas.get('stress_nivel', 5)
        
        # Adaptive questions based on stress level
        base_questions = [
            {
                'id': 'f3_001',
                'type': 'scale',
                'title': '¿Cuán cómodo te sientes hablando de dinero con tu pareja/familia?',
                'scale': [1, 2, 3, 4, 5]
            },
            {
                'id': 'f3_002',
                'type': 'scale',
                'title': '¿Cuánta confianza tienes en tus decisiones financieras?',
                'scale': [1, 2, 3, 4, 5]
            }
        ]
        
        # High stress questions
        if stress_nivel >= 8:
            base_questions.extend([
                {
                    'id': 'f3_003',
                    'type': 'scale',
                    'title': '¿Cuán urgente es resolver tu situación financiera?',
                    'scale': [1, 2, 3, 4, 5]
                },
                {
                    'id': 'f3_004',
                    'type': 'multiple_choice',
                    'title': '¿Te gustaría apoyo profesional para tu plan financiero?',
                    'options': ['No necesario', 'Quizás', 'Probablemente', 'Definitivamente']
                }
            ])
        # Moderate stress questions
        elif stress_nivel >= 5:
            base_questions.extend([
                {
                    'id': 'f3_005',
                    'type': 'scale',
                    'title': '¿Cómo equilibras ahorro e inversión en tu estrategia?',
                    'scale': [1, 2, 3, 4, 5]
                }
            ])
        # Low stress questions
        else:
            base_questions.extend([
                {
                    'id': 'f3_006',
                    'type': 'multiple_choice',
                    'title': '¿Te gustaría optimizar aún más tu situación financiera?',
                    'options': ['No necesario', 'Sí, marginalmente', 'Sí, considerablemente']
                }
            ])
        
        return base_questions

    def export_json(self, data: Any) -> Dict[str, Any]:
        """Export data to JSON-serializable format"""
        return self.base_engine.export_json(data)
