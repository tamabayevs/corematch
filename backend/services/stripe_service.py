"""
CoreMatch — Stripe Billing Service
Handles Checkout sessions, Customer Portal, webhook events, and plan management.
"""
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Lazy-import stripe to avoid hard dependency if not configured
_stripe = None


def _get_stripe():
    global _stripe
    if _stripe is None:
        import stripe
        stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")
        _stripe = stripe
    return _stripe


# ──────────────────────────────────────────────────────────────
# Plan Configuration
# ──────────────────────────────────────────────────────────────
PLANS = {
    "free": {
        "name": "Free",
        "max_campaigns": 1,
        "max_candidates_per_month": 10,
        "max_team_members": 1,
    },
    "starter": {
        "name": "Starter",
        "max_campaigns": 3,
        "max_candidates_per_month": 50,
        "max_team_members": 3,
    },
    "growth": {
        "name": "Growth",
        "max_campaigns": 10,
        "max_candidates_per_month": 200,
        "max_team_members": 10,
    },
    "enterprise": {
        "name": "Enterprise",
        "max_campaigns": 999,
        "max_candidates_per_month": 9999,
        "max_team_members": 999,
    },
}


def is_configured() -> bool:
    """Check if Stripe is configured."""
    return bool(os.environ.get("STRIPE_SECRET_KEY"))


def create_checkout_session(
    user_id: str,
    email: str,
    price_id: str,
    success_url: str,
    cancel_url: str,
    stripe_customer_id: Optional[str] = None,
) -> dict:
    """Create a Stripe Checkout session for a subscription."""
    stripe = _get_stripe()

    params = {
        "mode": "subscription",
        "payment_method_types": ["card"],
        "line_items": [{"price": price_id, "quantity": 1}],
        "success_url": success_url,
        "cancel_url": cancel_url,
        "metadata": {"user_id": user_id},
        "allow_promotion_codes": True,
    }

    if stripe_customer_id:
        params["customer"] = stripe_customer_id
    else:
        params["customer_email"] = email

    session = stripe.checkout.Session.create(**params)
    return {"session_id": session.id, "url": session.url}


def create_portal_session(stripe_customer_id: str, return_url: str) -> dict:
    """Create a Stripe Customer Portal session for managing subscriptions."""
    stripe = _get_stripe()
    session = stripe.billing_portal.Session.create(
        customer=stripe_customer_id,
        return_url=return_url,
    )
    return {"url": session.url}


def construct_webhook_event(payload: bytes, sig_header: str) -> object:
    """Verify and construct a Stripe webhook event."""
    stripe = _get_stripe()
    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET")
    return stripe.Webhook.construct_event(payload, sig_header, webhook_secret)


def get_subscription(subscription_id: str) -> object:
    """Retrieve a Stripe subscription."""
    stripe = _get_stripe()
    return stripe.Subscription.retrieve(subscription_id)


def price_id_to_plan_tier(price_id: str) -> str:
    """Map a Stripe price ID to a plan tier."""
    starter_price = os.environ.get("STRIPE_STARTER_PRICE_ID", "")
    growth_price = os.environ.get("STRIPE_GROWTH_PRICE_ID", "")

    if price_id == starter_price:
        return "starter"
    elif price_id == growth_price:
        return "growth"
    else:
        return "starter"  # Default fallback
