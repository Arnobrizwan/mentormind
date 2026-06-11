import time

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .middleware import TOKEN_PROTOCOL_LABELS

# Token bucket per connection — bursty typing is fine, sustained spam isn't.
RATE_LIMIT_MESSAGES = 10
RATE_LIMIT_WINDOW_SECONDS = 10


class CourseChatConsumer(AsyncJsonWebsocketConsumer):
    """Live chat room per course. Requires the 'chat' feature flag and an
    enrollment (or instructor/staff)."""

    async def connect(self):
        slug = self.scope["url_route"]["kwargs"]["slug"]
        user = self.scope.get("user")

        allowed, course_id = await self._authorize(user, slug)
        if not allowed:
            await self.close(code=4003)
            return

        self.course_id = course_id
        self.group_name = f"chat_course_{course_id}"
        self._bucket_tokens = float(RATE_LIMIT_MESSAGES)
        self._bucket_refilled = time.monotonic()
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        # Browsers drop the connection unless the server selects one of the
        # offered subprotocols (the auth label, never the token itself).
        offered = self.scope.get("subprotocols") or []
        subprotocol = next(
            (p for p in offered if p.lower() in TOKEN_PROTOCOL_LABELS),
            offered[0] if offered else None,
        )
        await self.accept(subprotocol=subprotocol)

    async def disconnect(self, code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    def _take_token(self):
        now = time.monotonic()
        rate = RATE_LIMIT_MESSAGES / RATE_LIMIT_WINDOW_SECONDS
        self._bucket_tokens = min(
            float(RATE_LIMIT_MESSAGES),
            self._bucket_tokens + (now - self._bucket_refilled) * rate,
        )
        self._bucket_refilled = now
        if self._bucket_tokens < 1:
            return False
        self._bucket_tokens -= 1
        return True

    async def receive_json(self, content, **kwargs):
        body = str(content.get("message", "")).strip()[:2000]
        if not body:
            return
        if not self._take_token():
            await self.send_json(
                {"error": "rate_limited", "detail": "Slow down — too many messages."}
            )
            return
        message = await self._persist(body)
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "chat.message",
                "id": message["id"],
                "sender": message["sender"],
                "body": message["body"],
                "created_at": message["created_at"],
            },
        )

    async def chat_message(self, event):
        await self.send_json(
            {
                "id": event["id"],
                "sender": event["sender"],
                "body": event["body"],
                "created_at": event["created_at"],
            }
        )

    @database_sync_to_async
    def _authorize(self, user, slug):
        from apps.core.models import Course
        from apps.flags.services import flag_enabled

        from .permissions import can_join_chat

        # Absent flag means enabled — consistent with the other features
        if not flag_enabled("chat", default=True):
            return False, None
        try:
            course = Course.objects.get(slug=slug)
        except Course.DoesNotExist:
            return False, None
        return can_join_chat(user, course), course.id

    @database_sync_to_async
    def _persist(self, body):
        from .models import ChatMessage

        message = ChatMessage.objects.create(
            course_id=self.course_id, sender=self.scope["user"], body=body
        )
        return {
            "id": message.id,
            "sender": message.sender.display_name or message.sender.email,
            "body": message.body,
            "created_at": message.created_at.isoformat(),
        }
