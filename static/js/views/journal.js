/* ============================================
   视图3 · 决策日志
   ============================================ */

ROX.register('/journal', async function(container) {
  const [decisions, stats] = await Promise.all([
    ROX.api.get('/api/journal/?limit=50'),
    ROX.api.get('/api/journal/stats/summary'),
  ]);

  if (!decisions) {
    container.innerHTML = '<div class="empty-state"><p>数据加载失败</p></div>';
    return;
  }

  container.innerHTML = `
    <div style="display:flex;flex-direction:column;gap:16px;">
      <!-- Stats Overview -->
      ${stats ? `
      <div class="grid-4">
        <div class="card">
          <div class="stat-item">
            <span class="stat-label">平均一致性评分</span>
            <span class="stat-value">${stats.avg_consistency}</span>
            <span class="stat-change" style="color:var(--text-tertiary);">共 ${stats.total} 条记录</span>
          </div>
        </div>
        <div class="card">
          <div class="stat-item">
            <span class="stat-label">框架符合率</span>
            <span class="stat-value">${stats.compliance_rate}<span>%</span></span>
            <span class="stat-change" style="color:var(--text-tertiary);">≥70分 ${stats.score_distribution.high} 条</span>
          </div>
        </div>
        <div class="card">
          <div class="stat-item">
            <span class="stat-label">胜率</span>
            <span class="stat-value">${stats.win_rate}<span>%</span></span>
            <span class="stat-change ${stats.wins>=stats.losses?'text-up':'text-down'}">盈 ${stats.wins} / 亏 ${stats.losses}</span>
          </div>
        </div>
        <div class="card">
          <div class="stat-item">
            <span class="stat-label">待观察</span>
            <span class="stat-value">${stats.pending}</span>
            <span class="stat-change" style="color:var(--text-tertiary);">${stats.common_error}</span>
          </div>
        </div>
      </div>
      ` : ''}

      <!-- Action Bar -->
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <div class="tabs" style="border:none;margin:0;">
          <div class="tab active" data-journal-filter="" id="filter-all">全部 (${decisions.total})</div>
          <div class="tab" data-journal-filter="买入" id="filter-buy">买入</div>
          <div class="tab" data-journal-filter="卖出" id="filter-sell">卖出</div>
          <div class="tab" data-journal-filter="持有" id="filter-hold">持有</div>
          <div class="tab" data-journal-filter="减仓" id="filter-reduce">减仓</div>
        </div>
        <div style="display:flex;gap:8px;">
          <button class="btn btn-secondary btn-sm" data-action="generate-review">生成复盘报告</button>
          <button class="btn btn-primary btn-sm" data-action="add-decision">+ 记录决策</button>
        </div>
      </div>

      <!-- Timeline -->
      <div class="timeline" id="journal-timeline">
        ${decisions.decisions.map(d => `
          <div class="timeline-item ${d.consistency_score < 60 ? 'low-score' : ''} ${d.result === '盈' ? 'win' : d.result === '亏' ? 'loss' : ''}">
            <div class="decision-card ${d.consistency_score < 60 ? 'low-score' : ''}" style="min-width:0;">
              <div class="decision-header">
                <div style="display:flex;align-items:center;gap:12px;">
                  <div>
                    <div class="decision-stock" style="cursor:pointer;" data-action="view-stock" data-code="${ROX.escape(d.code)}">${ROX.escape(d.stock)}</div>
                    <div class="decision-meta">${ROX.escape(d.code)} · ${ROX.escape(d.date)} · 持仓 ${Number(d.holding_days) || 0} 天</div>
                  </div>
                  <span class="tag ${ROX.fmt.actionTag(d.action)}">${d.action}</span>
                  <span class="tag tag-gray">${d.stage}</span>
                </div>
                <div style="display:flex;align-items:center;gap:8px;">
                  <span class="score-badge ${ROX.fmt.scoreClass(d.consistency_score)}">${d.consistency_score}</span>
                  <span style="font-size:10px;color:var(--text-tertiary);">${ROX.fmt.scoreLabel(d.consistency_score)}</span>
                </div>
              </div>

              <div style="display:flex;gap:12px;font-size:11px;color:var(--text-tertiary);">
                <span>周期：${d.cycle_stage}</span>
                <span>矛盾强度：${d.contradiction_intensity}</span>
                <span>价值实现度：${d.value_realization}</span>
              </div>

              <div style="font-size:12px;color:var(--text-secondary);line-height:1.6;padding:8px 12px;background:var(--bg-input);border-radius:var(--radius-md);">
                ${ROX.escape(d.reason || '未填写决策理由')}
              </div>

              <div style="display:flex;justify-content:space-between;align-items:center;">
                <div style="display:flex;align-items:center;gap:8px;">
                  ${d.result === '盈' ? `<span class="tag tag-red">盈 ${d.result_pct>=0?'+':''}${d.result_pct}%</span>` :
                    d.result === '亏' ? `<span class="tag tag-green">亏 ${d.result_pct}%</span>` :
                    `<span class="tag tag-gray">待观察</span>`}
                  ${d.review ? `<span style="font-size:11px;color:var(--text-tertiary);">${ROX.escape(d.review)}</span>` : ''}
                </div>
                <button class="btn btn-ghost btn-sm" data-action="edit-decision" data-id="${d.id}">更新结果</button>
              </div>
            </div>
          </div>
        `).join('')}
      </div>
    </div>
  `;

  // Filter tabs
  container.querySelectorAll('[data-journal-filter]').forEach(tab => {
    tab.addEventListener('click', async () => {
      container.querySelectorAll('[data-journal-filter]').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      const filter = tab.dataset.journalFilter;
      const url = filter ? `/api/journal/?action=${encodeURIComponent(filter)}&limit=50` : '/api/journal/?limit=50';
      const data = await ROX.api.get(url);
      if (!data) return;

      const timeline = document.getElementById('journal-timeline');
      if (data.decisions.length === 0) {
        timeline.innerHTML = '<div class="empty-state"><p>暂无记录</p></div>';
        return;
      }
      timeline.innerHTML = data.decisions.map(d => `
        <div class="timeline-item ${d.consistency_score < 60 ? 'low-score' : ''} ${d.result === '盈' ? 'win' : d.result === '亏' ? 'loss' : ''}">
          <div class="decision-card ${d.consistency_score < 60 ? 'low-score' : ''}" style="min-width:0;">
            <div class="decision-header">
              <div style="display:flex;align-items:center;gap:12px;">
                <div>
                  <div class="decision-stock" style="cursor:pointer;" data-action="view-stock" data-code="${d.code}">${d.stock}</div>
                  <div class="decision-meta">${d.code} · ${d.date} · 持仓 ${d.holding_days} 天</div>
                </div>
                <span class="tag ${ROX.fmt.actionTag(d.action)}">${d.action}</span>
                <span class="tag tag-gray">${d.stage}</span>
              </div>
              <div style="display:flex;align-items:center;gap:8px;">
                <span class="score-badge ${ROX.fmt.scoreClass(d.consistency_score)}">${d.consistency_score}</span>
                <span style="font-size:10px;color:var(--text-tertiary);">${ROX.fmt.scoreLabel(d.consistency_score)}</span>
              </div>
            </div>
            <div style="display:flex;gap:12px;font-size:11px;color:var(--text-tertiary);">
              <span>周期：${d.cycle_stage}</span>
              <span>矛盾强度：${d.contradiction_intensity}</span>
              <span>价值实现度：${d.value_realization}</span>
            </div>
            <div style="font-size:12px;color:var(--text-secondary);line-height:1.6;padding:8px 12px;background:var(--bg-input);border-radius:var(--radius-md);">
              ${d.reason || '未填写决策理由'}
            </div>
            <div style="display:flex;justify-content:space-between;align-items:center;">
              <div style="display:flex;align-items:center;gap:8px;">
                ${d.result === '盈' ? `<span class="tag tag-red">盈 ${d.result_pct>=0?'+':''}${d.result_pct}%</span>` :
                  d.result === '亏' ? `<span class="tag tag-green">亏 ${d.result_pct}%</span>` :
                  `<span class="tag tag-gray">待观察</span>`}
                ${d.review ? `<span style="font-size:11px;color:var(--text-tertiary);">${ROX.escape(d.review)}</span>` : ''}
              </div>
              <button class="btn btn-ghost btn-sm" data-action="edit-decision" data-id="${d.id}">更新结果</button>
            </div>
          </div>
        </div>
      `).join('');
    });
  });

  // Edit decision handler
  container.querySelectorAll('[data-action="edit-decision"]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const id = parseInt(btn.dataset.id);
      const decision = await ROX.api.get(`/api/journal/${id}`);
      if (!decision || decision.error) return;

      ROX.showModal(`
        <div class="modal-header">
          <span class="modal-title">更新决策结果 — ${ROX.escape(decision.stock)}</span>
          <div class="modal-close" data-action="close-modal"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6L6 18M6 6l12 12"/></svg></div>
        </div>
        <div style="display:flex;flex-direction:column;gap:16px;">
          <div class="grid-2">
            <div class="form-group">
              <label class="form-label">结果</label>
              <select class="form-select" id="edit-result">
                <option value="待观察" ${decision.result==='待观察'?'selected':''}>待观察</option>
                <option value="盈" ${decision.result==='盈'?'selected':''}>盈</option>
                <option value="亏" ${decision.result==='亏'?'selected':''}>亏</option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">收益率 (%)</label>
              <input class="form-input" type="number" step="0.1" id="edit-pct" value="${decision.result_pct||0}" placeholder="如 2.5 或 -1.5">
            </div>
          </div>
          <div class="form-group">
            <label class="form-label">复盘笔记</label>
            <textarea class="form-textarea" id="edit-review" placeholder="事后总结...">${ROX.escape(decision.review || '')}</textarea>
          </div>
          <div style="display:flex;gap:8px;justify-content:flex-end;">
            <button class="btn btn-secondary" data-action="close-modal">取消</button>
            <button class="btn btn-primary" id="btn-save-decision">保存</button>
          </div>
        </div>
      `);

      document.getElementById('btn-save-decision').addEventListener('click', async () => {
        const res = await ROX.api.put(`/api/journal/${id}`, {
          result: document.getElementById('edit-result').value,
          result_pct: parseFloat(document.getElementById('edit-pct').value),
          review: document.getElementById('edit-review').value,
        });
        if (res && res.success) {
          ROX.closeModal();
          ROX.navigate('/journal');
        }
      });
    });
  });
});
