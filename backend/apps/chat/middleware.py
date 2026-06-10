"""JWT auth for websockets — browsers can't set Authorization headers on
WebSocket upgrade requests, so the access token rides the query string:

    ws://host/ws/courses/<slug>/chat/?token=<access>
"""

from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser


@database_sync_to_async
def _user_for_token(raw_token):
    from rest_framework_simplejwt.authentication import JWTAuthentication

    try:
        jwt_auth = JWTAuthentication()
        validated = jwt_auth.get_validated_token(raw_token)
        return jwt_auth.get_user(validated)
    except Exception:
        return AnonymousUser()


class JWTAuthMiddleware:
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        query = parse_qs(scope.get("query_string", b"").decode())
        token = (query.get("token") or [None])[0]
        scope["user"] = await _user_for_token(token) if token else AnonymousUser()
        return await self.inner(scope, receive, send)
