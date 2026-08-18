/* ============================================
   ROX投资助手 — 预警管理视图
   ============================================ */
ROX.register('/alerts', async function() {
  const view = document.getElementById('view-container');
  view.innerHTML = '<div style="text-align:center;padding:60px 0;color:var(--text-secondary);"><div style="font-size:14px;">加载预警中...</div></div>';
  await ROX.views.alerts.load();
});

ROX.views = ROX.views || {};
ROX.views.alerts = {
  async load() {
    const data = await ROX.api.get('/api/alerts/');
    if (!data) {
      document.getElementById('view-container').innerHTML = '<div class="empty-state"><p>预警数据加载失败</p></div>';
      return;
    }
    if (data.status === 'disabled') {
      document.getElementById('view-container').innerHTML = ROX.disabledState(data.reason);
      return;
    }
    this.render(data);
  },

  render(data) {
    const alerts = data.alerts || [];
    const esc = ROX.escape;
    const fmt = ROX.fmt;

    // 分组：已触发 / 生效中 / 已暂停
    const triggered = alerts.filter(a => a.triggered);
    const active = alerts.filter(a => a.active && !a.triggered);
    const paused = alerts.filter(a => !a.active);

    let html = `
      <div class="page-header" style="display:flex;justify-content:space-between;align-items:center;margin-bottom:24px;">
        <div>
          <h1 style="font-size:24px;font-weight:590;margin:0;">价格预警</h1>
          <p style="color:var(--text-secondary);font-size:13px;margin:4px 0 0;">触发检测 · 激活暂停 · 实时监控</p>
        </div>
        <div style="display:flex;gap:8px;align-items:center;">
          <button class="btn btn-secondary btn-sm" data-action="refresh-alerts">刷新</button>
          <button class="btn btn-primary" data-action="add-alert">+ 新建预警</button>
        </div>
      </div>

      <div class="card" style="padding:16px;margin-bottom:20px;">
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(100px,1fr));gap:16px;">
          <div style="text-align:center;"><div style="font-size:11px;color:var(--text-tertiary);">总预警</div><div style="font-size:22px;font-weight:590;">${alerts.length}</div></div>
          <div style="text-align:center;"><div style="font-size:11px;color:var(--text-tertiary);">已触发</div><div style="font-size:22px;font-weight:590;color:var(--rox-up);">${triggered.length}</div></div>
          <div style="text-align:center;"><div style="font-size:11px;color:var(--text-tertiary);">生效中</div><div style="font-size:22px;font-weight:590;color:var(--rox-accent);">${active.length}</div></div>
          <div style="text-align:center;"><div style="font-size:11px;color:var(--text-tertiary);">已暂停</div><div style="font-size:22px;font-weight:590;color:var(--text-tertiary);">${paused.length}</div></div>
        </div>
      </div>
    `;

    if (alerts.length === 0) {
      html += '<div class="card" style="padding:40px;text-align:center;color:var(--text-tertiary);"><p>暂无预警，点击"+ 新建预警"开始设置价格提醒</p></div>';
    } else {
      // 已触发
      if (triggered.length) {
        html += `<div class="card" style="padding:16px;margin-bottom:16px;">
          <div class="card-header"><div class="card-title">已触发 (${triggered.length})</div><span class="tag tag-red">触发</span></div>
          ${triggered.map(a => this.renderRow(a, esc, fmt)).join('')}
        </div>`;
      }
      // 生效中
      if (active.length) {
        html += `<div class="card" style="padding:16px;margin-bottom:16px;">
          <div class="card-header"><div class="card-title">生效中 (${active.length})</div><span class="tag tag-green">监控</span></div>
          ${active.map(a => this.renderRow(a, esc, fmt)).join('')}
        </div>`;
      }
      // 已暂停
      if (paused.length) {
        html += `<div class="card" style="padding:16px;margin-bottom:16px;">
          <div class="card-header"><div class="card-title">已暂停 (${paused.length})</div><span class="tag tag-gray">暂停</span></div>
          ${paused.map(a => this.renderRow(a, esc, fmt)).join('')}
        </div>`;
      }
    }

    document.getElementById('view-container').innerHTML = html;
    this.prepareActions();
  },

  renderRow(a, esc, fmt) {
    const dirIcon = a.direction === 'above' ? '↑≥' : '↓≤';
    const dirColor = a.direction === 'above' ? 'var(--rox-up)' : 'var(--rox-down)';
    const statusBadge = a.triggered
      ? '<span class="tag tag-red">已触发</span>'
      : a.active
        ? '<span class="tag tag-green">生效中</span>'
        : '<span class="tag tag-gray">已暂停</span>';
    const toggleLabel = a.active ? '暂停' : '激活';
    const toggleColor = a.active ? 'var(--text-tertiary)' : 'var(--rox-accent)';

    return `
      <div style="display:flex;justify-content:space-between;align-items:center;padding:10px 12px;border-bottom:1px solid var(--border-color-light);cursor:pointer;" data-action="view-stock" data-code="${esc(a.code)}">
        <div style="display:flex;align-items:center;gap:12px;flex:1;min-width:0;">
          <div>
            <div style="font-size:13px;font-weight:500;">${esc(a.price_name || a.name)}</div>
            <div style="font-size:11px;color:var(--text-tertiary);font-family:var(--font-mono);">${esc(a.code)}</div>
          </div>
          ${statusBadge}
        </div>
        <div style="display:flex;align-items:center;gap:16px;flex-shrink:0;">
          <div style="text-align:right;">
            <div style="font-size:11px;color:var(--text-tertiary);">目标价</div>
            <div style="font-size:13px;font-family:var(--font-mono);color:${dirColor};">${dirIcon} ${fmt.num(a.target_price)}</div>
          </div>
          <div style="text-align:right;">
            <div style="font-size:11px;color:var(--text-tertiary);">现价</div>
            <div style="font-size:13px;font-family:var(--font-mono);">${a.current_price != null ? fmt.num(a.current_price) : '--'}</div>
          </div>
          <button class="btn btn-sm btn-ghost" data-action="toggle-alert" data-id="${a.id}" data-active="${a.active}" style="font-size:11px;color:${toggleColor};white-space:nowrap;" onclick="event.stopPropagation()">${toggleLabel}</button>
          <button class="btn btn-sm btn-ghost" data-action="delete-alert" data-id="${a.id}" style="font-size:11px;color:var(--rox-down);white-space:nowrap;" onclick="event.stopPropagation()">删除</button>
        </div>
      </div>
    `;
  },

  prepareActions() {
    document.querySelector('[data-action="refresh-alerts"]')?.addEventListener('click', async () => {
      await this.load();
      ROX.toast('预警已刷新', 'info');
    });

    document.querySelector('[data-action="add-alert"]')?.addEventListener('click', () => {
      this.showAddModal();
    });

    document.querySelectorAll('[data-action="toggle-alert"]').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        const id = btn.dataset.id;
        const currentActive = btn.dataset.active === 'true';
        const res = await ROX.api.put(`/api/alerts/${id}`, { active: !currentActive });
        if (res && res.success) {
          ROX.toast(!currentActive ? '预警已激活' : '预警已暂停', 'success');
          await this.load();
        } else {
          ROX.toast('操作失败', 'error');
        }
      });
    });

    document.querySelectorAll('[data-action="delete-alert"]').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        const id = btn.dataset.id;
        ROX.confirm('确认删除该预警？', async () => {
          await ROX.api.delete(`/api/alerts/${id}`);
          ROX.toast('预警已删除', 'success');
          await this.load();
        });
      });
    });
  },

  showAddModal() {
    ROX.showModal(`
      <div class="modal-header">
        <span class="modal-title">新建价格预警</span>
        <div class="modal-close" data-action="close-modal"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6L6 18M6 6l12 12"/></svg></div>
      </div>
      <form id="add-alert-form" style="display:flex;flex-direction:column;gap:14px;">
        <div class="form-group"><label class="form-label">股票代码</label><input class="form-input" name="code" placeholder="如 600519" required maxlength="10"></div>
        <div class="form-group"><label class="form-label">股票名称</label><input class="form-input" name="name" placeholder="如 贵州茅台" required maxlength="30"></div>
        <div class="grid-2">
          <div class="form-group"><label class="form-label">目标价格</label><input class="form-input" name="target_price" placeholder="如 1800.00" required type="number" step="0.01" min="0.01"></div>
          <div class="form-group"><label class="form-label">触发方向</label><select class="form-select" name="direction"><option value="above">向上突破 ≥</option><option value="below">向下跌破 ≤</option></select></div>
        </div>
        <div style="display:flex;gap:10px;justify-content:flex-end;">
          <button type="button" class="btn btn-secondary" data-action="close-modal">取消</button>
          <button type="submit" class="btn btn-primary">创建预警</button>
        </div>
      </form>`);
    document.getElementById('add-alert-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      const fd = new FormData(e.target);
      const payload = Object.fromEntries(fd);
      payload.target_price = parseFloat(payload.target_price);
      const res = await ROX.api.post('/api/alerts/', payload);
      if (res && res.success) {
        ROX.closeModal();
        ROX.toast('预警创建成功', 'success');
        await this.load();
      } else {
        ROX.toast('创建失败，请检查输入', 'error');
      }
    });
  },
};
