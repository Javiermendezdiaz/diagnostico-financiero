#!/usr/bin/env python3
"""Capture the actual exception with traceback"""
import sys
import traceback
from pathlib import Path

app_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(app_dir))

# Monkey-patch the logger to raise instead of catching
import logging
logging.basicConfig(level=logging.DEBUG)

from diagnostic_engine_extended import DiagnosticEngineExtended

engine_ext = DiagnosticEngineExtended("data-schema-500.json")

test_data = {
    "ingresos_netos": 2000,
    "gastos_totales": 1900,
    "saldo_hipoteca": 300000,
    "saldo_tarjetas": 20000,
    "ahorros_totales": 2000,
    "stress_nivel": 9
}

# Patch generate_perfil to not catch exceptions
original_generate_perfil = engine_ext.generate_perfil

def patched_generate_perfil(respuestas):
    """Patched version that doesn't catch exceptions"""
    try:
        # Extract Phase 1 financial metrics
        ingresos_netos = respuestas.get('ingresos_netos', 0)
        gastos_totales = respuestas.get('gastos_totales', 0)
        saldo_hipoteca = respuestas.get('saldo_hipoteca', 0)
        saldo_tarjetas = respuestas.get('saldo_tarjetas', 0)
        ahorros_totales = respuestas.get('ahorros_totales', 0)
        stress_nivel = respuestas.get('stress_nivel', 5)
        control_gastos = respuestas.get('control_gastos', 5)

        print(f"   Extracted values:")
        print(f"     ingresos_netos = {ingresos_netos}")
        print(f"     saldo_hipoteca = {saldo_hipoteca}")
        print(f"     saldo_tarjetas = {saldo_tarjetas}")

        # Calculate debt and savings ratios
        total_deuda = saldo_hipoteca + saldo_tarjetas
        ratio_deuda_ingresos = total_deuda / ingresos_netos if ingresos_netos > 0 else 10
        ratio_ahorros = ahorros_totales / ingresos_netos if ingresos_netos > 0 else 0
        ratio_gasto_ingreso = gastos_totales / ingresos_netos if ingresos_netos > 0 else 1

        print(f"   Calculated ratios:")
        print(f"     ratio_deuda_ingresos = {ratio_deuda_ingresos}")
        print(f"     stress_nivel = {stress_nivel}")
        print(f"     saldo_tarjetas = {saldo_tarjetas}")

        # Check first condition
        cond1 = ratio_deuda_ingresos > 4
        cond2 = stress_nivel >= 8 and saldo_tarjetas > 5000
        print(f"   Condition 1 (ratio > 4): {cond1}")
        print(f"   Condition 2 (stress >= 8 and tarjetas > 5000): {cond2}")

        if cond1 or cond2:
            perfil = 'endeudado_critico'
        else:
            perfil = 'estable'

        return perfil
    except Exception as e:
        print(f"   Exception in logic: {type(e).__name__}: {e}")
        raise

engine_ext.generate_perfil = patched_generate_perfil

print("\nCalling patched generate_perfil:")
try:
    perfil = engine_ext.generate_perfil(test_data)
    print(f"\nResult: {perfil}")
except Exception as e:
    print(f"\nException caught at top level:")
    print(f"Type: {type(e).__name__}")
    print(f"Message: {e}")
    print("\nFull traceback:")
    traceback.print_exc()
