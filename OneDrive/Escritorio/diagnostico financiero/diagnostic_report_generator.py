"""
DIAGNOSTIC REPORT GENERATOR v3.0-PREMIUM — FRICTION-BASED DIAGNOSTIC
Generación de reportes premium con: Score de Salud Financiera, Arquetipo Dinámico,
Semáforo de Alertas, y Plan de Acción N.A.P. (Núcleo/Acción/Plazo)
"""

import sys
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from io import BytesIO

from reportlab.lib.pagesizes import A4, LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib.colors import HexColor, Color
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, PageBreak,
                                 Table, TableStyle, Image, KeepTogether, Preformatted)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY

try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import matplotlib
    matplotlib.use('Agg')
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

import numpy as np


class PremiumColorScheme:
    """Paleta premium Adapta Family Office + psicología del color"""
    # Marca Adapta
    PRIMARY = HexColor("#1a1a1a")
    ACCENT = HexColor("#FFB81C")
    BACKGROUND = HexColor("#FAFAFA")
    TEXT = HexColor("#333333")

    # Semáforo de alertas (rojo>naranja>amarillo>verde)
    ROJO = HexColor("#D32F2F")      # Crítico
    NARANJA = HexColor("#F57C00")   # Alerta
    AMARILLO = HexColor("#FBC02D")  # Atención
    VERDE = HexColor("#388E3C")     # OK
    AZUL = HexColor("#1976D2")      # Excelente

    # Áreas de salud financiera (5 dimensiones)
    CLARITY = HexColor("#2196F3")       # Claridad
    RESILIENCE = HexColor("#FF9800")    # Resiliencia
    CONTROL = HexColor("#4CAF50")       # Control
    KNOWLEDGE = HexColor("#9C27B0")     # Conocimiento
    AGENCY = HexColor("#F44336")        # Agencia


class HealthArea:
    """Mapeo de dimensiones de fricción a 5 áreas de salud financiera"""
    AREAS = {
        'clarity': {
            'nombre': 'Claridad Financiera',
            'color': PremiumColorScheme.CLARITY,
            'descripcion': 'Visibilidad sobre ingresos, gastos y deuda',
            'dimensiones': ['claridad_financiera', 'flujo_caja']
        },
        'resilience': {
            'nombre': 'Resiliencia',
            'color': PremiumColorScheme.RESILIENCE,
            'descripcion': 'Capacidad para resistir golpes financieros',
            'dimensiones': ['resiliencia_financiera', 'vulnerabilidad_laboral']
        },
        'control': {
            'nombre': 'Control de Gastos',
            'color': PremiumColorScheme.CONTROL,
            'descripcion': 'Dominio sobre tus decisiones de gasto',
            'dimensiones': ['control_impulsos', 'desperdicio_capital']
        },
        'knowledge': {
            'nombre': 'Conocimiento',
            'color': PremiumColorScheme.KNOWLEDGE,
            'descripcion': 'Comprensión de tasas, costos y opciones',
            'dimensiones': ['conocimiento_deuda']
        },
        'agency': {
            'nombre': 'Agencia/Poder',
            'color': PremiumColorScheme.AGENCY,
            'descripcion': 'Creencia en tu capacidad de cambiar',
            'dimensiones': []
        }
    }


class Archetype:
    """Arquetipos psicológicos de dinero basados en Kahneman/Thaler"""
    ARCHETYPES = {
        'gastador_impulsivo': {
            'nombre': 'El Gastador Impulsivo',
            'description': 'Responde a impulsos emocionales, descuentos y FOMO',
            'traits': ['No puede pasar un descuento', 'Gasta sin presupuesto', 'Arrepentimiento posterior'],
            'bias': 'Present bias + Loss aversion activation',
            'recomendacion': 'Implementa fricción de compra (24h de espera, restricción tarjeta)'
        },
        'vividor_presente': {
            'nombre': 'El Vividor del Presente',
            'description': 'Optimista excesivo, no ahorra para el futuro',
            'traits': ['Vive para hoy', 'Asume que "algo saldrá"', 'No tiene fondo de emergencia'],
            'bias': 'Hyperbolic discounting + Optimism bias',
            'recomendacion': 'Visibiliza el costo real: inflación, oportunidades perdidas'
        },
        'negador_deuda': {
            'nombre': 'El Negador de Deuda',
            'description': 'Sabe que tiene problemas pero no los confronta',
            'traits': ['Ignora estados de cuenta', 'No negocia tasas', 'Desconoce su TAE real'],
            'bias': 'Ostrich effect + Sunk cost fallacy',
            'recomendacion': 'Confrontación crudeza: esto es lo que cuesta hoy, esto mañana'
        },
        'negociador_astuto': {
            'nombre': 'El Negociador Astuto',
            'description': 'Busca activamente optimizaciones, valora la educación',
            'traits': ['Revisa periódicamente', 'Negocia tasas', 'Lee detalles contractuales'],
            'bias': 'Minimal bias, buen numeracy',
            'recomendacion': 'Ofrécele herramientas avanzadas: optimización fiscal, seguro'
        },
        'paralizado_decision': {
            'nombre': 'El Paralizado de Decisión',
            'description': 'Abrumado por opciones, no toma decisiones',
            'traits': ['Posterga acciones', 'Duda constantemente', 'Busca aprobación externa'],
            'bias': 'Decision paralysis + Need for approval',
            'recomendacion': 'Proporciona 3 opciones claras, costo de no hacer nada'
        }
    }


class DiagnosticReportGenerator:
    """Constructor de reportes PDF premium para diagnóstico friction-based"""

    COLORS = PremiumColorScheme()

    def __init__(self, output_path: str):
        """Inicializar generador de PDF"""
        self.output_path = output_path
        self.doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )
        self.story = []
        self.styles = self._setup_styles()

    def _setup_styles(self):
        """Configurar estilos personalizados premium"""
        styles = getSampleStyleSheet()

        # Título premium
        styles.add(ParagraphStyle(
            name='TitlePremium',
            parent=styles['Heading1'],
            fontSize=28,
            textColor=self.COLORS.PRIMARY,
            spaceAfter=6,
            fontName='Helvetica-Bold',
            alignment=TA_CENTER
        ))

        # Subtítulo de sección
        styles.add(ParagraphStyle(
            name='SectionHead',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=self.COLORS.ACCENT,
            spaceAfter=12,
            fontName='Helvetica-Bold',
            borderColor=self.COLORS.ACCENT,
            borderWidth=2,
            borderPadding=6
        ))

        # Subtítulo secundario
        styles.add(ParagraphStyle(
            name='Subtitle',
            parent=styles['Normal'],
            fontSize=11,
            textColor=self.COLORS.TEXT,
            spaceAfter=8,
            fontName='Helvetica-Oblique'
        ))

        # Número grande (para scores)
        styles.add(ParagraphStyle(
            name='BigNumber',
            parent=styles['Normal'],
            fontSize=48,
            textColor=self.COLORS.ACCENT,
            fontName='Helvetica-Bold',
            alignment=TA_CENTER
        ))

        return styles

    def _score_to_semaphore(self, score: float) -> Tuple[str, str]:
        """Convertir score (0-100) a color y etiqueta del semáforo"""
        if score >= 80:
            return ('✓ EXCELENTE', self.COLORS.AZUL)
        elif score >= 60:
            return ('✓ BUENO', self.COLORS.VERDE)
        elif score >= 40:
            return ('⚠ ATENCIÓN', self.COLORS.AMARILLO)
        elif score >= 20:
            return ('⚠ ALERTA', self.COLORS.NARANJA)
        else:
            return ('✗ CRÍTICO', self.COLORS.ROJO)

    def _generate_health_score_chart(self, health_scores: Dict[str, float]) -> BytesIO:
        """Generar gráfico de barras horizontal para 5 áreas de salud"""
        if not MATPLOTLIB_AVAILABLE:
            return None

        fig, ax = plt.subplots(figsize=(8, 4))
        fig.patch.set_facecolor('white')

        areas = []
        scores = []
        colors = []

        for area_key in ['clarity', 'resilience', 'control', 'knowledge', 'agency']:
            area_info = HealthArea.AREAS[area_key]
            areas.append(area_info['nombre'])
            scores.append(health_scores.get(area_key, 0))
            colors.append(area_info['color'])

        # Gráfico de barras horizontales
        y_pos = np.arange(len(areas))
        # Convertir HexColor a tuplas RGB para matplotlib (0-1 scale)
        color_rgb = []
        for c in colors:
            if hasattr(c, 'rgb') and callable(c.rgb):
                color_rgb.append(c.rgb())
            else:
                color_rgb.append((0.5, 0.5, 0.5))
        ax.barh(y_pos, scores, color=color_rgb, alpha=0.8, edgecolor='black', linewidth=1.5)

        # Configurar ejes
        ax.set_yticks(y_pos)
        ax.set_yticklabels(areas, fontsize=10, fontweight='bold')
        ax.set_xlabel('Score (0-100)', fontsize=10, fontweight='bold')
        ax.set_xlim(0, 100)
        ax.set_title('Tu Score de Salud Financiera', fontsize=14, fontweight='bold', pad=20)
        ax.grid(axis='x', alpha=0.3, linestyle='--')

        # Añadir etiquetas de valor
        for i, (area, score) in enumerate(zip(areas, scores)):
            ax.text(score + 2, i, f'{score:.0f}', va='center', fontweight='bold')

        # Guardar a BytesIO
        img_buffer = BytesIO()
        plt.savefig(img_buffer, format='png', dpi=100, bbox_inches='tight', facecolor='white')
        img_buffer.seek(0)
        plt.close(fig)

        return img_buffer

    def _generate_archetype_profile(self, archetype_key: str) -> str:
        """Generar descripción de arquetipo"""
        archetype = Archetype.ARCHETYPES.get(archetype_key, Archetype.ARCHETYPES['paralizado_decision'])
        return (
            f"<b>{archetype['nombre']}</b><br/>"
            f"<i>{archetype['description']}</i><br/><br/>"
            f"<b>Rasgos:</b> {', '.join(archetype['traits'])}<br/>"
            f"<b>Sesgo Cognitivo:</b> {archetype['bias']}<br/>"
            f"<b>Recomendación:</b> {archetype['recomendacion']}"
        )

    def add_cover_page(self, user_id: str, overall_score: float, timestamp: str):
        """Crear portada premium"""
        self.story.append(Spacer(1, 1*inch))

        # Logo/Brand
        brand = Paragraph(
            "<font size=14>ADAPTA FAMILY OFFICE</font>",
            self.styles['Normal']
        )
        self.story.append(brand)
        self.story.append(Spacer(1, 0.3*inch))

        # Título principal
        title = Paragraph(
            "<b>Diagnóstico Financiero Personal Premium</b>",
            self.styles['TitlePremium']
        )
        self.story.append(title)
        self.story.append(Spacer(1, 0.3*inch))

        # Score general prominente
        score_section = [
            [Paragraph(
                f"<font size=11><b>Tu Puntuación General</b></font>",
                self.styles['Normal']
            )],
            [Paragraph(f"{overall_score:.0f}", self.styles['BigNumber'])]
        ]
        score_table = Table(score_section, colWidths=[6*inch])
        score_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ]))
        self.story.append(score_table)
        self.story.append(Spacer(1, 0.5*inch))

        # Metadata
        metadata = Paragraph(
            f"<font size=9 color='#666666'>"
            f"Generado: {datetime.now().strftime('%d de %B de %Y')}<br/>"
            f"Usuario: {user_id}<br/>"
            f"Metodología: Kahneman & Thaler (Behavioral Economics)</font>",
            self.styles['Normal']
        )
        self.story.append(metadata)

        self.story.append(PageBreak())

    def add_executive_summary(self, overall_score: float, archetype_key: str):
        """Resumen ejecutivo de 1 página"""
        self.story.append(Paragraph("<b>Resumen Ejecutivo</b>", self.styles['SectionHead']))
        self.story.append(Spacer(1, 0.2*inch))

        # Interpretación de score
        if overall_score >= 80:
            interpretation = (
                "Tu salud financiera es sólida. Tienes fundamentals consolidados y "
                "gestionas bien la mayoría de áreas. Enfócate en optimización y preservación de patrimonio."
            )
        elif overall_score >= 60:
            interpretation = (
                "Tienes baseline saludable con margen claro de mejora. Aborda sistémáticamente "
                "las vulnerabilidades identificadas en este diagnóstico."
            )
        elif overall_score >= 40:
            interpretation = (
                "Tu resiliencia financiera es moderada. Múltiples áreas requieren atención urgente. "
                "Sigue las recomendaciones priorizadas para fortalecer tu posición."
            )
        else:
            interpretation = (
                "INTERVENCIÓN URGENTE. Tienes vulnerabilidades significativas que ponen en riesgo "
                "tu estabilidad financiera. Implementa las acciones críticas AHORA."
            )

        summary_para = Paragraph(
            f"<b>Estado Actual:</b> {interpretation}",
            self.styles['Normal']
        )
        self.story.append(summary_para)
        self.story.append(Spacer(1, 0.3*inch))

        # Tu arquetipo
        self.story.append(Paragraph("<b>Tu Patrón de Dinero</b>", self.styles['Subtitle']))
        archetype_text = self._generate_archetype_profile(archetype_key)
        self.story.append(Paragraph(archetype_text, self.styles['Normal']))

        self.story.append(PageBreak())

    def add_health_scores_section(self, health_scores: Dict[str, float]):
        """Sección de 5 áreas de salud financiera"""
        self.story.append(Paragraph("<b>Tu Score de Salud Financiera</b>", self.styles['SectionHead']))
        self.story.append(Spacer(1, 0.15*inch))

        self.story.append(Paragraph(
            "Hemos evaluado tu situación en 5 áreas clave. Cada una mide un aspecto diferente de tu salud financiera:",
            self.styles['Normal']
        ))
        self.story.append(Spacer(1, 0.2*inch))

        # Generar gráfico
        if MATPLOTLIB_AVAILABLE:
            img_buffer = self._generate_health_score_chart(health_scores)
            if img_buffer:
                img = Image(img_buffer, width=6*inch, height=3*inch)
                self.story.append(img)
                self.story.append(Spacer(1, 0.2*inch))

        # Detalles por área
        for area_key in ['clarity', 'resilience', 'control', 'knowledge', 'agency']:
            area_info = HealthArea.AREAS[area_key]
            score = health_scores.get(area_key, 0)
            semaphore_label, semaphore_color = self._score_to_semaphore(score)

            area_text = (
                f"<b>{area_info['nombre']}</b> {semaphore_label}<br/>"
                f"{area_info['descripcion']}<br/>"
                f"<font size=10 color='#999999'><i>{area_info['descripcion']}</i></font>"
            )
            self.story.append(Paragraph(area_text, self.styles['Normal']))
            self.story.append(Spacer(1, 0.12*inch))

        self.story.append(PageBreak())

    def add_semaphore_section(self, alerts: List[Dict]):
        """Semáforo de alertas - identificación visual de problemas críticos"""
        self.story.append(Paragraph("<b>Semáforo de Alertas</b>", self.styles['SectionHead']))
        self.story.append(Spacer(1, 0.15*inch))

        self.story.append(Paragraph(
            "Estos son los problemas financieros más críticos detectados. Requieren tu atención inmediata:",
            self.styles['Normal']
        ))
        self.story.append(Spacer(1, 0.2*inch))

        if not alerts:
            ok_para = Paragraph(
                "<font color='#388E3C'><b>✓ BIEN</b> No se detectaron alertas críticas.</font>",
                self.styles['Normal']
            )
            self.story.append(ok_para)
        else:
            for alert in alerts:
                severity = alert.get('severity', 'atención').lower()
                color_map = {
                    'crítico': self.COLORS.ROJO,
                    'alerta': self.COLORS.NARANJA,
                    'atención': self.COLORS.AMARILLO,
                    'ok': self.COLORS.VERDE
                }
                color = color_map.get(severity, self.COLORS.AMARILLO)

                alert_header = Paragraph(
                    f"<font color='{color}'><b>{alert.get('title', 'Alerta')}</b></font>",
                    self.styles['Normal']
                )
                self.story.append(alert_header)

                alert_body = Paragraph(
                    f"{alert.get('description', 'Sin descripción')}",
                    self.styles['Normal']
                )
                self.story.append(alert_body)
                self.story.append(Spacer(1, 0.15*inch))

        self.story.append(PageBreak())

    def add_nap_action_plan(self, nap_actions: List[Dict]):
        """Plan de acción N.A.P. (Núcleo/Acción/Plazo)"""
        self.story.append(Paragraph("<b>Próximos 3 Pasos</b>", self.styles['SectionHead']))
        self.story.append(Spacer(1, 0.15*inch))

        self.story.append(Paragraph(
            "Tu plan de acción personalizado. Cada paso tiene un objetivo claro, "
            "un conjunto de acciones concretas, y un plazo realista.",
            self.styles['Normal']
        ))
        self.story.append(Spacer(1, 0.2*inch))

        for idx, action in enumerate(nap_actions[:3], 1):
            # Paso N
            step_header = Paragraph(
                f"<b>PASO {idx}: {action.get('nucleos', 'Objetivo')}</b>",
                self.styles['Subtitle']
            )
            self.story.append(step_header)

            # Núcleo (problema)
            if action.get('nucleos'):
                self.story.append(Paragraph(
                    f"<b>El Problema:</b> {action['nucleos']}",
                    self.styles['Normal']
                ))

            # Acciones (qué hacer)
            if action.get('acciones'):
                actions_text = '<b>Qué Hacer:</b><br/>'
                for act in action['acciones']:
                    actions_text += f"• {act}<br/>"
                self.story.append(Paragraph(actions_text, self.styles['Normal']))

            # Plazo (cuándo)
            if action.get('plazo'):
                self.story.append(Paragraph(
                    f"<b>Plazo:</b> {action['plazo']}",
                    self.styles['Normal']
                ))

            self.story.append(Spacer(1, 0.2*inch))

        self.story.append(PageBreak())

    def add_methodology(self):
        """Sección de metodología - Kahneman/Thaler"""
        self.story.append(Paragraph("<b>Metodología</b>", self.styles['SectionHead']))
        self.story.append(Spacer(1, 0.15*inch))

        methodology_text = (
            "<b>Fundamento: Economía del Comportamiento (Behavioral Economics)</b><br/>"
            "Este diagnóstico utiliza principios de Daniel Kahneman y Richard Thaler "
            "para identificar sesgos cognitivos y patrones de decisión que afectan tu vida financiera.<br/><br/>"

            "<b>Enfoque Friction-Based:</b><br/>"
            "En lugar de preguntas abstractas, usamos escenarios reales que crean 'fricción'—"
            "momento de verdad donde confrontas cómo realmente manejas el dinero versus cómo crees que lo manejas.<br/><br/>"

            "<b>5 Dimensiones de Salud Financiera:</b><br/>"
            "• <b>Claridad:</b> ¿Ves exactamente dónde va tu dinero?<br/>"
            "• <b>Resiliencia:</b> ¿Puedes sobrevivir un golpe financiero?<br/>"
            "• <b>Control:</b> ¿Dominas tus decisiones de gasto o ellas te dominan?<br/>"
            "• <b>Conocimiento:</b> ¿Entiendes tasas, costos, opciones?<br/>"
            "• <b>Agencia:</b> ¿Crees que puedes cambiar tu situación?<br/><br/>"

            "<b>Tu Patrón de Dinero (Archetype):</b><br/>"
            "Identificamos el arquetipo psicológico que mejor describe tu relación con el dinero—"
            "desde el Gastador Impulsivo hasta el Negociador Astuto. Esto es crítico porque "
            "el cambio financiero es 10% números y 90% psicología."
        )

        self.story.append(Paragraph(methodology_text, self.styles['Normal']))
        self.story.append(Spacer(1, 0.3*inch))

        # Footer
        footer = Paragraph(
            "<font size=8 color='#999999'>"
            "ADAPTA FAMILY OFFICE | Especialistas en diagnóstico financiero integral<br/>"
            "javier@mendezconsultoria.com | www.adaptafamilyoffice.es"
            "</font>",
            self.styles['Normal']
        )
        self.story.append(footer)

    def generate_report(self, diagnostic_result: Dict) -> str:
        """
        Generar reporte PDF completo desde resultado de diagnóstico

        diagnostic_result debe contener:
        - overall_score: float 0-100
        - user_id: str
        - health_scores: Dict[str, float]
        - archetype: str
        - alerts: List[Dict]
        - nap_actions: List[Dict]
        """

        overall_score = diagnostic_result.get('overall_score', 50)
        user_id = diagnostic_result.get('user_id', 'Anónimo')
        health_scores = diagnostic_result.get('health_scores', {
            'clarity': 50, 'resilience': 50, 'control': 50, 'knowledge': 50, 'agency': 50
        })
        archetype = diagnostic_result.get('archetype', 'paralizado_decision')
        alerts = diagnostic_result.get('alerts', [])
        nap_actions = diagnostic_result.get('nap_actions', [])

        # Construir documento
        self.add_cover_page(user_id, overall_score, datetime.now().isoformat())
        self.add_executive_summary(overall_score, archetype)
        self.add_health_scores_section(health_scores)
        self.add_semaphore_section(alerts)
        self.add_nap_action_plan(nap_actions)
        self.add_methodology()

        # Generar PDF
        self.doc.build(self.story)
        return self.output_path


# ============================================================================
# TESTING
# ============================================================================

if __name__ == '__main__':
    # Test con datos de muestra
    test_result = {
        'overall_score': 65,
        'user_id': 'test_user_001',
        'health_scores': {
            'clarity': 55,
            'resilience': 45,
            'control': 70,
            'knowledge': 60,
            'agency': 75
        },
        'archetype': 'vividor_presente',
        'alerts': [
            {
                'severity': 'crítico',
                'title': 'Fondo de Emergencia Insuficiente',
                'description': 'Solo tienes 1 mes de gastos ahorrado. Necesitas 6.'
            },
            {
                'severity': 'alerta',
                'title': 'Deuda de Tarjeta de Crédito',
                'description': 'Estás pagando 22% de TAE en revolving.'
            }
        ],
        'nap_actions': [
            {
                'nucleos': 'Crear fondo de emergencia',
                'acciones': [
                    'Abre cuenta separada "emergencias"',
                    'Transfiere €200/mes automáticamente',
                    'Objetivo: 6 meses de gastos en 3 años'
                ],
                'plazo': '90 días para primeros €1000'
            },
            {
                'nucleos': 'Reducir TAE en revolving',
                'acciones': [
                    'Llama al banco (números exactos a mano)',
                    'Solicita reducción a 15-18%',
                    'Si no, transferencia a producto más barato'
                ],
                'plazo': '30 días'
            },
            {
                'nucleos': 'Visibilidad de gastos',
                'acciones': [
                    'Descarga 3 últimos meses de estado de cuenta',
                    'Categoriza: vivienda, comida, transporte, suscripciones, otro',
                    'Identifica 2-3 "fugas" para eliminar'
                ],
                'plazo': '1 semana'
            }
        ]
    }

    ou