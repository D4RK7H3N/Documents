import logging
import uuid
from datetime import datetime
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.db.models import F

from catalog.models import Product, ProductVariant

from .models import Cart, CartItem, Order, OrderItem

logger = logging.getLogger(__name__)


class CheckoutError(Exception):
    """Raised when the cart cannot be turned into an order."""


def get_or_create_cart(user) -> Cart:
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


def generate_order_number() -> str:
    stamp = datetime.now().strftime("%Y%m%d")
    return f"ORD-{stamp}-{uuid.uuid4().hex[:8].upper()}"


def create_order_from_cart(user, *, payment_method: str, shipping: dict) -> Order:
    """Turn the user's cart into an order.

    Transactional guarantees:
      - Server-side prices only (never trust the client).
      - Stock is validated and decremented with a conditional UPDATE
        (stock >= quantity) inside a transaction, so two concurrent
        checkouts can never oversell the same unit: if any line fails,
        the whole transaction rolls back.
      - The cart is cleared only after the order is safely created.
    """
    cart = getattr(user, "cart", None)
    if cart is None or not cart.items.exists():
        raise CheckoutError("Your cart is empty.")

    with transaction.atomic():
        items = list(cart.items.select_related("product", "variant"))
        subtotal = Decimal("0.00")
        lines = []

        for item in items:
            product = item.product
            if not product.is_active:
                raise CheckoutError(f"'{product.name}' is no longer available.")

            if item.variant_id:
                variant = item.variant
                unit_price = variant.effective_price
                variant_label = f"{variant.name}: {variant.value}"
            else:
                unit_price = product.price
                variant_label = ""

            if item.quantity < 1:
                raise CheckoutError("Invalid quantity in cart.")
            subtotal += unit_price * item.quantity
            lines.append((item, unit_price, variant_label))

        shipping_fee = settings.SHOP_SHIPPING_FEE
        total = subtotal + shipping_fee

        order = Order.objects.create(
            number=generate_order_number(),
            user=user,
            status="pending",
            payment_method=payment_method,
            payment_status="unpaid",
            subtotal=subtotal,
            shipping_fee=shipping_fee,
            total=total,
            shipping_name=shipping["shipping_name"],
            shipping_phone=shipping["shipping_phone"],
            shipping_address=shipping["shipping_address"],
            shipping_city=shipping["shipping_city"],
            shipping_postal_code=shipping["shipping_postal_code"],
            notes=shipping.get("notes", ""),
        )

        for item, unit_price, variant_label in lines:
            if item.variant_id:
                updated = ProductVariant.objects.filter(
                    pk=item.variant_id, stock__gte=item.quantity
                ).update(stock=F("stock") - item.quantity)
            else:
                updated = Product.objects.filter(
                    pk=item.product_id, stock__gte=item.quantity
                ).update(stock=F("stock") - item.quantity)

            if updated != 1:
                name = item.variant.product.name if item.variant_id else item.product.name
                raise CheckoutError(f"Insufficient stock for '{name}'.")

            OrderItem.objects.create(
                order=order,
                product=item.product,
                variant=item.variant,
                product_name=item.product.name,
                variant_label=variant_label,
                unit_price=unit_price,
                quantity=item.quantity,
                line_total=unit_price * item.quantity,
            )

        if payment_method == "cod":
            order.status = "processing"
            order.save(update_fields=["status", "updated_at"])

        cart.items.all().delete()

    logger.info("Order %s created for user %s (%s)", order.number, user, payment_method)
    return order
