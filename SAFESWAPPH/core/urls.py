from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from core import views

urlpatterns = [
    # Root
    path('', views.api_root_view, name='api-root'),
    # User
    path('users/me/', views.current_user_view, name='current-user'),
    # Auth
    path('register/', views.register_view, name='register'),
    path('verify-otp/', views.verify_otp_view, name='verify-otp'),
    path('token/', views.CustomTokenObtainPairView.as_view(), name='token-obtain-pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    # Listings
    path('listings/', views.listings_view, name='listings'),
    # Trades
    path('trade/start/', views.trade_start_view, name='trade-start'),
    path('trade/confirm/', views.trade_confirm_view, name='trade-confirm'),
    path('trade/dispute/', views.trade_dispute_view, name='trade-dispute'),
    # Disputes
    path('dispute/resolve/', views.dispute_resolve_view, name='dispute-resolve'),
    # Admin
    path('ban/', views.ban_user_view, name='ban-user'),
    # Platform Config
    path('config/', views.get_config_view, name='get-config'),
    path('config/update/', views.update_config_view, name='update-config'),
    # KYC Verification
    path('kyc/submit/', views.submit_kyc_view, name='kyc-submit'),
    path('kyc/status/', views.kyc_status_view, name='kyc-status'),
    path('kyc/review/', views.review_kyc_view, name='kyc-review'),
    path('kyc/pending/', views.pending_kyc_list_view, name='kyc-pending'),
    # Upload
    path('upload-url/', views.get_upload_url_view, name='upload-url'),
    # Messaging
    path('conversations/', views.conversation_list_view, name='conversation-list'),
    path('conversations/<int:conversation_id>/', views.conversation_detail_view, name='conversation-detail'),
    path('messages/send/', views.send_message_view, name='send-message'),
    path('messages/report/', views.report_message_view, name='report-message'),
    # Device Tokens (FCM)
    path('devices/register/', views.register_device_token_view, name='register-device'),
    # Notifications
    path('notifications/', views.notifications_view, name='notifications'),
    path('notifications/read/', views.mark_notification_read_view, name='notification-read'),
    path('notifications/unread-count/', views.unread_notification_count_view, name='notification-unread-count'),
    # Terms of Service
    path('tos/current/', views.current_tos_view, name='tos-current'),
    path('tos/accept/', views.accept_tos_view, name='tos-accept'),
    path('tos/check/', views.check_tos_accepted_view, name='tos-check'),
    # Trade Completion Acknowledgment
    path('trade/acknowledge/', views.acknowledge_completion_view, name='trade-acknowledge'),
    # Payment Gateway
    path('payment/create/', views.create_payment_intent_view, name='payment-create'),
    path('payment/webhook/', views.payment_webhook_view, name='payment-webhook'),
    # Onboarding
    path('onboarding/status/', views.onboarding_status_view, name='onboarding-status'),
    path('onboarding/done/', views.mark_onboarding_seen_view, name='onboarding-done'),
    # Honeypot traps
    path('admin/', views.honeypot_view, name='honeypot-admin'),
    path('wp-admin/', views.honeypot_view, name='honeypot-wp'),
]
