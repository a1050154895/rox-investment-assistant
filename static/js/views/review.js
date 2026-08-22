/* ============================================
   ROX投资助手 — 每日复盘视图
   ============================================ */
ROX.register('/review', async function() {
  const html = `
    <div class="page-header review-header-row" style="display:flex;justify-content:space-between;align-items:center;margin-bottom:24px;">
      <div>
        <h1 style="font-size:24px;font-weight:700;margin:0;">每日复盘</h1>
        <p style="color:var(--text-secondary);font-size:13px;margin:4px 0 0;">市场全景 · 涨跌统计 · 板块资金 · 情绪评分</p>
      </div>
      <button class="btn btn-secondary" data-action="refresh-review">刷新</button>
    </div>
    <div id="review-content">
      <div style="text-align:center;padding:60px 0;color:var(--text-secondary);">
        <div style="font-size:14px;">加载复盘中...</div>
      </div>
    </div>
  `;
  document.getElementById('view-container').innerHTML = html;
  await ROX.views.review.load();
});

ROX.views = ROX.views || {};
ROX.views.review = {
  async load() {
    const [data, researchStats] = await Promise.all([
      ROX.api.get('/api/review/daily'),
      ROX.api.get('/api/review/research-stats'),
    ]);
    if (!data || data.error) {
      document.getElementById('review-content').innerHTML = `
        <div style="text-align:center;padding:40px;color:var(--text-secondary);">
          <div style="font-size:14px;">复盘数据加载失败，请稍后重试</div>
        </div>`;
      return;
    }
    this.render(data, researchStats && !researchStats.error ? researchStats : null);
  },

  render(data, researchStats) {
    const fmt = ROX.fmt;
    const esc = ROX.escape;
    let html = '';

    // 复盘摘要
    html += `
      <div class="card review-summary-card" style="margin-bottom:20px;padding:20px;">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px;">
          <h2 style="font-size:16px;font-weight:600;margin:0;">复盘摘要</h2>
          <span style="font-size:12px;color:var(--text-secondary);">${esc(data.datetime || data.date || '')}</span>
        </div>
        <p style="font-size:14px;line-height:1.8;color:var(--text-primary);margin:0;">${esc(data.summary || '')}</p>
        <div style="margin-top:12px;padding-top:12px;border-top:1px solid var(--border-color);font-size:12px;color:var(--text-tertiary);">
          数据来源：${esc(data.data_source || '')} · ${esc(data.disclaimer || '')}
        </div>
      </div>
    `;

    if (researchStats) {
      const cards = researchStats.cards || {};
      const decisions = researchStats.decisions || {};
      const coverage = researchStats.coverage || {};
      const hs = (cards.hypothesis_status || {});
      const validationRate = cards.hypothesis_validation_rate == null ? '--' : `${cards.hypothesis_validation_rate}%`;
      const winRate = decisions.win_rate == null ? '--' : `${decisions.win_rate}%`;
      const avgScore = decisions.avg_consistency == null ? '--' : decisions.avg_consistency;
      const avgReturn = decisions.avg_result_pct == null ? '--' : `${decisions.avg_result_pct > 0 ? '+' : ''}${decisions.avg_result_pct}%`;
      html += `
        <div class="card research-review-card review-research-card" style="margin-bottom:20px;padding:20px;">
          <div class="card-header" style="margin-bottom:14px;">
            <div><div class="eyebrow">ROX LOOP / REVIEW</div><div class="card-title">研究卡复盘</div><div class="card-subtitle">只统计已关联研究卡的决策；待观察样本不计入胜率。</div></div>
            <span class="tag tag-gray">${coverage.linked_cards || 0}/${cards.total || 0} 张已产生决策</span>
          </div>
          <div class="research-review-metrics">
            <div><span>研究卡</span><strong>${cards.total || 0}</strong><small>草稿 ${cards.draft || 0} · 待决策 ${cards.ready || 0}</small></div>
            <div><span>关联决策</span><strong>${decisions.total || 0}</strong><small>待观察 ${decisions.pending || 0} · 已结算 ${decisions.settled || 0}</small></div>
            <div><span>结算胜率</span><strong>${winRate}</strong><small>盈 ${decisions.wins || 0} · 亏 ${decisions.losses || 0}</small></div>
            <div><span>平均一致性</span><strong>${avgScore}</strong><small>平均结果 ${avgReturn}</small></div>
          </div>
          <div class="research-hypothesis-row">
            <span>假设成立 <strong>${hs['成立'] || 0}</strong></span>
            <span>部分成立 <strong>${hs['部分成立'] || 0}</strong></span>
            <span>失效 <strong>${hs['失效'] || 0}</strong></span>
            <span>未验证 <strong>${hs['未验证'] || 0}</strong></span>
            <span class="research-hypothesis-rate">假设验证率 ${validationRate}</span>
          </div>
          <div class="research-review-note">未关联决策的研究卡：${coverage.unlinked_cards || 0} 张。先完成研究卡，再记录决策，复盘才有依据。</div>
          <div class="research-review-actions" style="display:flex;gap:8px;margin-top:12px;">
            <button class="btn btn-secondary btn-sm" data-route="/research">去研究台更新状态 →</button>
          </div>
        </div>
      `;
    }

    // 情绪评分 + 指数概览
    const sentiment = data.sentiment || {};
    const sentimentColor = sentiment.score >= 60 ? 'var(--color-up)' : sentiment.score >= 40 ? 'var(--text-secondary)' : 'var(--color-down)';
    html += `
      <div class="review-overview-grid review-market-snapshot" style="display:grid;grid-template-columns:1fr 2fr;gap:20px;margin-bottom:20px;" id="review-grid">
        <div class="card" style="padding:20px;text-align:center;">
          <h3 style="font-size:14px;font-weight:600;margin:0 0 12px;color:var(--text-secondary);">市场情绪</h3>
          <div style="font-size:36px;font-weight:700;color:${sentimentColor};margin-bottom:4px;">${fmt.num(sentiment.score, 0)}</div>
          <div style="font-size:16px;font-weight:600;color:${sentimentColor};margin-bottom:8px;">${esc(sentiment.label || '--')}</div>
          <div style="font-size:12px;color:var(--text-tertiary);line-height:1.6;">${esc(sentiment.suggestion || '')}</div>
        </div>
        <div class="card" style="padding:20px;">
          <h3 style="font-size:14px;font-weight:600;margin:0 0 12px;color:var(--text-secondary);">主要指数</h3>
          <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:12px;">
            ${(data.indices || []).map(idx => {
              const color = idx.change_pct > 0 ? 'var(--color-up)' : idx.change_pct < 0 ? 'var(--color-down)' : 'var(--text-secondary)';
              return `
                <div style="padding:12px;background:var(--bg-secondary);border-radius:8px;">
                  <div style="font-size:12px;color:var(--text-secondary);margin-bottom:4px;">${esc(idx.name)}</div>
                  <div style="font-size:18px;font-weight:600;color:${color};">${fmt.num(idx.price)}</div>
                  <div style="font-size:12px;color:${color};">${fmt.pct(idx.change_pct)}</div>
                </div>
              `;
            }).join('')}
          </div>
        </div>
      </div>
    `;

    // 涨跌统计
    const br = data.breadth || {};
    html += `
      <div class="review-breadth-grid review-market-evidence" style="display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:20px;">
        <div class="card" style="padding:20px;">
          <h3 style="font-size:14px;font-weight:600;margin:0 0 12px;color:var(--text-secondary);">涨跌统计（样本池 ${br.total_stocks || 0} 只）</h3>
          <div style="display:flex;gap:16px;margin-bottom:16px;">
            <div style="flex:1;text-align:center;padding:12px;background:rgba(255,69,58,0.08);border-radius:8px;">
              <div style="font-size:24px;font-weight:700;color:var(--color-up);">${br.up_count || 0}</div>
              <div style="font-size:12px;color:var(--text-secondary);">上涨</div>
            </div>
            <div style="flex:1;text-align:center;padding:12px;background:var(--bg-secondary);border-radius:8px;">
              <div style="font-size:24px;font-weight:700;color:var(--text-secondary);">${br.flat_count || 0}</div>
              <div style="font-size:12px;color:var(--text-secondary);">平盘</div>
            </div>
            <div style="flex:1;text-align:center;padding:12px;background:rgba(48,209,88,0.08);border-radius:8px;">
              <div style="font-size:24px;font-weight:700;color:var(--color-down);">${br.down_count || 0}</div>
              <div style="font-size:12px;color:var(--text-secondary);">下跌</div>
            </div>
          </div>
          <div style="display:flex;gap:16px;">
            <div style="flex:1;text-align:center;padding:8px;background:rgba(255,69,58,0.06);border-radius:6px;">
              <span style="font-size:14px;font-weight:600;color:var(--color-up);">涨停 ${br.limit_up || 0}</span>
            </div>
            <div style="flex:1;text-align:center;padding:8px;background:rgba(48,209,88,0.06);border-radius:6px;">
              <span style="font-size:14px;font-weight:600;color:var(--color-down);">跌停 ${br.limit_down || 0}</span>
            </div>
          </div>
        </div>
        <div class="card" style="padding:20px;">
          <h3 style="font-size:14px;font-weight:600;margin:0 0 12px;color:var(--text-secondary);">领涨 / 领跌</h3>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">
            <div>
              <div style="font-size:12px;color:var(--color-up);margin-bottom:8px;font-weight:600;">领涨</div>
              ${(br.top_gainers || []).map(s => `
                <div style="display:flex;justify-content:space-between;padding:4px 0;font-size:13px;cursor:pointer;" data-action="view-stock" data-code="${esc(s.code)}">
                  <span>${esc(s.name)}</span>
                  <span style="color:var(--color-up);font-weight:600;">${fmt.pct(s.change_pct)}</span>
                </div>
              `).join('') || '<div style="font-size:12px;color:var(--text-tertiary);">暂无</div>'}
            </div>
            <div>
              <div style="font-size:12px;color:var(--color-down);margin-bottom:8px;font-weight:600;">领跌</div>
              ${(br.top_losers || []).map(s => `
                <div style="display:flex;justify-content:space-between;padding:4px 0;font-size:13px;cursor:pointer;" data-action="view-stock" data-code="${esc(s.code)}">
                  <span>${esc(s.name)}</span>
                  <span style="color:var(--color-down);font-weight:600;">${fmt.pct(s.change_pct)}</span>
                </div>
              `).join('') || '<div style="font-size:12px;color:var(--text-tertiary);">暂无</div>'}
            </div>
          </div>
        </div>
      </div>
    `;

    // 板块资金流
    const sectors = data.sectors || [];
    html += `
      <div class="card review-sector-card" style="padding:20px;margin-bottom:20px;">
        <h3 style="font-size:14px;font-weight:600;margin:0 0 12px;color:var(--text-secondary);">板块资金流向（近5日）</h3>
        <div style="overflow-x:auto;" class="review-table-wrap">
          <table style="width:100%;border-collapse:collapse;font-size:13px;">
            <thead>
              <tr style="border-bottom:1px solid var(--border-color);">
                <th style="text-align:left;padding:8px 12px;color:var(--text-secondary);font-weight:600;">板块</th>
                <th style="text-align:right;padding:8px 12px;color:var(--text-secondary);font-weight:600;">主力净流入(亿)</th>
                <th style="text-align:right;padding:8px 12px;color:var(--text-secondary);font-weight:600;">净占比(%)</th>
                <th style="text-align:center;padding:8px 12px;color:var(--text-secondary);font-weight:600;">方向</th>
                <th style="text-align:left;padding:8px 12px;color:var(--text-secondary);font-weight:600;">驱动因素</th>
              </tr>
            </thead>
            <tbody>
              ${sectors.map(s => {
                const isInflow = s.trend === 'inflow';
                const flowColor = isInflow ? 'var(--color-up)' : 'var(--color-down)';
                return `
                  <tr style="border-bottom:1px solid var(--border-color-light);">
                    <td style="padding:8px 12px;font-weight:500;">${esc(s.sector)}</td>
                    <td style="padding:8px 12px;text-align:right;color:${flowColor};font-weight:600;">${s.flow > 0 ? '+' : ''}${fmt.num(s.flow)}</td>
                    <td style="padding:8px 12px;text-align:right;color:${flowColor};">${s.flow_pct != null ? fmt.pct(s.flow_pct) : '--'}</td>
                    <td style="padding:8px 12px;text-align:center;">
                      <span style="padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;background:${isInflow ? 'rgba(255,69,58,0.1)' : 'rgba(48,209,88,0.1)'};color:${flowColor};">
                        ${isInflow ? '流入' : '流出'}
                      </span>
                    </td>
                    <td style="padding:8px 12px;color:var(--text-tertiary);font-size:12px;">${esc(s.driver || '')}</td>
                  </tr>
                `;
              }).join('')}
            </tbody>
          </table>
        </div>
      </div>
    `;

    // 海外参照系
    const globalIdx = data.global_indices || [];
    if (globalIdx.length > 0) {
      html += `
        <div class="card" style="padding:20px;margin-bottom:20px;">
          <h3 style="font-size:14px;font-weight:600;margin:0 0 12px;color:var(--text-secondary);">外部参照系</h3>
          <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:12px;">
            ${globalIdx.map(g => {
              const gColor = g.change_pct > 0 ? 'var(--color-up)' : g.change_pct < 0 ? 'var(--color-down)' : 'var(--text-secondary)';
              return `
                <div style="padding:10px 12px;background:var(--bg-secondary);border-radius:8px;">
                  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
                    <span style="font-size:12px;color:var(--text-secondary);">${esc(g.name)}</span>
                    <span style="font-size:10px;color:var(--text-tertiary);">${esc(g.region)}</span>
                  </div>
                  <div style="font-size:16px;font-weight:600;color:${gColor};">${fmt.num(g.price)}</div>
                  <div style="font-size:12px;color:${gColor};">${fmt.pct(g.change_pct)}</div>
                </div>
              `;
            }).join('')}
          </div>
          <div style="margin-top:10px;padding-top:10px;border-top:1px solid var(--border-color);font-size:11px;color:var(--text-tertiary);line-height:1.5;">
            外部市场流向是 A 股主矛盾的外生变量——若海外风险资产共振下跌而 A 股抗跌，说明内生结构性因素在主导。
          </div>
        </div>
      `;
    }

    // 历史复盘
    html += `<div id="review-history" style="margin-bottom:20px;"></div>`;

    document.getElementById('review-content').innerHTML = html;

    // 异步加载历史
    this.loadHistory();
  },

  async loadHistory() {
    const container = document.getElementById('review-history');
    if (!container) return;
    container.innerHTML = '<div class="card" style="padding:20px;"><div style="font-size:13px;color:var(--text-secondary);">加载历史复盘...</div></div>';

    const data = await ROX.api.get('/api/review/history?days=7');
    if (!data || data.error || !data.history || data.history.length === 0) {
      container.innerHTML = '';
      return;
    }

    const rows = data.history.map(h => {
      const color = h.change_pct > 0 ? 'var(--color-up)' : h.change_pct < 0 ? 'var(--color-down)' : 'var(--text-secondary)';
      return `
        <tr style="border-bottom:1px solid var(--border-color-light);">
          <td style="padding:8px 12px;">${ROX.escape(h.date)}</td>
          <td style="padding:8px 12px;text-align:right;font-weight:600;">${ROX.fmt.num(h.index_price)}</td>
          <td style="padding:8px 12px;text-align:right;color:${color};font-weight:600;">${ROX.fmt.pct(h.change_pct)}</td>
          <td style="padding:8px 12px;text-align:center;">
            <span style="padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;background:var(--bg-secondary);color:${color};">${ROX.escape(h.sentiment)}</span>
          </td>
        </tr>
      `;
    }).join('');

    container.innerHTML = `
      <div class="card" style="padding:20px;">
        <h3 style="font-size:14px;font-weight:600;margin:0 0 12px;color:var(--text-secondary);">近7个交易日回顾</h3>
        <table style="width:100%;border-collapse:collapse;font-size:13px;">
          <thead>
            <tr style="border-bottom:1px solid var(--border-color);">
              <th style="text-align:left;padding:8px 12px;color:var(--text-secondary);font-weight:600;">日期</th>
              <th style="text-align:right;padding:8px 12px;color:var(--text-secondary);font-weight:600;">上证收盘</th>
              <th style="text-align:right;padding:8px 12px;color:var(--text-secondary);font-weight:600;">涨跌幅</th>
              <th style="text-align:center;padding:8px 12px;color:var(--text-secondary);font-weight:600;">情绪</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    `;
  },
};
