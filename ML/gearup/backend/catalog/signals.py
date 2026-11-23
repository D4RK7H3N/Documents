import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Product

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Product)
def recompute_embedding_on_save(sender, instance, raw, **kwargs):
    """Keep the semantic-search embedding in sync whenever a product is saved.

    Silently skips when the embedding model is not available yet (e.g. first
    run before `embed_all` / model download); `python manage.py embed_all`
    can backfill at any time.
    """
    if raw:  # fixtures / loaddata
        return
    from ai import services

    if services.encoder_available():
        try:
            services.update_product_embedding(instance)
        except Exception:
            logger.exception("Failed to update embedding for product %s", instance.pk)
