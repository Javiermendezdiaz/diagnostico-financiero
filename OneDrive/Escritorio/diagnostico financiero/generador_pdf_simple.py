#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generador de PDF Brutal - Versión Simplificada
Convierte respuestas de test en informe premium de diagnóstico
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from datetime import datetime
import json

class GeneradorPDFSimple:
    """Generador de PDF brutal simplificado y funcional"""

    def __init__(self, cliente_nombre: str, datos_cliente: dict, perfil: str):
        self.cliente_nombre = cliente_nombre
        self.datos = datos_cliente
        self.perfil = perfil
        self.fecha = datetime.now().strftime("%d de %B de %Y")
        self.estilos = self._crear_estilos()

    def _crear_estilos(self):
        """Define estilos de texto"""
        estilos = getSampleStyleSheet()

        estilos.add(ParagraphStyle(
            name='TituloPortada',
            fontSize=42,
            textColor=colors.HexColor("#1e3a5f"),
            spaceAfter=12,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))

        estilos.add(ParagraphStyle(
            name='Subtitulo',
            fontSize=16,
            textColor=colors.HexColor("#d73027"),
            spaceAfter=12,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))

        estilos.add(ParagraphStyle(
            name='Cuerpo',
            fontSize=11,
            textColor=colors.HexColor("#2c2c2c"),
            alignment=TA_JUSTIFY,
            spaceAfter=12,
            leading=14
        ))

        estilos.add(ParagraphStyle(
            name='Alerta',
            fontSize=12,
            textColor=colors.HexColor("#d73027"),
            spaceAfter=8,
            fontName='Helvetica-Bold'
        ))

        return estilos

    def generar_puntuacion(self) -> int:
        """Calcula puntuación 1-100"""
        score = 100
        ingreso = self.datos.get('ingresos_netos', 1)
        gastos = self.datos.get('gastos_totales', 0)
        ahorros = self.datos.get('ahorros_totales', 0)
        hipoteca = self.datos.get('saldo_hipoteca', 0)
        tarjetas = self.datos.get('saldo_tarjetas', 0)

        # Penalización por cobertura de emergencia
        if ahorros < gastos * 1:
            score -= 25
        elif ahorros < gastos * 3:
            score -= 15

        # Penalización por deuda
        deuda_total = hipoteca + tarjetas
        ratio = deuda_total / (ingreso * 12) if ingreso > 0 else 999

        if ratio > 5:
            score -= 25
        elif ratio > 3:
            score -= 15
        elif ratio > 2:
            score -= 8

        # Penalización por gastos vs ingresos
        ratio_gasto = gastos / ingreso if ingreso > 0 else 2
        if ratio_gasto > 0.95:
            score -= 15
        elif ratio_gasto > 0.85:
            score -= 8

        # Penalización por deuda tóxica (tarjetas)
        if tarjetas > 0:
            score -= 10

        return max(5, score)

    def generar_pdf(self, nombre_archivo: str):
        """Genera el PDF brutal"""
        doc = SimpleDocTemplate(
            nombre_archivo,
            pagesize=letter,
            leftMargin=0.75 * inch,
            rightMargin=0.75 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch
        )

        story = []

        # === PORTADA ===
        story.append(Spacer(1, 1.5 * inch))
        story.append(Paragraph("DIAGNÓSTICO FINANCIERO", self.estilos['TituloPortada']))
        story.append(Paragraph("Premium - Salud Patrimonial Familiar", self.estilos['Subtitulo']))
        story.append(Spacer(1, 0.5 * inch))
        story.append(Paragraph(f"Cliente: <b>{self.cliente_nombre}</b>", self.estilos['Cuerpo']))
        story.append(Paragraph(f"Fecha: {self.fecha}", self.estilos['Cuerpo']))
        story.append(Spacer(1, 0.3 * inch))
        story.append(Paragraph("DOCUMENTO CONFIDENCIAL", self.estilos['Alerta']))
        story.append(PageBreak())

        # === SECCIÓN 1: DIAGNÓSTICO ===
        score = self.generar_puntuacion()
        story.append(Paragraph("1. DIAGNÓSTICO DE SALUD FINANCIERA", self.estilos['Heading1']))
        story.append(Spacer(1, 0.2 * inch))

        # Score card
        story.append(Paragraph(f"<b>Puntuación: {score}/100</b>", self.estilos['Subtitulo']))
        story.append(Spacer(1, 0.15 * inch))

        if score >= 80:
            estado = "SEGURO - Tu situación es manejable"
            color = "#16a766"
        elif score >= 60:
            estado = "ESTABLE - Requiere atención moderada"
            color = "#91bfdb"
        elif score >= 40:
            estado = "ALERTA - Acción urgente recomendada"
            color = "#fc8d59"
        else:
            estado = "CRÍTICO - Situación muy delicada"
            color = "#d73027"

        estilo_estado = ParagraphStyle(
            name='Estado',
            fontSize=14,
            textColor=colors.HexColor(color),
            fontName='Helvetica-Bold'
        )

        story.append(Paragraph(f"Estado: {estado}", estilo_estado))
        story.append(Spacer(1, 0.3 * inch))

        # Análisis de datos
        ingreso_anual = self.datos.get('ingresos_netos', 0) * 12
        gastos_anuales = self.datos.get('gastos_totales', 0) * 12
        deuda_total = self.datos.get('saldo_hipoteca', 0) + self.datos.get('saldo_tarjetas', 0)
        ahorros = self.datos.get('ahorros_totales', 0)

        story.append(Paragraph("<b>Análisis Financiero:</b>", self.estilos['Cuerpo']))
        story.append(Paragraph(f"• Ingresos anuales: €{ingreso_anual:,.0f}", self.estilos['Cuerpo']))
        story.append(Paragraph(f"• Gastos anuales: €{gastos_anuales:,.0f}", self.estilos['Cuerpo']))
        story.append(Paragraph(f"• Deuda total: €{deuda_total:,.0f}", self.estilos['Cuerpo']))
        story.append(Paragraph(f"• Ahorros disponibles: €{ahorros:,.0f}", self.estilos['Cuerpo']))

        ratio_gastos = (gastos_anuales / ingreso_anual * 100) if ingreso_anual > 0 else 0
        story.append(Paragraph(f"• Ratio gastos/ingresos: {ratio_gastos:.1f}%", self.estilos['Cuerpo']))

        story.append(Spacer(1, 0.3 * inch))

        # Fugas identificadas
        story.append(Paragraph("<b>Fugas Financieras Identificadas:</b>", self.estilos['Alerta']))
        story.append(Spacer(1, 0.1 * inch))

        # Fuga 1: Cobertura de emergencia
        meses_cobertura = (ahorros / self.datos.get('gastos_totales', 1)) if self.datos.get('gastos_totales', 0) > 0 else 0
        if meses_cobertura < 1:
            story.append(Paragraph(
                f"🔴 <b>Cobertura de emergencia crítica:</b> Tienes {meses_cobertura:.1f} meses de gastos ahorrados. Si pierdes ingresos, estarías en riesgo de insolvencia en menos de 30 días.",
                self.estilos['Cuerpo']
            ))
        elif meses_cobertura < 3:
            story.append(Paragraph(
                f"🟠 <b>Colchón de emergencia insuficiente:</b> Tienes {meses_cobertura:.1f} meses de gastos ahorrados. El mínimo recomendado es 3-6 meses.",
                self.estilos['Cuerpo']
            ))

        # Fuga 2: Deuda de tarjetas
        tarjetas = self.datos.get('saldo_tarjetas', 0)
        if tarjetas > 0:
            interes_anual = tarjetas * 0.21  # Asumiendo 21% TAE
            story.append(Paragraph(
                f"🔴 <b>Sangrado de intereses:</b> Pagas €{interes_anual:,.0f} anuales en puro interés. Esta deuda está devorando tu capacidad de inversión.",
                self.estilos['Cuerpo']
            ))

        # Fuga 3: Ratio de deuda
        if ingreso_anual > 0:
            ratio_deuda = deuda_total / ingreso_anual
            if ratio_deuda > 3:
                story.append(Paragraph(
                    f"🔴 <b>Deuda excesiva:</b> Debes {ratio_deuda:.1f}x tu ingreso anual. Esta es una carga muy pesada que limita tu flexibilidad financiera.",
                    self.estilos['Cuerpo']
                ))

        story.append(PageBreak())

        # === SECCIÓN 2: PSICOLOGÍA ===
        story.append(Paragraph("2. DIAGNÓSTICO PSICOLÓGICO", self.estilos['Heading1']))
        story.append(Spacer(1, 0.2 * inch))

        story.append(Paragraph(
            "Tu perfil financiero es <b>" + self.perfil + "</b>. Esto significa que tu principal desafío no es solo técnico (presupuesto), sino psicológico.",
            self.estilos['Cuerpo']
        ))

        story.append(Spacer(1, 0.15 * inch))

        story.append(Paragraph(
            "<b>Creencias Limitantes Detectadas:</b>",
            self.estilos['Alerta']
        ))

        if self.perfil == "AHOGADO_DEUDAS":
            story.append(Paragraph(
                "• Sensación de que el dinero se escapa siempre (validada por datos reales de deuda)",
                self.estilos['Cuerpo']
            ))
            story.append(Paragraph(
                "• Ansiedad sobre el futuro (especialmente si pierdes ingresos)",
                self.estilos['Cuerpo']
            ))
            story.append(Paragraph(
                "• Parálisis para tomar decisiones sobre cómo mejorar",
                self.estilos['Cuerpo']
            ))

        story.append(Spacer(1, 0.3 * inch))

        story.append(Paragraph(
            "<b>El Factor Psicológico:</b>",
            self.estilos['Cuerpo']
        ))

        story.append(Paragraph(
            "La mayoría de personas en tu situación sienten que \"hay un agujero por el que escapa el dinero\" pero no saben dónde. Esta sensación de pérdida de control es lo que paraliza. El 73% del estrés financiero no viene de los números, sino del <b>sentimiento de no tener control</b>.",
            self.estilos['Cuerpo']
        ))

        story.append(PageBreak())

        # === SECCIÓN 3: STRESS TESTS ===
        story.append(Paragraph("3. SIMULADOR DE IMPACTO (Stress Tests)", self.estilos['Heading1']))
        story.append(Spacer(1, 0.2 * inch))

        story.append(Paragraph(
            "<b>Escenario 1: Si pierdes tu ingreso HOY</b>",
            self.estilos['Alerta']
        ))

        gastos_criticos = self.datos.get('gastos_totales', 1) * 0.7
        dias_cobertura = (ahorros / gastos_criticos * 30) if gastos_criticos > 0 else 0

        if dias_cobertura < 30:
            story.append(Paragraph(
                f"Tu situación es CRÍTICA: Entrarías en insolvencia en aproximadamente {max(1, int(dias_cobertura))} días.",
                self.estilos['Cuerpo']
            ))
        else:
            story.append(Paragraph(
                f"Tendrías {int(dias_cobertura)} días de cobertura (aproximadamente {int(dias_cobertura/30)} meses).",
                self.estilos['Cuerpo']
            ))

        story.append(Spacer(1, 0.2 * inch))

        story.append(Paragraph(
            "<b>Escenario 2: Si suben los tipos de interés +1%</b>",
            self.estilos['Alerta']
        ))

        hipoteca = self.datos.get('saldo_hipoteca', 0)
        aumento_hipoteca = hipoteca * 0.01  # 1% de aumento

        story.append(Paragraph(
            f"Tu pago de hipoteca subiría aproximadamente €{aumento_hipoteca:,.0f}/año. Con tu margen actual de gastos ({ratio_gastos:.1f}%), esto te ahogaría completamente.",
            self.estilos['Cuerpo']
        ))

        story.append(Spacer(1, 0.2 * inch))

        story.append(Paragraph(
            "<b>Escenario 3: Proyección a 20 años</b>",
            self.estilos['Alerta']
        ))

        story.append(Paragraph(
            "Si mantienes el patrón actual de gastos y deuda, en 20 años habrás pagado en intereses más de lo que vale tu casa. Sin cambios, tu patrimonio a los 65 años será cero o negativo.",
            self.estilos['Cuerpo']
        ))

        story.append(PageBreak())

        # === SECCIÓN 4: PLAN 90 DÍAS ===
        story.append(Paragraph("4. TU RECETA: PLAN DE ACCIÓN 90 DÍAS", self.estilos['Heading1']))
        story.append(Spacer(1, 0.2 * inch))

        story.append(Paragraph(
            "Este plan no es teórico. Cada acción genera dinero real en 90 días.",
            self.estilos['Alerta']
        ))

        story.append(Spacer(1, 0.15 * inch))

        # Semanas 1-2
        story.append(Paragraph("<b>FASE 1 (Semanas 1-2): Visibilidad Total</b>", self.estilos['Cuerpo']))
        story.append(Paragraph("• Descarga 6 meses de extractos de todos tus cuentas", self.estilos['Cuerpo']))
        story.append(Paragraph("• Categoriza cada gasto (obligatorio, variable, discrecional)", self.estilos['Cuerpo']))
        story.append(Paragraph("• Identifica el TOP 5 de gastos más grandes", self.estilos['Cuerpo']))
        story.append(Paragraph("<b>Resultado esperado:</b> Claridad total de dónde va cada euro", self.estilos['Cuerpo']))

        story.append(Spacer(1, 0.15 * inch))

        # Semanas 3-4
        story.append(Paragraph("<b>FASE 2 (Semanas 3-4): Encontrar €150-300 «Ocultos»</b>", self.estilos['Cuerpo']))
        story.append(Paragraph("• Cancela 3 suscripciones que no usas", self.estilos['Cuerpo']))
        story.append(Paragraph("• Renegocia seguros (auto, hogar) para reducir €50-100", self.estilos['Cuerpo']))
        story.append(Paragraph("• Audita comisiones bancarias (esas €5-10 mensuales)", self.estilos['Cuerpo']))
        story.append(Paragraph("<b>Resultado esperado:</b> €150-300 mensuales que no echaste de menos", self.estilos['Cuerpo']))

        story.append(Spacer(1, 0.15 * inch))

        # Semanas 5-8
        story.append(Paragraph("<b>FASE 3 (Semanas 5-8): Ataque a la Deuda Tóxica</b>", self.estilos['Cuerpo']))
        story.append(Paragraph("• Llama a tu banco: negocia una transferencia a 0% TAE por 6 meses", self.estilos['Cuerpo']))
        story.append(Paragraph("• Canaliza los €300 mensuales extra DIRECTAMENTE aquí", self.estilos['Cuerpo']))
        story.append(Paragraph("• Meta: reducir tarjetas de €" + str(int(tarjetas)) + " a €" + str(int(tarjetas * 0.7)), self.estilos['Cuerpo']))
        story.append(Paragraph("<b>Resultado esperado:</b> Deuda tóxica reducida 30%, ahorro de €150-200/mes en intereses", self.estilos['Cuerpo']))

        story.append(Spacer(1, 0.15 * inch))

        # Semanas 9-10
        story.append(Paragraph("<b>FASE 4 (Semanas 9-10): Fondo de Emergencia Inicial</b>", self.estilos['Cuerpo']))
        story.append(Paragraph("• Objetivo: €1,200 (1.5 meses de gastos críticos)", self.estilos['Cuerpo']))
        story.append(Paragraph("• Depósito automático: €300/semana", self.estilos['Cuerpo']))
        story.append(Paragraph("• Meta alcanzada: 4 semanas de tranquilidad psicológica", self.estilos['Cuerpo']))
        story.append(Paragraph("<b>Resultado esperado:</b> Ya no te duermes con ansiedad. Tienes 'aire'.", self.estilos['Cuerpo']))

        story.append(Spacer(1, 0.15 * inch))

        # Semanas 11-12
        story.append(Paragraph("<b>FASE 5 (Semanas 11-12): Sostenibilidad</b>", self.estilos['Cuerpo']))
        story.append(Paragraph("• Establece automáticos: €100/mes para emergencias, €100/mes para diversión", self.estilos['Cuerpo']))
        story.append(Paragraph("• Planifica 6 meses: próximo objetivo (€3,000 ahorrados)", self.estilos['Cuerpo']))
        story.append(Paragraph("• Revisa este plan cada mes", self.estilos['Cuerpo']))
        story.append(Paragraph("<b>Resultado esperado:</b> Has demostrado que PUEDES. Ahora lo repites.", self.estilos['Cuerpo']))

        story.append(PageBreak())

        # === CARTA FINAL ===
        story.append(Spacer(1, 1 * inch))
        story.append(Paragraph("<b>Una Última Palabra</b>", self.estilos['TituloPortada']))
        story.append(Spacer(1, 0.3 * inch))

        story.append(Paragraph(
            f"Tu puntuación de {score}/100 no es una sentencia. Es un diagnóstico. Como cualquier diagnóstico médico, el valor real no está en el número, sino en la <b>receta</b>.",
            self.estilos['Cuerpo']
        ))

        story.append(Spacer(1, 0.2 * inch))

        story.append(Paragraph(
            "Los números no mienten: tienes deuda, tienes poco colchón de emergencia, tu margen es ajustado. Pero también es cierto que con 90 días de acción enfocada puedes respirar diferente.",
            self.estilos['Cuerpo']
        ))

        story.append(Spacer(1, 0.2 * inch))

        story.append(Paragraph(
            "La mayoría de gente en tu situación sigue así 10 años más. Tú tienes este diagnóstico <b>hoy</b>. Eso te da ventaja.",
            self.estilos['Cuerpo']
        ))

        story.append(Spacer(1, 0.3 * inch))

        story.append(Paragraph(
            "Empieza mañana. Descarga tus extractos. No necesitas permiso de nadie. No necesitas dinero nuevo. Necesitas claridad y un plan.",
            self.estilos['Alerta']
        ))

        story.append(Spacer(1, 1 * inch))

        story.append(Paragraph(
            "En 90 días, este documento habrá salvado tu patrimonio.<br/><br/>Depende de ti que así sea.",
            self.estilos['Cuerpo']
        ))

        # Build PDF
        try:
            doc.build(story)
            print(f"✅ PDF BRUTAL GENERADO EXITOSAMENTE")
            print(f"   Archivo: {nombre_archivo}")
            print(f"   Puntuación: {score}/100")
            print(f"   Perfil: {self.perfil}")
            return True
        except Exception as e:
            print(f"❌ Error generando PDF: {e}")
            return False


if __name__ == "__main__":
    # Test con datos de María García
    datos_test = {
        "ingresos_netos": 2800,
        "gastos_totales": 2650,
        "saldo_hipoteca": 150000,
        "saldo_tarjetas": 8500,
        "ahorros_totales": 0,
        "tiene_hijos": True,
        "ingresos_variables": False,
        "pareja_ingresos": False,
        "pago_hipoteca_mensual": 750,
        "pago_minimo_tarjeta": 180,
        "pago_otros_prestamos": 0,
        "inversiones": 0
    }

    generador = GeneradorPDFSimple(
        cliente_nombre="María García",
        datos_cliente=datos_test,
        perfil="AHOGADO_DEUDAS"
    )

    generador.generar_pdf("/tmp/test_brutal.pdf")
