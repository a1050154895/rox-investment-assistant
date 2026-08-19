/* ============================================
   ROX投资助手 — SPA Core
   Router + State + API Client + Utils
   ============================================ */

const ROX = {
  // State
  state: {
    currentRoute: '/',
    currentStock: null,
    settings: null,
    membership: null,
    user: null,
    authMode: 'login',
    refreshTimer: null,
    onboardingSteps: [],
    onboardingStep: 0,
  },

  // API client（自动携带 JWT；非 2xx 返回含 error/status/detail，便于前端提示）
  api: {
    _headers(json = true) {
      const headers = {};
      if (json) headers['Content-Type'] = 'application/json';
      return headers;
    },
    async _request(url, options) {
      try {
        const res = await fetch(url, { credentials: 'same-origin', ...options });
        const data = await res.json().catch(() => null);
        if (!res.ok) return { status: res.status, error: true, ...(data || {}) };
        return data;
      } catch (e) {
        console.error('API error:', url, e);
        return null;
      }
    },
    get(url) { return this._request(url, { headers: this._headers(false) }); },
    post(url, data) { return this._request(url, { method: 'POST', headers: this._headers(), body: JSON.stringify(data) }); },
    put(url, data) { return this._request(url, { method: 'PUT', headers: this._headers(), body: JSON.stringify(data) }); },
    delete(url) { return this._request(url, { method: 'DELETE', headers: this._headers(false) }); },
  },

  // Utils
  escape(value) {
    return String(value ?? '').replace(/[&<>'"]/g, char => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
    }[char]));
  },
  // 功能门控：能力未启用时的诚实占位（与后端 capabilities 对齐）
  disabledState(reason) {
    return `<div class="empty-state" style="padding:48px 16px;text-align:center;">
      <div style="font-size:15px;font-weight:600;margin-bottom:8px;">暂不可用</div>
      <p style="color:var(--text-secondary);font-size:12px;max-width:360px;margin:0 auto;line-height:1.7;">${this.escape(reason || '该功能暂不可用。')}</p>
    </div>`;
  },
  fmt: {
    num(v, dec = 2) { return v != null ? Number(v).toFixed(dec) : '--'; },
    pct(v, dec = 2) { return v != null ? (v > 0 ? '+' : '') + Number(v).toFixed(dec) + '%' : '--'; },
    color(val) { return val > 0 ? 'text-up' : val < 0 ? 'text-down' : ''; },
    date(d) { return d ? new Date(d).toLocaleDateString('zh-CN') : '--'; },
    scoreClass(s) { return s >= 75 ? 'score-high' : s >= 45 ? 'score-medium' : 'score-low'; },
    scoreLabel(s) { return s >= 75 ? '高' : s >= 60 ? '较高' : s >= 45 ? '中等' : '低'; },
    actionTag(a) {
      const map = { '买入': 'tag-red', '卖出': 'tag-green', '持有': 'tag-blue', '减仓': 'tag-amber' };
      return map[a] || 'tag-gray';
    },
    actionColor(a) {
      const map = { '买入': 'text-up', '卖出': 'text-down', '持有': '', '减仓': '' };
      return map[a] || '';
    },
  },

  // Auto-refresh timer management
  startAutoRefresh(callback, interval = 30000) {
    this.stopAutoRefresh();
    this.state.refreshTimer = setInterval(callback, interval);
  },
  stopAutoRefresh() {
    if (this.state.refreshTimer) {
      clearInterval(this.state.refreshTimer);
      this.state.refreshTimer = null;
    }
  },

  // Router — route map (clean, no if-else chain)
  routes: {},
  routePatterns: [
    { match: /^\/?$/,                    handler: '/',           title: '仪表盘' },
    { match: /^\/stock(\/(\d+))?\/?$/,   handler: '/stock',      title: '个股透视', extract: m => ({ code: m[2] }) },
    { match: /^\/journal/,               handler: '/journal',    title: '决策日志' },
    { match: /^\/framework/,             handler: '/framework',  title: '认知框架' },
    { match: /^\/guide/,                 handler: '/guide',      title: '使用教程' },
    { match: /^\/intelligence/,          handler: '/intelligence', title: '宏观情报' },
    { match: /^\/screener/,              handler: '/screener',   title: '选股筛选' },
    { match: /^\/backtest/,              handler: '/backtest',   title: '策略回测' },
    { match: /^\/review/,                handler: '/review',     title: '每日复盘' },
    { match: /^\/portfolio/,             handler: '/portfolio',  title: '持仓组合' },
    { match: /^\/watchlist/,             handler: '/watchlist',  title: '自选股' },
    { match: /^\/alerts/,                handler: '/alerts',     title: '价格预警' },
  ],
  register(route, handler) { this.routes[route] = handler; },

  resolveRoute(path) {
    for (const pattern of this.routePatterns) {
      const m = path.match(pattern.match);
      if (m) {
        const params = pattern.extract ? pattern.extract(m) : {};
        return { handler: pattern.handler, title: pattern.title, params };
      }
    }
    return null;
  },

  navigate(path) {
    history.pushState(null, '', path);
    this.render(path);
  },

  async render(path) {
    this.state.currentRoute = path;
    this.stopAutoRefresh();
    // 清理 ECharts 实例
    if (this._chartInstances) {
      this._chartInstances.forEach(c => { try { c.dispose(); } catch(_) {} });
      this._chartInstances = [];
    }
    const container = document.getElementById('view-container');

    // Resolve route via route map
    const resolved = this.resolveRoute(path);
    const handler = resolved ? this.routes[resolved.handler] : null;
    const params = resolved ? resolved.params : {};

    // Update nav active state
    document.querySelectorAll('.nav-item[data-route]').forEach(item => {
      const route = item.dataset.route;
      let isActive = false;
      if (route === '/' && (path === '/' || path === '')) isActive = true;
      else if (route !== '/' && path.startsWith(route)) isActive = true;
      item.classList.toggle('active', isActive);
    });

    // Update page title and search visibility
    document.getElementById('page-title').textContent = resolved ? resolved.title : 'ROX投资助手';
    document.getElementById('search-box').style.display = (resolved && resolved.handler === '/stock') ? 'block' : 'none';

    // Mobile nav
    this.updateMobileNav(path);

    // Render
    if (handler) {
      container.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
      try {
        await handler(container, params);
      } catch (e) {
        container.innerHTML = `<div class="empty-state"><p>加载失败: ${e.message}</p></div>`;
      }
    } else {
      container.innerHTML = '<div class="empty-state"><p>页面未找到</p></div>';
    }
  },

  updateMobileNav(path) {
    const nav = document.getElementById('mobile-nav');
    const items = [
      { route: '/', label: '仪表盘', icon: '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>' },
      { route: '/stock', label: '个股', icon: '<path d="M3 17l6-6 4 4 8-8"/><path d="M17 7h4v4"/>' },
      { route: '/journal', label: '日志', icon: '<path d="M4 4h16v16H4z"/><path d="M4 9h16"/>' },
      { route: '/framework', label: '框架', icon: '<circle cx="12" cy="12" r="9"/><path d="M12 3v18M3 12h18"/>' },
      { route: '/guide', label: '教程', icon: '<circle cx="12" cy="12" r="9"/><path d="M9.09 9a3 3 0 015.83 1c0 2-3 3-3 3"/><path d="M12 17h.01"/>' },
      { route: '/intelligence', label: '情报', icon: '<path d="M4 5h16v14H4z"/><path d="M7 9h10M7 13h7"/>' },
      { route: '/review', label: '复盘', icon: '<path d="M3 3v18h18"/><path d="M7 14l4-4 3 3 5-6"/><circle cx="19" cy="19" r="2"/>' },
      { route: '/portfolio', label: '持仓', icon: '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M8 12h8M12 8v8"/>' },
      { route: '/watchlist', label: '自选', icon: '<path d="M12 17.27L18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z"/>' },
    ];
    nav.innerHTML = items.map(item => {
      const active = (item.route === '/' && (path === '/' || path === '')) || (item.route !== '/' && path.startsWith(item.route));
      return `<div class="mobile-nav-item ${active ? 'active' : ''}" data-route="${item.route}">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">${item.icon}</svg>
        <span>${item.label}</span>
      </div>`;
    }).join('');
  },

  // Settings panel
  async openSettings() {
    const overlay = document.getElementById('settings-overlay');
    const panel = document.getElementById('settings-panel');
    overlay.classList.add('open');
    panel.classList.add('open');
    await this.renderSettings('ai');
  },

  closeSettings() {
    document.getElementById('settings-overlay').classList.remove('open');
    document.getElementById('settings-panel').classList.remove('open');
  },

  async renderSettings(tab) {
    document.querySelectorAll('.settings-tab').forEach(t => {
      t.classList.toggle('active', t.dataset.settingsTab === tab);
    });
    const body = document.getElementById('settings-body');

    if (!this.state.settings) {
      this.state.settings = await this.api.get('/api/settings/');
    }
    if (!this.state.membership) {
      this.state.membership = await this.api.get('/api/settings/membership');
    }
    const s = this.state.settings || {};
    const m = this.state.membership || {};

    const tabs = {
      ai: `
        <div class="settings-section active">
          <h4>AI 模型配置</h4>
          <div style="display:flex;flex-direction:column;gap:16px;">
            <div class="form-group">
              <label class="form-label">AI 服务商</label>
              <select class="form-select" id="set-ai-provider">
                <option value="deepseek" ${s.ai_provider==='deepseek'?'selected':''}>DeepSeek</option>
                <option value="openai" ${s.ai_provider==='openai'?'selected':''}>OpenAI</option>
                <option value="zhipu" ${s.ai_provider==='zhipu'?'selected':''}>智谱AI</option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">API 地址</label>
              <input class="form-input" id="set-ai-url" value="${s.ai_api_url||''}" placeholder="https://api.deepseek.com">
            </div>
            <div class="form-group">
              <label class="form-label">API Key</label>
              <input class="form-input" type="password" id="set-ai-key" placeholder="输入 API Key">
            </div>
            <div class="form-group">
              <label class="form-label">默认模型</label>
              <input class="form-input" id="set-ai-model" value="${s.ai_model||''}" placeholder="deepseek-chat">
            </div>
            <button class="btn btn-primary" data-action="save-settings">保存配置</button>
          </div>
        </div>`,
      interface: `
        <div class="settings-section active">
          <h4>界面设置</h4>
          <div style="display:flex;flex-direction:column;gap:16px;">
            <div class="form-group">
              <label class="form-label">主题</label>
              <select class="form-select" id="set-theme">
                <option value="dark" ${s.theme==='dark'?'selected':''}>深色</option>
                <option value="light" ${s.theme==='light'?'selected':''}>浅色</option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">紧凑模式</label>
              <select class="form-select" id="set-compact">
                <option value="false" ${!s.compact_mode?'selected':''}>关闭</option>
                <option value="true" ${s.compact_mode?'selected':''}>开启</option>
              </select>
            </div>
            <button class="btn btn-primary" data-action="save-settings">保存</button>
          </div>
        </div>`,
      chart: `
        <div class="settings-section active">
          <h4>图表设置</h4>
          <div style="display:flex;flex-direction:column;gap:16px;">
            <div class="form-group">
              <label class="form-label">K线样式</label>
              <select class="form-select" id="set-chart-style">
                <option value="candlestick" ${s.chart_style==='candlestick'?'selected':''}>蜡烛图</option>
                <option value="bar" ${s.chart_style==='bar'?'selected':''}>柱状图</option>
                <option value="line" ${s.chart_style==='line'?'selected':''}>折线图</option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">默认周期</label>
              <select class="form-select" id="set-period">
                <option value="daily" ${s.default_period==='daily'?'selected':''}>日线</option>
                <option value="weekly" ${s.default_period==='weekly'?'selected':''}>周线</option>
              </select>
            </div>
            <button class="btn btn-primary" data-action="save-settings">保存</button>
          </div>
        </div>`,
      account: `
        <div class="settings-section active">
          <h4>账户</h4>
          <div class="card" style="margin-bottom:16px;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
              <div>
                <div style="font-size:16px;font-weight:600;">${ROX.escape(this.state.user?.username || '未登录')}</div>
                <div style="font-size:12px;color:var(--text-tertiary);">${ROX.escape(m.plan||'基础版')} · ${m.status==='active'?'已激活':'免费版'}</div>
              </div>
              <button class="btn btn-secondary btn-sm" data-action="logout">退出登录</button>
            </div>
            ${m.note ? `<div style="font-size:12px;color:var(--text-tertiary);line-height:1.7;">${ROX.escape(m.note)}</div>` : ''}
          </div>
          <h4>套餐选择</h4>
          ${(m.plans||[]).map(p => `
            <div class="card" style="margin-bottom:12px;">
              <div style="display:flex;justify-content:space-between;align-items:center;">
                <div>
                  <div style="font-weight:600;font-size:14px;">${ROX.escape(p.name)}</div>
                  <div style="font-size:11px;color:var(--text-tertiary);">${ROX.escape(p.features.join(' · '))}</div>
                </div>
                <div style="text-align:right;">
                  <div style="font-family:var(--font-mono);font-size:18px;font-weight:700;">¥${p.price}</div>
                  <div style="font-size:11px;color:var(--text-tertiary);">/${ROX.escape(p.period)}</div>
                </div>
              </div>
            </div>
          `).join('')}
          <div style="font-size:11px;color:var(--text-tertiary);margin-top:8px;">付费套餐接入中，当前为基础版；后续版本开放支付与权益激活。</div>
        </div>`,
    };

    body.innerHTML = tabs[tab] || tabs.ai;
  },

  // Modal
  showModal(html) {
    document.getElementById('modal-content').innerHTML = html;
    document.getElementById('modal-overlay').classList.add('open');
  },
  closeModal() {
    document.getElementById('modal-overlay').classList.remove('open');
  },

  // Toast 通知（替代 alert）
  toast(msg, type = 'info', duration = 3000) {
    let container = document.querySelector('.toast-container');
    if (!container) {
      container = document.createElement('div');
      container.className = 'toast-container';
      document.body.appendChild(container);
    }
    const icons = {
      success: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M20 6L9 17l-5-5"/></svg>',
      error: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><path d="M15 9l-6 6M9 9l6 6"/></svg>',
      warn: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M12 9v4M12 17h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/></svg>',
      info: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/></svg>',
    };
    const el = document.createElement('div');
    el.className = `toast ${type}`;
    el.innerHTML = `<span class="toast-icon">${icons[type] || icons.info}</span><span class="toast-msg">${this.escape(msg)}</span>`;
    container.appendChild(el);
    const remove = () => {
      el.classList.add('hide');
      setTimeout(() => el.remove(), 250);
    };
    el.addEventListener('click', remove);
    setTimeout(remove, duration);
  },

  // Confirm dialog (replaces browser confirm)
  confirm(message, onConfirm, onCancel) {
    this.showModal(`
      <div class="modal-header">
        <span class="modal-title">确认操作</span>
      </div>
      <p style="font-size:14px;color:var(--text-secondary);line-height:1.6;margin:0 0 20px;">${this.escape(message)}</p>
      <div style="display:flex;gap:8px;justify-content:flex-end;">
        <button class="btn btn-secondary" id="confirm-cancel">取消</button>
        <button class="btn btn-primary" id="confirm-ok" style="background:var(--color-down);">确认</button>
      </div>
    `);
    document.getElementById('confirm-ok').addEventListener('click', () => {
      this.closeModal();
      if (onConfirm) onConfirm();
    });
    document.getElementById('confirm-cancel').addEventListener('click', () => {
      this.closeModal();
      if (onCancel) onCancel();
    });
  },

  // ============ Auth ============
  async authCheck() {
    const gate = document.getElementById('auth-gate');
    const res = await this.api.get('/api/auth/me');
    if (res && res.user) {
      this.state.user = res.user;
      if (gate) gate.style.display = 'none';
      this.updateUserChip();
      this.showOnboarding();
    } else {
      this.state.user = null;
      this.showAuthGate();
    }
  },

  showAuthGate() {
    const gate = document.getElementById('auth-gate');
    if (gate) gate.style.display = 'flex';
    this.state.authMode = 'login';
    this.setAuthMode('login');
    // 检查数据库持久化状态，非持久化时显示警告
    this.checkDbStatus();
  },

  async checkDbStatus() {
    try {
      const res = await this.api.get('/health');
      if (res && res.db_persistent === false) {
        const warn = document.getElementById('db-warning');
        if (warn) warn.style.display = 'block';
      }
    } catch (e) { /* 静默 */ }
  },

  setAuthMode(mode) {
    this.state.authMode = mode;
    document.querySelectorAll('[data-auth-tab]').forEach(t =>
      t.classList.toggle('active', t.dataset.authTab === mode));
    const submit = document.getElementById('auth-submit');
    if (submit) submit.textContent = mode === 'login' ? '登录' : '注册并进入';
    this.hideAuthError();
  },

  showAuthError(msg) {
    const el = document.getElementById('auth-error');
    if (el) { el.textContent = msg; el.style.display = 'block'; }
  },
  hideAuthError() {
    const el = document.getElementById('auth-error');
    if (el) el.style.display = 'none';
  },

  async submitAuth() {
    const username = document.getElementById('auth-username')?.value.trim() || '';
    const password = document.getElementById('auth-password')?.value || '';
    if (!username || !password) { this.showAuthError('请输入用户名和密码'); return; }
    if (this.state.authMode === 'register' && password.length < 6) { this.showAuthError('密码至少 6 位'); return; }
    const url = this.state.authMode === 'login' ? '/api/auth/login' : '/api/auth/register';
    const res = await this.api.post(url, { username, password });
    if (res && res.success) {
      this.state.user = res.user;
      this.hideAuthError();
      const gate = document.getElementById('auth-gate');
      if (gate) gate.style.display = 'none';
      this.updateUserChip();
      this.loadIndexTicker();
      this.render(location.pathname);
      this.showOnboarding();
    } else {
      const detail = res?.detail;
      const msg = typeof detail === 'string' ? detail : (this.state.authMode === 'login' ? '登录失败，请检查用户名或密码' : '注册失败，用户名可能已存在');
      this.showAuthError(msg);
    }
  },

  async logout() {
    try { await this.api.post('/api/auth/logout'); } catch (_) { /* 忽略登出接口错误 */ }
    this.state.user = null;
    this.state.settings = null;
    this.state.membership = null;
    localStorage.removeItem('rox-discipline-profile');
    this.showAuthGate();
  },

  updateUserChip() {
    const chip = document.getElementById('user-chip');
    const name = document.getElementById('user-chip-name');
    if (this.state.user) {
      if (chip) chip.style.display = 'inline-flex';
      if (name) name.textContent = this.state.user.username;
    } else if (chip) {
      chip.style.display = 'none';
    }
  },

  // ============ Onboarding ============
  async showOnboarding() {
    if (localStorage.getItem('rox_onboarded') === '1') return;
    const data = await this.api.get('/api/guide/');
    const steps = (data && data.onboarding_steps) || [];
    if (!steps.length) return;
    this.state.onboardingSteps = steps;
    this.state.onboardingStep = 0;
    const overlay = document.getElementById('onboarding-overlay');
    if (overlay) overlay.style.display = 'flex';
    this.renderOnboardingStep();
  },

  renderOnboardingStep() {
    const steps = this.state.onboardingSteps;
    const i = this.state.onboardingStep;
    const s = steps[i];
    const body = document.getElementById('onboarding-body');
    if (!body || !s) return;
    const progress = document.getElementById('onboarding-progress');
    if (progress) progress.textContent = `${i + 1} / ${steps.length}`;
    body.innerHTML = `
      <div class="onboarding-title">${this.escape(s.title)}</div>
      <div class="onboarding-detail">${this.escape(s.detail)}</div>
    `;
    const prev = document.getElementById('onboarding-prev');
    const next = document.getElementById('onboarding-next');
    if (prev) prev.style.visibility = i === 0 ? 'hidden' : 'visible';
    if (next) next.textContent = i === steps.length - 1 ? '开始使用' : '下一步';
  },

  onboardingPrev() {
    if (this.state.onboardingStep > 0) {
      this.state.onboardingStep -= 1;
      this.renderOnboardingStep();
    }
  },

  onboardingNext() {
    const last = this.state.onboardingSteps.length - 1;
    if (this.state.onboardingStep < last) {
      this.state.onboardingStep += 1;
      this.renderOnboardingStep();
    } else {
      this.finishOnboarding();
    }
  },

  finishOnboarding() {
    localStorage.setItem('rox_onboarded', '1');
    const overlay = document.getElementById('onboarding-overlay');
    if (overlay) overlay.style.display = 'none';
  },

  // Init
  init() {
    // Event delegation
    document.addEventListener('click', (e) => {
      // Nav route
      const navItem = e.target.closest('[data-route]');
      if (navItem) {
        e.preventDefault();
        this.navigate(navItem.dataset.route);
        return;
      }

      // Action
      const actionEl = e.target.closest('[data-action]');
      if (actionEl) {
        const action = actionEl.dataset.action;
        const actions = {
          'open-settings': () => this.openSettings(),
          'close-settings': () => this.closeSettings(),
          'close-modal': () => this.closeModal(),
          'save-settings': () => this.saveSettings(),
          'add-decision': () => this.showDecisionForm(),
          'submit-decision': () => this.submitDecision(),
          'cancel-decision': () => this.closeModal(),
          'generate-review': () => this.showReviewReport(),
          'search-stock': () => this.searchStock(),
          'open-discipline': () => this.openDisciplineWorkspace(),
          'save-discipline': () => this.saveDisciplineProfile(),
          'ask-discipline-coach': () => this.askDisciplineCoach(),
          'refresh-intelligence': async () => {
            const button = actionEl;
            button.disabled = true;
            button.textContent = '刷新中…';
            await this.api.get('/api/intelligence/brief?refresh=true');
            this.render('/intelligence');
          },
          'view-stock': () => {
            const code = actionEl.dataset.code;
            if (code) this.navigate(`/stock/${code}`);
          },
          'refresh-review': async () => {
            const button = actionEl;
            button.disabled = true;
            button.textContent = '刷新中…';
            await this.api.get('/api/review/daily?force=true');
            this.render('/review');
          },
          'auth-submit': () => this.submitAuth(),
          'logout': () => this.logout(),
          'onboarding-prev': () => this.onboardingPrev(),
          'onboarding-next': () => this.onboardingNext(),
          'skip-onboarding': () => this.finishOnboarding(),
        };
        actions[action]?.();
        return;
      }

      // Settings tab
      const settingsTab = e.target.closest('[data-settings-tab]');
      if (settingsTab) {
        this.renderSettings(settingsTab.dataset.settingsTab);
        return;
      }

      // Auth tab (login / register)
      const authTab = e.target.closest('[data-auth-tab]');
      if (authTab) {
        this.setAuthMode(authTab.dataset.authTab);
        return;
      }

      // Close modal on overlay click
      if (e.target.id === 'modal-overlay') {
        this.closeModal();
      }
    });

    // Settings tab switch handled above
    // Search input
    let searchTimer;
    document.addEventListener('input', (e) => {
      if (e.target.id === 'stock-search') {
        clearTimeout(searchTimer);
        searchTimer = setTimeout(() => this.searchStocks(e.target.value), 300);
      }
    });

    // Auth form: Enter key submits
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && (e.target.id === 'auth-username' || e.target.id === 'auth-password')) {
        e.preventDefault();
        this.submitAuth();
      }
    });

    // Keyboard shortcuts: number keys 1-9, 0 for quick navigation
    document.addEventListener('keydown', (e) => {
      // Skip if typing in input/textarea/select
      const tag = e.target.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
      // Skip if modal or settings is open
      if (document.getElementById('modal-overlay')?.classList.contains('open')) return;
      if (document.getElementById('settings-panel')?.classList.contains('open')) return;
      if (!this.state.user) return; // not logged in

      const shortcuts = {
        '1': '/', '2': '/stock', '3': '/journal', '4': '/framework',
        '5': '/intelligence', '6': '/screener', '7': '/backtest',
        '8': '/portfolio', '9': '/watchlist', '0': '/alerts',
      };
      if (shortcuts[e.key]) {
        e.preventDefault();
        this.navigate(shortcuts[e.key]);
      }
    });

    // Browser back/forward
    window.addEventListener('popstate', () => this.render(location.pathname));

    // Boot：先登录检查，通过后再加载数据与渲染
    this.boot();
  },

  async boot() {
    await this.authCheck();
    if (!this.state.user) return; // 未登录：登录门禁已显示
    this.updateUserChip();
    this.loadIndexTicker();
    this.render(location.pathname);
    // Show keyboard shortcut hint (once per session)
    if (!sessionStorage.getItem('kbd-hint-shown')) {
      const hint = document.getElementById('kbd-hint');
      if (hint) {
        hint.style.display = 'block';
        setTimeout(() => { hint.style.opacity = '0'; }, 5000);
        sessionStorage.setItem('kbd-hint-shown', '1');
      }
    }
  },

  async loadIndexTicker() {
    const data = await this.api.get('/api/dashboard/overview');
    if (!data || !data.market_indices) return;
    const ticker = document.getElementById('index-ticker');
    if (!ticker) return;
    ticker.innerHTML = data.market_indices.map(idx => `
      <div class="index-item" title="${idx.stale ? `历史快照 · ${idx.as_of || ''}` : '实时数据'}">
        <span class="index-name">${idx.name}</span>
        <span class="index-price">${this.fmt.num(idx.price)}</span>
        <span class="index-change ${this.fmt.color(idx.change_pct)}">${this.fmt.pct(idx.change_pct)}</span>
      </div>
    `).join('');
  },

  async searchStocks(query) {
    if (!query || query.length < 1) {
      document.getElementById('search-results').classList.remove('show');
      return;
    }
    const data = await this.api.get(`/api/stock/search?q=${encodeURIComponent(query)}`);
    if (!data || !data.results) return;
    const results = document.getElementById('search-results');
    if (data.results.length === 0) {
      results.innerHTML = '<div class="search-result-item" style="color:var(--text-tertiary);">无匹配结果（当前支持 A 股全市场）</div>';
    } else {
      results.innerHTML = data.results.map(s => `
        <div class="search-result-item" data-action="view-stock" data-code="${s.code}">
          <span style="font-weight:500;">${s.name}</span>
          <span style="font-family:var(--font-mono);font-size:11px;color:var(--text-tertiary);margin-left:8px;">${s.code}</span>
          ${s.industry ? `<span class="tag tag-gray" style="margin-left:4px;">${s.industry}</span>` : ''}
          <button class="search-star-btn" data-quick-watch="${s.code}" data-quick-name="${this.escape(s.name)}" title="加入自选" style="margin-left:auto;background:none;border:none;color:var(--text-tertiary);cursor:pointer;padding:2px 4px;font-size:14px;line-height:1;">☆</button>
        </div>
      `).join('');
      // Bind quick-watch star buttons
      results.querySelectorAll('[data-quick-watch]').forEach(btn => {
        btn.addEventListener('click', async (e) => {
          e.stopPropagation();
          const code = btn.dataset.quickWatch;
          const name = btn.dataset.quickName;
          const res = await this.api.post('/api/watchlist/', { code, name });
          if (res && res.success && !res.exists) {
            btn.textContent = '★';
            btn.style.color = 'var(--color-up)';
            this.toast(`${name} 已加入自选`, 'success');
          } else if (res && res.success && res.exists) {
            btn.textContent = '★';
            btn.style.color = 'var(--text-tertiary)';
            this.toast(`${name} 已在自选列表中`, 'info');
          } else {
            this.toast('加入失败', 'error');
          }
        });
      });
    }
    results.classList.add('show');
  },

  async saveSettings() {
    const data = {};
    const fields = ['set-ai-provider', 'set-ai-url', 'set-ai-key', 'set-ai-model', 'set-theme', 'set-compact', 'set-chart-style', 'set-period'];
    const map = {
      'set-ai-provider': 'ai_provider', 'set-ai-url': 'ai_api_url', 'set-ai-key': 'ai_api_key',
      'set-ai-model': 'ai_model', 'set-theme': 'theme', 'set-compact': 'compact_mode',
      'set-chart-style': 'chart_style', 'set-period': 'default_period'
    };
    fields.forEach(f => {
      const el = document.getElementById(f);
      if (el) {
        let val = el.value;
        if (f === 'set-compact') val = val === 'true';
        data[map[f]] = val;
      }
    });
    const res = await this.api.put('/api/settings/', data);
    if (res && res.success) {
      this.state.settings = res.settings;
      const keySaved = data.ai_api_key ? '；AI Key 已安全保存（不回显）' : '';
      this.showModal(`<div class="modal-header"><span class="modal-title">提示</span></div><p>设置已保存${keySaved}。</p><div style="margin-top:16px;text-align:right;"><button class="btn btn-primary" data-action="close-modal">确定</button></div>`);
    } else {
      const detail = res?.detail;
      this.showModal(`<div class="modal-header"><span class="modal-title">保存失败</span></div><p>${ROX.escape(typeof detail === 'string' ? detail : '设置保存失败，请重试')}</p><div style="margin-top:16px;text-align:right;"><button class="btn btn-primary" data-action="close-modal">确定</button></div>`);
    }
  },

  // 334 risk-discipline workspace
  async openDisciplineWorkspace() {
    let profile = null;
    // 优先读取服务端档案（跨设备），其次 localStorage，最后默认值
    try {
      const server = await this.api.get('/api/discipline/profile');
      if (server && server.profile) profile = server.profile;
    } catch (_) { /* 忽略 */ }
    if (!profile) {
      try { profile = JSON.parse(localStorage.getItem('rox-discipline-profile')); } catch (_) {}
    }
    if (!profile) {
      const defaults = await this.api.get('/api/discipline/defaults');
      profile = defaults?.profile || {};
    }
    const field = (id, label, value, min = 0, max = 100, step = 1) => `
      <div class="form-group">
        <label class="form-label" for="${id}">${label}</label>
        <input class="form-input" type="number" id="${id}" value="${value ?? 0}" min="${min}" max="${max}" step="${step}">
      </div>`;
    this.showModal(`
      <div class="modal-header">
        <div><div class="modal-title">334 纪律工作台</div><div class="card-subtitle">仓位由可承受风险反推，不由主观信心正推</div></div>
        <button class="modal-close" data-action="close-modal" aria-label="关闭">×</button>
      </div>
      <div class="discipline-form">
        <div class="discipline-form-section">
          <h4>当前资产结构</h4>
          <div class="grid-3">${field('dp-core','核心仓位 %',profile.core_pct)}${field('dp-satellite','卫星仓位 %',profile.satellite_pct)}${field('dp-cash','现金仓位 %',profile.cash_pct)}</div>
        </div>
        <div class="discipline-form-section">
          <h4>风险预算</h4>
          <div class="grid-3">
            ${field('dp-max-total','总仓位上限 %',profile.max_total_position_pct)}
            ${field('dp-risk','单笔风险预算 %',profile.single_trade_risk_pct,0.1,20,0.1)}
            ${field('dp-stop','止损距离 %',profile.stop_loss_pct,0.1,100,0.1)}
            ${field('dp-single-limit','单票上限 %',profile.single_position_limit_pct,0.1,100,0.1)}
            ${field('dp-sector-limit','行业上限 %',profile.sector_limit_pct,0.1,100,0.1)}
            ${field('dp-sector-current','当前行业暴露 %',profile.current_sector_exposure_pct)}
          </div>
        </div>
        <div class="discipline-form-section">
          <h4>本次操作</h4>
          <div class="grid-3">
            ${field('dp-planned','计划单票仓位 %',profile.planned_position_pct)}
            ${field('dp-trades','本月已操作次数',profile.monthly_trades,0,1000,1)}
            ${field('dp-trade-limit','月操作上限',profile.monthly_trade_limit,1,1000,1)}
          </div>
          <div class="form-group" style="margin-top:12px;">
            <label class="form-label" for="dp-rules">我的操作纪律</label>
            <textarea class="form-textarea" id="dp-rules" placeholder="例如：不补亏损仓；加仓必须有订单、业绩或量价中的两项新证据。">${this.escape(profile.operating_rules || '')}</textarea>
          </div>
        </div>
        <div id="discipline-result" aria-live="polite"></div>
        <div class="discipline-coach">
          <div class="card-title">研究助手</div>
          <div class="card-subtitle">助手只解释风险与纪律冲突，不替你预测涨跌或覆盖硬规则。</div>
          <div class="coach-input-row">
            <input class="form-input" id="discipline-question" placeholder="例如：为什么我的计划仓位超限？">
            <button class="btn btn-secondary" data-action="ask-discipline-coach">提问</button>
          </div>
          <div id="discipline-coach-answer" class="coach-answer">先保存评估，再根据结果提问。</div>
        </div>
        <div class="modal-actions">
          <button class="btn btn-secondary" data-action="close-modal">关闭</button>
          <button class="btn btn-primary" data-action="save-discipline">保存并评估</button>
        </div>
      </div>`);
  },

  disciplineProfileFromForm() {
    const number = id => Number(document.getElementById(id)?.value || 0);
    return {
      core_pct: number('dp-core'), satellite_pct: number('dp-satellite'), cash_pct: number('dp-cash'),
      max_total_position_pct: number('dp-max-total'), single_trade_risk_pct: number('dp-risk'),
      stop_loss_pct: number('dp-stop'), single_position_limit_pct: number('dp-single-limit'),
      sector_limit_pct: number('dp-sector-limit'), current_sector_exposure_pct: number('dp-sector-current'),
      planned_position_pct: number('dp-planned'), monthly_trades: number('dp-trades'),
      monthly_trade_limit: number('dp-trade-limit'), operating_rules: document.getElementById('dp-rules')?.value || ''
    };
  },

  async saveDisciplineProfile() {
    const profile = this.disciplineProfileFromForm();
    const result = await this.api.post('/api/discipline/evaluate', profile);
    const box = document.getElementById('discipline-result');
    if (!result?.assessment) {
      if (box) box.innerHTML = '<div class="discipline-alert danger">参数校验失败，请确认三类仓位不超过 100%，且风险参数大于 0。</div>';
      return;
    }
    localStorage.setItem('rox-discipline-profile', JSON.stringify(profile));
    // 同步到服务端（账号级持久化，跨设备可用）；失败不阻断本地评估展示
    try { await this.api.put('/api/discipline/profile', profile); } catch (_) { /* 忽略 */ }
    this.state.disciplineAssessment = result.assessment;
    if (box) box.innerHTML = this.renderDisciplineAssessment(result.assessment);
    const coach = document.getElementById('discipline-coach-answer');
    if (coach) coach.textContent = result.assessment.guidance;
  },

  renderDisciplineAssessment(assessment) {
    return `<div class="discipline-assessment">
      <div class="discipline-summary"><div><strong>${assessment.status_label}</strong><p>${assessment.guidance}</p></div><span class="tag ${assessment.status === 'blocked' ? 'tag-red' : 'tag-green'}">${assessment.status === 'blocked' ? '需修正' : '已检查'}</span></div>
      <div class="discipline-limit">风险仓位上限 <strong>${assessment.limits.allowed_position_pct}%</strong><span>${assessment.method}</span></div>
      <div class="discipline-checks">${assessment.checks.map(item => `<div class="discipline-check ${item.passed ? 'passed' : 'failed'}"><span>${item.passed ? '通过' : '冲突'}</span><div><strong>${item.title}</strong><p>${item.detail}</p></div></div>`).join('')}</div>
    </div>`;
  },

  async askDisciplineCoach() {
    const question = document.getElementById('discipline-question')?.value.trim();
    const answer = document.getElementById('discipline-coach-answer');
    if (!answer) return;
    if (!question) { answer.textContent = '请输入你要咨询的问题，例如：为什么我的计划仓位超限？'; return; }
    const assessment = this.state.disciplineAssessment;
    // 把确定性评估结果作为上下文交给 AI（AI 只解释纪律与风险，不覆盖硬规则）
    const context = assessment ? JSON.stringify({
      status: assessment.status,
      checks: (assessment.checks || []).map(c => ({ title: c.title, passed: c.passed, detail: c.detail })),
      limits: assessment.limits,
      guidance: assessment.guidance,
    }) : null;
    answer.textContent = '';

    try {
      const resp = await fetch('/api/ai/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, context }),
      });
      if (!resp.ok) {
        answer.textContent = resp.status === 503 ? 'AI 服务未配置，请在设置中填写 API Key。'
          : resp.status === 401 ? '请先登录以使用 AI 助手。'
          : 'AI 服务调用失败。';
        return;
      }
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const text = decoder.decode(value, { stream: true });
        for (const line of text.split('\n')) {
          const content = line.startsWith('data: ') ? line.slice(6) : '';
          if (content && content !== '[DONE]' && !content.startsWith('{')) {
            answer.textContent += content;
          }
        }
      }
    } catch (e) {
      answer.textContent = '网络异常，请稍后重试。';
    }
  },

  // Decision form
  showDecisionForm(stockCode, stockName) {
    const html = `
      <div class="modal-header">
        <span class="modal-title">记录决策</span>
        <div class="modal-close" data-action="cancel-decision"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6L6 18M6 6l12 12"/></svg></div>
      </div>
      <div style="display:flex;flex-direction:column;gap:16px;">
        <div class="grid-2">
          <div class="form-group">
            <label class="form-label">股票名称</label>
            <input class="form-input" id="dec-stock" value="${stockName||''}" placeholder="如：贵州茅台">
          </div>
          <div class="form-group">
            <label class="form-label">股票代码</label>
            <input class="form-input" id="dec-code" value="${stockCode||''}" placeholder="如：600519">
          </div>
        </div>
        <div class="grid-2">
          <div class="form-group">
            <label class="form-label">操作类型</label>
            <select class="form-select" id="dec-action">
              <option value="买入">买入</option>
              <option value="卖出">卖出</option>
              <option value="持有">持有</option>
              <option value="减仓">减仓</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">334 阶段</label>
            <select class="form-select" id="dec-stage">
              <option value="试仓30%">试仓 30%</option>
              <option value="确认30%">确认 30%</option>
              <option value="主力40%">主力 40%</option>
            </select>
          </div>
        </div>
        <div class="grid-3">
          <div class="form-group">
            <label class="form-label">矛盾强度 (0-100)</label>
            <input class="form-input" type="number" id="dec-contradiction" value="50" min="0" max="100">
          </div>
          <div class="form-group">
            <label class="form-label">价值实现度 (0-100)</label>
            <input class="form-input" type="number" id="dec-value" value="50" min="0" max="100">
          </div>
          <div class="form-group">
            <label class="form-label">一致性评分 (0-100)</label>
            <input class="form-input" type="number" id="dec-score" value="50" min="0" max="100">
          </div>
        </div>
        <div class="form-group">
          <label class="form-label">决策理由</label>
          <textarea class="form-textarea" id="dec-reason" placeholder="阐述本次决策的框架依据..."></textarea>
        </div>
        <div style="display:flex;gap:8px;justify-content:flex-end;">
          <button class="btn btn-secondary" data-action="cancel-decision">取消</button>
          <button class="btn btn-primary" data-action="submit-decision">提交</button>
        </div>
      </div>`;
    this.showModal(html);
  },

  async submitDecision() {
    const data = {
      stock: document.getElementById('dec-stock').value,
      code: document.getElementById('dec-code').value,
      action: document.getElementById('dec-action').value,
      stage: document.getElementById('dec-stage').value,
      cycle_stage: '流转',
      contradiction_intensity: parseInt(document.getElementById('dec-contradiction').value),
      value_realization: parseInt(document.getElementById('dec-value').value),
      consistency_score: parseInt(document.getElementById('dec-score').value),
      reason: document.getElementById('dec-reason').value,
    };
    const res = await this.api.post('/api/journal/', data);
    if (res && res.success) {
      this.closeModal();
      this.navigate('/journal');
    }
  },

  async showReviewReport() {
    const res = await this.api.post('/api/journal/review?start_date=2026-07-01&end_date=2026-07-31');
    if (!res) return;
    const html = `
      <div class="modal-header">
        <span class="modal-title">复盘报告 — ${res.period}</span>
        <div class="modal-close" data-action="close-modal"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6L6 18M6 6l12 12"/></svg></div>
      </div>
      <div style="display:flex;flex-direction:column;gap:16px;">
        <div class="grid-4">
          <div class="stat-item"><span class="stat-label">决策总数</span><span class="stat-value">${res.total_decisions}</span></div>
          <div class="stat-item"><span class="stat-label">盈利</span><span class="stat-value" style="color:var(--rox-up);">${res.wins}</span></div>
          <div class="stat-item"><span class="stat-label">亏损</span><span class="stat-value" style="color:var(--rox-down);">${res.losses}</span></div>
          <div class="stat-item"><span class="stat-label">总收益</span><span class="stat-value ${res.total_return>=0?'text-up':'text-down'}">${res.total_return>=0?'+':''}${res.total_return}%</span></div>
        </div>
        <div class="card">
          <div class="card-title" style="margin-bottom:12px;">按周期阶段统计</div>
          ${Object.entries(res.stage_breakdown||{}).map(([stage, s]) => `
            <div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid var(--border-default);">
              <span style="font-size:13px;">${stage}</span>
              <div style="display:flex;gap:16px;font-size:12px;">
                <span style="color:var(--text-tertiary);">决策 ${s.count} 次</span>
                <span style="color:var(--text-tertiary);">胜率 ${s.win_rate}%</span>
                <span class="score-badge ${ROX.fmt.scoreClass(s.avg_score)}">${s.avg_score}</span>
              </div>
            </div>
          `).join('')}
        </div>
        <div class="card">
          <div class="card-title" style="margin-bottom:12px;">洞察</div>
          <ul style="list-style:disc;padding-left:20px;font-size:13px;color:var(--text-secondary);line-height:1.8;">
            ${(res.insights||[]).map(i => `<li>${i}</li>`).join('')}
          </ul>
        </div>
        <div class="card">
          <div class="card-title" style="margin-bottom:12px;">建议</div>
          <ul style="list-style:disc;padding-left:20px;font-size:13px;color:var(--text-secondary);line-height:1.8;">
            ${(res.suggestions||[]).map(i => `<li>${i}</li>`).join('')}
          </ul>
        </div>
      </div>`;
    this.showModal(html);
  },
};

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => ROX.init());
