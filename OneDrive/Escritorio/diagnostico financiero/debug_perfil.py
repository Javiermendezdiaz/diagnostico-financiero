#!/usr/bin/env python3
"""Debug script to identify where generate_perfil fails"""
import sys
from pathlib import Path

app_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(app_dir))

from diagnostic_engine_extended import DiagnosticEngineExtended

engine_ext = DiagnosticEngineExtended("data-schema-500.json")

test_cases = [
    {
        "name": "endeudado_critico",
        "data": {
            "ingresos_netos": 2000,
            "gastos_totales": 1900,
            "saldo_hipoteca": 300000,
            "saldo_tarjetas": 20000,
            "ahorros_totales": 2000,
            "stress_nivel": 9
        }
    },
    {
        "name": "estable",
        "data": {
            "ingresos_netos": 3000,
            "gastos_totales": 2500,
            "saldo_hipoteca": 200000,
            "saldo_tarjetas": 5000,
            "ahorros_totales": 10000,
            "stress_nivel": 5
        }
    },
    {
        "name": "patrimonial",
        "data": {
            "ingresos_netos": 5000,
            "gastos_totales": 2000,
            "saldo_hipoteca": 100000,
            "saldo_tarjetas": 0,
            "ahorros_totales": 50000,
            "stress_nivel": 2
        }
    }
]

for test in test_cases:
    data = test["data"]
    print(f"\n=== Test: {test['name']} ===")
    print(f"Input data: {data}")

    # Manual calculation
    total_deuda = data['saldo_hipoteca'] + data['saldo_tarjetas']
    ingresos = data['ingresos_netos']
    ratio_deuda_ingresos = total_deuda / ingresos if ingresos > 0 else 10
    ratio_ahorros = data['ahorros_totales'] / ingresos if ingresos > 0 else 0
    ratio_gasto_ingreso = data['gastos_totales'] / ingresos if ingresos > 0 else 1

    print(f"Ratios: deuda/ing={ratio_deuda_ingresos:.2f}, ahorros/ing={ratio_ahorros:.2f}, gasto/ing={ratio_gasto_ingreso:.2f}")

    # Try to call method with detailed error info
    try:
        perfil = engine_ext.generate_perfil(data)
        print(f"Result: {perfil}")
    except Exception as e:
        print(f"EXCEPTION: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
