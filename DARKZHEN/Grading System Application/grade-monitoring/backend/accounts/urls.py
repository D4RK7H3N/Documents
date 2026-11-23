from django.urls import path

from . import views

urlpatterns = [
    path("me/", views.MeView.as_view(), name="me"),
    path("me/avatar/", views.MeAvatarView.as_view(), name="me-avatar"),
    path("admin/users/create/", views.CreateStaffView.as_view(), name="user-create"),
    path("admin/users/<int:user_id>/set-password/", views.SetPasswordView.as_view(), name="user-set-password"),
    path("admin/users/<int:user_id>/reset-password/", views.ResetPasswordView.as_view(), name="user-reset-password"),
    path("admin/users/<int:user_id>/status/", views.UserStatusView.as_view(), name="user-status"),
]
