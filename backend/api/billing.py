"""
CoreMatch — Billing Blueprint
Endpoints: checkout, portal, webhook, plan info
"""
import os
import logging
from flask import Blueprint, request, jsonify, g
from database.connection import get_db
from api.middleware import require_auth
from services.stripe_service import (
    is_configured,
    create_checkout_session,
    create_portal_session,
    construct_webhook_event,
    price_id_to_plan_tier,
    PLANS,
)

logger = logging.getLogger(__name__)
billing_bp = Blueprint("billing", __name__)

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")


# ──────────────────────────────────────────────────────────────
# GET /api/billing/plans — Public plan info
# ──────────────────────────────────────────────────────────────
@billing_bp.route("/plans", methods=["GET"])
def get_plans():
    """Return available plans and pricing info."""
    starter_price = os.environ.get("STRIPE_STARTER_PRICE_ID", "")
    growth_price = os.environ.get("STRIPE_GROWTH_PRICE_ID", "")

    return jsonify({
        "configured": is_configured(),
        "plans": [
            {
                "tier": "free",
                "name": "Free",
                "price": 0,
                "price_id": None,
                **PLANS["free"],
            },
            {
                "tier": "starter",
                "name": "Starter",
                "price": 99,
                "price_id": starter_price or None,
                **PLANS["starter"],
            },
            {
                "tier": "growth",
                "name": "Growth",
                "price": 249,
                "price_id": growth_price or None,
                **PLANS["growth"],
            },
        ],
    }), 200


# ──────────────────────────────────────────────────────────────
# GET /api/billing/status — Current user's billing status
# ──────────────────────────────────────────────────────────────
@billing_bp.route("/status", methods=["GET"])
@require_auth
def billing_status():
    """Return current user's plan and billing info."""
    user_id = g.user_id

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT pl.plan_tier, pl.max_campaigns, pl.max_candidates_per_month,
                       pl.max_team_members, pl.current_candidates_this_month, pl.period_start,
                       u.stripe_customer_id, u.stripe_subscription_id, u.stripe_subscription_status
                FROM plan_limits pl
                JOIN users u ON u.id = pl.user_id
                WHERE pl.user_id = %s
                """,
                (user_id,),
            )
            row = cur.fetchone()

    if not row:
        return jsonify({"error": "No plan found"}), 404

    return jsonify({
        "plan_tier": row[0],
        "max_campaigns": row[1],
        "max_candidates_per_month": row[2],
        "max_team_members": row[3],
        "current_candidates_this_month": row[4],
        "period_start": row[5].isoformat() if row[5] else None,
        "has_stripe": bool(row[6]),
        "subscription_status": row[8],
    }), 200


# ──────────────────────────────────────────────────────────────
# POST /api/billing/checkout — Create Stripe Checkout session
# ──────────────────────────────────────────────────────────────
@billing_bp.route("/checkout", methods=["POST"])
@require_auth
def create_checkout():
    """Create a Stripe Checkout session for upgrading."""
    if not is_configured():
        return jsonify({"error": "Billing not configured"}), 503

    data = request.get_json(silent=True) or {}
    price_id = data.get("price_id")
    if not price_id:
        return jsonify({"error": "price_id required"}), 400

    user_id = g.user_id

    # Get user email and existing Stripe customer ID
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT email, stripe_customer_id FROM users WHERE id = %s",
                (user_id,),
            )
            user = cur.fetchone()

    if not user:
        return jsonify({"error": "User not found"}), 404

    email, stripe_customer_id = user[0], user[1]

    try:
        result = create_checkout_session(
            user_id=user_id,
            email=email,
            price_id=price_id,
            stripe_customer_id=stripe_customer_id,
            success_url=FRONTEND_URL + "/dashboard/settings?billing=success",
            cancel_url=FRONTEND_URL + "/dashboard/settings?billing=cancelled",
        )
        return jsonify(result), 200
    except Exception as e:
        logger.error("Stripe checkout error: %s", str(e))
        return jsonify({"error": "Failed to create checkout session"}), 500


# ──────────────────────────────────────────────────────────────
# POST /api/billing/portal — Create Stripe Customer Portal session
# ──────────────────────────────────────────────────────────────
@billing_bp.route("/portal", methods=["POST"])
@require_auth
def create_portal():
    """Create a Stripe Customer Portal session for managing subscription."""
    if not is_configured():
        return jsonify({"error": "Billing not configured"}), 503

    user_id = g.user_id

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT stripe_customer_id FROM users WHERE id = %s",
                (user_id,),
            )
            row = cur.fetchone()

    if not row or not row[0]:
        return jsonify({"error": "No billing account found. Please subscribe first."}), 404

    try:
        result = create_portal_session(
            stripe_customer_id=row[0],
            return_url=FRONTEND_URL + "/dashboard/settings",
        )
        return jsonify(result), 200
    except Exception as e:
        logger.error("Stripe portal error: %s", str(e))
        return jsonify({"error": "Failed to create portal session"}), 500


# ──────────────────────────────────────────────────────────────
# POST /api/billing/webhook — Stripe webhook handler
# ──────────────────────────────────────────────────────────────
@billing_bp.route("/webhook", methods=["POST"])
def stripe_webhook():
    """Handle Stripe webhook events."""
    payload = request.get_data()
    sig_header = request.headers.get("Stripe-Signature")

    if not sig_header:
        return jsonify({"error": "Missing signature"}), 400

    try:
        event = construct_webhook_event(payload, sig_header)
    except ValueError:
        return jsonify({"error": "Invalid payload"}), 400
    except Exception as e:
        logger.error("Webhook signature verification failed: %s", str(e))
        return jsonify({"error": "Invalid signature"}), 400

    event_type = event["type"]
    data = event["data"]["object"]

    logger.info("Stripe webhook: %s", event_type)

    try:
        if event_type == "checkout.session.completed":
            _handle_checkout_completed(data)
        elif event_type == "customer.subscription.updated":
            _handle_subscription_updated(data)
        elif event_type == "customer.subscription.deleted":
            _handle_subscription_deleted(data)
        elif event_type == "invoice.payment_failed":
            _handle_payment_failed(data)
    except Exception as e:
        logger.error("Webhook handler error for %s: %s", event_type, str(e))
        # Return 200 anyway to prevent Stripe retries on application errors
        return jsonify({"status": "error", "message": str(e)}), 200

    return jsonify({"status": "ok"}), 200


# ──────────────────────────────────────────────────────────────
# Webhook Handlers
# ──────────────────────────────────────────────────────────────
def _handle_checkout_completed(session):
    """Handle successful checkout — link customer + subscription to user, upgrade plan."""
    user_id = session.get("metadata", {}).get("user_id")
    if not user_id:
        logger.warning("Checkout completed without user_id in metadata")
        return

    customer_id = session.get("customer")
    subscription_id = session.get("subscription")

    if not subscription_id:
        logger.warning("Checkout completed without subscription for user %s", user_id)
        return

    # Get subscription to determine plan tier
    from services.stripe_service import get_subscription
    subscription = get_subscription(subscription_id)
    price_id = subscription["items"]["data"][0]["price"]["id"]
    plan_tier = price_id_to_plan_tier(price_id)
    plan_config = PLANS.get(plan_tier, PLANS["starter"])

    with get_db() as conn:
        with conn.cursor() as cur:
            # Update user with Stripe IDs
            cur.execute(
                """
                UPDATE users
                SET stripe_customer_id = %s,
                    stripe_subscription_id = %s,
                    stripe_subscription_status = 'active'
                WHERE id = %s
                """,
                (customer_id, subscription_id, user_id),
            )

            # Upgrade plan limits
            cur.execute(
                """
                UPDATE plan_limits
                SET plan_tier = %s,
                    max_campaigns = %s,
                    max_candidates_per_month = %s,
                    max_team_members = %s
                WHERE user_id = %s
                """,
                (
                    plan_tier,
                    plan_config["max_campaigns"],
                    plan_config["max_candidates_per_month"],
                    plan_config["max_team_members"],
                    user_id,
                ),
            )

    logger.info("User %s upgraded to %s plan", user_id, plan_tier)


def _handle_subscription_updated(subscription):
    """Handle subscription changes (plan change, status change)."""
    subscription_id = subscription.get("id")
    status = subscription.get("status")
    price_id = subscription["items"]["data"][0]["price"]["id"]
    plan_tier = price_id_to_plan_tier(price_id)
    plan_config = PLANS.get(plan_tier, PLANS["starter"])

    with get_db() as conn:
        with conn.cursor() as cur:
            # Find user by subscription ID
            cur.execute(
                "SELECT id FROM users WHERE stripe_subscription_id = %s",
                (subscription_id,),
            )
            row = cur.fetchone()
            if not row:
                logger.warning("No user found for subscription %s", subscription_id)
                return

            user_id = str(row[0])

            # Update subscription status
            cur.execute(
                "UPDATE users SET stripe_subscription_status = %s WHERE id = %s",
                (status, user_id),
            )

            # Update plan if subscription is active
            if status == "active":
                cur.execute(
                    """
                    UPDATE plan_limits
                    SET plan_tier = %s,
                        max_campaigns = %s,
                        max_candidates_per_month = %s,
                        max_team_members = %s
                    WHERE user_id = %s
                    """,
                    (
                        plan_tier,
                        plan_config["max_campaigns"],
                        plan_config["max_candidates_per_month"],
                        plan_config["max_team_members"],
                        user_id,
                    ),
                )

    logger.info("Subscription %s updated: status=%s tier=%s", subscription_id, status, plan_tier)


def _handle_subscription_deleted(subscription):
    """Handle subscription cancellation — downgrade to free."""
    subscription_id = subscription.get("id")
    free_config = PLANS["free"]

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM users WHERE stripe_subscription_id = %s",
                (subscription_id,),
            )
            row = cur.fetchone()
            if not row:
                return

            user_id = str(row[0])

            cur.execute(
                """
                UPDATE users
                SET stripe_subscription_status = 'cancelled',
                    stripe_subscription_id = NULL
                WHERE id = %s
                """,
                (user_id,),
            )

            cur.execute(
                """
                UPDATE plan_limits
                SET plan_tier = 'free',
                    max_campaigns = %s,
                    max_candidates_per_month = %s,
                    max_team_members = %s
                WHERE user_id = %s
                """,
                (
                    free_config["max_campaigns"],
                    free_config["max_candidates_per_month"],
                    free_config["max_team_members"],
                    user_id,
                ),
            )

    logger.info("Subscription %s deleted — user %s downgraded to free", subscription_id, user_id)


def _handle_payment_failed(invoice):
    """Handle failed payment — log it, Stripe handles dunning emails."""
    customer_id = invoice.get("customer")
    logger.warning("Payment failed for customer %s", customer_id)
