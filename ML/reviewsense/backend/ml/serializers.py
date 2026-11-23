from rest_framework import serializers

from .models import Prediction

MAX_TEXT_LENGTH = 5000
MIN_TEXT_LENGTH = 3


class PredictRequestSerializer(serializers.Serializer):
    """Validates the body of POST /api/predict/."""

    text = serializers.CharField(
        required=True,
        allow_blank=False,
        max_length=MAX_TEXT_LENGTH,
        trim_whitespace=True,
        help_text="Review text to classify",
    )

    def validate_text(self, value):
        value = value.strip()
        if len(value) < MIN_TEXT_LENGTH:
            raise serializers.ValidationError(
                f"Text must be at least {MIN_TEXT_LENGTH} characters long."
            )
        return value


class PredictionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prediction
        fields = ["id", "input_text", "prediction", "confidence", "created_at"]
