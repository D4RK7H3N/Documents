import logging

from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import CartItem, Order
from .payments import (
    PaymentError,
    PaymentNotConfiguredError,
    create_checkout_session,
    process_webhook_event,
    verify_webhook_signature,
)
from .serializers import (
    CartItemAddSerializer,
    CartItemSerializer,
    CartItemUpdateSerializer,
    CartSerializer,
    CheckoutSerializer,
    OrderListSerializer,
    OrderSerializer,
)
from .services import CheckoutError, create_order_from_cart, get_or_create_cart

logger = logging.getLogger(__name__)


class CartView(APIView):
    """GET /api/cart/ - the current user's cart with totals."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        cart = get_or_create_cart(request.user)
        items = cart.items.select_related("product", "variant")
        data = CartSerializer({"items": list(items)}).data
        return Response(data)


class CartItemCreateView(APIView):
    """POST /api/cart/items/ - add a product (optionally a variant)."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = CartItemAddSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cart = get_or_create_cart(request.user)

        item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=serializer.validated_data["product_obj"],
            variant=serializer.validated_data["variant_obj"],
            defaults={"quantity": serializer.validated_data["quantity"]},
        )
        if not created:
            item.quantity += serializer.validated_data["quantity"]
            available = (
                item.variant.stock if item.variant_id else item.product.stock
            )
            if item.quantity > available:
                return Response(
                    {"error": f"Only {available} left in stock."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            item.save(update_fields=["quantity"])
        return Response(CartItemSerializer(item, context={"request": request}).data, status=201)


class CartItemDetailView(APIView):
    """PATCH/DELETE /api/cart/items/{id}/"""

    permission_classes = [permissions.IsAuthenticated]

    def _get_item(self, request, pk):
        return get_object_or_404(CartItem, pk=pk, cart__user=request.user)

    def patch(self, request, pk):
        item = self._get_item(request, pk)
        serializer = CartItemUpdateSerializer(
            data=request.data, context={"cart_item": item}
        )
        serializer.is_valid(raise_exception=True)
        item.quantity = serializer.validated_data["quantity"]
        item.save(update_fields=["quantity"])
        return Response(CartItemSerializer(item, context={"request": request}).data)

    def delete(self, request, pk):
        item = self._get_item(request, pk)
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CheckoutView(APIView):
    """POST /api/checkout/ - create the order transactionally and start payment."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)

        try:
            order = create_order_from_cart(
                request.user,
                payment_method=data["payment_method"],
                shipping=data,
            )
        except CheckoutError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        response_data = {
            "order_number": order.number,
            "status": order.status,
            "payment_method": order.payment_method,
            "payment_status": order.payment_status,
            "total": str(order.total),
        }

        if order.payment_method == "paymongo":
            try:
                checkout_url = create_checkout_session(order)
            except PaymentNotConfiguredError as exc:
                response_data["warning"] = str(exc)
                return Response(response_data, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            except PaymentError as exc:
                response_data["warning"] = str(exc)
                return Response(response_data, status=status.HTTP_502_BAD_GATEWAY)
            response_data["checkout_url"] = checkout_url

        return Response(response_data, status=status.HTTP_201_CREATED)


class OrderListView(APIView):
    """GET /api/orders/ - the current user's orders."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        orders = Order.objects.filter(user=request.user).prefetch_related("items")
        return Response(OrderListSerializer(orders, many=True, context={"request": request}).data)


class OrderDetailView(APIView):
    """GET /api/orders/{number}/ - order detail with status tracking."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, number):
        order = get_object_or_404(Order, number=number, user=request.user)
        return Response(OrderSerializer(order, context={"request": request}).data)


class PaymentWebhookView(APIView):
    """POST /api/payments/webhook/ - PayMongo webhook with signature verification."""

    permission_classes = []
    authentication_classes = []

    def post(self, request):
        raw_body = request.body
        signature = request.META.get("HTTP_PAYMONGO_SIGNATURE", "")
        if not verify_webhook_signature(raw_body, signature):
            logger.warning("Rejected webhook with invalid signature")
            return Response({"error": "Invalid signature."}, status=status.HTTP_400_BAD_REQUEST)

        import json

        try:
            payload = json.loads(raw_body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return Response({"error": "Invalid JSON."}, status=status.HTTP_400_BAD_REQUEST)

        order = process_webhook_event(payload)
        return Response({"received": True, "order": order.number if order else None})
