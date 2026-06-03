#!/usr/bin/env python3
"""Explicit debug with print statements to trace error"""
import sys
from pathlib import Path

print("1. Starting script")

app_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(app_dir))

print("2. About to import diagnostic_engine_extended")
from diagnostic_engine_extended import DiagnosticEngineExtended
print("3. Import successful")

print("4. About to initialize DiagnosticEngineExtended")
engine_ext = DiagnosticEngineExtended("data-schema-500.json")
print("5. Engine initialized successfully")

test_data = {
    "ingresos_netos": 2000,
    "gastos_totales": 1900,
    "saldo_hipoteca": 300000,
    "saldo_tarjetas": 20000,
    "ahorros_totales": 2000,
    "stress_nivel": 9
}

print("6. About to call generate_perfil")
print(f"   Input: {test_data}")

import logging
logging.basicConfig(level=logging.DEBUG, format='%(name)s - %(levelname)s - %(message)s')

perfil = engine_ext.generate_perfil(test_data)
print(f"7. generate_perfil returned: {perfil}")
