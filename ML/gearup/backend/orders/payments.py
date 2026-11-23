"""PayMongo integration (test mode).

PayMongo API: https://developers.paymongo.com
- Checkout Sessions are created with Basic auth (base64 of "SECRET_KEY:").
- Amounts are integers in centavos (PHP * 100).
- Webhooks are signed with the PayMongo-Signature header:
  "t=<timestamp>,te=<hmac-for-test-keys>" (or "li=" for live keys),
  where hmac = HMAC-SHA256(webhook_secret, f"{t}.{raw_body}").
"""
import base64
import hashlib
import hmac
import json
import logging

import requests
from django.conf import settings

from .models import Order

logger = logging.getLogger(__name__)

PAID_EVENTS = {"payment.paid", "checkout.session.payment_paid"}


class PaymentNotConfiguredError(Exception):
    pass


class PaymentError(Exception):
    pass


def _auth_header():
    secret = settings.PAYMONGO_SECRET_KEY
    if not secret:
        raise PaymentNotConfiguredError(
            "Payments are not configured (set PAYMONGO_SECRET_KEY in .env). "
            "You can still order with Cash on delivery."
        )
    return "Basic " + base64.b64encode(secret.encode()).decode()


def create_checkout_session(order: Order) -> str:
    """Create a PayMongo Checkout Session and return its checkout URL."""
    line_items = [
        {
            "currency": "PHP",
            "name": (
                f"{item.product_name}"
                + (f" ({item.variant_label})" if item.variant_label else "")
            ),
            "amount": int(item.unit_price * 100) * item.quantity,
            "quantity": 1,
        }
        for item in order.items.all()
    ]
    if order.shipping_fee > 0:
        line_items.append(
            {
                "currency": "PHP",
                "name": "Shipping fee",
                "amount": int(order.shipping_fee * 100),
                "quantity": 1,
            }
        )

    payload = {
        "data": {
            "attributes": {
                "line_items": line_items,
                "payment_method_types": ["card", "gcash", "grab_pay", "paymaya"],
                "success_url": f"{settings.FRONTEND_URL}/orders/{order.number}?paid=1",
                "cancel_url": f"{settings.FRONTEND_URL}/checkout?canceled=1",
                "reference_number": order.number,
                "metadata": {"order_number": order.number},
            }
        }
    }

    try:
        response = requests.post(
            f"{settings.PAYMONGO_API_URL}/checkout_sessions",
            json=payload,
            headers={
                "Authorization": _auth_header(),
                "Content-Type": "application/json",
            },
            timeout=15,
        )
    except requests.RequestException as exc:
        raise PaymentError(f"Could not reach PayMongo: {exc}") from exc

    if response.status_code >= 400:
        logger.error("PayMongo error %s: %s", response.status_code, response.text[:500])
        raise PaymentError("PayMongo rejected the checkout session.")

    attributes = response.json().get("data", {}).get("attributes", {})
    checkout_url = attributes.get("checkout_url")
    session_id = response.json().get("data", {}).get("id", "")
    if not checkout_url:
        raise PaymentError("PayMongo did not return a checkout URL.")

    order.paymongo_session_id = session_id
    order.save(update_fields=["paymongo_session_id", "updated_at"])
    return checkout_url


def verify_webhook_signature(raw_body: bytes, signature_header: str) -> bool:
    """Validate the PayMongo-Signature header against the raw request body."""
    secret = settings.PAYMONGO_WEBHOOK_SECRET
    if not secret or not signature_header:
        return False
    try:
        parts = dict(
            piece.split("=", 1) for piece in signature_header.split(",") if "=" in piece
        )
        timestamp = parts["t"]
        provided = parts.get("te") or parts.get("li")
        if not provided:
            return False
    except (ValueError, KeyError):
        return False

    expected = hmac.new(
        secret.encode(), f"{timestamp}.".encode() + raw_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, provided)


def _find_metadata_order_number(node, depth=0):
    """Defensively search a webhook payload for metadata.order_number."""
    if depth > 6 or not isinstance(node, dict):
        return None
    metadata = node.get("metadata")
    if isinstance(metadata, dict) and metadata.get("order_number"):
        return str(metadata["order_number"])
    for value in node.values():
        found = _find_metadata_order_number(value, depth + 1)
        if found:
            return found
    return None


def process_webhook_event(payload: dict):
    """Mark the matching order as paid for a payment.paid webhook event.

    Returns the order (or None if no order matched).
    """
    data = payload.get("data", {}) or {}
    attributes = data.get("attributes", {}) or {}
    event_type = data.get("type") or attributes.get("type") or ""

    if event_type not in PAID_EVENTS:
        logger.info("Ignoring webhook event type: %s", event_type or "<unknown>")
        return None

    order_number = _find_metadata_order_number(payload)
    session_id = data.get("id") or ""
    order = None

    if order_number:
        order = Order.objects.filter(number=order_number).first()
    if order is None and session_id:
        order = Order.objects.filter(paymongo_session_id=session_id).first()

    if order is None:
        logger.warning("Webhook %s matched no order", session_id or event_type)
        return None

    order.payment_status = "paid"
    if order.status in ("pending",):
        order.status = "paid"
    order.save(update_fields=["payment_status", "status", "updated_at"])
    logger.info("Order %s marked paid via webhook", order.number)
    return order
