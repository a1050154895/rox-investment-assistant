"""ROX投资助手 — FastAPI 应用入口"""
import os

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from app.core.config import settings
from app.core.security import SecurityHeadersMiddleware
from app.db import DB_BACKEND, check_database, init_db
from app.api import (
    dashboard, stock, journal, framework, settings_api, intelligence,
    discipline, macro, auth, ai, screener, backtest,
)

app = FastAPI(
    title="ROX投资助手",
    version="3.5.0",
    description="投资认知系统 — 宏观定调 · 矛盾追踪 · 334纪律 · 决策日志",
)

# 启动时建表（幂等）
init_db()

# 安全响应头与统一错误响应
app.add_middleware(SecurityHeadersMiddleware)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件
static_path = os.path.join(settings.BASE_DIR, "static")
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")

# 模板
templates_path = os.path.join(settings.BASE_DIR, "templates")
templates = Jinja2Templates(directory=templates_path) if os.path.exists(templates_path) else None

# 注册 API 路由
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(stock.router, prefix="/api/stock", tags=["stock"])
app.include_router(journal.router, prefix="/api/journal", tags=["journal"])
app.include_router(framework.router, prefix="/api/framework", tags=["framework"])
app.include_router(settings_api.router, prefix="/api/settings", tags=["settings"])
app.include_router(intelligence.router, prefix="/api/intelligence", tags=["intelligence"])
app.include_router(discipline.router, prefix="/api/discipline", tags=["discipline"])
app.include_router(macro.router, prefix="/api/macro", tags=["macro"])
app.include_router(ai.router, prefix="/api/ai", tags=["ai"])
app.include_router(screener.router, prefix="/api/screener", tags=["screener"])
app.include_router(backtest.router, prefix="/api/backtest", tags=["backtest"])


# ========== Health Check (必须在 catch-all 之前) ==========

@app.get("/health")
async def health():
    return {"status": "ok", "version": "3.5.0", "name": "ROX投资助手"}


@app.get("/ready")
async def ready():
    """就绪检查：数据库连接与关键服务状态。"""
    from app.services.market_data import REAL_QUOTES
    db_ok = check_database()
    checks = {
        "configuration": {"status": "ok", "environment": settings.ENVIRONMENT},
        "database": {
            "status": "ok" if db_ok else "error",
            "backend": DB_BACKEND,
            "message": "PostgreSQL" if DB_BACKEND == "postgresql" else "SQLite（生产建议配置 DATABASE_URL 使用 PostgreSQL）",
        },
        "market_snapshot": {"status": "ok" if REAL_QUOTES else "degraded", "symbols": len(REAL_QUOTES)},
    }
    return {
        "status": "ok" if db_ok else "degraded",
        "checks": checks,
    }


# ========== SPA 前端路由 ==========

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """SPA 壳页面 — 所有视图通过前端路由渲染"""
    if templates is None:
        return "<h1>ROX投资助手</h1><p>模板未找到</p>"
    return templates.TemplateResponse("shell.html", {"request": request})


@app.get("/{path:path}", response_class=HTMLResponse)
async def spa_fallback(request: Request, path: str):
    """SPA 路由兜底 — 所有非 API/static 路径返回壳页面"""
    if path.startswith("api/") or path.startswith("static/"):
        return HTMLResponse(status_code=404, content="Not Found")
    if templates is None:
        return "<h1>ROX投资助手</h1><p>模板未找到</p>"
    return templates.TemplateResponse("shell.html", {"request": request})


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8008))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)
