/* ============================================
   ROX投资助手 — 快速速记视图
   借鉴 Gangtise 录音速记：盘中灵感、事件快记、关联研究卡
   ============================================ */
ROX.register('/notes', async function(container) {
  container.innerHTML = `
    <div class="page-header" style="display:flex;justify-content:space-between;align-items:center;margin-bottom:24px;">
      <div>
        <h1 style="font-size:24px;font-weight:590;margin:0;">快速速记</h1>
        <p style="color:var(--text-secondary);font-size:13px;margin:4px 0 0;">盘中灵感 · 事件快记 · 关联研究卡</p>
      </div>
    </div>
    <div id="notes-body">
      <div style="text-align:center;padding:60px 0;color:var(--text-secondary);"><div style="font-size:14px;">加载中...</div></div>
    </div>
  `;
  await ROX.views.notes.load();
});

ROX.views = ROX.views || {};
ROX.views.notes = {
  async load() {
    const body = document.getElementById('notes-body');
    if (!body) return;

    const loggedIn = await ROX.auth.ensure();
    if (!loggedIn) {
      body.innerHTML = '<div class="card" style="padding:48px;text-align:center;color:var(--text-tertiary);"><p>登录后使用速记功能</p></div>';
      return;
    }

    const [notes, tags] = await Promise.all([
      ROX.api.get('/api/notes/'),
      ROX.api.get('/api/notes/tags'),
    ]);

    if (!notes) {
      body.innerHTML = '<div class="empty-state"><p>加载失败，请检查网络</p></div>';
      return;
    }

    this.render(body, notes || [], tags || []);
  },

  render(body, notes, tags) {
    let html = '<div style="display:grid;grid-template-columns:1fr;gap:20px;">';

    // Composer
    html += `
      <div class="card" style="padding:20px;">
        <textarea id="note-input" class="form-input" rows="3" placeholder="记下一条灵感或观察..." style="width:100%;resize:vertical;font-size:14px;min-height:72px;"></textarea>
        <div style="display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-top:12px;">
          <input id="note-code" class="form-input" placeholder="代码(可选)" style="width:120px;font-size:13px;" maxlength="10">
          <input id="note-stock" class="form-input" placeholder="名称(可选)" style="width:120px;font-size:13px;" maxlength="30">
          <input id="note-tag" class="form-input" placeholder="标签" style="width:100px;font-size:13px;" maxlength="20">
          <button class="btn btn-primary btn-sm" data-action="note-add" style="margin-left:auto;">记下</button>
        </div>
      </div>`;

    // Tag filter
    if (tags.length > 0) {
      html += '<div style="display:flex;flex-wrap:wrap;gap:8px;">';
      html += `<button class="btn btn-sm btn-ghost note-tag-btn ${!this._tag ? 'active' : ''}" data-tag="" style="font-size:12px;">全部</button>`;
      tags.forEach(t => {
        html += `<button class="btn btn-sm btn-ghost note-tag-btn ${this._tag === t ? 'active' : ''}" data-tag="${ROX.escape(t)}" style="font-size:12px;">${ROX.escape(t)}</button>`;
      });
      html += '</div>';
    }

    // Notes list
    if (notes.length === 0) {
      html += `
        <div class="card" style="padding:48px;text-align:center;color:var(--text-tertiary);">
          <p style="margin:0;">还没有速记</p>
          <p style="font-size:12px;margin:8px 0 0;">在上方输入框写下你的第一条灵感</p>
        </div>`;
    } else {
      notes.forEach(n => {
        const pinned = n.pinned;
        const time = n.created_at ? ROX.fmt.time(n.created_at) : '';
        html += `
        <div class="card note-item ${pinned ? 'note-pinned' : ''}" style="padding:16px 20px;display:flex;gap:12px;align-items:flex-start;${pinned ? 'border-left:3px solid var(--rox-accent);' : ''}">
          <div style="flex:1;min-width:0;">
            <div style="font-size:14px;line-height:1.7;white-space:pre-wrap;word-break:break-word;">${ROX.escape(n.content)}</div>
            <div style="display:flex;flex-wrap:wrap;gap:8px;margin-top:8px;align-items:center;">
              <span style="font-size:11px;color:var(--text-tertiary);font-family:var(--font-mono);">${ROX.escape(time)}</span>
              ${n.code ? `<span style="font-size:11px;color:var(--rox-accent);font-family:var(--font-mono);">${ROX.escape(n.code)}</span>` : ''}
              ${n.stock ? `<span style="font-size:11px;color:var(--text-secondary);">${ROX.escape(n.stock)}</span>` : ''}
              ${n.tag ? `<span style="font-size:11px;padding:2px 8px;border-radius:4px;background:var(--bg-chip);color:var(--text-secondary);">${ROX.escape(n.tag)}</span>` : ''}
              ${n.research_card_id ? `<span style="font-size:11px;color:var(--rox-accent);cursor:pointer;" data-action="note-goto-card" data-id="${n.research_card_id}">→研究卡#${n.research_card_id}</span>` : ''}
            </div>
          </div>
          <div style="display:flex;flex-direction:column;gap:4px;">
            <button class="btn btn-sm btn-ghost" data-action="note-pin" data-id="${n.id}" title="${pinned ? '取消置顶' : '置顶'}" style="padding:4px 6px;">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="${pinned ? 'currentColor' : 'none'}" stroke="currentColor" stroke-width="2"><path d="M12 17v5M9 2h6l-1 7 3 3v2H7v-2l3-3-1-7z"/></svg>
            </button>
            <button class="btn btn-sm btn-ghost" data-action="note-del" data-id="${n.id}" style="padding:4px 6px;color:var(--text-tertiary);">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6"/></svg>
            </button>
          </div>
        </div>`;
      });
    }

    html += '</div>';
    body.innerHTML = html;
    this.bind(body);
  },

  bind(body) {
    // Add
    const addBtn = body.querySelector('[data-action="note-add"]');
    if (addBtn) {
      addBtn.addEventListener('click', async () => {
        const content = document.getElementById('note-input').value.trim();
        if (!content) { ROX.toast('内容不能为空', 'error'); return; }
        const res = await ROX.api.post('/api/notes/', {
          content,
          code: document.getElementById('note-code').value.trim(),
          stock: document.getElementById('note-stock').value.trim(),
          tag: document.getElementById('note-tag').value.trim(),
        });
        if (res && res.id) {
          document.getElementById('note-input').value = '';
          document.getElementById('note-code').value = '';
          document.getElementById('note-stock').value = '';
          document.getElementById('note-tag').value = '';
          ROX.toast('已记下', 'success');
          await this.load();
        }
      });
    }

    // Pin toggle
    body.querySelectorAll('[data-action="note-pin"]').forEach(btn => {
      btn.addEventListener('click', async () => {
        await ROX.api.post(`/api/notes/${btn.dataset.id}/toggle-pin`);
        await this.load();
      });
    });

    // Delete
    body.querySelectorAll('[data-action="note-del"]').forEach(btn => {
      btn.addEventListener('click', async () => {
        await ROX.api.delete(`/api/notes/${btn.dataset.id}`);
        await this.load();
      });
    });

    // Goto research card
    body.querySelectorAll('[data-action="note-goto-card"]').forEach(span => {
      span.addEventListener('click', () => {
        ROX.navigate(`/research?id=${span.dataset.id}`);
      });
    });

    // Tag filter
    body.querySelectorAll('.note-tag-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        this._tag = btn.dataset.tag || '';
        const notes = await ROX.api.get('/api/notes/', this._tag ? { tag: this._tag } : {});
        const tags = await ROX.api.get('/api/notes/tags');
        this.render(body, notes || [], tags || []);
      });
    });
  },
};
