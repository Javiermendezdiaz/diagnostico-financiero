#!/usr/bin/env python3
"""Debug script with full traceback to isolate the exact failure point"""
import sys
import traceback
from pathlib import Path

app_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(app_dir))

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

print("Calling generate_perfil with test data...")
print(f"Input: {test_data}\n")

try:
    perfil = engine_ext.generate_perfil(test_data)
    print(f"Result: {perfil}")
except Exception as e:
    print(f"Exception caught at top level:")
    print(f"Type: {type(e).__name__}")
    print(f"Message: {e}")
    print("\nFull traceback:")
    traceback.print_exc()
