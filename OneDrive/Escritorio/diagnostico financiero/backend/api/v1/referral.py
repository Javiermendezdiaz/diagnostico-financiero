"""
referral.py

Bucle de Recomendación "Skin in the Game":
- Usuario recibe código referral único con su Score actual
- Desafío: "Si 3 amigos completan el test, recuperas 50% del pago"
- Webhook: Validar cuando 3 referrals completaron, trigger 50% refund a Bizum
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
import uuid
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum

router = APIRouter()


class ReferralStatus(str, enum.Enum):
    PENDING = "pending"  # Referral enviado pero amigo no inició test
    IN_PROGRESS = "in_progress"  # Amigo está completando el test
    COMPLETED = "completed"  # Amigo completó el test
    CLAIMED = "claimed"  # Recompensa ya reclamada


# ============ ORM Models ============
class ReferralCode(object):
    """
    Modelo ORM para códigos referral únicos
    """
    __tablename__ = "referral_codes"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("user_credit_accounts.user_id"), nullable=False)
    code = Column(String(16), unique=True, nullable=False)  # e.g., "CARLOS-42-XY7Z"
    
    # Score en el momento de crear el código (para mostrar en invitación)
    user_score_snapshot = Column(Integer)
    
    # Cuánto pagó el usuario original (para calcular 50%)
    original_payment_amount = Column(Float)
    
    # Contador de completions validadas
    completed_referrals_count = Column(Integer, default=0)
    
    # Recompensa reclamada?
    reward_claimed = Column(Integer, default=0)  # boolean: 0=false, 1=true
    
    created_at = Column(DateTime, default=datetime.now)
    expires_at = Column(DateTime)  # 90 días desde creación
    
    referrals = relationship("ReferralCompletion", back_populates="code")


class ReferralCompletion(object):
    """
    Modelo ORM para registrar cuando un referral completó el test
    """
    __tablename__ = "referral_completions"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    referral_code_id = Column(String(36), ForeignKey("referral_codes.id"), nullable=False)
    
    # Datos del usuario que fue referido
    referred_user_email = Column(String(255))
    referred_user_id = Column(String(36))
    
    # Su Score después de completar el test
    referred_score = Column(Integer)
    
    status = Column(SQLEnum(ReferralStatus), default=ReferralStatus.PENDING)
    
    created_at = Column(DateTime, default=datetime.now)
    completed_at = Column(DateTime)
    
    code = relationship("ReferralCode", back_populates="referrals")


# ============ Pydantic Schemas ============
class ReferralGenerateRequest(BaseModel):
    diagnostic_id: str
    user_id: str
    user_score: int
    original_payment_amount: float


class ReferralGenerateResponse(BaseModel):
    referral_code: str
    shareable_link: str
    challenge_text: str
    reward_amount: float
    expires_at: str


class ReferralCompleteRequest(BaseModel):
    referral_code: str
    referred_user_id: str
    referred_user_email: str
    referred_score: int


class ReferralStatusResponse(BaseModel):
    referral_code: str
    completed_count: int
    required_count: int
    reward_unlocked: bool
    reward_amount: float


# ============ Endpoints ============
@router.post("/generate")
async def generate_referral_code(request: ReferralGenerateRequest):
    """
    POST /api/v1/referral/generate
    
    Crea un código referral único para el usuario.
    
    Request:
    {
        "diagnostic_id": "uuid",
        "user_id": "uuid",
        "user_score": 42,
        "original_payment_amount": 29.0
    }
    
    Response:
    {
        "referral_code": "CARLOS-42-XY7Z",
        "shareable_link": "https://diagfinanciero.com/join?ref=CARLOS-42-XY7Z",
        "challenge_text": "Carlos, tu Score actual es de 42/100. Si 3 amigos completan el test...",
        "reward_amount": 14.50,
        "expires_at": "2026-08-28"
    }
    """
    
    # Generar código único: NOMBRE-SCORE-RANDOM
    code = f"REF-{request.user_id[:4].upper()}-{uuid.uuid4().hex[:6].upper()}"
    
    reward_amount = request.original_payment_amount * 0.5  # 50% refund
    
    shareable_link = f"https://diagfinanciero.com/join?ref={code}"
    
    challenge_text = f"""
{request.user_id}, tu Score actual es de {request.user_score}/100.

Si compartes tu enlace de Auditoría con 3 amigos que completen su test express, 
te devolvemos el 50% de lo que pagaste (€{reward_amount:.2f}) directamente a tu Bizum.

No es spam. Es un pacto: retáles a mejorar financieramente mientras recuperas tu inversión.
    """.strip()
    
    return {
        "referral_code": code,
        "shareable_link": shareable_link,
        "challenge_text": challenge_text,
        "reward_amount": reward_amount,
        "expires_at": (datetime.now() + timedelta(days=90)).isoformat(),
        "instructions": "Comparte el enlace con amigos. Cuando 3 completen el test, tu recompensa se activa automáticamente."
    }


@router.post("/complete")
async def mark_referral_complete(request: ReferralCompleteRequest):
    """
    POST /api/v1/referral/complete
    
    Webhook: Se llama cuando un referred user completa el test.
    Validar conteo de completions. Si >= 3, trigger refund.
    
    Request:
    {
        "referral_code": "CARLOS-42-XY7Z",
        "referred_user_id": "uuid",
        "referred_user_email": "amigo@example.com",
        "referred_score": 55
    }
    """
    
    # 1. Validar código existe
    # 2. Crear ReferralCompletion record con status=COMPLETED
    # 3. Incrementar completed_referrals_count
    # 4. Si completed_count >= 3:
    #    a. Marcar reward_claimed=1
    #    b. Crear CreditTransaction REFERRAL_REWARD
    #    c. Trigger Bizum refund webhook (50% del original_payment_amount)
    
    return {
        "message": "Referral completion registered",
        "referral_code": request.referral_code,
        "status": "completed",
        "reward_unlocked": False  # Será True cuando 3 completen
    }


@router.get("/status/{referral_code}")
async def get_referral_status(referral_code: str):
    """
    GET /api/v1/referral/status/{referral_code}
    
    Retorna progreso del referral.
    """
    
    return {
        "referral_code": referral_code,
        "completed_count": 1,
        "required_count": 3,
        "reward_unlocked": False,
        "reward_amount": 14.50,
        "message": "2 amigos más para recuperar tu inversión"
    }


@router.post("/claim-reward")
async def claim_referral_reward(payload: dict):
    """
    POST /api/v1/referral/claim-reward
    
    Usuario reclama su recompensa cuando hay 3+ completions.
    Trigger: Bizum refund de 50% a su cuenta.
    """
    
    referral_code = payload.get("referral_code")
    user_id = payload.get("user_id")
    
    # 1. Validar que completed_count >= 3
    # 2. Validar que reward_claimed != 1
    # 3. Crear CreditTransaction tipo REFERRAL_REWARD
    # 4. Trigger Bizum refund endpoint con 50% del monto original
    # 5. Marcar reward_claimed=1
    
    return {
        "message": "Reward claimed successfully",
        "refund_amount": 14.50,
        "payment_method": "bizum",
        "estimated_delivery": "1-2 business days"
    }
