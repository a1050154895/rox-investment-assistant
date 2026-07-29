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
    <div style="display:flex;flex-direction:column;gap:16px;">
      <!-- 宏观指南针 -->
      <div class="card full-width">
        <div class="card-header">
          <div>
            <div class="card-title">宏观指南针</div>
            <div class="card-subtitle">主权信用 × 价值实现矩阵</div>
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
        <div style="margin-top:12px;padding:12px 14px;background:var(--ink-vermilion-glow);border-left:2px solid var(--ink-vermilion);font-size:12px;color:var(--ink-vermilion-soft);">
          ${data.macro_compass.framework_advice}
        </div>
      </div>

      <!-- 资本周期 + 矛盾追踪 -->
      <div class="grid-2">
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
        </div>

        <!-- 矛盾追踪 -->
        <div class="card">
          <div class="card-header">
            <div class="card-title">主矛盾追踪</div>
          </div>
          <div style="display:flex;flex-direction:column;gap:12px;">
            <div>
              <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
                <span style="font-size:12px;color:var(--text-primary);">主要矛盾</span>
                <span style="font-size:11px;color:var(--text-tertiary);">${data.contradictions.primary.trend === 'up' ? '↑ 强化' : data.contradictions.primary.trend === 'down' ? '↓ 缓解' : '→ 稳定'}</span>
              </div>
              <div style="font-size:11px;color:var(--text-secondary);margin-bottom:4px;">${data.contradictions.primary.name}</div>
              <div class="progress"><div class="progress-fill red" style="width:${data.contradictions.primary.intensity}%"></div></div>
            </div>
            <div>
              <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
                <span style="font-size:12px;color:var(--text-primary);">次要矛盾</span>
                <span style="font-size:11px;color:var(--text-tertiary);">${data.contradictions.secondary.trend === 'up' ? '↑ 强化' : data.contradictions.secondary.trend === 'down' ? '↓ 缓解' : '→ 稳定'}</span>
              </div>
              <div style="font-size:11px;color:var(--text-secondary);margin-bottom:4px;">${data.contradictions.secondary.name}</div>
              <div class="progress"><div class="progress-fill amber" style="width:${data.contradictions.secondary.intensity}%"></div></div>
            </div>
            <div>
              <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
                <span style="font-size:12px;color:var(--text-primary);">第三矛盾</span>
                <span style="font-size:11px;color:var(--text-tertiary);">${data.contradictions.tertiary.trend === 'up' ? '↑ 强化' : data.contradictions.tertiary.trend === 'down' ? '↓ 缓解' : '→ 稳定'}</span>
              </div>
              <div style="font-size:11px;color:var(--text-secondary);margin-bottom:4px;">${data.contradictions.tertiary.name}</div>
              <div class="progress"><div class="progress-fill green" style="width:${data.contradictions.tertiary.intensity}%"></div></div>
            </div>
          </div>
        </div>
      </div>

      <!-- 334 仓位纪律 + 自选股 -->
      <div class="grid-2">
        <!-- 334 -->
        <div class="card">
          <div class="card-header">
            <div class="card-title">334 仓位纪律</div>
            <span class="tag ${data.discipline_334.cash.actual > data.discipline_334.cash.target ? 'tag-amber' : 'tag-green'}">
              ${data.discipline_334.cash.actual > data.discipline_334.cash.target ? '现金偏高' : '符合基准'}
            </span>
          </div>
          <div class="discipline-bar" style="margin-bottom:12px;">
            <div class="discipline-segment discipline-core" style="width:${data.discipline_334.core.actual}%;">核心 ${data.discipline_334.core.actual}%</div>
            <div class="discipline-segment discipline-satellite" style="width:${data.discipline_334.satellite.actual}%;">卫星 ${data.discipline_334.satellite.actual}%</div>
            <div class="discipline-segment discipline-cash" style="width:${data.discipline_334.cash.actual}%;">现金 ${data.discipline_334.cash.actual}%</div>
          </div>
          <div style="font-size:11px;color:var(--text-tertiary);margin-bottom:8px;">
            基准：核心 30% / 卫星 30% / 现金 40%
          </div>
          <div style="display:flex;flex-direction:column;gap:4px;">
            <div style="font-size:11px;color:var(--text-secondary);">核心池：${data.discipline_334.core.stocks.join('、')}</div>
            <div style="font-size:11px;color:var(--text-secondary);">卫星池：${data.discipline_334.satellite.stocks.join('、')}</div>
          </div>
          <div style="margin-top:12px;padding:10px 12px;background:rgba(200,153,66,0.08);border-left:2px solid var(--ink-warn);font-size:11px;color:var(--ink-warn);">
            ${data.discipline_334.advice}
          </div>
        </div>

        <!-- 自选股 -->
        <div class="card">
          <div class="card-header">
            <div class="card-title">自选股概览</div>
            <button class="btn btn-ghost btn-sm" data-action="search-stock">查看全部</button>
          </div>
          <div style="display:flex;flex-direction:column;gap:2px;">
            ${data.watchlist.map(s => `
              <div class="stock-row" data-action="view-stock" data-code="${s.code}">
                <div class="stock-info">
                  <div class="stock-name">${s.name}</div>
                  <div class="stock-code">${s.code}</div>
                </div>
                <div style="display:flex;align-items:center;gap:12px;">
                  <span class="tag ${s.stale ? 'tag-amber' : 'tag-green'}">${s.stale ? '快照' : '实时'}</span>
                  <div style="text-align:right;">
                    <div class="stock-price ${ROX.fmt.color(s.change_pct)}">${ROX.fmt.num(s.price)}</div>
                    <div class="stock-change ${ROX.fmt.color(s.change_pct)}">${ROX.fmt.pct(s.change_pct)}</div>
                  </div>
                </div>
              </div>
            `).join('')}
          </div>
        </div>
      </div>

      <!-- 宏观资讯研判摘要 -->
      ${data.intelligence ? `
      <div class="grid-2">
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
      <div class="card full-width">
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
});
