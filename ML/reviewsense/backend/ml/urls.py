from django.urls import path

from .views import HistoryView, PredictView

urlpatterns = [
    path("predict/", PredictView.as_view(), name="predict"),
    path("history/", HistoryView.as_view(), name="history"),
]
