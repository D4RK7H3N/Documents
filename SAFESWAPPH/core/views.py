import hashlib
import hmac
import logging
import random
import re
from datetime import timedelta
from decimal import Decimal

import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from core.models import (
    Blacklist,
    Commission,
    Conversation,
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
from core.serializers import (
    AcceptTOSSerializer,
    BanUserSerializer,
    ConversationSerializer,
    CreateListingSerializer,
    CreatePaymentIntentSerializer,
    CustomTokenObtainPairSerializer,
    DeviceTokenSerializer,
    DisputeSerializer,
    InAppNotificationSerializer,
    KYCSerializer,
    ListingSerializer,
    MessageSerializer,
    OpenDisputeSerializer,
    PaymentIntentSerializer,
    PrivateUserSerializer,
    RegisterSerializer,
    ReportMessageSerializer,
    ResolveDisputeSerializer,
    ReviewKYCSerializer,
    SendMessageSerializer,
    StartTradeSerializer,
    SubmitKYCSerializer,
    TermsOfServiceSerializer,
    TradeCompletionAcknowledgmentSerializer,
    TradeSerializer,
    UserSerializer,
    VerifyOTPSerializer,
)
from core.throttles import LoginRateThrottle, OTPRateThrottle, RegisterRateThrottle
from core.notifications import notify_trade_completed
from core.models import normalize_phone

User = get_user_model()
logger = logging.getLogger(__name__)
security_logger = logging.getLogger('security')


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    throttle_classes = [LoginRateThrottle]


# ── Current User ──────────────────────────────────────────────────────

@api_view(['GET'])
def current_user_view(request):
    serializer = PrivateUserSerializer(request.user)
    return Response(serializer.data)


# ── API Root ──────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([AllowAny])
def api_root_view(request):
    return Response({
        'message': 'SafeSwap PH API is running',
        'version': '1.0.0',
        'endpoints': {
            'register': '/api/register/',
            'verify_otp': '/api/verify-otp/',
            'token': '/api/token/',
            'listings': '/api/listings/',
            'trade_start': '/api/trade/start/',
            'trade_confirm': '/api/trade/confirm/',
            'trade_dispute': '/api/trade/dispute/',
            'dispute_resolve': '/api/dispute/resolve/',
            'kyc_submit': '/api/kyc/submit/',
            'kyc_status': '/api/kyc/status/',
            'kyc_review': '/api/kyc/review/',
            'kyc_pending': '/api/kyc/pending/',
            'config': '/api/config/',
            'config_update': '/api/config/update/',
            'upload_url': '/api/upload-url/',
            'ban': '/api/ban/',
        }
    })


# ── Helpers ───────────────────────────────────────────────────────────

def _generate_otp(length=6):
    return ''.join(str(random.randint(0, 9)) for _ in range(length))


def _hash_otp(otp):
    return hashlib.sha256(otp.encode()).hexdigest()


def _verify_otp_hash(otp, otp_hash):
    return hmac.compare_digest(_hash_otp(otp), otp_hash)


def _send_sms_via_semaphore(phone_number, message):
    api_key = settings.SEMAPHORE_API_KEY
    if not api_key:
        logger.warning('SEMAPHORE_API_KEY not set — skipping SMS')
        return True
    resp = requests.post(
        'https://api.semaphore.co/api/v4/messages',
        data={
            'apikey': api_key,
            'number': phone_number,
            'message': message,
            'sendername': settings.SEMAPHORE_SENDER_NAME,
        },
        timeout=10,
    )
    if resp.status_code != 200:
        logger.error('Semaphore SMS failed: %s', resp.text)
        return False
    return True


def _get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


def _assign_middleman():
    return MiddleMan.objects.filter(
        user__is_verified=True, is_available=True
    ).order_by('total_trades').first()


def _maya_payout(gcash_number, amount):
    logger.info('MAYA PAYOUT: ₱%s to GCash %s', amount, gcash_number)
    return True


# ── Commission Split Logic ────────────────────────────────────────────

def split_commission(trade):
    with transaction.atomic():
        from core.models import PlatformConfig

        config = PlatformConfig.get_config()
        escrow = trade.escrow
        total_escrow = escrow.amount
        commission_amount = config.commission_total

        if total_escrow < commission_amount:
            raise ValueError('Escrow amount is less than commission')

        seller_release = total_escrow - commission_amount

        commission, _ = Commission.objects.get_or_create(
            trade=trade,
            defaults={
                'total': commission_amount,
                'creator_cut': config.commission_creator_cut,
                'middleman_cut': config.commission_middleman_cut,
                'reserve_cut': config.commission_reserve_cut,
                'is_paid': True,
            },
        )

        _maya_payout(trade.seller.gcash_number, seller_release)

        escrow.is_released = True
        escrow.save(update_fields=['is_released'])

        trade.status = 'completed'
        trade.save(update_fields=['status'])

        mm_profile = trade.middleman
        if mm_profile:
            mm_profile.total_trades += 1
            mm_profile.save(update_fields=['total_trades'])

    return commission


# ── 1. Register ───────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([RegisterRateThrottle])
def register_view(request):
    serializer = RegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    phone = normalize_phone(data['phone_number'])

    if not re.match(r'^\+639\d{9}$', phone):
        return Response(
            {'error': 'Invalid Philippine phone number format (e.g. +639123456789)'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    gcash = data.get('gcash_number', '')
    if gcash and not re.match(r'^\+639\d{9}$', gcash):
        return Response(
            {'error': 'Invalid GCash number format (e.g. +639123456789)'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if User.objects.filter(phone_number=phone).exists():
        return Response(
            {'error': 'Phone number already registered'},
            status=status.HTTP_409_CONFLICT,
        )

    user = User.objects.create_user(
        phone_number=phone,
        name=data['name'],
        facebook_url=data.get('facebook_url', ''),
        gcash_number=data.get('gcash_number', ''),
        role=data.get('role', 'buyer'),
        is_verified=False,
    )

    if user.role == 'middleman':
        MiddleMan.objects.get_or_create(user=user)

    otp = _generate_otp()
    otp_hash = _hash_otp(otp)

    PhoneOTP.objects.filter(phone_number=phone, is_verified=False).delete()
    PhoneOTP.objects.create(phone_number=phone, otp_hash=otp_hash)

    message = f'Your SafeSwap PH OTP code is: {otp}. Valid for 5 minutes.'
    _send_sms_via_semaphore(phone, message)

    logger.info('OTP for %s: %s (hash: %s)', phone, otp, otp_hash)

    return Response(
        {'message': 'OTP sent successfully', 'phone_number': phone},
        status=status.HTTP_201_CREATED,
    )


# ── 2. Verify OTP ─────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([OTPRateThrottle])
def verify_otp_view(request):
    serializer = VerifyOTPSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    phone = normalize_phone(data['phone_number'])
    otp = data['otp']

    otp_record = (
        PhoneOTP.objects.filter(phone_number=phone, is_verified=False)
        .order_by('-created_at')
        .first()
    )

    if not otp_record:
        return Response(
            {'error': 'No OTP found for this phone number. Please register again.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if timezone.now() - otp_record.created_at > timedelta(minutes=5):
        return Response(
            {'error': 'OTP has expired. Please register again.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not _verify_otp_hash(otp, otp_record.otp_hash):
        security_logger.warning(
            'Failed OTP attempt — phone: %s — IP: %s',
            phone, request.META.get('REMOTE_ADDR', 'unknown'),
        )
        return Response(
            {'error': 'Invalid OTP'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    otp_record.is_verified = True
    otp_record.save(update_fields=['is_verified'])

    user = User.objects.get(phone_number=phone)
    user.is_verified = True
    user.save(update_fields=['is_verified'])

    tokens = _get_tokens_for_user(user)
    user_data = PrivateUserSerializer(user).data

    return Response(
        {'message': 'Account verified successfully', 'user': user_data, **tokens},
        status=status.HTTP_200_OK,
    )


# ── 3. Listings ───────────────────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def listings_view(request):
    if request.method == 'GET':
        listings = Listing.objects.filter(is_active=True).select_related('seller')
        serializer = ListingSerializer(listings, many=True)
        return Response(serializer.data)

    # POST — create listing (seller only)
    if not request.user.is_authenticated:
        return Response(
            {'error': 'Authentication required'},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    if request.user.role != 'seller':
        return Response(
            {'error': 'Only sellers can create listings'},
            status=status.HTTP_403_FORBIDDEN,
        )

    if not request.user.is_verified:
        return Response(
            {'error': 'You must verify your phone number first'},
            status=status.HTTP_403_FORBIDDEN,
        )

    if request.user.is_banned:
        return Response(
            {'error': 'Your account is banned'},
            status=status.HTTP_403_FORBIDDEN,
        )

    if not hasattr(request.user, 'kyc') or request.user.kyc.status != 'approved':
        return Response(
            {'error': 'You must complete KYC verification before creating listings'},
            status=status.HTTP_403_FORBIDDEN,
        )

    serializer = CreateListingSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    price = serializer.validated_data.get('price')
    if price is not None and price <= 0:
        return Response(
            {'error': 'Price must be greater than zero'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    listing = serializer.save(seller=request.user)

    resp_serializer = ListingSerializer(listing)
    return Response(resp_serializer.data, status=status.HTTP_201_CREATED)


# ── 4. Start Trade ────────────────────────────────────────────────────

@api_view(['POST'])
def trade_start_view(request):
    if request.user.role != 'buyer':
        return Response(
            {'error': 'Only buyers can start trades'},
            status=status.HTTP_403_FORBIDDEN,
        )

    if not request.user.is_verified:
        return Response(
            {'error': 'You must verify your phone number first'},
            status=status.HTTP_403_FORBIDDEN,
        )

    serializer = StartTradeSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    listing_id = serializer.validated_data['listing_id']

    try:
        listing = Listing.objects.get(id=listing_id, is_active=True)
    except Listing.DoesNotExist:
        return Response(
            {'error': 'Listing not found or inactive'},
            status=status.HTTP_404_NOT_FOUND,
        )

    if listing.seller == request.user:
        return Response(
            {'error': 'You cannot trade with yourself'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # prevent duplicate active trades on same listing by same buyer
    if Trade.objects.filter(
        listing=listing, buyer=request.user, status='active'
    ).exists():
        return Response(
            {'error': 'You already have an active trade on this listing'},
            status=status.HTTP_409_CONFLICT,
        )

    middleman = _assign_middleman()
    if not middleman:
        return Response(
            {'error': 'No middleman available at this time. Please try again later.'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    with transaction.atomic():
        trade = Trade.objects.create(
            listing=listing,
            buyer=request.user,
            seller=listing.seller,
            middleman=middleman,
            status='active',
        )

        escrow_amount = listing.price
        Escrow.objects.create(trade=trade, amount=escrow_amount)

    resp_serializer = TradeSerializer(trade)
    return Response(resp_serializer.data, status=status.HTTP_201_CREATED)


# ── 5. Confirm Trade (buyer confirms account received) ────────────────

@api_view(['POST'])
def trade_confirm_view(request):
    trade_id = request.data.get('trade_id')

    if not trade_id:
        return Response(
            {'error': 'trade_id is required'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        trade = Trade.objects.select_related(
            'escrow', 'seller', 'middleman', 'listing'
        ).get(id=trade_id)
    except Trade.DoesNotExist:
        return Response(
            {'error': 'Trade not found'},
            status=status.HTTP_404_NOT_FOUND,
        )

    if trade.buyer != request.user:
        return Response(
            {'error': 'You are not the buyer of this trade'},
            status=status.HTTP_403_FORBIDDEN,
        )

    if trade.status != 'active':
        return Response(
            {'error': f'Cannot confirm trade in status: {trade.status}'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        commission = split_commission(trade)
    except ValueError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    # Lock conversation to read-only
    Conversation.objects.filter(trade=trade).update(is_locked=True)

    # Push + in-app notification for both parties
    notify_trade_completed(trade)

    # In-app notification for both parties
    InAppNotification.objects.create(
        user=trade.buyer,
        notification_type='trade_completed',
        title='Trade Completed',
        body=f'Your trade for {trade.listing.title} has been completed. Please confirm TOS compliance.',
        transaction=trade,
    )
    InAppNotification.objects.create(
        user=trade.seller,
        notification_type='trade_completed',
        title='Trade Completed',
        body=f'Your trade for {trade.listing.title} has been completed. Please confirm TOS compliance.',
        transaction=trade,
    )

    return Response(
        {'message': 'Trade completed successfully', 'commission_id': commission.id},
        status=status.HTTP_200_OK,
    )


# ── 6. Open Dispute ───────────────────────────────────────────────────

@api_view(['POST'])
def trade_dispute_view(request):
    if request.user.role != 'buyer':
        return Response(
            {'error': 'Only the buyer can open a dispute'},
            status=status.HTTP_403_FORBIDDEN,
        )

    serializer = OpenDisputeSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    try:
        trade = Trade.objects.get(id=data['trade_id'])
    except Trade.DoesNotExist:
        return Response(
            {'error': 'Trade not found'},
            status=status.HTTP_404_NOT_FOUND,
        )

    if trade.buyer != request.user:
        return Response(
            {'error': 'You are not the buyer of this trade'},
            status=status.HTTP_403_FORBIDDEN,
        )

    if trade.status in ('completed', 'disputed'):
        return Response(
            {'error': f'Cannot dispute a trade with status: {trade.status}'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    with transaction.atomic():
        trade.status = 'disputed'
        trade.save(update_fields=['status'])

        dispute = Dispute.objects.create(
            trade=trade,
            reason=data['reason'],
            evidence_screenshot=data.get('evidence_screenshot', ''),
            opened_by=request.user,
        )

    resp_serializer = DisputeSerializer(dispute)
    return Response(resp_serializer.data, status=status.HTTP_201_CREATED)


# ── 7. Resolve Dispute ────────────────────────────────────────────────

@api_view(['POST'])
def dispute_resolve_view(request):
    if request.user.role != 'middleman':
        return Response(
            {'error': 'Only middlemen can resolve disputes'},
            status=status.HTTP_403_FORBIDDEN,
        )

    serializer = ResolveDisputeSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    try:
        dispute = Dispute.objects.select_related('trade__escrow').get(
            id=data['dispute_id']
        )
    except Dispute.DoesNotExist:
        return Response(
            {'error': 'Dispute not found'},
            status=status.HTTP_404_NOT_FOUND,
        )

    if dispute.outcome != 'pending':
        return Response(
            {'error': 'Dispute is already resolved'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    trade = dispute.trade
    escrow = trade.escrow

    with transaction.atomic():
        outcome = data['outcome']
        dispute.outcome = outcome
        dispute.resolved_by = request.user
        dispute.save(update_fields=['outcome', 'resolved_by'])

        if outcome == 'buyer_wins':
            escrow.is_refunded = True
            escrow.save(update_fields=['is_refunded'])
            trade.status = 'completed'
            trade.save(update_fields=['status'])
            _maya_payout(trade.buyer.gcash_number, escrow.amount)
        else:
            from core.models import PlatformConfig
            config = PlatformConfig.get_config()
            seller_release = escrow.amount - config.commission_total
            _maya_payout(trade.seller.gcash_number, seller_release)
            escrow.is_released = True
            escrow.save(update_fields=['is_released'])
            trade.status = 'completed'
            trade.save(update_fields=['status'])

    return Response(
        {'message': f'Dispute resolved — {outcome}', 'dispute_id': dispute.id},
        status=status.HTTP_200_OK,
    )


# ── 8. Ban User ───────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAdminUser])
def ban_user_view(request):
    serializer = BanUserSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    try:
        user = User.objects.get(id=data['user_id'])
    except User.DoesNotExist:
        return Response(
            {'error': 'User not found'},
            status=status.HTTP_404_NOT_FOUND,
        )

    if user.is_banned:
        return Response(
            {'error': 'User is already banned'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    with transaction.atomic():
        user.is_banned = True
        user.is_active = False
        user.save(update_fields=['is_banned', 'is_active'])

        if user.gcash_number:
            Blacklist.objects.get_or_create(
                gcash_number=user.gcash_number,
                defaults={'reason': data.get('reason', 'Banned by admin')},
            )

    security_logger.warning(
        'BAN — Admin %s (id=%s) banned user %s (id=%s) — Reason: %s',
        request.user.name, request.user.id,
        user.name, user.id,
        data.get('reason', 'No reason provided'),
    )

    return Response(
        {'message': f'User {user.name} has been banned'},
        status=status.HTTP_200_OK,
    )


# ── 9. Get Platform Config ─────────────────────────────────────────

@api_view(['GET'])
@permission_classes([AllowAny])
def get_config_view(request):
    from core.models import PlatformConfig
    config = PlatformConfig.get_config()
    return Response({
        'commission_total': str(config.commission_total),
        'commission_creator_cut': str(config.commission_creator_cut),
        'commission_middleman_cut': str(config.commission_middleman_cut),
        'commission_reserve_cut': str(config.commission_reserve_cut),
        'updated_at': config.updated_at,
    })


# ── 10. Update Platform Config ──────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAdminUser])
def update_config_view(request):
    from core.models import PlatformConfig
    config = PlatformConfig.get_config()

    commission_total = request.data.get('commission_total')
    creator_cut = request.data.get('commission_creator_cut')
    middleman_cut = request.data.get('commission_middleman_cut')
    reserve_cut = request.data.get('commission_reserve_cut')

    if commission_total is not None:
        config.commission_total = Decimal(str(commission_total))
    if creator_cut is not None:
        config.commission_creator_cut = Decimal(str(creator_cut))
    if middleman_cut is not None:
        config.commission_middleman_cut = Decimal(str(middleman_cut))
    if reserve_cut is not None:
        config.commission_reserve_cut = Decimal(str(reserve_cut))

    if (config.commission_creator_cut + config.commission_middleman_cut + config.commission_reserve_cut) != config.commission_total:
        return Response(
            {'error': 'creator_cut + middleman_cut + reserve_cut must equal commission_total'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    config.save()
    return Response({
        'message': 'Commission updated successfully',
        'commission_total': str(config.commission_total),
    })


# ── 11. Submit KYC ─────────────────────────────────────────────────

@api_view(['POST'])
def submit_kyc_view(request):
    if request.user.role != 'seller':
        return Response(
            {'error': 'Only sellers need KYC verification'},
            status=status.HTTP_403_FORBIDDEN,
        )

    if hasattr(request.user, 'kyc'):
        kyc = request.user.kyc
        if kyc.status == 'approved':
            return Response(
                {'error': 'Your KYC is already approved'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if kyc.status == 'pending':
            return Response(
                {'error': 'Your KYC is already under review'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        kyc.delete()

    serializer = SubmitKYCSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    kyc = KYCVerification.objects.create(
        user=request.user,
        full_legal_name=data['full_legal_name'],
        id_type=data['id_type'],
        id_photo_url=data['id_photo_url'],
        selfie_url=data['selfie_url'],
    )

    return Response(
        {
            'message': 'KYC submitted successfully. Under review.',
            'kyc_id': kyc.id,
            'status': kyc.status,
        },
        status=status.HTTP_201_CREATED,
    )


# ── 12. KYC Status ─────────────────────────────────────────────────

@api_view(['GET'])
def kyc_status_view(request):
    if not hasattr(request.user, 'kyc'):
        return Response(
            {'status': 'not_submitted', 'message': 'No KYC submitted yet'},
            status=status.HTTP_200_OK,
        )
    return Response(KYCSerializer(request.user.kyc).data)


# ── 13. Review KYC ────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAdminUser])
def review_kyc_view(request):
    serializer = ReviewKYCSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    try:
        kyc = KYCVerification.objects.select_related('user').get(
            id=data['kyc_id']
        )
    except KYCVerification.DoesNotExist:
        return Response(
            {'error': 'KYC record not found'},
            status=status.HTTP_404_NOT_FOUND,
        )

    if kyc.status != 'pending':
        return Response(
            {'error': f'KYC is already {kyc.status}'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if data['status'] == 'rejected' and not data.get('rejection_reason'):
        return Response(
            {'error': 'rejection_reason is required when rejecting KYC'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    with transaction.atomic():
        kyc.status = data['status']
        kyc.rejection_reason = data.get('rejection_reason', '')
        kyc.reviewed_at = timezone.now()
        kyc.reviewed_by = request.user
        kyc.save()

        if data['status'] == 'approved':
            kyc.user.is_verified = True
            kyc.user.save(update_fields=['is_verified'])

    return Response({
        'message': f"KYC {data['status']} for {kyc.user.name}",
        'kyc_id': kyc.id,
        'status': kyc.status,
    })


# ── 14. Pending KYC List ───────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAdminUser])
def pending_kyc_list_view(request):
    pending = KYCVerification.objects.filter(
        status='pending'
    ).select_related('user').order_by('submitted_at')
    return Response(KYCSerializer(pending, many=True).data)


# ── 15. Get R2 Presigned Upload URL ─────────────────────────────────

@api_view(['GET'])
def get_upload_url_view(request):
    import uuid

    import boto3
    from botocore.config import Config as BotoConfig

    filename = request.query_params.get('filename', '')
    if not filename:
        return Response(
            {'error': 'filename is required'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    ext = filename.rsplit('.', 1)[-1].lower()
    if ext not in ['jpg', 'jpeg', 'png', 'webp']:
        return Response(
            {'error': 'Only jpg, jpeg, png, webp allowed'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    unique_key = f'kyc/{request.user.id}/{uuid.uuid4()}.{ext}'

    s3 = boto3.client(
        's3',
        endpoint_url=settings.R2_ENDPOINT_URL,
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        config=BotoConfig(signature_version='s3v4'),
        region_name='auto',
    )

    presigned_url = s3.generate_presigned_url(
        'put_object',
        Params={
            'Bucket': settings.R2_BUCKET_NAME,
            'Key': unique_key,
            'ContentType': f'image/{ext}',
        },
        ExpiresIn=300,
    )

    public_url = f'{settings.R2_PUBLIC_URL}/{unique_key}'

    return Response({
        'upload_url': presigned_url,
        'public_url': public_url,
        'key': unique_key,
    })


# ── 16. Conversation List ─────────────────────────────────────────────

@api_view(['GET'])
def conversation_list_view(request):
    trades = Trade.objects.filter(
        Q(buyer=request.user) | Q(seller=request.user)
    ).prefetch_related('conversation').order_by('-created_at')
    convs = []
    for t in trades:
        conv, _ = Conversation.objects.get_or_create(trade=t)
        convs.append(conv)
    serializer = ConversationSerializer(
        convs, many=True, context={'request': request}
    )
    return Response(serializer.data)


# ── 17. Conversation Detail (paginated messages) ─────────────────────

@api_view(['GET'])
def conversation_detail_view(request, conversation_id):
    try:
        conv = Conversation.objects.select_related('trade').get(id=conversation_id)
    except Conversation.DoesNotExist:
        return Response({'error': 'Conversation not found'}, status=404)

    trade = conv.trade
    if trade.buyer != request.user and trade.seller != request.user:
        return Response({'error': 'Access denied'}, status=403)

    page = int(request.query_params.get('page', 1))
    per_page = 50
    offset = (page - 1) * per_page
    msgs = conv.messages.select_related('sender').order_by('-created_at')[
        offset:offset + per_page
    ]
    serializer = MessageSerializer(reversed(msgs), many=True)
    return Response({
        'conversation': ConversationSerializer(conv, context={'request': request}).data,
        'messages': serializer.data,
        'page': page,
        'has_more': conv.messages.count() > offset + per_page,
    })


# ── 18. Send Message (REST fallback) ─────────────────────────────────

@api_view(['POST'])
def send_message_view(request):
    serializer = SendMessageSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    text = data.get('text', '')
    image_url = data.get('image_url', '')
    if not text and not image_url:
        return Response({'error': 'text or image_url required'}, status=400)

    try:
        conv = Conversation.objects.select_related('trade').get(
            id=data['conversation_id']
        )
    except Conversation.DoesNotExist:
        return Response({'error': 'Conversation not found'}, status=404)

    trade = conv.trade
    if trade.buyer != request.user and trade.seller != request.user:
        return Response({'error': 'Access denied'}, status=403)

    if conv.is_locked:
        return Response({'error': 'Conversation is locked'}, status=400)

    from core.consumers import flag_content
    is_flagged, flag_reason = flag_content(text)

    msg = Message.objects.create(
        conversation=conv,
        sender=request.user,
        text=text,
        image_url=image_url,
        is_flagged=is_flagged,
        flag_reason=flag_reason,
    )

    return Response(MessageSerializer(msg).data, status=201)


# ── 19. Report Message ───────────────────────────────────────────────

@api_view(['POST'])
def report_message_view(request):
    serializer = ReportMessageSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    try:
        msg = Message.objects.select_related('conversation__trade').get(
            id=data['message_id']
        )
    except Message.DoesNotExist:
        return Response({'error': 'Message not found'}, status=404)

    trade = msg.conversation.trade
    if trade.buyer != request.user and trade.seller != request.user:
        return Response({'error': 'Access denied'}, status=403)

    MessageReport.objects.create(
        message=msg,
        reported_by=request.user,
        reason=data['reason'],
    )

    return Response({'message': 'Message reported'}, status=201)


# ── 20. Register Device Token (FCM) ──────────────────────────────────

@api_view(['POST'])
def register_device_token_view(request):
    serializer = DeviceTokenSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    token, created = DeviceToken.objects.update_or_create(
        user=request.user,
        fcm_token=serializer.validated_data['fcm_token'],
        defaults={
            'platform': serializer.validated_data.get('platform', 'android'),
        },
    )
    return Response(DeviceTokenSerializer(token).data, status=201 if created else 200)


# ── 21. Notifications List ───────────────────────────────────────────

@api_view(['GET'])
def notifications_view(request):
    page = int(request.query_params.get('page', 1))
    per_page = 20
    offset = (page - 1) * per_page
    notifs = InAppNotification.objects.filter(
        user=request.user
    ).order_by('-created_at')[offset:offset + per_page]
    return Response({
        'notifications': InAppNotificationSerializer(notifs, many=True).data,
        'page': page,
        'has_more': InAppNotification.objects.filter(
            user=request.user
        ).count() > offset + per_page,
    })


@api_view(['POST'])
def mark_notification_read_view(request):
    notif_id = request.data.get('notification_id')
    if notif_id:
        InAppNotification.objects.filter(
            id=notif_id, user=request.user
        ).update(is_read=True)
    else:
        InAppNotification.objects.filter(
            user=request.user, is_read=False
        ).update(is_read=True)
    return Response({'message': 'Marked as read'})


@api_view(['GET'])
def unread_notification_count_view(request):
    count = InAppNotification.objects.filter(
        user=request.user, is_read=False
    ).count()
    return Response({'unread_count': count})


# ── 22. Terms of Service ─────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([AllowAny])
def current_tos_view(request):
    tos = TermsOfService.objects.filter(is_current=True).first()
    if not tos:
        return Response({'message': 'No current TOS'}, status=404)
    return Response(TermsOfServiceSerializer(tos).data)


@api_view(['POST'])
def accept_tos_view(request):
    serializer = AcceptTOSSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    tos_id = serializer.validated_data['tos_id']

    try:
        tos = TermsOfService.objects.get(id=tos_id, is_current=True)
    except TermsOfService.DoesNotExist:
        return Response({'error': 'Current TOS not found'}, status=404)

    agreement, created = TraderAgreement.objects.get_or_create(
        user=request.user, tos=tos,
    )
    return Response({
        'message': 'TOS accepted',
        'version': tos.version,
        'accepted_at': agreement.accepted_at,
    })


@api_view(['GET'])
def check_tos_accepted_view(request):
    current = TermsOfService.objects.filter(is_current=True).first()
    if not current:
        return Response({'accepted': False, 'version': None})
    agreed = TraderAgreement.objects.filter(
        user=request.user, tos=current
    ).exists()
    return Response({
        'accepted': agreed,
        'version': current.version,
        'tos_id': current.id,
        'content': current.content if not agreed else None,
    })


# ── 23. Trade Completion Acknowledgment ──────────────────────────────

@api_view(['POST'])
def acknowledge_completion_view(request):
    trade_id = request.data.get('trade_id')
    confirmed = request.data.get('confirmed', True)
    skipped = request.data.get('skipped', False)

    try:
        trade = Trade.objects.get(id=trade_id)
    except Trade.DoesNotExist:
        return Response({'error': 'Trade not found'}, status=404)

    if trade.buyer != request.user and trade.seller != request.user:
        return Response({'error': 'Access denied'}, status=403)

    if trade.status != 'completed':
        return Response({'error': 'Trade not completed'}, status=400)

    ack, created = TradeCompletionAcknowledgment.objects.get_or_create(
        user=request.user, transaction=trade,
        defaults={'confirmed': confirmed, 'skipped': skipped},
    )
    return Response(TradeCompletionAcknowledgmentSerializer(ack).data)


# ── 24. Payment Gateway ──────────────────────────────────────────────

@api_view(['POST'])
def create_payment_intent_view(request):
    serializer = CreatePaymentIntentSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    try:
        trade = Trade.objects.select_related('escrow', 'listing').get(
            id=data['trade_id']
        )
    except Trade.DoesNotExist:
        return Response({'error': 'Trade not found'}, status=404)

    if trade.buyer != request.user:
        return Response({'error': 'Only buyer can create payment'}, status=403)

    if trade.status != 'pending':
        return Response({'error': f'Trade status: {trade.status}'}, status=400)

    if hasattr(trade, 'payment_intent'):
        return Response({'error': 'Payment intent already exists'}, status=409)

    escrow = trade.escrow
    provider = data['provider']
    ref = f'SAFESWAP-{trade.id}-{provider}-{int(timezone.now().timestamp())}'

    checkout_url = ''
    if provider == 'gcash':
        # TODO: Integrate GCash/Xendit API
        checkout_url = f'https://checkout.xendit.co/{ref}'
    elif provider == 'maya':
        # TODO: Integrate Maya/PayMongo API
        checkout_url = f'https://payments.paymongo.com/checkouts/{ref}'

    pi = PaymentIntent.objects.create(
        trade=trade,
        amount=escrow.amount,
        provider=provider,
        provider_reference=ref,
        checkout_url=checkout_url,
    )

    return Response(PaymentIntentSerializer(pi).data, status=201)


@api_view(['POST'])
@permission_classes([AllowAny])
def payment_webhook_view(request):
    """Stub webhook endpoint — TODO: verify signature in production."""
    ref = request.data.get('reference', '')
    status_val = request.data.get('status', 'paid')

    try:
        pi = PaymentIntent.objects.get(provider_reference=ref)
    except PaymentIntent.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)

    pi.status = status_val
    pi.save(update_fields=['status'])

    if status_val == 'paid':
        trade = pi.trade
        trade.status = 'active'
        trade.save(update_fields=['status'])

    return Response({'message': 'Webhook received'})


# ── 25. User Onboarding Status ───────────────────────────────────────

@api_view(['GET'])
def onboarding_status_view(request):
    return Response({
        'has_seen_onboarding': request.user.has_seen_onboarding,
    })


@api_view(['POST'])
def mark_onboarding_seen_view(request):
    request.user.has_seen_onboarding = True
    request.user.save(update_fields=['has_seen_onboarding'])
    return Response({'message': 'Onboarding marked as seen'})


# ── 26. Honeypot (Trap for scanners) ─────────────────────────────────

@api_view(['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([AllowAny])
def honeypot_view(request):
    security_logger.warning(
        'HONEYPOT trigger — IP: %s — UA: %s — Path: %s — Method: %s — Data: %s',
        request.META.get('REMOTE_ADDR', 'unknown'),
        request.META.get('HTTP_USER_AGENT', 'unknown'),
        request.path,
        request.method,
        request.data if request.data else '(no data)',
    )
    return Response(
        {'detail': 'Not found.'},
        status=status.HTTP_404_NOT_FOUND,
    )
