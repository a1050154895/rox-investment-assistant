"""数据导出 API — CSV 下载。"""
import csv
import io

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db import get_db
from app.models import JournalEntry, Position, User

router = APIRouter()


@router.get("/journal")
async def export_journal(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """导出决策日志为 CSV。"""
    rows = db.query(JournalEntry).filter(
        JournalEntry.user_id == user.id
    ).order_by(JournalEntry.date.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["日期", "股票", "代码", "操作", "阶段", "周期", "一致性", "矛盾强度", "价值实现", "理由", "结果", "收益率%", "复盘"])
    for r in rows:
        writer.writerow([
            r.date, r.stock, r.code, r.action, r.stage, r.cycle_stage,
            r.consistency_score, r.contradiction_intensity, r.value_realization,
            r.reason, r.result, r.result_pct or "", r.review or "",
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=rox-journal.csv"},
    )


@router.get("/portfolio")
async def export_portfolio(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """导出持仓为 CSV。"""
    rows = db.query(Position).filter(Position.user_id == user.id).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["代码", "名称", "股数", "成本价", "建仓日期", "备注"])
    for r in rows:
        writer.writerow([r.code, r.name, r.shares, r.cost_price, r.date, r.notes])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=rox-portfolio.csv"},
    )
