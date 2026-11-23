import logging

from rest_framework import permissions, status
from rest_framework.generics import ListAPIView, get_object_or_404
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from catalog.serializers import ProductListSerializer

from .models import ChatLog  # noqa: F401  (registered below via admin)
from .services import (
    LLMError,
    LLMNotConfiguredError,
    chat_answer,
    generate_description,
    recommendations_for,
    search_products,
)

logger = logging.getLogger(__name__)


class SearchView(ListAPIView):
    """GET /api/search/?q= - semantic product search (typo tolerant)."""

    serializer_class = ProductListSerializer
    permission_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "search"

    def get_queryset(self):
        query = self.request.query_params.get("q", "")
        try:
            limit = min(int(self.request.query_params.get("limit", 12)), 24)
        except ValueError:
            limit = 12
        return search_products(query, limit=limit)


class RecommendationView(APIView):
    """GET /api/recommendations/{slug}/ - similar + customers-also-bought."""

    permission_classes = []

    def get(self, request, slug):
        from catalog.models import Product

        product = get_object_or_404(Product, slug=slug, is_active=True)
        data = recommendations_for(product)
        context = {"request": request}
        return Response(
            {
                "similar": ProductListSerializer(data["similar"], many=True, context=context).data,
                "also_bought": ProductListSerializer(
                    data["also_bought"], many=True, context=context
                ).data,
                "also_bought_fallback": data["also_bought_fallback"],
            }
        )


class ChatView(APIView):
    """POST /api/chat/ - RAG shopping assistant over the product catalog."""

    permission_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "chat"

    def post(self, request):
        message = (request.data.get("message") or "").strip()
        if not message:
            return Response({"error": "Message is required."}, status=400)
        if len(message) > 1000:
            return Response({"error": "Message too long (max 1000 chars)."}, status=400)

        try:
            result = chat_answer(request.user if request.user.is_authenticated else None, message)
        except LLMNotConfiguredError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except LLMError as exc:
            logger.exception("Chat LLM call failed")
            return Response(
                {"error": f"AI assistant error: {exc}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        return Response(result)


class DescribeView(APIView):
    """POST /api/ai/describe/ - admin-only product description generator."""

    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        name = (request.data.get("name") or "").strip()
        features = (request.data.get("features") or "").strip()
        if not name:
            return Response({"error": "Product name is required."}, status=400)

        try:
            description = generate_description(name, features)
        except LLMNotConfiguredError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except LLMError as exc:
            return Response(
                {"error": f"AI error: {exc}"}, status=status.HTTP_502_BAD_GATEWAY
            )
        return Response({"description": description})
