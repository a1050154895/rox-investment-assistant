# ROX投资助手

投资认知系统 — 宏观定调 · 矛盾追踪 · 334纪律 · 决策日志

## 本地运行

```bash
# 安装依赖
pip install -r requirements.txt

# 启动
uvicorn app.main:app --host 0.0.0.0 --port 8008 --reload

# 访问
open http://localhost:8008
```

## Render 部署

1. 将项目推送到 GitHub
2. 在 Render 控制台创建 Web Service，选择该仓库
3. 配置：
   - Runtime: Python 3
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. 或直接使用 `render.yaml`（已包含配置）

## 功能

- **仪表盘** — 宏观指南针、资本周期阶段、矛盾追踪、334仓位纪律、自选股概览、最近决策
- **个股透视** — K线图(ECharts)、框架一致性评分、矛盾分析、价值规律评估、技术指标
- **决策日志** — 时间线、框架依据、一致性评分、事后复盘、统计概览
- **认知框架** — 五层逻辑链方法论、策略库、知识库

## 技术栈

- FastAPI + Jinja2 (后端)
- 原生 JS SPA (前端，零构建依赖)
- ECharts (图表)
- 统一 Design Token 系统
- 响应式设计 (桌面/平板/手机)
