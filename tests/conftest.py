"""pytest 共享夹具 —— SQLite 文件数据库 + TestClient。"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.db import Base, get_db as _orig_get_db
from app.main import app


@pytest.fixture(scope="function")
def dbsession(tmp_path):
    """每个测试独立的 SQLite 文件数据库（避免 :memory: 多连接不共享表）。"""
    db_file = tmp_path / "test.db"
    engine = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _fk(dbapi_conn, _rec):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = SessionLocal()

    def _test_get_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[_orig_get_db] = _test_get_db

    yield session

    session.rollback()
    session.close()
    app.dependency_overrides.pop(_orig_get_db, None)
    engine.dispose()


@pytest.fixture
def client(dbsession):
    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth_token(client):
    resp = client.post("/api/auth/register", json={
        "username": "pytest_user",
        "password": "Test1234!",
    })
    data = resp.json()
    return {"token": data.get("token", ""), "username": "pytest_user"}


@pytest.fixture
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token['token']}"}
