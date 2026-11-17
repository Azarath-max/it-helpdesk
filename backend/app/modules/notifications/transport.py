"""Email transport abstraction and SMTP implementation."""

from __future__ import annotations

import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Protocol

from app.core.config import get_settings


class PermanentEmailError(Exception):
    """A failure that should not be retried."""


class TransientEmailError(Exception):
    """A failure that may succeed on retry."""


class EmailTransport(Protocol):
    def send(self, message: EmailMessage) -> None: ...


@dataclass
class SmtpTransport:
    """Send email through an SMTP server."""

    def send(self, message: EmailMessage) -> None:
        settings = get_settings()
        try:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
                if settings.smtp_use_tls:
                    smtp.starttls()
                if settings.smtp_username:
                    smtp.login(settings.smtp_username, settings.smtp_password or "")
                smtp.send_message(message)
        except (smtplib.SMTPRecipientsRefused, smtplib.SMTPSenderRefused) as exc:
            raise PermanentEmailError(str(exc)) from exc
        except (smtplib.SMTPException, OSError, TimeoutError) as exc:
            raise TransientEmailError(str(exc)) from exc
