from django.db import models


class Prediction(models.Model):
    """One stored /api/predict/ request and its result."""

    input_text = models.TextField(help_text="Raw review text sent by the client")
    prediction = models.CharField(max_length=32, help_text="Predicted label")
    confidence = models.FloatField(help_text="Probability of the predicted label (0-1)")
    model_version = models.CharField(max_length=64, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "predictions"

    def __str__(self):
        return f"{self.prediction} ({self.confidence:.2f}) at {self.created_at:%Y-%m-%d %H:%M}"
