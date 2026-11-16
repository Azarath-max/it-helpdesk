from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    """Base class for all ORM models."""


engine = create_engine(get_settings().database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session]:
    """Yield a database session for request-scoped dependencies."""
    with SessionLocal() as session:
        yield session


def check_database() -> None:
    """Raise when the database is not reachable."""
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
