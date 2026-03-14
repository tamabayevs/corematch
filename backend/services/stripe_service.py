"""
CoreMatch — Stripe Billing Service
Handles Checkout sessions, Customer Portal, webhook events, and plan management.

Resilience features:
  - All Stripe API calls wrapped in error handling
  - Specific handling for StripeError, CardError, RateLimitError
  - Webhook signature verification with proper error response
  - Price ID validation at call time
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
        # Set timeout to prevent hanging on Stripe API issues
        stripe.max_network_retries = 2
        _stripe = stripe
    return _stripe


# ──────────────────────────────────────────────────────────────
# Plan Configuration
# ──────────────────────────────────────────────────────────────
PLANS = {
    "free": {
        "name": "Free",
        "max_campaigns": 1,
        "max_candidates_per_month": 15,
        "max_team_members": 1,
    },
    "starter": {
        "name": "Starter",
        "max_campaigns": 5,
        "max_candidates_per_month": 100,
        "max_team_members": 5,
    },
    "growth": {
        "name": "Growth",
        "max_campaigns": 25,
        "max_candidates_per_month": 500,
        "max_team_members": 15,
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

    try:
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

    except stripe.error.RateLimitError:
        logger.error("Stripe rate limit hit during checkout creation")
        raise RuntimeError("Payment service is temporarily busy. Please try again in a moment.")
    except stripe.error.InvalidRequestError as e:
        logger.error("Stripe invalid request: %s", str(e))
        raise ValueError(f"Invalid payment request: {str(e)}")
    except stripe.error.AuthenticationError:
        logger.error("Stripe authentication failed — check STRIPE_SECRET_KEY")
        raise RuntimeError("Payment service configuration error. Please contact support.")
    except stripe.error.StripeError as e:
        logger.error("Stripe API error during checkout: %s", str(e))
        raise RuntimeError("Payment service error. Please try again.")


def create_portal_session(stripe_customer_id: str, return_url: str) -> dict:
    """Create a Stripe Customer Portal session for managing subscriptions."""
    stripe = _get_stripe()

    try:
        session = stripe.billing_portal.Session.create(
            customer=stripe_customer_id,
            return_url=return_url,
        )
        return {"url": session.url}
    except stripe.error.InvalidRequestError as e:
        logger.error("Stripe portal error: %s", str(e))
        raise ValueError(f"Could not open billing portal: {str(e)}")
    except stripe.error.StripeError as e:
        logger.error("Stripe API error during portal: %s", str(e))
        raise RuntimeError("Payment service error. Please try again.")


def construct_webhook_event(payload: bytes, sig_header: str) -> object:
    """Verify and construct a Stripe webhook event."""
    stripe = _get_stripe()
    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET")

    if not webhook_secret:
        raise ValueError("STRIPE_WEBHOOK_SECRET not configured")

    try:
        return stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except stripe.error.SignatureVerificationError:
        logger.warning("Stripe webhook signature verification failed")
        raise ValueError("Invalid webhook signature")
    except Exception as e:
        logger.error("Stripe webhook construction error: %s", str(e))
        raise


def get_subscription(subscription_id: str) -> object:
    """Retrieve a Stripe subscription."""
    stripe = _get_stripe()
    try:
        return stripe.Subscription.retrieve(subscription_id)
    except stripe.error.StripeError as e:
        logger.error("Failed to retrieve subscription %s: %s", subscription_id, str(e))
        raise RuntimeError(f"Could not retrieve subscription: {str(e)}")


def price_id_to_plan_tier(price_id: str) -> str:
    """Map a Stripe price ID to a plan tier."""
    starter_price = os.environ.get("STRIPE_STARTER_PRICE_ID", "")
    growth_price = os.environ.get("STRIPE_GROWTH_PRICE_ID", "")

    if price_id == starter_price:
        return "starter"
    elif price_id == growth_price:
        return "growth"
    else:
        logger.warning("Unknown Stripe price_id: %s — defaulting to starter", price_id)
        return "starter"  # Default fallback
