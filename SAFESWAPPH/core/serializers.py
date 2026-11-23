from rest_framework import serializers

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
    TermsOfService,
    Trade,
    TradeCompletionAcknowledgment,
    TraderAgreement,
)
# ── CustomUser Serializers ────────────────────────────────────────────

class RegisterSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    phone_number = serializers.CharField(max_length=15)
    facebook_url = serializers.URLField(max_length=500, required=False, allow_blank=True)
    gcash_number = serializers.CharField(max_length=15, required=False, allow_blank=True)
    role = serializers.ChoiceField(
        choices=['buyer', 'seller', 'middleman', 'administrator'],
        default='buyer',
    )


class VerifyOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15)
    otp = serializers.CharField(max_length=6)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = [
            'id', 'phone_number', 'name', 'facebook_url',
            'gcash_number', 'is_verified', 'is_banned',
            'strike_count', 'role', 'date_joined',
        ]
        read_only_fields = ['id', 'is_verified', 'is_banned', 'strike_count', 'date_joined']


class PrivateUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = [
            'id', 'phone_number', 'name', 'facebook_url',
            'is_verified', 'is_banned',
            'strike_count', 'role', 'date_joined',
        ]
        read_only_fields = ['id', 'is_verified', 'is_banned', 'strike_count', 'date_joined']


from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from core.models import normalize_phone


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = 'phone_number'

    def validate(self, attrs):
        phone = attrs.get(self.username_field)
        if phone:
            attrs = attrs.copy()
            attrs[self.username_field] = normalize_phone(phone)
        data = super().validate(attrs)
        refresh = self.get_token(self.user)
        data['refresh'] = str(refresh)
        data['access'] = str(refresh.access_token)
        return data


# ── PhoneOTP Serializer ───────────────────────────────────────────────

class PhoneOTPSerializer(serializers.ModelSerializer):
    class Meta:
        model = PhoneOTP
        fields = ['id', 'phone_number', 'is_verified', 'created_at']
        read_only_fields = ['id', 'is_verified', 'created_at']


# ── MiddleMan Serializer ──────────────────────────────────────────────

class MiddleManSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = MiddleMan
        fields = ['id', 'user', 'is_available', 'total_trades', 'rating']


# ── Listing Serializer ────────────────────────────────────────────────

class ListingSerializer(serializers.ModelSerializer):
    seller = UserSerializer(read_only=True)

    class Meta:
        model = Listing
        fields = [
            'id', 'seller', 'title', 'roblox_username', 'price',
            'description', 'screenshots', 'is_active', 'created_at',
        ]
        read_only_fields = ['id', 'seller', 'is_active', 'created_at']


class CreateListingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Listing
        fields = [
            'title', 'roblox_username', 'price',
            'description', 'screenshots',
        ]


# ── Trade Serializer ──────────────────────────────────────────────────

class TradeSerializer(serializers.ModelSerializer):
    listing = ListingSerializer(read_only=True)
    buyer = UserSerializer(read_only=True)
    seller = UserSerializer(read_only=True)
    middleman = MiddleManSerializer(read_only=True)

    class Meta:
        model = Trade
        fields = [
            'id', 'listing', 'buyer', 'seller', 'middleman',
            'status', 'created_at',
        ]
        read_only_fields = ['id', 'buyer', 'seller', 'middleman', 'status', 'created_at']


class StartTradeSerializer(serializers.Serializer):
    listing_id = serializers.IntegerField()


# ── Escrow Serializer ─────────────────────────────────────────────────

class EscrowSerializer(serializers.ModelSerializer):
    class Meta:
        model = Escrow
        fields = ['id', 'trade', 'amount', 'is_released', 'is_refunded', 'created_at']
        read_only_fields = ['id', 'trade', 'amount', 'is_released', 'is_refunded', 'created_at']


# ── Commission Serializer ─────────────────────────────────────────────

class CommissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Commission
        fields = [
            'id', 'trade', 'total', 'creator_cut',
            'middleman_cut', 'reserve_cut', 'is_paid',
        ]
        read_only_fields = [
            'id', 'trade', 'total', 'creator_cut',
            'middleman_cut', 'reserve_cut', 'is_paid',
        ]


# ── Dispute Serializer ────────────────────────────────────────────────

class DisputeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dispute
        fields = [
            'id', 'trade', 'reason', 'evidence_screenshot',
            'opened_by', 'resolved_by', 'outcome', 'created_at',
        ]
        read_only_fields = [
            'id', 'trade', 'opened_by', 'resolved_by', 'outcome', 'created_at',
        ]


class OpenDisputeSerializer(serializers.Serializer):
    trade_id = serializers.IntegerField()
    reason = serializers.CharField()
    evidence_screenshot = serializers.URLField(max_length=500, required=False, allow_blank=True)


class ResolveDisputeSerializer(serializers.Serializer):
    dispute_id = serializers.IntegerField()
    outcome = serializers.ChoiceField(choices=['buyer_wins', 'seller_wins'])


# ── Blacklist Serializer ──────────────────────────────────────────────

class BlacklistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Blacklist
        fields = ['id', 'gcash_number', 'reason', 'date_added']
        read_only_fields = ['id', 'date_added']


class BanUserSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    reason = serializers.CharField(required=False, allow_blank=True)


# ── KYC Serializers ────────────────────────────────────────────────────

class SubmitKYCSerializer(serializers.Serializer):
    full_legal_name = serializers.CharField(max_length=255)
    id_type = serializers.ChoiceField(choices=[
        'philsys', 'drivers_license', 'passport', 'umid', 'sss', 'voters_id'
    ])
    id_photo_url = serializers.URLField(max_length=500)
    selfie_url = serializers.URLField(max_length=500)


class ReviewKYCSerializer(serializers.Serializer):
    kyc_id = serializers.IntegerField()
    status = serializers.ChoiceField(choices=['approved', 'rejected'])
    rejection_reason = serializers.CharField(required=False, allow_blank=True)


class KYCSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    reviewed_by = UserSerializer(read_only=True)

    class Meta:
        model = KYCVerification
        fields = [
            'id', 'user', 'full_legal_name', 'id_type',
            'id_photo_url', 'selfie_url', 'status',
            'rejection_reason', 'submitted_at',
            'reviewed_at', 'reviewed_by',
        ]
        read_only_fields = [
            'id', 'user', 'status', 'rejection_reason',
            'submitted_at', 'reviewed_at', 'reviewed_by',
        ]


# ── Messaging Serializers ────────────────────────────────────────────

class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.name', read_only=True)

    class Meta:
        model = Message
        fields = [
            'id', 'conversation', 'sender', 'sender_name',
            'text', 'image_url', 'is_read', 'is_flagged',
            'flag_reason', 'created_at',
        ]
        read_only_fields = [
            'id', 'sender', 'sender_name', 'is_read',
            'is_flagged', 'flag_reason', 'created_at',
        ]


class ConversationSerializer(serializers.ModelSerializer):
    trade_id = serializers.IntegerField(source='trade.id', read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            'id', 'trade_id', 'is_locked', 'last_message',
            'unread_count', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def get_last_message(self, obj):
        msg = obj.messages.order_by('-created_at').first()
        if msg:
            return {
                'id': msg.id,
                'sender_name': msg.sender.name,
                'text': msg.text[:100] if msg.text else '[image]',
                'created_at': msg.created_at.isoformat(),
            }
        return None

    def get_unread_count(self, obj):
        user = self.context.get('request').user if self.context.get('request') else None
        if user:
            return obj.messages.filter(is_read=False).exclude(sender=user).count()
        return 0


class SendMessageSerializer(serializers.Serializer):
    conversation_id = serializers.IntegerField()
    text = serializers.CharField(required=False, allow_blank=True, default='')
    image_url = serializers.URLField(max_length=500, required=False, allow_blank=True, default='')


class ReportMessageSerializer(serializers.Serializer):
    message_id = serializers.IntegerField()
    reason = serializers.CharField()


# ── DeviceToken Serializer ───────────────────────────────────────────

class DeviceTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceToken
        fields = ['id', 'fcm_token', 'platform', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


# ── InAppNotification Serializer ─────────────────────────────────────

class InAppNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = InAppNotification
        fields = [
            'id', 'notification_type', 'title', 'body',
            'transaction', 'is_read', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


# ── TOS Serializers ──────────────────────────────────────────────────

class TermsOfServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = TermsOfService
        fields = ['id', 'version', 'content', 'is_current', 'created_at']
        read_only_fields = ['id', 'created_at']


class AcceptTOSSerializer(serializers.Serializer):
    tos_id = serializers.IntegerField()


# ── TradeCompletionAcknowledgment Serializer ─────────────────────────

class TradeCompletionAcknowledgmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TradeCompletionAcknowledgment
        fields = ['id', 'user', 'transaction', 'confirmed', 'skipped', 'confirmed_at']
        read_only_fields = ['id', 'user', 'transaction', 'confirmed_at']


# ── Payment Intent Serializer ────────────────────────────────────────

class PaymentIntentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentIntent
        fields = [
            'id', 'trade', 'amount', 'provider', 'status',
            'provider_reference', 'checkout_url', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'status', 'provider_reference', 'checkout_url', 'created_at', 'updated_at']


class CreatePaymentIntentSerializer(serializers.Serializer):
    trade_id = serializers.IntegerField()
    provider = serializers.ChoiceField(choices=['gcash', 'maya'])
