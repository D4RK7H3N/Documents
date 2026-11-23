from django.core.management.base import BaseCommand

from products.models import Product


class Command(BaseCommand):
    help = "Seed sample cashier inventory (uniforms and supplies)"

    def handle(self, *args, **options):
        # These are sellable items at the counter, so they all belong to the
        # "Product & Supplies" category. Academic fees are not Products - they
        # live on StudentCharge, which is what the cashier's Academic Fees tab
        # reads.
        items = [
            {"name": "Official School Uniform Set (SHS)", "price": 950, "stock": 50},
            {"name": "P.E. Uniform & Official Activity Shirt", "price": 650, "stock": 50},
            {"name": "Laboratory Apron", "price": 350, "stock": 25},
            {"name": "Student ID Lace", "price": 50, "stock": 200},
            {"name": "Student ID Card", "price": 100, "stock": 200},
        ]

        for item in items:
            obj, created = Product.objects.get_or_create(
                name=item["name"],
                defaults={
                    "price": item["price"],
                    "stock": item["stock"],
                    "category": "products",
                },
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created: {item['name']}"))
            else:
                self.stdout.write(self.style.WARNING(f"Already exists: {item['name']}"))