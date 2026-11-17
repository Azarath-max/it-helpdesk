from fastapi import FastAPI

from app.api.system import router as system_router
from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import (
    OriginCheckMiddleware,
    RequestIdMiddleware,
    SecurityHeadersMiddleware,
)
from app.modules.auth.router import router as auth_router
from app.modules.comments.router import router as comments_router
from app.modules.tickets.router import router as tickets_router
from app.modules.users.router import router as users_router
from app.modules.webhooks.router import router as webhooks_router


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(OriginCheckMiddleware)
    app.add_middleware(RequestIdMiddleware)
    register_exception_handlers(app)
    app.include_router(system_router)
    app.include_router(auth_router)
    app.include_router(users_router)
    app.include_router(tickets_router)
    app.include_router(comments_router)
    app.include_router(webhooks_router)

    return app


app = create_app()
