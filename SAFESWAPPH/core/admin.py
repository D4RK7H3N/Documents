from django.contrib import admin

from core.models import (
    Blacklist,
    Commission,
    Conversation,
    CustomUser,
    DeviceToken,
    Dispute,
    Escrow,
    InAppNotification,
    KYCVerification,
    Listing,
    Message,
    MessageReport,
    MiddleMan,
    PaymentIntent,
    PhoneOTP,
    PlatformConfig,
    TermsOfService,
    Trade,
    TradeCompletionAcknowledgment,
    TraderAgreement,
)


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone_number', 'role',
                    'is_verified', 'is_banned', 'strike_count', 'date_joined']
    list_filter = ['role', 'is_verified', 'is_banned']
    search_fields = ['name', 'phone_number', 'gcash_number']
    ordering = ['-date_joined']


@admin.register(MiddleMan)
class MiddleManAdmin(admin.ModelAdmin):
    list_display = ['user', 'is_available', 'total_trades', 'rating']
    list_filter = ['is_available']


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ['title', 'seller', 'roblox_username',
                    'price', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['title', 'roblox_username', 'seller__name']
    ordering = ['-created_at']


@admin.register(Trade)
class TradeAdmin(admin.ModelAdmin):
    list_display = ['id', 'listing', 'buyer', 'seller',
                    'middleman', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['buyer__name', 'seller__name']
    ordering = ['-created_at']


@admin.register(Escrow)
class EscrowAdmin(admin.ModelAdmin):
    list_display = ['trade', 'amount', 'is_released',
                    'is_refunded', 'created_at']
    list_filter = ['is_released', 'is_refunded']


@admin.register(Commission)
class CommissionAdmin(admin.ModelAdmin):
    list_display = ['trade', 'total', 'creator_cut',
                    'middleman_cut', 'reserve_cut', 'is_paid']
    list_filter = ['is_paid']


@admin.register(Dispute)
class DisputeAdmin(admin.ModelAdmin):
    list_display = ['trade', 'opened_by', 'outcome', 'created_at']
    list_filter = ['outcome']
    search_fields = ['opened_by__name']
    ordering = ['-created_at']


@admin.register(KYCVerification)
class KYCVerificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'full_legal_name', 'id_type',
                    'status', 'submitted_at', 'reviewed_at']
    list_filter = ['status', 'id_type']
    search_fields = ['user__name', 'full_legal_name']
    ordering = ['-submitted_at']


@admin.register(Blacklist)
class BlacklistAdmin(admin.ModelAdmin):
    list_display = ['gcash_number', 'reason', 'date_added']
    search_fields = ['gcash_number']
    ordering = ['-date_added']


@admin.register(PlatformConfig)
class PlatformConfigAdmin(admin.ModelAdmin):
    list_display = ['commission_total', 'creator_cut',
                    'middleman_cut', 'reserve_cut', 'updated_at']

    def creator_cut(self, obj):
        return obj.commission_creator_cut
    creator_cut.short_description = 'Creator Cut'

    def middleman_cut(self, obj):
        return obj.commission_middleman_cut
    middleman_cut.short_description = 'MM Cut'

    def reserve_cut(self, obj):
        return obj.commission_reserve_cut
    reserve_cut.short_description = 'Reserve Cut'


@admin.register(PhoneOTP)
class PhoneOTPAdmin(admin.ModelAdmin):
    list_display = ['phone_number', 'is_verified', 'created_at']
    list_filter = ['is_verified']
    ordering = ['-created_at']


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['id', 'trade', 'is_locked', 'created_at']
    list_filter = ['is_locked']
    ordering = ['-created_at']


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'conversation', 'sender', 'is_read',
                    'is_flagged', 'flag_reason', 'created_at']
    list_filter = ['is_flagged', 'is_read']
    search_fields = ['sender__name', 'text']
    ordering = ['-created_at']


@admin.register(MessageReport)
class MessageReportAdmin(admin.ModelAdmin):
    list_display = ['message', 'reported_by', 'reason', 'created_at']
    ordering = ['-created_at']


@admin.register(DeviceToken)
class DeviceTokenAdmin(admin.ModelAdmin):
    list_display = ['user', 'platform', 'updated_at']
    list_filter = ['platform']
    search_fields = ['user__name']


@admin.register(InAppNotification)
class InAppNotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'notification_type', 'title', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read']
    ordering = ['-created_at']


@admin.register(TermsOfService)
class TermsOfServiceAdmin(admin.ModelAdmin):
    list_display = ['version', 'is_current', 'created_at']
    list_filter = ['is_current']


@admin.register(TraderAgreement)
class TraderAgreementAdmin(admin.ModelAdmin):
    list_display = ['user', 'tos', 'accepted_at']
    search_fields = ['user__name']
    ordering = ['-accepted_at']


@admin.register(TradeCompletionAcknowledgment)
class TradeCompletionAcknowledgmentAdmin(admin.ModelAdmin):
    list_display = ['user', 'transaction', 'confirmed', 'skipped', 'confirmed_at']
    list_filter = ['confirmed', 'skipped']
    ordering = ['-confirmed_at']


@admin.register(PaymentIntent)
class PaymentIntentAdmin(admin.ModelAdmin):
    list_display = ['trade', 'amount', 'provider', 'status', 'created_at']
    list_filter = ['provider', 'status']
    ordering = ['-created_at']
