/* ============================================
   视图2 · 个股透视
   ============================================ */

let _klineChart = null;
let _flowChart = null;
let _klineSeries = null;
let _stockDecisions = [];
window.addEventListener('resize', () => {
  if (_klineChart && typeof _klineChart.resize === 'function') {
    const el = document.getElementById('kline-chart');
    if (el && window.LightweightCharts && _klineChart.resize.length >= 2) _klineChart.resize(el.clientWidth, el.clientHeight);
    else _klineChart.resize();
  }
  _flowChart?.resize();
});

ROX.register('/stock', async function(container, params) {
  const code = params.code || '600519';

  // Load data in parallel
  const [info, analysis, kline, indicators, fundamentals] = await Promise.all([
    ROX.api.get(`/api/stock/${code}`),
    ROX.api.get(`/api/stock/${code}/analysis`),
    ROX.api.get(`/api/stock/${code}/kline`),
    ROX.api.get(`/api/stock/${code}/indicators`),
    ROX.api.get(`/api/fundamentals/${code}`),
  ]);

  if (!info || info.error) {
    container.innerHTML = '<div class="empty-state"><p>未找到该股票</p></div>';
    return;
  }

  ROX.state.currentStock = code;

  container.innerHTML = `
    <div class="stock-detail-layout stock-page">
      <!-- Left: K-Line -->
      <div class="stock-main-column">
        <!-- Stock header -->
        <div class="card stock-hero stock-summary-card">
          <div class="stock-hero-row">
            <div class="stock-identity">
              <h2 style="font-size:18px;font-weight:600;">${info.name}</h2>
              <span style="font-family:var(--font-mono);font-size:12px;color:var(--text-tertiary);">${info.code}</span>
              <span class="tag tag-gray">${info.industry}</span>
              <span class="evidence-badge ${info.stale ? 'is-stale' : 'is-live'}"><i></i>${info.stale ? `快照 · ${info.as_of || ''}` : `实时 · ${info.as_of || ''}`}</span>
            </div>
            <div class="stock-hero-actions stock-action-bar">
              <div class="stock-live-price">
                <span style="font-family:var(--font-mono);font-size:20px;font-weight:700;color:${info.change_pct>=0?'var(--rox-up)':'var(--rox-down)'};">${ROX.fmt.num(info.price)}</span>
                <span style="font-family:var(--font-mono);font-size:13px;color:${info.change_pct>=0?'var(--rox-up)':'var(--rox-down)'};">${ROX.fmt.pct(info.change_pct)}</span>
              </div>
              <div class="stock-period-actions stock-chart-periods">
                <button class="btn btn-secondary btn-sm" data-period="daily" id="btn-daily">日线</button>
                <button class="btn btn-secondary btn-sm" data-period="weekly" id="btn-weekly">周线</button>
              </div>
              <button class="btn btn-secondary btn-sm" id="btn-add-watch" data-code="${info.code}" data-name="${ROX.escape(info.name)}">+ 自选</button>
              <button class="btn btn-primary btn-sm" data-action="create-research-card" data-code="${info.code}" data-name="${ROX.escape(info.name)}" data-price="${info.price ?? ''}" data-data-status="${ROX.escape(info.data_status || '')}" data-data-source="${ROX.escape(info.data_source || '')}" data-as-of="${ROX.escape(info.as_of || '')}">开始研究</button>
              <button class="btn btn-secondary btn-sm" data-action="open-evidence-drawer" data-title="${ROX.escape(info.name)}" data-content="${ROX.escape(`行情：${info.name} ${ROX.fmt.num(info.price)}（${ROX.fmt.pct(info.change_pct)}）`)}" data-source="${ROX.escape(info.data_source || '')}" data-as-of="${ROX.escape(info.as_of || '')}" data-code="${info.code}" data-stock="${ROX.escape(info.name)}">存为证据</button>
              <button class="btn btn-secondary btn-sm" data-action="add-decision" data-code="${info.code}" data-name="${ROX.escape(info.name)}">记录决策</button>
              <button class="btn btn-secondary btn-sm" id="btn-add-alert" data-code="${info.code}" data-name="${ROX.escape(info.name)}">+ 预警</button>
            </div>
          </div>
          <div class="stock-metrics">
            <span>PE <span style="color:var(--text-secondary);font-family:var(--font-mono);">${ROX.fmt.num(info.pe,1)}</span></span>
            <span>PB <span style="color:var(--text-secondary);font-family:var(--font-mono);">${ROX.fmt.num(info.pb)}</span></span>
            <span>ROE <span style="color:var(--text-secondary);font-family:var(--font-mono);">${ROX.fmt.num(info.roe,1)}%</span></span>
            <span>市值 <span style="color:var(--text-secondary);">${info.market_cap}</span></span>
            <span>换手 <span style="color:var(--text-secondary);font-family:var(--font-mono);">${ROX.fmt.num(info.turnover)}%</span></span>
          </div>
        </div>

        <!-- K-Line Chart -->
        <div class="card stock-chart-card" style="flex:1;padding:12px;overflow:hidden;">
          ${kline?.data_status === 'unavailable' ? `<div class="empty-state"><p>${kline.message || 'K线数据暂不可用'}</p></div>` : `<div id="kline-chart" class="chart-container"></div>`}
        </div>
        <div class="card" id="stock-research-links" style="padding:12px;"><div class="loading"><div class="spinner"></div></div></div>

        <!-- Fund Flow -->
        <div class="card stock-flow-card" style="padding:12px;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
            <span style="font-size:12px;font-weight:500;">主力资金流向</span>
            <span style="font-family:var(--font-mono);font-size:13px;color:${analysis?.fund_flow?.main_inflow != null && analysis.fund_flow.main_inflow>=0?'var(--rox-up)':'var(--rox-down)'};">${analysis?.fund_flow?.main_inflow == null ? '数据不可用' : `${analysis.fund_flow.main_inflow>=0?'+':''}${ROX.fmt.num(analysis.fund_flow.main_inflow)} 亿`}</span>
          </div>
          <div id="flow-chart"></div>
        </div>
      </div>

      <!-- Right: Framework Panel -->
      <aside class="stock-framework-panel stock-analysis-column">
        ${analysis ? `
          <!-- Consistency Score -->
          <div class="card">
            <div class="card-header">
              <div class="card-title">框架一致性评分</div>
              <span class="score-badge ${analysis.consistency_score == null ? 'score-low' : ROX.fmt.scoreClass(analysis.consistency_score)}" style="font-size:16px;min-width:48px;height:28px;">${analysis.consistency_score ?? '--'}</span>
            </div>
            <div style="font-size:11px;color:var(--text-tertiary);margin-bottom:12px;">总体评价：${analysis.score_label}</div>
            ${Object.entries(analysis.dimensions).map(([key, dim]) => `
              <div style="margin-bottom:10px;">
                <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
                  <span style="font-size:11px;color:var(--text-secondary);">${dim.label} <span style="color:var(--text-muted);">(${dim.weight}%)</span></span>
                  <span style="font-size:11px;font-family:var(--font-mono);color:var(--text-secondary);">${dim.score ?? '--'}</span>
                </div>
                ${dim.score != null ? `<div class="progress"><div class="progress-fill ${dim.score>=70?'green':dim.score>=45?'amber':'red'}" style="width:${dim.score}%"></div></div>` : ''}
                <div style="font-size:10px;color:var(--text-muted);margin-top:3px;">${dim.detail}</div>
              </div>
            `).join('')}
          </div>

          <!-- Contradictions -->
          <div class="card">
            <div class="card-header"><div class="card-title">矛盾分析</div><span class="tag tag-amber">待验证</span></div>
            <div style="font-size:11px;color:var(--text-secondary);line-height:1.7;">当前没有足够的真实量价、政策与行业数据计算矛盾强度，系统不会生成随机结论。</div>
          </div>

          <!-- Value Assessment -->
          <div class="card">
            <div class="card-header"><div class="card-title">价值规律评估</div></div>
            <div class="grid-2" style="gap:8px;">
              <div><div style="font-size:10px;color:var(--text-tertiary);">PE</div><div style="font-family:var(--font-mono);font-size:14px;font-weight:500;">${ROX.fmt.num(analysis.value_assessment.pe,1)}</div></div>
              <div><div style="font-size:10px;color:var(--text-tertiary);">PB</div><div style="font-family:var(--font-mono);font-size:14px;font-weight:500;">${ROX.fmt.num(analysis.value_assessment.pb,2)}</div></div>
              <div><div style="font-size:10px;color:var(--text-tertiary);">ROE代理</div><div style="font-family:var(--font-mono);font-size:14px;font-weight:500;">${analysis.value_assessment.roe_proxy == null ? '--' : ROX.fmt.num(analysis.value_assessment.roe_proxy,1)+'%'}</div></div>
              <div><div style="font-size:10px;color:var(--text-tertiary);">结论</div><div style="font-size:12px;font-weight:500;">${analysis.value_assessment.value_grade}</div></div>
            </div>
          </div>

          <!-- Indicators -->
          ${indicators && indicators.data_status !== 'unavailable' ? `
          <div class="card">
            <div class="card-header"><div class="card-title">技术指标</div></div>
            <div class="grid-2" style="gap:8px;">
              <div><div style="font-size:10px;color:var(--text-tertiary);">RSI(14)</div><div style="font-family:var(--font-mono);font-size:13px;">${ROX.fmt.num(indicators.rsi,1)}</div></div>
              <div><div style="font-size:10px;color:var(--text-tertiary);">KDJ(J)</div><div style="font-family:var(--font-mono);font-size:13px;">${ROX.fmt.num(indicators.kdj_j,1)}</div></div>
              <div><div style="font-size:10px;color:var(--text-tertiary);">MACD</div><div style="font-family:var(--font-mono);font-size:13px;color:${indicators.macd>=0?'var(--rox-up)':'var(--rox-down)'};">${ROX.fmt.num(indicators.macd,3)}</div></div>
              <div><div style="font-size:10px;color:var(--text-tertiary);">MA20</div><div style="font-family:var(--font-mono);font-size:13px;">${ROX.fmt.num(indicators.ma20)}</div></div>
            </div>
          </div>
          ` : ''}

          <!--   Fundamentals  -->
          ${fundamentals && fundamentals.summary && fundamentals.summary.length ? `
          <div class="card">
            <div class="card-header"><div class="card-title">基本面</div></div>
            <div style="font-size:11px;color:var(--text-secondary);margin-bottom:10px;line-height:1.6;">${ROX.escape(fundamentals.notes || '')}</div>
            <div class="grid-2" style="gap:8px;margin-bottom:10px;">
              ${fundamentals.valuation?.pe_ttm != null ? `<div><div style="font-size:10px;color:var(--text-tertiary);">PE(TTM)</div><div style="font-family:var(--font-mono);font-size:13px;">${ROX.fmt.num(fundamentals.valuation.pe_ttm,1)}</div></div>` : ''}
              ${fundamentals.valuation?.pb != null ? `<div><div style="font-size:10px;color:var(--text-tertiary);">PB</div><div style="font-family:var(--font-mono);font-size:13px;">${ROX.fmt.num(fundamentals.valuation.pb,2)}</div></div>` : ''}
              ${fundamentals.valuation?.market_cap != null ? `<div><div style="font-size:10px;color:var(--text-tertiary);">市值(亿)</div><div style="font-family:var(--font-mono);font-size:13px;">${ROX.fmt.num(fundamentals.valuation.market_cap)}</div></div>` : ''}
              ${fundamentals.quality?.score != null ? `<div><div style="font-size:10px;color:var(--text-tertiary);">财务质量</div><div style="font-family:var(--font-mono);font-size:13px;color:${fundamentals.quality.score>=65?'var(--rox-up)':fundamentals.quality.score>=45?'var(--text-secondary)':'var(--rox-down)'};">${fundamentals.quality.score}分 ${ROX.escape(fundamentals.quality.label)}</div></div>` : ''}
            </div>
            ${fundamentals.summary ? `
            <div style="overflow-x:auto;">
              <table style="width:100%;border-collapse:collapse;font-size:10px;">
                <thead><tr style="border-bottom:1px solid var(--border-color);">
                  <th style="text-align:left;padding:2px 4px;color:var(--text-tertiary);">报告期</th>
                  <th style="text-align:right;padding:2px 4px;color:var(--text-tertiary);">营收(亿)</th>
                  <th style="text-align:right;padding:2px 4px;color:var(--text-tertiary);">净利(亿)</th>
                  <th style="text-align:right;padding:2px 4px;color:var(--text-tertiary);">ROE%</th>
                </tr></thead>
                <tbody>
                  ${fundamentals.summary.slice(-5).map(r => `
                    <tr style="border-bottom:1px solid var(--border-color-light);">
                      <td style="padding:2px 4px;">${(r.period||'').slice(0,4)}</td>
                      <td style="text-align:right;padding:2px 4px;font-family:var(--font-mono);">${r.revenue!=null?(r.revenue/1e8).toFixed(1):'--'}</td>
                      <td style="text-align:right;padding:2px 4px;font-family:var(--font-mono);">${r.net_profit!=null?(r.net_profit/1e8).toFixed(1):'--'}</td>
                      <td style="text-align:right;padding:2px 4px;font-family:var(--font-mono);">${r.roe!=null?r.roe.toFixed(1):'--'}</td>
                    </tr>
                  `).join('')}
                </tbody>
              </table>
            </div>
            ` : ''}
          </div>
          <div id="valuation-panel" style="margin-top:12px;padding-top:10px;border-top:1px solid var(--border-color);font-size:12px;color:var(--text-tertiary);">估值加载中...</div>
          ` : fundamentals?.summary && fundamentals.summary.length === 0 ? `<div class="card"><p style="color:var(--text-tertiary);font-size:12px;">基本面数据暂不可用</p></div>` : ''}
        ` : '<div class="card"><p style="color:var(--text-tertiary);font-size:12px;">分析数据加载中...</p></div>'}
      </aside>
    </div>
  `;

  // Render charts
  if (kline?.candles?.length) {
    renderKline(kline.candles, info, _stockDecisions);
  }
  loadRelatedResearch(code, document.getElementById('stock-research-links')).then(data => {
    _stockDecisions = data?.decisions || [];
    if (kline?.candles?.length) renderKline(kline.candles, info, _stockDecisions);
  });

  // Period switch
  document.getElementById('btn-daily')?.addEventListener('click', async () => {
    const data = await ROX.api.get(`/api/stock/${code}/kline?period=daily`);
    if (data?.candles?.length) renderKline(data.candles, info, _stockDecisions);
  });
  document.getElementById('btn-weekly')?.addEventListener('click', async () => {
    const data = await ROX.api.get(`/api/stock/${code}/kline?period=weekly`);
    if (data?.candles?.length) renderKline(data.candles, info, _stockDecisions);
  });

  // Price alert — custom modal form (replaces prompt + confirm)
  document.getElementById('btn-add-alert')?.addEventListener('click', async () => {
    const btn = document.getElementById('btn-add-alert');
    const code = btn.dataset.code;
    const name = decodeURIComponent(btn.dataset.name || code);
    const currentPrice = ROX.fmt.num(info.price);
    ROX.showModal(`
      <div class="modal-header">
        <span class="modal-title">设置价格预警 — ${ROX.escape(name)}</span>
        <div class="modal-close" data-action="close-modal"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6L6 18M6 6l12 12"/></svg></div>
      </div>
      <div style="display:flex;flex-direction:column;gap:16px;">
        <div style="padding:10px 14px;background:var(--bg-input);border-radius:var(--radius-md);font-size:13px;color:var(--text-secondary);">
          当前价格：<strong style="font-family:var(--font-mono);font-size:16px;">¥${currentPrice}</strong>
        </div>
        <div class="form-group">
          <label class="form-label">预警价格</label>
          <input class="form-input" type="number" id="alert-target-price" placeholder="输入目标价格" step="0.01" min="0" style="font-family:var(--font-mono);">
        </div>
        <div class="form-group">
          <label class="form-label">触发方向</label>
          <div style="display:flex;gap:8px;">
            <label style="flex:1;display:flex;align-items:center;gap:6px;cursor:pointer;padding:10px 14px;border:0.5px solid var(--border-color);border-radius:var(--radius-md);font-size:13px;">
              <input type="radio" name="alert-dir" value="above" checked> 向上突破 ≥
            </label>
            <label style="flex:1;display:flex;align-items:center;gap:6px;cursor:pointer;padding:10px 14px;border:0.5px solid var(--border-color);border-radius:var(--radius-md);font-size:13px;">
              <input type="radio" name="alert-dir" value="below"> 向下突破 ≤
            </label>
          </div>
        </div>
        <div style="display:flex;gap:8px;justify-content:flex-end;">
          <button class="btn btn-secondary" data-action="close-modal">取消</button>
          <button class="btn btn-primary" id="alert-submit-btn">确认设置</button>
        </div>
      </div>
    `);
    document.getElementById('alert-submit-btn')?.addEventListener('click', async () => {
      const price = parseFloat(document.getElementById('alert-target-price')?.value);
      const dir = document.querySelector('input[name="alert-dir"]:checked')?.value || 'above';
      if (!price || price <= 0) { ROX.toast('请输入有效的预警价格', 'warn'); return; }
      const res = await ROX.api.post('/api/alerts/', { code, name, target_price: price, direction: dir });
      if (res?.success) {
        ROX.closeModal();
        ROX.toast(`已为 ${name} 设置 ${dir==='above'?'≥':'≤'}${price} 预警`, 'success');
      } else {
        ROX.toast('设置失败', 'error');
      }
    });
  });

  // Add to watchlist
  const addWatchBtn = document.getElementById('btn-add-watch');
  if (addWatchBtn) {
    const markAdded = () => {
      addWatchBtn.textContent = '已加入 ✓';
      addWatchBtn.classList.add('btn-primary');
      addWatchBtn.classList.remove('btn-secondary');
    };
    addWatchBtn.addEventListener('click', async () => {
      const code = addWatchBtn.dataset.code;
      const name = decodeURIComponent(addWatchBtn.dataset.name || code);
      addWatchBtn.disabled = true;
      addWatchBtn.textContent = '添加中…';
      const res = await ROX.api.post('/api/watchlist/', { code, name });
      if (res && res.success) {
        markAdded();
      } else {
        addWatchBtn.disabled = false;
        addWatchBtn.textContent = '+ 自选';
        const detail = res?.detail;
        ROX.toast(typeof detail === 'string' ? detail : '加入自选失败', 'error');
      }
    });
    // 初始状态：若已在自选股中则标记
    try {
      const wl = await ROX.api.get('/api/watchlist/');
      if ((wl?.watchlist || []).some(w => w.code === addWatchBtn.dataset.code)) markAdded();
    } catch (_) { /* 忽略 */ }
  }

  // Fund flow mini chart
  if (analysis?.fund_flow?.trend?.length) {
    renderFlowChart(analysis.fund_flow.trend);
  } else {
    const flowEl = document.getElementById('flow-chart');
    if (flowEl) flowEl.innerHTML = '<div class="empty-state" style="padding:16px;"><p>资金趋势数据暂不可用</p></div>';
  }

  // Async load valuation (DCF + Comps)
  ROX.views.stock.loadValuation(code);

  // 自动刷新：每 30s 更新实时价格
  ROX.startAutoRefresh(async () => {
    const fresh = await ROX.api.get(`/api/stock/${code}`);
    if (!fresh || fresh.error) return;
    const priceEl = document.querySelector('.stock-live-price');
    if (priceEl) {
      const upColor = fresh.change_pct >= 0 ? 'var(--rox-up)' : 'var(--rox-down)';
      priceEl.innerHTML = `
        <span style="font-family:var(--font-mono);font-size:20px;font-weight:700;color:${upColor};">${ROX.fmt.num(fresh.price)}</span>
        <span style="font-family:var(--font-mono);font-size:13px;color:${upColor};">${ROX.fmt.pct(fresh.change_pct)}</span>
      `;
    }
  }, 30000);
});

async function loadRelatedResearch(code, mount) {
  if (!mount) return;
  const data = await ROX.api.get(`/api/research/related/${encodeURIComponent(code)}`);
  if (!data || data.error) { mount.innerHTML = '<div class="empty-state"><p>关联研究数据暂不可用</p></div>'; return null; }
  mount.innerHTML = `<div class="card-header"><div><div class="card-title">研究与决策关联</div><div class="card-subtitle">${data.cards.length} 张研究卡 · ${data.decisions.length} 条决策</div></div><button class="btn btn-secondary btn-sm" data-route="/research/new">新建研究卡</button></div>${data.cards.length ? `<div class="research-link-list">${data.cards.map(card => `<button class="research-link-item" data-route="/research/${card.id}"><strong>${ROX.escape(card.title)}</strong><span>${ROX.escape(card.status_label)} · ${ROX.escape(card.action || '观察')}</span></button>`).join('')}</div>` : '<div class="empty-state"><p>暂无关联研究卡</p></div>'}${data.decisions.length ? `<div class="research-link-decisions">${data.decisions.slice(0, 5).map(d => `<div><span class="tag ${ROX.fmt.actionTag(d.action)}">${ROX.escape(d.action)}</span><span>${ROX.escape(d.date)} · ${ROX.escape(d.result)}</span></div>`).join('')}</div>` : ''}`;
  mount.querySelectorAll('[data-route]').forEach(item => item.addEventListener('click', () => ROX.navigate(item.dataset.route)));
  return data;
}

function renderKline(candles, info, decisions = []) {
  const chartEl = document.getElementById('kline-chart');
  if (!chartEl) return;

  if (window.LightweightCharts) {
    if (_klineChart) _klineChart.remove();
    chartEl.innerHTML = '';
    _klineChart = LightweightCharts.createChart(chartEl, {
      layout: { background: { color: 'transparent' }, textColor: ROX.chartTheme().text },
      grid: { vertLines: { color: ROX.chartTheme().grid }, horzLines: { color: ROX.chartTheme().grid } },
      rightPriceScale: { borderColor: ROX.chartTheme().border },
      timeScale: { borderColor: ROX.chartTheme().border, timeVisible: false },
      crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
      handleScroll: true,
      handleScale: true,
    });
    _klineSeries = _klineChart.addCandlestickSeries({
      upColor: '#26A69A', downColor: '#EF5350', borderUpColor: '#26A69A', borderDownColor: '#EF5350', wickUpColor: '#26A69A', wickDownColor: '#EF5350',
    });
    _klineSeries.setData(candles.map(c => ({ time: c.date, open: c.open, high: c.high, low: c.low, close: c.close })));
    if (typeof _klineSeries.setMarkers === 'function') {
      const markers = decisions.filter(d => d.date && candles.some(c => c.date === d.date)).map(d => ({
        time: d.date,
        position: ['买入', '持有'].includes(d.action) ? 'belowBar' : 'aboveBar',
        color: d.action === '买入' ? '#ff453a' : d.action === '卖出' ? '#30d158' : '#0a84ff',
        shape: d.action === '买入' ? 'arrowUp' : d.action === '卖出' ? 'arrowDown' : 'circle',
        text: `${d.action}${d.result && d.result !== '待观察' ? ` · ${d.result}` : ''}`,
      }));
      _klineSeries.setMarkers(markers);
    }
    _klineChart.timeScale().fitContent();
    requestAnimationFrame(() => _klineChart && _klineChart.resize(chartEl.clientWidth, chartEl.clientHeight));
    return;
  }

  if (_klineChart) _klineChart.dispose();
  _klineChart = echarts.init(chartEl, 'dark');

  const dates = candles.map(c => c.date);
  const ohlc = candles.map(c => [c.open, c.close, c.low, c.high]);
  const volumes = candles.map(c => ({
    value: c.volume,
    itemStyle: { color: c.close >= c.open ? 'rgba(255,69,58,0.52)' : 'rgba(48,209,88,0.52)' }
  }));

  const option = {
    backgroundColor: 'transparent',
    grid: [
      { left: '8%', right: '3%', top: '5%', height: '60%' },
      { left: '8%', right: '3%', top: '72%', height: '18%' }
    ],
    xAxis: [
      { type: 'category', data: dates, gridIndex: 0, axisLine: { lineStyle: { color: ROX.chartTheme().border } }, axisLabel: { color: ROX.chartTheme().text, fontSize: 10 } },
      { type: 'category', data: dates, gridIndex: 1, axisLabel: { show: false } }
    ],
    yAxis: [
      { scale: true, gridIndex: 0, splitLine: { lineStyle: { color: ROX.chartTheme().grid } }, axisLabel: { color: ROX.chartTheme().text, fontSize: 10 } },
      { gridIndex: 1, splitLine: { show: false }, axisLabel: { show: false } }
    ],
    dataZoom: [
      { type: 'inside', xAxisIndex: [0, 1], start: 60, end: 100 },
      { type: 'slider', xAxisIndex: [0, 1], start: 60, end: 100, height: 20, bottom: 5, borderColor: 'transparent', backgroundColor: 'rgba(255,255,255,0.05)', fillerColor: 'rgba(10,132,255,0.14)', handleStyle: { color: '#0a84ff' } }
    ],
    tooltip: {
      trigger: 'axis', axisPointer: { type: 'cross' },
      backgroundColor: 'rgba(28,28,30,0.97)', borderColor: 'rgba(255,255,255,0.12)',
      textStyle: { color: '#f5f5f7', fontSize: 11 }
    },
    series: [
      {
        name: info.name, type: 'candlestick', data: ohlc, xAxisIndex: 0, yAxisIndex: 0,
        itemStyle: { color: '#ff453a', color0: '#30d158', borderColor: '#ff453a', borderColor0: '#30d158' }
      },
      {
        name: '成交量', type: 'bar', data: volumes, xAxisIndex: 1, yAxisIndex: 1,
      }
    ]
  };

  _klineChart.setOption(option);
  requestAnimationFrame(() => _klineChart && _klineChart.resize());
}

function renderFlowChart(trend) {
  const chartEl = document.getElementById('flow-chart');
  if (!chartEl) return;

  if (_flowChart) _flowChart.dispose();
  _flowChart = echarts.init(chartEl, 'dark');

  _flowChart.setOption({
    backgroundColor: 'transparent',
    grid: { left: '3%', right: '3%', top: '5%', bottom: '5%' },
    xAxis: { type: 'category', show: false, data: trend.map((_,i) => i+1) },
    yAxis: { show: false },
    series: [{
      type: 'bar', data: trend.map(v => ({
        value: v,
        itemStyle: { color: v >= 0 ? 'rgba(255,69,58,0.68)' : 'rgba(48,209,88,0.68)' }
      })),
      barWidth: '60%'
    }],
    tooltip: { trigger: 'axis', backgroundColor: 'rgba(28,28,30,0.97)', borderColor: 'rgba(255,255,255,0.12)', textStyle: { color: '#f5f5f7', fontSize: 11 } }
  });
  requestAnimationFrame(() => _flowChart && _flowChart.resize());
}

ROX.views = ROX.views || {};
ROX.views.stock = ROX.views.stock || {};
ROX.views.stock.loadValuation = async function(code) {
  const panel = document.getElementById('valuation-panel');
  if (!panel) return;

  try {
    const [dcf, comps] = await Promise.all([
      ROX.api.get(`/api/fundamentals/${code}/dcf`),
      ROX.api.get(`/api/fundamentals/${code}/comps`),
    ]);

    let html = '';

    // DCF section
    if (dcf && dcf.status === 'available' && dcf.fair_price != null) {
      const upColor = dcf.upside_pct > 0 ? 'var(--rox-up)' : dcf.upside_pct < 0 ? 'var(--rox-down)' : 'var(--text-secondary)';
      html += `
        <div style="margin-bottom:10px;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
            <span style="font-weight:500;">DCF 估值</span>
            <span style="font-family:var(--font-mono);color:${upColor};font-weight:500;">${ROX.escape(dcf.verdict)} ${dcf.upside_pct > 0 ? '+' : ''}${ROX.fmt.num(dcf.upside_pct)}%</span>
          </div>
          <div class="grid-2" style="gap:6px;margin-bottom:6px;">
            <div><span style="font-size:10px;color:var(--text-tertiary);">目标价</span><span style="font-family:var(--font-mono);font-size:12px;margin-left:4px;">${ROX.fmt.num(dcf.fair_price)}</span></div>
            <div><span style="font-size:10px;color:var(--text-tertiary);">当前</span><span style="font-family:var(--font-mono);font-size:12px;margin-left:4px;">${ROX.fmt.num(dcf.current_price)}</span></div>
            <div><span style="font-size:10px;color:var(--text-tertiary);">WACC</span><span style="font-family:var(--font-mono);font-size:12px;margin-left:4px;">${dcf.assumptions.wacc_pct}%</span></div>
            <div><span style="font-size:10px;color:var(--text-tertiary);">增长率</span><span style="font-family:var(--font-mono);font-size:12px;margin-left:4px;">${dcf.assumptions.revenue_growth_pct}%</span></div>
          </div>
          <div style="font-size:10px;color:var(--text-tertiary);margin-bottom:2px;">${ROX.escape(dcf.assumptions.source || '')}</div>
        </div>
      `;

      // 可调参数面板
      html += `
        <div style="margin-bottom:10px;">
          <button class="btn btn-sm btn-ghost" style="font-size:10px;padding:2px 8px;" onclick="this.nextElementSibling.style.display=this.nextElementSibling.style.display==='none'?'block':'none'">调参</button>
          <div id="dcf-params" style="display:none;padding:8px;margin-top:6px;background:var(--bg-secondary);border-radius:var(--radius-md);">
            <div class="grid-2" style="gap:8px;">
              <div><span style="font-size:10px;color:var(--text-tertiary);">WACC %</span><input type="number" id="dcf-wacc" value="${(dcf.assumptions.wacc_pct||9).toFixed(1)}" step="0.1" min="3" max="25" style="width:100%;background:var(--bg-input);border:0.5px solid var(--border-color);border-radius:6px;color:var(--text-primary);font-size:12px;padding:4px 6px;"></div>
              <div><span style="font-size:10px;color:var(--text-tertiary);">增长率 %</span><input type="number" id="dcf-growth" value="${(dcf.assumptions.revenue_growth_pct||0).toFixed(1)}" step="0.5" min="-10" max="30" style="width:100%;background:var(--bg-input);border:0.5px solid var(--border-color);border-radius:6px;color:var(--text-primary);font-size:12px;padding:4px 6px;"></div>
              <div><span style="font-size:10px;color:var(--text-tertiary);">永续 %</span><input type="number" id="dcf-termg" value="${(dcf.assumptions.terminal_growth_pct||2.5).toFixed(1)}" step="0.1" min="0.5" max="5" style="width:100%;background:var(--bg-input);border:0.5px solid var(--border-color);border-radius:6px;color:var(--text-primary);font-size:12px;padding:4px 6px;"></div>
              <div><span style="font-size:10px;color:var(--text-tertiary);">FCF率 %</span><input type="number" id="dcf-fcfr" value="${(parseFloat(dcf.assumptions.fcf_ratio||0)*100).toFixed(0)}" step="1" min="10" max="80" style="width:100%;background:var(--bg-input);border:0.5px solid var(--border-color);border-radius:6px;color:var(--text-primary);font-size:12px;padding:4px 6px;"></div>
            </div>
            <button class="btn btn-primary btn-sm" id="dcf-recalc" style="margin-top:8px;width:100%;">重新计算</button>
          </div>
        </div>
      `;
    } else {
      html += '<div style="margin-bottom:8px;font-size:11px;color:var(--text-tertiary);">DCF 数据不足，无法建模</div>';
    }

    // Comps section
    if (comps && comps.status === 'available' && comps.peer_median) {
      const peDev = comps.deviation.pe_dev_pct;
      const peColor = peDev != null ? (peDev < 0 ? 'var(--rox-up)' : peDev > 10 ? 'var(--rox-down)' : 'var(--text-secondary)') : 'var(--text-tertiary)';
      html += `
        <div style="padding-top:8px;border-top:1px solid var(--border-color-light);margin-bottom:6px;">
          <div style="font-weight:500;margin-bottom:4px;">可比估值 (${ROX.escape(comps.industry||'')} ${comps.peer_count}家)</div>
          <div class="grid-2" style="gap:6px;">
            <div><span style="font-size:10px;color:var(--text-tertiary);">PE 偏离</span><span style="font-family:var(--font-mono);font-size:12px;color:${peColor};margin-left:4px;">${peDev != null ? (peDev>0?'+':'')+peDev+'%' : '--'}</span></div>
            <div><span style="font-size:10px;color:var(--text-tertiary);">判断</span><span style="font-size:12px;color:${peColor};margin-left:4px;">${ROX.escape(comps.verdict)}</span></div>
            <div><span style="font-size:10px;color:var(--text-tertiary);">PE</span><span style="font-family:var(--font-mono);font-size:11px;margin-left:4px;">${ROX.fmt.num(comps.target.pe)} / 同业${ROX.fmt.num(comps.peer_median.pe)}</span></div>
            <div><span style="font-size:10px;color:var(--text-tertiary);">PB</span><span style="font-family:var(--font-mono);font-size:11px;margin-left:4px;">${ROX.fmt.num(comps.target.pb)} / 同业${ROX.fmt.num(comps.peer_median.pb)}</span></div>
          </div>
        </div>
      `;
    }

    if (!html) {
      panel.innerHTML = '<div style="font-size:11px;color:var(--text-tertiary);">估值模型数据暂不可用</div>';
    } else {
      panel.innerHTML = html;

      // DCF 参数重算
      const recalc = document.getElementById('dcf-recalc');
      if (recalc) {
        recalc.addEventListener('click', async () => {
          const w = document.getElementById('dcf-wacc')?.value;
          const g = document.getElementById('dcf-growth')?.value;
          const t = document.getElementById('dcf-termg')?.value;
          const f = document.getElementById('dcf-fcfr')?.value;
          const params = [];
          if (w) params.push(`wacc=${w / 100}`);
          if (g) params.push(`growth=${g}`);
          if (t) params.push(`terminal_g=${t}`);
          if (f) params.push(`fcf_ratio=${f / 100}`);
          const url = `/api/fundamentals/${code}/dcf?force=true&${params.join('&')}`;
          const newDcf = await ROX.api.get(url);
          if (newDcf?.status === 'available') {
            const c = newDcf.upside_pct > 0 ? 'var(--rox-up)' : newDcf.upside_pct < 0 ? 'var(--rox-down)' : 'var(--text-secondary)';
            recalc.textContent = `目标价 ${ROX.fmt.num(newDcf.fair_price)} (${ROX.fmt.pct(newDcf.upside_pct)}) ${newDcf.verdict}`;
            recalc.style.color = c;
            recalc.classList.remove('btn-primary');
            recalc.style.background = 'transparent';
          }
        });
      }
    }
  } catch (e) {
    panel.innerHTML = '<div style="font-size:11px;color:var(--text-tertiary);">估值模型加载失败</div>';
  }
};
