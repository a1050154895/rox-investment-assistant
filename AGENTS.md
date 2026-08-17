# ROX 投资助手 — Agent 工作流与项目约定

本项目对 Agent 采用 SCALE 引擎的满血闭环工作流：

```text
define -> plan -> build -> verify -> review -> ship
```

## 1. 编码前先思考（define）

- 明确陈述假设；存在多种解释时先提出，不要默默选择。
- 改动越简单越好，不添加超出需求的功能，不做一次性抽象。
- 只修改必要部分；发现无关死代码只标注，不删除。

## 2. 生成计划（plan）

每个非平凡改动先写出：

1. 要改哪些文件、为什么。
2. 风险点与回滚方式。
3. 验证命令（见下）。

## 3. 改代码（build）

- 数据原则：**不生成模拟行情、不生成随机评分、不伪造技术指标、不伪造资金流、不把方法论当实时结论。**
- 方法论数据一律以 `app/services/methodology.py` 为单一事实源，不要在 API 层再硬编码一份。
- 缺失数据诚实降级（`snapshot` / `unavailable` / `stale`），绝不编造。

## 4. 真实验证（verify）

```bash
.venv/bin/python -m pytest tests/ -q
.venv/bin/python -m compileall -q app
.venv/bin/python -m flake8 app/ --count --select=E9,F63,F7,F82
find static/js -name '*.js' -print0 | xargs -0 -n1 node --check
git diff --check
```

## 5. 复核与交付（review -> ship）

- 汇报时列出实际命令、结果、未验证项及原因。
- 涉及第三方能力或外部 token（gbrain / Graphify / 飞书 / 行情授权）时，先 dry-run 或先说明，不静默降级。
- 提交前 `git diff --check`，推送至 `origin main`。

## 关键文件索引

- 方法论单一事实源：`app/services/methodology.py`
- 架构与模块图：`docs/ARCHITECTURE.md`
- 方法论蒸馏知识库：`docs/methodology.md`
- 思想来源登记：`docs/strategy_origins.md`
- 设计语境：`.impeccable.md`
