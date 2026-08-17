# ROX 投资助手 — 架构与知识索引

本文是代码结构索引（CodeGraph 价值）与知识图谱（Graphify 价值）的轻量落点：
让后续 Agent 无需通读全部源码即可定位模块、数据流与方法论归属。

## 1. 顶层数据流

```text
Browser (原生 JS SPA, static/js)
   │  /api/* REST (同源)
   ▼
FastAPI (app/main.py)
   ├── api/           路由层：参数校验 + 鉴权 + 编排
   ├── services/      领域层：行情 / 宏观 / 分析引擎（确定性计算）
   ├── core/          横切：配置 / 鉴权 / 安全 / 限流
   ├── db.py + models.py  持久化（SQLAlchemy 2.0）
   └── templates/shell.html  SPA 外壳
```

## 2. 模块图

### api 路由层

| 模块 | 职责 | 依赖的 service |
| --- | --- | --- |
| dashboard.py | 仪表盘聚合 | review_engine / macro_data / contradiction_engine |
| stock.py | 个股透视 | market_data / tencent_data / analysis_engine |
| framework.py | 方法论 / 策略库 / 知识库 | methodology（单一事实源） |
| macro.py | 宏观矩阵 | macro_data |
| review.py | 每日复盘 | review_engine |
| backtest.py | 策略回测 | backtest_engine |
| screener.py | 选股扫描 | screener_engine |
| discipline.py | 334 纪律 | discipline_engine |
| fundamentals.py | 基本面估值 | fundamentals_engine |
| intelligence.py | 资讯情报 | intelligence_data |
| journal.py / portfolio.py / watchlist.py / alerts.py / settings_api.py | 日志 / 持仓 / 自选 / 预警 / 设置 | db / models |
| auth.py | 注册 / 登录 / 登出 / 当前用户 | core.auth |
| export_api.py | 备份导出 / Markdown 报告 | db / 各 service |
| ai.py | AI 对话（SSE） | ai_service |

### services 领域层

| 模块 | 性质 | 说明 |
| --- | --- | --- |
| market_data.py | 行情降级源 | 内置可信快照 + 数据状态标签 |
| tencent_data.py | 行情主源 | 腾讯自选股公开接口 + 短时缓存 |
| intelligence_data.py | 资讯 + 板块资金 | AKShare 接口 + 快照降级 |
| macro_data.py | L1 宏观矩阵 | 财政信用 × 价值实现，AKShare + 降级快照 |
| contradiction_engine.py | L3 矛盾分析 | 量价/资金/结构/预期四类矛盾强度 |
| analysis_engine.py | L5 个股一致性 | 确定性估值/资金/质量/纪律加权 |
| review_engine.py | 每日复盘 | 指数/广度/板块/情绪 |
| backtest_engine.py | 策略回测 | 确定性收益计算 |
| screener_engine.py / fundamentals_engine.py / discipline_engine.py | 选股 / 估值 / 纪律 | 确定性计算 |
| ai_service.py | AI 对话 | 提示词编排，不伪造行情 |
| methodology.py | **静态方法论单一事实源** | L1-L5 蒸馏知识 + 策略库 + 知识库 |

## 3. 方法论归属（知识图谱）

卢麒元五层逻辑链，数据在 `app/services/methodology.py`，实时计算分散在对应 engine：

| 层级 | 名称 | 静态知识 | 实时计算 |
| --- | --- | --- | --- |
| L1 | 宏观定调 | methodology.L1 | macro_data.get_macro_matrix |
| L2 | 资本周期 | methodology.L2 | review_engine（盘面特征） |
| L3 | 矛盾分析 | methodology.L3 | contradiction_engine.get_contradictions |
| L4 | 334 纪律 | methodology.L4 | discipline_engine |
| L5 | 一致性评分 | methodology.L5 | analysis_engine.build_analysis |

## 4. 数据可信度契约

任何返回给前端的行情/宏观数据都应携带来源与时效语义：
`realtime` / `snapshot` / `unavailable` / `stale`。失败时逐级降级，**禁止生成模拟数据**。
