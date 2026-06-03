#!/usr/bin/env python3
"""
PSYCHOLOGY BACKEND SERVICE — SPRINT 7
Timer urgency + Social proof + FOMO badges + event logging
TOP 1% MUNDO — Mecanismos psicológicos persistidos en BD
"""

from datetime import datetime, timedelta
from typing import Dict, List
import random
import json

class PsychologyBackendService:
    """Orquesta timer urgency, social proof, FOMO — todo persistido en BD"""

    # 6 ciudades españolas para social proof
    PROOF_CITIES = ["Madrid", "Barcelona", "Valencia", "Bilbao", "Sevilla", "Palma"]

    # Contadores iniciales de spots FOMO
    INITIAL_SPOTS = {
        "basic": 2,
        "professional": 1,
        "pareja": 3
    }

    @staticmethod
    def initialize_session_psychology(session_obj, db_session=None):
        """
        Inicializa mecanismos psicológicos al crear sesión.
        Retorna dict con configuración para frontend.
        """
        # 1. Asignar ciudad aleatoria
        city = random.choice(PsychologyBackendService.PROOF_CITIES)
        session_obj.social_proof_city = city
        session_obj.social_proof_generated_at = datetime.utcnow()

        # 2. Iniciar timer urgency (15 minutos)
        session_obj.session_urgency_started_at = datetime.utcnow()
        session_obj.session_urgency_expires_at = datetime.utcnow() + timedelta(minutes=15)
        session_obj.urgency_status = "active"

        # 3. Inicializar FOMO spots
        session_obj.tier_spots_available_basic = PsychologyBackendService.INITIAL_SPOTS["basic"]
        session_obj.tier_spots_available_professional = PsychologyBackendService.INITIAL_SPOTS["professional"]
        session_obj.tier_spots_available_pareja = PsychologyBackendService.INITIAL_SPOTS["pareja"]
        session_obj.fomo_last_update_at = datetime.utcnow()

        if db_session:
            db_session.commit()

        return {
            "city": city,
            "timer_expires_at": session_obj.session_urgency_expires_at.isoformat(),
            "spots": {
                "basic": session_obj.tier_spots_available_basic,
                "professional": session_obj.tier_spots_available_professional,
                "pareja": session_obj.tier_spots_available_pareja
            }
        }

    @staticmethod
    def get_urgency_state(session_obj) -> Dict:
        """Retorna estado actual del timer (para refresh en frontend)"""
        if not session_obj or not session_obj.session_urgency_expires_at:
            return {"remaining_seconds": 0, "is_expired": True}

        now = datetime.utcnow()
        remaining = (session_obj.session_urgency_expires_at - now).total_seconds()

        if remaining < 0:
            session_obj.urgency_status = "expired"
            remaining = 0

        minutes = int(remaining // 60)
        seconds = int(remaining % 60)

        return {
            "remaining_seconds": max(0, remaining),
            "is_expired": remaining < 0,
            "display_string": f"{minutes:02d}:{seconds:02d}",
            "status": session_obj.urgency_status if hasattr(session_obj, 'urgency_status') else "unknown"
        }

    @staticmethod
    def get_social_proof_data(session_obj) -> Dict:
        """Retorna ciudad asignada para este session"""
        if not session_obj:
            return {"city": "España", "timestamp": None}

        return {
            "city": session_obj.social_proof_city or "España",
            "timestamp": session_obj.social_proof_generated_at.isoformat() if session_obj.social_proof_generated_at else None
        }

    @staticmethod
    def get_fomo_badges(session_obj) -> Dict:
        """Retorna spots disponibles actualizados dinámicamente"""
        if not session_obj:
            return {"basic_spots": 0, "professional_spots": 0, "pareja_spots": 0}

        return {
            "basic_spots": max(0, session_obj.tier_spots_available_basic or 0),
            "professional_spots": max(0, session_obj.tier_spots_available_professional or 0),
            "pareja_spots": max(0, session_obj.tier_spots_available_pareja or 0),
            "last_update": session_obj.fomo_last_update_at.isoformat() if session_obj.fomo_last_update_at else None
        }

    @staticmethod
    def decrement_fomo_spot(session_obj, tier: str, db_session=None) -> bool:
        """Decrementa contador de spots para tier (simulación de presión)"""
        if not session_obj:
            return False

        if tier == "basic" and (session_obj.tier_spots_available_basic or 0) > 0:
            session_obj.tier_spots_available_basic -= 1
        elif tier == "professional" and (session_obj.tier_spots_available_professional or 0) > 0:
            session_obj.tier_spots_available_professional -= 1
        elif tier == "pareja" and (session_obj.tier_spots_available_pareja or 0) > 0:
            session_obj.tier_spots_available_pareja -= 1
        else:
            return False

        session_obj.fomo_last_update_at = datetime.utcnow()

        if db_session:
            db_session.commit()

        return True
