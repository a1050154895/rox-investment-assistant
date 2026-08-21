/* ============================================
   视图1 · 仪表盘
   ============================================ */

ROX.register('/', async function(container) {
  const data = await ROX.api.get('/api/dashboard/overview');
  if (!data) {
    container.innerHTML = '<div class="empty-state"><p>数据加载失败，请检查网络连接</p></div>';
    return;
  }

  container.innerHTML = `
    <div class="dashboard-page" style="display:flex;flex-direction:column;gap:16px;">
      <!-- 研究传导链 -->
      <div class="card full-width dashboard-chain-card" style="padding:16px 20px;">
        <div class="card-header" style="margin-bottom:8px;">
          <div class="card-title">研究传导链</div>
        </div>
        <div style="font-size:13px;color:var(--text-primary);line-height:1.7;">${ROX.escape(data.research_chain?.summary || '宏观数据不足')}</div>
        <div style="font-size:11px;color:var(--text-tertiary);margin-top:6px;">宏观定调 → 资本周期 → 矛盾分析 → 决策纪律，逐层传导、可追溯。</div>
      </div>
      <!-- 今日研究队列：ROX Loop 的主入口 -->
      <div class="card full-width research-today-card dashboard-priority-card">
        <div class="card-header">
          <div>
            <div class="eyebrow">ROX LOOP / TODAY</div>
            <div class="card-title">今日先把哪一个判断想清楚？</div>
            <div class="card-subtitle">研究卡把事实、假设、反证和风控连成一条可复盘的证据链。</div>
          </div>
          <button class="btn btn-primary btn-sm" data-route="/research">+ 新建研究卡</button>
        </div>
        <div id="research-today-body"><div class="research-queue-loading">正在加载你的研究队列…</div></div>
      </div>
      <!-- 宏观指南针 -->
      <div class="card full-width dashboard-macro-card">
        <div class="card-header">
          <div>
            <div class="card-title">宏观指南针</div>
            <div class="card-subtitle">${data.macro_compass.methodology || '财政信用条件 × 价值实现条件代理矩阵'}</div>
          </div>
          <span class="tag tag-amber">${data.macro_compass.sovereign_credit.status}</span>
        </div>
        <div class="grid-2">
          <div>
            <div style="display:flex;justify-content:space-between;margin-bottom:8px;">
              <span style="font-size:12px;color:var(--text-secondary);">主权信用状态</span>
              <span style="font-size:12px;font-family:var(--font-mono);">${data.macro_compass.sovereign_credit.score}</span>
            </div>
            <div class="progress"><div class="progress-fill amber" style="width:${data.macro_compass.sovereign_credit.score}%"></div></div>
            <div style="font-size:11px;color:var(--text-tertiary);margin-top:6px;">${data.macro_compass.sovereign_credit.detail}</div>
          </div>
          <div>
            <div style="display:flex;justify-content:space-between;margin-bottom:8px;">
              <span style="font-size:12px;color:var(--text-secondary);">价值实现度</span>
              <span style="font-size:12px;font-family:var(--font-mono);">${data.macro_compass.value_realization.score}</span>
            </div>
            <div class="progress"><div class="progress-fill blue" style="width:${data.macro_compass.value_realization.score}%"></div></div>
            <div style="font-size:11px;color:var(--text-tertiary);margin-top:6px;">${data.macro_compass.value_realization.detail}</div>
          </div>
        </div>
        <div class="macro-evidence-grid">
          ${[...(data.macro_compass.sovereign_credit.indicators || []), ...(data.macro_compass.value_realization.indicators || [])].map(item => `
            <div class="macro-evidence ${item.status === 'available' || item.status === 'snapshot' ? 'available' : 'unavailable'}">
              <div><strong>${item.label}</strong><span>${item.publisher || ''}</span></div>
              <div class="macro-value">${item.status === 'available' || item.status === 'snapshot' ? `${item.value}${item.unit} · ${item.period}` : '暂不可用'}</div>
            </div>`).join('')}
        </div>
        <div style="margin-top:12px;padding:12px 14px;background:var(--ink-vermilion-glow);border-left:2px solid var(--ink-vermilion);font-size:12px;color:var(--ink-vermilion-soft);">
          ${data.macro_compass.framework_advice}
        </div>
        <div class="macro-meta">覆盖 ${data.macro_compass.coverage?.available ?? 0}/${data.macro_compass.coverage?.total ?? 0} 项 · ${data.macro_compass.disclaimer || ''}</div>
        <div class="macro-quality-line">数据质量：${ROX.escape(data.macro_compass.data_quality?.status || '未标注')} · 最新观察期：${ROX.escape(data.macro_compass.data_quality?.latest_observation || '未知')} · ${ROX.escape(data.macro_compass.data_quality?.message || '')}</div>
      </div>

      <!-- 资本周期 + 矛盾追踪 -->
      <div class="grid-2 dashboard-secondary-grid">
        <!-- 资本周期 -->
        <div class="card">
          <div class="card-header">
            <div class="card-title">资本周期阶段</div>
            <span class="tag tag-blue">${data.capital_cycle.stage_name}</span>
          </div>
          <div class="cycle-stages" style="margin-bottom:12px;">
            ${data.capital_cycle.stages.map((stage, i) => `
              <div class="cycle-stage ${data.capital_cycle.current_stage != null && i < data.capital_cycle.current_stage ? 'passed' : data.capital_cycle.current_stage != null && i === data.capital_cycle.current_stage ? 'active' : ''}">${stage}</div>
            `).join('')}
          </div>
          <div class="progress" style="margin-bottom:8px;"><div class="progress-fill blue" style="width:${data.capital_cycle.progress}%"></div></div>
          <div style="font-size:11px;color:var(--text-tertiary);">${data.capital_cycle.stage_detail}</div>
          ${data.capital_cycle.evidence ? `<div style="font-size:11px;color:var(--text-secondary);margin-top:6px;">${ROX.escape(data.capital_cycle.evidence)}${data.capital_cycle.confidence ? ` · 置信度 ${data.capital_cycle.confidence}` : ''}</div>` : ''}
        </div>

        <!-- 矛盾追踪 -->
        <div class="card">
          <div class="card-header">
            <div class="card-title">主矛盾追踪</div>
          </div>
          <div style="display:flex;flex-direction:column;gap:14px;">
            ${[['primary', '主要矛盾', 'red'], ['secondary', '次要矛盾', 'amber'], ['tertiary', '第三矛盾', 'green']].map(([key, label, color]) => {
              const c = data.contradictions[key];
              return `
                <div>
                  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
                    <span style="font-size:12px;color:var(--text-primary);font-weight:600;">${label} · ${ROX.escape(c.name)}</span>
                    <span style="font-size:11px;color:var(--text-tertiary);font-family:var(--font-mono);">强度 ${c.intensity}</span>
                  </div>
                  <div style="font-size:11px;color:var(--text-secondary);margin-bottom:2px;">${ROX.escape(c.type)} · ${ROX.escape(c.trend)}</div>
                  <div style="font-size:11px;color:var(--text-tertiary);margin-bottom:6px;">${ROX.escape(c.desc)}</div>
                  <div class="progress"><div class="progress-fill ${color}" style="width:${c.intensity}%"></div></div>
                  ${c.evidence ? `<div style="font-size:10px;color:var(--text-muted);margin-top:3px;">${ROX.escape(c.evidence)}</div>` : ''}
                </div>
              `;
            }).join('')}
          </div>
        </div>
      </div>

      <!-- 334 纪律体检 + 自选股 -->
      <div class="grid-2 dashboard-secondary-grid dashboard-risk-grid">
        <!-- 334 纪律体检（异步加载真实持仓 + 周期阶段） -->
        <div class="card" id="discipline-card">
          <div class="card-header">
            <div><div class="card-title">334 纪律体检</div><div class="card-subtitle">真实持仓 + 周期阶段 + 风险边界</div></div>
            <button class="btn btn-secondary btn-sm" data-action="open-discipline">录入我的数据</button>
          </div>
          <div id="discipline-assessment-body" style="font-size:12px;color:var(--text-tertiary);">登录后可查看你的纪律体检。</div>
        </div>

        <!-- 自选股 -->
        <div class="card">
          <div class="card-header">
            <div class="card-title">自选股概览</div>
            <button class="btn btn-ghost btn-sm" data-route="/watchlist">查看全部</button>
          </div>
          <div id="watchlist-overview-body">
            <div class="loading"><div class="spinner"></div></div>
          </div>
        </div>
      </div>

      <!-- 宏观资讯研判摘要 -->
      ${data.intelligence ? `
      <div class="grid-2 dashboard-secondary-grid dashboard-intelligence-grid">
        <div class="card">
          <div class="card-header">
            <div><div class="card-title">政策与全球变量</div><div class="card-subtitle">先看传导路径，再看交易信号</div></div>
            <button class="btn btn-ghost btn-sm" data-route="/intelligence">查看情报台</button>
          </div>
          <div style="display:flex;flex-direction:column;gap:8px;">
            ${data.intelligence.global_risk.slice(0, 3).map(item => `
              <div style="display:flex;justify-content:space-between;gap:12px;padding:8px 0;border-bottom:1px solid var(--ink-border-faint);">
                <div><div class="stock-name">${item.factor}</div><div class="stock-code">${item.transmission}</div></div>
                <span class="tag ${item.direction === 'warning' ? 'tag-amber' : item.direction === 'positive' ? 'tag-red' : 'tag-gray'}">${item.status}</span>
              </div>`).join('')}
          </div>
        </div>
        <div class="card">
          <div class="card-header"><div><div class="card-title">最新资讯线索</div><div class="card-subtitle">${data.intelligence.source_status}</div></div><span class="tag tag-gray">公开信息</span></div>
          <div style="display:flex;flex-direction:column;gap:10px;">
            ${data.intelligence.news.slice(0, 3).map(item => `
              <div style="border-left:2px solid var(--ink-indigo);padding-left:10px;">
                <div style="font-size:12px;color:var(--text-primary);line-height:1.6;">${item.title}</div>
                <div style="margin-top:3px;font-size:10px;color:var(--text-tertiary);">${item.category} · ${item.fact_or_view}</div>
              </div>`).join('')}
          </div>
        </div>
      </div>` : ''}

      <!-- 最近决策 -->
      <div class="card full-width dashboard-history-card">
        <div class="card-header">
          <div class="card-title">最近决策记录</div>
          <button class="btn btn-secondary btn-sm" data-action="add-decision">+ 记录决策</button>
        </div>
        <div style="display:flex;gap:12px;overflow-x:auto;padding-bottom:4px;">
          ${data.recent_decisions.length ? data.recent_decisions.map(d => `
            <div class="decision-card ${d.score < 60 ? 'low-score' : ''}" data-action="view-stock" data-code="${d.code}">
              <div class="decision-header"><div><div class="decision-stock">${d.stock}</div><div class="decision-meta">${d.code} · ${d.date}</div></div><span class="tag ${ROX.fmt.actionTag(d.action)}">${d.action}</span></div>
            </div>`).join('') : `<div class="empty-state" style="width:100%;padding:20px;"><p>暂无真实决策记录，请从“记录决策”开始建立自己的样本。</p></div>`}
        </div>
      </div>
    </div>
  `;

  // Async: 持仓概览卡片
  loadPortfolioCard();
  loadAlertsCard();
  loadWatchlistCard();
  loadStatsCard();
  loadDisciplineAssessment();
  loadResearchToday();

  // 自动刷新：指数 ticker + 自选股 + 持仓卡片每 30s 更新
  ROX.startAutoRefresh(async () => {
    ROX.loadIndexTicker();
    loadWatchlistCard();
    loadPortfolioCard();
  }, 30000);
});

async function loadResearchToday() {
  const body = document.getElementById('research-today-body');
  if (!body) return;
  const data = await ROX.api.get('/api/research/today');
  if (!data || data.error) {
    body.innerHTML = '<div class="research-queue-empty">登录后即可建立你的第一张研究卡。</div>';
    return;
  }
  const cards = data.cards || [];
  const reviews = data.pending_reviews || [];
  body.innerHTML = cards.length ? `<div class="research-queue-grid">${cards.slice(0, 4).map(card => `
    <div class="research-queue-item" data-route="/research/${card.id}">
      <div class="research-queue-item-head"><span class="research-status ${card.status === 'ready' ? 'ready' : ''}">${card.status === 'ready' ? '待决策' : '草稿'}</span><span class="research-queue-date">${ROX.fmt.date(card.updated_at)}</span></div>
      <div class="research-queue-title">${ROX.escape(card.title)}</div>
      <div class="research-queue-meta">${ROX.escape(card.stock || card.code || '未绑定标的')} · ${ROX.escape(card.action || '观察')}</div>
      <div class="research-queue-progress"><span style="width:${[card.question, card.hypothesis, (card.facts || []).length, card.counter_evidence, card.invalidation].filter(Boolean).length * 20}%"></span></div>
    </div>`).join('')}</div>` : `<div class="research-queue-empty"><div><strong>还没有研究卡</strong><p>从一个具体问题开始，不要从“看一下市场”开始。</p></div><button class="btn btn-secondary btn-sm" data-route="/research">创建第一张</button></div>`;
  if (reviews.length) {
    body.innerHTML += `<div class="research-pending-line"><span>待复盘 ${reviews.length} 条决策</span><button class="btn btn-secondary btn-sm" data-route="/review">去复盘 →</button></div>`;
  }
  body.querySelectorAll('[data-route]').forEach(item => item.addEventListener('click', () => ROX.navigate(item.dataset.route)));
  document.querySelectorAll('[data-route="/research"]').forEach(item => item.addEventListener('click', () => ROX.navigate('/research')));
}

async function loadDisciplineAssessment() {
  const body = document.getElementById('discipline-assessment-body');
  if (!body) return;
  const data = await ROX.api.get('/api/discipline/assessment');
  if (!data || data.error) {
    body.innerHTML = '<div style="font-size:12px;color:var(--text-tertiary);">登录后可查看你的纪律体检。</div>';
    return;
  }
  const a = data.assessment || {};
  const c = data.cycle || {};
  const p = data.portfolio || {};
  const violations = (a.checks || []).filter(x => !x.passed);
  body.innerHTML = `
    <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:8px;">
      <span style="color:var(--text-secondary);">真实持仓</span>
      <span style="font-family:var(--font-mono);color:var(--text-primary);">${p.count || 0} 只 · 市值 ${ROX.fmt.num(p.total_market)}</span>
    </div>
    <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:8px;">
      <span style="color:var(--text-secondary);">周期阶段</span>
      <span style="color:var(--rox-primary);">${ROX.escape(c.stage || '未评估')} · ${ROX.escape(c.posture || '')}</span>
    </div>
    <div style="font-size:11px;color:var(--text-secondary);line-height:1.6;margin-bottom:10px;">${ROX.escape(c.note || '')}</div>
    <div style="font-size:11px;color:var(--text-secondary);margin-bottom:10px;">
      ${ROX.escape(a.status_label || '未评估')}${violations.length ? ` · <span style="color:var(--rox-danger);">${violations.length} 项冲突</span>` : ''}
    </div>
    <div style="padding:10px 12px;background:rgba(255,159,10,0.08);border-left:2px solid var(--ink-warn);font-size:11px;color:var(--ink-warn);line-height:1.6;">${ROX.escape(data.guidance || '')}</div>
  `;
}

async function loadPortfolioCard() {
  // 找到宏观指南针卡片后的插入位置
  const compass = document.querySelector('.macro-meta')?.closest('.card');
  if (!compass) return;

  const data = await ROX.api.get('/api/portfolio/');
  if (!data) return;

  const s = data.summary || {};
  const posCount = s.count || 0;
  const pnlColor = (s.total_pnl || 0) >= 0 ? 'var(--color-up)' : 'var(--color-down)';
  const fmt = ROX.fmt;

  const card = document.createElement('div');
  card.className = 'card full-width';
  card.style.marginTop = '16px';
  card.innerHTML = posCount === 0 ? `
    <div class="card-header">
      <div class="card-title">持仓概览</div>
    </div>
    <div style="text-align:center;padding:20px 0;color:var(--text-tertiary);">
      <p style="margin:0 0 8px;">暂无持仓</p>
      <button class="btn btn-secondary btn-sm" data-route="/portfolio">管理持仓</button>
    </div>
  ` : `
    <div class="card-header">
      <div class="card-title">持仓概览</div>
      <button class="btn btn-secondary btn-sm" data-route="/portfolio">全部</button>
    </div>
    <div style="display:flex;gap:16px;align-items:flex-start;flex-wrap:wrap;">
      <div style="flex:1;min-width:200px;">
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(80px,1fr));gap:12px;margin-bottom:12px;">
          <div style="text-align:center;"><div style="font-size:11px;color:var(--text-tertiary);">持仓数</div><div style="font-size:18px;font-weight:590;">${posCount}</div></div>
          <div style="text-align:center;"><div style="font-size:11px;color:var(--text-tertiary);">总成本</div><div style="font-size:18px;font-weight:590;">${fmt.num(s.total_cost)}</div></div>
          <div style="text-align:center;"><div style="font-size:11px;color:var(--text-tertiary);">总市值</div><div style="font-size:18px;font-weight:590;">${fmt.num(s.total_market)}</div></div>
          <div style="text-align:center;"><div style="font-size:11px;color:var(--text-tertiary);">总盈亏</div><div style="font-size:18px;font-weight:590;color:${pnlColor};">${fmt.num(s.total_pnl)}</div></div>
          <div style="text-align:center;"><div style="font-size:11px;color:var(--text-tertiary);">收益率</div><div style="font-size:18px;font-weight:590;color:${pnlColor};">${fmt.pct(s.total_pnl_pct)}</div></div>
        </div>
        ${(data.positions || []).slice(0, 3).map(p => {
          const c = p.pnl >= 0 ? 'var(--color-up)' : 'var(--color-down)';
          return `<div style="display:flex;justify-content:space-between;align-items:center;padding:8px 10px;background:var(--bg-secondary);border-radius:var(--radius-md);margin-bottom:6px;cursor:pointer;" data-action="view-stock" data-code="${ROX.escape(p.code)}">
            <span style="font-size:12px;font-weight:500;">${ROX.escape(p.name)} <span style="color:var(--text-tertiary);font-size:11px;">${ROX.escape(p.code)}</span></span>
            <span style="font-size:12px;font-family:var(--font-mono);color:${c};">${fmt.pct(p.pnl_pct)}</span>
          </div>`;
        }).join('')}
      </div>
      <div id="portfolio-pie-chart" style="width:200px;height:200px;flex-shrink:0;"></div>
    </div>
  `;

  // 插入到宏观指南针卡片之后
  compass.after(card);

  // 渲染持仓配置饼图
  if (posCount > 0 && typeof echarts !== 'undefined') {
    const chartEl = card.querySelector('#portfolio-pie-chart');
    if (chartEl) {
      const chart = echarts.init(chartEl);
      const positions = data.positions || [];
      const pieData = positions.map(p => ({
        name: p.name,
        value: Math.max(p.market || p.cost || 0, 0.01),
      }));
      chart.setOption({
        tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)', textStyle: { fontSize: 12 } },
        series: [{
          type: 'pie',
          radius: ['40%', '70%'],
          center: ['50%', '50%'],
          avoidLabelOverlap: true,
          itemStyle: { borderRadius: 6, borderColor: 'transparent', borderWidth: 2 },
          label: { show: false },
          emphasis: { label: { show: true, fontSize: 13, fontWeight: 'bold' } },
          data: pieData,
        }],
        color: ['#0a84ff', '#5e5ce6', '#bf5af2', '#ff9f0a', '#ffd60a', '#30d158', '#64d2ff', '#ff453a'],
      });
      // 响应式
      ROX._chartInstances = ROX._chartInstances || [];
      ROX._chartInstances.push(chart);
    }
  }

  // 路由按钮事件
  card.querySelectorAll('[data-route]').forEach(btn => {
    btn.addEventListener('click', () => ROX.navigate(btn.dataset.route));
  });
}

async function loadAlertsCard() {
  const data = await ROX.api.get('/api/alerts/');
  if (!data || !data.alerts || data.alerts.length === 0) return;

  const compass = document.querySelector('.card:has([data-route="/portfolio"])');
  if (!compass) return;

  const triggered = data.alerts.filter(a => a.triggered);
  const active = data.alerts.filter(a => a.active && !a.triggered);

  const card = document.createElement('div');
  card.className = 'card full-width';
  card.style.cssText = 'margin-top:16px;';

  let html = '<div class="card-header"><div class="card-title">价格预警</div></div>';

  if (triggered.length) {
    html += `<div style="margin-bottom:10px;">${triggered.map(a => `
      <div style="display:flex;justify-content:space-between;align-items:center;padding:8px 10px;background:rgba(255,69,58,0.1);border-radius:8px;margin-bottom:4px;border-left:3px solid var(--color-up);cursor:pointer;" data-action="view-stock" data-code="${ROX.escape(a.code)}">
        <span style="font-size:12px;font-weight:500;">${ROX.escape(a.price_name||a.name)} <span style="color:var(--color-up);">触发!</span></span>
        <span style="font-size:11px;font-family:var(--font-mono);">${a.direction==='above'?'↑≥':'↓≤'}${ROX.fmt.num(a.target_price)} 现价${ROX.fmt.num(a.current_price)}</span>
      </div>`).join('')}</div>`;
  }
  if (active.length) {
    html += `<div>${active.map(a => `
      <div style="display:flex;justify-content:space-between;padding:4px 8px;font-size:11px;color:var(--text-secondary);">
        <span>${ROX.escape(a.price_name||a.name)} ${a.direction==='above'?'↑≥':'↓≤'}${ROX.fmt.num(a.target_price)}</span>
        <span style="font-family:var(--font-mono);">现价 ${a.current_price != null ? ROX.fmt.num(a.current_price) : '--'}</span>
      </div>`).join('')}</div>`;
  }

  card.innerHTML = html;
  compass.after(card);
}

async function loadWatchlistCard() {
  const body = document.getElementById('watchlist-overview-body');
  if (!body) return;
  const data = await ROX.api.get('/api/watchlist/');
  if (!data) { body.innerHTML = '<div class="empty-state"><p>加载失败</p></div>'; return; }
  const list = data.watchlist || [];
  if (list.length === 0) {
    body.innerHTML = `<div style="text-align:center;padding:16px 0;color:var(--text-tertiary);font-size:12px;">
      <p style="margin:0 0 8px;">暂无自选股</p>
      <button class="btn btn-secondary btn-sm" data-route="/watchlist">去添加</button>
    </div>`;
    return;
  }
  body.innerHTML = `<div style="display:flex;flex-direction:column;gap:2px;">${list.slice(0, 6).map(s => {
    const cls = ROX.fmt.color(s.change_pct || 0);
    return `<div class="stock-row" data-action="view-stock" data-code="${ROX.escape(s.code)}">
      <div class="stock-info">
        <div class="stock-name">${ROX.escape(s.price_name || s.name)}</div>
        <div class="stock-code">${ROX.escape(s.code)}</div>
      </div>
      <div style="text-align:right;">
        <div class="stock-price ${cls}">${s.price != null ? ROX.fmt.num(s.price) : '--'}</div>
        <div class="stock-change ${cls}">${s.change_pct != null ? ROX.fmt.pct(s.change_pct) : '--'}</div>
      </div>
    </div>`;
  }).join('')}</div>`;
}

async function loadStatsCard() {
  const data = await ROX.api.get('/api/dashboard/stats');
  if (!data) return;
  const j = data.journal || {}, p = data.portfolio || {}, a = data.alerts || {}, w = data.watchlist || {};
  const card = document.createElement('div');
  card.className = 'card full-width';
  card.style.marginTop = '16px';
  card.innerHTML = `
    <div class="card-header"><div class="card-title">我的投资数据</div></div>
    <div class="grid-4" style="gap:16px;">
      <div class="stat-item"><span class="stat-label">决策记录</span><span class="stat-value">${j.total || 0}</span><span style="font-size:11px;color:var(--text-tertiary);">胜率 ${j.win_rate || 0}% · 均分 ${j.avg_consistency || 0}</span></div>
      <div class="stat-item"><span class="stat-label">持仓</span><span class="stat-value">${p.count || 0}</span><span style="font-size:11px;color:var(--text-tertiary);">盈亏 ${ROX.fmt.num(p.total_pnl || 0)}</span></div>
      <div class="stat-item"><span class="stat-label">价格预警</span><span class="stat-value">${a.total || 0}</span><span style="font-size:11px;color:var(--text-tertiary);">触发 ${a.triggered || 0} · 生效 ${a.active || 0}</span></div>
      <div class="stat-item"><span class="stat-label">自选股</span><span class="stat-value">${w.count || 0}</span><span style="font-size:11px;color:var(--text-tertiary);"><span data-route="/watchlist" style="color:var(--rox-accent);cursor:pointer;">管理 →</span></span></div>
    </div>`;
  const view = document.getElementById('view-container');
  if (view) view.appendChild(card);
}
