from django.urls import path
from . import views

app_name = 'staff'

urlpatterns = [
    path('', views.home, name='home'),
    path('', views.staff_home, name='staff_home'),
    path('register/', views.staff_register, name='staff_register'),
    path('login/', views.staff_login, name='staff_login'),
    path('dashboard/', views.staff_dashboard, name='staff_dashboard'),
    path('logout/', views.staff_logout, name='staff_logout'),
]