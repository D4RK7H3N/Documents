from django.apps import AppConfig


class MlConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "ml"

    def ready(self):
        # Load the trained model artifact into process memory exactly once,
        # at server startup, before the first request is served.
        from ml import services

        services.load_model()
