import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class AiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "ai"

    def ready(self):
        # Load the embedding model exactly once, at server startup.
        from ai import services

        try:
            encoder = services.get_encoder()
        except Exception as exc:  # downloads may be blocked on first run
            logger.warning("Embedding model not loaded at startup: %s", exc)
            return
        if encoder is not None:
            logger.info("Embedding model '%s' loaded.", services.EMBEDDING_MODEL_NAME)
