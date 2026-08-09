/* ============================================
   视图2 · 个股透视
   ============================================ */

let _klineChart = null;
let _flowChart = null;
window.addEventListener('resize', () => {
  _klineChart?.resize();
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
    <div class="stock-detail-layout">
      <!-- Left: K-Line -->
      <div class="stock-main-column">
        <!-- Stock header -->
        <div class="card stock-hero">
          <div class="stock-hero-row">
            <div class="stock-identity">
              <h2 style="font-size:18px;font-weight:600;">${info.name}</h2>
              <span style="font-family:var(--font-mono);font-size:12px;color:var(--text-tertiary);">${info.code}</span>
              <span class="tag tag-gray">${info.industry}</span>
              <span class="tag ${info.stale ? 'tag-amber' : 'tag-green'}">${info.stale ? `历史快照 ${info.as_of || ''}` : '实时数据'}</span>
            </div>
            <div class="stock-hero-actions">
              <div class="stock-live-price">
                <span style="font-family:var(--font-mono);font-size:20px;font-weight:700;color:${info.change_pct>=0?'var(--rox-up)':'var(--rox-down)'};">${ROX.fmt.num(info.price)}</span>
                <span style="font-family:var(--font-mono);font-size:13px;color:${info.change_pct>=0?'var(--rox-up)':'var(--rox-down)'};">${ROX.fmt.pct(info.change_pct)}</span>
              </div>
              <div class="stock-period-actions">
                <button class="btn btn-secondary btn-sm" data-period="daily" id="btn-daily">日线</button>
                <button class="btn btn-secondary btn-sm" data-period="weekly" id="btn-weekly">周线</button>
              </div>
              <button class="btn btn-primary btn-sm" data-action="add-decision" data-code="${info.code}">记录决策</button>
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
        <div class="card" style="flex:1;padding:12px;overflow:hidden;">
          ${kline?.data_status === 'unavailable' ? `<div class="empty-state"><p>${kline.message || 'K线数据暂不可用'}</p></div>` : `<div id="kline-chart" class="chart-container"></div>`}
        </div>

        <!-- Fund Flow -->
        <div class="card" style="padding:12px;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
            <span style="font-size:12px;font-weight:500;">主力资金流向</span>
            <span style="font-family:var(--font-mono);font-size:13px;color:${analysis?.fund_flow?.main_inflow != null && analysis.fund_flow.main_inflow>=0?'var(--rox-up)':'var(--rox-down)'};">${analysis?.fund_flow?.main_inflow == null ? '数据不可用' : `${analysis.fund_flow.main_inflow>=0?'+':''}${ROX.fmt.num(analysis.fund_flow.main_inflow)} 亿`}</span>
          </div>
          <div id="flow-chart"></div>
        </div>
      </div>

      <!-- Right: Framework Panel -->
      <aside class="stock-framework-panel">
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
    renderKline(kline.candles, info);
  }

  // Period switch
  document.getElementById('btn-daily')?.addEventListener('click', async () => {
    const data = await ROX.api.get(`/api/stock/${code}/kline?period=daily`);
    if (data?.candles?.length) renderKline(data.candles, info);
  });
  document.getElementById('btn-weekly')?.addEventListener('click', async () => {
    const data = await ROX.api.get(`/api/stock/${code}/kline?period=weekly`);
    if (data?.candles?.length) renderKline(data.candles, info);
  });

  // Fund flow mini chart
  if (analysis?.fund_flow?.trend?.length) {
    renderFlowChart(analysis.fund_flow.trend);
  } else {
    const flowEl = document.getElementById('flow-chart');
    if (flowEl) flowEl.innerHTML = '<div class="empty-state" style="padding:16px;"><p>资金趋势数据暂不可用</p></div>';
  }

  // Async load valuation (DCF + Comps)
  ROX.views.stock.loadValuation(code);
});

function renderKline(candles, info) {
  const chartEl = document.getElementById('kline-chart');
  if (!chartEl) return;

  if (_klineChart) _klineChart.dispose();
  _klineChart = echarts.init(chartEl, 'dark');

  const dates = candles.map(c => c.date);
  const ohlc = candles.map(c => [c.open, c.close, c.low, c.high]);
  const volumes = candles.map(c => ({
    value: c.volume,
    itemStyle: { color: c.close >= c.open ? 'rgba(212,87,74,0.52)' : 'rgba(122,158,110,0.52)' }
  }));

  const option = {
    backgroundColor: 'transparent',
    grid: [
      { left: '8%', right: '3%', top: '5%', height: '60%' },
      { left: '8%', right: '3%', top: '72%', height: '18%' }
    ],
    xAxis: [
      { type: 'category', data: dates, gridIndex: 0, axisLine: { lineStyle: { color: 'rgba(200,180,160,0.14)' } }, axisLabel: { color: '#8a7f70', fontSize: 10 } },
      { type: 'category', data: dates, gridIndex: 1, axisLabel: { show: false } }
    ],
    yAxis: [
      { scale: true, gridIndex: 0, splitLine: { lineStyle: { color: 'rgba(200,180,160,0.07)' } }, axisLabel: { color: '#8a7f70', fontSize: 10 } },
      { gridIndex: 1, splitLine: { show: false }, axisLabel: { show: false } }
    ],
    dataZoom: [
      { type: 'inside', xAxisIndex: [0, 1], start: 60, end: 100 },
      { type: 'slider', xAxisIndex: [0, 1], start: 60, end: 100, height: 20, bottom: 5, borderColor: 'transparent', backgroundColor: 'rgba(200,180,160,0.05)', fillerColor: 'rgba(200,65,44,0.14)', handleStyle: { color: '#c8412c' } }
    ],
    tooltip: {
      trigger: 'axis', axisPointer: { type: 'cross' },
      backgroundColor: 'rgba(34,29,24,0.97)', borderColor: 'rgba(200,180,160,0.18)',
      textStyle: { color: '#f5ede0', fontSize: 11 }
    },
    series: [
      {
        name: info.name, type: 'candlestick', data: ohlc, xAxisIndex: 0, yAxisIndex: 0,
        itemStyle: { color: '#d4574a', color0: '#7a9e6e', borderColor: '#d4574a', borderColor0: '#7a9e6e' }
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
        itemStyle: { color: v >= 0 ? 'rgba(212,87,74,0.68)' : 'rgba(122,158,110,0.68)' }
      })),
      barWidth: '60%'
    }],
    tooltip: { trigger: 'axis', backgroundColor: 'rgba(34,29,24,0.97)', borderColor: 'rgba(200,180,160,0.18)', textStyle: { color: '#f5ede0', fontSize: 11 } }
  });
  requestAnimationFrame(() => _flowChart && _flowChart.resize());
}

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
