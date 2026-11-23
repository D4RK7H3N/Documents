from django.urls import path
from . import views

app_name = 'revenue'

urlpatterns = [
    path('', views.revenue_dashboard, name='dashboard'),
    path('report/', views.revenue_report, name='report'),
]