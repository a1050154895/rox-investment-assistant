> **⚠️ 历史文档（2025）**：本报告记录的是 v3.3.0 阶段的工作，仅供追溯。
> 当前主线已演进至 **v4.25.0**（研究闭环/数据契约/情报主题/AI三层模式/回测v2/移动端左右布局等），
> 最新状态以 [README.md](README.md) 与 [docs/ROX3-merge-analysis.md](docs/ROX3-merge-analysis.md) 为准。

# ROX 投资助手 — 生产化地基升级概览（v3.3.0）

## 本次升级内容（P0 阶段）

### 1. 数据库持久化（决策日志 / 设置 / 纪律档案）
- 新增 `app/db.py`：SQLAlchemy 2.0，`DATABASE_URL` 环境变量优先（生产 PostgreSQL），未配置时自动降级本地 SQLite（`data/rox.db`，已在 .gitignore）。
- 新增 `app/models.py`：`User` / `JournalEntry` / `DisciplineProfile` / `Setting` 四张表，启动时自动建表。
- 决策日志从内存列表迁移到数据库，实例重启不丢失。

### 2. 多用户认证（JWT + 账号级隔离）
- 新增 `app/core/auth.py`：PBKDF2 加盐密码哈希（标准库，200k 迭代）+ PyJWT 签发/校验，`SECRET_KEY` 环境变量（生产必配）。
- 新增 `app/api/auth.py`：`POST /api/auth/register`、`POST /api/auth/login`、`GET /api/auth/me`。
- 决策日志、设置、纪律档案、AI 全部按用户隔离；未携带有效 token 一律 401。
- 前端新增登录/注册门禁（`#auth-gate`），token 存 localStorage，请求自动携带 `Authorization: Bearer`；顶栏用户标识 + 设置面板「账户」标签支持登出。

### 3. AI 助手真实后端
- 新增 `app/services/ai_service.py` + `app/api/ai.py`：OpenAI 兼容 `chat/completions` 调用。
- 配置优先级：环境变量（`AI_API_KEY`/`AI_API_BASE`/`AI_MODEL`）> 用户设置（数据库）。
- `GET /api/ai/status` 返回配置状态（不回传密钥）；`POST /api/ai/chat` 未配置返回 503 `AI_NOT_CONFIGURED`，调用失败返回 502 友好提示。
- 334 工作台「研究助手」从纯前端模板回答改为真实调用后端 AI，并把确定性评估结果作为上下文；AI 只解释纪律与风险、不覆盖硬规则。
- `settings_api.py` 重写：设置按用户落库，AI Key 允许保存但任何 GET 不回传明文（仅返回是否已配置）。

### 4. 去假数据
- 会员信息不再返回硬编码假数据：基于用户真实 plan 计算，`days_left`/`api_used` 改为 `null`，明示付费套餐接入中。

## 新增接口
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/register` | 注册（返回 JWT） |
| POST | `/api/auth/login` | 登录（返回 JWT） |
| GET | `/api/auth/me` | 当前用户 |
| GET | `/api/ai/status` | AI 配置状态 |
| POST | `/api/ai/chat` | AI 对话 |
| GET/PUT | `/api/discipline/profile` | 334 纪律档案服务端持久化 |

## 验证结果
- Python compileall 全应用通过；6 个 JS 文件 node --check 通过；密钥扫描无泄漏；git diff --check 通过。
- 冒烟测试通过：注册/重复注册409/登录/错误密码401/me/未登录401/日志CRUD/用户隔离/settings含Key保存且不回传/纪律档案存取/AI未配置503/会员无假数据。

## 生产部署注意
1. Render 控制台新增环境变量：`SECRET_KEY`（随机长字符串）、`DATABASE_URL`（Render PostgreSQL 的 Internal URL）、可选 `AI_API_KEY`。
2. 不配置 `DATABASE_URL` 时使用 SQLite，Render 免费实例重启文件会丢失——正式数据务必用 PostgreSQL。
3. 部署后 `Manual Deploy latest commit`，验收 `/health` = 3.3.0、`/ready` 数据库 = ok。

## 后续（P1）
实时行情升级（westock-data/neodata）、选股模块（westock-tool）、资讯研判（news-search）、宏观矩阵增强、回测/框架验证（策略回测专家方法论）。
