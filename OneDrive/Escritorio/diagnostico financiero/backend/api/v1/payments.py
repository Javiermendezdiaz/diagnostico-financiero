"""
Payment Management API

Gestiona:
1. Inicialización de pagos Bizum (deep-linking nativo)
2. Callbacks post-pago desde banco (webhook)
3. Validación de estado de pago
4. Crédito automático al usuario tras confirmación

Estrategia Bizum:
- Payloadez como proveedor (especialista español)
- App-to-App deep linking (cero formularios)
- Biometric auth en app bancaria
- Return-to-app automático tras pago

Flujo:
Usuario en LoadingSequence ve "Agregar 300 créditos (29€)"
→ POST /api/v1/payments/initialize_bizum
→ Retorna deep_link_url
→ User tap → app bancaria abre
→ Biometric + confirmation
→ Banco POST a /api/v1/payments/callback?payment_id=XXX&status=success
→ Claude API crea CreditTransaction (+300)
→ User vuelve a app con créditos ya sumados
"""

import uuid
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from enum import Enum

from fastapi import APIRouter, HTTPException, Request, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import httpx

from backend.models.credit_system import (
    UserCreditAccount,
    CreditTransaction,
    CreditTransactionType
)
from backend.schemas.payment import (
    PaymentInitRequest,
    PaymentInitResponse,
    PaymentCallbackRequest,
    PaymentStatusResponse
)
from backend.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])


class PaymentStatus(str, Enum):
    """Estados de un pago en el sistema"""
    PENDING = "PENDING"              # Esperando confirmación del banco
    SUCCESS = "SUCCESS"              # Pago confirmado, créditos otorgados
    FAILED = "FAILED"                # Pago fallido o rechazado
    EXPIRED = "EXPIRED"              # Timeout (15min sin confirmación)
    CANCELLED = "CANCELLED"          # Usuario canceló en app bancaria


class PaymentRecord(Base):
    """
    Registro de cada intento de pago.

    Vincula: usuario → transacción de créditos → estado de pago → Bizum reference
    """
    __tablename__ = "payment_records"

    id = Column(String(36), primary_key=True)  # UUID
    user_id = Column(String(36), nullable=False, index=True)

    # Datos del pago
    amount_eur = Column(Numeric(10, 2), nullable=False)  # €29.00
    credits_amount = Column(Integer, nullable=False)  # 300 créditos

    # Estado
    payment_status = Column(String(20), default=PaymentStatus.PENDING.value, nullable=False, index=True)

    # Referencias externas
    payloadez_reference = Column(String(100), nullable=True, unique=True, index=True)  # Del banco
    bizum_reference_id = Column(String(100), nullable=True)  # Nuestro reference en Bizum

    # Links
    deep_link_url = Column(String(500), nullable=True)  # URL para abrir app bancaria
    return_url = Column(String(500), nullable=True)  # Donde vuelve el usuario

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    confirmed_at = Column(DateTime, nullable=True)  # Cuándo confirma el banco
    expires_at = Column(DateTime, nullable=True)  # Timeout (created_at + 15min)

    # Metadata
    metadata = Column(JSON, default=dict, nullable=False)

    def is_expired(self) -> bool:
        """Comprueba si el pago expiró (15min timeout)"""
        return datetime.utcnow() > self.expires_at if self.expires_at else False


# Config Payloadez (normalmente desde environment variables)
PAYLOADEZ_CONFIG = {
    "api_url": "https://api.payloadez.com",
    "api_key": "sk_live_your_payloadez_api_key",  # TODO: environment variable
    "beneficiary_name": "Adapta Family Office",
    "timeout_seconds": 900  # 15 minutos
}

BIZUM_CONFIG = {
    "app_scheme": "bizum://",
    "return_scheme": "diagnosticofinanciero://",
    "timeout_seconds": 900
}

PAYMENT_PRICING = {
    "standard_bundle": {
        "credits": 300,
        "amount_eur": 29.00,
        "description": "Pack de 300 créditos de auditoría"
    },
    "large_bundle": {
        "credits": 600,
        "amount_eur": 49.00,
        "description": "Pack de 600 créditos de auditoría"
    }
}


@router.post("/initialize_bizum", response_model=PaymentInitResponse)
async def initialize_bizum_payment(
    request: PaymentInitRequest,
    db: Session = Depends(get_db)
) -> PaymentInitResponse:
    """
    Inicializa un pago Bizum.

    Flujo:
    1. Validar que usuario existe y tiene cuenta de créditos
    2. Crear PaymentRecord en estado PENDING
    3. Generar deep-link URL a app bancaria
    4. Retornar URL al frontend (user taps → app abre)

    Args:
        request.user_id: UUID del usuario
        request.bundle_type: "standard_bundle" (300€ 29€) o "large_bundle" (600€ 49€)
        request.return_url: URL para volver tras pago (ej: app://payments/callback)

    Returns:
        PaymentInitResponse con deep_link_url y payment_id

    Raises:
        HTTPException 400: usuario no encontrado, bundle inválido
        HTTPException 500: error creando pago
    """

    # Validar que usuario existe
    user_account = db.query(UserCreditAccount).filter_by(user_id=request.user_id).first()
    if not user_account:
        raise HTTPException(status_code=400, detail=f"Usuario {request.user_id} no tiene cuenta de créditos")

    # Validar bundle
    if request.bundle_type not in PAYMENT_PRICING:
        raise HTTPException(
            status_code=400,
            detail=f"Bundle '{request.bundle_type}' no válido. Usa: {list(PAYMENT_PRICING.keys())}"
        )

    bundle = PAYMENT_PRICING[request.bundle_type]

    try:
        # Crear PaymentRecord
        payment_id = str(uuid.uuid4())
        bizum_reference = f"DIAG_{payment_id[:8].upper()}"  # Ej: DIAG_A1B2C3D4

        # Deep-link URL a Payloadez
        # Payloadez abre app bancaria, configura pago, vuelve con status
        deep_link_url = (
            f"{PAYLOADEZ_CONFIG['api_url']}/bizum/open"
            f"?reference={bizum_reference}"
            f"&amount={bundle['amount_eur']}"
            f"&beneficiary={PAYLOADEZ_CONFIG['beneficiary_name']}"
            f"&description={bundle['description']}"
            f"&return_url=https://app.diagnosticofinanciero.com/api/v1/payments/callback"
            f"&timeout={BIZUM_CONFIG['timeout_seconds']}"
        )

        # iOS deep-link alternativo (si falla Payloadez web)
        ios_deeplink = f"bizum://pay/{bizum_reference}"

        # Crear registro de pago
        payment_record = PaymentRecord(
            id=payment_id,
            user_id=request.user_id,
            amount_eur=float(bundle["amount_eur"]),
            credits_amount=bundle["credits"],
            payment_status=PaymentStatus.PENDING.value,
            bizum_reference_id=bizum_reference,
            deep_link_url=deep_link_url,
            return_url=request.return_url,
            expires_at=datetime.utcnow() + timedelta(seconds=BIZUM_CONFIG["timeout_seconds"]),
            metadata={
                "bundle_type": request.bundle_type,
                "client_ip": request.client.host if request.client else "unknown"
            }
        )

        db.add(payment_record)
        db.commit()

        logger.info(
            f"Payment initialized: user={request.user_id} "
            f"payment_id={payment_id} amount={bundle['amount_eur']}€ "
            f"credits={bundle['credits']}"
        )

        return PaymentInitResponse(
            payment_id=payment_id,
            deep_link_url=deep_link_url,
            ios_deeplink=ios_deeplink,
            amount_eur=float(bundle["amount_eur"]),
            credits_amount=bundle["credits"],
            reference=bizum_reference
        )

    except IntegrityError as e:
        db.rollback()
        logger.error(f"Integrity error creating payment: {str(e)}")
        raise HTTPException(status_code=500, detail="Error creando registro de pago")
    except Exception as e:
        db.rollback()
        logger.error(f"Error initializing payment: {str(e)}")
        raise HTTPException(status_code=500, detail="Error inicializando pago Bizum")


@router.post("/callback")
async def payment_callback(
    payment_id: str = Query(...),
    status: str = Query(...),  # success | failed | cancelled
    bizum_reference: Optional[str] = Query(None),
    amount: Optional[float] = Query(None),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Webhook desde Payloadez/banco tras completar pago.

    Llega aquí cuando:
    - Usuario completa pago en app bancaria ✓
    - Usuario cancela operación ✗
    - Timeout sin respuesta
    - Pago rechazado por insuficiencia de fondos

    Pasos:
    1. Validar payment_id y status
    2. Si SUCCESS: crear CreditTransaction (+créditos), actualizar UserCreditAccount
    3. Si FAILED/CANCELLED: marcar como fallido, no otorgar créditos
    4. Retornar status para app (user puede ver result)

    Args:
        payment_id: UUID del pago (enviado por Payloadez)
        status: "success" | "failed" | "cancelled"
        bizum_reference: referencia de Bizum (ej: DIAG_A1B2C3D4)
        amount: cantidad confirmada en €

    Returns:
        {"status": "processed", "user_id": "...", "credits_added": N}

    Raises:
        HTTPException 400: payment_id no encontrado o inválido
        HTTPException 500: error procesando callback
    """

    try:
        # Buscar registro de pago
        payment = db.query(PaymentRecord).filter_by(id=payment_id).first()
        if not payment:
            logger.warning(f"Callback para payment_id desconocido: {payment_id}")
            raise HTTPException(status_code=400, detail=f"Payment ID {payment_id} no encontrado")

        # Validar que no está expirado
        if payment.is_expired() and status == "success":
            logger.warning(f"Pago llegó después de timeout: {payment_id}")
            payment.payment_status = PaymentStatus.EXPIRED.value
            db.commit()
            raise HTTPException(status_code=400, detail="Pago expiró (timeout de 15min)")

        # Procesar según status
        if status.lower() == "success":
            # ✓ PAGO CONFIRMADO: otorgar créditos
            payment.payment_status = PaymentStatus.SUCCESS.value
            payment.payloadez_reference = bizum_reference
            payment.confirmed_at = datetime.utcnow()

            # Obtener cuenta de usuario
            user_account = db.query(UserCreditAccount).filter_by(user_id=payment.user_id).first()
            if not user_account:
                # Crear si no existe (edge case: usuario sin cuenta anterior)
                user_account = UserCreditAccount(
                    id=str(uuid.uuid4()),
                    user_id=payment.user_id
                )
                db.add(user_account)
                db.flush()

            # Crear transacción de créditos
            transaction = user_account.add_credits(
                amount=payment.credits_amount,
                transaction_type=CreditTransactionType.PURCHASE,
                description=f"Compra de {payment.credits_amount} créditos - Bizum {payment.amount_eur}€",
                metadata={
                    "payment_id": payment_id,
                    "bizum_reference": bizum_reference,
                    "bundle_type": payment.metadata.get("bundle_type"),
                    "amount_eur": float(payment.amount_eur)
                }
            )
            db.add(transaction)
            db.commit()

            logger.info(
                f"Payment SUCCESS: user={payment.user_id} "
                f"payment_id={payment_id} credits={payment.credits_amount} "
                f"amount={payment.amount_eur}€"
            )

            return {
                "status": "processed",
                "user_id": payment.user_id,
                "credits_added": payment.credits_amount,
                "credits_total": user_account.available_credits,
                "payment_status": PaymentStatus.SUCCESS.value
            }

        else:
            # ✗ PAGO FALLIDO O CANCELADO: no otorgar créditos
            if status.lower() == "failed":
                payment.payment_status = PaymentStatus.FAILED.value
            elif status.lower() == "cancelled":
                payment.payment_status = PaymentStatus.CANCELLED.value

            db.commit()

            logger.info(
                f"Payment {status.upper()}: user={payment.user_id} "
                f"payment_id={payment_id}"
            )

            return {
                "status": "processed",
                "user_id": payment.user_id,
                "credits_added": 0,
                "payment_status": payment.payment_status
            }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error procesando callback: {str(e)}")
        raise HTTPException(status_code=500, detail="Error procesando pago")


@router.get("/status/{payment_id}", response_model=PaymentStatusResponse)
async def get_payment_status(
    payment_id: str,
    db: Session = Depends(get_db)
) -> PaymentStatusResponse:
    """
    Consulta estado de un pago (usado si callback se pierda o para polling).

    Retorna:
    - payment_status: PENDING | SUCCESS | FAILED | EXPIRED | CANCELLED
    - credits_added: N si SUCCESS, 0 si no
    - confirmed_at: timestamp si confirmado

    Args:
        payment_id: UUID del pago

    Returns:
        PaymentStatusResponse

    Raises:
        HTTPException 404: payment_id no encontrado
    """
    payment = db.query(PaymentRecord).filter_by(id=payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail=f"Payment {payment_id} no encontrado")

    credits_added = payment.credits_amount if payment.payment_status == PaymentStatus.SUCCESS.value else 0

    return PaymentStatusResponse(
        payment_id=payment_id,
        payment_status=payment.payment_status,
        amount_eur=float(payment.amount_eur),
        credits_amount=payment.credits_amount,
        credits_added=credits_added,
        confirmed_at=payment.confirmed_at,
        expires_at=payment.expires_at
    )
