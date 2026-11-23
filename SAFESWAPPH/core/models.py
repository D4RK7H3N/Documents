import re

from django.conf import settings
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models
from django.db.models import Q


def normalize_phone(phone):
    """Normalize Philippine phone numbers to +63XXXXXXXXXX format."""
    if not phone:
        return phone
    cleaned = re.sub(r'[^0-9]', '', phone)
    if cleaned.startswith('0'):
        cleaned = '63' + cleaned[1:]
    elif not cleaned.startswith('63'):
        cleaned = '63' + cleaned
    return '+' + cleaned


# ── Custom User Manager ───────────────────────────────────────────────

class CustomUserManager(BaseUserManager):
    def create_user(self, phone_number, name, password=None, **extra_fields):
        if not phone_number:
            raise ValueError('Phone number is required')
        if not name:
            raise ValueError('Name is required')
        extra_fields.setdefault('is_active', True)
        phone_number = normalize_phone(phone_number)
        user = self.model(phone_number=phone_number, name=name, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, name, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_verified', True)
        return self.create_user(phone_number, name, password, **extra_fields)


# ── CustomUser ────────────────────────────────────────────────────────

class CustomUser(AbstractBaseUser, PermissionsMixin):
    phone_number = models.CharField(max_length=15, unique=True)
    name = models.CharField(max_length=255)
    facebook_url = models.URLField(max_length=500, blank=True, default='')
    gcash_number = models.CharField(max_length=15, blank=True, default='')
    is_verified = models.BooleanField(default=False)
    is_banned = models.BooleanField(default=False)
    strike_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    has_seen_onboarding = models.BooleanField(default=False)
    role = models.CharField(
        max_length=20,
        choices=[
            ('buyer', 'Buyer'),
            ('seller', 'Seller'),
            ('middleman', 'Middleman'),
            ('administrator', 'Administrator'),
        ],
        default='buyer',
    )

    objects = CustomUserManager()

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['name']

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return f'{self.name} ({self.phone_number})'


# ── PhoneOTP ──────────────────────────────────────────────────────────

class PhoneOTP(models.Model):
    phone_number = models.CharField(max_length=15)
    otp_hash = models.CharField(max_length=128)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Phone OTP'
        verbose_name_plural = 'Phone OTPs'

    def __str__(self):
        return f'OTP for {self.phone_number}'


# ── MiddleMan ─────────────────────────────────────────────────────────

class MiddleMan(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='middleman_profile',
    )
    is_available = models.BooleanField(default=True)
    total_trades = models.PositiveIntegerField(default=0)
    rating = models.FloatField(default=0.0)

    class Meta:
        verbose_name = 'Middleman'
        verbose_name_plural = 'Middlemen'

    def __str__(self):
        return f'MM: {self.user.name}'


# ── Listing ───────────────────────────────────────────────────────────

class Listing(models.Model):
    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='listings',
    )
    title = models.CharField(max_length=255)
    roblox_username = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True, default='')
    screenshots = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Listing'
        verbose_name_plural = 'Listings'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.title} — ₱{self.price}'


# ── Trade ─────────────────────────────────────────────────────────────

class Trade(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('disputed', 'Disputed'),
    ]

    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name='trades',
    )
    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='buyer_trades',
    )
    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='seller_trades',
    )
    middleman = models.ForeignKey(
        MiddleMan,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='trades',
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Trade'
        verbose_name_plural = 'Trades'

    def __str__(self):
        return f'Trade #{self.id} — {self.listing.title}'


# ── Escrow ────────────────────────────────────────────────────────────

class Escrow(models.Model):
    trade = models.OneToOneField(
        Trade,
        on_delete=models.CASCADE,
        related_name='escrow',
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    is_released = models.BooleanField(default=False)
    is_refunded = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Escrow'
        verbose_name_plural = 'Escrows'

    def __str__(self):
        return f'Escrow for Trade #{self.trade_id} — ₱{self.amount}'


# ── Commission ────────────────────────────────────────────────────────

class Commission(models.Model):
    trade = models.OneToOneField(
        Trade,
        on_delete=models.CASCADE,
        related_name='commission',
    )
    total = models.DecimalField(
        max_digits=10, decimal_places=2,
        default=settings.COMMISSION_TOTAL,
    )
    creator_cut = models.DecimalField(
        max_digits=10, decimal_places=2,
        default=settings.COMMISSION_CREATOR_CUT,
    )
    middleman_cut = models.DecimalField(
        max_digits=10, decimal_places=2,
        default=settings.COMMISSION_MIDDLEMAN_CUT,
    )
    reserve_cut = models.DecimalField(
        max_digits=10, decimal_places=2,
        default=settings.COMMISSION_RESERVE_CUT,
    )
    is_paid = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Commission'
        verbose_name_plural = 'Commissions'

    def __str__(self):
        return f'Commission for Trade #{self.trade_id}'


# ── Dispute ───────────────────────────────────────────────────────────

class Dispute(models.Model):
    trade = models.OneToOneField(
        Trade,
        on_delete=models.CASCADE,
        related_name='dispute',
    )
    reason = models.TextField()
    evidence_screenshot = models.URLField(max_length=500, blank=True, default='')
    opened_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='disputes_opened',
    )
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='disputes_resolved',
    )
    outcome = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('buyer_wins', 'Buyer Wins'),
            ('seller_wins', 'Seller Wins'),
        ],
        default='pending',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Dispute'
        verbose_name_plural = 'Disputes'

    def __str__(self):
        return f'Dispute for Trade #{self.trade_id}'


# ── Blacklist ─────────────────────────────────────────────────────────

class Blacklist(models.Model):
    gcash_number = models.CharField(max_length=15, unique=True)
    reason = models.TextField(blank=True, default='')
    date_added = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Blacklist'
        verbose_name_plural = 'Blacklists'

    def __str__(self):
        return f'Blacklisted GCash: {self.gcash_number}'


# ── PlatformConfig ─────────────────────────────────────────────────────

class PlatformConfig(models.Model):
    commission_total = models.DecimalField(max_digits=10, decimal_places=2, default=20)
    commission_creator_cut = models.DecimalField(max_digits=10, decimal_places=2, default=10)
    commission_middleman_cut = models.DecimalField(max_digits=10, decimal_places=2, default=7)
    commission_reserve_cut = models.DecimalField(max_digits=10, decimal_places=2, default=3)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Platform Config'

    def __str__(self):
        return f'Commission: ₱{self.commission_total}'

    @classmethod
    def get_config(cls):
        config, _ = cls.objects.get_or_create(id=1)
        return config


# ── KYC Verification ───────────────────────────────────────────────────

class KYCVerification(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='kyc',
    )
    full_legal_name = models.CharField(max_length=255)
    id_type = models.CharField(
        max_length=50,
        choices=[
            ('philsys', 'PhilSys National ID'),
            ('drivers_license', "Driver's License"),
            ('passport', 'Passport'),
            ('umid', 'UMID'),
            ('sss', 'SSS ID'),
            ('voters_id', "Voter's ID"),
        ]
    )
    id_photo_url = models.URLField(max_length=500)
    selfie_url = models.URLField(max_length=500)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
    )
    rejection_reason = models.TextField(blank=True, default='')
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='kyc_reviews',
    )

    class Meta:
        verbose_name = 'KYC Verification'
        verbose_name_plural = 'KYC Verifications'

    def __str__(self):
        return f'KYC: {self.user.name} — {self.status}'


# ── Conversation (per-transaction scoped) ────────────────────────────

class Conversation(models.Model):
    trade = models.OneToOneField(
        'Trade', on_delete=models.CASCADE,
        related_name='conversation',
    )
    is_locked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Conversation'
        verbose_name_plural = 'Conversations'

    def __str__(self):
        return f'Conversation for Trade #{self.trade_id}'


# ── Message ──────────────────────────────────────────────────────────

class Message(models.Model):
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE,
        related_name='messages',
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='sent_messages',
    )
    text = models.TextField(blank=True, default='')
    image_url = models.URLField(max_length=500, blank=True, default='')
    is_read = models.BooleanField(default=False)
    is_flagged = models.BooleanField(default=False)
    flag_reason = models.CharField(max_length=100, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Message'
        verbose_name_plural = 'Messages'
        ordering = ['created_at']

    def __str__(self):
        return f'Message #{self.id} in Conv #{self.conversation_id}'


# ── MessageReport ────────────────────────────────────────────────────

class MessageReport(models.Model):
    message = models.ForeignKey(
        Message, on_delete=models.CASCADE,
        related_name='reports',
    )
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='message_reports',
    )
    reason = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Message Report'
        verbose_name_plural = 'Message Reports'

    def __str__(self):
        return f'Report on Msg #{self.message_id} by {self.reported_by.name}'


# ── DeviceToken (FCM Push) ───────────────────────────────────────────

class DeviceToken(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='device_tokens',
    )
    fcm_token = models.CharField(max_length=500)
    platform = models.CharField(
        max_length=20,
        choices=[('android', 'Android'), ('ios', 'iOS')],
        default='android',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Device Token'
        verbose_name_plural = 'Device Tokens'
        unique_together = [('user', 'fcm_token')]

    def __str__(self):
        return f'{self.platform} token for {self.user.name}'


# ── InAppNotification ────────────────────────────────────────────────

class InAppNotification(models.Model):
    TYPE_CHOICES = [
        ('trade_completed', 'Trade Completed'),
        ('new_message', 'New Message'),
        ('dispute_update', 'Dispute Update'),
        ('kyc_update', 'KYC Update'),
        ('system', 'System'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='notifications',
    )
    notification_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True, default='')
    transaction = models.ForeignKey(
        'Trade', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='notifications',
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'In-App Notification'
        verbose_name_plural = 'In-App Notifications'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.notification_type} — {self.title}'


# ── Terms of Service ─────────────────────────────────────────────────

class TermsOfService(models.Model):
    version = models.CharField(max_length=20, unique=True)
    content = models.TextField()
    is_current = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Terms of Service'
        verbose_name_plural = 'Terms of Service'
        ordering = ['-version']

    def __str__(self):
        return f'TOS v{self.version}'


class TraderAgreement(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='tos_agreements',
    )
    tos = models.ForeignKey(
        TermsOfService, on_delete=models.CASCADE,
        related_name='agreements',
    )
    accepted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Trader Agreement'
        verbose_name_plural = 'Trader Agreements'
        unique_together = [('user', 'tos')]

    def __str__(self):
        return f'{self.user.name} accepted v{self.tos.version}'


class TradeCompletionAcknowledgment(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='completion_acknowledgments',
    )
    transaction = models.ForeignKey(
        'Trade', on_delete=models.CASCADE,
        related_name='completion_acknowledgments',
    )
    confirmed = models.BooleanField(default=True)
    skipped = models.BooleanField(default=False)
    confirmed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Trade Completion Acknowledgment'
        verbose_name_plural = 'Trade Completion Acknowledgments'
        unique_together = [('user', 'transaction')]

    def __str__(self):
        return f'Ack: {self.user.name} — Trade #{self.transaction_id}'


# ── Payment Intent ──────────────────────────────────────────────────

class PaymentIntent(models.Model):
    PAYMENT_PROVIDERS = [
        ('gcash', 'GCash'),
        ('maya', 'Maya'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

    trade = models.OneToOneField(
        'Trade', on_delete=models.CASCADE,
        related_name='payment_intent',
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    provider = models.CharField(max_length=20, choices=PAYMENT_PROVIDERS)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    provider_reference = models.CharField(max_length=255, blank=True, default='')
    checkout_url = models.URLField(max_length=500, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Payment Intent'
        verbose_name_plural = 'Payment Intents'

    def __str__(self):
        return f'{self.provider} — Trade #{self.trade_id} — {self.status}'
