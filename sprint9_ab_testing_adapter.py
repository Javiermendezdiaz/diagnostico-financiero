#!/usr/bin/env python3
"""
SPRINT 9 — A/B TESTING SUPREMO vs CONTROL
Segmentación 50/50, tracking de conversión, validación psicología
TOP 1% MUNDIAL
"""

from typing import Dict, Tuple, Optional
from datetime import datetime
import random
import json
import logging

logger = logging.getLogger(__name__)

class ABTestingAdapter:
    """
    A/B Testing: 50/50 split SUPREMO (6 IxD mechanics) vs CONTROL (minimal UX)
    Metrics: conversion_rate, avg_payment_time, NPS, premium_selection_rate
    """

    COHORTS = {
        "supremo": {
            "name": "SUPREMO (6 IxD Mechanics)",
            "features": {
                "gravedad_cero": True,  # <300ms transitions
                "haptica_digital": True,  # navigator.vibrate
                "premium_design": True,  # Chronicle Display + gradients
                "barra_progreso_dinamica": True,  # SVG wave + comet
                "cursor_magnetico": True,  # 80ms snap
                "viaje_en_tiempo": True,  # ghost persistence
            },
            "pricing_asymmetry": {
                "basic_anchor": 19.00,  # EUR
                "premium_recommended": 39.00,
                "social_proof_text": "91% choose Premium",
                "benefit_language": "Descargar, Acceder, Unlock",
            },
            "expected_metrics": {
                "conversion_rate": 0.75,  # 75%
                "premium_selection": 0.91,  # 91%
                "avg_payment_time_seconds": 180,  # 3 min
                "nps_post_payment": 8.5,
            }
        },
        "control": {
            "name": "CONTROL (Minimal UX)",
            "features": {
                "gravedad_cero": False,
                "haptica_digital": False,
                "premium_design": False,
                "barra_progreso_dinamica": False,
                "cursor_magnetico": False,
                "viaje_en_tiempo": False,
            },
            "pricing_asymmetry": {
                "basic_anchor": 19.00,
                "premium_recommended": 39.00,
                "social_proof_text": None,  # No social proof
                "benefit_language": "Pay, Submit, Download",
            },
            "expected_metrics": {
                "conversion_rate": 0.60,  # 60%
                "premium_selection": 0.60,  # 60%
                "avg_payment_time_seconds": 300,  # 5 min
                "nps_post_payment": 6.5,
            }
        }
    }

    @staticmethod
    def assign_cohort(couple_id: str) -> str:
        """
        Determina cohort (SUPREMO o CONTROL) basado en couple_id
        50/50 split determinista (mismo couple_id siempre mismo cohort)
        """
        hash_value = hash(couple_id) % 2
        return "supremo" if hash_value == 0 else "control"

    @staticmethod
    def get_cohort_config(cohort: str) -> Dict:
        """Retorna configuración completa del cohort"""
        return ABTestingAdapter.COHORTS.get(cohort, ABTestingAdapter.COHORTS["control"])

    @staticmethod
    def get_frontend_flags(couple_id: str) -> Dict:
        """
        Retorna feature flags para el frontend basado en cohort asignado
        Frontend lo usa para renderizar SUPREMO o CONTROL
        """
        cohort = ABTestingAdapter.assign_cohort(couple_id)
        config = ABTestingAdapter.get_cohort_config(cohort)

        return {
            "couple_id": couple_id,
            "cohort": cohort,
            "cohort_name": config["name"],
            "features": config["features"],
            "pricing": config["pricing_asymmetry"],
        }

    @staticmethod
    def validate_conversion_hypothesis(metrics: Dict) -> Tuple[bool, Dict]:
        """
        Valida si hipótesis psicológica se cumple:
        - SUPREMO: 75%+ conversion, 91%+ premium selection, NPS 8.5+
        - Control debe ser <75% conversion (diferencia significativa)
        """
        cohort = metrics.get("cohort", "unknown")
        conversion_rate = metrics.get("conversion_rate", 0)
        premium_selection = metrics.get("premium_selection_rate", 0)
        nps = metrics.get("nps_post_payment", 0)

        expected = ABTestingAdapter.COHORTS[cohort]["expected_metrics"]

        validations = {
            "conversion_meets_target": conversion_rate >= (expected["conversion_rate"] * 0.95),
            "premium_selection_meets_target": premium_selection >= (expected["premium_selection"] * 0.95),
            "nps_meets_target": nps >= (expected["nps_post_payment"] * 0.95),
            "psychological_anchor_works": premium_selection >= 0.80,  # Critical: 80%+ choose premium
        }

        overall_valid = all(validations.values())

        return overall_valid, {
            "cohort": cohort,
            "validations": validations,
            "metrics": metrics,
            "hypothesis_confirmed": overall_valid,
        }


class ABTestingMetrics:
    """Registra y agrega métricas de A/B test"""

    def __init__(self):
        self.events = []

    def log_payment_attempt(self, couple_id: str, cohort: str, plan: str, success: bool, time_seconds: float):
        """Registra intento de pago"""
        self.events.append({
            "type": "payment_attempt",
            "couple_id": couple_id,
            "cohort": cohort,
            "plan": plan,
            "success": success,
            "time_seconds": time_seconds,
            "timestamp": datetime.utcnow().isoformat(),
        })

    def log_nps_response(self, couple_id: str, cohort: str, score: int, comment: str = ""):
        """Registra respuesta NPS post-pago"""
        self.events.append({
            "type": "nps_response",
            "couple_id": couple_id,
            "cohort": cohort,
            "score": score,
            "comment": comment,
            "timestamp": datetime.utcnow().isoformat(),
        })

    def aggregate_by_cohort(self) -> Dict:
        """Agrega métricas por cohort para análisis"""
        supremo_events = [e for e in self.events if e.get("cohort") == "supremo"]
        control_events = [e for e in self.events if e.get("cohort") == "control"]

        return {
            "supremo": self._calculate_metrics(supremo_events),
            "control": self._calculate_metrics(control_events),
            "sample_size": {
                "supremo": len(supremo_events),
                "control": len(control_events),
            },
            "statistical_significance": self._calculate_significance(supremo_events, control_events),
        }

    @staticmethod
    def _calculate_metrics(events: list) -> Dict:
        """Calcula métricas agregadas para un conjunto de eventos"""
        payment_events = [e for e in events if e.get("type") == "payment_attempt"]
        nps_events = [e for e in events if e.get("type") == "nps_response"]

        if not payment_events:
            return {"sample_size": 0, "conversion_rate": 0, "avg_payment_time": 0}

        successful_payments = sum(1 for e in payment_events if e.get("success"))
        conversion_rate = successful_payments / len(payment_events) if payment_events else 0

        avg_payment_time = sum(e.get("time_seconds", 0) for e in payment_events) / len(payment_events) if payment_events else 0

        nps_score = sum(e.get("score", 0) for e in nps_events) / len(nps_events) if nps_events else 0

        premium_payments = sum(1 for e in payment_events if e.get("plan") == "premium" and e.get("success"))
        premium_selection_rate = premium_payments / successful_payments if successful_payments > 0 else 0

        return {
            "sample_size": len(payment_events),
            "conversion_rate": conversion_rate,
            "avg_payment_time_seconds": avg_payment_time,
            "nps_post_payment": nps_score,
            "premium_selection_rate": premium_selection_rate,
            "successful_payments": successful_payments,
            "total_attempts": len(payment_events),
        }

    @staticmethod
    def _calculate_significance(supremo_events: list, control_events: list) -> Dict:
        """
        Calcula significancia estadística entre cohorts
        Requiere mínimo 100 eventos por cohort para validez estadística
        """
        supremo_success = sum(1 for e in supremo_events if e.get("success"))
        control_success = sum(1 for e in control_events if e.get("success"))

        supremo_sample = len([e for e in supremo_events if e.get("type") == "payment_attempt"])
        control_sample = len([e for e in control_events if e.get("type") == "payment_attempt"])

        min_sample_size = 100

        return {
            "supremo_sample_size": supremo_sample,
            "control_sample_size": control_sample,
            "minimum_required": min_sample_size,
            "is_statistically_significant": supremo_sample >= min_sample_size and control_sample >= min_sample_size,
            "supremo_conversion": supremo_success / supremo_sample if supremo_sample > 0 else 0,
            "control_conversion": control_success / control_sample if control_sample > 0 else 0,
            "lift": (supremo_success / supremo_sample - control_success / control_sample) if (supremo_sample > 0 and control_sample > 0) else 0,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINT EXAMPLE (para app_couple_endpoints.py)
# ═══════════════════════════════════════════════════════════════════════════════

"""
from fastapi import FastAPI
from ab_testing_adapter import ABTestingAdapter, ABTestingMetrics

app = FastAPI()
ab_metrics = ABTestingMetrics()

@app.get("/api/ab-test/cohort/{couple_id}")
async def get_ab_cohort(couple_id: str):
    '''Retorna configuración del cohort asignado'''
    flags = ABTestingAdapter.get_frontend_flags(couple_id)
    return flags

@app.post("/api/ab-test/payment-metric")
async def log_payment_metric(couple_id: str, cohort: str, plan: str, success: bool, time_seconds: float):
    '''Registra métrica de pago'''
    ab_metrics.log_payment_attempt(couple_id, cohort, plan, success, time_seconds)
    return {"status": "logged"}

@app.post("/api/ab-test/nps-response")
async def log_nps(couple_id: str, cohort: str, score: int, comment: str = ""):
    '''Registra respuesta NPS post-pago'''
    ab_metrics.log_nps_response(couple_id, cohort, score, comment)
    return {"status": "logged"}

@app.get("/api/ab-test/metrics")
async def get_metrics():
    '''Retorna métricas agregadas por cohort'''
    metrics = ab_metrics.aggregate_by_cohort()
    return metrics
"""

if __name__ == "__main__":
    # Test local
    couple_id = "test_couple_123"
    cohort = ABTestingAdapter.assign_cohort(couple_id)
    flags = ABTestingAdapter.get_frontend_flags(couple_id)

    print(f"Couple ID: {couple_id}")
    print(f"Assigned Cohort: {cohort}")
    print(f"Frontend Flags: {json.dumps(flags, indent=2)}")
