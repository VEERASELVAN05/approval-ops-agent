import os
os.environ.update(DATABASE_URL="sqlite://", JWT_SECRET="test-secret", BCRYPT_ROUNDS="4")  # before app import

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.models import User
from app.seed import seed


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)() as s:
        seed(s)
        yield s


@pytest.fixture()
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def login(client):
    def _login(username):
        r = client.post("/api/auth/login", data={"username": username, "password": f"{username}-pass"})
        assert r.status_code == 200
        return {"Authorization": f"Bearer {r.json()['access_token']}"}
    return _login


@pytest.fixture()
def get_user(db):
    return lambda name: db.scalar(select(User).where(User.username == name))