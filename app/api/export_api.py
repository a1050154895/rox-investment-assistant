"""数据导出 API — CSV 下载。"""
import csv
import io
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db import get_db
from app.models import Alert, DisciplineProfile, JournalEntry, Position, Setting, User, Watchlist

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


@router.get("/backup")
async def export_backup(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """导出当前账号全部数据为 JSON，用于手动备份（防止免费 PostgreSQL 过期丢数据）。"""
    profile = db.query(DisciplineProfile).filter(DisciplineProfile.user_id == user.id).first()
    payload = {
        "version": 1,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "username": user.username,
        "journal": [e.to_dict() for e in db.query(JournalEntry).filter(JournalEntry.user_id == user.id).order_by(JournalEntry.date.desc()).all()],
        "positions": [p.to_dict() for p in db.query(Position).filter(Position.user_id == user.id).all()],
        "watchlist": [w.to_dict() for w in db.query(Watchlist).filter(Watchlist.user_id == user.id).order_by(Watchlist.sort_order).all()],
        "alerts": [a.to_dict() for a in db.query(Alert).filter(Alert.user_id == user.id).all()],
        "settings": {s.key: s.value for s in db.query(Setting).filter(Setting.user_id == user.id).all()},
        "discipline_profile": profile.profile_json if profile else None,
    }

    output = io.StringIO()
    json.dump(payload, output, ensure_ascii=False, indent=2)
    output.seek(0)
    filename = f"rox-backup-{user.username}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/report")
async def export_report(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """生成一份 Markdown 研究报告：汇总决策复盘、持仓、自选、预警与纪律档案。"""
    journal = db.query(JournalEntry).filter(
        JournalEntry.user_id == user.id
    ).order_by(JournalEntry.date.desc()).all()
    positions = db.query(Position).filter(Position.user_id == user.id).all()
    watchlist = db.query(Watchlist).filter(
        Watchlist.user_id == user.id
    ).order_by(Watchlist.sort_order).all()
    alerts = db.query(Alert).filter(Alert.user_id == user.id).all()
    profile = db.query(DisciplineProfile).filter(
        DisciplineProfile.user_id == user.id
    ).first()

    closed = [e for e in journal if e.result in ("盈", "亏")]
    wins = sum(1 for e in closed if e.result == "盈")
    losses = sum(1 for e in closed if e.result == "亏")
    win_rate = round(wins / len(closed) * 100, 1) if closed else None
    returns = [e.result_pct for e in closed if e.result_pct is not None]
    avg_return = round(sum(returns) / len(returns), 2) if returns else None

    out = []
    out.append("# ROX 研究报告")
    out.append("")
    out.append(f"- 账号：{user.username}")
    out.append(f"- 生成时间：{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")
    out.append("")

    out.append("## 决策复盘")
    out.append("")
    out.append(f"- 总决策：{len(journal)} 条")
    out.append(f"- 已了结：{len(closed)} 条（盈 {wins} / 亏 {losses}）")
    out.append(f"- 胜率：{f'{win_rate}%' if win_rate is not None else '暂无'}")
    out.append(f"- 平均收益率：{f'{avg_return}%' if avg_return is not None else '暂无'}")
    out.append("")
    if journal:
        out.append("| 日期 | 股票 | 代码 | 操作 | 阶段 | 理由 | 结果 | 收益率 |")
        out.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
        for e in journal[:20]:
            out.append(
                f"| {e.date or '-'} | {e.stock or '-'} | {e.code or '-'} | {e.action or '-'} | {e.stage or '-'} "
                f"| {(e.reason or '-')[:40]} | {e.result or '待观察'} | {e.result_pct if e.result_pct is not None else '-'} |"
            )
        out.append("")

    out.append("## 当前持仓")
    out.append("")
    if positions:
        out.append("| 代码 | 名称 | 股数 | 成本价 | 建仓日期 |")
        out.append("| --- | --- | --- | --- | --- |")
        for p in positions:
            out.append(f"| {p.code} | {p.name} | {p.shares} | {p.cost_price} | {p.date or '-'} |")
    else:
        out.append("（暂无持仓）")
    out.append("")

    out.append("## 自选股")
    out.append("")
    if watchlist:
        out.append("| 代码 | 名称 |")
        out.append("| --- | --- |")
        for w in watchlist:
            out.append(f"| {w.code} | {w.name} |")
    else:
        out.append("（暂无自选）")
    out.append("")

    out.append("## 价格预警")
    out.append("")
    if alerts:
        out.append("| 代码 | 名称 | 目标价 | 方向 | 状态 |")
        out.append("| --- | --- | --- | --- | --- |")
        for a in alerts:
            direction = "上穿" if a.direction == "above" else "下穿"
            state = "触发" if a.triggered else ("启用" if a.active else "暂停")
            out.append(f"| {a.code} | {a.name} | {a.target_price} | {direction} | {state} |")
    else:
        out.append("（暂无预警）")
    out.append("")

    out.append("## 334 纪律档案")
    out.append("")
    if profile and profile.profile_json:
        out.append("```json")
        out.append(profile.profile_json)
        out.append("```")
    else:
        out.append("（未录入纪律档案）")

    markdown = "\n".join(out) + "\n"
    filename = f"rox-report-{user.username}-{datetime.now().strftime('%Y%m%d')}.md"
    return StreamingResponse(
        iter([markdown]),
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
