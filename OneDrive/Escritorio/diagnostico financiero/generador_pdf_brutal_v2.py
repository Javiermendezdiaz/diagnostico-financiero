#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generador de PDF BRUTAL - v2.0
Convierte respuestas de test adaptativo en informe premium de 30 páginas

Las 4 SECCIONES DE IMPACTO:
1. Diagnóstico del Cirujano (Qué te pasa) - Puntuación 1-100 + Fugas visuales
2. Espejo Psicológico (Por qué te pasa) - Sesgos heredados + Creencias limitantes
3. Simulador de Impacto (Qué pasará si no haces nada) - Stress test + Proyecciones
4. Receta Médica a 90 Días (Cómo lo solucionas) - Tareas hiper-específicas semanales

Copywriting Neurofinanciero: impacto emocional + datos brutales + esperanza actionable
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
from datetime import datetime, timedelta
import json

class GeneradorPDFBrutal:
    """Generador de informes brutales personalizados"""

    # Colores corporativos de impacto
    COLOR_CRITICO = "#d73027"      # Rojo fuerte
    COLOR_ALERTA = "#fc8d59"       # Naranja
    COLOR_ESTABLE = "#91bfdb"      # Azul claro
    COLOR_SEGURO = "#16a766"       # Verde
    COLOR_PRIMARY = "#1e3a5f"      # Azul corporativo
    COLOR_TEXTO = "#2c2c2c"        # Gris oscuro
    COLOR_FONDO_LIGERO = "#f5f5f5" # Gris muy claro

    def __init__(self, cliente_nombre: str, datos_cliente: dict, perfil: str):
        self.cliente_nombre = cliente_nombre
        self.datos = datos_cliente
        self.perfil = perfil
        self.fecha = datetime.now().strftime("%d de %B de %Y")
        self.estilos = self._crear_estilos()

    def _crear_estilos(self):
        """Define estilos de texto premium para neurofinanzas"""
        estilos = getSampleStyleSheet()

        # Override de estilos standard
        estilos.add(ParagraphStyle(
            name='TituloPortada',
            parent=estilos['Heading1'],
            fontSize=48,
            textColor=colors.HexColor(self.COLOR_PRIMARY),
            spaceAfter=6,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold',
            leading=56
        ))

        estilos.add(ParagraphStyle(
            name='SubtituloPortada',
            fontSize=18,
            textColor=colors.HexColor(self.COLOR_ALERTA),
            spaceAfter=12,
            alignment=TA_CENTER,
            fontName='Helvetica-Oblique'
        ))

        estilos.add(ParagraphStyle(
            name='CuerpoJustificado',
            fontSize=11,
            textColor=colors.HexColor(self.COLOR_TEXTO),
            alignment=TA_JUSTIFY,
            spaceAfter=12,
            leading=14,
            fontName='Helvetica'
        ))

        estilos.add(ParagraphStyle(
            name='Impacto',
            fontSize=14,
            textColor=colors.HexColor(self.COLOR_CRITICO),
            spaceAfter=8,
            fontName='Helvetica-Bold',
            leading=16
        ))

        return estilos

    def generar_puntuacion_1_100(self) -> int:
        """
        Calcula Salud Financiera 1-100 usando algoritmo brutal pero justo
        Basado en 5 factores:
        1. Cobertura de emergencia (25 puntos)
        2. Ratio deuda/ingresos (25 puntos)
        3. Gastos vs ingresos (20 puntos)
        4. Protección/seguros (15 puntos)
        5. Gestión deuda tóxica (15 puntos)
        """

        score = 100
        ingreso_anual = self.datos['ingresos_netos'] * 12
        gastos_anuales = self.datos['gastos_totales'] * 12

        # Factor 1: Cobertura de emergencia
        ahorros = self.datos['ahorros_totales']
        gastos_criticos = self.datos['gastos_totales'] * 0.7  # Mínimo vital
        meses_cobertura = ahorros / gastos_criticos if gastos_criticos > 0 else 0

        if meses_cobertura < 1:
            score -= 25
        elif meses_cobertura < 3:
            score -= 15
        elif meses_cobertura < 6:
            score -= 5

        # Factor 2: Ratio deuda/ingresos (25 puntos)
        deuda_total = self.datos['saldo_hipoteca'] + self.datos['saldo_tarjetas']
        ratio_deuda = (deuda_total / ingreso_anual) if ingreso_anual > 0 else 999

        if ratio_deuda > 10:
            score -= 25
        elif ratio_deuda > 5:
            score -= 20
        elif ratio_deuda > 3:
            score -= 10
        elif ratio_deuda > 2:
            score -= 5

        # Factor 3: Gastos vs Ingresos (20 puntos)
        ratio_gastos = (gastos_anuales / ingreso_anual) if ingreso_anual > 0 else 2

        if ratio_gastos > 1.1:
            score -= 20  # Gastas más de lo que ganas
        elif ratio_gastos > 0.95:
            score -= 12  # Gastas 95%+ del ingreso
        elif ratio_gastos > 0.85:
            score -= 5   # Margen muy ajustado

        # Factor 4: Protección (15 puntos)
        proteccion = self.datos.get('tiene_seguro_vida', False)
        proteccion_ingresos = self.datos.get('incapacidad_laboral', False)
        responsabilidad_civil = self.datos.get('responsabilidad_civil', False)

        seguros_activos = sum([proteccion, proteccion_ingresos, responsabilidad_civil])
        if seguros_activos == 0:
            score -= 15
        elif seguros_activos == 1:
            score -= 8
        elif seguros_activos == 2:
            score -= 3

        # Factor 5: Deuda tóxica (tarjetas > 15% TAE) (15 puntos)
        tarjeta_saldo = self.datos['saldo_tarjetas']
        tarjeta_tae = self.datos.get('tarjeta_tae', 21)

        if tarjeta_saldo > 0:
            if tarjeta_tae > 18:
                score -= 15
            elif tarjeta_tae > 15:
                score -= 10
            elif tarjeta_tae > 10:
                score -= 5

        return max(5, score)  # Mínimo: 5 puntos

    def calcular_fugas_financieras(self) -> list:
        """
        Identifica las fugas de dinero específicas que están destruyendo patrimonio
        """

        fugas = []

        # Fuga 1: Gastos variables excesivos
        gastos_variables = self.datos.get('gastos_variables', 0)
        gastos_total = self.datos['gastos_totales']
        pct_variables = (gastos_variables / gastos_total * 100) if gastos_total > 0 else 0

        if pct_variables > 30:
            destruccion_anual = gastos_variables * 12
            fugas.append({
                'titulo': 'Derrumbe de Gastos Variables',
                'descripcion': f'Tus gastos variables representan el {pct_variables:.0f}% de tu presupuesto.',
                'impacto_anual': destruccion_anual,
                'severidad': 'CRÍTICA' if pct_variables > 40 else 'ALTA'
            })

        # Fuga 2: Intereses de tarjeta de crédito
        tarjeta_saldo = self.datos['saldo_tarjetas']
        tarjeta_tae = self.datos.get('tarjeta_tae', 21)

        if tarjeta_saldo > 0:
            interes_anual = tarjeta_saldo * (tarjeta_tae / 100)
            fugas.append({
                'titulo': 'Sangrado de Intereses en Tarjeta',
                'descripcion': f'Pagas €{interes_anual:.0f} anuales en puro interés al {tarjeta_tae}% TAE.',
                'impacto_anual': interes_anual,
                'severidad': 'CRÍTICA'
            })

        # Fuga 3: Dinero fantasma (suscripciones, seguros innecesarios)
        dinero_fantasma = self.datos.get('suscripciones', 0) + self.datos.get('seguros_duplicados', 0)
        if dinero_fantasma > 0:
            fugas.append({
                'titulo': 'Dinero Fantasma (Suscripciones & Seguros)',
                'descripcion': f'Pierdes €{dinero_fantasma:.0f}/mes en servicios que no recuerdas contratar.',
                'impacto_anual': dinero_fantasma * 12,
                'severidad': 'MEDIA'
            })

        # Fuga 4: Oportunidad perdida (inflación sobre ahorros)
        ahorros = self.datos['ahorros_totales']
        inflacion = 0.03  # 3% anual

        if ahorros > 0:
            perdida_poder_adquisitivo = ahorros * inflacion
            fugas.append({
                'titulo': 'Pérdida de Poder Adquisitivo',
                'descripcion': f'Tu dinero en el banco pierde €{perdida_poder_adquisitivo:.0f}/año a causa de la inflación.',
                'impacto_anual': perdida_poder_adquisitivo,
                'severidad': 'MEDIA'
            })

        return sorted(fugas, key=lambda x: x['impacto_anual'], reverse=True)

    def generar_stress_tests(self) -> dict:
        """
        Simula escenarios catastróficos realistas que afectan la viabilidad
        """

        gastos_criticos_mes = self.datos['gastos_totales'] * 0.7  # Hipoteca + servicios + alimento
        ahorros = self.datos['ahorros_totales']

        # STRESS TEST 1: Pérdida de trabajo
        dias_hasta_colapso = (ahorros / gastos_criticos_mes) * 30 if gastos_criticos_mes > 0 else 0
        semanas_hasta_colapso = dias_hasta_colapso / 7

        stress_test_1 = {
            'nombre': 'Crisis: Pérdida de Trabajo',
            'escenario': 'Pierdes el 100% de tus ingresos mañana',
            'dias_hasta_impago_hipoteca': int(dias_hasta_colapso) if dias_hasta_colapso > 0 else 0,
            'sentencia': 'COLAPSO INMEDIATO' if dias_hasta_colapso < 30 else f'Aguantas {dias_hasta_colapso:.0f} días',
            'severidad': 'CRÍTICA'
        }

        # STRESS TEST 2: Aumento de tipos de interés
        hipoteca_saldo = self.datos['saldo_hipoteca']
        tae_actual = self.datos.get('hipoteca_tae', 3.0)
        tae_subida = tae_actual + 1.0

        cuota_actual = self._calcular_cuota_hipoteca(hipoteca_saldo, tae_actual)
        cuota_nueva = self._calcular_cuota_hipoteca(hipoteca_saldo, tae_subida)
        diferencia_mensual = cuota_nueva - cuota_actual

        stress_test_2 = {
            'nombre': 'Crisis: Aumento de Tipos al +1%',
            'escenario': 'El BCE sube tipos 1 punto (de 3% a 4%, ejemplo)',
            'diferencia_cuota_mensual': diferencia_mensual,
            'impacto_anual': diferencia_mensual * 12,
            'sentencia': f'Tu cuota hipotecaria sube €{diferencia_mensual:.0f}/mes',
            'severidad': 'ALTA'
        }

        # STRESS TEST 3: Jubilación (brecha de pensión)
        edad_jubilacion = 67
        edad_actual = self.datos.get('edad', 45)
        anos_hasta_jubilacion = max(0, edad_jubilacion - edad_actual)

        pension_estimada = self.datos['ingresos_netos'] * 0.6  # 60% de últimos salarios
        gastos_jubilacion = self.datos['gastos_totales'] * 0.7  # Menos gastos sin trabajo

        deficit_mensual = gastos_jubilacion - pension_estimada
        deficit_30anos = deficit_mensual * 12 * 30

        stress_test_3 = {
            'nombre': 'Jubilación: Brecha de Pensión',
            'escenario': f'En {anos_hasta_jubilacion} años te jubilas',
            'pension_estimada': pension_estimada,
            'gastos_jubilacion': gastos_jubilacion,
            'deficit_mensual': max(0, deficit_mensual),
            'deficit_30anos': max(0, deficit_30anos),
            'sentencia': f'Déficit de €{max(0, deficit_30anos):.0f} en 30 años de jubilación',
            'severidad': 'CRÍTICA'
        }

        return {
            'crisis_empleo': stress_test_1,
            'crisis_tipos': stress_test_2,
            'crisis_jubilacion': stress_test_3
        }

    def _calcular_cuota_hipoteca(self, capital: float, tae: float) -> float:
        """Calcula cuota mensual de hipoteca"""
        meses = 360  # 30 años standard
        tae_mensual = (tae / 100) / 12

        if tae_mensual == 0:
            return capital / meses

        return capital * (tae_mensual * (1 + tae_mensual) ** meses) / ((1 + tae_mensual) ** meses - 1)

    def generar_plan_90_dias(self) -> dict:
        """
        Genera un plan de acción semanal de 90 días hiper-específico

        Estructura:
        - Semanas 1-2: Documentación + Diagnóstico
        - Semanas 3-4: Encontrar dinero "fantasma" (€200-300/mes)
        - Semanas 5-8: Ataque contra deuda tóxica
        - Semanas 9-12: Construcción de colchón + Planning futura
        """

        plan = {
            'fase_1': {
                'titulo': 'FASE 1: Documento + Diagnóstico (Semanas 1-2)',
                'objetivo': 'Tener visibilidad TOTAL de la situación',
                'tareas': [
                    {
                        'semana': 1,
                        'tarea': 'Crear carpeta "Salud Financiera" con TODOS los documentos',
                        'subtareas': [
                            'Últimos 6 nóminas',
                            'Hipoteca: contrato + última cuota',
                            'Tarjeta: extracto completo',
                            'Seguros: pólizas activas',
                            'Extractos bancarios (últimos 3 meses)',
                            'Declaración de impuestos último año'
                        ],
                        'resultado': '€0 impacto inmediato | Base para decisiones'
                    },
                    {
                        'semana': 2,
                        'tarea': 'Mapear TODOS tus gastos mes a mes',
                        'subtareas': [
                            'Descargar extractos del banco',
                            'Crear spreadsheet de gastos reales',
                            'Agrupar en: Hipoteca | Servicios | Alimentación | Ocio | Otras',
                            'Identificar dónde va tu dinero'
                        ],
                        'resultado': '€0 impacto inmediato | Visibilidad total'
                    }
                ]
            },
            'fase_2': {
                'titulo': 'FASE 2: Encontrar Dinero Fantasma (Semanas 3-4)',
                'objetivo': 'Liberar €150-300/mes sin cambiar nada estructural',
                'tareas': [
                    {
                        'semana': 3,
                        'tarea': 'Auditar suscripciones y servicios',
                        'subtareas': [
                            'Netflix, Spotify, Disney+, etc.: CANCELAR lo que no uses',
                            'Seguros de hogar/auto: obtener 3 cotizaciones (ahorro típico: 20-30%)',
                            'Internet/Telefonía: renegociar (muchos operadores ofrecen descuentos)',
                            'Servicios financieros: comisiones bancarias (algunas son eliminables)'
                        ],
                        'resultado': 'Encontrar €150-200/mes en dinero puro',
                        'roi': 'Inmediato (próximo recibo)'
                    },
                    {
                        'semana': 4,
                        'tarea': 'Crear sistema de control de gastos',
                        'subtareas': [
                            'Instalar app de control (YNAB, Googledocs)',
                            'Categorizar cada gasto esta semana',
                            'Identificar patrones de gasto hormiga',
                            'Establecer alertas de presupuesto'
                        ],
                        'resultado': '€0-50/mes de ahorro + consciencia radical',
                        'roi': 'Conocimiento = cambio'
                    }
                ]
            },
            'fase_3': {
                'titulo': 'FASE 3: Ataque a Deuda Tóxica (Semanas 5-8)',
                'objetivo': 'Reducir tarjeta de crédito en 30% (si aplica)',
                'tareas': [
                    {
                        'semana': 5,
                        'tarea': 'Renegociar tarjeta de crédito',
                        'subtareas': [
                            'Llamar a banco: solicitar reducción de TAE',
                            'Amenaza creíble: cambiar a otro banco (tienes poder)',
                            f'Si TAE > 18%: solicitar transferencia a 0% durante 6-12 meses',
                            'Si rechazan: cambiar de banco (muchos ofrecen transferencias 0%)'
                        ],
                        'resultado': 'Reducción TAE + 6-12 meses sin interés (potencial)',
                        'roi': '€1,000-2,000 de ahorro en interés'
                    },
                    {
                        'semana': 6,
                        'tarea': 'Crear plan de pago de tarjeta',
                        'subtareas': [
                            f'Calcular: si pagas €300/mes, ¿cuándo se paga?',
                            'Asignar los €150-200 encontrados + otros €100-150',
                            'Automatizar pagos (no olvidar)',
                            'Meta: reducir saldo en €1,200-1,600 en 8 semanas'
                        ],
                        'resultado': 'Sistema automático de ataque a deuda',
                        'roi': 'Psicológico: sientes progreso'
                    },
                    {
                        'semana': 7,
                        'tarea': 'Buscar ingresos complementarios (OPCIONAL)',
                        'subtareas': [
                            'Vender cosas no usadas (ropa, electrónica)',
                            'Freelance: ¿qué puedes hacer en 5h/semana?',
                            'Cashback: usar apps de compra inteligente',
                            'Meta: €200-300 extra en 2-3 semanas'
                        ],
                        'resultado': '€200-300 extra para ataque a deuda',
                        'roi': 'Acelera pagos en 20%'
                    },
                    {
                        'semana': 8,
                        'tarea': 'Revisar progreso y ajustar',
                        'subtareas': [
                            'Comparar saldo inicial vs. actual',
                            'Calcular dinero ahorrado en interés',
                            'Celebrar progreso (psicología importante)',
                            'Reajustar si hay cambios en ingresos/gastos'
                        ],
                        'resultado': 'Claridad sobre velocidad de pago',
                        'roi': 'Motivación para continuar'
                    }
                ]
            },
            'fase_4': {
                'titulo': 'FASE 4: Construcción de Colchón de Emergencia (Semanas 9-10)',
                'objetivo': 'Crear €1,200 en ahorro de emergencia (4 semanas de gastos críticos)',
                'tareas': [
                    {
                        'semana': 9,
                        'tarea': 'Crear cuenta separada de "Emergencia"',
                        'subtareas': [
                            'Banco diferente (para no tocarla)',
                            'Automatizar transferencia de €300/semana',
                            'Objetivo: €1,200 en 4 semanas',
                            'Etiqueta emocional: "Mi paracaídas"'
                        ],
                        'resultado': 'Inicio del colchón (€300)',
                        'roi': 'Reducción de ansiedad: tienes 1 semana de cobertura'
                    },
                    {
                        'semana': 10,
                        'tarea': 'Asegurar que el dinero se acumula',
                        'subtareas': [
                            'Vigilar que no gastes de ahí',
                            'Aumentar si surge dinero extra',
                            'Psicología: ver crecer el número es adictivo'
                        ],
                        'resultado': '€600 acumulado (2 semanas)',
                        'roi': 'Confianza = mejor toma de decisiones'
                    }
                ]
            },
            'fase_5': {
                'titulo': 'FASE 5: Planning Futura (Semanas 11-12)',
                'objetivo': 'Establecer rutina de mantenimiento y planning a mediano plazo',
                'tareas': [
                    {
                        'semana': 11,
                        'tarea': 'Planificar próximos 6 meses',
                        'subtareas': [
                            'Seguir con plan de ataque a tarjeta',
                            'Crecer colchón a €1,800 (si es posible)',
                            'Explorar mejora de ingresos (ascenso, cambio trabajo)',
                            'Planificar seguros faltantes (vida, incapacidad)'
                        ],
                        'resultado': 'Roadmap claro a 6 meses',
                        'roi': 'Dirección = tranquilidad'
                    },
                    {
                        'semana': 12,
                        'tarea': 'Establecer revisión mensual',
                        'subtareas': [
                            'Primer viernes de cada mes: revisar gastos + progreso',
                            '30 minutos máximo (mantener disciplina)',
                            'Ajustar presupuestos si es necesario',
                            'Celebrar pequeñas victorias'
                        ],
                        'resultado': 'Sistema sostenible de control',
                        'roi': 'Libertad = poder financiero'
                    }
                ]
            }
        }

        return plan

    def generar_pdf(self, nombre_archivo: str):
        """Orquesta la generación del PDF brutal completo (30 páginas)"""

        doc = SimpleDocTemplate(
            nombre_archivo,
            pagesize=letter,
            leftMargin=0.75 * inch,
            rightMargin=0.75 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
            title=f"Diagnóstico Financiero - {self.cliente_nombre}"
        )

        story = []

        # PORTADA
        story.append(self._crear_portada())
        story.append(PageBreak())

        # SECCIÓN 1: DIAGNÓSTICO DEL CIRUJANO
        score = self.generar_puntuacion_1_100()
        fugas = self.calcular_fugas_financieras()

        story.extend(self._crear_seccion_diagnostico(score, fugas))
        story.append(PageBreak())

        # SECCIÓN 2: ESPEJO PSICOLÓGICO
        story.extend(self._crear_seccion_psicologica())
        story.append(PageBreak())

        # SECCIÓN 3: SIMULADOR DE IMPACTO
        stress_tests = self.generar_stress_tests()
        story.extend(self._crear_seccion_stress_tests(stress_tests))
        story.append(PageBreak())

        # SECCIÓN 4: RECETA MÉDICA 90 DÍAS
        plan = self.generar_plan_90_dias()
        story.extend(self._crear_seccion_plan_90_dias(plan))
        story.append(PageBreak())

        # CARTA FINAL DEL CONSULTOR
        story.extend(self._crear_carta_final(score))

        # Generar
        doc.build(story)
        print(f"✅ PDF BRUTAL generado: {nombre_archivo}")

    def _crear_portada(self) -> list:
        """Crea portada impactante"""
        return [
            Spacer(1, 1.5 * inch),
            Paragraph(
                f"DIAGNÓSTICO FINANCIERO",
                self.estilos['TituloPortada']
            ),
            Paragraph(
                f"Salud Patrimonial Familiar",
                self.estilos['SubtituloPortada']
            ),
            Spacer(1, 0.3 * inch),
            Paragraph(
                f"Cliente: {self.cliente_nombre}",
                self.estilos['CuerpoJustificado']
            ),
            Paragraph(
                f"Fecha: {self.fecha}",
                self.estilos['CuerpoJustificado']
            ),
            Spacer(1, 0.5 * inch),
            Paragraph(
                "DOCUMENTO CONFIDENCIAL",
                self.estilos['Impacto']
            ),
        ]

    def _crear_seccion_diagnostico(self, score: int, fugas: list) -> list:
        """Crea sección 1: El Diagnóstico del Cirujano"""
        content = [
            Paragraph("1. EL DIAGNÓSTICO DEL CIRUJANO", self.estilos['Heading1']),
            Paragraph("¿Qué te pasa?", self.estilos['Heading2']),
            Spacer(1, 0.3 * inch),
        ]

        # Mostrar score
        color_score = self.COLOR_CRITICO if score < 50 else self.COLOR_ALERTA if score < 70 else self.COLOR_SEGURO

        content.append(
            Paragraph(
                f"Tu Puntuación de Salud Financiera: <b><font color='{color_score}'>{score}/100</font></b>",
                self.estilos['Impacto']
            )
        )

        content.append(Spacer(1, 0.2 * inch))

        # Descripción por rango
        if score < 40:
            diagnostico_texto = f"<b>CRÍTICO:</b> Tu estructura financiera está bajo riesgo inmediato. Sin cambios, una emergencia te llevaría al colapso en menos de 30 días."
        elif score < 60:
            diagnostico_texto = f"<b>ALERTA:</b> Tienes vulnerabilidades importantes. El margen es muy estrecho."
        elif score < 80:
            diagnostico_texto = f"<b>ESTABLE:</b> Tu situación es controlada, pero hay oportunidades de mejora."
        else:
            diagnostico_texto = f"<b>SEGURO:</b> Tu estructura es sólida. Ahora el foco es optimizar y crecer."

        content.append(Paragraph(diagnostico_texto, self.estilos['CuerpoJustificado']))
        content.append(Spacer(1, 0.2 * inch))

        # Mostrar fugas
        if fugas:
            content.append(Paragraph("<b>Las 3 Fugas Principales:</b>", self.estilos['Heading3']))
            for i, fuga in enumerate(fugas[:3], 1):
                content.append(Paragraph(
                    f"<b>Fuga {i}: {fuga['titulo']}</b> ({fuga['severidad']})",
                    self.estilos['Impacto']
                ))
                content.append(Paragraph(
                    f"{fuga['descripcion']} <br/>Impacto anual: €{fuga['impacto_anual']:.0f}",
                    self.estilos['CuerpoJustificado']
                ))
                content.append(Spacer(1, 0.15 * inch))

        return content

    def _crear_seccion_psicologica(self) -> list:
        """Crea sección 2: Espejo Psicológico"""
        return [
            Paragraph("2. EL ESPEJO PSICOLÓGICO", self.estilos['Heading1']),
            Paragraph("¿Por qué te pasa?", self.estilos['Heading2']),
            Spacer(1, 0.2 * inch),
            Paragraph(
                "Tu problema no es el dinero. Es cómo lo veas, cómo lo heredaste, y cómo crees que debe comportarse.",
                self.estilos['CuerpoJustificado']
            ),
            Spacer(1, 0.3 * inch),
            Paragraph("<b>Los datos muestran algo interesante:</b>", self.estilos['Heading3']),
            Paragraph(
                "Tus decisiones sobre dinero vienen de patrones heredados. Nada de esto es tu culpa. Pero ahora que lo ves claro, ES tu responsabilidad cambiarlo.",
                self.estilos['CuerpoJustificado']
            ),
        ]

    def _crear_seccion_stress_tests(self, stress_tests: dict) -> list:
        """Crea sección 3: Simulador de Impacto"""
        content = [
            Paragraph("3. EL SIMULADOR DE IMPACTO", self.estilos['Heading1']),
            Paragraph("¿Qué pasará si no haces nada?", self.estilos['Heading2']),
            Spacer(1, 0.3 * inch),
        ]

        for nombre, test in stress_tests.items():
            content.append(Paragraph(f"<b>{test['nombre']}</b>", self.estilos['Impacto']))
            content.append(Paragraph(f"<i>{test['escenario']}</i>", self.estilos['Heading3']))
            content.append(Paragraph(test['sentencia'], self.estilos['CuerpoJustificado']))
            content.append(Spacer(1, 0.15 * inch))

        return content

    def _crear_seccion_plan_90_dias(self, plan: dict) -> list:
        """Crea sección 4: Receta Médica a 90 Días"""
        content = [
            Paragraph("4. LA RECETA MÉDICA: TU PLAN DE 90 DÍAS", self.estilos['Heading1']),
            Paragraph("¿Cómo lo solucionas?", self.estilos['Heading2']),
            Spacer(1, 0.2 * inch),
        ]

        for fase_key, fase in plan.items():
            content.append(Paragraph(f"<b>{fase['titulo']}</b>", self.estilos['Impacto']))
            content.append(Paragraph(f"Objetivo: {fase['objetivo']}", self.estilos['Heading3']))

            for tarea in fase['tareas']:
                content.append(Paragraph(
                    f"Semana {tarea['semana']}: {tarea['tarea']}",
                    self.estilos['Heading4']
                ))

            content.append(Spacer(1, 0.2 * inch))

        return content

    def _crear_carta_final(self, score: int) -> list:
        """Crea carta final del consultor"""
        return [
            Paragraph("CARTA FINAL DEL CONSULTOR", self.estilos['Heading1']),
            Spacer(1, 0.3 * inch),
            Paragraph(
                f"Estimado/a {self.cliente_nombre},",
                self.estilos['CuerpoJustificado']
            ),
            Paragraph(
                f"Tu puntuación actual es {score}/100. No es el número que querías leer, lo sé. Pero es honesto.",
                self.estilos['CuerpoJustificado']
            ),
            Paragraph(
                "El verdadero problema no es que hayas llegado a esta situación. El verdadero problema sería quedarte aquí.",
                self.estilos['Impacto']
            ),
            Paragraph(
                "Tu plan de 90 días es ejecutable. Cada tarea fue diseñada para ser concreta, específica, y dentro de tu capacidad HOY.",
                self.estilos['CuerpoJustificado']
            ),
            Spacer(1, 0.2 * inch),
            Paragraph(
                "<b>Las próximas 12 semanas van a cambiar tu relación con el dinero. No porque será fácil. Porque será diferente.</b>",
                self.estilos['Impacto']
            ),
            Spacer(1, 0.5 * inch),
            Paragraph(
                "Con respeto,<br/>Tu Consultor Financiero",
                self.estilos['CuerpoJustificado']
            ),
        ]


# Test del generador
if __name__ == "__main__":
    datos_maria = {
        'ingresos_netos': 2800,
        'gastos_totales': 2650,
        'saldo_hipoteca': 150000,
        'hipoteca_tae': 4.2,
        'saldo_tarjetas': 8500,
        'tarjeta_tae': 21.0,
        'ahorros_totales': 0,
        'edad': 38,
        'tiene_seguro_vida': False,
        'incapacidad_laboral': False,
        'responsabilidad_civil': False,
        'gastos_variables': 800,
        'suscripciones': 65
    }

    generador = GeneradorPDFBrutal("María García López", datos_maria, "AHOGADO_DEUDAS")
    generador.generar_pdf("C:\\Users\\javie\\OneDrive\\Escritorio\\diagnostico financiero\\INFORME_BRUTAL_v2_MARIA.pdf")
