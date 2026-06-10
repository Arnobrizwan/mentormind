from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer


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
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        body = str(content.get("message", "")).strip()[:2000]
        if not body:
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

        if not flag_enabled("chat"):
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
