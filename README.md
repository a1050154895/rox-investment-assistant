# ROX 投资助手

> 面向中国股票市场研究场景的投资认知与决策辅助系统。

ROX 将宏观变量、公开政策、全球风险、产业链传导、市场行情与投资纪律组织为一套可追溯的研究工作流，帮助用户区分**事实线索、分析假设与交易结论**。

**线上演示：** [https://rox-investment-assistant.onrender.com](https://rox-investment-assistant.onrender.com)

> [!IMPORTANT]
> 本项目目前处于生产化改造阶段，定位为信息整理与研究辅助工具，不构成投资建议、收益承诺或自动荐股服务。市场数据可能是延时快照；数据不可用时系统会明确标示，不会生成模拟行情或随机研判结果。

## 目录

- [产品定位](#产品定位)
- [最终顶层设计](#最终顶层设计)
- [核心能力](#核心能力)
- [移动端现状与适配计划](#移动端现状与适配计划)
- [可信数据原则](#可信数据原则)
- [技术架构](#技术架构)
- [项目结构](#项目结构)
- [快速开始](#快速开始)
- [环境变量](#环境变量)
- [API 概览](#api-概览)
- [测试与质量检查](#测试与质量检查)
- [部署到 Render](#部署到-render)
- [安全基线](#安全基线)
- [当前限制](#当前限制)
- [推荐技能与工具](#推荐技能与工具)
- [后续路线图](#后续路线图)
- [风险声明](#风险声明)

## 产品定位

ROX 不试图用单一指标预测涨跌，而是把投资研究拆成五类可验证问题：

1. **宏观环境**：增长、通胀、利率、汇率、能源、贸易和供应链发生了什么变化？
2. **政策传导**：公开政策会经过哪些行业和利润链条影响上市公司？
3. **产业与资金**：资本、订单、产能和资金流正在向哪里集中或扩散？
4. **个股价值**：估值、盈利能力、行情与资金信息是否支持当前假设？
5. **决策纪律**：结论的依据、触发条件、仓位阶段和事后复盘是否完整？

系统强调“先验证，再决策”：资讯标题只作为线索，政策文本只作为事实来源，所有研判都需要通过后续数据验证。

## 最终顶层设计

ROX 的最终定位是：

> **面向主动投资者的证据优先投研工作台，把市场信息、研究判断、决策纪律和事后复盘连接成一个可验证闭环。**

ROX 不是行情终端、AI 荐股机器人、自动交易系统或情绪预测软件。它的核心价值是：

```text
把感知变成研究
把研究变成决策
把决策变成复盘
把复盘变成下一次更好的判断
```

### 唯一核心对象：研究卡

所有市场对象都应能进入同一张研究卡：

- 股票
- ETF/基金
- 指数
- 行业/概念
- 宏观主题

研究卡由四层组成：

```text
研究对象 → 判断 → 证据 → 结果
```

正式研究至少包含：研究问题、核心假设、关键事实、反证、失效条件、数据来源、观察日期、风控边界和下次复核日期。

### ROX Loop

```text
今日队列 → 发现对象/事件 → 创建研究卡 → 收集证据
→ 写出假设 → 主动寻找反证 → 硬性风控
→ 记录决策 → 跟踪变化 → 验证假设 → 复盘沉淀
```

### GlobalPulse 的借鉴边界

GlobalPulse（全球资讯量化系统）值得研究的部分是：新闻专题主线、热度排序、关键词关注、突发事件置顶、全球变量聚合和多来源信息组织。这些能力可补充 ROX 的情报入口。

ROX 不复制其 3D 概念星图、代码残影 HUD、次日涨跌预测、情绪置信度或“快人一步”的交易营销。ROX 将相关能力转化为：

```text
事实线索 → 事件主题 → 传导路径 → 行业影响 → 验证动作 → 加入研究卡
```

### AI 的最终位置

AI 是增强层，不是核心功能的前置条件：

1. **无 AI 模式**：研究卡、数据、风控、决策和复盘完整可用。
2. **平台 AI**：摘要、事实/观点拆分、研究问题改写、反证提示和复盘归纳。
3. **BYOK 模式**：高级用户可接入 OpenAI 兼容 API、DeepSeek、Claude、Gemini、Ollama 或企业模型。

AI 可以整理、解释、追问和归纳，但不能荐股、自动调仓、覆盖硬性风控或伪造数据。用户自带模型是高级能力，不是使用门槛。

## 核心能力

### 仪表盘

- 宏观指南针与主权信用/价值实现方法框架
- 资本周期阶段模型与状态说明
- 主要矛盾、次要矛盾和验证纪律
- 334 仓位方法论基准（核心 30% / 卫星 30% / 现金 40%）
- 自选股行情快照及数据状态
- 政策、全球变量和资讯线索摘要

### 个股透视

- 股票代码与名称搜索
- 行情快照、涨跌幅、估值及行业信息
- 基于真实 K 线的 ECharts 蜡烛图
- 基于有效输入的确定性多维分析
- RSI、KDJ、MACD、均线与布林带技术指标
- 资金流状态及宏观/政策/产业链传导说明
- 数据来源、数据日期、实时/快照/不可用状态

### 基金/ETF透视

- 常用 ETF 搜索与研究透视
- 场内价格、价格 K 线和区间风险指标
- 区间收益、最大回撤、波动代理和样本日期
- 跟踪指数、基金类型、宽基/行业分类
- 数据覆盖矩阵：场内价格、K 线、净值、IOPV、折溢价、持仓、跟踪误差
- 一键创建研究卡与关联决策
- 净值、IOPV、持仓或跟踪误差不可用时明确显示，不用交易价格替代

### 宏观情报

- 公开市场资讯线索
- 公开政策跟踪及行业传导路径
- 全球增长、利率与汇率、能源与航运、供应链风险观察
- 行业资金和产业链验证清单
- 新闻事实与研究判断分层展示
- 支持手动刷新短时缓存

### 决策日志

- 新建、查看、更新和删除决策记录
- 记录股票、动作、周期阶段、框架评分和决策理由
- 补充结果与事后复盘
- 汇总样本、胜率和错误模式

> 决策日志已持久化到数据库（生产 PostgreSQL / 本地 SQLite），并按用户账号隔离，实例重启不丢失。

### 认知框架

- 五层研究逻辑链
- 资本周期、矛盾分析、价值规律和 334 纪律方法说明
- 策略库与知识库接口
- 无可靠数据时只展示方法结构，不输出确定性市场判断

### 响应式界面

- 桌面、平板和手机布局（桌面端为当前主场景）
- “战略文房”暖墨与朱砂视觉系统
- 移动端底部五项导航
- 加载、空数据和接口失败状态
- 浏览器缩放与基础键盘可访问性

> 桌面端的信息密度与研究卡片布局已基本稳定；手机端核心路径已完成第一轮适配，
> 高级页面、首次使用引导和正式自动化 E2E 仍需继续完善，详见
> [移动端现状与适配计划](#移动端现状与适配计划)。

## 移动端现状与适配计划

当前状态：桌面端体验较好；今日页、个股页、研究卡、决策日志和复盘页已完成第一轮手机适配，正在继续收敛细节。

已知问题集中在六类：

| 类别 | 现状 | 改造方向 |
| --- | --- | --- |
| 触控尺寸 | 部分按钮和列表项小于 44×44px，单手易误触 | 统一最小触控目标，扩大热区 |
| 文字密度 | 11px 字号偏小，卡片内信息过密 | 移动端提升正文到 13–15px，弱化次要信息 |
| 滑块与输入 | 数值滑块、日期选择在手机上操作困难 | 改用可点击步进、分段控件或原生控件 |
| 图表交互 | K 线缩放、十字线在触屏上不跟手 | 明确双指缩放与长按提示，提供暂停/恢复 |
| 横向布局 | 核心页面已完成无溢出验收，高级页面仍需回归 | 表格改卡片/抽屉，指标改两列自适应 |
| 弹窗与底部导航 | 核心页面已处理；首次引导仍会覆盖工作区 | 使用安全区与 `100dvh`，引导改为不阻断核心任务 |

适配原则：

1. 先修“用起来难受”的高频路径：今日队列、个股页、研究卡、决策日志。
2. 触控与可读性优先于信息密度，不把桌面端的所有指标硬塞进手机。
3. 用 `ui-ux-pro-max` 作为响应式与无障碍验收门槛，用浏览器截图做真机尺寸回归。
4. 不改动后端数据契约，纯前端渐进增强，分多次小改动验证，避免大范围重写。
5. 已用本地浏览器在 375/390/414px 验证核心路径无横向溢出；正式 E2E 与 Lighthouse 仍待接入。

## 可信数据原则

自 `3.1.x` 起，ROX 执行以下数据纪律：

- **不生成模拟行情**：数据源失败时不补造 K 线、成交量或价格。
- **不生成随机评分**：同一组输入得到相同结果，缺失输入不会被随机数替代。
- **不伪造技术指标**：只有真实 K 线满足最小样本要求时才计算指标。
- **不伪造资金流**：资金数据缺失时返回 `unavailable`。
- **不把方法论当实时结论**：没有可靠宏观数据时显示“未评估”。
- **不预置虚构收益**：默认决策日志为空，不展示虚构历史收益。

主要数据状态：

| 状态 | 含义 |
| --- | --- |
| `realtime` | 数据源返回的实时或近实时数据 |
| `snapshot` | 内置或缓存的历史快照，可能已经过期 |
| `unavailable` | 当前没有可靠数据，拒绝生成替代值 |
| `stale` | 数据时间早于预期，使用时需要谨慎 |

所有研究数据逐步统一为以下契约：

```json
{
  "data_status": "realtime",
  "data_source": "腾讯自选股公开指数接口",
  "as_of": "2026-08-22 10:15:32",
  "stale": false,
  "coverage": "full",
  "message": null
}
```

允许状态：`realtime`、`snapshot`、`stale`、`unavailable`、`partial`。接口会附带 `data_source`、`as_of`、`stale` 和缺失原因，帮助前端解释数据来源和时效。

## 技术架构

| 层级 | 技术 | 说明 |
| --- | --- | --- |
| Web 服务 | FastAPI + Uvicorn | REST API、健康检查和 SPA 路由 |
| 模板 | Jinja2 | 输出单页应用外壳 |
| 前端 | 原生 JavaScript SPA | 无构建步骤，客户端路由与视图渲染 |
| 可视化 | Apache ECharts 5 | K 线和资金趋势图 |
| 市场数据 | 腾讯自选股公开接口（行情/K线/搜索）→ AKShare → 可信快照降级 | 行情与 K 线实时；失败时逐级降级，绝不生成模拟数据 |
| 样式 | 原生 CSS + Design Tokens | 响应式“战略文房”设计系统 |
| 测试 | pytest + Playwright + Lighthouse | 后端、移动端关键路径 E2E、无障碍和最佳实践审计 |
| 部署 | Render Web Service | 使用 `render.yaml` 自动配置 |

当前为**单体全栈应用**：浏览器通过同源 REST API 获取数据，不需要独立前端服务，也没有 WebSocket/SSE 实时通道。

```text
Browser
   │
   ├── HTML / CSS / JavaScript SPA
   │
   └── /api/* REST
          │
       FastAPI
          ├── dashboard / stock / intelligence
          ├── journal / framework / settings
          ├── analysis_engine（确定性分析）
          ├── market_data（行情与降级状态）
          └── intelligence_data（资讯与宏观线索）
```

## 项目结构

```text
rox-investment-assistant/
├── app/
│   ├── api/                    # REST 路由（18 个模块）
│   │   ├── auth.py             # 注册 / 登录 / 当前用户
│   │   ├── dashboard.py
│   │   ├── stock.py
│   │   ├── intelligence.py
│   │   ├── journal.py
│   │   ├── framework.py
│   │   ├── settings_api.py
│   │   ├── discipline.py       # 334 纪律
│   │   ├── macro.py            # 宏观矩阵
│   │   ├── ai.py               # AI 对话（含 SSE）
│   │   ├── screener.py         # 选股扫描
│   │   ├── backtest.py         # 策略回测
│   │   ├── review.py           # 每日复盘
│   │   ├── fundamentals.py     # 基本面估值
│   │   ├── portfolio.py        # 持仓
│   │   ├── export_api.py       # 数据导出
│   │   ├── alerts.py           # 价格预警
│   │   └── watchlist.py        # 自选股
│   ├── core/
│   │   ├── config.py           # 环境配置与 CORS 白名单
│   │   ├── auth.py             # PBKDF2 密码哈希 + JWT
│   │   ├── security.py         # 请求 ID、错误处理与安全响应头
│   │   └── limiter.py          # slowapi 请求限流
│   ├── services/
│   │   ├── market_data.py      # 市场行情、K 线与资金数据
│   │   ├── tencent_data.py     # 腾讯行情接口 + 短时缓存
│   │   ├── analysis_engine.py  # 确定性分析与技术指标
│   │   ├── fundamentals_engine.py
│   │   ├── macro_data.py
│   │   ├── discipline_engine.py
│   │   ├── screener_engine.py
│   │   ├── backtest_engine.py
│   │   ├── review_engine.py
│   │   ├── ai_service.py
│   │   └── intelligence_data.py
│   ├── db.py                   # SQLAlchemy 2.0 + DATABASE_URL 降级
│   ├── models.py               # 用户 / 日志 / 纪律 / 设置 / 持仓 / 预警 / 自选股
│   └── main.py                 # FastAPI 应用入口
├── static/
│   ├── css/                    # Design Tokens 与响应式样式
│   ├── js/                     # SPA 内核和 12 个页面视图
│   └── manifest.json           # PWA 清单
├── templates/shell.html        # SPA 页面外壳
├── tests/                      # pytest：可信数据 + API 冒烟测试
├── .env.example                # 环境变量示例
├── render.yaml                 # Render Blueprint
├── requirements.txt
└── README.md
```

> `dist/` 是早期静态预览产物，不是 Render 生产服务的运行入口；正式服务使用 `templates/`、`static/` 和 `app/`。

## 快速开始

### 1. 获取项目

```bash
git clone https://github.com/a1050154895/rox-investment-assistant.git
cd rox-investment-assistant
```

### 2. 创建虚拟环境

建议使用 Python 3.11：

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell：

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. 安装依赖

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. 配置环境

```bash
cp .env.example .env
```

当前配置类直接读取进程环境。开发环境使用默认值即可；如需覆盖，请先导出变量：

```bash
export ENVIRONMENT=development
export ALLOWED_ORIGINS=http://localhost:8008,http://127.0.0.1:8008
export PORT=8008
```

### 5. 启动应用

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8008 --reload
```

访问：

- 应用：<http://localhost:8008>
- OpenAPI：<http://localhost:8008/docs>
- 健康检查：<http://localhost:8008/health>
- 就绪检查：<http://localhost:8008/ready>

## 环境变量

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `ENVIRONMENT` | `development` | 运行环境；Render 设置为 `production` |
| `ALLOWED_ORIGINS` | 本地两个来源 | 逗号分隔的 CORS 允许来源 |
| `PORT` | `8008` | 本地运行端口；Render 使用平台 `$PORT` |
| `DATABASE_URL` | 未设置（自动 SQLite） | 生产建议配置 PostgreSQL 连接串；未设置时本地使用 `data/rox.db` |
| `SECRET_KEY` | 自动生成 | JWT 签名密钥；生产必须显式设置，否则重启后登录全部失效 |
| `AI_API_KEY` | 未设置 | 可选全局 AI 服务密钥；用户也可登录后在「设置 → AI模型」中自行填写 |

生产环境默认只允许：

```text
https://rox-investment-assistant.onrender.com
```

如果使用自定义域名，需要同步更新 Render 的 `ALLOWED_ORIGINS`。

## API 概览

FastAPI 自动提供 `/docs` 和 `/openapi.json`。主要接口如下：

### 系统

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/health` | 存活检查与应用版本 |
| GET | `/ready` | 配置、市场快照和数据库就绪状态 |

### 账户认证

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| POST | `/api/auth/register` | 注册并返回 JWT |
| POST | `/api/auth/login` | 登录并返回 JWT |
| GET | `/api/auth/me` | 当前用户信息 |

### 仪表盘

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/api/dashboard/overview` | 仪表盘聚合数据 |
| GET | `/api/dashboard/market_heatmap` | 板块热力图；无可靠数据时返回不可用状态 |
| GET | `/api/dashboard/stats` | 决策胜率、持仓盈亏、预警、自选股数量统计 |

### 股票

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/api/stock/search?q=茅台` | 按代码或名称搜索股票 |
| GET | `/api/stock/{code}` | 行情和基础信息 |
| GET | `/api/stock/{code}/kline?period=daily&limit=120` | 真实 K 线及数据状态 |
| GET | `/api/stock/{code}/analysis` | 确定性框架分析 |
| GET | `/api/stock/{code}/indicators` | 基于真实 K 线计算技术指标 |

### 基本面估值

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/api/fundamentals/{code}` | 个股基本面概览 |
| GET | `/api/fundamentals/{code}/dcf` | DCF 估值（参数可调） |
| GET | `/api/fundamentals/{code}/comps` | 可比公司估值 |

### 宏观情报

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/api/intelligence/brief` | 资讯、政策、全球风险和行业资金简报 |
| GET | `/api/intelligence/brief?refresh=true` | 绕过短时缓存手动刷新 |
| GET | `/api/intelligence/stock/{code}` | 个股关联的传导路径与验证清单 |

### 宏观矩阵

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/api/macro/matrix` | 财政信用 × 价值实现 宏观矩阵 |

### 决策日志

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/api/journal/` | 获取日志列表 |
| POST | `/api/journal/` | 新建决策日志 |
| GET | `/api/journal/{decision_id}` | 获取单条记录 |
| PUT | `/api/journal/{decision_id}` | 更新记录与复盘 |
| DELETE | `/api/journal/{decision_id}` | 删除记录 |
| GET | `/api/journal/stats/summary` | 汇总统计 |
| POST | `/api/journal/review` | 生成规则化复盘摘要 |

### 持仓

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/api/portfolio/` | 持仓列表 |
| POST | `/api/portfolio/` | 新建持仓 |
| PUT | `/api/portfolio/{pos_id}` | 更新持仓 |
| DELETE | `/api/portfolio/{pos_id}` | 删除持仓 |

### 自选股

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/api/watchlist/` | 自选股列表（附带行情） |
| POST | `/api/watchlist/` | 加入自选（重复返回已有记录） |
| DELETE | `/api/watchlist/{item_id}` | 移除自选 |
| PUT | `/api/watchlist/reorder` | 批量调整排序 |

### 价格预警

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/api/alerts/` | 预警列表 |
| POST | `/api/alerts/` | 新建预警 |
| PUT | `/api/alerts/{alert_id}` | 更新或激活/暂停预警 |
| DELETE | `/api/alerts/{alert_id}` | 删除预警 |

### 选股扫描

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/api/screener/presets` | 选股预设 |
| POST | `/api/screener/scan` | 执行扫描 |

### 策略回测

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/api/backtest/strategies` | 回测策略库 |
| GET | `/api/backtest/stocks` | 可回测股票列表 |
| POST | `/api/backtest/run` | 运行回测 |

### 334 纪律

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/api/discipline/defaults` | 纪律默认参数 |
| POST | `/api/discipline/evaluate` | 执行纪律检查 |
| GET | `/api/discipline/profile` | 获取纪律档案 |
| PUT | `/api/discipline/profile` | 保存纪律档案 |

### 每日复盘

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/api/review/daily` | 今日复盘 |
| GET | `/api/review/history` | 复盘历史 |

### 数据导出

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/api/export/journal` | 导出决策日志 CSV |
| GET | `/api/export/portfolio` | 导出持仓 CSV |

### AI 助手

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/api/ai/status` | AI 配置状态（不回传密钥） |
| POST | `/api/ai/chat` | AI 对话 |
| POST | `/api/ai/chat/stream` | AI 对话（SSE 流式） |

### 框架与设置

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/api/framework/methodology` | 五层方法论 |
| GET | `/api/framework/strategies` | 策略库 |
| GET | `/api/framework/knowledge` | 知识库 |
| GET/PUT | `/api/settings/` | 当前运行期设置 |
| GET | `/api/settings/membership` | 会员信息（基于用户真实 plan，无假数据） |

## 测试与质量检查

### 运行测试

```bash
PYTHONPATH=. python -m pytest tests/ -v
```

现有 86 个后端测试覆盖，并由 Playwright E2E 与 Lighthouse 移动审计补充前端质量检查：

- 健康检查与就绪检查
- 注册 / 登录 / 鉴权与账号级数据隔离
- 决策日志、持仓、预警、自选股 CRUD 与统计
- 可信数据层：股票代码标准化、分析确定性、K 线样本不足拒算指标、未知股票不造数据

### Python 编译检查

```bash
python -m compileall -q app
```

### JavaScript 语法检查

需要 Node.js 18+：

```bash
find static/js -name '*.js' -print0 | xargs -0 -n1 node --check
```

### Git 差异检查

```bash
git diff --check
```

发布前建议至少执行以上四类检查，并验证 `/health`、`/ready`、仪表盘、个股页和手机底部导航。推送到 `main` 分支后，GitHub Actions 会自动运行 pytest、flake8 和前端 JS 语法检查。

## 部署到 Render

仓库包含 `render.yaml`，可使用 Render Blueprint 创建服务。

### Blueprint 部署

1. Fork 或推送本仓库到 GitHub。
2. 登录 [Render Dashboard](https://dashboard.render.com)。
3. 选择 **New → Blueprint**。
4. 连接仓库并确认 `render.yaml`。
5. 创建服务并等待首次构建。

当前 Blueprint 配置：

```yaml
services:
  - type: web
    name: rox-investment-assistant
    runtime: python
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### 手动创建 Web Service

| 配置项 | 值 |
| --- | --- |
| Runtime | Python |
| Branch | `main` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Health Check Path | `/health` |
| Environment | `ENVIRONMENT=production` |

在 **Settings → Build & Deploy** 中开启 Auto-Deploy 后，每次推送 `main` 都会触发构建。如果没有自动触发，可选择 **Manual Deploy → Deploy latest commit**。

### 部署验收

```bash
curl https://rox-investment-assistant.onrender.com/health
curl https://rox-investment-assistant.onrender.com/ready
curl https://rox-investment-assistant.onrender.com/api/intelligence/brief
```

预期：

- `/health` 返回 `status: ok` 和当前版本。
- `/ready` 返回 JSON；数据库已接入时总体状态为 `ok`（本地 SQLite 或生产 PostgreSQL）。
- 情报接口返回 `news`、`global_risk`、`policy_tracker` 和 `sector_flow`。

> Render 免费实例会在闲置后休眠，首次访问可能需要等待冷启动。正式运营应使用不休眠实例，并配置监控、备份和回滚。

## 安全基线

当前版本已经具备：

- 请求 ID（`X-Request-ID`）
- 统一服务端 500 错误结构
- 内容安全策略（CSP）
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy`
- 摄像头、麦克风、定位权限禁用
- 生产 CORS 显式白名单
- 关键日志字段前端转义
- Git 仓库不保存真实环境变量和访问令牌

当前 API 已具备多用户 JWT 鉴权、账号级数据隔离与接口限流（全局 200 次/分钟、登录 5 次/分钟）；找回密码与 RBAC 仍在路线图中，正式收费服务前需补齐并完成合规审核。

### 密钥安全

- 不要把 GitHub Token、数据供应商密钥或密码写入代码、README、Git 远程 URL。
- 使用 Render Environment Variables 或本地 `.env` 管理秘密。
- 如果密钥曾出现在聊天、日志或提交历史中，应立即撤销并轮换。
- 提交前建议运行密钥扫描工具，例如 Gitleaks。

## 当前限制

| 领域 | 当前状态 |
| --- | --- |
| 数据授权 | AKShare 用于研发验证；商业展示和再分发前需确认供应商许可 |
| 行情时效 | 行情与 K 线经腾讯自选股公开接口实时获取（沪深京全市场）；个别新股或数据源异常时降级快照/不可用 |
| 新闻版权 | 仅应使用允许抓取、摘要和展示的公开来源 |
| 数据库 | 已接入（生产 PostgreSQL / 本地 SQLite 自动降级），日志、设置、纪律档案按用户持久化 |
| 用户体系 | 已支持注册、登录（JWT + PBKDF2 哈希）与账号级数据隔离；找回密码、RBAC 待实现 |
| AI 服务 | 已接入真实后端（OpenAI 兼容），需配置 API Key；AI 仅做解释/复盘，不覆盖硬性风控规则 |
| 缓存 | 行情接口有 30 秒进程内 TTL 缓存，实例重启后失效；无 Redis |
| 任务系统 | 暂无独立采集 Worker、消息队列和定时任务 |
| 可观测性 | 有请求 ID，但尚无集中日志、错误追踪和告警 |
| 移动端 | 核心路径已完成 UI 2.0 适配；375/390/414px 已做浏览器验收 |
| 测试 | 已有 86 个后端测试，并接入 Playwright E2E 与 Lighthouse 移动审计 |
| 基金/ETF | 已支持 ETF 透视、价格风险指标、证据覆盖矩阵与关联决策；净值/IOPV/持仓/跟踪误差待可靠数据源 |
| 研究卡 | 已支持生命周期、假设状态、下次复核日期和决策关联；跨页面证据抽屉待实现 |
| 主题 | 当前以深色“战略文房”为主，完整 light/dark/system 切换待实现 |
| 商业合规 | 用户协议、隐私政策、风险揭示和法律审核尚未完成 |

## 推荐技能与工具

以下按适用性整理，用于后续改造与质量验收，不要求一次性全部接入。

### 已在当前环境可用

| 技能 | 用途 | 采用建议 |
| --- | --- | --- |
| ui-ux-pro-max | 响应式、可访问性、金融图表语义的验收门槛 | 立即用于移动端适配与回归 |
| awesome-design-md | “战略文房”视觉语言与 DESIGN.md 决策 | 移动端改造前先对齐品牌约束 |
| browser:control-in-app-browser | 真机尺寸截图、点击与可访问性检查 | 用于移动端 E2E 截图回归 |
| graphify | 代码结构/知识图谱索引 | 项目规模更大后按需启用 |

### 检索到的公开技能（建议评估后采用）

| 仓库 | 用途 | 采用建议 |
| --- | --- | --- |
| ceorkm/mobile-app-ui-design | 移动端 UI/UX 设计规范（264 stars） | 作为移动端触控/层级参考 |
| dungnotnull/mobile-app-uxui-audit-agent-skill | 移动端 UX 审计（拇指热区、Fitts 定律） | 用于移动端问题清单复核 |
| Autodesk/claude-browser-test-skills | E2E 浏览器测试流水线（Playwright MCP） | 可信度高，适合引入回归 |
| bacoco/ShipGuard | 路由发现 + YAML 测试清单 + 执行 | 需要额外运行依赖，验证后采用 |
| LEO0331/lighthouse-skill-pack | Lighthouse 性能/可访问性/SEO 审计 | 用于移动端性能与可访问性打分 |
| andreykuzin/qa-persona | 人格化 E2E 走查，抓“用起来难受”的问题 | 与移动端痛点排查契合 |

### 暂不建议直接采用

- game-ui-mobile-friendly-design-agent-skill：面向游戏 UI，与投研工作台场景不符。
- kafka000/mobile-design-director：面向 React Native/SwiftUI/Flutter，本项目为原生 JS 单页应用。
- 通用蓝图/视觉生成类技能：在完成移动端高频路径适配前，先不引入风格重造。

## 后续路线图


### 阶段 2：账户与持久化（✅ 已基本完成，v3.3.0）

- ✅ PostgreSQL 数据库（生产）/ SQLite 自动降级（本地）
- ✅ SQLAlchemy 模型：用户、决策日志、纪律档案、设置、持仓、预警、自选股
- ✅ 注册、登录（JWT + PBKDF2 密码哈希）、账号级数据隔离
- ⏳ 邮箱验证和密码重置
- ⏳ 服务端安全会话与 HttpOnly Cookie（当前为 Bearer Token）
- ⏳ 管理员权限与审计日志

### 阶段 3.5：移动端适配（核心路径第一轮已完成）

- 触控目标、文字密度与安全区统一
- 滑块/数值输入改可点击步进或分段控件
- K 线触屏缩放、长按提示与暂停/恢复
- 表格改卡片/抽屉，指标改两列自适应
- 弹窗与底部导航的视口与安全区处理
- ✅ 用本地浏览器在 375/390/414px 宽度验收核心路径无横向溢出
- ✅ 新手引导改为不阻断核心任务
- ✅ 接入正式 E2E、Lighthouse 和截图基线

### 阶段 3：生产质量


- ✅ 接口限流（slowapi：全局 200 次/分钟、登录 5 次/分钟）
- ✅ GitHub Actions 测试（pytest + flake8 + 前端 JS 语法检查）
- ⏳ Redis 缓存（当前为进程内 30 秒 TTL）
- ⏳ 数据源超时、重试、熔断和降级监控
- ⏳ 结构化日志、错误追踪和性能监控
- ⏳ 依赖扫描和密钥扫描
- ⏳ staging / production 分离
- ⏳ 自动备份、恢复演练与发布回滚

### 阶段 4：可信研究平台

- 获得商业许可的行情、财务、公告和新闻数据源
- 模型版本、参数、输入和输出审计
- 资讯来源管理与重复内容归并
- 政策原文引用、行业映射与事件时间线
- 样本外回测、偏差报告和研判解释
- 研究报告导出与风险预警中心

### 阶段 4.5：研究卡联动与主题情报（当前优先）

- 证据抽屉：来源、时间、传导路径、行业影响和下一步验证动作
- 情报/股票/ETF/宏观页面一键加入研究卡
- 证据标记为事实、假设、反证或待验证
- 资讯专题主线、热度与研究关联度排序
- 研究卡状态从草稿到研究中、待验证、待决策、观察中、已复盘、已失效
- 研究卡验证日期到期提示和假设变化提醒
- 数据源注册表与数据覆盖矩阵扩展到所有研究对象

### 阶段 4.6：AI增强层

- 无 AI 模式保证核心功能完整
- 平台 AI 做摘要、拆分、追问、反证提示和复盘归纳
- BYOK 接入 OpenAI 兼容 API、DeepSeek、Claude、Gemini、Ollama 等
- AI 输出必须标注模型辅助并回链原始证据
- AI 不荐股、不自动调仓、不覆盖硬性风控

### 阶段 5：正式商业发布

- 用户协议、隐私政策、风险揭示和数据许可审查
- 订阅、支付、退款、发票和权益系统
- 客服、反馈、数据纠错和运营后台
- 正式 SLA、灾难恢复和容量规划

## 风险声明

ROX 投资助手提供的是公开信息整理、研究框架和决策记录能力：

- 不保证数据实时、完整或无误。
- 不构成证券投资咨询、交易指令或收益承诺。
- 历史数据、模型评分和宏观判断不代表未来表现。
- 用户应独立核验信息，并根据自身风险承受能力作出决策。
- 在任何地区公开运营或收费前，应完成当地证券、数据、隐私和内容版权合规审核。

---

如果你认同“事实可追溯、判断可解释、决策可复盘”的研究方式，欢迎通过 GitHub Issues 提交问题、数据纠错和改进建议。
