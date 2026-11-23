from django import template
from django.contrib.auth import get_user_model
from django.db.models import Count, Sum

from core.models import Dispute, Escrow, KYCVerification, Trade

register = template.Library()
User = get_user_model()


@register.simple_tag
def total_users():
    return User.objects.all().count()


@register.simple_tag
def active_trades():
    return Trade.objects.filter(status='active').count()


@register.simple_tag
def pending_kyc():
    return KYCVerification.objects.filter(status='pending').count()


@register.simple_tag
def open_disputes():
    return Dispute.objects.filter(outcome='pending').count()


@register.simple_tag
def total_escrow_value():
    result = Escrow.objects.filter(
        is_released=False, is_refunded=False
    ).aggregate(total=Sum('amount'))
    return result['total'] or 0


@register.simple_tag
def completed_trades():
    return Trade.objects.filter(status='completed').count()


@register.simple_tag
def recent_trades(limit=5):
    return Trade.objects.select_related(
        'listing', 'buyer', 'seller', 'middleman__user'
    ).order_by('-created_at')[:limit]


@register.simple_tag
def pending_kyc_list(limit=5):
    return KYCVerification.objects.filter(
        status='pending'
    ).select_related('user').order_by('submitted_at')[:limit]
