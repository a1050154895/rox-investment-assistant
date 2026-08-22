"""ROX投资助手 — FastAPI 应用入口"""
import logging
import os
import time

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from app.core.config import settings
from app.core.limiter import limiter
from app.core.security import SecurityHeadersMiddleware
from app.db import DB_BACKEND, check_database, init_db

# 结构化日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-5s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("rox")
from app.api import (
    dashboard, stock, journal, framework, settings_api, intelligence,
    discipline, macro, auth, ai, screener, backtest, review, fundamentals, portfolio, export_api, alerts, watchlist,
    guide, research, funds, data,
)

app = FastAPI(
    title="ROX投资助手",
    version="4.17.0",
    description="投资认知系统 — 宏观定调 · 矛盾追踪 · 334纪律 · 决策日志",
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """请求耗时日志（跳过静态文件）。"""
    start = time.time()
    response = await call_next(request)
    elapsed = (time.time() - start) * 1000
    if not request.url.path.startswith("/static"):
        logger.info("%s %s → %d (%.0fms)", request.method, request.url.path, response.status_code, elapsed)
    return response


# 启动时建表（幂等）
init_db()

# Rate limiting — 全局 200/min，登录 5/min
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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
app.include_router(review.router, prefix="/api/review", tags=["review"])
app.include_router(fundamentals.router, prefix="/api/fundamentals", tags=["fundamentals"])
app.include_router(portfolio.router, prefix="/api/portfolio", tags=["portfolio"])
app.include_router(export_api.router, prefix="/api/export", tags=["export"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["alerts"])
app.include_router(watchlist.router, prefix="/api/watchlist", tags=["watchlist"])
app.include_router(guide.router, prefix="/api/guide", tags=["guide"])
app.include_router(research.router, prefix="/api/research", tags=["research"])
app.include_router(funds.router, prefix="/api/funds", tags=["funds"])
app.include_router(data.router, prefix="/api/data", tags=["data"])


# ========== Health Check (必须在 catch-all 之前) ==========

@app.get("/health")
async def health():
    from app.core.auth import KEY_SOURCE
    return {
        "status": "ok",
        "version": app.version,
        "name": "ROX投资助手",
        "db_persistent": DB_BACKEND == "postgresql",
        "key_source": KEY_SOURCE,
    }


@app.get("/ready")
async def ready():
    """就绪检查：数据库连接与关键服务状态。"""
    from app.services.market_data import REAL_QUOTES
    from app.core.auth import KEY_SOURCE
    db_ok = check_database()
    checks = {
        "configuration": {"status": "ok", "environment": settings.ENVIRONMENT},
        "auth": {
            "status": "ok" if KEY_SOURCE == "env" else "degraded",
            "key_source": KEY_SOURCE,
            "message": "SECRET_KEY 来自环境变量，稳定" if KEY_SOURCE == "env" else "SECRET_KEY 为随机生成 — 重启后所有 JWT 失效，请设置 SECRET_KEY 环境变量",
        },
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
    return templates.TemplateResponse(request, "shell.html", {"version": app.version})


@app.get("/{path:path}", response_class=HTMLResponse)
async def spa_fallback(request: Request, path: str):
    """SPA 路由兜底 — 所有非 API/static 路径返回壳页面"""
    if path.startswith("api/") or path.startswith("static/"):
        return HTMLResponse(status_code=404, content="Not Found")
    if templates is None:
        return "<h1>ROX投资助手</h1><p>模板未找到</p>"
    return templates.TemplateResponse(request, "shell.html", {"version": app.version})


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8008))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)
