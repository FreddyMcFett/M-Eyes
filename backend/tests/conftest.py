import os

# Must be set before app modules import: the engine is created at import time.
os.environ.setdefault("MEYES_DATABASE_URL", "sqlite://")
os.environ.setdefault("MEYES_BIND_OUTPUT_DIR", "/tmp/meyes-test/bind")
os.environ.setdefault("MEYES_KEA_OUTPUT_DIR", "/tmp/meyes-test/kea")
os.environ.setdefault("MEYES_TLS_DIR", "/tmp/meyes-test/tls")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import get_db
from app.main import app
from app.models import Base, User
from app.security import hash_password


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = TestingSession()
    session.add(User(username="admin", password_hash=hash_password("admin"), role="admin"))
    session.commit()
    yield session
    session.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(client):
    response = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin"})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
