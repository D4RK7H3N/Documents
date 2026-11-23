"""Management command: python manage.py seed_shop

Creates categories, products (with variants + generated SVG images), an
admin account, a demo customer, and a few sample past orders so the
"customers also bought" recommendations have data on first run.
Idempotent: re-running updates instead of duplicating.
"""
import json
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from catalog.models import Category, Product, ProductImage, ProductVariant
from orders.models import Order, OrderItem
from orders.services import generate_order_number

User = get_user_model()

SEED_PATH = Path(__file__).resolve().parents[4] / "data" / "products_seed.json"

PALETTE = [
    ("#0ea5e9", "#1e293b"),
    ("#a855f7", "#312e81"),
    ("#22c55e", "#14532d"),
    ("#f97316", "#7c2d12"),
    ("#ec4899", "#831843"),
    ("#14b8a6", "#134e4a"),
]


def make_svg(product) -> str:
    initials = "".join(word[0] for word in product.name.split()[:2]).upper()
    color_a, color_b = PALETTE[hash(product.slug) % len(PALETTE)]
    brand = product.brand or "GearUp"
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="640" height="640" viewBox="0 0 640 640">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{color_a}"/>
      <stop offset="100%" stop-color="{color_b}"/>
    </linearGradient>
  </defs>
  <rect width="640" height="640" fill="url(#g)"/>
  <circle cx="320" cy="300" r="170" fill="#ffffff" opacity="0.08"/>
  <text x="320" y="330" font-family="Segoe UI, Arial, sans-serif" font-size="140" font-weight="bold" fill="#ffffff" text-anchor="middle" opacity="0.92">{initials}</text>
  <text x="320" y="560" font-family="Segoe UI, Arial, sans-serif" font-size="30" fill="#e2e8f0" text-anchor="middle">{brand}</text>
</svg>"""


class Command(BaseCommand):
    help = "Seed the shop with sample categories, products, users, and orders."

    def handle(self, *args, **options):
        if not SEED_PATH.exists():
            raise CommandError(f"Seed dataset not found at {SEED_PATH}")
        with SEED_PATH.open("r", encoding="utf-8") as fh:
            data = json.load(fh)

        self._seed_categories(data.get("categories", []))
        products = self._seed_products(data.get("products", []))
        demo_user = self._seed_users()
        self._seed_orders(demo_user)
        self._try_embed(products)

        self.stdout.write(self.style.SUCCESS("Seed complete."))
        self.stdout.write("Admin:  /admin/  (see ADMIN_USERNAME / ADMIN_PASSWORD in backend/.env)")
        self.stdout.write("Demo:   demo@gearup.test / demo1234")

    # ------------------------------------------------------------------
    def _seed_categories(self, categories):
        for entry in categories:
            Category.objects.update_or_create(
                slug=entry["slug"], defaults={"name": entry["name"]}
            )
        self.stdout.write(f"Categories: {Category.objects.count()}")

    def _seed_products(self, products):
        created = []
        for entry in products:
            category = Category.objects.get(slug=entry["category"])
            slug = entry.get("slug") or slugify(entry["name"])[:220]
            product, product_created = Product.objects.update_or_create(
                slug=slug,
                defaults={
                    "category": category,
                    "name": entry["name"],
                    "brand": entry.get("brand", ""),
                    "description": entry.get("description", ""),
                    "price": Decimal(entry["price"]),
                    "stock": entry.get("stock", 0),
                    "is_active": True,
                    "is_featured": entry.get("featured", False),
                },
            )
            for variant in entry.get("variants", []):
                ProductVariant.objects.update_or_create(
                    product=product,
                    name=variant["name"],
                    value=variant["value"],
                    defaults={
                        "price": (
                            Decimal(variant["price"]) if variant.get("price") else None
                        ),
                        "stock": variant.get("stock", 0),
                    },
                )
            if not product.images.exists():
                image = ProductImage(product=product, alt=product.name, is_primary=True)
                image.image.save(
                    f"{slug}.svg", ContentFile(make_svg(product).encode("utf-8")), save=True
                )
            if product_created:
                created.append(product)
        self.stdout.write(f"Products: {Product.objects.count()}")
        return created

    def _seed_users(self):
        admin = User.objects.filter(username=settings.ADMIN_USERNAME).first()
        if admin is None:
            User.objects.create_superuser(
                settings.ADMIN_USERNAME,
                settings.ADMIN_EMAIL,
                settings.ADMIN_PASSWORD,
            )
            self.stdout.write(f"Created admin user '{settings.ADMIN_USERNAME}'")
        else:
            self.stdout.write(f"Admin user '{settings.ADMIN_USERNAME}' already exists")

        demo, created = User.objects.get_or_create(
            username="demo",
            defaults={"email": "demo@gearup.test", "first_name": "Demo", "last_name": "Customer"},
        )
        if created:
            demo.set_password("demo1234")
            demo.save()
        return demo

    def _seed_orders(self, demo_user):
        if Order.objects.exists():
            self.stdout.write("Orders already exist; skipping sample orders.")
            return

        plans = [
            [("apexstrike-k87-mechanical-keyboard", "Black", 1), ("glidepad-xl-desk-mat", None, 1)],
            [("vortex-pro-wireless-gaming-mouse", "White", 1), ("glidepad-xl-desk-mat", None, 1), ("swiftclick-lightweight-mouse", None, 1)],
            [("echowave-71-surround-headset", "Black", 1), ("glidepad-xl-desk-mat", None, 1)],
        ]
        for plan in plans:
            order = Order.objects.create(
                number=generate_order_number(),
                user=demo_user,
                status="delivered",
                payment_method="cod",
                payment_status="paid",
                subtotal=Decimal("0.00"),
                shipping_fee=settings.SHOP_SHIPPING_FEE,
                total=Decimal("0.00"),
                shipping_name="Demo Customer",
                shipping_phone="09171234567",
                shipping_address="123 Sample Street",
                shipping_city="Quezon City",
                shipping_postal_code="1100",
            )
            subtotal = Decimal("0.00")
            for slug, variant_value, quantity in plan:
                product = Product.objects.get(slug=slug)
                variant = (
                    product.variants.filter(value=variant_value).first() if variant_value else None
                )
                unit_price = variant.effective_price if variant else product.price
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    variant=variant,
                    product_name=product.name,
                    variant_label=(f"{variant.name}: {variant.value}" if variant else ""),
                    unit_price=unit_price,
                    quantity=quantity,
                    line_total=unit_price * quantity,
                )
                subtotal += unit_price * quantity
            order.subtotal = subtotal
            order.total = subtotal + order.shipping_fee
            order.save(update_fields=["subtotal", "total"])
        self.stdout.write(f"Sample orders: {Order.objects.count()}")

    def _try_embed(self, products):
        from ai import services

        if services.get_encoder() is None:
            self.stdout.write(
                self.style.WARNING(
                    "Embedding model not loaded yet - run `python manage.py embed_all` "
                    "before using semantic search."
                )
            )
            return
        from catalog.models import Product

        count = 0
        for product in Product.objects.filter(is_active=True, embedding__isnull=True):
            if services.update_product_embedding(product):
                count += 1
        self.stdout.write(f"Embeddings computed for {count} products.")
