/* 宏观行业漏斗 — 宏观状态 → 行业排序 → 候选样本。
   三段式过滤器：终点是候选池与方法论理由，不是买卖建议。 */
(function () {
  const DISCLAIMER_STYLE = 'font-size:11px;color:var(--text-tertiary);line-height:1.7;border-top:1px solid var(--border-default);padding-top:8px;margin-top:10px;';

  ROX.register('/funnel', async function (container) {
    container.innerHTML = `
      <div class="page-header"><h2>宏观行业漏斗</h2></div>
      <div class="card" style="padding:14px 20px;margin-bottom:14px;">
        <div style="font-size:12px;color:var(--text-tertiary);line-height:1.7;">三段式过滤器：宏观状态 → 行业排序（方法论匹配 + 实测资金流）→ 行业内候选样本。终点是<b>候选池</b>，具体操作看你自己。</div>
      </div>
      <div class="card" id="funnel-macro" style="margin-bottom:14px;"><div class="loading"><div class="spinner"></div></div></div>
      <div class="card" id="funnel-industries" style="margin-bottom:14px;"></div>
      <div class="card" id="funnel-pool"><div class="empty-state" style="padding:20px;"><p style="font-size:12px;margin:0;">在上方行业列表点「查看候选样本」，这里会显示该行业按流通市值排序的候选池。</p></div></div>`;

    const data = await ROX.api.get('/api/funnel/macro-industry');
    const macroEl = document.getElementById('funnel-macro');
    const indEl = document.getElementById('funnel-industries');
    if (!data || data.error) {
      macroEl.innerHTML = '<div class="empty-state"><p>漏斗数据加载失败，请稍后重试。</p></div>';
      return;
    }

    const scores = data.matrix_scores || {};
    macroEl.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
        <div class="card-title" style="font-size:14px;font-weight:600;">第一步 · 宏观状态</div>
        <span class="tag tag-blue">${ROX.escape(data.matrix_cell || '数据不足')}</span>
      </div>
      <div style="display:flex;gap:16px;font-size:12px;color:var(--text-secondary);">
        <span>财政信用条件：<b>${ROX.fmt.num(scores.fiscal, 1)}</b></span>
        <span>价值实现：<b>${ROX.fmt.num(scores.value, 1)}</b></span>
        <span>命中方法论规则：<b>${data.rule_count} 条</b></span>
      </div>
      <div style="font-size:11px;color:var(--text-tertiary);margin-top:6px;">${ROX.escape(data.message || '')}</div>`;

    if (!data.industries || !data.industries.length) {
      indEl.innerHTML = '<div class="empty-state" style="padding:24px;"><p>宏观状态处于中性区间，未命中任何行业规则——如实不排序，避免输出没有依据的偏好。</p></div>';
      return;
    }

    const flowCell = (item) => item.fund_flow != null
      ? `<span style="font-family:var(--font-mono);color:${item.fund_flow >= 0 ? 'var(--rox-up)' : 'var(--rox-down)'};">${item.fund_flow >= 0 ? '+' : ''}${ROX.fmt.num(item.fund_flow, 1)} 亿</span>`
      : '<span style="color:var(--text-tertiary);">暂不可用</span>';

    indEl.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
        <div class="card-title" style="font-size:14px;font-weight:600;">第二步 · 行业排序</div>
        <span class="tag tag-amber">方法论匹配 + 实测资金流</span>
      </div>
      <div style="display:flex;flex-direction:column;gap:8px;">
        ${data.industries.map(item => `
          <div style="border:1px solid var(--border-default);border-radius:10px;padding:10px 14px;">
            <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;">
              <div style="min-width:0;">
                <span style="font-weight:600;font-size:14px;">${ROX.escape(item.industry)}</span>
                <span class="tag tag-gray" style="margin-left:6px;">命中 ${item.score} 条规则</span>
              </div>
              <div style="display:flex;align-items:center;gap:10px;">
                <span style="font-size:11px;color:var(--text-tertiary);">5日主力资金 ${flowCell(item)}</span>
                ${item.pool_status === 'available'
                  ? `<button class="btn btn-secondary btn-sm" data-funnel-board="${ROX.escape(item.resolved_board)}" data-funnel-name="${ROX.escape(item.industry)}">查看候选样本</button>`
                  : `<button class="btn btn-secondary btn-sm" disabled title="${ROX.escape(item.pool_message || '候选样本不可用')}">候选不可用</button>`}
              </div>
            </div>
            <div style="font-size:11px;color:var(--text-tertiary);line-height:1.8;margin-top:6px;">
              ${item.reasons.map(r => `• ${ROX.escape(r)}`).join('<br>')}
            </div>
          </div>`).join('')}
      </div>
      <div style="${DISCLAIMER_STYLE}">${ROX.escape(data.disclaimer)}</div>`;

    indEl.querySelectorAll('[data-funnel-board]').forEach(btn => {
      btn.addEventListener('click', () => loadPool(btn.dataset.funnelBoard, btn.dataset.funnelName));
    });
  });

  async function loadPool(board, name) {
    const poolEl = document.getElementById('funnel-pool');
    if (!poolEl) return;
    poolEl.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
    poolEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    const data = await ROX.api.get(`/api/funnel/candidate-pool?board=${encodeURIComponent(board)}&size=8`);
    if (!data || data.error || data.data_status === 'unavailable') {
      const detail = data && data.message ? data.message : '候选样本加载失败';
      poolEl.innerHTML = `<div class="empty-state" style="padding:20px;"><p>${ROX.escape(detail)}</p></div>`;
      return;
    }
    poolEl.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
        <div class="card-title" style="font-size:14px;font-weight:600;">第三步 · ${ROX.escape(name)}候选池</div>
        <span class="tag tag-blue">${ROX.escape(data.sort_factor)}</span>
      </div>
      <div class="table-wrap" style="overflow-x:auto;">
        <table style="width:100%;border-collapse:collapse;font-size:13px;">
          <thead><tr style="color:var(--text-tertiary);text-align:left;">
            <th style="padding:6px 10px;">代码</th><th style="padding:6px 10px;">名称</th>
            <th style="padding:6px 10px;">现价</th><th style="padding:6px 10px;">流通市值</th>
            <th style="padding:6px 10px;">研究</th>
          </tr></thead>
          <tbody>
          ${data.candidates.map(c => `
            <tr style="border-top:1px solid var(--border-default);">
              <td style="padding:8px 10px;font-family:var(--font-mono);">${ROX.escape(c.code)}</td>
              <td style="padding:8px 10px;font-weight:600;">${ROX.escape(c.name)}</td>
              <td style="padding:8px 10px;font-family:var(--font-mono);">${c.price != null ? ROX.fmt.num(c.price) : '--'}</td>
              <td style="padding:8px 10px;font-size:12px;color:var(--text-tertiary);">${ROX.escape(c.market_cap_text)}</td>
              <td style="padding:8px 10px;"><button class="btn btn-secondary btn-sm" data-action="view-stock" data-code="${ROX.escape(c.code)}">个股透视</button></td>
            </tr>`).join('')}
          </tbody>
        </table>
      </div>
      <div style="${DISCLAIMER_STYLE}">${ROX.escape(data.disclaimer)}</div>`;
  }
})();
