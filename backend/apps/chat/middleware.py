"""JWT auth for websockets — browsers can't set Authorization headers on
WebSocket upgrade requests, so the access token rides either:

- the Sec-WebSocket-Protocol header (preferred — stays out of access logs):
    new WebSocket(url, ["jwt", "<access>"])
- the query string (legacy fallback):
    ws://host/ws/courses/<slug>/chat/?token=<access>
"""

from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser

# Subprotocol labels that mark the next entry as the token (not tokens themselves)
TOKEN_PROTOCOL_LABELS = ("jwt", "bearer")


@database_sync_to_async
def _user_for_token(raw_token):
    from rest_framework_simplejwt.authentication import JWTAuthentication

    try:
        jwt_auth = JWTAuthentication()
        validated = jwt_auth.get_validated_token(raw_token)
        return jwt_auth.get_user(validated)
    except Exception:
        return AnonymousUser()


def _token_from_scope(scope):
    # Preferred: Sec-WebSocket-Protocol, e.g. ["jwt", "<access>"]
    subprotocols = [p for p in scope.get("subprotocols") or [] if p]
    candidates = [p for p in subprotocols if p.lower() not in TOKEN_PROTOCOL_LABELS]
    if candidates:
        return candidates[0]
    # Fallback: ?token=<access> for older clients
    query = parse_qs(scope.get("query_string", b"").decode())
    return (query.get("token") or [None])[0]


class JWTAuthMiddleware:
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        token = _token_from_scope(scope)
        scope["user"] = await _user_for_token(token) if token else AnonymousUser()
        return await self.inner(scope, receive, send)
