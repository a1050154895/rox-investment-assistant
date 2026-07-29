/* ============================================
   视图2 · 个股透视
   ============================================ */

let _klineChart = null;
let _flowChart = null;

ROX.register('/stock', async function(container, params) {
  const code = params.code || '600519';

  // Load data in parallel
  const [info, analysis, kline, indicators] = await Promise.all([
    ROX.api.get(`/api/stock/${code}`),
    ROX.api.get(`/api/stock/${code}/analysis`),
    ROX.api.get(`/api/stock/${code}/kline`),
    ROX.api.get(`/api/stock/${code}/indicators`),
  ]);

  if (!info || info.error) {
    container.innerHTML = '<div class="empty-state"><p>未找到该股票</p></div>';
    return;
  }

  ROX.state.currentStock = code;

  container.innerHTML = `
    <div style="display:flex;gap:16px;height:calc(100vh - 96px);">
      <!-- Left: K-Line -->
      <div style="flex:1;display:flex;flex-direction:column;gap:12px;min-width:0;">
        <!-- Stock header -->
        <div class="card" style="padding:12px 16px;">
          <div style="display:flex;align-items:center;justify-content:space-between;">
            <div style="display:flex;align-items:center;gap:12px;">
              <h2 style="font-size:18px;font-weight:600;">${info.name}</h2>
              <span style="font-family:var(--font-mono);font-size:12px;color:var(--text-tertiary);">${info.code}</span>
              <span class="tag tag-gray">${info.industry}</span>
            </div>
            <div style="display:flex;align-items:center;gap:16px;">
              <div style="text-align:right;">
                <span style="font-family:var(--font-mono);font-size:20px;font-weight:700;color:${info.change_pct>=0?'var(--rox-up)':'var(--rox-down)'};">${ROX.fmt.num(info.price)}</span>
                <span style="font-family:var(--font-mono);font-size:13px;margin-left:8px;color:${info.change_pct>=0?'var(--rox-up)':'var(--rox-down)'};">${ROX.fmt.pct(info.change_pct)}</span>
              </div>
              <div style="display:flex;gap:4px;">
                <button class="btn btn-secondary btn-sm" data-period="daily" id="btn-daily">日线</button>
                <button class="btn btn-secondary btn-sm" data-period="weekly" id="btn-weekly">周线</button>
              </div>
              <button class="btn btn-primary btn-sm" data-action="add-decision" data-code="${info.code}">记录决策</button>
            </div>
          </div>
          <div style="display:flex;gap:20px;margin-top:8px;font-size:11px;color:var(--text-tertiary);">
            <span>PE <span style="color:var(--text-secondary);font-family:var(--font-mono);">${ROX.fmt.num(info.pe,1)}</span></span>
            <span>PB <span style="color:var(--text-secondary);font-family:var(--font-mono);">${ROX.fmt.num(info.pb)}</span></span>
            <span>ROE <span style="color:var(--text-secondary);font-family:var(--font-mono);">${ROX.fmt.num(info.roe,1)}%</span></span>
            <span>市值 <span style="color:var(--text-secondary);">${info.market_cap}</span></span>
            <span>换手 <span style="color:var(--text-secondary);font-family:var(--font-mono);">${ROX.fmt.num(info.turnover)}%</span></span>
          </div>
        </div>

        <!-- K-Line Chart -->
        <div class="card" style="flex:1;padding:12px;overflow:hidden;">
          <div id="kline-chart" class="chart-container"></div>
        </div>

        <!-- Fund Flow -->
        <div class="card" style="padding:12px;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
            <span style="font-size:12px;font-weight:500;">主力资金流向</span>
            <span style="font-family:var(--font-mono);font-size:13px;color:${analysis?.fund_flow?.main_inflow>=0?'var(--rox-up)':'var(--rox-down)'};">${analysis?.fund_flow?.main_inflow>=0?'+':''}${ROX.fmt.num(analysis?.fund_flow?.main_inflow)} 亿</span>
          </div>
          <div id="flow-chart"></div>
        </div>
      </div>

      <!-- Right: Framework Panel -->
      <div style="width:340px;flex-shrink:0;overflow-y:auto;display:flex;flex-direction:column;gap:12px;">
        ${analysis ? `
          <!-- Consistency Score -->
          <div class="card">
            <div class="card-header">
              <div class="card-title">框架一致性评分</div>
              <span class="score-badge ${ROX.fmt.scoreClass(analysis.consistency_score)}" style="font-size:16px;min-width:48px;height:28px;">${analysis.consistency_score}</span>
            </div>
            <div style="font-size:11px;color:var(--text-tertiary);margin-bottom:12px;">总体评价：${analysis.score_label}</div>
            ${Object.entries(analysis.dimensions).map(([key, dim]) => `
              <div style="margin-bottom:10px;">
                <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
                  <span style="font-size:11px;color:var(--text-secondary);">${dim.label} <span style="color:var(--text-muted);">(${dim.weight}%)</span></span>
                  <span style="font-size:11px;font-family:var(--font-mono);color:var(--text-secondary);">${dim.score}</span>
                </div>
                <div class="progress"><div class="progress-fill ${dim.score>=70?'green':dim.score>=45?'amber':'red'}" style="width:${dim.score}%"></div></div>
                <div style="font-size:10px;color:var(--text-muted);margin-top:3px;">${dim.detail}</div>
              </div>
            `).join('')}
          </div>

          <!-- Contradictions -->
          <div class="card">
            <div class="card-header"><div class="card-title">矛盾分析</div></div>
            <div style="display:flex;flex-direction:column;gap:10px;">
              <div>
                <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
                  <span style="font-size:11px;color:var(--text-primary);">主要矛盾</span>
                  <span style="font-size:11px;color:var(--text-tertiary);">强度 ${analysis.contradictions.primary.intensity}</span>
                </div>
                <div style="font-size:11px;color:var(--text-secondary);margin-bottom:4px;">${analysis.contradictions.primary.name}</div>
                <div class="progress"><div class="progress-fill red" style="width:${analysis.contradictions.primary.intensity}%"></div></div>
              </div>
              <div>
                <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
                  <span style="font-size:11px;color:var(--text-primary);">次要矛盾</span>
                  <span style="font-size:11px;color:var(--text-tertiary);">强度 ${analysis.contradictions.secondary.intensity}</span>
                </div>
                <div style="font-size:11px;color:var(--text-secondary);margin-bottom:4px;">${analysis.contradictions.secondary.name}</div>
                <div class="progress"><div class="progress-fill amber" style="width:${analysis.contradictions.secondary.intensity}%"></div></div>
              </div>
            </div>
          </div>

          <!-- Value Assessment -->
          <div class="card">
            <div class="card-header"><div class="card-title">价值规律评估</div></div>
            <div class="grid-2" style="gap:8px;">
              <div>
                <div style="font-size:10px;color:var(--text-tertiary);">剩余价值率</div>
                <div style="font-family:var(--font-mono);font-size:14px;font-weight:500;">${analysis.value_assessment.surplus_rate}%</div>
              </div>
              <div>
                <div style="font-size:10px;color:var(--text-tertiary);">资本有机构成</div>
                <div style="font-family:var(--font-mono);font-size:14px;font-weight:500;">${analysis.value_assessment.organic_composition}</div>
              </div>
              <div>
                <div style="font-size:10px;color:var(--text-tertiary);">周转率</div>
                <div style="font-family:var(--font-mono);font-size:14px;font-weight:500;">${analysis.value_assessment.turnover_rate}</div>
              </div>
              <div>
                <div style="font-size:10px;color:var(--text-tertiary);">定价权</div>
                <div style="font-size:14px;font-weight:500;">${analysis.value_assessment.pricing_power}</div>
              </div>
            </div>
          </div>

          <!-- Indicators -->
          ${indicators && !indicators.error ? `
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
        ` : '<div class="card"><p style="color:var(--text-tertiary);font-size:12px;">分析数据加载中...</p></div>'}
      </div>
    </div>
  `;

  // Render charts
  if (kline && kline.candles) {
    renderKline(kline.candles, info);
  }

  // Period switch
  document.getElementById('btn-daily')?.addEventListener('click', async () => {
    const data = await ROX.api.get(`/api/stock/${code}/kline?period=daily`);
    if (data && data.candles) renderKline(data.candles, info);
  });
  document.getElementById('btn-weekly')?.addEventListener('click', async () => {
    const data = await ROX.api.get(`/api/stock/${code}/kline?period=weekly`);
    if (data && data.candles) renderKline(data.candles, info);
  });

  // Fund flow mini chart
  if (analysis && analysis.fund_flow) {
    renderFlowChart(analysis.fund_flow.trend || []);
  }
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
  window.addEventListener('resize', () => _klineChart && _klineChart.resize());
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
  window.addEventListener('resize', () => _flowChart && _flowChart.resize());
}
