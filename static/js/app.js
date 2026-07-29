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
  },

  // API client
  api: {
    async get(url) {
      try {
        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
      } catch (e) {
        console.error('API GET error:', url, e);
        return null;
      }
    },
    async post(url, data) {
      try {
        const res = await fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data),
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
      } catch (e) {
        console.error('API POST error:', url, e);
        return null;
      }
    },
    async put(url, data) {
      try {
        const res = await fetch(url, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data),
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
      } catch (e) {
        console.error('API PUT error:', url, e);
        return null;
      }
    },
    async delete(url) {
      try {
        const res = await fetch(url, { method: 'DELETE' });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
      } catch (e) {
        console.error('API DELETE error:', url, e);
        return null;
      }
    },
  },

  // Utils
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

  // Router
  routes: {},
  register(route, handler) { this.routes[route] = handler; },

  navigate(path) {
    history.pushState(null, '', path);
    this.render(path);
  },

  async render(path) {
    this.state.currentRoute = path;
    const container = document.getElementById('view-container');

    // Determine route handler
    let handler = null;
    let params = {};

    if (path === '/' || path === '') {
      handler = this.routes['/'];
    } else if (path.startsWith('/stock')) {
      handler = this.routes['/stock'];
      const match = path.match(/\/stock\/?(\d+)?/);
      if (match && match[1]) params.code = match[1];
    } else if (path.startsWith('/journal')) {
      handler = this.routes['/journal'];
    } else if (path.startsWith('/framework')) {
      handler = this.routes['/framework'];
    }

    // Update nav active state
    document.querySelectorAll('.nav-item[data-route]').forEach(item => {
      const route = item.dataset.route;
      let isActive = false;
      if (route === '/' && (path === '/' || path === '')) isActive = true;
      else if (route !== '/' && path.startsWith(route)) isActive = true;
      item.classList.toggle('active', isActive);
    });

    // Update page title and search visibility
    const titles = { '/': '仪表盘', '/stock': '个股透视', '/journal': '决策日志', '/framework': '认知框架' };
    let titleKey = '/';
    if (path.startsWith('/stock')) titleKey = '/stock';
    else if (path.startsWith('/journal')) titleKey = '/journal';
    else if (path.startsWith('/framework')) titleKey = '/framework';
    document.getElementById('page-title').textContent = titles[titleKey] || 'ROX投资助手';
    document.getElementById('search-box').style.display = titleKey === '/stock' ? 'block' : 'none';

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
          <h4>会员信息</h4>
          <div class="card" style="margin-bottom:16px;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
              <div>
                <div style="font-size:16px;font-weight:600;color:var(--rox-accent);">${m.plan||'基础版'}</div>
                <div style="font-size:12px;color:var(--text-tertiary);">${m.status==='active'?'已激活':'未激活'}</div>
              </div>
              <span class="tag tag-amber">${m.days_left||0} 天剩余</span>
            </div>
            <div style="display:flex;flex-direction:column;gap:12px;">
              <div>
                <div style="display:flex;justify-content:space-between;font-size:11px;color:var(--text-tertiary);margin-bottom:4px;">
                  <span>API 调用量</span><span>${m.api_used||0} / ${m.api_limit||100}</span>
                </div>
                <div class="progress"><div class="progress-fill blue" style="width:${Math.round((m.api_used||0)/(m.api_limit||100)*100)}%"></div></div>
              </div>
              <div style="display:flex;justify-content:space-between;font-size:11px;color:var(--text-tertiary);">
                <span>已解锁功能</span><span>${m.features_unlocked||0} / ${m.features_total||0} 项</span>
              </div>
            </div>
          </div>
          <h4>套餐选择</h4>
          ${(m.plans||[]).map(p => `
            <div class="card" style="margin-bottom:12px;">
              <div style="display:flex;justify-content:space-between;align-items:center;">
                <div>
                  <div style="font-weight:600;font-size:14px;">${p.name}</div>
                  <div style="font-size:11px;color:var(--text-tertiary);">${p.features.join(' · ')}</div>
                </div>
                <div style="text-align:right;">
                  <div style="font-family:var(--font-mono);font-size:18px;font-weight:700;">¥${p.price}</div>
                  <div style="font-size:11px;color:var(--text-tertiary);">/${p.period}</div>
                </div>
              </div>
            </div>
          `).join('')}
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
          'view-stock': () => {
            const code = actionEl.dataset.code;
            if (code) this.navigate(`/stock/${code}`);
          },
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

    // Browser back/forward
    window.addEventListener('popstate', () => this.render(location.pathname));

    // Load index ticker
    this.loadIndexTicker();

    // Initial render
    this.render(location.pathname);
  },

  async loadIndexTicker() {
    const data = await this.api.get('/api/dashboard/overview');
    if (!data || !data.market_indices) return;
    const ticker = document.getElementById('index-ticker');
    ticker.innerHTML = data.market_indices.map(idx => `
      <div class="index-item">
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
      results.innerHTML = '<div class="search-result-item" style="color:var(--text-tertiary);">无结果</div>';
    } else {
      results.innerHTML = data.results.map(s => `
        <div class="search-result-item" data-action="view-stock" data-code="${s.code}">
          <span style="font-weight:500;">${s.name}</span>
          <span style="font-family:var(--font-mono);font-size:11px;color:var(--text-tertiary);margin-left:8px;">${s.code}</span>
          <span class="tag tag-gray" style="margin-left:4px;">${s.industry}</span>
        </div>
      `).join('');
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
      this.showModal('<div class="modal-header"><span class="modal-title">提示</span></div><p>设置已保存</p><div style="margin-top:16px;text-align:right;"><button class="btn btn-primary" data-action="close-modal">确定</button></div>');
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
