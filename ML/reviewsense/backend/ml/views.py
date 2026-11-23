import logging

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .models import Prediction
from .serializers import PredictRequestSerializer, PredictionSerializer

logger = logging.getLogger(__name__)


class PredictView(APIView):
    """POST /api/predict/ - validate input, run inference, store the result."""

    def post(self, request):
        serializer = PredictRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        text = serializer.validated_data["text"]

        try:
            result = services.predict(text)
        except services.ModelNotReadyError as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except Exception:
            logger.exception("Inference failed for text of length %d", len(text))
            return Response(
                {"error": "Internal error during prediction."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        record = Prediction.objects.create(
            input_text=text,
            prediction=result["prediction"],
            confidence=result["confidence"],
            model_version=result.get("model_version", ""),
        )

        data = PredictionSerializer(record).data
        data["model_version"] = result["model_version"]
        data["inference_ms"] = result.get("inference_ms")
        return Response(data, status=status.HTTP_201_CREATED)


class HistoryView(generics.ListAPIView):
    """GET /api/history/ - the last 50 predictions, newest first."""

    serializer_class = PredictionSerializer
    pagination_class = None

    def get_queryset(self):
        return Prediction.objects.all().order_by("-created_at")[:50]
