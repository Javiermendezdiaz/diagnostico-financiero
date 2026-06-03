#!/usr/bin/env python3
"""
COUPLE MANAGEMENT ORM — FASE 2 Sprint 2
Modelos SQLAlchemy para Espejo Fantasma (sesiones, respuestas, reportes).
TOP 1% MUNDIAL
"""

from datetime import datetime, timedelta
from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import os

Base = declarative_base()


class CoupleSession(Base):
    """Sesión de pareja (blind session con magic tokens)"""
    __tablename__ = "couple_sessions"

    id = Column(String(255), primary_key=True)
    user_a_id = Column(String(255), nullable=False)
    user_b_id = Column(String(255), nullable=False)
    status = Column(String(50), default="pending")  # pending, in_progress, completed
    tiene_hijos = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, default=lambda: datetime.utcnow() + timedelta(hours=72))

    # SPRINT 7 — Timer urgency fields
    session_urgency_started_at = Column(DateTime, nullable=True)
    session_urgency_expires_at = Column(DateTime, nullable=True)
    urgency_status = Column(String(20), default="inactive")  # inactive, active, expired, completed

    # SPRINT 7 — Social proof fields
    social_proof_city = Column(String(50), nullable=True)
    social_proof_generated_at = Column(DateTime, nullable=True)

    # SPRINT 7 — FOMO fields (decremental spots)
    tier_spots_available_basic = Column(Integer, default=2)
    tier_spots_available_professional = Column(Integer, default=1)
    tier_spots_available_pareja = Column(Integer, default=3)
    fomo_last_update_at = Column(DateTime, nullable=True)

    # SPRINT 9 — A/B Testing fields
    ab_cohort = Column(String(20), default="unknown")  # "supremo", "control", "unknown"
    ab_assigned_at = Column(DateTime, nullable=True)
    ab_variant_active = Column(Boolean, default=True)

    def __repr__(self):
        return f"<CoupleSession {self.id} ({self.status}) [cohort:{self.ab_cohort}]>"


class CoupleAnswers(Base):
    """Respuestas de un miembro de la pareja (500 preguntas × 2 usuarios)"""
    __tablename__ = "couple_answers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    couple_session_id = Column(String(255), nullable=False)
    user_id = Column(String(50), nullable=False)  # user_a, user_b
    answers = Column(Text, nullable=False)  # JSON serializado {q_id: answer}
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<CoupleAnswers {self.couple_session_id}:{self.user_id}>"


class CoupleReport(Base):
    """Resultado final del diagnóstico (23 módulos, PDF)"""
    __tablename__ = "couple_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    couple_session_id = Column(String(255), nullable=False)
    friction_score = Column(Float, default=0.0)  # 0-100 (general)
    shield_score = Column(Float, default=0.0)  # 0-100 (robustez)
    runway_days = Column(Integer, default=0)  # días de estabilidad
    report_data = Column(Text, nullable=False)  # JSON serializado (análisis completo)
    pdf_url = Column(String(500), nullable=True)  # URL descarga PDF
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, default=lambda: datetime.utcnow() + timedelta(hours=72))

    def __repr__(self):
        return f"<CoupleReport {self.couple_session_id} (friction:{self.friction_score})>"


class AnalyticsEvent(Base):
    """Registra eventos granulares de interacción (agnóstico de variant)"""
    __tablename__ = "analytics_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    couple_session_id = Column(String(255), nullable=False, index=True)
    event_type = Column(String(100), nullable=False)  # timer_viewed, badge_viewed, tier_clicked, etc.
    ab_cohort = Column(String(20), nullable=False, default="unknown")  # "supremo", "control"
    event_data = Column(Text, nullable=False)  # JSON payload
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"<AnalyticsEvent {self.event_type} @ {self.created_at} ({self.ab_cohort})>"


class CoupleService:
    """Servicio CRUD para operaciones con parejas"""

    def __init__(self, session: Session = None):
        self.session = session

    def create_session(self, couple_id: str, user_a_id: str, user_b_id: str, tiene_hijos: bool = False) -> CoupleSession:
        """Crea nueva sesión de pareja"""
        session = CoupleSession(
            id=couple_id,
            user_a_id=user_a_id,
            user_b_id=user_b_id,
            tiene_hijos=tiene_hijos,
            status="pending"
        )
        if self.session:
            self.session.add(session)
            self.session.commit()
        return session

    def save_answers(self, couple_id: str, user_id: str, answers: dict) -> CoupleAnswers:
        """Guarda respuestas de un usuario"""
        import json
        answers_obj = CoupleAnswers(
            couple_session_id=couple_id,
            user_id=user_id,
            answers=json.dumps(answers)
        )
        if self.session:
            self.session.add(answers_obj)
            self.session.commit()
        return answers_obj

    def get_session(self, couple_id: str) -> CoupleSession:
        """Obtiene sesión por ID"""
        if not self.session:
            return None
        return self.session.query(CoupleSession).filter_by(id=couple_id).first()

    def get_answers(self, couple_id: str, user_id: str) -> CoupleAnswers:
        """Obtiene respuestas de un usuario"""
        if not self.session:
            return None
        return self.session.query(CoupleAnswers).filter_by(
            couple_session_id=couple_id,
            user_id=user_id
        ).first()

    def save_report(self, couple_id: str, friction_score: float, shield_score: float,
                    runway_days: int, report_data: dict, pdf_url: str = None) -> CoupleReport:
        """Guarda reporte final"""
        import json
        report = CoupleReport(
            couple_session_id=couple_id,
            friction_score=friction_score,
            shield_score=shield_score,
            runway_days=runway_days,
            report_data=json.dumps(report_data),
            pdf_url=pdf_url
        )
        if self.session:
            self.session.add(report)
            self.session.commit()
        return report

    def get_report(self, couple_id: str) -> CoupleReport:
        """Obtiene reporte final"""
        if not self.session:
            return None
        return self.session.query(CoupleReport).filter_by(
            couple_session_id=couple_id
        ).first()

    def mark_session_completed(self, couple_id: str):
        """Marca sesión como completada"""
        if not self.session:
            return
        session = self.get_session(couple_id)
        if session:
            session.status = "completed"
            self.session.commit()

    def cleanup_expired_sessions(self):
        """Limpia sesiones expiradas (GDPR compliance)"""
        if not self.session:
            return 0
        expired = self.session.query(CoupleSession).filter(
            CoupleSession.expires_at < datetime.utcnow()
        ).delete()
        self.session.commit()
        return expired


def get_db_session():
    """Factory para crear sesión de BD"""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL no está configurada")

    engine = create_engine(database_url, echo=False)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()
