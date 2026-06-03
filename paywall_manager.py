#!/usr/bin/env python3
"""
PAYWALL MANAGER — FASE 2 Sprint 3
Gestión de suscripción + Stripe integration para Espejo Fantasma.
€19 basic | €39 premium | €500+ high-ticket
TOP 1% MUNDIAL
"""

import stripe
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# ============================================================================
# ENUMS Y CONSTANTS
# ============================================================================

class SubscriptionTier(Enum):
    """Tiers de suscripción de Espejo Fantasma"""
    FREE = "free"  # Sin suscripción
    BASIC = "basic"  # €19 — score + radar
    PREMIUM = "premium"  # €39 — NLP audit + COI + quick wins
    HIGH_TICKET = "high_ticket"  # €500+ — 1-1 session + custom report

class AccessLevel(Enum):
    """Niveles de acceso a contenido"""
    NONE = 0  # Sin acceso
    SCORE = 1  # Solo score (básico)
    VISUALIZATIONS = 2  # Score + 4 visualizaciones
    NLP_AUDIT = 4  # + auditoría NLP
    STRATEGY = 8  # + estrategia COI + quick wins
    CONSULTING = 16  # + acceso a 1-1 session

TIER_PRICES = {
    SubscriptionTier.BASIC: 1900,  # €19.00 en centavos
    SubscriptionTier.PREMIUM: 3900,  # €39.00
    SubscriptionTier.HIGH_TICKET: 50000,  # €500.00
}

TIER_ACCESS = {
    SubscriptionTier.FREE: AccessLevel.SCORE,
    SubscriptionTier.BASIC: AccessLevel.VISUALIZATIONS,
    SubscriptionTier.PREMIUM: AccessLevel.STRATEGY,
    SubscriptionTier.HIGH_TICKET: AccessLevel.CONSULTING,
}

TIER_FEATURES = {
    SubscriptionTier.BASIC: [
        "Score de Compatibilidad",
        "Radar 5D (5 dimensiones)",
    ],
    SubscriptionTier.PREMIUM: [
        "Score de Compatibilidad",
        "Radar 5D + Heatmap + Timeline + Tarjetas",
        "Auditoría NLP (análisis de patrones de lenguaje)",
        "Matriz COI (Conflictos, Objetivos, Influencias)",
        "5 Quick Wins personalizados",
    ],
    SubscriptionTier.HIGH_TICKET: [
        "TODO lo de Premium +",
        "Sesión 1-1 con Javier Méndez (90 min)",
        "Reporte personalizado PDF (20 páginas)",
        "Plan de acción trimestral",
        "Acceso a comunidad cerrada Adapta",
        "Follow-up trimestral de 30 min",
    ],
}


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class SubscriptionRecord:
    """Registro de suscripción de pareja"""
    couple_id: str
    tier: SubscriptionTier
    stripe_customer_id: str
    stripe_subscription_id: Optional[str]
    created_at: datetime
    expires_at: Optional[datetime]
    status: str  # active, cancelled, expired
    invoice_id: Optional[str] = None

    def is_active(self) -> bool:
        """¿Está activa la suscripción?"""
        if self.status != "active":
            return False
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        return True

    def has_access(self, feature: AccessLevel) -> bool:
        """¿Tiene acceso a esta feature?"""
        tier_access = TIER_ACCESS.get(self.tier, AccessLevel.NONE)
        return tier_access.value >= feature.value


# ============================================================================
# PAYWALL MANAGER
# ============================================================================

class PaywallManager:
    """Gestor de pagos y suscripciones para Espejo Fantasma"""

    def __init__(self, stripe_api_key: str, api_base_url: str = "http://localhost:8000"):
        """
        stripe_api_key: clave API de Stripe (sk_test_... o sk_live_...)
        api_base_url: URL base de la API (para webhooks)
        """
        stripe.api_key = stripe_api_key
        self.api_base_url = api_base_url

        # Mock DB (en producción: PostgreSQL)
        self.subscriptions: Dict[str, SubscriptionRecord] = {}

    # ========================================================================
    # STRIPE CHECKOUT
    # ========================================================================

    def create_checkout_session(
        self,
        couple_id: str,
        tier: SubscriptionTier,
        success_url: str = "https://espejo-fantasma.com/success",
        cancel_url: str = "https://espejo-fantasma.com/cancel",
    ) -> Dict:
        """
        Crear sesión de checkout de Stripe.
        Retorna URL de checkout para redirigir al cliente.
        """
        try:
            # Crear o obtener Stripe customer
            customer = stripe.Customer.create(
                metadata={"couple_id": couple_id}
            )

            # Crear sesión de checkout
            price_cents = TIER_PRICES.get(tier)
            if not price_cents:
                raise ValueError(f"Tier {tier.value} no válido")

            session = stripe.checkout.Session.create(
                customer=customer.id,
                payment_method_types=["card"],
                line_items=[
                    {
                        "price_data": {
                            "currency": "eur",
                            "unit_amount": price_cents,
                            "product_data": {
                                "name": f"Espejo Fantasma — {tier.value.capitalize()}",
                                "description": f"Diagnóstico Financiero de Pareja — {tier.value}",
                                "metadata": {
                                    "tier": tier.value,
                                    "couple_id": couple_id,
                                }
                            }
                        },
                        "quantity": 1,
                    }
                ],
                mode="subscription" if tier != SubscriptionTier.HIGH_TICKET else "payment",
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={
                    "couple_id": couple_id,
                    "tier": tier.value,
                }
            )

            logger.info(f"Checkout session created: {session.id} for {couple_id}")

            return {
                "session_id": session.id,
                "checkout_url": session.url,
                "customer_id": customer.id,
            }

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating checkout: {str(e)}")
            raise Exception(f"Error creating checkout: {str(e)}")

    # ========================================================================
    # WEBHOOK HANDLING
    # ========================================================================

    def handle_stripe_webhook(self, event: Dict) -> Dict:
        """
        Procesar webhook de Stripe (pago completado, suscripción confirmada, etc.).
        En producción: verificar firma de webhook con stripe_webhook_secret.
        """
        event_type = event.get("type")

        if event_type == "charge.succeeded":
            return self._handle_charge_succeeded(event)
        elif event_type == "customer.subscription.created":
            return self._handle_subscription_created(event)
        elif event_type == "customer.subscription.deleted":
            return self._handle_subscription_deleted(event)
        else:
            logger.info(f"Unhandled webhook type: {event_type}")
            return {"status": "ignored"}

    def _handle_charge_succeeded(self, event: Dict) -> Dict:
        """Procesador: pago completado (one-time o primer pago)"""
        charge = event["data"]["object"]
        customer_id = charge.get("customer")
        metadata = charge.get("metadata", {})
        couple_id = metadata.get("couple_id")
        tier_str = metadata.get("tier")

        try:
            tier = SubscriptionTier(tier_str)
        except ValueError:
            logger.error(f"Invalid tier: {tier_str}")
            return {"status": "error", "message": "Invalid tier"}

        # Crear registro de suscripción
        self.subscriptions[couple_id] = SubscriptionRecord(
            couple_id=couple_id,
            tier=tier,
            stripe_customer_id=customer_id,
            stripe_subscription_id=charge.id,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=365),  # 1 año
            status="active",
            invoice_id=charge.id,
        )

        logger.info(f"Subscription created for {couple_id} (tier: {tier.value})")

        return {
            "status": "success",
            "couple_id": couple_id,
            "tier": tier.value,
            "expires_at": self.subscriptions[couple_id].expires_at.isoformat(),
        }

    def _handle_subscription_created(self, event: Dict) -> Dict:
        """Procesador: suscripción recurring creada"""
        subscription = event["data"]["object"]
        customer_id = subscription.get("customer")
        metadata = subscription.get("metadata", {})
        couple_id = metadata.get("couple_id")
        tier_str = metadata.get("tier")

        try:
            tier = SubscriptionTier(tier_str)
        except ValueError:
            logger.error(f"Invalid tier: {tier_str}")
            return {"status": "error", "message": "Invalid tier"}

        self.subscriptions[couple_id] = SubscriptionRecord(
            couple_id=couple_id,
            tier=tier,
            stripe_customer_id=customer_id,
            stripe_subscription_id=subscription.id,
            created_at=datetime.utcnow(),
            expires_at=None,  # Recurring, no expiry
            status="active",
        )

        logger.info(f"Recurring subscription created for {couple_id}")

        return {
            "status": "success",
            "couple_id": couple_id,
            "subscription_id": subscription.id,
        }

    def _handle_subscription_deleted(self, event: Dict) -> Dict:
        """Procesador: suscripción cancelada"""
        subscription = event["data"]["object"]
        customer_id = subscription.get("customer")

        # Buscar registro por customer ID
        couple_id = None
        for cid, sub in self.subscriptions.items():
            if sub.stripe_customer_id == customer_id:
                couple_id = cid
                break

        if couple_id:
            self.subscriptions[couple_id].status = "cancelled"
            logger.info(f"Subscription cancelled for {couple_id}")

        return {"status": "success", "couple_id": couple_id}

    # ========================================================================
    # SUBSCRIPTION LOOKUP
    # ========================================================================

    def get_subscription(self, couple_id: str) -> Optional[SubscriptionRecord]:
        """Obtener suscripción de una pareja"""
        return self.subscriptions.get(couple_id)

    def get_tier(self, couple_id: str) -> SubscriptionTier:
        """Obtener tier de suscripción de una pareja (FREE si no existe)"""
        sub = self.get_subscription(couple_id)
        return sub.tier if sub and sub.is_active() else SubscriptionTier.FREE

    def check_access(self, couple_id: str, feature: AccessLevel) -> bool:
        """¿Tiene acceso a una feature?"""
        sub = self.get_subscription(couple_id)
        if not sub or not sub.is_active():
            return feature == AccessLevel.SCORE  # FREE tier tiene acceso a score
        return sub.has_access(feature)

    # ========================================================================
    # PAYWALL ENDPOINTS (para integrar en FastAPI)
    # ========================================================================

    def get_checkout_html(self, couple_id: str) -> str:
        """Generar HTML con opciones de suscripción"""
        return f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Planes — Espejo Fantasma</title>
    <style>
        body {{ font-family: Poppins, sans-serif; background: #FAF8F3; padding: 40px; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{ text-align: center; color: #020203; margin-bottom: 40px; }}
        .plans {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 30px; }}
        .plan {{ background: white; padding: 30px; border-radius: 8px; border: 2px solid #EEEEEE; }}
        .plan.featured {{ border-color: #FDD731; box-shadow: 0 8px 24px rgba(253, 215, 49, 0.2); }}
        .plan-title {{ font-size: 20px; font-weight: 700; color: #020203; margin-bottom: 15px; }}
        .plan-price {{ font-size: 36px; color: #FDD731; font-weight: 700; margin-bottom: 20px; }}
        .plan-price small {{ font-size: 14px; color: #999; }}
        .plan-features {{ list-style: none; margin-bottom: 30px; }}
        .plan-features li {{ padding: 8px 0; color: #666; }}
        .plan-features li:before {{ content: "✓ "; color: #FDD731; font-weight: 700; }}
        .btn {{ display: inline-block; padding: 12px 30px; background: #FDD731; color: #020203; border: none; border-radius: 6px; cursor: pointer; font-weight: 700; text-decoration: none; }}
        .btn:hover {{ background: #FFC500; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Planes de Espejo Fantasma</h1>
        <div class="plans">
            <div class="plan">
                <div class="plan-title">BASIC</div>
                <div class="plan-price">€19 <small>/operación</small></div>
                <ul class="plan-features">
                    <li>Score de Compatibilidad</li>
                    <li>Radar 5D</li>
                </ul>
                <form action="/api/checkout" method="POST">
                    <input type="hidden" name="couple_id" value="{couple_id}">
                    <input type="hidden" name="tier" value="basic">
                    <button type="submit" class="btn">Seleccionar</button>
                </form>
            </div>

            <div class="plan featured">
                <div class="plan-title">PREMIUM</div>
                <div class="plan-price">€39 <small>/operación</small></div>
                <ul class="plan-features">
                    <li>Todas las visualizaciones</li>
                    <li>Auditoría NLP</li>
                    <li>Matriz COI</li>
                    <li>5 Quick Wins</li>
                </ul>
                <form action="/api/checkout" method="POST">
                    <input type="hidden" name="couple_id" value="{couple_id}">
                    <input type="hidden" name="tier" value="premium">
                    <button type="submit" class="btn">Seleccionar</button>
                </form>
            </div>

            <div class="plan">
                <div class="plan-title">HIGH-TICKET</div>
                <div class="plan-price">€500+ <small>/sesión</small></div>
                <ul class="plan-features">
                    <li>Sesión 1-1 con Javier</li>
                    <li>Reporte personalizado 20pp</li>
                    <li>Plan de acción trimestral</li>
                    <li>Community access</li>
                </ul>
                <form action="/api/checkout" method="POST">
                    <input type="hidden" name="couple_id" value="{couple_id}">
                    <input type="hidden" name="tier" value="high_ticket">
                    <button type="submit" class="btn">Contactar</button>
                </form>
            </div>
        </div>
    </div>
</body>
</html>
"""


if __name__ == "__main__":
    # Test
    manager = PaywallManager(stripe_api_key="sk_test_fake_key")

    print("✅ PaywallManager initialized")
    print(f"✅ Tier prices: {TIER_PRICES}")
    print(f"✅ Tier features: {TIER_FEATURES}")
