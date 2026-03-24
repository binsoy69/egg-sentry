import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DATABASE_URL", f"sqlite:///{(ROOT / 'test_backend.db').as_posix()}")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("AUTO_CREATE_SCHEMA", "true")
os.environ.setdefault("SEED_ADMIN_PASSWORD", "admin123")
os.environ.setdefault("SEED_VIEWER_PASSWORD", "viewer123")
os.environ.setdefault("SEED_DEVICE_API_KEY", "dev-cam-001-key")

from app.main import app  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.seed import seed_defaults  # noqa: E402


@pytest.fixture(autouse=True)
def reset_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_defaults(db)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def auth_headers(client: TestClient):
    response = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def device_headers():
    return {"X-Device-Key": "dev-cam-001-key"}


@pytest.fixture()
def db_session():
    with SessionLocal() as db:
        yield db
