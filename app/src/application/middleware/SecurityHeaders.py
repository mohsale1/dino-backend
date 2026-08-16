from starlette.types import ASGIApp, Scope, Receive, Send

class SecurityHeadersMiddleware:
    _STATIC_HEADERS = [
        (b"x-content-type-options", b"nosniff"),
        (b"x-frame-options", b"DENY"),
        (b"referrer-policy", b"no-referrer"),
        (b"x-xss-protection", b"0"),
    ]
    _HSTS_HEADER = (b"strict-transport-security", b"max-age=63072000; includeSubDomains")

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers_map = dict(scope.get("headers", []))
        forwarded_proto = headers_map.get(b"x-forwarded-proto", b"").decode()
        is_https = scope.get("scheme") == "https" or forwarded_proto == "https"

        extra_headers = list(self._STATIC_HEADERS)
        if is_https:
            extra_headers.append(self._HSTS_HEADER)

        async def send_with_security_headers(message):
            if message["type"] == "http.response.start":
                message["headers"] = list(message.get("headers", [])) + extra_headers
            await send(message)

        await self.app(scope, receive, send_with_security_headers)
