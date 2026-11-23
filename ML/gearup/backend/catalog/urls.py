from django.urls import path

from .views import (
    CategoryListView,
    ProductDetailView,
    ProductListView,
    ReviewListCreateView,
)

urlpatterns = [
    path("categories/", CategoryListView.as_view(), name="categories"),
    path("products/", ProductListView.as_view(), name="products"),
    path("products/<slug:slug>/", ProductDetailView.as_view(), name="product-detail"),
    path(
        "products/<slug:slug>/reviews/",
        ReviewListCreateView.as_view(),
        name="product-reviews",
    ),
]
