import uuid
from urllib.parse import urlsplit, urlunsplit

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import get_settings
from app.core.errors import error_response

UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def allowed_origins() -> set[str]:
    """Return the browser origins allowed to call state-changing API routes."""
    base = get_settings().app_base_url.rstrip("/")
    origins = {base}

    # In development, accept both loopback spellings so localhost and 127.0.0.1 behave the same.
    if get_settings().environment != "production":
        parts = urlsplit(base)
        if parts.hostname in {"127.0.0.1", "localhost"}:
            alternate = "localhost" if parts.hostname == "127.0.0.1" else "127.0.0.1"
            netloc = alternate if parts.port is None else f"{alternate}:{parts.port}"
            origins.add(urlunsplit((parts.scheme, netloc, parts.path, "", "")))

    return origins


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Attach a request ID to the request state and response headers."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class OriginCheckMiddleware(BaseHTTPMiddleware):
    """Reject cross-origin state-changing API requests.

    Cookie sessions use SameSite=Lax. Checking Origin as well defends against
    same-site cross-origin tricks and misconfigured proxies.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path
        if (
            request.method in UNSAFE_METHODS
            and path.startswith("/api/")
            and not path.startswith("/api/webhooks/")
        ):
            origin = request.headers.get("origin")
            if origin is not None and origin.rstrip("/") not in allowed_origins():
                return error_response(
                    request,
                    403,
                    "INVALID_ORIGIN",
                    "Request origin is not allowed",
                )
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Apply conservative security headers to every response."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        return response
