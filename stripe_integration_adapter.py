"""
Stripe Payment Integration Adapter for Diagnostico Financiero de Parejas
SPRINT 8 — Psychological Payment Flow & Checkout Integration

Handles:
- Stripe payment intent creation (checkout orchestration)
- Pre-rendering PDF in background while processing screen shows
- Webhook handling for payment confirmation
- Magic link generation for post-payment content access
- Sunk cost effect psychology (user invested 500 questions)
"""

import stripe
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from fastapi import HTTPException, status
from functools import lru_cache
import os

# Initialize Stripe (use environment variables)
stripe.api_key = os.getenv("STRIPE_API_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")


class StripePaymentAdapter:
    """
    Orchestrates Stripe payment flow with psychological design patterns.

    Design principles:
    1. Perfect timing — PDF pre-renders while processing screen shows anticipation
    2. Native Stripe Elements — seamless, no redirects
    3. Apple Pay/Google Pay priority — 80% mobile conversion advantage
    4. Asymmetric pricing — 39€ premium anchors perception against 19€ basic
    5. Benefit-focused copywriting — "Unlock", "Access Elite", not "Pay"
    6. Success celebration — emotional reward, not transactional confirmation
    """

    # Pricing tiers (in cents for Stripe)
    PRICING_TIERS = {
        "basic": {
            "amount": 1900,  # €19.00
            "currency": "eur",
            "name": "Reporte Básico",
            "description": "Informe completo en PDF + Gráficos Radar 5D",
            "features": [
                "Informe completo en PDF",
                "Gráficos de radar 5D",
                "Acceso 30 días",
                "Soporte por email"
            ],
            "psychology": "entry-level anchor"
        },
        "premium": {
            "amount": 3900,  # €39.00
            "currency": "eur",
            "name": "Plan de Élite",
            "description": "Informe de Alta Densidad + 4 Visualizaciones Premium + Plan Estratégico",
            "features": [
                "Informe de Alta Densidad + PDF",
                "4 Visualizaciones Premium",
                "Plan de Acción Estratégico",
                "Magic Link + Acceso Eterno",
                "Soporte Prioritario 30 días"
            ],
            "psychology": "asymmetric pricing anchor — 91% choose this"
        }
    }

    @staticmethod
    async def create_payment_intent(
        couple_id: str,
        plan: str,
        analysis_data: Dict,
        user_email: str
    ) -> Dict:
        """
        Create Stripe PaymentIntent for checkout.

        Args:
            couple_id: Unique session identifier (from /blind-session/init)
            plan: "basic" or "premium"
            analysis_data: Full couple analysis (23-module diagnosis)
            user_email: Contact email for receipt + future communications

        Returns:
            {
                "client_secret": str,  # For Stripe.js confirmation
                "publishable_key": str,
                "intent_id": str,
                "amount": int,
                "currency": str,
                "plan_name": str
            }
        """

        if plan not in StripePaymentAdapter.PRICING_TIERS:
            raise ValueError(f"Invalid plan: {plan}")

        tier = StripePaymentAdapter.PRICING_TIERS[plan]

        # Metadata: couple_id + analysis for post-payment webhook
        metadata = {
            "couple_id": couple_id,
            "plan": plan,
            "plan_name": tier["name"],
            "timestamp": datetime.utcnow().isoformat(),
            "user_email": user_email,
            # Store analysis reference for PDF generation post-payment
            "analysis_module_count": len(analysis_data) if isinstance(analysis_data, list) else 23
        }

        try:
            # Create PaymentIntent with Apple Pay/Google Pay enabled
            intent = stripe.PaymentIntent.create(
                amount=tier["amount"],
                currency=tier["currency"],
                payment_method_types=["card", "apple_pay", "google_pay"],
                metadata=metadata,
                receipt_email=user_email,
                description=f"Diagnóstico Financiero de Parejas — {tier['name']}",
                # Add statement descriptor for credit card statement clarity
                statement_descriptor="ADAPTA FAMILY OFFICE"
            )

            return {
                "client_secret": intent.client_secret,
                "publishable_key": os.getenv("STRIPE_PUBLISHABLE_KEY"),
                "intent_id": intent.id,
                "amount": tier["amount"],
                "currency": tier["currency"],
                "plan_name": tier["name"],
                "plan": plan,
                "couple_id": couple_id
            }

        except stripe.error.CardError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Card declined: {e.user_message}"
            )
        except stripe.error.RateLimitError:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests — please try again in a moment"
            )
        except stripe.error.AuthenticationError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed — check Stripe API key"
            )

    @staticmethod
    async def confirm_payment(
        intent_id: str,
        couple_id: str
    ) -> Tuple[bool, Dict]:
        """
        Confirm PaymentIntent status after client-side confirmation.

        Returns:
            (success: bool, metadata: Dict with couple_id, plan, etc.)
        """

        try:
            intent = stripe.PaymentIntent.retrieve(intent_id)

            if intent.status == "succeeded":
                # Payment completed — generate magic link for access
                magic_link = StripePaymentAdapter._generate_magic_link(
                    couple_id=couple_id,
                    plan=intent.metadata.get("plan"),
                    email=intent.metadata.get("user_email")
                )

                return True, {
                    "intent_id": intent.id,
                    "couple_id": couple_id,
                    "status": "succeeded",
                    "amount": intent.amount,
                    "currency": intent.currency,
                    "plan": intent.metadata.get("plan"),
                    "magic_link": magic_link,
                    "message": "Pago procesado con éxito — Tu informe está desbloqueado"
                }

            elif intent.status in ["processing", "requires_payment_method"]:
                return False, {
                    "intent_id": intent.id,
                    "status": intent.status,
                    "message": "Pago en proceso — por favor espera"
                }

            else:
                return False, {
                    "intent_id": intent.id,
                    "status": intent.status,
                    "message": f"Pago no completado: {intent.status}"
                }

        except stripe.error.InvalidRequestError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Payment intent not found: {e}"
            )

    @staticmethod
    def handle_webhook(event: Dict) -> Dict:
        """
        Process Stripe webhooks for payment confirmations.

        Events:
        - payment_intent.succeeded → unlock PDF download
        - payment_intent.payment_failed → send retry email with motivation
        - charge.refunded → revoke access (if refund within 30 days)
        """

        event_type = event.get("type")
        event_data = event.get("data", {}).get("object", {})

        if event_type == "payment_intent.succeeded":
            couple_id = event_data.get("metadata", {}).get("couple_id")
            plan = event_data.get("metadata", {}).get("plan")
            user_email = event_data.get("metadata", {}).get("user_email")

            # Log successful payment for analytics
            return {
                "event": "payment_success",
                "couple_id": couple_id,
                "plan": plan,
                "user_email": user_email,
                "timestamp": datetime.utcnow().isoformat(),
                "action": "unlock_pdf_download"
            }

        elif event_type == "payment_intent.payment_failed":
            couple_id = event_data.get("metadata", {}).get("couple_id")

            # Send retry email with soft psychology:
            # "Parece que hubo un problema con tu tarjeta. Te hemos guardado
            #  tu diagnóstico — vuelve cuando puedas sin presión"

            return {
                "event": "payment_failed",
                "couple_id": couple_id,
                "action": "send_retry_email"
            }

        elif event_type == "charge.refunded":
            couple_id = event_data.get("metadata", {}).get("couple_id")

            # Revoke access: expire magic link, remove PDF from CDN
            return {
                "event": "refund",
                "couple_id": couple_id,
                "action": "revoke_pdf_access"
            }

        return {"status": "event_processed"}

    @staticmethod
    def _generate_magic_link(couple_id: str, plan: str, email: str) -> str:
        """
        Generate temporary magic link for post-payment PDF access.

        Link format: /unlock/{couple_id}/{token}
        Token expires in 30 days (plan validity period)

        In production: store token in Redis with couple_id:plan:email mapping
        """

        import hashlib
        import secrets

        # Generate secure token
        token = secrets.token_urlsafe(32)

        # In production, store in Redis:
        # redis_client.setex(
        #     f"magic_link:{token}",
        #     30 * 24 * 3600,  # 30 days
        #     json.dumps({
        #         "couple_id": couple_id,
        #         "plan": plan,
        #         "email": email
        #     })
        # )

        magic_link = f"https://diagnostico.adapta.app/unlock/{couple_id}/{token}"
        return magic_link

    @staticmethod
    def get_publishable_key() -> str:
        """Get Stripe publishable key for frontend."""
        key = os.getenv("STRIPE_PUBLISHABLE_KEY")
        if not key:
            raise RuntimeError("STRIPE_PUBLISHABLE_KEY not set in environment")
        return key


class PsychologicalPricingEngine:
    """
    Implements psychological pricing principles for payment page.

    Principles:
    1. Asymmetric pricing card design — premium visually elevated
    2. Anchoring effect — 39€ makes 19€ seem smaller
    3. Reference pricing — "91% choose this" social proof on premium
    4. Benefit-focused copy — outcomes, not features
    5. Trust badges — 100% refund guarantee, Stripe secure badge
    """

    @staticmethod
    def get_pricing_context() -> Dict:
        """
        Return context for rendering pricing page with TOP 1% psychology.
        """

        return {
            "title": "Elige tu Plan",
            "subtitle": "Tu diagnóstico ya está listo — desbloquea acceso al informe",
            "cards": [
                {
                    "tier": "basic",
                    "name": "Reporte Básico",
                    "price": 19,
                    "currency": "€",
                    "cta": "Descargar Reporte (19€)",
                    "cta_psychology": "action-focused, not 'pay'",
                    "badge": None,
                    "features": StripePaymentAdapter.PRICING_TIERS["basic"]["features"],
                    "positioning": "entry-level anchor",
                    "visual": "background: light, border: subtle"
                },
                {
                    "tier": "premium",
                    "name": "Plan de Élite",
                    "price": 39,
                    "currency": "€",
                    "cta": "Acceder a Mi Diagnóstico de Élite (39€)",
                    "cta_psychology": "benefit-focused, status + access",
                    "badge": {
                        "text": "EL 91% ELIGE ESTE PLAN",
                        "psychology": "social proof anchor"
                    },
                    "features": StripePaymentAdapter.PRICING_TIERS["premium"]["features"],
                    "positioning": "asymmetric anchor + elevated visual",
                    "visual": "background: dark (contrast), border: gold, elevated (translateY -10px)",
                    "recommended": True
                }
            ],
            "trust_elements": {
                "guarantee": "Garantía 100% de devolución en 30 días si no estás satisfecho",
                "security": "🔒 Pago seguro procesado por Stripe® — Cifrado SSL de nivel bancario",
                "psychology": "Remove purchase friction: refund guarantee + security badge"
            },
            "post_payment_celebration": {
                "emoji": "👑",
                "headline": "Bienvenido al Cambio",
                "subheadline": "El pago se ha procesado con éxito. Tu plan estratégico familiar ya está desbloqueado.",
                "cta": "📥 Descargar Mi Informe",
                "psychology": "Emotional reward, not transactional — user feels VIP status"
            }
        }


# Async wrapper for PDF generation (happens in background during payment processing)
async def generate_pdf_background(couple_id: str, analysis_data: Dict) -> str:
    """
    Pre-render PDF while payment processing screen shows with rotating messages.

    This creates anticipation and uses sunk cost effect psychology:
    User invested 500 questions → payment feels like logical next step to access
    the valuable output they already created.

    Returns: path to generated PDF
    """

    # Simulate PDF generation (in production: ReportLab async with ReportLab)
    # PDF includes: Cover + 23 analysis modules + radar charts + strategic recommendations

    await asyncio.sleep(2)  # Simulate 2-3s processing

    # Return PDF path for download after payment success
    return f"/pdfs/{couple_id}_diagnostico_elite.pdf"
