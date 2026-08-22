/* ============================================
   ROX投资助手 — 自选股视图
   ============================================ */
ROX.register('/watchlist', async function(container) {
  container.innerHTML = `
    <div class="page-header" style="display:flex;justify-content:space-between;align-items:center;margin-bottom:24px;">
      <div>
        <h1 style="font-size:24px;font-weight:590;margin:0;">自选股</h1>
        <p style="color:var(--text-secondary);font-size:13px;margin:4px 0 0;">实时行情 · 一键加入 / 移除</p>
      </div>
      <button class="btn btn-primary" data-action="add-watch">+ 添加自选</button>
    </div>
    <div id="watchlist-body">
      <div style="text-align:center;padding:60px 0;color:var(--text-secondary);"><div style="font-size:14px;">加载中...</div></div>
    </div>
  `;
  await ROX.views.watchlist.load();
});

ROX.views = ROX.views || {};
ROX.views.watchlist = {
  async load() {
    const body = document.getElementById('watchlist-body');
    if (!body) return;
    const data = await ROX.api.get('/api/watchlist/');
    if (!data) {
      body.innerHTML = '<div class="empty-state"><p>加载失败，请检查网络连接</p></div>';
      return;
    }

    const list = data.watchlist || [];
    if (list.length === 0) {
      body.innerHTML = `
        <div class="card" style="padding:48px;text-align:center;color:var(--text-tertiary);">
          <p style="margin:0 0 8px;">暂无自选股</p>
          <p style="font-size:12px;margin:0 0 16px;">在个股页点击“加入自选”，或点击下方按钮手动添加。</p>
          <button class="btn btn-secondary btn-sm" data-action="add-watch">+ 添加自选</button>
        </div>`;
      this.bindAdd();
      return;
    }

    let html = '<div class="card" style="padding:8px 12px;"><div style="overflow-x:auto;"><table class="table-cards" style="width:100%;border-collapse:collapse;font-size:13px;">';
    html += `<thead><tr style="border-bottom:1px solid var(--border-color);">
      <th style="text-align:left;padding:8px 12px;color:var(--text-secondary);font-weight:500;">股票</th>
      <th style="text-align:right;padding:8px 12px;color:var(--text-secondary);font-weight:500;">现价</th>
      <th style="text-align:right;padding:8px 12px;color:var(--text-secondary);font-weight:500;">涨跌幅</th>
      <th style="text-align:center;padding:8px 12px;color:var(--text-secondary);font-weight:500;">排序 / 操作</th>
    </tr></thead><tbody>`;

    list.forEach((w, i) => {
      const up = (w.change_pct || 0) >= 0;
      const c = up ? 'var(--rox-up)' : 'var(--rox-down)';
      html += `<tr style="border-bottom:1px solid var(--border-color-light);cursor:pointer;" data-action="view-stock" data-code="${ROX.escape(w.code)}">
        <td data-label="股票" style="padding:8px 12px;font-weight:500;">${ROX.escape(w.price_name || w.name)} <span style="font-family:var(--font-mono);font-size:11px;color:var(--text-tertiary);">${ROX.escape(w.code)}</span></td>
        <td data-label="现价" style="text-align:right;padding:8px 12px;font-family:var(--font-mono);color:${c};">${w.price != null ? ROX.fmt.num(w.price) : '--'}</td>
        <td data-label="涨跌幅" style="text-align:right;padding:8px 12px;font-family:var(--font-mono);color:${c};">${w.change_pct != null ? ROX.fmt.pct(w.change_pct) : '--'}</td>
        <td data-label="" style="text-align:center;padding:8px 12px;white-space:nowrap;">
          <button class="btn btn-sm btn-ghost" data-action="watch-up" data-id="${w.id}" ${i === 0 ? 'disabled' : ''} style="margin-right:2px;" title="上移">↑</button>
          <button class="btn btn-sm btn-ghost" data-action="watch-down" data-id="${w.id}" ${i === list.length - 1 ? 'disabled' : ''} style="margin-right:8px;" title="下移">↓</button>
          <button class="btn btn-sm btn-ghost" data-action="watch-remove" data-id="${w.id}" style="color:var(--rox-down);font-size:12px;">移除</button>
        </td>
      </tr>`;
    });
    html += '</tbody></table></div></div>';
    body.innerHTML = html;
    this.bindActions(list);
  },

  bindActions(list) {
    document.querySelectorAll('[data-action="watch-remove"]').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        const res = await ROX.api.delete(`/api/watchlist/${btn.dataset.id}`);
        if (res && res.success) await this.load();
      });
    });
    document.querySelectorAll('[data-action="watch-up"], [data-action="watch-down"]').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        const id = btn.dataset.id;
        const idx = list.findIndex(w => String(w.id) === String(id));
        const swap = btn.dataset.action === 'watch-up' ? idx - 1 : idx + 1;
        if (swap < 0 || swap >= list.length) return;
        const order = list.map(w => w.id);
        [order[idx], order[swap]] = [order[swap], order[idx]];
        await ROX.api.put('/api/watchlist/reorder', order);
        await this.load();
      });
    });
    this.bindAdd();
  },

  bindAdd() {
    document.querySelectorAll('[data-action="add-watch"]').forEach(btn => {
      if (btn.dataset.bound) return;
      btn.dataset.bound = '1';
      btn.addEventListener('click', () => this.showAddModal());
    });
  },

  showAddModal() {
    ROX.showModal(`
      <div class="modal-header">
        <span class="modal-title">添加自选股</span>
        <div class="modal-close" data-action="close-modal"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6L6 18M6 6l12 12"/></svg></div>
      </div>
      <form id="add-watch-form" style="display:flex;flex-direction:column;gap:14px;">
        <div class="form-group">
          <label class="form-label">股票代码</label>
          <input class="form-input" name="code" placeholder="如 600519" required maxlength="10">
        </div>
        <div class="form-group">
          <label class="form-label">股票名称</label>
          <input class="form-input" name="name" placeholder="如 贵州茅台" required maxlength="30">
        </div>
        <div style="display:flex;gap:10px;justify-content:flex-end;">
          <button type="button" class="btn btn-secondary" data-action="close-modal">取消</button>
          <button type="submit" class="btn btn-primary">添加</button>
        </div>
      </form>`);
    document.getElementById('add-watch-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      const fd = new FormData(e.target);
      const payload = Object.fromEntries(fd);
      const res = await ROX.api.post('/api/watchlist/', payload);
      if (res && res.success) {
        ROX.closeModal();
        await this.load();
      } else {
        const detail = res?.detail;
        ROX.toast(typeof detail === 'string' ? detail : '添加失败，请检查输入', 'error');
      }
    });
  },
};
