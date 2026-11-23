from rest_framework import serializers

from catalog.models import Product, ProductVariant

from .models import CartItem, Order, OrderItem


class CartItemSerializer(serializers.ModelSerializer):
    product_slug = serializers.CharField(source="product.slug", read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)
    image = serializers.SerializerMethodField()
    variant_label = serializers.SerializerMethodField()
    unit_price = serializers.SerializerMethodField()
    line_total = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = [
            "id", "product", "product_slug", "product_name", "variant",
            "variant_label", "image", "quantity", "unit_price", "line_total",
        ]

    def get_image(self, obj):
        request = self.context.get("request")
        primary = obj.product.images.filter(is_primary=True).first() or obj.product.images.first()
        if not primary:
            return None
        url = primary.image.url
        return request.build_absolute_uri(url) if request else url

    def get_variant_label(self, obj):
        if not obj.variant_id:
            return ""
        return f"{obj.variant.name}: {obj.variant.value}"

    def get_unit_price(self, obj):
        return str(obj.unit_price)

    def get_line_total(self, obj):
        return str(obj.line_total)


class CartSerializer(serializers.Serializer):
    items = CartItemSerializer(many=True, read_only=True)
    subtotal = serializers.SerializerMethodField()
    shipping_fee = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()

    def get_subtotal(self, data):
        from decimal import Decimal

        items = data["items"]
        if not items:
            return "0.00"
        return str(sum((item.line_total for item in items), Decimal("0.00")))

    def get_shipping_fee(self, data):
        from django.conf import settings

        return str(settings.SHOP_SHIPPING_FEE)

    def get_total(self, data):
        from decimal import Decimal

        subtotal = Decimal(self.get_subtotal(data))
        return str(subtotal + Decimal(self.get_shipping_fee(data)))


class CartItemAddSerializer(serializers.Serializer):
    product = serializers.SlugField()
    variant = serializers.IntegerField(required=False, allow_null=True)
    quantity = serializers.IntegerField(min_value=1, max_value=99, default=1)

    def validate(self, attrs):
        product = Product.objects.filter(slug=attrs["product"], is_active=True).first()
        if product is None:
            raise serializers.ValidationError({"product": "Product not found."})

        variant = None
        if attrs.get("variant"):
            variant = ProductVariant.objects.filter(
                pk=attrs["variant"], product=product
            ).first()
            if variant is None:
                raise serializers.ValidationError({"variant": "Variant not found for this product."})

        available = variant.stock if variant is not None else product.stock
        if available < attrs["quantity"]:
            raise serializers.ValidationError(
                {"quantity": f"Only {available} left in stock."}
            )
        attrs["product_obj"] = product
        attrs["variant_obj"] = variant
        return attrs


class CartItemUpdateSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1, max_value=99)

    def validate_quantity(self, value):
        cart_item = self.context["cart_item"]
        available = (
            cart_item.variant.stock if cart_item.variant_id else cart_item.product.stock
        )
        if value > available:
            raise serializers.ValidationError(f"Only {available} left in stock.")
        return value


class CheckoutSerializer(serializers.Serializer):
    payment_method = serializers.ChoiceField(choices=[("cod", "COD"), ("paymongo", "PayMongo")])
    shipping_name = serializers.CharField(max_length=120)
    shipping_phone = serializers.CharField(max_length=32)
    shipping_address = serializers.CharField(max_length=255)
    shipping_city = serializers.CharField(max_length=100)
    shipping_postal_code = serializers.CharField(max_length=16)
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class OrderItemSerializer(serializers.ModelSerializer):
    product_slug = serializers.CharField(source="product.slug", read_only=True)
    image = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = [
            "id", "product_slug", "product_name", "variant_label", "image",
            "unit_price", "quantity", "line_total",
        ]

    def get_image(self, obj):
        request = self.context.get("request")
        primary = obj.product.images.filter(is_primary=True).first() or obj.product.images.first()
        if not primary:
            return None
        url = primary.image.url
        return request.build_absolute_uri(url) if request else url


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            "id", "number", "status", "payment_method", "payment_status",
            "subtotal", "shipping_fee", "total", "shipping_name", "shipping_phone",
            "shipping_address", "shipping_city", "shipping_postal_code", "notes",
            "items", "created_at", "updated_at",
        ]


class OrderListSerializer(serializers.ModelSerializer):
    item_count = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id", "number", "status", "payment_method", "payment_status",
            "total", "item_count", "created_at",
        ]

    def get_item_count(self, obj):
        return obj.items.count()
