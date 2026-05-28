#!/usr/bin/env python3
"""
Generador de reporte PDF ejemplo para diagnostico financiero.
Simula un cuestionario completado con 100 respuestas y genera PDF.
"""

import sys
import json
from datetime import datetime
from pathlib import Path

# Importar el generador de reportes
from diagnostic_report_generator import DiagnosticReportGenerator

def generate_example_report():
    """Generar PDF de ejemplo con datos realistas de 100 preguntas completadas"""

    # Datos de diagnóstico ejemplo - simulando respuestas a 100 preguntas
    # El score se calcula sobre la base de patrones de respuesta ficticios
    diagnostic_result = {
        'overall_score': 62,  # Score moderado - margen de mejora
        'user_id': 'USUARIO_EJEMPLO_001',
        'timestamp': datetime.now().isoformat(),

        # 5 áreas de salud financiera (scores derivados de 100 preguntas)
        'health_scores': {
            'clarity': 58,      # Visibilidad parcial: tiene presupuesto pero no detallado
            'resilience': 48,   # Baja resiliencia: fondo emergencia insuficiente
            'control': 65,      # Buen control: disciplina moderada en gastos
            'knowledge': 62,    # Conocimiento medio: entiende basics, no opciones complejas
            'agency': 72        # Alta agencia: cree que puede mejorar su situación
        },

        # Arquetipo psicológico de dinero (basado en Kahneman/Thaler)
        'archetype': 'vividor_presente',

        # Alertas identificadas del análisis
        'alerts': [
            {
                'severity': 'crítico',
                'title': 'Fondo de Emergencia Crítico',
                'description': (
                    'Solo tienes €3,500 ahorrados (aprox. 1.5 meses de gastos). '
                    'Estándar recomendado: 6 meses. En caso de desempleo tendrías estrés severo.'
                )
            },
            {
                'severity': 'alerta',
                'title': 'Deuda de Tarjeta de Crédito (TAE 21.8%)',
                'description': (
                    'Llevas €8,200 en revolving pagando intereses cada mes. '
                    'Estimado: €150/mes de coste financiero puro. Transferencia urgente a producto más barato.'
                )
            },
            {
                'severity': 'atención',
                'title': 'Visibilidad Limitada de Gastos Discrecionales',
                'description': (
                    'Suscripciones + entretenimiento + restaurantes sin categorización clara. '
                    'Estimado €600-800/mes en "fugas" identificables.'
                )
            },
            {
                'severity': 'atención',
                'title': 'Ausencia de Planificación Fiscal Deliberada',
                'description': (
                    'No estás aprovechando desgravaciones disponibles (planes pensiones, vivienda, hijo a cargo). '
                    'Estimado €1,500-2,000/año de ahorro fiscal sin aprovechar.'
                )
            }
        ],

        # Plan de acción N.A.P. (Núcleo/Acción/Plazo)
        'nap_actions': [
            {
                'nucleos': 'Crear Fondo de Emergencia a 6 Meses',
                'acciones': [
                    'Abre una cuenta separada etiquetada "EMERGENCIAS"',
                    'Configura transferencia automática €250/mes',
                    'Objetivo fase 1 (3 meses): €750 | Fase 2 (1 año): €3,000 | Objetivo final: €21,000',
                    'Deja el dinero en depósito a plazo fijo (2-3% rentabilidad segura)'
                ],
                'plazo': '90 días para €750 iniciales; objetivo completo en 3 años'
            },
            {
                'nucleos': 'Eliminar Deuda de Crédito de Revolving',
                'acciones': [
                    'Paso 1 (semana 1): Llama a tu banco con cifra exacta (€8,200) + extractos 6 meses',
                    'Paso 2 (semana 2): Negocia reducción TAE de 21.8% a 15-17% (es posible)',
                    'Paso 3 (si rechazan): Transferencia a producto competencia (Raisin, ING, BBVA) con TAE 9-12%',
                    'Paso 4 (mes 1): Paga mínimo + €100/mes extra = eliminar en 3.5 años sin nuevos gastos'
                ],
                'plazo': '30 días decisión transferencia; pago completo 42 meses'
            },
            {
                'nucleos': 'Visibilidad y Control de Gasto Discrecional',
                'acciones': [
                    'Descarga estado de cuenta últimos 6 meses (todos los movimientos)',
                    'Crea hoja categorías: VIVIENDA | COMIDA | TRANSPORTE | SUSCRIPCIONES | ENTRETENIMIENTO | OTRO',
                    'Identifica "fugas": streaming (€45/mes), gimnasio sin usar (€40/mes), apps pagadas (€25/mes) = €110',
                    'Cancela hoy mismo suscripciones innecesarias; reasigna €110 a emergencia'
                ],
                'plazo': '1 semana para auditoría; cancelaciones inmediatas'
            }
        ],

        # Metadata adicional (simular 100 preguntas completadas)
        'questionnaire_metadata': {
            'total_questions': 100,
            'fase_1_completed': 5,      # Fase rápida: 5 preguntas (demográficas)
            'fase_2_completed': 26,     # Fase adaptativa: 26 preguntas
            'fase_3_completed': 69,     # Fase específica: 69 preguntas
            'completion_time_minutes': 18,
            'completion_percentage': 100,
            'question_categories_covered': [
                'Ingresos y Gastos (15 preguntas)',
                'Ahorros y Emergencias (12 preguntas)',
                'Deuda y Crédito (14 preguntas)',
                'Inversiones (11 preguntas)',
                'Seguros y Protección (9 preguntas)',
                'Comportamiento Financiero (18 preguntas)',
                'Sesgo Cognitivo y Decisiones (21 preguntas)'
            ]
        }
    }

    # Crear generador y producir PDF
    output_path = 'DIAGNOSTICO_FINANCIERO_EJEMPLO.pdf'
    generator = DiagnosticReportGenerator(output_path)

    print(f"Generando PDF de ejemplo...")
    print(f"  • Score general: {diagnostic_result['overall_score']}/100")
    print(f"  • Preguntas completadas: {diagnostic_result['questionnaire_metadata']['total_questions']}")
    print(f"  • Tiempo completación: {diagnostic_result['questionnaire_metadata']['completion_time_minutes']} minutos")
    print(f"  • Arquetipo: {diagnostic_result['archetype']}")

    # Generar PDF
    pdf_file = generator.generate_report(diagnostic_result)

    print(f"\n✓ PDF generado exitosamente: {pdf_file}")
    print(f"\nEstructura del reporte:")
    print(f"  1. Portada con score general y branding")
    print(f"  2. Resumen ejecutivo + patrón de dinero")
    print(f"  3. Gráfico de 5 áreas de salud (Clarity, Resilience, Control, Knowledge, Agency)")
    print(f"  4. Semáforo de alertas ({len(diagnostic_result['alerts'])} problemas identificados)")
    print(f"  5. Plan de acción N.A.P. (3 pasos priorizados)")
    print(f"  6. Metodología (Kahneman/Thaler + Behavioral Economics)")

    return pdf_file

if __name__ == '__main__':
    generate_example_report()
