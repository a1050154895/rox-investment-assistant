"""ROX 数据库引擎与会话管理。

生产环境使用 PostgreSQL：设置环境变量 DATABASE_URL（如
postgresql://user:pass@host:5432/roxdb）。
本地开发未配置 DATABASE_URL 时自动降级为 SQLite 文件（data/rox.db）。
"""
import os

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

if DATABASE_URL:
    _engine_options = {"pool_pre_ping": True}
    engine = create_engine(DATABASE_URL, **_engine_options)
    DB_BACKEND = "postgresql"
else:
    db_path = os.path.join(settings.DATA_DIR, "rox.db")
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    DB_BACKEND = "sqlite"

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def get_db():
    """FastAPI 依赖：每个请求一个会话。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """启动时建表（幂等）。"""
    from app import models  # noqa: F401  确保模型已注册
    Base.metadata.create_all(bind=engine)
    _ensure_compat_columns()


def _ensure_compat_columns() -> None:
    """补齐早期版本缺失的轻量字段；重复执行安全。"""
    for table, column, ddl in (
        ("journal_entries", "research_card_id", "INTEGER"),
        ("research_cards", "hypothesis_status", "VARCHAR(20)"),
    ):
        columns = {column["name"] for column in inspect(engine).get_columns(table)}
        if column in columns:
            continue
        with engine.begin() as conn:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))


def check_database() -> bool:
    """就绪检查：能否建立连接并执行查询。"""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
