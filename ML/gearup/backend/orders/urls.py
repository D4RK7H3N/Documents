from django.urls import path

from .views import (
    CartItemCreateView,
    CartItemDetailView,
    CartView,
    CheckoutView,
    OrderDetailView,
    OrderListView,
    PaymentWebhookView,
)

urlpatterns = [
    path("cart/", CartView.as_view(), name="cart"),
    path("cart/items/", CartItemCreateView.as_view(), name="cart-item-create"),
    path("cart/items/<int:pk>/", CartItemDetailView.as_view(), name="cart-item-detail"),
    path("checkout/", CheckoutView.as_view(), name="checkout"),
    path("orders/", OrderListView.as_view(), name="orders"),
    path("orders/<str:number>/", OrderDetailView.as_view(), name="order-detail"),
    path("payments/webhook/", PaymentWebhookView.as_view(), name="payment-webhook"),
]
