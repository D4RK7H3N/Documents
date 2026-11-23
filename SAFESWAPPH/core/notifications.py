import logging

from django.conf import settings
from firebase_admin import credentials, initialize_app, messaging

from core.models import DeviceToken, InAppNotification

logger = logging.getLogger(__name__)

_firebase_app = None


def _get_fb_app():
    global _firebase_app
    if _firebase_app is None:
        try:
            cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS)
            _firebase_app = initialize_app(cred)
        except Exception as e:
            logger.warning('Firebase init failed (push disabled): %s', e)
    return _firebase_app


def send_push(user, title, body, data=None):
    tokens = list(
        DeviceToken.objects.filter(user=user).values_list('fcm_token', flat=True)
    )
    if not tokens:
        return

    app = _get_fb_app()
    if app is None:
        return

    for token in tokens:
        try:
            msg = messaging.Message(
                notification=messaging.Notification(title=title, body=body),
                data=data or {},
                token=token,
            )
            messaging.send(msg)
        except Exception as e:
            logger.warning('FCM send failed for %s: %s', user, e)


def notify_new_message(message_obj):
    conv = message_obj.conversation
    trade = conv.trade
    recipient = trade.seller if message_obj.sender == trade.buyer else trade.buyer
    preview = message_obj.text[:100] if message_obj.text else '[image]'

    InAppNotification.objects.create(
        user=recipient,
        notification_type='new_message',
        title=message_obj.sender.name,
        body=preview,
        transaction=trade,
    )

    send_push(
        recipient,
        title=message_obj.sender.name,
        body=preview,
        data={
            'type': 'new_message',
            'conversation_id': str(conv.id),
            'trade_id': str(trade.id),
        },
    )


def notify_trade_completed(trade):
    for user in [trade.buyer, trade.seller]:
        send_push(
            user,
            title='Trade Completed',
            body=f'Trade for {trade.listing.title} completed successfully.',
            data={
                'type': 'trade_completed',
                'trade_id': str(trade.id),
            },
        )
