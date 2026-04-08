from __future__ import annotations

import os
import uuid
from collections.abc import Generator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEST_DATABASE_ADMIN_URL = os.getenv(
    "TEST_DATABASE_ADMIN_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/postgres",
)


def _build_test_database_url(admin_url: str, db_name: str) -> str:
    """строит url временной тестовой базы из admin url"""

    return make_url(admin_url).set(database=db_name).render_as_string(
        hide_password=False
    )


@pytest.fixture(scope="session")
def postgres_database() -> Generator[str, None, None]:
    """поднимает временную postgresql-базу и накатывает alembic-миграции"""

    admin_engine = create_engine(
        TEST_DATABASE_ADMIN_URL,
        future=True,
        isolation_level="AUTOCOMMIT",
    )
    db_name = f"polls_test_{uuid.uuid4().hex}"
    database_url = _build_test_database_url(TEST_DATABASE_ADMIN_URL, db_name)

    try:
        with admin_engine.connect() as connection:
            connection.execute(text(f'CREATE DATABASE "{db_name}"'))
    except OperationalError as exc:
        admin_engine.dispose()
        pytest.fail(
            "Не удалось подключиться к PostgreSQL для тестов. "
            "Перед запуском тестов подними БД командой `make db-up` "
            "или передай TEST_DATABASE_ADMIN_URL. "
            f"Оригинальная ошибка: {exc}"
        )

    os.environ["DATABASE_URL"] = database_url

    alembic_config = Config(str(PROJECT_ROOT / "alembic.ini"))
    alembic_config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(alembic_config, "head")

    try:
        yield database_url
    finally:
        admin_engine.dispose()
        cleanup_engine = create_engine(
            TEST_DATABASE_ADMIN_URL,
            future=True,
            isolation_level="AUTOCOMMIT",
        )
        with cleanup_engine.connect() as connection:
            connection.execute(
                text(
                    """
                    SELECT pg_terminate_backend(pid)
                    FROM pg_stat_activity
                    WHERE datname = :db_name
                    AND pid <> pg_backend_pid()
                    """
                ),
                {"db_name": db_name},
            )
            connection.execute(text(f'DROP DATABASE IF EXISTS "{db_name}"'))
        cleanup_engine.dispose()


@pytest.fixture(scope="session")
def app_components(
    postgres_database: str,
):
    """импортирует приложение после настройки тестовой БД"""

    from app.db.session import SessionLocal, engine, get_db
    from app.main import app

    return app, get_db, SessionLocal, engine


@pytest.fixture()
def db_session(app_components) -> Generator[Session, None, None]:
    """создает тестовую сессию для postgresql-базы"""

    _, _, SessionLocal, engine = app_components
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
        with engine.begin() as connection:
            connection.execute(
                text(
                    "TRUNCATE TABLE votes, poll_options, polls "
                    "RESTART IDENTITY CASCADE"
                )
            )


@pytest.fixture()
def client(db_session: Session, app_components) -> Generator[TestClient, None, None]:
    """создает тестовый http-клиент"""

    app, get_db, _, _ = app_components

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
