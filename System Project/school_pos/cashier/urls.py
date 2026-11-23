from django.urls import path
from . import views

app_name = "cashier"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("checkout/", views.checkout, name="checkout"),
    path("receipt/<int:sale_id>/", views.receipt, name="receipt"),
    
    # Tuition payments
    path("tuition/search/", views.tuition_search, name="tuition_search"),
    path("student/<int:student_id>/pay/", views.add_tuition_payment, name="add_tuition_payment"),
    path("tuition/receipt/<int:payment_id>/", views.tuition_receipt, name="tuition_receipt"),
]