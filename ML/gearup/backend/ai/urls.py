from django.urls import path

from .views import ChatView, DescribeView, RecommendationView, SearchView

urlpatterns = [
    path("search/", SearchView.as_view(), name="search"),
    path("recommendations/<slug:slug>/", RecommendationView.as_view(), name="recommendations"),
    path("chat/", ChatView.as_view(), name="chat"),
    path("ai/describe/", DescribeView.as_view(), name="ai-describe"),
]
