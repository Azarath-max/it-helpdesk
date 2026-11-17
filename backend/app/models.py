"""ORM model registry.

Import every model module here so Alembic autogenerate can discover the tables.
"""

from app.core.db import Base
from app.modules.audit.models import AuditActorType, AuditEvent
from app.modules.auth.models import PasswordResetToken, UserSession
from app.modules.tickets.models import Ticket, TicketPriority, TicketSource, TicketStatus
from app.modules.users.models import User, UserRole

__all__ = [
    "AuditActorType",
    "AuditEvent",
    "Base",
    "PasswordResetToken",
    "Ticket",
    "TicketPriority",
    "TicketSource",
    "TicketStatus",
    "User",
    "UserRole",
    "UserSession",
]
