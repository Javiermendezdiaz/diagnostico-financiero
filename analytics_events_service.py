#!/usr/bin/env python3
"""
ANALYTICS EVENTS SERVICE — SPRINT 7 + SPRINT 9
Captura granular de eventos para ambos variants (SUPREMO + Control)
Agnóstico de A/B — cada evento lleva cohort para medición
"""

from datetime import datetime
from typing import Dict, Any, Optional
import json


class AnalyticsEventsService:
    """Captura eventos y los persiste en BD para análisis posterior"""

    # Tipos de eventos soportados
    EVENT_TYPES = {
        "timer_viewed": "Usuario vio el timer urgency",
        "social_proof_city_viewed": "Usuario vio ciudad de social proof",
        "fomo_badge_viewed": "Usuario vio FOMO badge",
        "tier_clicked": "Usuario clickeó en tier",
        "checkout_started": "Usuario inició checkout",
        "payment_attempt": "Intento de pago (exitoso/fallido)",
        "session_started": "Sesión iniciada",
        "session_completed": "Sesión completada"
    }

    @staticmethod
    def create_event(db_session, session_id: str, event_type: str, ab_cohort: str,
                     event_data: Dict[str, Any], couple_id: Optional[str] = None):
        """
        Crea un evento granular en la BD.
        REQUIERE: tabla AnalyticsEvent en ORM (ver couple_management.py)
        """
        if event_type not in AnalyticsEventsService.EVENT_TYPES:
            return None

        try:
            # Importar aquí para evitar circular imports
            from couple_management import AnalyticsEvent

            event = AnalyticsEvent(
                couple_session_id=session_id,
                event_type=event_type,
                ab_cohort=ab_cohort or "unknown",
                event_data=json.dumps(event_data),
                created_at=datetime.utcnow()
            )

            db_session.add(event)
            db_session.commit()
            return event

        except Exception as e:
            print(f"Error creating event: {e}")
            return None

    @staticmethod
    def log_timer_viewed(db_session, session_id: str, remaining_seconds: int, ab_cohort: str):
        """Evento: usuario vio el timer urgency"""
        return AnalyticsEventsService.create_event(
            db_session, session_id, "timer_viewed", ab_cohort,
            {"remaining_seconds": remaining_seconds}
        )

    @staticmethod
    def log_city_viewed(db_session, session_id: str, city: str, ab_cohort: str):
        """Evento: usuario vio social proof ciudad"""
        return AnalyticsEventsService.create_event(
            db_session, session_id, "social_proof_city_viewed", ab_cohort,
            {"city": city}
        )

    @staticmethod
    def log_badge_viewed(db_session, session_id: str, tier: str, spots_remaining: int, ab_cohort: str):
        """Evento: usuario vio FOMO badge"""
        return AnalyticsEventsService.create_event(
            db_session, session_id, "fomo_badge_viewed", ab_cohort,
            {"tier": tier, "spots_remaining": spots_remaining}
        )

    @staticmethod
    def log_tier_clicked(db_session, session_id: str, tier: str, ab_cohort: str):
        """Evento: usuario clickeó tier"""
        return AnalyticsEventsService.create_event(
            db_session, session_id, "tier_clicked", ab_cohort,
            {"tier": tier}
        )

    @staticmethod
    def log_checkout_started(db_session, session_id: str, tier: str, ab_cohort: str):
        """Evento: usuario inició checkout"""
        return AnalyticsEventsService.create_event(
            db_session, session_id, "checkout_started", ab_cohort,
            {"tier": tier}
        )

    @staticmethod
    def log_payment_attempt(db_session, session_id: str, tier: str, success: bool,
                           time_seconds: float, ab_cohort: str):
        """Evento: intento de pago"""
        return AnalyticsEventsService.create_event(
            db_session, session_id, "payment_attempt", ab_cohort,
            {
                "tier": tier,
                "success": success,
                "time_seconds": time_seconds
            }
        )

    @staticmethod
    def log_session_started(db_session, session_id: str, ab_cohort: str):
        """Evento: sesión iniciada"""
        return AnalyticsEventsService.create_event(
            db_session, session_id, "session_started", ab_cohort,
            {}
        )

    @staticmethod
    def log_session_completed(db_session, session_id: str, ab_cohort: str):
        """Evento: sesión completada"""
        return AnalyticsEventsService.create_event(
            db_session, session_id, "session_completed", ab_cohort,
            {}
        )

    @staticmethod
    def get_events_for_session(db_session, session_id: str) -> list:
        """Obtiene todos los eventos de una sesión"""
        try:
            from couple_management import AnalyticsEvent
            events = db_session.query(AnalyticsEvent).filter_by(
                couple_session_id=session_id
            ).order_by(AnalyticsEvent.created_at).all()
            return events
        except Exception as e:
            print(f"Error fetching events: {e}")
            return []

    @staticmethod
    def count_events_by_type(db_session, event_type: str, cohort: Optional[str] = None) -> int:
        """Cuenta eventos de un tipo específico, opcionalmente filtrado por cohort"""
        try:
            from couple_management import AnalyticsEvent
            query = db_session.query(AnalyticsEvent).filter_by(event_type=event_type)
            if cohort:
                query = query.filter_by(ab_cohort=cohort)
            return query.count()
        except Exception as e:
            print(f"Error counting events: {e}")
            return 0
