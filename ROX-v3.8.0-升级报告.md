# ROX v3.8.0 升级完成报告

## 本轮新增功能（v3.7.0 → v3.8.0）

### 1. 自选股 Watchlist 功能
- 新增 `Watchlist` 数据模型（用户级、code 唯一约束、排序字段）
- 新增 `app/api/watchlist.py`：增删、去重、批量排序接口
- 路由 `/api/watchlist/` 已注册

### 2. 补全 CRUD — PUT 更新接口
- `PUT /api/portfolio/{id}` — 修改持仓（股数/成本价/日期/备注）
- `PUT /api/alerts/{id}` — 激活/暂停切换（重新激活自动重置触发状态）、改目标价/方向
- 日志 `PUT /api/journal/{id}` 此前已存在

### 3. 行情数据内存缓存层
- `app/services/tencent_data.py` 的 `fetch_quotes` 增加 30s TTL 内存缓存
- 显著减少重复外部 API 调用，提升并发响应速度
- 提供 `clear_quote_cache()` 供测试使用

### 4. 用户统计聚合接口
- `GET /api/dashboard/stats` — 聚合决策胜率/持仓盈亏/预警/自选股数量
- 供仪表盘综合数据卡片使用

### 5. CI/CD 流水线
- `.github/workflows/ci.yml` — pytest 测试 + flake8 代码质量检查
- ⚠️ 因 GitHub OAuth token 缺少 `workflow` scope，**暂未推送**（见下方"待办"）

### 6. 测试与质量
- 新增 11 个测试用例（Watchlist/PUT/统计/缓存），总计 **36 个测试全部通过**
- 版本号升至 **v3.8.0**

## 部署状态
- ✅ 核心代码已推送至 `main` (c8bc0c0 → b4efd8a)，触发 Render 自动构建
- ✅ Render 健康检查路径 `/health` 已配置
- ⏳ 线上版本验证需等 Render 冷启动完成

## 待办事项（需用户操作）

### A. 启用 CI/CD（二选一）
**方式 1（推荐）：通过 GitHub Web 界面创建**
1. 打开 https://github.com/a1050154895/rox-investment-assistant/new/main
2. 文件名填写 `.github/workflows/ci.yml`
3. 将下方内容粘贴进去并提交

**方式 2：重新授权 OAuth App 获取 workflow scope**
1. GitHub → Settings → Applications → 找到 WorkBuddy/连接器授权
2. 重新授权并勾选 `workflow` 权限
3. 之后运行 `git add .github && git commit && git push`

#### ci.yml 内容
```yaml
name: CI
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest
      - env:
          ENVIRONMENT: test
          SECRET_KEY: ci-test-secret-key-not-for-production
        run: python -m pytest tests/ -v --tb=short
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install flake8
      - run: |
          flake8 app/ --count --select=E9,F63,F7,F82 --show-source --statistics
          flake8 app/ --count --exit-zero --max-complexity=15 --max-line-length=120 --statistics
```

### B. PostgreSQL 持久化部署（如尚未完成）
Render 控制台 → New → Blueprint → 选仓库 → 已自动读取 `render.yaml` → Apply。
该配置会自动创建免费 PostgreSQL 实例并注入 `DATABASE_URL`，
解决免费实例重启后 SQLite 被清空、注册账号丢失的问题。

### C. 前端适配（建议下一轮）
当前后端已支持 Watchlist / 统计接口，但前端 `static/js/` 尚未添加对应视图。
建议下一轮补充：
- `static/js/views/watchlist.js` — 自选股增删列表 + 实时行情卡片
- 仪表盘统计卡片调用 `/api/dashboard/stats`
- 个股页"加入自选"按钮
