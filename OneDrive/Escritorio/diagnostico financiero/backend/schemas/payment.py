"""
Payment Schemas

Definiciones de request/response para endpoints de pago Bizum.
Validación automática via Pydantic.
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, validator


class PaymentInitRequest(BaseModel):
    """
    Request para inicializar un pago Bizum.

    POST /api/v1/payments/initialize_bizum
    {
        "user_id": "123e4567-e89b-12d3-a456-426614174000",
        "bundle_type": "standard_bundle",
        "return_url": "diagnosticofinanciero://payments/callback"
    }
    """
    user_id: str = Field(..., description="UUID del usuario")
    bundle_type: str = Field(
        default="standard_bundle",
        description="Tipo de pack: standard_bundle (300€ 29€) o large_bundle (600€ 49€)"
    )
    return_url: Optional[str] = Field(
        default=None,
        description="URL para volver al app tras pago (opcional, server genera default)"
    )

    @validator("user_id")
    def validate_user_id(cls, v):
        if not v or len(v) < 10:
            raise ValueError("user_id debe ser UUID válido")
        return v

    class Config:
        schema_extra = {
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "bundle_type": "standard_bundle",
                "return_url": None
            }
        }


class PaymentInitResponse(BaseModel):
    """
    Response de inicialización de pago.

    Contiene URLs para diferentes plataformas (web, iOS, Android).
    Frontend elige cuál usar basado en device.
    """
    payment_id: str = Field(..., description="UUID del pago (para tracking)")
    deep_link_url: str = Field(..., description="URL web para abrir app bancaria (default)")
    ios_deeplink: Optional[str] = Field(
        default=None,
        description="Deep-link iOS nativo (bizum://pay/...)"
    )
    amount_eur: float = Field(..., description="Cantidad en € a pagar")
    credits_amount: int = Field(..., description="Créditos que recibirá tras confirmación")
    reference: str = Field(..., description="Referencia Bizum (DIAG_XXXXXXXX)")

    class Config:
        schema_extra = {
            "example": {
                "payment_id": "a1b2c3d4-e5f6-47a8-b9c0-d1e2f3a4b5c6",
                "deep_link_url": "https://api.payloadez.com/bizum/open?reference=DIAG_A1B2C3D4&amount=29.00&...",
                "ios_deeplink": "bizum://pay/DIAG_A1B2C3D4",
                "amount_eur": 29.00,
                "credits_amount": 300,
                "reference": "DIAG_A1B2C3D4"
            }
        }


class PaymentStatusResponse(BaseModel):
    """
    Response de consulta de estado de pago.

    GET /api/v1/payments/status/{payment_id}
    """
    payment_id: str
    payment_status: str = Field(..., description="PENDING | SUCCESS | FAILED | EXPIRED | CANCELLED")
    amount_eur: float
    credits_amount: int
    credits_added: int = Field(..., description="Créditos efectivamente otorgados (0 si no SUCCESS)")
    confirmed_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp de confirmación (None si pendiente)"
    )
    expires_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp de expiración (timeout de 15min)"
    )

    class Config:
        schema_extra = {
            "example": {
                "payment_id": "a1b2c3d4-e5f6-47a8-b9c0-d1e2f3a4b5c6",
                "payment_status": "SUCCESS",
                "amount_eur": 29.00,
                "credits_amount": 300,
                "credits_added": 300,
                "confirmed_at": "2026-05-29T14:32:15.123456",
                "expires_at": "2026-05-29T14:47:15.123456"
            }
        }


class PaymentCallbackRequest(BaseModel):
    """
    Request de callback desde Payloadez (webhook).

    POST /api/v1/payments/callback?payment_id=XXX&status=success&amount=29.00&...

    Nota: Payloadez envía como query params, no JSON body.
    Este schema es para documentación; el endpoint usa Query() params directos.
    """
    payment_id: str
    status: str = Field(..., description="success | failed | cancelled")
    bizum_reference: Optional[str] = None
    amount: Optional[float] = None

    @validator("status")
    def validate_status(cls, v):
        if v.lower() not in ["success", "failed", "cancelled"]:
            raise ValueError("status debe ser: success, failed, cancelled")
        return v.lower()

    class Config:
        schema_extra = {
            "example": {
                "payment_id": "a1b2c3d4-e5f6-47a8-b9c0-d1e2f3a4b5c6",
                "status": "success",
                "bizum_reference": "DIAG_A1B2C3D4",
                "amount": 29.00
            }
        }


class CreditStatusResponse(BaseModel):
    """
    Response de estado de créditos (usado por LoadingSequence).

    GET /api/v1/diagnostics/{diagnostic_id}/credit-status
    """
    available_credits: int = Field(..., description="Saldo actual disponible")
    total_earned: int = Field(..., description="Total ganado desde el inicio")
    pdf_cost: int = Field(default=500, description="Costo en créditos para descargar PDF")
    can_redeem: bool = Field(..., description="True si tiene suficientes para PDF")
    credits_needed_to_redeem: int = Field(
        ...,
        description="0 si can_redeem=True, o diferencia si False"
    )

    class Config:
        schema_extra = {
            "example": {
                "available_credits": 200,
                "total_earned": 200,
                "pdf_cost": 500,
                "can_redeem": False,
                "credits_needed_to_redeem": 300
            }
        }
