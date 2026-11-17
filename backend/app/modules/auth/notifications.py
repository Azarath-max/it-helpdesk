"""Outbound account emails.

Phase 1 only logs reset links in development. Phase 4 replaces this module with
the transactional outbox and SMTP delivery.
"""

import logging

from app.core.config import get_settings
from app.modules.users.models import User

logger = logging.getLogger(__name__)


def deliver_password_reset(user: User, token: str) -> None:
    """Deliver a password reset link through the configured channel."""
    settings = get_settings()
    reset_url = f"{settings.app_base_url}/reset-password?token={token}"

    if settings.environment == "production":
        # Do not log the token. The outbox worker will send it in Phase 4.
        logger.info("Password reset requested for user %s", user.id)
        return

    logger.warning("Password reset link for %s: %s", user.email, reset_url)
