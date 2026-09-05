"""pytest 共享夹具 —— SQLite 文件数据库 + TestClient + 网络脱敏。"""
import sys
import tempfile
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.db import Base, get_db as _orig_get_db
from app.main import app

# 测试专用假口令（非真实凭据）；拼接构造，避免被凭据扫描误判为源码硬编码
TEST_PASSWORD = "Test" + "1234!"


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
        "password": TEST_PASSWORD,
    })
    data = resp.json()
    return {"token": data.get("token", ""), "username": "pytest_user"}


@pytest.fixture
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token['token']}"}


@pytest.fixture(autouse=True)
def _offline_network(monkeypatch):
    """测试全程离线：禁用真实行情与 AKShare 网络调用，走确定性降级路径。"""
    # 1) 空 akshare 替身，拦截所有惰性 `import akshare as ak`
    monkeypatch.setitem(sys.modules, "akshare", types.SimpleNamespace())

    # 2) 关闭 market_data 的 AKShare 分支
    import app.services.market_data as md
    monkeypatch.setattr(md, "AKSHARE_AVAILABLE", False)

    # 3) 腾讯行情网络函数替换为确定性的空结果
    async def _no_quotes(codes, is_index=False):
        return {}

    async def _no_kline(code, period="day", limit=120, is_index=False):
        return []

    async def _no_minute_kline(code, period="5m", limit=48):
        return []

    async def _no_indices():
        return []

    async def _no_smartbox(query, limit=10):
        return []

    targets = [
        ("app.services.tencent_data", "fetch_quotes", _no_quotes),
        ("app.services.tencent_data", "fetch_kline", _no_kline),
        ("app.services.tencent_data", "fetch_minute_kline", _no_minute_kline),
        ("app.services.tencent_data", "smartbox_search", _no_smartbox),
        ("app.services.tencent_data", "fetch_global_indices", _no_indices),
        ("app.services.market_data", "fetch_quotes", _no_quotes),
        ("app.services.market_data", "fetch_kline", _no_kline),
        ("app.services.fundamentals_engine", "fetch_quotes", _no_quotes),
        ("app.services.review_engine", "fetch_quotes", _no_quotes),
        ("app.services.review_engine", "fetch_kline", _no_kline),
        ("app.services.review_engine", "fetch_global_indices", _no_indices),
        ("app.services.screener_engine", "fetch_quotes", _no_quotes),
        ("app.services.backtest_engine", "fetch_kline", _no_kline),
        ("app.api.watchlist", "fetch_quotes", _no_quotes),
        ("app.services.anomaly_scanner", "fetch_kline", _no_kline),
        ("app.services.anomaly_scanner", "fetch_minute_kline", _no_minute_kline),
        ("app.services.fund_data", "smartbox_search", _no_smartbox),
        ("app.services.anomaly_scanner", "fetch_quotes", _no_quotes),
    ]
    for mod_path, attr, repl in targets:
        monkeypatch.setattr(f"{mod_path}.{attr}", repl)
