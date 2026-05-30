#!/usr/bin/env python3
"""
Consent Management - GDPR Art. 7, 15-20, 21, 17
Explicit, revocable, auditable consent with email verification
Task #23 — RGPD Foundation Builder
"""

import json
import secrets
import logging
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple

from sqlalchemy import Column, String, DateTime, Boolean, Enum as SQLEnum, JSON, Index, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)
Base = declarative_base()

# ============ ENUMS ============

class ConsentType(str, Enum):
    DIAGNOSIS = "diagnosis"                  # Procesar diagnóstico completo
    EMAIL_TRIGGERS = "email_triggers"        # Recibir emails +30d, +180d
    DATA_RETENTION = "data_retention"        # Retención 12 meses vs borrado automático
    THIRD_PARTY_DPA = "third_party_dpa"     # Compartir con processor (ej. Render, SendGrid)

class ConsentStatus(str, Enum):
    INITIATED = "initiated"                  # Usuario comenzó flujo, pendiente email
    PENDING_VERIFICATION = "pending_verification"  # Email enviado, await click
    VERIFIED = "verified"                    # Consentimiento activo
    WITHDRAWN = "withdrawn"                  # Revocado (Art. 7.3)
    EXPIRED = "expired"                      # Token expiró (48h)

# ============ ORM MODELS ============

class ConsentRecord(Base):
    """
    Consentimiento explícito, revocable, auditable (Art. 7 GDPR)
    - Cada consentimiento es granular (diagnosis, email_triggers, etc.)
    - Requiere verificación por email
    - Audit trail completo de decisiones
    - TTL en token (48h)
    """
    __tablename__ = "consent_records"
    __table_args__ = (
        Index("idx_user_id_type", "user_id", "consent_type"),
        Index("idx_verification_token", "verification_token"),
        Index("idx_email", "email"),
    )

    id = Column(String(36), primary_key=True)
    user_id = Column(String(100), nullable=False, index=True)
    email = Column(String(255), nullable=False)
    consent_type = Column(SQLEnum(ConsentType), nullable=False)
    status = Column(SQLEnum(ConsentStatus), default=ConsentStatus.INITIATED)

    # Email verification
    verification_token = Column(String(64), unique=True, nullable=True)
    verification_token_expires_at = Column(DateTime, nullable=True)
    verification_sent_at = Column(DateTime, nullable=True)
    verified_at = Column(DateTime, nullable=True)

    # Withdrawal (Art. 7.3, Art. 17, Art. 21)
    withdrawn_at = Column(DateTime, nullable=True)
    withdrawal_reason = Column(String(500), nullable=True)

    # Audit trail
    ip_address = Column(String(45), nullable=True)  # IPv4/IPv6
    user_agent = Column(String(500), nullable=True)
    audit_log = Column(JSON, default=list)  # [{action, timestamp, ip, reason}, ...]

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> Dict:
        """Serializar para API response"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "email": self.email,
            "consent_type": self.consent_type.value,
            "status": self.status.value,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "withdrawn_at": self.withdrawn_at.isoformat() if self.withdrawn_at else None,
            "created_at": self.created_at.isoformat(),
            "audit_log": self.audit_log
        }

# ============ CONSENT SERVICE ============

class ConsentService:
    """Lógica de negocio para consentimiento GDPR"""

    TOKEN_EXPIRY_HOURS = 48
    EMAIL_VERIFICATION_SUBJECT = "Verifica tu consentimiento — Diagnóstico Financiero"

    @staticmethod
    def initiate_consent(
        user_id: str,
        email: str,
        consent_type: ConsentType,
        ip_address: str,
        user_agent: str,
        session: Session,
        send_email_func=None  # Mock para testing
    ) -> Tuple[ConsentRecord, str]:
        """
        Paso 1: Usuario inicia flujo consentimiento
        - Generar token de verificación (48h TTL)
        - Guardar en BD
        - Enviar email
        - Retornar consent_id + token (token solo para testing)
        """
        try:
            # Generar token criptográfico
            verification_token = secrets.token_urlsafe(32)
            consent_id = str(uuid.uuid4())
            now = datetime.utcnow()

            record = ConsentRecord(
                id=consent_id,
                user_id=user_id,
                email=email,
                consent_type=consent_type,
                status=ConsentStatus.PENDING_VERIFICATION,
                verification_token=verification_token,
                verification_token_expires_at=now + timedelta(hours=self.TOKEN_EXPIRY_HOURS),
                verification_sent_at=now,
                ip_address=ip_address,
                user_agent=user_agent,
                audit_log=[{
                    "action": "initiated",
                    "timestamp": now.isoformat(),
                    "ip": ip_address,
                    "consent_type": consent_type.value
                }]
            )

            session.add(record)
            session.flush()  # Generar ID antes de enviar email

            # Enviar email (si se proporciona función)
            if send_email_func:
                email_body = ConsentService._build_verification_email(
                    user_name=user_id,
                    verification_token=verification_token,
                    consent_type=consent_type.value
                )
                send_email_func(
                    to_email=email,
                    subject=self.EMAIL_VERIFICATION_SUBJECT,
                    body=email_body
                )

            session.commit()
            logger.info(f"[CONSENT] Initiated {consent_type.value} for {user_id}")

            return record, verification_token  # Token solo para testing/logging

        except IntegrityError as e:
            session.rollback()
            logger.error(f"[CONSENT] Integrity error: {e}")
            raise ValueError("Consentimiento ya existe para este usuario/email")
        except Exception as e:
            session.rollback()
            logger.error(f"[CONSENT] Error initiating consent: {e}")
            raise

    @staticmethod
    def verify_consent(
        verification_token: str,
        session: Session
    ) -> ConsentRecord:
        """
        Paso 2: Usuario hace click en email
        - Validar token (no expirado)
        - Marcar como VERIFIED
        - Audit trail
        """
        now = datetime.utcnow()

        record = session.query(ConsentRecord).filter_by(
            verification_token=verification_token
        ).first()

        if not record:
            raise ValueError("Token inválido o no encontrado")

        if record.status == ConsentStatus.VERIFIED:
            raise ValueError("Consentimiento ya verificado")

        if record.status == ConsentStatus.WITHDRAWN:
            raise ValueError("Consentimiento fue revocado")

        if record.verification_token_expires_at < now:
            record.status = ConsentStatus.EXPIRED
            session.commit()
            raise ValueError("Token expirado (válido 48h). Solicita uno nuevo.")

        # Mark verified
        record.status = ConsentStatus.VERIFIED
        record.verified_at = now
        record.audit_log.append({
            "action": "verified",
            "timestamp": now.isoformat(),
            "method": "email_click"
        })

        session.commit()
        logger.info(f"[CONSENT] Verified {record.consent_type.value} for {record.user_id}")

        return record

    @staticmethod
    def withdraw_consent(
        user_id: str,
        consent_type: Optional[ConsentType],
        reason: str,
        session: Session
    ) -> int:
        """
        Art. 7.3 (Revocar consentimiento)
        Art. 17 (Derecho al olvido) — si withdrawal_reason = "right_to_be_forgotten"

        Retornar número de registros revocados
        """
        now = datetime.utcnow()

        # Buscar todos los consentimientos activos del usuario
        query = session.query(ConsentRecord).filter_by(
            user_id=user_id,
            status=ConsentStatus.VERIFIED
        )

        if consent_type:
            query = query.filter_by(consent_type=consent_type)

        records = query.all()
        count = len(records)

        for record in records:
            record.status = ConsentStatus.WITHDRAWN
            record.withdrawn_at = now
            record.withdrawal_reason = reason
            record.audit_log.append({
                "action": "withdrawn",
                "timestamp": now.isoformat(),
                "reason": reason
            })

        session.commit()
        logger.info(f"[CONSENT] Withdrawn {count} consent(s) for {user_id}: {reason}")

        # IMPORTANTE: Si reason = "right_to_be_forgotten", trigger Mark for Deletion
        # (será llamado desde open_answers_processor.mark_for_deletion)

        return count

    @staticmethod
    def get_user_consents(
        user_id: str,
        session: Session
    ) -> List[ConsentRecord]:
        """
        Art. 15 (Derecho de acceso)
        Retornar todos los consentimientos del usuario con audit trail
        """
        return session.query(ConsentRecord).filter_by(user_id=user_id).order_by(
            ConsentRecord.created_at.desc()
        ).all()

    @staticmethod
    def get_consent_status(
        user_id: str,
        consent_type: ConsentType,
        session: Session
    ) -> Optional[ConsentRecord]:
        """
        ¿Tiene el usuario consentimiento ACTIVO para este tipo?
        Usado antes de procesar diagnóstico/emails
        """
        return session.query(ConsentRecord).filter_by(
            user_id=user_id,
            consent_type=consent_type,
            status=ConsentStatus.VERIFIED
        ).first()

    @staticmethod
    def _build_verification_email(user_name: str, verification_token: str, consent_type: str) -> str:
        """Construir cuerpo de email de verificación"""
        verification_url = f"https://diagnóstico-financiero.com/api/v1/consent/verify?token={verification_token}"

        return f"""
Hola {user_name},

Para completar tu diagnóstico financiero, necesitamos que verifies tu consentimiento.

**Tipo de consentimiento:** {consent_type}

👉 **Hacer clic aquí para verificar:**
{verification_url}

Este enlace es válido por 48 horas.

---
Si no solicitaste esto, puedes ignorar este correo.

Adapta Family Office
        """.strip()

# ============ TESTING ============

def test_consent_flow():
    """Unit test: flujo completo consentimiento"""
    from sqlalchemy import create_engine

    # Setup: BD temporal en memoria
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    print("[TEST] Testing consent flow...")

    # 1. Initiate
    record, token = ConsentService.initiate_consent(
        user_id="test_user_001",
        email="test@example.com",
        consent_type=ConsentType.DIAGNOSIS,
        ip_address="127.0.0.1",
        user_agent="Mozilla/5.0",
        session=session,
        send_email_func=None  # Mock: no enviar email real
    )
    assert record.status == ConsentStatus.PENDING_VERIFICATION
    assert len(token) > 20
    print(f"  ✓ Initiated: {record.id}")

    # 2. Verify
    verified = ConsentService.verify_consent(token, session)
    assert verified.status == ConsentStatus.VERIFIED
    assert verified.verified_at is not None
    print(f"  ✓ Verified: {verified.verified_at.isoformat()}")

    # 3. Check status
    consents = ConsentService.get_user_consents("test_user_001", session)
    assert len(consents) == 1
    assert consents[0].status == ConsentStatus.VERIFIED
    print(f"  ✓ Retrieved {len(consents)} consent record(s)")

    # 4. Withdraw
    withdrawn_count = ConsentService.withdraw_consent(
        user_id="test_user_001",
        consent_type=ConsentType.DIAGNOSIS,
        reason="user_request",
        session=session
    )
    assert withdrawn_count == 1

    # Verify withdrawn
    record_after = session.query(ConsentRecord).filter_by(id=record.id).first()
    assert record_after.status == ConsentStatus.WITHDRAWN
    print(f"  ✓ Withdrawn: {record_after.withdrawn_at.isoformat()}")

    # 5. Check audit trail
    assert len(record_after.audit_log) >= 3
    print(f"  ✓ Audit trail: {len(record_after.audit_log)} events")

    session.close()
    print("[TEST] ✅ All tests passed!")

if __name__ == "__main__":
    test_consent_flow()
