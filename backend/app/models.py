"""ORM model registry.

Import every model module here so Alembic autogenerate can discover the tables.
"""

from app.core.db import Base

__all__ = ["Base"]
