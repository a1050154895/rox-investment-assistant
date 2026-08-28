/* ============================================
   ROX投资助手 — 异动雷达视图
   ATR 基线 + 波动率突破 + 成交量异动 + 新闻反查
   ============================================ */
ROX.register('/anomaly', async function(container) {
  container.innerHTML = `
    <div class="page-header" style="display:flex;justify-content:space-between;align-items:center;margin-bottom:24px;">
      <div>
        <h1 style="font-size:24px;font-weight:590;margin:0;">异动雷达</h1>
        <p style="color:var(--text-secondary);font-size:13px;margin:4px 0 0;">ATR 基线 · 波动率突破 · 成交量异动 · 新闻反查</p>
      </div>
      <button class="btn btn-primary" data-action="anomaly-scan">扫描自选</button>
    </div>
    <div id="anomaly-body">
      <div style="text-align:center;padding:60px 0;color:var(--text-secondary);"><div style="font-size:14px;">点击"扫描自选"开始检测</div></div>
    </div>
  `;
  await ROX.views.anomaly.load();
});

ROX.views = ROX.views || {};
ROX.views.anomaly = {
  async load() {
    const body = document.getElementById('anomaly-body');
    if (!body) return;

    const loggedIn = await ROX.auth.ensure();
    if (!loggedIn) {
      body.innerHTML = '<div class="card" style="padding:48px;text-align:center;color:var(--text-tertiary);"><p>登录后使用异动雷达</p></div>';
      return;
    }
  },

  async scan() {
    const body = document.getElementById('anomaly-body');
    if (!body) return;
    body.innerHTML = '<div style="text-align:center;padding:60px 0;color:var(--text-secondary);"><div class="spinner"></div><p style="margin-top:12px;">正在扫描自选股...</p></div>';

    const data = await ROX.api.get('/api/anomaly/scan');
    if (!data) {
      body.innerHTML = '<div class="empty-state"><p>扫描失败，请检查网络</p></div>';
      return;
    }

    this.render(body, data);
  },

  render(body, data) {
    const anomalies = data.anomalies || [];
    let html = '';

    // Intraday section (loaded on demand)
    html += `
      <div class="card" style="padding:16px 20px;margin-bottom:16px;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
          <span style="font-size:14px;font-weight:590;">盘中监控</span>
          <button class="btn btn-sm btn-secondary" data-action="intraday-scan" style="font-size:11px;">扫描盘中异动</button>
        </div>
        <div style="font-size:11px;color:var(--text-tertiary);margin-bottom:8px;">基于 5 分钟 K 线检测实时波动率和成交量异动</div>
        <div id="intraday-results"></div>
      </div>`;

    // Summary
    html += `
      <div class="card" style="padding:16px 20px;margin-bottom:16px;display:flex;justify-content:space-between;align-items:center;">
        <div style="font-size:13px;color:var(--text-secondary);">
          扫描 ${data.scanned || 0} 只标的 · 发现 ${data.flagged || 0} 项异动
        </div>
        <div style="font-size:11px;color:var(--text-tertiary);font-family:var(--font-mono);">
          ${data.updated_at ? ROX.fmt.time(data.updated_at) : ''}
        </div>
      </div>`;

    if (anomalies.length === 0) {
      html += `
        <div class="card" style="padding:48px;text-align:center;color:var(--text-tertiary);">
          <p style="margin:0;font-size:14px;">自选股中暂无异动</p>
          <p style="font-size:12px;margin:8px 0 0;">异动标准：当日振幅 >= 1.5×ATR 或成交量 >= 1.5×均值</p>
        </div>`;
    } else {
      anomalies.forEach(a => {
        const levelClass = a.anomaly_level === 'high' ? 'high' : a.anomaly_level === 'medium' ? 'medium' : 'low';
        const levelLabel = a.anomaly_level === 'high' ? '高异动' : a.anomaly_level === 'medium' ? '中异动' : '低异动';
        const up = (a.change_pct || 0) >= 0;
        const c = up ? 'var(--rox-up)' : 'var(--rox-down)';
        const types = (a.anomaly_types || []).map(t => {
          if (t === 'volatility_expansion') return '波动率突破';
          if (t === 'volume_spike') return '成交量放大';
          return t;
        }).join(' · ');

        html += `
        <div class="card" style="padding:16px 20px;margin-bottom:12px;">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px;">
            <div style="cursor:pointer;" data-action="anomaly-goto-stock" data-code="${ROX.escape(a.code)}">
              <span style="font-weight:590;font-size:15px;">${ROX.escape(a.name)}</span>
              <span style="font-family:var(--font-mono);font-size:11px;color:var(--text-tertiary);margin-left:6px;">${ROX.escape(a.code)}</span>
            </div>
            <span class="anomaly-strength ${levelClass}">${levelLabel}</span>
          </div>
          <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));gap:12px;margin-bottom:12px;">
            <div>
              <div style="font-size:11px;color:var(--text-tertiary);">现价</div>
              <div style="font-family:var(--font-mono);font-size:15px;color:${c};">${a.price ? ROX.fmt.num(a.price) : '--'}</div>
            </div>
            <div>
              <div style="font-size:11px;color:var(--text-tertiary);">涨跌幅</div>
              <div style="font-family:var(--font-mono);font-size:15px;color:${c};">${a.change_pct != null ? ROX.fmt.pct(a.change_pct) : '--'}</div>
            </div>
            <div>
              <div style="font-size:11px;color:var(--text-tertiary);">振幅/ATR</div>
              <div style="font-family:var(--font-mono);font-size:15px;">${a.range_ratio || 0}×</div>
            </div>
            <div>
              <div style="font-size:11px;color:var(--text-tertiary);">量比</div>
              <div style="font-family:var(--font-mono);font-size:15px;">${a.volume_ratio || 0}×</div>
            </div>
          </div>
          <div style="font-size:12px;color:var(--text-secondary);margin-bottom:8px;">${types}</div>`;

        // News timeline
        if (a.news && a.news.length > 0) {
          html += '<div class="anomaly-timeline" style="margin-top:8px;">';
          a.news.forEach(n => {
            html += `
              <div class="anomaly-event anomaly-news">
                <div style="font-size:12px;color:var(--text-primary);">${ROX.escape(n.title)}</div>
                <div style="font-size:11px;color:var(--text-tertiary);margin-top:2px;">${ROX.escape(n.published_at || '')} · ${ROX.escape(n.source || '')}</div>
              </div>`;
          });
          html += '</div>';
        } else {
          html += '<div style="font-size:11px;color:var(--text-tertiary);margin-top:4px;">该标的近期无关联新闻</div>';
        }

        // Actions
        html += `
          <div style="display:flex;gap:8px;margin-top:12px;">
            <button class="btn btn-sm btn-ghost" data-action="anomaly-goto-stock" data-code="${ROX.escape(a.code)}">查看个股</button>
            <button class="btn btn-sm btn-ghost" data-action="anomaly-create-card" data-code="${ROX.escape(a.code)}" data-name="${ROX.escape(a.name)}">→研究卡</button>
          </div>
        </div>`;
      });
    }

    // Disclaimer
    html += `
      <div style="margin-top:20px;padding:12px 16px;border-radius:8px;background:var(--bg-surface);font-size:11px;color:var(--text-tertiary);line-height:1.6;">
        异动检测基于公开行情数据（振幅、成交量）与 ATR 基线的统计比较，不构成投资建议。新闻关联为标题关键词匹配，不代表因果关系。大单资金流向需 Level-2 商业数据，本功能以成交量/振幅异动作为代理指标。
      </div>`;

    body.innerHTML = html;
    this.bind(body);
  },

  bind(body) {
    body.querySelectorAll('[data-action="anomaly-goto-stock"]').forEach(el => {
      el.addEventListener('click', () => {
        ROX.navigate(`/stock?code=${el.dataset.code}`);
      });
    });

    body.querySelectorAll('[data-action="anomaly-create-card"]').forEach(btn => {
      btn.addEventListener('click', () => {
        ROX.navigate(`/research?new=1&code=${btn.dataset.code}&name=${encodeURIComponent(btn.dataset.name)}`);
      });
    });

    const scanBtn = document.querySelector('[data-action="anomaly-scan"]');
    if (scanBtn && !scanBtn.dataset.bound) {
      scanBtn.dataset.bound = '1';
      scanBtn.addEventListener('click', () => this.scan());
    }

    const intradayBtn = document.querySelector('[data-action="intraday-scan"]');
    if (intradayBtn && !intradayBtn.dataset.bound) {
      intradayBtn.dataset.bound = '1';
      intradayBtn.addEventListener('click', () => this.scanIntraday());
    }
  },

  async scanIntraday() {
    const mount = document.getElementById('intraday-results');
    if (!mount) return;
    mount.innerHTML = '<div style="text-align:center;padding:12px;color:var(--text-tertiary);font-size:12px;">扫描中...</div>';
    const data = await ROX.api.get('/api/anomaly/intraday');
    if (!data || !data.alerts) {
      mount.innerHTML = '<div style="font-size:11px;color:var(--text-tertiary);">扫描失败或不可用</div>';
      return;
    }
    if (data.alerts.length === 0) {
      mount.innerHTML = '<div style="font-size:11px;color:var(--text-tertiary);">自选股中暂无盘中异动</div>';
      return;
    }
    let html = '';
    data.alerts.forEach(a => {
      const types = (a.spike_types || []).map(t => t === 'intraday_range_spike' ? '振幅突破' : t === 'intraday_volume_spike' ? '量能放大' : t).join(' · ');
      const up = (a.change_pct || 0) >= 0;
      const c = up ? 'var(--rox-up)' : 'var(--rox-down)';
      html += `
        <div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-top:1px solid var(--border-color-light);">
          <div style="cursor:pointer;" data-action="anomaly-goto-stock" data-code="${ROX.escape(a.code)}">
            <span style="font-size:13px;font-weight:500;">${ROX.escape(a.name || a.code)}</span>
            <span style="font-size:11px;color:var(--text-tertiary);margin-left:6px;">${types} · 振幅${a.range_ratio || 0}× · 量比${a.volume_ratio || 0}×</span>
            <div style="font-size:10px;color:var(--text-tertiary);margin-top:3px;">${ROX.escape(a.flow_direction_label || '量价方向待观察')} · 最大量 ${ROX.escape(a.max_volume_time || '未知')} · 最大振幅 ${ROX.escape(a.max_range_time || '未知')} · 速度 ${a.velocity_ratio || 0}×</div>
            <div style="font-size:10px;color:var(--text-tertiary);margin-top:3px;">新闻：${a.news_relation === 'matched' ? `已匹配 ${(a.news || []).length} 条` : '未匹配到相关标题'} · 仅作时间线线索</div>
          </div>
          <span style="font-family:var(--font-mono);font-size:12px;color:${c};">${a.price ? ROX.fmt.num(a.price) : '--'} ${a.change_pct != null ? ROX.fmt.pct(a.change_pct) : ''}</span>
        </div>
        ${a.news?.length ? `<div style="padding:6px 0 8px;border-top:1px solid var(--border-color-light);font-size:10px;color:var(--text-secondary);">${a.news.slice(0, 3).map(n => `${ROX.escape(n.published_at || '时间未知')} · ${ROX.escape(n.title)}`).join('<br>')}</div>` : ''}`;
    });
    mount.innerHTML = html;
    this.bind(mount);
  },
};
