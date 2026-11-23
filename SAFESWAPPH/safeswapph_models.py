"""
SafeSwap PH — Django Model Skeletons
Backend: Django 4.2+ / Django REST Framework / PostgreSQL

Design assumptions flagged with inline comments (# ⚠️ ASSUMPTION).
Hand this file to your code-gen workflow (DeepSeek/OpenCode) for implementation.
"""

import uuid
from decimal import Decimal

from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models


# ---------------------------------------------------------------------------
# 1. USERS & IDENTITY
# ---------------------------------------------------------------------------

class User(models.Model):
    """
    Custom user model. In production, inherit from AbstractBaseUser or
    AbstractUser and move this into accounts/models.py.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(max_length=50, unique=True, db_index=True)
    email = models.EmailField(max_length=255, unique=True, db_index=True)
    phone = models.CharField(max_length=20, unique=True, null=True, blank=True)
    password_hash = models.CharField(max_length=255)

    # roles stored as JSONB via Django's JSONField (PostgreSQL backend)
    roles = models.JSONField(default=list, help_text='e.g., ["trader"], ["trader", "admin"]')

    KYC_TIER_CHOICES = [
        (0, 'unverified'),
        (1, 'basic'),
        (2, 'verified'),
        (3, 'trusted'),
    ]
    kyc_tier = models.SmallIntegerField(
        choices=KYC_TIER_CHOICES,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(3)],
    )

    is_active = models.BooleanField(default=True)
    email_verified = models.BooleanField(default=False)
    phone_verified = models.BooleanField(default=False)

    # Materialized trust score (recalculated async)
    trust_score = models.SmallIntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'users'
        indexes = [
            models.Index(fields=['kyc_tier', 'is_active']),
        ]

    def __str__(self):
        return self.username


class KYCVerification(models.Model):
    """
    Know-Your-Customer verification request.
    One active record per user at a time (enforced via partial unique index in DB).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='kyc_verifications'
    )

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    tier = models.SmallIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(3)],
        help_text='Target KYC tier being applied for',
    )

    ID_DOC_TYPE_CHOICES = [
        ('passport', 'Passport'),
        ('drivers_license', "Driver's License"),
        ('umid', 'UMID'),
        ('national_id', 'National ID'),
    ]
    id_doc_type = models.CharField(
        max_length=20, choices=ID_DOC_TYPE_CHOICES, null=True, blank=True
    )

    # Security: hashed for lookups, encrypted for recovery/review.
    id_doc_number_hash = models.CharField(max_length=255, null=True, blank=True)
    id_doc_number_enc = models.BinaryField(null=True, blank=True)

    # Cloudflare R2 keys (pre-signed URLs generated on demand)
    selfie_r2_key = models.CharField(max_length=500, null=True, blank=True)
    id_front_r2_key = models.CharField(max_length=500, null=True, blank=True)
    id_back_r2_key = models.CharField(max_length=500, null=True, blank=True)

    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewer = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='kyc_reviews'
    )
    rejection_reason = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'kyc_verifications'
        # Enforce one active KYC per user at DB level (optional, add via RunSQL)
        # unique_together = ('user', 'status')  # not valid for partial; use SQL

    def __str__(self):
        return f"KYC({self.user.username} → tier {self.tier})"


class RobloxAccount(models.Model):
    """
    Linked Roblox account. ⚠️ ASSUMPTION: users may link multiple accounts.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='roblox_accounts'
    )
    roblox_user_id = models.BigIntegerField(unique=True, db_index=True)
    roblox_username = models.CharField(max_length=50)
    is_verified = models.BooleanField(default=False)
    verification_code = models.CharField(max_length=50, null=True, blank=True)
    account_age_days = models.PositiveIntegerField(null=True, blank=True)
    trust_score = models.SmallIntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    last_synced_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'roblox_accounts'
        # ⚠️ ASSUMPTION: multiple accounts allowed. If only one per user:
        # unique_together = ('user', 'is_verified')

    def __str__(self):
        return f"{self.roblox_username} ({self.user.username})"


# ---------------------------------------------------------------------------
# 2. WALLET & LEDGER (Double-Entry)
# ---------------------------------------------------------------------------

class Wallet(models.Model):
    """
    User wallet with materialized balance.
    Must reconcile against ledger_entries nightly.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='wallet'
    )
    balance = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    hold_balance = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Funds locked in active escrows',
    )
    currency = models.CharField(max_length=3, default='PHP')
    last_reconciled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'wallets'

    def __str__(self):
        return f"Wallet({self.user.username}: ₱{self.balance})"


class LedgerEntry(models.Model):
    """
    Immutable double-entry ledger. Every financial movement is recorded here.
    ⚠️ ASSUMPTION: Platform fees are captured as separate ledger entries.
    """
    id = models.BigAutoField(primary_key=True)
    wallet = models.ForeignKey(
        Wallet, on_delete=models.PROTECT, related_name='ledger_entries'
    )

    ENTRY_TYPE_CHOICES = [
        ('credit', 'Credit'),
        ('debit', 'Debit'),
    ]
    entry_type = models.CharField(max_length=10, choices=ENTRY_TYPE_CHOICES)
    amount = models.DecimalField(
        max_digits=15, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    balance_after = models.DecimalField(max_digits=15, decimal_places=2)

    trade = models.ForeignKey(
        'Trade', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='ledger_entries'
    )
    payment = models.ForeignKey(
        'PaymentRecord', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='ledger_entries'
    )

    description = models.CharField(max_length=255)
    metadata = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'ledger_entries'
        indexes = [
            models.Index(fields=['wallet', 'created_at']),
        ]
        # Consider partitioning by created_at (monthly) at scale.

    def __str__(self):
        return f"Ledger({self.wallet.user.username}: {self.entry_type} ₱{self.amount})"


# ---------------------------------------------------------------------------
# 3. LISTINGS
# ---------------------------------------------------------------------------

class Listing(models.Model):
    """
    Marketplace listing. ⚠️ ASSUMPTION: seller-posted; trade_type='buy' means WTB.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    seller = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='listings'
    )
    roblox_account = models.ForeignKey(
        RobloxAccount, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='listings'
    )

    TRADE_TYPE_CHOICES = [
        ('sell', 'Sell'),
        ('buy', 'Buy'),
        ('trade', 'Trade'),
    ]
    trade_type = models.CharField(max_length=20, choices=TRADE_TYPE_CHOICES)

    ITEM_TYPE_CHOICES = [
        ('robux', 'Robux'),
        ('limited_item', 'Limited Item'),
        ('gamepass', 'Game Pass'),
        ('other', 'Other'),
    ]
    item_type = models.CharField(max_length=30, choices=ITEM_TYPE_CHOICES)
    item_name = models.CharField(max_length=255)
    item_roblox_asset_id = models.BigIntegerField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)

    price = models.DecimalField(
        max_digits=15, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('sold', 'Sold'),
        ('expired', 'Expired'),
        ('deleted', 'Deleted'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    expires_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'listings'
        indexes = [
            models.Index(fields=['status', 'item_type', 'price']),
            models.Index(fields=['seller', 'status']),
        ]

    def __str__(self):
        return f"Listing({self.item_name} @ ₱{self.price})"


# ---------------------------------------------------------------------------
# 4. TRADES & ESCROW
# ---------------------------------------------------------------------------

class Trade(models.Model):
    """
    Core escrow transaction. Status governed by state machine.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.ForeignKey(
        Listing, on_delete=models.PROTECT, related_name='trades'
    )
    buyer = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name='buy_trades'
    )
    seller = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name='sell_trades'
    )

    STATUS_CHOICES = [
        ('initiated', 'Initiated'),
        ('funded', 'Funded'),
        ('in_progress', 'In Progress'),
        ('delivered', 'Delivered'),
        ('confirmed', 'Confirmed'),
        ('released', 'Released'),
        ('completed', 'Completed'),
        ('disputed', 'Disputed'),
        ('resolved', 'Resolved'),
        ('refunded', 'Refunded'),
        ('cancelled', 'Cancelled'),
    ]
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='initiated'
    )

    amount = models.DecimalField(max_digits=15, decimal_places=2)
    platform_fee = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal('0.00')
    )
    net_amount = models.DecimalField(max_digits=15, decimal_places=2)

    buyer_confirmed = models.BooleanField(default=False)
    seller_confirmed = models.BooleanField(default=False)
    buyer_confirmed_at = models.DateTimeField(null=True, blank=True)
    seller_confirmed_at = models.DateTimeField(null=True, blank=True)

    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    disputed_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'trades'
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['buyer', 'status']),
            models.Index(fields=['seller', 'status']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"Trade({self.id.hex[:8]}: {self.status})"


class TradeEvent(models.Model):
    """
    Event-sourced audit trail for trade state machine.
    """
    id = models.BigAutoField(primary_key=True)
    trade = models.ForeignKey(
        Trade, on_delete=models.CASCADE, related_name='events'
    )
    actor = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='trade_events'
    )

    EVENT_TYPE_CHOICES = [
        ('status_change', 'Status Change'),
        ('payment_received', 'Payment Received'),
        ('dispute_opened', 'Dispute Opened'),
        ('admin_override', 'Admin Override'),
        ('auto_timeout', 'Auto Timeout'),
        ('system', 'System'),
    ]
    event_type = models.CharField(max_length=30, choices=EVENT_TYPE_CHOICES)
    from_status = models.CharField(max_length=20, null=True, blank=True)
    to_status = models.CharField(max_length=20, null=True, blank=True)
    metadata = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'trade_events'
        indexes = [
            models.Index(fields=['trade', 'created_at']),
        ]
        ordering = ['-created_at']
        # Partition by created_at (monthly) at high volume.

    def __str__(self):
        return f"Event({self.trade.id.hex[:8]}: {self.event_type})"


# ---------------------------------------------------------------------------
# 5. PAYMENTS
# ---------------------------------------------------------------------------

class PaymentRecord(models.Model):
    """
    PayMongo / Xendit payment tracking with idempotency.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    trade = models.ForeignKey(
        Trade, on_delete=models.CASCADE, related_name='payments'
    )

    PROVIDER_CHOICES = [
        ('paymongo', 'PayMongo'),
        ('xendit', 'Xendit'),
        ('internal_wallet', 'Internal Wallet'),
    ]
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    provider_ref = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    provider_charge_id = models.CharField(max_length=255, null=True, blank=True)

    amount = models.DecimalField(max_digits=15, decimal_places=2)
    fee = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('cancelled', 'Cancelled'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    idempotency_key = models.UUIDField(unique=True, default=uuid.uuid4)
    webhook_payload = models.JSONField(null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'payment_records'
        indexes = [
            models.Index(fields=['provider', 'provider_ref']),
            models.Index(fields=['status', 'created_at']),
        ]

    def __str__(self):
        return f"Payment({self.provider}: {self.status})"


# ---------------------------------------------------------------------------
# 6. DISPUTES
# ---------------------------------------------------------------------------

class Dispute(models.Model):
    """
    Trade dispute resolution.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    trade = models.OneToOneField(
        Trade, on_delete=models.PROTECT, related_name='dispute'
    )
    raised_by = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name='disputes_raised'
    )

    REASON_CHOICES = [
        ('item_not_received', 'Item Not Received'),
        ('item_not_as_described', 'Item Not As Described'),
        ('seller_not_responding', 'Seller Not Responding'),
        ('fraud', 'Fraud'),
        ('other', 'Other'),
    ]
    reason = models.CharField(max_length=50, choices=REASON_CHOICES)
    description = models.TextField()

    STATUS_CHOICES = [
        ('open', 'Open'),
        ('under_review', 'Under Review'),
        ('resolved_buyer', 'Resolved — Buyer Favored'),
        ('resolved_seller', 'Resolved — Seller Favored'),
        ('resolved_split', 'Resolved — Split'),
        ('closed_no_action', 'Closed — No Action'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    resolution_note = models.TextField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='disputes_resolved'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'disputes'
        indexes = [
            models.Index(fields=['status', 'created_at']),
        ]

    def __str__(self):
        return f"Dispute({self.trade.id.hex[:8]}: {self.status})"


class DisputeEvidence(models.Model):
    """
    Evidence uploaded during dispute resolution.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dispute = models.ForeignKey(
        Dispute, on_delete=models.CASCADE, related_name='evidences'
    )
    uploaded_by = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name='dispute_evidences'
    )
    file_r2_key = models.CharField(max_length=500)

    FILE_TYPE_CHOICES = [
        ('screenshot', 'Screenshot'),
        ('video', 'Video'),
        ('chat_export', 'Chat Export'),
        ('receipt', 'Receipt'),
        ('other', 'Other'),
    ]
    file_type = models.CharField(max_length=20, choices=FILE_TYPE_CHOICES)
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'dispute_evidences'

    def __str__(self):
        return f"Evidence({self.file_type})"


# ---------------------------------------------------------------------------
# 7. CHAT (Django Channels)
# ---------------------------------------------------------------------------

class ChatRoom(models.Model):
    """
    One chat room per trade.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    trade = models.OneToOneField(
        Trade, on_delete=models.CASCADE, related_name='chat_room'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'chat_rooms'

    def __str__(self):
        return f"Room(trade={self.trade.id.hex[:8]})"


class Message(models.Model):
    """
    Chat message. ⚠️ ASSUMPTION: soft-delete only (no hard delete).
    """
    id = models.BigAutoField(primary_key=True)
    room = models.ForeignKey(
        ChatRoom, on_delete=models.CASCADE, related_name='messages'
    )
    sender = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='messages'
    )
    content = models.TextField()

    MESSAGE_TYPE_CHOICES = [
        ('text', 'Text'),
        ('image', 'Image'),
        ('system', 'System'),
        ('trade_update', 'Trade Update'),
    ]
    message_type = models.CharField(
        max_length=20, choices=MESSAGE_TYPE_CHOICES, default='text'
    )
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'messages'
        indexes = [
            models.Index(fields=['room', 'created_at']),
        ]
        ordering = ['created_at']
        # Partition by room_id hash or created_at (monthly) at scale.

    def __str__(self):
        return f"Msg({self.room.trade.id.hex[:8]}: {self.content[:30]})"


# ---------------------------------------------------------------------------
# 8. NOTIFICATIONS
# ---------------------------------------------------------------------------

class Notification(models.Model):
    """
    FCM push notification log.
    """
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='notifications'
    )
    fcm_token = models.CharField(max_length=255, null=True, blank=True)
    title = models.CharField(max_length=255)
    body = models.TextField()
    payload = models.JSONField(null=True, blank=True)

    CATEGORY_CHOICES = [
        ('trade_update', 'Trade Update'),
        ('payment', 'Payment'),
        ('dispute', 'Dispute'),
        ('chat', 'Chat'),
        ('system', 'System'),
    ]
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES)

    is_read = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    error_info = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notifications'
        indexes = [
            models.Index(fields=['user', 'is_read', '-created_at']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"Notify({self.user.username}: {self.title[:30]})"


# ---------------------------------------------------------------------------
# 9. RATINGS
# ---------------------------------------------------------------------------

class Rating(models.Model):
    """
    Post-trade reputation. ⚠️ ASSUMPTION: one rating per trade (buyer→seller).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    trade = models.OneToOneField(
        Trade, on_delete=models.PROTECT, related_name='rating'
    )
    rater = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name='ratings_given'
    )
    ratee = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name='ratings_received'
    )
    score = models.SmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ratings'
        # ⚠️ ASSUMPTION: if mutual ratings wanted, change to:
        # unique_together = ('trade', 'rater')

    def __str__(self):
        return f"Rating({self.ratee.username}: {self.score}/5)"


# ---------------------------------------------------------------------------
# 10. MEDIA ATTACHMENTS
# ---------------------------------------------------------------------------

class MediaAttachment(models.Model):
    """
    Cloudflare R2 file metadata.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='media_attachments'
    )

    FILE_TYPE_CHOICES = [
        ('kyc_doc', 'KYC Document'),
        ('listing_image', 'Listing Image'),
        ('dispute_evidence', 'Dispute Evidence'),
        ('chat_media', 'Chat Media'),
    ]
    file_type = models.CharField(max_length=20, choices=FILE_TYPE_CHOICES)
    r2_key = models.CharField(max_length=500, unique=True)
    r2_bucket = models.CharField(max_length=100)
    file_size = models.BigIntegerField()
    mime_type = models.CharField(max_length=100)
    checksum = models.CharField(max_length=64, null=True, blank=True)
    metadata = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'media_attachments'

    def __str__(self):
        return f"Media({self.file_type}: {self.r2_key[:40]})"
