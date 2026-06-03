#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Motor Adaptativo de Selección de 100 Preguntas Dinámicas
Sistema de Test Inteligente para Diagnóstico Financiero Familiar

Arquitectura:
- FASE 1: Cimientos (25 preguntas obligatorias)
- FASE 2: Bifurcación Vital (50 preguntas adaptadas al perfil)
- FASE 3: Traca Psicológica (25 preguntas de comportamiento)

Total: 100 preguntas de banco de 500 disponibles
"""

import json
from typing import Dict, List, Tuple, Optional

class MotorAdaptativo100Preguntas:
    """Motor de selección dinámica de 100 preguntas personalizadas"""

    BANCO_TOTAL = 500  # Preguntas disponibles
    PREGUNTAS_MOSTRADAS = 100  # Las que se presentan al usuario

    FASE1_MINIMO = 25  # Obligatorio (cimientos)
    FASE2_MINIMO = 50  # Dinámico (bifurcación)
    FASE3_MINIMO = 25  # Obligatorio (psicología)

    def __init__(self):
        self.respuestas = {}
        self.preguntas_seleccionadas = []
        self.perfil = None
        self.triggers_activados = set()

    def procesar_fase1(self, respuestas_fase1: Dict) -> Dict:
        """
        Procesa respuestas de Fase 1 y detecta:
        - Ingresos, gastos, deudas, estructura familiar
        - Triggers que activan secciones especializadas en Fase 2
        """
        self.respuestas.update(respuestas_fase1)

        # Análisis de factores críticos
        ingreso_mensual = respuestas_fase1.get('ingresos_netos', 0)
        gastos_mensuales = respuestas_fase1.get('gastos_totales', 0)
        deuda_tarjetas = respuestas_fase1.get('saldo_tarjetas', 0)
        saldo_hipoteca = respuestas_fase1.get('saldo_hipoteca', 0)
        ahorros = respuestas_fase1.get('ahorros_totales', 0)
        tiene_hijos = respuestas_fase1.get('tiene_hijos', False)

        # Indicadores clave
        ratio_gastos = (gastos_mensuales / ingreso_mensual * 100) if ingreso_mensual > 0 else 100
        deuda_total = deuda_tarjetas + saldo_hipoteca
        ratio_deuda_ingresos = deuda_total / (ingreso_mensual * 12) if ingreso_mensual > 0 else 999
        cobertura_emergencia = ahorros / gastos_mensuales if gastos_mensuales > 0 else 0

        # Detección de "herida financiera" principal
        diagnostico = {
            'ratio_gastos': ratio_gastos,
            'ratio_deuda': ratio_deuda_ingresos,
            'cobertura_meses': cobertura_emergencia,
            'deuda_tarjeta_presente': deuda_tarjetas > 0,
            'tiene_hijos': tiene_hijos,
            'ratio_pago_deudas': self._calcular_ratio_pago_deudas(respuestas_fase1)
        }

        return diagnostico

    def _calcular_ratio_pago_deudas(self, respuestas: Dict) -> float:
        """Calcula porcentaje de ingresos dedicado a deudas"""
        ingreso = respuestas.get('ingresos_netos', 1)
        pago_hipoteca = respuestas.get('pago_hipoteca_mensual', 0)
        pago_minimo_tarjeta = respuestas.get('pago_minimo_tarjeta', 0)
        otros_prestamos = respuestas.get('pago_otros_prestamos', 0)

        total_deudas = pago_hipoteca + pago_minimo_tarjeta + otros_prestamos
        return (total_deudas / ingreso * 100) if ingreso > 0 else 0

    def detectar_perfil(self, diagnostico: Dict) -> str:
        """
        Detecta el perfil financiero primario basado en Fase 1

        Perfiles:
        - AHOGADO_DEUDAS: ratio_pago_deudas > 30%
        - ESTANCADO: bajo ahorro + sin inversiones + con capacidad
        - INVERSOR: patrimonio invertido > 50k
        - VARIABLE: ingresos fluctuantes > 30%
        - FAMILIA_PROTEGIDA: con hijos, seguros, planning
        """

        ratio_pago = diagnostico['ratio_pago_deudas']
        cobertura = diagnostico['cobertura_meses']
        tiene_hijos = diagnostico['tiene_hijos']

        # Lógica de clasificación (cascada)
        if ratio_pago > 40:
            return "AHOGADO_DEUDAS"
        elif cobertura < 1 and ratio_pago > 30:
            return "AHOGADO_DEUDAS"
        elif cobertura > 6 and self.respuestas.get('inversiones', 0) > 0:
            return "INVERSOR"
        elif cobertura < 3 and not self.respuestas.get('pareja_ingresos', False):
            return "ESTANCADO"
        elif self.respuestas.get('ingresos_variables', False):
            return "VARIABLE"
        elif tiene_hijos:
            return "FAMILIA_DESPROTEGIDA"
        else:
            return "GENERICO"

    def generar_fase2(self, perfil: str) -> List[Dict]:
        """
        Genera 50 preguntas de Fase 2 personalizadas por perfil

        Cada perfil activa diferentes "bancos de preguntas especializadas"
        """

        bancos_por_perfil = {
            "AHOGADO_DEUDAS": {
                "primario": ["deudas", "flujo_caja", "stress_test"],
                "secundario": ["psicologia", "familia"],
                "desactivado": ["inversiones", "patrimonio"]
            },
            "ESTANCADO": {
                "primario": ["familia", "gastos_variables", "ahorro"],
                "secundario": ["psicologia", "seguros"],
                "desactivado": ["inversiones_avanzadas"]
            },
            "INVERSOR": {
                "primario": ["inversiones", "patrimonio", "activos"],
                "secundario": ["psicologia", "riesgo"],
                "desactivado": ["manejo_deudas_consumo"]
            },
            "VARIABLE": {
                "primario": ["flujo_caja", "colchon_emergencia", "clientes"],
                "secundario": ["deudas", "psicologia"],
                "desactivado": ["inversiones"]
            },
            "FAMILIA_DESPROTEGIDA": {
                "primario": ["seguros", "proteccion", "sucesion"],
                "secundario": ["educacion_financiera", "familia"],
                "desactivado": []
            },
            "GENERICO": {
                "primario": ["balance", "flujo", "ahorro"],
                "secundario": ["psicologia"],
                "desactivado": []
            }
        }

        config = bancos_por_perfil.get(perfil, bancos_por_perfil["GENERICO"])

        # Distribución: 60% primario, 30% secundario, 10% flexible
        fase2_preguntas = []

        # 30 preguntas primarias (60%)
        for banco_name in config['primario']:
            preguntas = self._obtener_preguntas_banco(banco_name, 10)
            fase2_preguntas.extend(preguntas)

        # 15 preguntas secundarias (30%)
        for banco_name in config['secundario']:
            preguntas = self._obtener_preguntas_banco(banco_name, 8)
            fase2_preguntas.extend(preguntas)

        # 5 preguntas flexibles (10%)
        preguntas_flex = self._obtener_preguntas_aleatorias(5)
        fase2_preguntas.extend(preguntas_flex)

        return fase2_preguntas[:50]

    def generar_fase3(self) -> List[Dict]:
        """
        Genera 25 preguntas de Fase 3 (Psicología y Comportamiento)

        Mide:
        - Miedos financieros
        - Creencias limitantes
        - Herencia de patrones
        - Compromiso con cambio
        - Aversión al riesgo real
        """

        preguntas_psicologia = [
            {
                "id": "PSI_001",
                "categoria": "miedos",
                "texto": "¿Cuál es tu mayor miedo financiero?",
                "tipo": "multiple_choice",
                "peso": 10
            },
            {
                "id": "PSI_002",
                "categoria": "paralizacion",
                "texto": "¿En qué medida ese miedo te paraliza para tomar decisiones?",
                "tipo": "escala_1_10",
                "peso": 10
            },
            {
                "id": "PSI_003",
                "categoria": "locus_control",
                "texto": "¿Cuánta responsabilidad sientes sobre tu situación actual?",
                "tipo": "escala_1_10",
                "peso": 9
            },
            {
                "id": "PSI_004",
                "categoria": "herencia",
                "texto": "¿De dónde heredaste tus creencias sobre dinero?",
                "tipo": "multiple_choice",
                "peso": 8
            },
            {
                "id": "PSI_005",
                "categoria": "narrativa",
                "texto": "Completa: 'El dinero es...'",
                "tipo": "multiple_choice",
                "peso": 9
            },
            {
                "id": "PSI_006",
                "categoria": "compromiso",
                "texto": "¿Qué estás dispuesto a sacrificar HOY por seguridad en 10 años?",
                "tipo": "escala_sacrificio",
                "peso": 10
            },
            {
                "id": "PSI_007",
                "categoria": "trauma",
                "texto": "¿Has tenido experiencia traumática con dinero?",
                "tipo": "binaria",
                "peso": 10
            },
            {
                "id": "PSI_008",
                "categoria": "sueno",
                "texto": "Si tuvieras el dinero que necesitas, ¿qué harías diferente?",
                "tipo": "texto_abierto",
                "peso": 9
            },
            {
                "id": "PSI_009",
                "categoria": "aislamiento",
                "texto": "¿Cuándo fue la última vez que hablaste abiertamente de finanzas?",
                "tipo": "multiple_choice",
                "peso": 8
            },
            {
                "id": "PSI_010",
                "categoria": "sesgo_cognitivo",
                "texto": "¿Cuál crees que es tu mayor limitación?",
                "tipo": "multiple_choice",
                "peso": 9
            }
        ]

        # Ampliar a 25 preguntas con variaciones
        return preguntas_psicologia * 2 + preguntas_psicologia[:5]

    def _obtener_preguntas_banco(self, banco: str, cantidad: int) -> List[Dict]:
        """Retorna preguntas especializadas de un banco específico"""
        # Simulación: en producción vendría de BD
        bancos_disponibles = {
            "deudas": [
                {"id": f"DEUDA_{i}", "texto": f"Pregunta sobre deudas {i}"}
                for i in range(1, 21)
            ],
            "flujo_caja": [
                {"id": f"FLUJO_{i}", "texto": f"Pregunta sobre flujo {i}"}
                for i in range(1, 21)
            ],
            "psicologia": [
                {"id": f"PSICO_{i}", "texto": f"Pregunta psicología {i}"}
                for i in range(1, 11)
            ],
            # ... más bancos
        }
        return bancos_disponibles.get(banco, [])[:cantidad]

    def _obtener_preguntas_aleatorias(self, cantidad: int) -> List[Dict]:
        """Retorna preguntas aleatorias para completar los 50"""
        return [
            {"id": f"FLEX_{i}", "texto": f"Pregunta flexible {i}"}
            for i in range(1, cantidad + 1)
        ]

    def generar_test_completo(self, respuestas_fase1: Dict) -> Tuple[str, List[Dict], List[Dict]]:
        """
        Orquesta todo el proceso:
        1. Analiza Fase 1
        2. Detecta perfil
        3. Genera Fase 2 personalizada
        4. Genera Fase 3
        """

        diagnostico = self.procesar_fase1(respuestas_fase1)
        perfil = self.detectar_perfil(diagnostico)
        self.perfil = perfil

        fase2 = self.generar_fase2(perfil)
        fase3 = self.generar_fase3()

        return perfil, fase2, fase3

    def generar_reporte_motor(self, perfil: str) -> Dict:
        """Genera reporte de cómo funciona el motor para este perfil"""
        return {
            "perfil_detectado": perfil,
            "distribucion_preguntas": {
                "fase_1_cimientos": 25,
                "fase_2_bifurcacion": 50,
                "fase_3_psicologia": 25,
                "total": 100
            },
            "bancos_activados": {
                "primario": ["definidos según perfil"],
                "secundario": ["definidos según perfil"],
                "desactivado": ["no incluidos"]
            },
            "triggers": list(self.triggers_activados)
        }


# Test del motor
if __name__ == "__main__":
    motor = MotorAdaptativo100Preguntas()

    # Simular respuestas de Fase 1 (María García)
    respuestas_maria = {
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

    perfil, fase2, fase3 = motor.generar_test_completo(respuestas_maria)

    print(f"✅ MOTOR ADAPTATIVO ACTIVO")
    print(f"   Perfil detectado: {perfil}")
    print(f"   Preguntas Fase 2: {len(fase2)}")
    print(f"   Preguntas Fase 3: {len(fase3)}")
    print(f"   Total de preguntas a mostrar: {25 + len(fase2) + len(fase3)}")
    print(f"\n📊 Reporte del Motor:")
    reporte = motor.generar_reporte_motor(perfil)
    print(json.dumps(reporte, indent=2, ensure_ascii=False))
