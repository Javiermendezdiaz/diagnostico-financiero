"""
Credit System Models

Gestión de créditos/tokens de auditoría:
- UserCreditAccount: saldo disponible, histórico de ganancias/gastos
- CreditTransaction: registro inmutable de cada movimiento (QUIZ_COMPLETION, PURCHASE, PDF_REDEMPTION, REFERRAL)

Diseñado para psicología inversa: usuarios sienten que gastan "tokens" (menos dolor psicológico)
vs. dinero real, lo que facilita conversión en punto de pago crítico.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from decimal import Decimal
from sqlalchemy import Column, String, Integer, DateTime, JSON, ForeignKey, Enum as SQLEnum, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class CreditTransactionType(str, Enum):
    """Tipos de transacciones de crédito"""
    QUIZ_COMPLETION = "QUIZ_COMPLETION"          # +200 créditos (auto-awarded)
    PURCHASE = "PURCHASE"                        # Usuario compra 300+ créditos por dinero
    PDF_REDEMPTION = "PDF_REDEMPTION"            # -500 créditos (costo de descarga PDF)
    REFERRAL = "REFERRAL"                        # +50 créditos (referido completó quiz)
    ADMIN_ADJUSTMENT = "ADMIN_ADJUSTMENT"        # Ajustes manuales del equipo


class UserCreditAccount(Base):
    """
    Cuenta de créditos de usuario.

    Almacena saldo actual y totalizadores históricos para auditoría y análisis
    de comportamiento de conversión.
    """
    __tablename__ = "user_credit_accounts"

    id = Column(String(36), primary_key=True)  # UUID
    user_id = Column(String(36), nullable=False, unique=True, index=True)

    # Saldo actual disponible
    available_credits = Column(Integer, default=0, nullable=False)

    # Históricos (consultas rápidas sin sumar transacciones)
    total_credits_earned = Column(Integer, default=0, nullable=False)
    total_credits_spent = Column(Integer, default=0, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relación con transacciones
    transactions = relationship("CreditTransaction", back_populates="account", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<UserCreditAccount user_id={self.user_id} available={self.available_credits}>"

    def add_credits(self, amount: int, transaction_type: CreditTransactionType,
                    description: str = "", metadata: dict = None) -> 'CreditTransaction':
        """
        Añade créditos a la cuenta y crea registro de transacción.

        Args:
            amount: número de créditos a añadir (positivo)
            transaction_type: tipo de transacción
            description: descripción legible (ej: "Quiz completado - Sección 4")
            metadata: dict de datos adicionales (ej: {"quiz_score": 85, "section": "patrimonio"})

        Returns:
            CreditTransaction creada
        """
        if amount < 0:
            raise ValueError(f"Use subtract_credits() for negative amounts. Got: {amount}")

        self.available_credits += amount
        self.total_credits_earned += amount
        self.updated_at = datetime.utcnow()

        transaction = CreditTransaction(
            account_id=self.id,
            transaction_type=transaction_type,
            amount=amount,
            balance_after=self.available_credits,
            description=description,
            metadata=metadata or {}
        )
        self.transactions.append(transaction)
        return transaction

    def subtract_credits(self, amount: int, transaction_type: CreditTransactionType,
                        description: str = "", metadata: dict = None) -> 'CreditTransaction':
        """
        Resta créditos de la cuenta y crea registro de transacción.

        Args:
            amount: número de créditos a restar (positivo; se convierte internamente a negativo)
            transaction_type: tipo de transacción
            description: descripción legible (ej: "PDF descargado - Diagnóstico #456")
            metadata: dict de datos adicionales

        Returns:
            CreditTransaction creada

        Raises:
            ValueError: si available_credits < amount
        """
        if amount < 0:
            raise ValueError(f"Pass positive amounts; subtraction is automatic. Got: {amount}")

        if self.available_credits < amount:
            raise ValueError(
                f"Insufficient credits. Available: {self.available_credits}, Required: {amount}"
            )

        self.available_credits -= amount
        self.total_credits_spent += amount
        self.updated_at = datetime.utcnow()

        transaction = CreditTransaction(
            account_id=self.id,
            transaction_type=transaction_type,
            amount=-amount,  # Negativo para indicar gasto
            balance_after=self.available_credits,
            description=description,
            metadata=metadata or {}
        )
        self.transactions.append(transaction)
        return transaction

    def can_redeem_pdf(self, pdf_cost: int = 500) -> bool:
        """Comprueba si tiene suficientes créditos para descargar PDF."""
        return self.available_credits >= pdf_cost


class CreditTransaction(Base):
    """
    Registro inmutable de cada movimiento de créditos.

    Funciona como ledger de auditoría: cada acción (quiz completado, compra, descarga PDF)
    genera una transacción con timestamp y contexto.

    Permite:
    - Auditoría financiera (PSD2, compliance español)
    - Análisis de conversión (qué usuarios compran, cuándo, después de cuántos quizzes)
    - Detección de fraude (múltiples transacciones sospechosas)
    """
    __tablename__ = "credit_transactions"

    id = Column(String(36), primary_key=True)  # UUID
    account_id = Column(String(36), ForeignKey("user_credit_accounts.id"), nullable=False, index=True)

    # Tipo de transacción (enum para constraints en BD)
    transaction_type = Column(SQLEnum(CreditTransactionType), nullable=False, index=True)

    # Monto (positivo si gana, negativo si gasta)
    amount = Column(Integer, nullable=False)

    # Saldo después de esta transacción (snapshot para auditoría)
    balance_after = Column(Integer, nullable=False)

    # Descripción legible
    description = Column(String(255), nullable=True)

    # Metadatos JSON para contexto (diagnostic_id, section, payment_id, etc.)
    metadata = Column(JSON, default=dict, nullable=False)

    # Timestamp (immutable después de creación)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relación con cuenta
    account = relationship("UserCreditAccount", back_populates="transactions")

    def __repr__(self):
        return (
            f"<CreditTransaction account_id={self.account_id} "
            f"type={self.transaction_type.value} amount={self.amount} "
            f"balance={self.balance_after} at={self.created_at.isoformat()}>"
        )


class CreditRedemptionRecord(Base):
    """
    Registro de redempciones de créditos para PDFs (auditoría específica).

    Vincula: usuario → transacción de créditos → PDF descargado → timestamp
    Permite trackear qué usuarios descargaron PDFs y cuándo (para análisis cohort).
    """
    __tablename__ = "credit_redemption_records"

    id = Column(String(36), primary_key=True)  # UUID
    user_id = Column(String(36), nullable=False, index=True)

    # Referencia a la transacción de créditos
    transaction_id = Column(String(36), ForeignKey("credit_transactions.id"), nullable=False)

    # Datos del PDF redeemido
    diagnostic_id = Column(String(36), nullable=False, index=True)
    pdf_filename = Column(String(255), nullable=False)
    pdf_pages = Column(Integer, default=38, nullable=False)
    pdf_size_bytes = Column(Integer, nullable=True)

    # Contexto de descarga
    session_type = Column(String(50), nullable=False)  # "individual" o "couple"
    credits_cost = Column(Integer, default=500, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    downloaded_at = Column(DateTime, nullable=True)  # Null si aún no descargado

    def __repr__(self):
        return (
            f"<CreditRedemptionRecord user_id={self.user_id} "
            f"diagnostic_id={self.diagnostic_id} credits={self.credits_cost}>"
        )
