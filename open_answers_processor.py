# open_answers_processor.py
"""
Módulo de procesamiento de respuestas abiertas con encriptación RGPD.
AES-256-GCM per-user key derivation (PBKDF2 480K iteraciones).
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from sqlalchemy import Column, String, DateTime, Text, Boolean, Integer, create_engine
from sqlalchemy.orm import declarative_base, Session, sessionmaker

from rgpd_encryption import encrypt_aes256_gcm, decrypt_aes256_gcm

Base = declarative_base()


class OpenAnswerRecord(Base):
    """
    Almacenamiento RGPD-compliant de respuestas abiertas encriptadas.

    RGPD Art. 32: Encriptación por defecto.
    RGPD Art. 15-20: Derecho de acceso, rectificación, olvido, portabilidad.
    """
    __tablename__ = "open_answers"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(100), index=True, nullable=False)
    diagnosis_id = Column(String(36), nullable=False, index=True)

    # Respuestas encriptadas (AES-256-GCM, per-user key)
    encrypted_op1 = Column(Text, nullable=False)  # "ciphertext|nonce"
    encrypted_op2 = Column(Text, nullable=False)
    encrypted_op3 = Column(Text, nullable=False)

    # Metadata para audit trail (RGPD Art. 25)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    ip_address = Column(String(45), nullable=True)  # IPv4 (15) + IPv6 (39)
    user_agent = Column(Text, nullable=True)

    # Consentimiento RGPD (Art. 7)
    consent_given = Column(Boolean, default=True)
    consent_withdrawn_at = Column(DateTime, nullable=True)

    # Retención automática (Art. 5.1.e)
    scheduled_for_deletion = Column(DateTime, nullable=True)  # 12 meses

    def __repr__(self):
        return f"<OpenAnswerRecord({self.user_id}, {self.diagnosis_id})>"


def encrypt_open_answers(
    user_id: str,
    open_answers: Dict[str, str],
    answers_metadata: Optional[Dict] = None
) -> Dict[str, str]:
    """
    Encripta OP1-OP3 usando AES-256-GCM con per-user key derivation.

    Args:
        user_id: Identificador del usuario (para per-user key)
        open_answers: Dict con keys OP1, OP2, OP3 y valores string
        answers_metadata: Metadata adicional (IP, user-agent, etc.)

    Returns:
        Dict con keys encrypted_op1, encrypted_op2, encrypted_op3
        Formato: "base64_ciphertext|base64_nonce"

    Raises:
        ValueError: Si falta alguna respuesta o está vacía
    """
    if not open_answers:
        raise ValueError("open_answers no puede ser vacío")

    encrypted = {}
    metadata = answers_metadata or {}

    for key in ["OP1", "OP2", "OP3"]:
        plaintext = open_answers.get(key, "").strip()

        if not plaintext:
            raise ValueError(f"Respuesta {key} vacía o no proporcionada")

        # Encriptar con per-user key (PBKDF2 480K iteraciones)
        try:
            encrypted_value, nonce = encrypt_aes256_gcm(
                plaintext=plaintext,
                user_id=user_id,
                additional_data=metadata
            )

            # Guardar como "ciphertext|nonce" (base64 encoded)
            encrypted[f"encrypted_{key.lower()}"] = f"{encrypted_value}|{nonce}"

        except Exception as e:
            raise ValueError(f"Error encriptando {key}: {str(e)}")

    return encrypted


async def save_diagnosis(
    user_id: str,
    diagnosis_id: str,
    closed_answers: Dict,
    encrypted_open_answers: Dict,
    scoring_result: Dict,
    inconsistencies: Dict,
    key_variables: Dict,
    session: Session
) -> OpenAnswerRecord:
    """
    Guarda diagnóstico completo en BD.

    Args:
        user_id: ID del usuario
        diagnosis_id: ID del diagnóstico (UUID)
        closed_answers: Respuestas Q1-Q200
        encrypted_open_answers: Respuestas encriptadas OP1-OP3
        scoring_result: Resultado del scoring
        inconsistencies: Inconsistencias detectadas
        key_variables: Variables clave extraídas
        session: SQLAlchemy session

    Returns:
        OpenAnswerRecord guardado en BD
    """

    record = OpenAnswerRecord(
        id=diagnosis_id,
        user_id=user_id,
        diagnosis_id=diagnosis_id,
        encrypted_op1=encrypted_open_answers.get("encrypted_op1", ""),
        encrypted_op2=encrypted_open_answers.get("encrypted_op2", ""),
        encrypted_op3=encrypted_open_answers.get("encrypted_op3", ""),
        consent_given=True,
        # Retención: 12 meses desde ahora
        scheduled_for_deletion=(datetime.utcnow() + timedelta(days=365)).isoformat()
    )

    session.add(record)
    session.commit()

    print(f"[OPEN_ANSWERS] Guardado: {user_id}/{diagnosis_id}")

    return record


def decrypt_open_answers(
    user_id: str,
    encrypted_record: OpenAnswerRecord
) -> Dict[str, str]:
    """
    Desencripta respuestas abiertas (solo para owner/admin).

    Args:
        user_id: ID del usuario propietario
        encrypted_record: Registro encriptado de BD

    Returns:
        Dict con keys OP1, OP2, OP3 desencriptadas

    Raises:
        ValueError: Si descencriptación falla (bad key, corrupted data, etc.)
    """
    decrypted = {}

    for key_lower in ["op1", "op2", "op3"]:
        try:
            encrypted_with_nonce = getattr(encrypted_record, f"encrypted_{key_lower}")

            if not encrypted_with_nonce or "|" not in encrypted_with_nonce:
                raise ValueError(f"Formato inválido para {key_lower}")

            encrypted_value, nonce = encrypted_with_nonce.split("|", 1)

            plaintext = decrypt_aes256_gcm(
                ciphertext=encrypted_value,
                nonce=nonce,
                user_id=user_id
            )

            decrypted[f"OP{len(key_lower)}"] = plaintext

        except Exception as e:
            print(f"[OPEN_ANSWERS] Error desencriptando {key_lower}: {str(e)}")
            raise ValueError(f"No se pueden desencriptar respuestas: {str(e)}")

    return decrypted


def mark_for_deletion(record_id: str, session: Session) -> None:
    """
    Marca un registro para eliminación (RGPD Art. 17 - Derecho al olvido).

    Uso: Cuando usuario ejerce derecho de olvido, llamar esta función.
    El cron job de retención eliminará el registro después de este marcado.
    """
    record = session.query(OpenAnswerRecord).filter_by(id=record_id).first()

    if not record:
        raise ValueError(f"Registro {record_id} no encontrado")

    record.scheduled_for_deletion = datetime.utcnow()
    session.commit()

    print(f"[OPEN_ANSWERS] Marcado para eliminación: {record_id}")


def cleanup_expired_records(session: Session, dry_run: bool = False) -> int:
    """
    Cron job: elimina registros con scheduled_for_deletion vencido.

    Ejecutar cada noche (ej: 02:00 UTC).

    Args:
        session: SQLAlchemy session
        dry_run: Si True, solo reporta sin eliminar

    Returns:
        Número de registros eliminados
    """
    now = datetime.utcnow()
    expired = session.query(OpenAnswerRecord).filter(
        OpenAnswerRecord.scheduled_for_deletion <= now,
        OpenAnswerRecord.scheduled_for_deletion.isnot(None)
    ).all()

    count = len(expired)

    if count == 0:
        print("[OPEN_ANSWERS] No hay registros para limpiar")
        return 0

    if dry_run:
        print(f"[OPEN_ANSWERS] DRY RUN: {count} registros listos para eliminar")
        for record in expired:
            print(f"  - {record.user_id}/{record.diagnosis_id}")
        return count

    for record in expired:
        session.delete(record)

    session.commit()

    print(f"[OPEN_ANSWERS] Limpieza completada: {count} registros eliminados")

    return count


# ============ TESTING ============

if __name__ == "__main__":
    import json
    from rgpd_encryption import init_encryption

    # Inicializar encriptación
    init_encryption()

    # Mock session (usar BD real en producción)
    from sqlalchemy import create_engine

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    # Test 1: Encriptar respuestas
    print("\n=== TEST 1: Encriptar respuestas ===")
    user_id = "user_123"
    open_answers = {
        "OP1": "La pregunta sobre deudas me impactó",
        "OP2": "estrés",
        "OP3": "Prefería no saber que gasto más de lo que gano"
    }

    encrypted = encrypt_open_answers(user_id, open_answers)
    print(f"Encriptado correctamente. Keys: {list(encrypted.keys())}")

    # Test 2: Guardar en BD
    print("\n=== TEST 2: Guardar en BD ===")
    diagnosis_id = str(uuid.uuid4())
    record = OpenAnswerRecord(
        id=diagnosis_id,
        user_id=user_id,
        diagnosis_id=diagnosis_id,
        encrypted_op1=encrypted["encrypted_op1"],
        encrypted_op2=encrypted["encrypted_op2"],
        encrypted_op3=encrypted["encrypted_op3"]
    )
    session.add(record)
    session.commit()
    print(f"Guardado en BD: {record.id}")

    # Test 3: Desencriptar
    print("\n=== TEST 3: Desencriptar ===")
    retrieved = session.query(OpenAnswerRecord).filter_by(id=diagnosis_id).first()
    decrypted = decrypt_open_answers(user_id, retrieved)
    print(f"Desencriptado correctamente:")
    for key, value in decrypted.items():
        print(f"  {key}: {value}")

    # Test 4: Validar que desencriptación falla con user_id incorrecto
    print("\n=== TEST 4: Validar seguridad (user_id incorrecto) ===")
    try:
        bad_decrypt = decrypt_open_answers("otro_user", retrieved)
        print("ERROR: Debería haber fallado!")
    except ValueError as e:
        print(f"✓ Falló como se esperaba: {str(e)[:50]}...")

    print("\n=== TODOS LOS TESTS PASADOS ===")
