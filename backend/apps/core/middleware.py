from django.conf import settings


class ServedByMiddleware:
    """Stamp every response with the instance that served it, so the
    nginx round-robin between api-1 and api-2 is visible in devtools."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response["X-Served-By"] = settings.INSTANCE_NAME
        return response
