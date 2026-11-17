"""Shared test fixtures.

Tests run inside an outer transaction that is rolled back, so they never leave
rows behind. The suite also runs against the development database, so
assertions must scope counts to the rows a test creates rather than assume the
tables are empty.
"""

import os

os.environ.setdefault("RATE_LIMIT_ENABLED", "false")

from collections.abc import Callable, Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session

from app.core.db import engine, get_db
from app.main import create_app
from app.modules.auth.security import hash_password
from app.modules.users.models import User, UserRole
from tests.helpers import DEFAULT_PASSWORD


@pytest.fixture()
def db_connection() -> Iterator[Connection]:
    """Open an outer transaction so each test can be rolled back."""
    connection = engine.connect()
    transaction = connection.begin()
    try:
        yield connection
    finally:
        transaction.rollback()
        connection.close()


@pytest.fixture()
def db(db_connection: Connection) -> Iterator[Session]:
    """Request session that commits into a savepoint the outer transaction can undo."""
    session = Session(
        bind=db_connection,
        join_transaction_mode="create_savepoint",
        autoflush=False,
        expire_on_commit=False,
    )
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def app(db: Session) -> FastAPI:
    application = create_app()
    application.dependency_overrides[get_db] = lambda: db
    return application


@pytest.fixture()
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def make_user(db: Session) -> Callable[..., User]:
    def factory(
        email: str = "user@example.com",
        *,
        name: str = "Test User",
        role: UserRole = UserRole.USER,
        is_active: bool = True,
        password: str = DEFAULT_PASSWORD,
    ) -> User:
        user = User(
            email=email,
            name=name,
            password_hash=hash_password(password),
            role=role,
            is_active=is_active,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    return factory
