"""ROX 数据模型 — 用户 / 决策日志 / 纪律档案 / 用户设置。

注意：不使用 `Mapped[X | None]` 注解风格 —— SQLAlchemy 2.0.36 在 Python 3.14 上
解析 PEP 604 联合类型会触发 typing.Union bug（TypeError: descriptor '__getitem__'）。
统一使用无注解的 mapped_column 声明，兼容 Python 3.11 ~ 3.14。
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import mapped_column

from app.db import Base


class User(Base):
    __tablename__ = "users"

    id = mapped_column(Integer, primary_key=True)
    username = mapped_column(String(50), unique=True, index=True)
    password_hash = mapped_column(String(200))
    plan = mapped_column(String(20), default="基础版")
    created_at = mapped_column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "plan": self.plan,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id = mapped_column(Integer, primary_key=True)
    user_id = mapped_column(ForeignKey("users.id"), index=True)
    date = mapped_column(String(10), index=True)
    stock = mapped_column(String(20))
    code = mapped_column(String(10))
    action = mapped_column(String(10))
    stage = mapped_column(String(20))
    cycle_stage = mapped_column(String(20), default="流转")
    contradiction_intensity = mapped_column(Integer, default=50)
    value_realization = mapped_column(Integer, default=50)
    consistency_score = mapped_column(Integer, default=50)
    reason = mapped_column(Text, default="")
    result = mapped_column(String(10), default="待观察")
    result_pct = mapped_column(Float, nullable=True)
    holding_days = mapped_column(Integer, default=0)
    review = mapped_column(Text, nullable=True)
    created_at = mapped_column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "date": self.date,
            "stock": self.stock,
            "code": self.code,
            "action": self.action,
            "stage": self.stage,
            "cycle_stage": self.cycle_stage,
            "contradiction_intensity": self.contradiction_intensity,
            "value_realization": self.value_realization,
            "consistency_score": self.consistency_score,
            "reason": self.reason,
            "result": self.result,
            "result_pct": self.result_pct,
            "holding_days": self.holding_days,
            "review": self.review,
        }


class DisciplineProfile(Base):
    __tablename__ = "discipline_profiles"

    id = mapped_column(Integer, primary_key=True)
    user_id = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    profile_json = mapped_column(Text, default="{}")
    updated_at = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Setting(Base):
    __tablename__ = "settings"
    __table_args__ = (UniqueConstraint("user_id", "key", name="uq_user_key"),)

    id = mapped_column(Integer, primary_key=True)
    user_id = mapped_column(ForeignKey("users.id"), index=True)
    key = mapped_column(String(50))
    value = mapped_column(Text, default="")


class Position(Base):
    __tablename__ = "positions"

    id = mapped_column(Integer, primary_key=True)
    user_id = mapped_column(ForeignKey("users.id"), index=True)
    code = mapped_column(String(10))
    name = mapped_column(String(30))
    shares = mapped_column(Float, default=0)       # 持仓股数
    cost_price = mapped_column(Float, default=0)    # 成本价
    date = mapped_column(String(10))                 # 建仓日期
    notes = mapped_column(Text, default="")
    created_at = mapped_column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "shares": self.shares,
            "cost_price": self.cost_price,
            "date": self.date,
            "notes": self.notes,
        }


class Alert(Base):
    __tablename__ = "alerts"

    id = mapped_column(Integer, primary_key=True)
    user_id = mapped_column(ForeignKey("users.id"), index=True)
    code = mapped_column(String(10))
    name = mapped_column(String(30))
    target_price = mapped_column(Float)
    direction = mapped_column(String(10), default="above")  # above / below
    active = mapped_column(Boolean, default=True)
    triggered = mapped_column(Boolean, default=False)
    triggered_at = mapped_column(DateTime, nullable=True)
    created_at = mapped_column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "target_price": self.target_price,
            "direction": self.direction,
            "active": self.active,
            "triggered": self.triggered,
            "triggered_at": self.triggered_at.isoformat() if self.triggered_at else None,
        }
