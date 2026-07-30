"""ROX投资助手 — FastAPI 应用入口"""
import os

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from app.core.config import settings
from app.core.security import SecurityHeadersMiddleware
from app.api import dashboard, stock, journal, framework, settings_api, intelligence, discipline, macro

app = FastAPI(
    title="ROX投资助手",
    version="3.2.0",
    description="投资认知系统 — 宏观定调 · 矛盾追踪 · 334纪律 · 决策日志",
)

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
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(stock.router, prefix="/api/stock", tags=["stock"])
app.include_router(journal.router, prefix="/api/journal", tags=["journal"])
app.include_router(framework.router, prefix="/api/framework", tags=["framework"])
app.include_router(settings_api.router, prefix="/api/settings", tags=["settings"])
app.include_router(intelligence.router, prefix="/api/intelligence", tags=["intelligence"])
app.include_router(discipline.router, prefix="/api/discipline", tags=["discipline"])
app.include_router(macro.router, prefix="/api/macro", tags=["macro"])


# ========== Health Check (必须在 catch-all 之前) ==========

@app.get("/health")
async def health():
    return {"status": "ok", "version": "3.2.0", "name": "ROX投资助手"}


@app.get("/ready")
async def ready():
    """就绪检查：当前阶段验证应用配置和关键服务可加载。"""
    from app.services.market_data import REAL_QUOTES
    checks = {
        "configuration": {"status": "ok", "environment": settings.ENVIRONMENT},
        "market_snapshot": {"status": "ok" if REAL_QUOTES else "degraded", "symbols": len(REAL_QUOTES)},
        "database": {"status": "not_configured", "message": "PostgreSQL 将在下一阶段接入"},
    }
    return {"status": "degraded" if checks["database"]["status"] != "ok" else "ok", "checks": checks}


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
