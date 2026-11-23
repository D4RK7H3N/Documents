import logging

from django.db.models import Q
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Category, Product, Review
from .serializers import (
    CategorySerializer,
    ProductDetailSerializer,
    ProductListSerializer,
    ReviewSerializer,
)

logger = logging.getLogger(__name__)

SORT_OPTIONS = {
    "price_asc": "price",
    "price_desc": "-price",
    "newest": "-created_at",
    "name": "name",
}


class CategoryListView(generics.ListAPIView):
    """GET /api/categories/"""

    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = []


class ProductListView(generics.ListAPIView):
    """GET /api/products/ with filters and sorting.

    Query params: category (slug), q (keyword search), min_price, max_price,
    in_stock (true/false), featured (true/false), sort (price_asc,
    price_desc, newest, name).
    """

    serializer_class = ProductListSerializer
    permission_classes = []

    def get_queryset(self):
        queryset = Product.objects.filter(is_active=True).select_related("category")
        params = self.request.query_params

        category = params.get("category")
        if category:
            queryset = queryset.filter(category__slug=category)

        q = params.get("q")
        if q:
            queryset = queryset.filter(
                Q(name__icontains=q) | Q(description__icontains=q) | Q(brand__icontains=q)
            )

        min_price = params.get("min_price")
        if min_price:
            try:
                queryset = queryset.filter(price__gte=float(min_price))
            except ValueError:
                pass

        max_price = params.get("max_price")
        if max_price:
            try:
                queryset = queryset.filter(price__lte=float(max_price))
            except ValueError:
                pass

        if params.get("in_stock") in ("true", "1"):
            queryset = queryset.filter(stock__gt=0)

        if params.get("featured") in ("true", "1"):
            queryset = queryset.filter(is_featured=True)

        return queryset.order_by(SORT_OPTIONS.get(params.get("sort"), "-created_at"))


class ProductDetailView(generics.RetrieveAPIView):
    """GET /api/products/{slug}/"""

    queryset = Product.objects.filter(is_active=True).select_related("category")
    serializer_class = ProductDetailSerializer
    permission_classes = []
    lookup_field = "slug"


class ReviewListCreateView(generics.ListCreateAPIView):
    """GET/POST /api/products/{slug}/reviews/"""

    serializer_class = ReviewSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [permissions.IsAuthenticated()]
        return []

    def get_product(self):
        return generics.get_object_or_404(
            Product, slug=self.kwargs["slug"], is_active=True
        )

    def get_queryset(self):
        return self.get_product().reviews.select_related("user")

    def perform_create(self, serializer):
        product = self.get_product()
        if Review.objects.filter(product=product, user=self.request.user).exists():
            raise serializers.ValidationError(
                "You have already reviewed this product."
            )
        sentiment = ""
        try:
            from ai import services

            result = services.classify_sentiment(serializer.validated_data["comment"])
            sentiment = result["sentiment"]
        except Exception:
            logger.exception("Sentiment classification failed; saving without it.")
        serializer.save(product=product, user=self.request.user, sentiment=sentiment)
