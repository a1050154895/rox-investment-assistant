# ROX 投资助手

> 面向中国股票市场研究场景的投资认知与决策辅助系统。

ROX 将宏观变量、公开政策、全球风险、产业链传导、市场行情与投资纪律组织为一套可追溯的研究工作流，帮助用户区分**事实线索、分析假设与交易结论**。

**线上演示：** [https://rox-investment-assistant.onrender.com](https://rox-investment-assistant.onrender.com)

> [!IMPORTANT]
> 本项目目前处于生产化改造阶段，定位为信息整理与研究辅助工具，不构成投资建议、收益承诺或自动荐股服务。市场数据可能是延时快照；数据不可用时系统会明确标示，不会生成模拟行情或随机研判结果。

## 目录

- [产品定位](#产品定位)
- [核心能力](#核心能力)
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

- 桌面、平板和手机布局
- “战略文房”暖墨与朱砂视觉系统
- 移动端底部五项导航
- 加载、空数据和接口失败状态
- 浏览器缩放与基础键盘可访问性

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

接口会尽可能附带 `data_source`、`as_of` 和 `stale` 等字段，帮助前端向用户解释数据来源和时效。

## 技术架构

| 层级 | 技术 | 说明 |
| --- | --- | --- |
| Web 服务 | FastAPI + Uvicorn | REST API、健康检查和 SPA 路由 |
| 模板 | Jinja2 | 输出单页应用外壳 |
| 前端 | 原生 JavaScript SPA | 无 Node 构建步骤，客户端路由与视图渲染 |
| 可视化 | Apache ECharts 5 | K 线和资金趋势图 |
| 市场数据 | AKShare + 可信快照降级 | 外部数据获取；失败时明确降级 |
| 样式 | 原生 CSS + Design Tokens | 响应式“战略文房”设计系统 |
| 测试 | Python `unittest` | 可信数据和确定性分析测试 |
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
│   ├── api/                    # REST 路由
│   │   ├── dashboard.py
│   │   ├── stock.py
│   │   ├── intelligence.py
│   │   ├── journal.py
│   │   ├── framework.py
│   │   └── settings_api.py
│   ├── core/
│   │   ├── config.py           # 环境配置与 CORS 白名单
│   │   └── security.py         # 请求 ID、错误处理与安全响应头
│   ├── services/
│   │   ├── market_data.py      # 市场行情、K 线与资金数据
│   │   ├── analysis_engine.py  # 确定性分析与技术指标
│   │   └── intelligence_data.py
│   └── main.py                 # FastAPI 应用入口
├── static/
│   ├── css/                    # Design Tokens 与响应式样式
│   └── js/                     # SPA 内核和各页面视图
├── templates/shell.html        # SPA 页面外壳
├── tests/test_trust_layer.py   # 可信数据测试
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

### 仪表盘

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/api/dashboard/overview` | 仪表盘聚合数据 |
| GET | `/api/dashboard/market_heatmap` | 板块热力图；无可靠数据时返回不可用状态 |

### 股票

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/api/stock/search?q=茅台` | 按代码或名称搜索股票 |
| GET | `/api/stock/{code}` | 行情和基础信息 |
| GET | `/api/stock/{code}/kline?period=daily&limit=120` | 真实 K 线及数据状态 |
| GET | `/api/stock/{code}/analysis` | 确定性框架分析 |
| GET | `/api/stock/{code}/indicators` | 基于真实 K 线计算技术指标 |

### 宏观情报

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/api/intelligence/brief` | 资讯、政策、全球风险和行业资金简报 |
| GET | `/api/intelligence/brief?refresh=true` | 绕过短时缓存手动刷新 |
| GET | `/api/intelligence/stock/{code}` | 个股关联的传导路径与验证清单 |

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

### 框架与设置

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/api/framework/methodology` | 五层方法论 |
| GET | `/api/framework/strategies` | 策略库 |
| GET | `/api/framework/knowledge` | 知识库 |
| GET/PUT | `/api/settings/` | 当前运行期设置 |
| GET | `/api/settings/membership` | 会员信息（基于用户真实 plan，无假数据） |

## 测试与质量检查

### 运行可信数据测试

```bash
PYTHONPATH=. python -m unittest discover -s tests -v
```

现有测试覆盖：

- 股票代码标准化
- 同输入下分析结果确定性
- K 线样本不足时拒绝生成技术指标
- 未知股票不生成模拟行情或资金流

### Python 编译检查

```bash
python -m compileall -q app
```

### JavaScript 语法检查

需要 Node.js 18+：

```bash
node --check static/js/app.js
node --check static/js/views/dashboard.js
node --check static/js/views/stock.js
node --check static/js/views/intelligence.js
node --check static/js/views/journal.js
node --check static/js/views/framework.js
```

### Git 差异检查

```bash
git diff --check
```

发布前建议至少执行以上四类检查，并验证 `/health`、`/ready`、仪表盘、个股页和手机底部导航。

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

当前 API 已具备多用户 JWT 鉴权与账号级数据隔离；请求限流、找回密码与 RBAC 仍在路线图中，正式收费服务前需补齐并完成合规审核。

### 密钥安全

- 不要把 GitHub Token、数据供应商密钥或密码写入代码、README、Git 远程 URL。
- 使用 Render Environment Variables 或本地 `.env` 管理秘密。
- 如果密钥曾出现在聊天、日志或提交历史中，应立即撤销并轮换。
- 提交前建议运行密钥扫描工具，例如 Gitleaks。

## 当前限制

| 领域 | 当前状态 |
| --- | --- |
| 数据授权 | AKShare 用于研发验证；商业展示和再分发前需确认供应商许可 |
| 行情时效 | 部分股票使用内置快照，不保证实时 |
| 新闻版权 | 仅应使用允许抓取、摘要和展示的公开来源 |
| 数据库 | 已接入（生产 PostgreSQL / 本地 SQLite 自动降级），日志、设置、纪律档案按用户持久化 |
| 用户体系 | 已支持注册、登录（JWT + PBKDF2 哈希）与账号级数据隔离；找回密码、RBAC 待实现 |
| AI 服务 | 已接入真实后端（OpenAI 兼容），需配置 API Key；AI 仅做解释/复盘，不覆盖硬性风控规则 |
| 缓存 | 仅有进程内短时缓存，实例重启后失效 |
| 任务系统 | 暂无独立采集 Worker、消息队列和定时任务 |
| 可观测性 | 有请求 ID，但尚无集中日志、错误追踪和告警 |
| 测试 | 已有可信数据单元测试，尚缺完整集成与 E2E 测试 |
| 主题 | 当前以深色“战略文房”为主，完整 light/dark/system 切换待实现 |
| 商业合规 | 用户协议、隐私政策、风险揭示和法律审核尚未完成 |

## 后续路线图

### 阶段 2：账户与持久化（✅ 已基本完成，v3.3.0）

- ✅ PostgreSQL 数据库（生产）/ SQLite 自动降级（本地）
- ✅ SQLAlchemy 模型：用户、决策日志、纪律档案、设置
- ✅ 注册、登录（JWT + PBKDF2 密码哈希）、账号级数据隔离
- ⏳ 邮箱验证和密码重置
- ⏳ 服务端安全会话与 HttpOnly Cookie（当前为 Bearer Token）
- ⏳ 管理员权限与审计日志

### 阶段 3：生产质量

- Redis 缓存和接口限流
- 数据源超时、重试、熔断和降级监控
- 结构化日志、错误追踪和性能监控
- GitHub Actions 测试、依赖扫描和密钥扫描
- staging / production 分离
- 自动备份、恢复演练与发布回滚

### 阶段 4：可信研究平台

- 获得商业许可的行情、财务、公告和新闻数据源
- 模型版本、参数、输入和输出审计
- 资讯来源管理与重复内容归并
- 政策原文引用、行业映射与事件时间线
- 样本外回测、偏差报告和研判解释
- 研究报告导出与风险预警中心

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
