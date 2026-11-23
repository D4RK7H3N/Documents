from django.urls import path
from . import views

app_name = 'dorm'

urlpatterns = [
    # Dashboard
    path('', views.dorm_dashboard, name='dorm_dashboard'),
    
    # Assignment Management
    path('add/', views.add_dorm_assignment, name='add_assignment'),
    path('terminate/<int:assignment_id>/', views.terminate_assignment, name='terminate_assignment'),
    
    # Payment Management
    path('payment/<int:assignment_id>/', views.add_dorm_payment, name='add_payment'),
    path('receipt/<int:payment_id>/', views.payment_receipt, name='payment_receipt'),
    
    # Building & Room Management
    path('buildings/', views.manage_buildings, name='manage_buildings'),
    path('buildings/add/', views.add_building, name='add_building'),
    path('buildings/edit/<int:building_id>/', views.edit_building, name='edit_building'),
    path('buildings/delete/<int:building_id>/', views.delete_building, name='delete_building'),
    
    path('rooms/', views.manage_rooms, name='manage_rooms'),
    path('rooms/building/<int:building_id>/', views.manage_rooms, name='manage_rooms_by_building'),
    path('rooms/add/', views.add_room, name='add_room'),
    path('rooms/edit/<int:room_id>/', views.edit_room, name='edit_room'),
    path('rooms/delete/<int:room_id>/', views.delete_room, name='delete_room'),
]