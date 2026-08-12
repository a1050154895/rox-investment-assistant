/* ============================================
   ROX投资助手 — 持仓组合视图
   ============================================ */
ROX.register('/portfolio', async function() {
  const view = document.getElementById('view-container');
  view.innerHTML = '<div style="text-align:center;padding:60px 0;color:var(--text-secondary);"><div style="font-size:14px;">加载持仓中...</div></div>';
  await ROX.views.portfolio.load();
});

ROX.views = ROX.views || {};
ROX.views.portfolio = {
  async load() {
    const data = await ROX.api.get('/api/portfolio/');
    if (!data) {
      document.getElementById('view-container').innerHTML = '<div class="empty-state"><p>持仓数据加载失败</p></div>';
      return;
    }
    this.render(data);
  },

  render(data) {
    const s = data.summary || {};
    const pnlColor = s.total_pnl >= 0 ? 'var(--color-up)' : 'var(--color-down)';
    const esc = ROX.escape;
    const fmt = ROX.fmt;

    let html = `
      <div class="page-header" style="display:flex;justify-content:space-between;align-items:center;margin-bottom:24px;">
        <div>
          <h1 style="font-size:24px;font-weight:590;margin:0;">持仓组合</h1>
          <p style="color:var(--text-secondary);font-size:13px;margin:4px 0 0;">实时盈亏 · 仓位分布</p>
        </div>
      <div style="display:flex;gap:8px;align-items:center;">
        <a href="/api/export/portfolio" class="btn btn-secondary btn-sm">导出CSV</a>
        <button class="btn btn-primary" data-action="add-position">添加持仓</button>
      </div>
      </div>

      <div class="card" style="padding:20px;margin-bottom:20px;">
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:16px;">
          <div style="text-align:center;"><div style="font-size:11px;color:var(--text-tertiary);">持仓数</div><div style="font-size:22px;font-weight:590;">${s.count || 0}</div></div>
          <div style="text-align:center;"><div style="font-size:11px;color:var(--text-tertiary);">总成本</div><div style="font-size:22px;font-weight:590;">${fmt.num(s.total_cost)}</div></div>
          <div style="text-align:center;"><div style="font-size:11px;color:var(--text-tertiary);">总市值</div><div style="font-size:22px;font-weight:590;">${fmt.num(s.total_market)}</div></div>
          <div style="text-align:center;"><div style="font-size:11px;color:var(--text-tertiary);">总盈亏</div><div style="font-size:22px;font-weight:590;color:${pnlColor};">${fmt.num(s.total_pnl)}</div></div>
          <div style="text-align:center;"><div style="font-size:11px;color:var(--text-tertiary);">收益率</div><div style="font-size:22px;font-weight:590;color:${pnlColor};">${fmt.pct(s.total_pnl_pct)}</div></div>
        </div>
      </div>
    `;

    const positions = data.positions || [];
    if (positions.length === 0) {
      html += '<div class="card" style="padding:40px;text-align:center;color:var(--text-tertiary);"><p>暂无持仓，点击"添加持仓"开始记录</p></div>';
    } else {
      html += '<div class="card" style="padding:20px;"><div style="overflow-x:auto;"><table style="width:100%;border-collapse:collapse;font-size:13px;"><thead><tr style="border-bottom:1px solid var(--border-color);">';
      ['股票','股数','成本价','现价','成本','市值','盈亏','盈亏%','建仓日',''].forEach(h => html += `<th style="text-align:${h==='股票'?'left':'right'};padding:8px 12px;color:var(--text-secondary);font-weight:500;">${h}</th>`);
      html += '</tr></thead><tbody>';
      positions.forEach(p => {
        const cp = p.pnl >= 0 ? 'var(--color-up)' : 'var(--color-down)';
        html += `<tr style="border-bottom:1px solid var(--border-color-light);cursor:pointer;" data-action="view-stock" data-code="${esc(p.code)}">
          <td style="padding:8px 12px;font-weight:500;">${esc(p.name)} <span style="font-family:var(--font-mono);font-size:11px;color:var(--text-tertiary);">${esc(p.code)}</span></td>
          <td style="text-align:right;padding:8px 12px;font-family:var(--font-mono);">${p.shares}</td>
          <td style="text-align:right;padding:8px 12px;font-family:var(--font-mono);">${fmt.num(p.cost_price)}</td>
          <td style="text-align:right;padding:8px 12px;font-family:var(--font-mono);">${p.price != null ? fmt.num(p.price) : '--'}</td>
          <td style="text-align:right;padding:8px 12px;font-family:var(--font-mono);color:var(--text-tertiary);">${fmt.num(p.cost)}</td>
          <td style="text-align:right;padding:8px 12px;font-family:var(--font-mono);">${fmt.num(p.market)}</td>
          <td style="text-align:right;padding:8px 12px;font-family:var(--font-mono);color:${cp};font-weight:500;">${fmt.num(p.pnl)}</td>
          <td style="text-align:right;padding:8px 12px;font-family:var(--font-mono);color:${cp};">${fmt.pct(p.pnl_pct)}</td>
          <td style="text-align:right;padding:8px 12px;font-size:12px;color:var(--text-tertiary);">${esc(p.date)}</td>
          <td style="text-align:right;padding:8px 12px;white-space:nowrap;"><button class="btn btn-sm btn-ghost" data-action="edit-position" data-id="${p.id}" data-code="${esc(p.code)}" data-name="${esc(p.name)}" data-shares="${p.shares}" data-cost="${p.cost_price}" data-date="${esc(p.date)}" data-notes="${esc(p.notes||'')}" style="font-size:11px;">编辑</button><button class="btn btn-sm btn-ghost" data-action="delete-position" data-id="${p.id}" style="font-size:11px;color:var(--color-up);margin-left:4px;">删除</button></td>
        </tr>`;
      });
      html += '</tbody></table></div></div>';
    }

    document.getElementById('view-container').innerHTML = html;

    // Add position modal + delete buttons
    this.prepareActions();
  },

  prepareActions() {
    document.querySelector('[data-action="add-position"]')?.addEventListener('click', () => {
      this.showAddModal();
    });

    document.querySelectorAll('[data-action="delete-position"]').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        const id = btn.dataset.id;
        if (confirm('确认删除该持仓？')) {
          await ROX.api.delete(`/api/portfolio/${id}`);
          ROX.toast('持仓已删除', 'success');
          await this.load();
        }
      });
    });

    document.querySelectorAll('[data-action="edit-position"]').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        this.showEditModal(btn.dataset);
      });
    });
  },

  showAddModal() {
    ROX.showModal(`
      <div class="modal-header">
        <span class="modal-title">添加持仓</span>
        <div class="modal-close" data-action="close-modal"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6L6 18M6 6l12 12"/></svg></div>
      </div>
      <form id="add-position-form" style="display:flex;flex-direction:column;gap:14px;">
        <div class="form-group"><label class="form-label">股票代码</label><input class="form-input" name="code" placeholder="如 600519" required maxlength="10"></div>
        <div class="form-group"><label class="form-label">股票名称</label><input class="form-input" name="name" placeholder="如 贵州茅台" required maxlength="30"></div>
        <div class="form-group"><label class="form-label">持仓股数</label><input class="form-input" name="shares" placeholder="持仓股数" required type="number" step="1" min="1"></div>
        <div class="form-group"><label class="form-label">成本价</label><input class="form-input" name="cost_price" placeholder="成本价" required type="number" step="0.01" min="0.01"></div>
        <div class="form-group"><label class="form-label">建仓日期</label><input class="form-input" name="date" placeholder="如 2026-08-09" required maxlength="10"></div>
        <div class="form-group"><label class="form-label">备注（可选）</label><textarea class="form-textarea" name="notes" placeholder="备注 (可选)" maxlength="500" rows="2"></textarea></div>
        <div style="display:flex;gap:10px;justify-content:flex-end;">
          <button type="button" class="btn btn-secondary" data-action="close-modal">取消</button>
          <button type="submit" class="btn btn-primary">确认添加</button>
        </div>
      </form>`);
    document.getElementById('add-position-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      const fd = new FormData(e.target);
      const payload = Object.fromEntries(fd);
      payload.shares = parseFloat(payload.shares);
      payload.cost_price = parseFloat(payload.cost_price);
      const res = await ROX.api.post('/api/portfolio/', payload);
      if (res && res.success) {
        ROX.closeModal();
        ROX.toast('持仓添加成功', 'success');
        await this.load();
      } else {
        ROX.toast('添加失败，请检查输入', 'error');
      }
    });
  },

  showEditModal(d) {
    ROX.showModal(`
      <div class="modal-header">
        <span class="modal-title">编辑持仓 — ${ROX.escape(d.name)}</span>
        <div class="modal-close" data-action="close-modal"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6L6 18M6 6l12 12"/></svg></div>
      </div>
      <form id="edit-position-form" style="display:flex;flex-direction:column;gap:14px;">
        <div class="form-group"><label class="form-label">股票代码</label><input class="form-input" value="${ROX.escape(d.code)}" disabled style="opacity:0.6;"></div>
        <div class="form-group"><label class="form-label">股票名称</label><input class="form-input" value="${ROX.escape(d.name)}" disabled style="opacity:0.6;"></div>
        <div class="form-group"><label class="form-label">持仓股数</label><input class="form-input" name="shares" value="${d.shares}" required type="number" step="1" min="1"></div>
        <div class="form-group"><label class="form-label">成本价</label><input class="form-input" name="cost_price" value="${d.cost}" required type="number" step="0.01" min="0.01"></div>
        <div class="form-group"><label class="form-label">建仓日期</label><input class="form-input" name="date" value="${ROX.escape(d.date)}" required maxlength="10"></div>
        <div class="form-group"><label class="form-label">备注（可选）</label><textarea class="form-textarea" name="notes" maxlength="500" rows="2">${ROX.escape(d.notes)}</textarea></div>
        <div style="display:flex;gap:10px;justify-content:flex-end;">
          <button type="button" class="btn btn-secondary" data-action="close-modal">取消</button>
          <button type="submit" class="btn btn-primary">保存修改</button>
        </div>
      </form>`);
    document.getElementById('edit-position-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      const fd = new FormData(e.target);
      const payload = Object.fromEntries(fd);
      payload.shares = parseFloat(payload.shares);
      payload.cost_price = parseFloat(payload.cost_price);
      const res = await ROX.api.put(`/api/portfolio/${d.id}`, payload);
      if (res && res.success) {
        ROX.closeModal();
        ROX.toast('持仓已更新', 'success');
        await this.load();
      } else {
        ROX.toast('更新失败，请检查输入', 'error');
      }
    });
  },
};
