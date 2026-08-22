/* ============================================
   证据抽屉 Evidence Drawer
   情报/个股/ETF/宏观 → 加入研究卡为事实/反证/待验证
   ============================================ */

ROX.EvidenceDrawer = {
  payload: null,

  open(payload) {
    if (!this._mounted) this._mount();
    this.payload = payload || {};
    document.getElementById('evidence-overlay').classList.add('open');
    document.getElementById('evidence-drawer').classList.add('open');
    this.renderForm();
  },

  close() {
    document.getElementById('evidence-overlay')?.classList.remove('open');
    document.getElementById('evidence-drawer')?.classList.remove('open');
  },

  _mount() {
    this._mounted = true;
    const overlay = document.createElement('div');
    overlay.id = 'evidence-overlay';
    overlay.className = 'evidence-overlay';
    overlay.addEventListener('click', () => this.close());
    const drawer = document.createElement('div');
    drawer.id = 'evidence-drawer';
    drawer.className = 'evidence-drawer';
    drawer.setAttribute('role', 'dialog');
    drawer.setAttribute('aria-label', '证据抽屉');
    document.body.append(overlay, drawer);
  },

  async renderForm() {
    const body = document.getElementById('evidence-drawer');
    const p = this.payload;
    body.innerHTML = `
      <div class="evidence-drawer-head">
        <div>
          <div class="evidence-drawer-title">加入研究卡</div>
          <div class="evidence-drawer-sub">来源 · 时间 · 数据状态随证据一起保存，不脱离上下文</div>
        </div>
        <button class="modal-close" data-action="close-evidence-drawer" aria-label="关闭">×</button>
      </div>
      <div class="evidence-drawer-body">
        <div class="form-group">
          <label class="form-label" for="ev-content">证据内容</label>
          <textarea class="form-textarea" id="ev-content" rows="4">${ROX.escape(p.content || '')}</textarea>
        </div>
        <div class="grid-2">
          <div class="form-group">
            <label class="form-label" for="ev-source">来源</label>
            <input class="form-input" id="ev-source" value="${ROX.escape(p.source || '')}" placeholder="如：腾讯实时行情">
          </div>
          <div class="form-group">
            <label class="form-label" for="ev-as-of">截至时间</label>
            <input class="form-input" id="ev-as-of" value="${ROX.escape(p.asOf || '')}" placeholder="数据时间">
          </div>
        </div>
        <div class="form-group">
          <label class="form-label" for="ev-type">证据类型</label>
          <select class="form-select" id="ev-type">
            <option value="fact">事实</option>
            <option value="counter">反证</option>
            <option value="to_verify">待验证</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label" for="ev-target">目标研究卡</label>
          <select class="form-select" id="ev-target"><option value="new">＋ 新建研究卡</option></select>
          <div id="ev-cards-loading" style="font-size:11px;color:var(--text-tertiary);margin-top:4px;">正在加载研究卡…</div>
        </div>
        <div class="evidence-drawer-note">AI 与资讯只是线索，进入研究卡的事实需可追溯、可复核。</div>
      </div>
      <div class="evidence-drawer-foot">
        <button class="btn btn-secondary" data-action="close-evidence-drawer">取消</button>
        <button class="btn btn-primary" data-action="submit-evidence">加入研究卡</button>
      </div>`;

    const data = await ROX.api.get('/api/research/?status=');
    const select = document.getElementById('ev-target');
    const loading = document.getElementById('ev-cards-loading');
    if (data && !data.error && data.cards?.length) {
      data.cards.forEach(card => {
        const opt = document.createElement('option');
        opt.value = card.id;
        opt.textContent = `#${card.id} ${card.title}`;
        select.appendChild(opt);
      });
      if (loading) loading.textContent = '';
    } else if (loading) {
      loading.textContent = data && data.error ? '研究卡加载失败' : '暂无研究卡，将直接新建';
    }
  },

  async submit() {
    const content = document.getElementById('ev-content')?.value.trim();
    const source = document.getElementById('ev-source')?.value.trim() || '';
    const asOf = document.getElementById('ev-as-of')?.value.trim() || '';
    const type = document.getElementById('ev-type')?.value || 'fact';
    const target = document.getElementById('ev-target')?.value || 'new';
    if (!content) { ROX.toast('请填写证据内容', 'warn'); return; }

    const meta = [source, asOf].filter(Boolean).join(' · ');
    const entry = meta ? `${content}（来源：${meta}）` : content;
    let res;
    if (target === 'new') {
      const p = this.payload;
      const prefix = type === 'counter' ? '[反证] ' : type === 'to_verify' ? '[待验证] ' : '[事实] ';
      res = await ROX.api.post('/api/research/', {
        title: (p.title || content).slice(0, 120),
        code: p.code || '',
        stock: p.stock || '',
        question: type === 'to_verify' ? content : '',
        facts: type === 'counter' ? [] : [prefix + entry],
        counter_evidence: type === 'counter' ? prefix + entry : '',
      });
    } else {
      res = await ROX.api.post(`/api/research/${target}/evidence`, {
        evidence_type: type, content, source, as_of: asOf,
      });
    }
    if (res && res.success) {
      this.close();
      ROX.toast(target === 'new' ? '已新建研究卡并写入证据' : '证据已加入研究卡', 'success');
    } else {
      ROX.toast(typeof res?.detail === 'string' ? res.detail : '提交失败，请重试', 'error');
    }
  },
};
