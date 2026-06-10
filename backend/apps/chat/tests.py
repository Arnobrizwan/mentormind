from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, TransactionTestCase
from rest_framework.test import APIClient

from apps.core.models import Course, Enrollment
from apps.flags.models import FeatureFlag
from config.asgi import application

from .models import ChatMessage

User = get_user_model()


def make_world():
    instructor = User.objects.create_user(
        email="chat-teach@mentormind.dev", password="pass-123456", display_name="Teach"
    )
    student = User.objects.create_user(
        email="chat-learn@mentormind.dev", password="pass-123456", display_name="Learner"
    )
    course = Course.objects.create(
        title="Chat 101",
        slug="chat-101",
        description="d",
        instructor=instructor,
        is_published=True,
    )
    Enrollment.objects.create(student=student, course=course)
    FeatureFlag.objects.create(key="chat", enabled=True)
    return instructor, student, course


class ChatHistoryApiTests(TestCase):
    def setUp(self):
        cache.clear()
        self.instructor, self.student, self.course = make_world()

    def test_history_requires_enrollment(self):
        outsider = User.objects.create_user(
            email="outsider@mentormind.dev", password="pass-123456"
        )
        client = APIClient()
        client.force_authenticate(user=outsider)
        res = client.get(f"/api/v1/chat/courses/{self.course.slug}/messages/")
        self.assertEqual(res.status_code, 403)

    def test_history_returns_messages_for_enrolled(self):
        ChatMessage.objects.create(course=self.course, sender=self.student, body="hi all")
        client = APIClient()
        client.force_authenticate(user=self.student)
        res = client.get(f"/api/v1/chat/courses/{self.course.slug}/messages/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()[0]["body"], "hi all")

    def test_history_blocked_when_flag_off(self):
        FeatureFlag.objects.filter(key="chat").update(enabled=False)
        cache.clear()
        client = APIClient()
        client.force_authenticate(user=self.student)
        res = client.get(f"/api/v1/chat/courses/{self.course.slug}/messages/")
        self.assertEqual(res.status_code, 403)


class ChatConsumerTests(TransactionTestCase):
    """Websocket round-trip through the real ASGI stack (in-memory layer)."""

    async def _connect(self, user, slug):
        from channels.db import database_sync_to_async
        from rest_framework_simplejwt.tokens import AccessToken

        token = await database_sync_to_async(lambda: str(AccessToken.for_user(user)))()
        communicator = WebsocketCommunicator(
            application, f"/ws/courses/{slug}/chat/?token={token}"
        )
        connected, _ = await communicator.connect()
        return communicator, connected

    async def test_enrolled_student_can_chat(self):
        from channels.db import database_sync_to_async

        cache.clear()
        instructor, student, course = await database_sync_to_async(make_world)()

        communicator, connected = await self._connect(student, course.slug)
        self.assertTrue(connected)

        await communicator.send_json_to({"message": "hello room"})
        reply = await communicator.receive_json_from(timeout=5)
        self.assertEqual(reply["body"], "hello room")
        self.assertEqual(reply["sender"], "Learner")

        count = await database_sync_to_async(
            lambda: ChatMessage.objects.filter(course=course).count()
        )()
        self.assertEqual(count, 1)
        await communicator.disconnect()

    async def test_outsider_rejected(self):
        from channels.db import database_sync_to_async

        cache.clear()
        instructor, student, course = await database_sync_to_async(make_world)()
        outsider = await database_sync_to_async(User.objects.create_user)(
            email="nope@mentormind.dev", password="pass-123456"
        )

        communicator, connected = await self._connect(outsider, course.slug)
        self.assertFalse(connected)
