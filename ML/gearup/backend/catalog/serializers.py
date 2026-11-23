from django.db.models import Avg
from rest_framework import serializers

from .models import Category, Product, ProductImage, ProductVariant, Review


class CategorySerializer(serializers.ModelSerializer):
    product_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["id", "name", "slug", "product_count"]

    def get_product_count(self, obj):
        return obj.products.filter(is_active=True).count()


class ProductImageSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ["id", "url", "alt", "is_primary"]

    def get_url(self, obj):
        request = self.context.get("request")
        if not obj.image:
            return None
        url = obj.image.url
        return request.build_absolute_uri(url) if request else url


class ProductVariantSerializer(serializers.ModelSerializer):
    price = serializers.SerializerMethodField()

    class Meta:
        model = ProductVariant
        fields = ["id", "name", "value", "price", "stock"]

    def get_price(self, obj):
        return str(obj.effective_price)


class ReviewSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Review
        fields = ["id", "username", "rating", "comment", "sentiment", "created_at"]
        read_only_fields = ["id", "sentiment", "created_at"]

    def validate_rating(self, value):
        if not 1 <= value <= 5:
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value


class ProductListSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    image = serializers.SerializerMethodField()
    search_score = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id", "name", "slug", "brand", "category", "price", "stock",
            "is_active", "is_featured", "image", "created_at", "search_score",
        ]

    def get_image(self, obj):
        primary = obj.images.filter(is_primary=True).first() or obj.images.first()
        if not primary:
            return None
        return ProductImageSerializer(primary, context=self.context).data["url"]

    def get_search_score(self, obj):
        return round(getattr(obj, "search_score", 0.0), 4)


class ProductDetailSerializer(ProductListSerializer):
    variants = ProductVariantSerializer(many=True, read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    reviews_summary = serializers.SerializerMethodField()

    class Meta(ProductListSerializer.Meta):
        fields = ProductListSerializer.Meta.fields + [
            "description", "variants", "images", "reviews_summary", "updated_at",
        ]

    def get_reviews_summary(self, obj):
        total = obj.reviews.count()
        by_sentiment = {"positive": 0, "neutral": 0, "negative": 0}
        for value in obj.reviews.exclude(sentiment="").values_list("sentiment", flat=True):
            if value in by_sentiment:
                by_sentiment[value] += 1
        avg = obj.reviews.aggregate(v=Avg("rating"))["v"]
        return {
            "total": total,
            "average_rating": round(float(avg), 2) if avg is not None else None,
            "sentiment_counts": by_sentiment,
        }
