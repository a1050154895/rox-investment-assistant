"""ROX 数据模型 — 用户 / 决策日志 / 纪律档案 / 用户设置。"""
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    plan: Mapped[str] = mapped_column(String(20), default="基础版")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "plan": self.plan,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    date: Mapped[str] = mapped_column(String(10), index=True)
    stock: Mapped[str] = mapped_column(String(20))
    code: Mapped[str] = mapped_column(String(10))
    action: Mapped[str] = mapped_column(String(10))
    stage: Mapped[str] = mapped_column(String(20))
    cycle_stage: Mapped[str] = mapped_column(String(20), default="流转")
    contradiction_intensity: Mapped[int] = mapped_column(Integer, default=50)
    value_realization: Mapped[int] = mapped_column(Integer, default=50)
    consistency_score: Mapped[int] = mapped_column(Integer, default=50)
    reason: Mapped[str] = mapped_column(Text, default="")
    result: Mapped[str] = mapped_column(String(10), default="待观察")
    result_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    holding_days: Mapped[int] = mapped_column(Integer, default=0)
    review: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

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

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    profile_json: Mapped[str] = mapped_column(Text, default="{}")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Setting(Base):
    __tablename__ = "settings"
    __table_args__ = (UniqueConstraint("user_id", "key", name="uq_user_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    key: Mapped[str] = mapped_column(String(50))
    value: Mapped[str] = mapped_column(Text, default="")
