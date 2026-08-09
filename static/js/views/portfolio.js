/* ============================================
   ROX投资助手 — 持仓组合视图
   ============================================ */
ROX.register('/portfolio', async function() {
  document.getElementById('app-main').innerHTML = '<div style="text-align:center;padding:60px 0;color:var(--text-secondary);"><div style="font-size:14px;">加载持仓中...</div></div>';
  await ROX.views.portfolio.load();
});

ROX.views = ROX.views || {};
ROX.views.portfolio = {
  async load() {
    const data = await ROX.api.get('/api/portfolio/');
    if (!data) {
      document.getElementById('app-main').innerHTML = '<div class="empty-state"><p>持仓数据加载失败</p></div>';
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
          <td style="text-align:right;padding:8px 12px;"><button class="btn btn-sm btn-ghost" data-action="delete-position" data-id="${p.id}" style="font-size:11px;color:var(--color-up);">删除</button></td>
        </tr>`;
      });
      html += '</tbody></table></div></div>';
    }

    document.getElementById('app-main').innerHTML = html;

    // Add position modal
    this.prepareAddForm();
  },

  prepareAddForm() {
    document.querySelector('[data-action="add-position"]')?.addEventListener('click', () => {
      const modal = document.getElementById('modal-container');
      if (!modal) return;
      modal.innerHTML = `
        <div class="modal-overlay" data-action="close-modal"></div>
        <div class="modal-card" style="background:var(--bg-glass);backdrop-filter:blur(20px);border:0.5px solid var(--border-color);border-radius:var(--radius-xl);padding:28px;max-width:420px;width:90%;">
          <h3 style="font-size:17px;font-weight:590;margin-bottom:18px;">添加持仓</h3>
          <form id="add-position-form" style="display:flex;flex-direction:column;gap:14px;">
            <input class="form-input" name="code" placeholder="股票代码 (6位)" required maxlength="10" style="border-radius:var(--radius-md);">
            <input class="form-input" name="name" placeholder="股票名称" required maxlength="30" style="border-radius:var(--radius-md);">
            <input class="form-input" name="shares" placeholder="持仓股数" required type="number" step="1" min="1" style="border-radius:var(--radius-md);">
            <input class="form-input" name="cost_price" placeholder="成本价" required type="number" step="0.01" min="0.01" style="border-radius:var(--radius-md);">
            <input class="form-input" name="date" placeholder="建仓日期 (如 2026-08-09)" required maxlength="10" style="border-radius:var(--radius-md);">
            <textarea class="form-textarea" name="notes" placeholder="备注 (可选)" maxlength="500" rows="2" style="border-radius:var(--radius-md);"></textarea>
            <div style="display:flex;gap:10px;justify-content:flex-end;">
              <button type="button" class="btn btn-secondary" data-action="close-modal">取消</button>
              <button type="submit" class="btn btn-primary">确认添加</button>
            </div>
          </form>
        </div>
      `;
      modal.style.display = 'flex';

      document.getElementById('add-position-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const fd = new FormData(e.target);
        const payload = Object.fromEntries(fd);
        payload.shares = parseFloat(payload.shares);
        payload.cost_price = parseFloat(payload.cost_price);
        const res = await ROX.api.post('/api/portfolio/', payload);
        if (res && res.success) {
          modal.style.display = 'none';
          await this.load();
        } else {
          alert('添加失败，请检查输入');
        }
      });
    });

    // Delete buttons
    document.querySelectorAll('[data-action="delete-position"]').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        const id = btn.dataset.id;
        if (confirm('确认删除该持仓？')) {
          await ROX.api.delete(`/api/portfolio/${id}`);
          await this.load();
        }
      });
    });

    // Close modal
    document.querySelectorAll('[data-action="close-modal"]').forEach(el => {
      el.addEventListener('click', () => {
        document.getElementById('modal-container').style.display = 'none';
      });
    });
  },
};
