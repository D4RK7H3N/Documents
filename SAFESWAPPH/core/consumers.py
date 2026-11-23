import json
import re

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model

from core.models import Conversation, Message
from core.notifications import notify_new_message

User = get_user_model()

OFF_PLATFORM_PATTERNS = {
    'phone': re.compile(r'(?:\+?63|0)[\d\s\-]{9,12}'),
    'handle': re.compile(r'@[\w_.]{2,}'),
    'external_link': re.compile(r'(?:https?://|www\.)[^\s]+'),
}


def flag_content(text):
    if not text:
        return False, ''
    for key, pattern in OFF_PLATFORM_PATTERNS.items():
        if pattern.search(text):
            return True, f'matches_{key}'
    return False, ''


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.user = self.scope.get('user')
        self.user = await self._resolve_user()

        if not self.user or not self.user.is_authenticated:
            await self.close(code=4001)
            return

        can_access = await self._user_can_access()
        if not can_access:
            await self.close(code=4003)
            return

        self.room_group_name = f'chat_{self.conversation_id}'
        await self.channel_layer.group_add(
            self.room_group_name, self.channel_name
        )
        await self.accept()

        unread = await self._mark_messages_read()
        if unread:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'read_receipt',
                    'user_id': self.user.id,
                    'conversation_id': int(self.conversation_id),
                }
            )

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name, self.channel_name
            )

    async def receive(self, text_data):
        data = json.loads(text_data)
        msg_type = data.get('type', 'message')

        if msg_type == 'typing':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'typing_indicator',
                    'user_id': self.user.id,
                    'user_name': self.user.name,
                }
            )
            return

        if msg_type != 'message':
            return

        text = data.get('text', '')
        image_url = data.get('image_url', '')
        if not text and not image_url:
            return

        locked = await self._is_locked()
        if locked:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'This conversation is locked (trade completed).',
            }))
            return

        is_flagged, flag_reason = flag_content(text)

        msg = await self._save_message(text, image_url, is_flagged, flag_reason)

        import asyncio
        asyncio.ensure_future(
            database_sync_to_async(notify_new_message)(msg)
        )

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'id': msg.id,
                'sender_id': self.user.id,
                'sender_name': self.user.name,
                'text': msg.text,
                'image_url': msg.image_url,
                'is_flagged': msg.is_flagged,
                'created_at': msg.created_at.isoformat(),
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'new_message',
            **event,
        }))

    async def typing_indicator(self, event):
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'user_id': event['user_id'],
            'user_name': event['user_name'],
        }))

    async def read_receipt(self, event):
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def _user_can_access(self):
        try:
            conv = Conversation.objects.select_related('trade').get(
                id=self.conversation_id
            )
            return conv.trade.buyer == self.user or conv.trade.seller == self.user
        except Conversation.DoesNotExist:
            return False

    @database_sync_to_async
    def _is_locked(self):
        try:
            return Conversation.objects.get(id=self.conversation_id).is_locked
        except Conversation.DoesNotExist:
            return True

    @database_sync_to_async
    def _save_message(self, text, image_url, is_flagged, flag_reason):
        return Message.objects.create(
            conversation_id=self.conversation_id,
            sender=self.user,
            text=text,
            image_url=image_url,
            is_flagged=is_flagged,
            flag_reason=flag_reason,
        )

    @database_sync_to_async
    def _mark_messages_read(self):
        count = Message.objects.filter(
            conversation_id=self.conversation_id,
            is_read=False,
        ).exclude(sender=self.user).update(is_read=True)
        return count

    async def _resolve_user(self):
        user = self.scope.get('user')
        if user and user.is_authenticated:
            return user
        qs = self.scope.get('query_string', b'').decode()
        params = dict(p.split('=') for p in qs.split('&') if '=' in p)
        token_str = params.get('token')
        if not token_str:
            return user
        try:
            from django.contrib.auth import get_user_model
            from rest_framework_simplejwt.tokens import AccessToken
            token = AccessToken(token_str)
            uid = token.payload.get('user_id')
            User = get_user_model()
            return await database_sync_to_async(User.objects.get)(id=uid)
        except Exception:
            return user


class EscrowStatusConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.trade_id = self.scope['url_route']['kwargs']['trade_id']
        self.user = self.scope.get('user')
        self.user = await self._resolve_user()

        if not self.user or not self.user.is_authenticated:
            await self.close(code=4001)
            return

        can_access = await self._user_can_access()
        if not can_access:
            await self.close(code=4003)
            return

        self.room_group_name = f'escrow_{self.trade_id}'
        await self.channel_layer.group_add(
            self.room_group_name, self.channel_name
        )
        await self.accept()

        status = await self._get_status()
        await self.send(text_data=json.dumps({
            'type': 'status',
            'trade_id': int(self.trade_id),
            'status': status['trade_status'],
            'escrow_released': status['escrow_released'],
            'escrow_refunded': status['escrow_refunded'],
        }))

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name, self.channel_name
            )

    async def escrow_update(self, event):
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def _user_can_access(self):
        from core.models import Trade
        try:
            trade = Trade.objects.get(id=self.trade_id)
            return trade.buyer == self.user or trade.seller == self.user
        except Trade.DoesNotExist:
            return False

    async def _resolve_user(self):
        user = self.scope.get('user')
        if user and user.is_authenticated:
            return user
        qs = self.scope.get('query_string', b'').decode()
        params = dict(p.split('=') for p in qs.split('&') if '=' in p)
        token_str = params.get('token')
        if not token_str:
            return user
        try:
            from django.contrib.auth import get_user_model
            from rest_framework_simplejwt.tokens import AccessToken
            token = AccessToken(token_str)
            uid = token.payload.get('user_id')
            User = get_user_model()
            return await database_sync_to_async(User.objects.get)(id=uid)
        except Exception:
            return user

    @database_sync_to_async
    def _get_status(self):
        from core.models import Escrow, Trade
        try:
            trade = Trade.objects.get(id=self.trade_id)
            escrow = getattr(trade, 'escrow', None)
            return {
                'trade_status': trade.status,
                'escrow_released': escrow.is_released if escrow else False,
                'escrow_refunded': escrow.is_refunded if escrow else False,
            }
        except Trade.DoesNotExist:
            return {
                'trade_status': 'unknown',
                'escrow_released': False,
                'escrow_refunded': False,
            }
