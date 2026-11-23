from django.core.management.base import BaseCommand

from ai import services
from catalog.models import Product


class Command(BaseCommand):
    help = "Compute embeddings for every active product (backfill / refresh)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Recompute even for products that already have an embedding.",
        )

    def handle(self, *args, **options):
        services.reset_encoder()  # retry a previously failed startup load

        if services.get_encoder() is None:
            self.stderr.write(
                self.style.ERROR(
                    "Embedding model could not be loaded. Check your internet "
                    "connection (first run downloads the model) and try again."
                )
            )
            return

        queryset = Product.objects.filter(is_active=True)
        if not options["force"]:
            queryset = queryset.filter(embedding__isnull=True)

        total = queryset.count()
        self.stdout.write(f"Embedding {total} products with {services.EMBEDDING_MODEL_NAME} ...")

        done = 0
        for product in queryset.iterator():
            if services.update_product_embedding(product):
                done += 1
                self.stdout.write(f"  [{done}/{total}] {product.name}")
            else:
                self.stderr.write(self.style.WARNING(f"  skipped: {product.name}"))

        missing = Product.objects.filter(is_active=True, embedding__isnull=True).count()
        self.stdout.write(
            self.style.SUCCESS(f"Done. {done} embedded, {missing} still missing.")
        )
