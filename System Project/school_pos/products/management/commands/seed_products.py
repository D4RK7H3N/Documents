from django.core.management.base import BaseCommand

from products.models import Product


class Command(BaseCommand):
    help = "Seed initial physical products"

    def handle(self, *args, **kwargs):
        # Tuition fees are NOT seeded here - tuition is set per student at
        # enrollment or via the Tuition column on bulk upload. This command
        # only seeds sellable items.
        products = [
            {"name": "Uniform - SHS Male", "price": 500, "stock": 100},
            {"name": "Uniform - SHS Female", "price": 500, "stock": 100},
            {"name": "College Uniform", "price": 600, "stock": 80},
            {"name": "ID Card", "price": 100, "stock": 200},
            {"name": "ID Lace", "price": 50, "stock": 300},
        ]

        for p in products:
            Product.objects.get_or_create(name=p["name"], defaults=p)

        self.stdout.write(self.style.SUCCESS(f"Seeded {len(products)} products."))