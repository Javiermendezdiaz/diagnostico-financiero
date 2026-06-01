# email_triggers.py
"""
Módulo de email triggers automáticos (30d, 180d).
RGPD-compliant: audit trail, tracking, personalización.
"""

import uuid
import asyncio
import smtplib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sqlalchemy import Column, String, DateTime, Text, Boolean, Integer, create_engine
from sqlalchemy.orm import declarative_base, Session, sessionmaker

Base = declarative_base()


class EmailTrigger(Base):
    """
    Registro de email triggers (30d, 180d).
    RGPD audit trail: timestamp, retry count, status.
    """
    __tablename__ = "email_triggers"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(100), index=True, nullable=False)
    diagnosis_id = Column(String(36), index=True, nullable=False)

    trigger_type = Column(String(20), index=True)  # "day_30" o "day_180"
    scheduled_at = Column(DateTime, index=True)
    sent_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    retry_count = Column(Integer, default=0, index=True)

    # Contenido del email (sin encriptación, solo audit)
    email_address = Column(String(254), index=True)
    email_subject = Column(Text)
    email_body = Column(Text)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        status = "SENT" if self.sent_at else ("FAILED" if self.failed_at else "PENDING")
        return f"<EmailTrigger({self.trigger_type}, {self.user_id}, {status})>"


def schedule_email_triggers(
    user_id: str,
    diagnosis_id: str,
    email: str,
    open_answers: Dict[str, str],
    session: Session
) -> Tuple[EmailTrigger, EmailTrigger]:
    """
    Programa dos email triggers automáticos (30d y 180d).

    Args:
        user_id: ID del usuario
        diagnosis_id: ID del diagnóstico
        email: Email del usuario para envío
        open_answers: Respuestas abiertas (para personalización)
        session: SQLAlchemy session

    Returns:
        Tuple (trigger_30d, trigger_180d)
    """
    if not email or "@" not in email:
        raise ValueError(f"Email inválido: {email}")

    now = datetime.utcnow()

    # Trigger 1: +30 días
    trigger_30d = EmailTrigger(
        id=str(uuid.uuid4()),
        user_id=user_id,
        diagnosis_id=diagnosis_id,
        trigger_type="day_30",
        scheduled_at=now + timedelta(days=30),
        email_address=email,
        email_subject="30 días después: ¿Cumpliste tu métrica?",
        email_body=generate_email_body_30d(open_answers)
    )
    session.add(trigger_30d)

    # Trigger 2: +180 días
    trigger_180d = EmailTrigger(
        id=str(uuid.uuid4()),
        user_id=user_id,
        diagnosis_id=diagnosis_id,
        trigger_type="day_180",
        scheduled_at=now + timedelta(days=180),
        email_address=email,
        email_subject="180 días después: Tu promesa del día 1",
        email_body=generate_email_body_180d(open_answers)
    )
    session.add(trigger_180d)

    session.commit()

    print(f"[EMAIL_TRIGGERS] Programados para {email}: +30d, +180d")

    return trigger_30d, trigger_180d


def generate_email_body_30d(open_answers: Dict[str, str]) -> str:
    """
    Cuerpo del email 30 días después.
    Referencia OP9 (métrica de éxito 30 días) con variable injection.
    """
    # OP9 será disponible en future iterations con full 10 preguntas
    # Por ahora, usar placeholder genérico
    metric = open_answers.get("OP9", "tu objetivo del mes pasado")

    body = f"""
Hola,

Han pasado exactamente 30 días desde que completaste tu Diagnóstico Financiero.

Cuando terminaste el cuestionario, estableciste esta métrica de éxito para los próximos 30 días:

"{metric}"

Ahora te preguntamos: ¿lo lograste?

Responde a este email con una línea — cuéntanos:
- ¿Qué progreso hiciste?
- ¿Qué obstáculos encontraste?
- ¿Cambió algo en tu plan?

Tu feedback nos ayuda a entender qué funciona en el análisis financiero real.

Un cordial saludo,
Javier Méndez
Adapta Family Office

---
Diagnóstico ID: {open_answers.get('diagnosis_id', 'N/A')}
"""

    return body.strip()


def generate_email_body_180d(open_answers: Dict[str, str]) -> str:
    """
    Cuerpo del email 180 días después.
    Referencia OP10 (promesa al futuro) con variable injection.
    """
    # OP10 será disponible en future iterations
    promise = open_answers.get("OP10", "tu compromiso futuro")

    body = f"""
Hola,

Han pasado 6 meses desde tu Diagnóstico Financiero.

Al final del cuestionario, te comprometiste a:

"{promise}"

Es hora de una reflexión seria. Pregúntate:

- ¿Ese compromiso sigue siendo válido?
- ¿Lo mantuviste? ¿Lo abandonaste? ¿Evolucionó?
- ¿Qué aprendiste sobre ti mismo en estos 180 días?

Si tu situación cambió, o si descubriste que necesitas reajustar el plan, estamos aquí para ayudarte.

Responde a este email o agenda una consulta. Tu situación financiera probablemente se movió más de lo que pensaste.

Un cordial saludo,
Javier Méndez
Adapta Family Office

---
Diagnóstico ID: {open_answers.get('diagnosis_id', 'N/A')}
"""

    return body.strip()


async def process_pending_email_triggers(
    session: Session,
    smtp_config: Optional[Dict] = None,
    dry_run: bool = False
) -> Dict:
    """
    Cron job: procesa email triggers pendientes.

    Ejecutar cada hora (ej: APScheduler o Celery beat).

    Args:
        session: SQLAlchemy session
        smtp_config: Dict con keys: host, port, username, password, from_email
        dry_run: Si True, solo reporta sin enviar

    Returns:
        Dict con stats: {sent, failed, retry}
    """

    now = datetime.utcnow()

    # Obtener triggers pendientes (scheduled_at <= now, sent_at is None, retry < 3)
    pending = session.query(EmailTrigger).filter(
        EmailTrigger.sent_at.is_(None),
        EmailTrigger.scheduled_at <= now,
        EmailTrigger.retry_count < 3
    ).all()

    stats = {"sent": 0, "failed": 0, "retry": 0}

    if len(pending) == 0:
        print("[EMAIL_TRIGGERS] No hay triggers pendientes")
        return stats

    print(f"[EMAIL_TRIGGERS] Procesando {len(pending)} triggers...")

    for trigger in pending:
        try:
            if dry_run:
                print(
                    f"[EMAIL_TRIGGERS] DRY RUN: {trigger.trigger_type} → "
                    f"{trigger.email_address}"
                )
                stats["sent"] += 1
            else:
                # Enviar email
                send_email(
                    to_email=trigger.email_address,
                    subject=trigger.email_subject,
                    body=trigger.email_body,
                    smtp_config=smtp_config
                )

                trigger.sent_at = datetime.utcnow()
                session.commit()

                print(
                    f"[EMAIL_TRIGGERS] ✓ {trigger.trigger_type} enviado a "
                    f"{trigger.email_address}"
                )
                stats["sent"] += 1

        except Exception as e:
            trigger.failed_at = datetime.utcnow()
            trigger.retry_count += 1
            session.commit()

            print(f"[EMAIL_TRIGGERS] ✗ Error en {trigger.trigger_type}: {str(e)[:60]}")
            stats["retry"] += 1

    return stats


def send_email(
    to_email: str,
    subject: str,
    body: str,
    smtp_config: Optional[Dict] = None,
    from_email: Optional[str] = None
) -> None:
    """
    Envía email (SMTP).

    Args:
        to_email: Email destino
        subject: Asunto
        body: Cuerpo del email (plaintext)
        smtp_config: Dict con keys: host, port, username, password
        from_email: Email remitente (si no en smtp_config)

    Raises:
        ValueError: Si SMTP no configurado
        Exception: Si falla envío SMTP
    """

    if not smtp_config:
        print("[EMAIL] SMTP no configurado. Simulando envío a:", to_email)
        return

    host = smtp_config.get("host")
    port = smtp_config.get("port", 587)
    username = smtp_config.get("username")
    password = smtp_config.get("password")
    from_addr = from_email or smtp_config.get("from_email")

    if not all([host, username, password, from_addr]):
        raise ValueError(
            "SMTP config incompleto. Requiere: host, port, username, password, from_email"
        )

    # Crear mensaje MIME
    msg = MIMEMultipart()
    msg["From"] = from_addr
    msg["To"] = to_email
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain"))

    # Enviar
    try:
        with smtplib.SMTP(host, port) as server:
            server.starttls()
            server.login(username, password)
            server.send_message(msg)

        print(f"[EMAIL] Enviado a {to_email}: {subject}")

    except Exception as e:
        raise Exception(f"Error enviando SMTP a {to_email}: {str(e)}")


# ============ TESTING ============

if __name__ == "__main__":
    from sqlalchemy import create_engine

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    # Test 1: Programar triggers
    print("\n=== TEST 1: Programar triggers ===")
    user_id = "user_123"
    diagnosis_id = str(uuid.uuid4())
    email = "user@example.com"
    open_answers = {
        "OP9": "Ahorrar 500€ este mes",
        "OP10": "Tener presupuesto controlado en 6 meses",
        "diagnosis_id": diagnosis_id
    }

    trigger_30d, trigger_180d = schedule_email_triggers(
        user_id, diagnosis_id, email, open_answers, session
    )

    print(f"✓ Trigger 30d: {trigger_30d.id}")
    print(f"✓ Trigger 180d: {trigger_180d.id}")

    # Test 2: Procesar triggers (dry run)
    print("\n=== TEST 2: Procesar triggers (dry run) ===")
    # Simular que scheduled_at ya pasó
    trigger_30d.scheduled_at = datetime.utcnow() - timedelta(days=1)
    session.commit()

    stats = asyncio.run(process_pending_email_triggers(session, dry_run=True))
    print(f"Stats: {stats}")

    print("\n=== TESTS COMPLETADOS ===")
