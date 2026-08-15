/* ============================================
   视图7 · 回测引擎
   ============================================ */

let _equityChart = null;
window.addEventListener('resize', () => { _equityChart?.resize(); });

ROX.register('/backtest', async function(container) {
  const [stratRes, stockRes] = await Promise.all([
    ROX.api.get('/api/backtest/strategies'),
    ROX.api.get('/api/backtest/stocks'),
  ]);

  const strategies = stratRes?.strategies || [];
  const stocks = stockRes?.stocks || [];

  container.innerHTML = `
    <div class="backtest-layout">
      <!-- 配置面板 -->
      <div class="card backtest-config">
        <h3 style="font-size:15px;font-weight:600;margin-bottom:12px;">回测配置</h3>

        <div class="form-group" style="margin-bottom:10px;">
          <label class="form-label">股票</label>
          <select class="form-input" id="bt-stock">
            ${stocks.map(s => `<option value="${s.code}">${s.name} (${s.code})</option>`).join('')}
          </select>
        </div>

        <div class="form-group" style="margin-bottom:10px;">
          <label class="form-label">策略</label>
          <select class="form-input" id="bt-strategy">
            ${strategies.map(s => `<option value="${s.id}">${s.name}</option>`).join('')}
          </select>
          <p id="bt-strategy-desc" style="font-size:12px;color:var(--text-tertiary);margin-top:4px;"></p>
        </div>

        <div id="bt-params" style="margin-bottom:10px;"></div>

        <div class="filter-row" style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:10px;">
          <div class="form-group">
            <label class="form-label">K线周期</label>
            <select class="form-input" id="bt-period">
              <option value="day">日线</option>
              <option value="week">周线</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">K线根数</label>
            <select class="form-input" id="bt-limit">
              <option value="120">120根</option>
              <option value="250" selected>250根</option>
              <option value="500">500根</option>
            </select>
          </div>
        </div>

        <div class="filter-row" style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:12px;">
          <div class="form-group">
            <label class="form-label">初始资金</label>
            <input class="form-input" type="number" id="bt-capital" value="100000" step="10000">
          </div>
          <div class="form-group">
            <label class="form-label">手续费率</label>
            <input class="form-input" type="number" id="bt-commission" value="0.001" step="0.0005">
          </div>
        </div>

        <button class="btn btn-primary" id="bt-run" data-action="run-backtest" style="width:100%;">运行回测</button>
      </div>

      <!-- 结果区域 -->
      <div class="backtest-results" id="bt-results">
        <div class="empty-state">
          <p>选择股票和策略后点击「运行回测」</p>
          <p style="font-size:12px;color:var(--text-tertiary);">回测仅用于框架验证，不代表未来收益</p>
        </div>
      </div>
    </div>
  `;

  // 渲染策略参数
  function renderParams() {
    const sid = document.getElementById('bt-strategy')?.value;
    const strat = strategies.find(s => s.id === sid);
    const descEl = document.getElementById('bt-strategy-desc');
    const paramEl = document.getElementById('bt-params');
    if (!strat) return;
    descEl.textContent = strat.description;
    paramEl.innerHTML = (strat.params || []).map(p => `
      <div class="form-group" style="margin-bottom:8px;">
        <label class="form-label">${p.label}</label>
        <input class="form-input bt-param" type="number" data-key="${p.key}" value="${p.default}" min="${p.min}" max="${p.max}" step="1">
      </div>
    `).join('');
  }
  renderParams();
  document.getElementById('bt-strategy')?.addEventListener('change', renderParams);

  // 运行回测
  const runBtn = document.getElementById('bt-run');
  runBtn?.addEventListener('click', async () => {
    runBtn.disabled = true;
    runBtn.textContent = '回测中…';
    document.getElementById('bt-results').innerHTML = '<div class="loading"><div class="spinner"></div></div>';

    const code = document.getElementById('bt-stock')?.value;
    const strategy = document.getElementById('bt-strategy')?.value;
    const period = document.getElementById('bt-period')?.value;
    const klineLimit = parseInt(document.getElementById('bt-limit')?.value || '250');
    const capital = parseFloat(document.getElementById('bt-capital')?.value || '100000');
    const commission = parseFloat(document.getElementById('bt-commission')?.value || '0.001');

    const params = {};
    document.querySelectorAll('.bt-param').forEach(el => {
      params[el.dataset.key] = parseFloat(el.value);
    });

    const res = await ROX.api.post('/api/backtest/run', {
      code, strategy, params,
      period, kline_limit: klineLimit,
      initial_capital: capital, commission_rate: commission,
    });

    runBtn.disabled = false;
    runBtn.textContent = '运行回测';

    if (res && !res.error) {
      renderResults(res);
    } else {
      document.getElementById('bt-results').innerHTML = `<div class="empty-state"><p>${res?.error || '回测失败，请重试'}</p></div>`;
    }
  });

  function renderResults(res) {
    const el = document.getElementById('bt-results');
    const up = res.total_return >= 0;
    const excessUp = res.excess_return >= 0;

    el.innerHTML = `
      <div class="card" style="margin-bottom:12px;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
          <div>
            <span style="font-size:16px;font-weight:600;">${ROX.escape(res.name)}</span>
            <span style="font-size:12px;color:var(--text-tertiary);margin-left:6px;">${res.code}</span>
          </div>
          <span class="tag tag-gray">${ROX.escape(res.strategy_name)}</span>
        </div>
        <div class="backtest-stats" style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;">
          <div class="stat-box">
            <div class="stat-label">策略收益</div>
            <div class="stat-value ${up ? 'text-up' : 'text-down'}" style="font-size:20px;font-weight:700;">
              ${up ? '+' : ''}${res.total_return}%
            </div>
          </div>
          <div class="stat-box">
            <div class="stat-label">买入持有</div>
            <div class="stat-value" style="font-size:20px;font-weight:700;color:var(--text-secondary);">
              ${res.buy_hold_return >= 0 ? '+' : ''}${res.buy_hold_return}%
            </div>
          </div>
          <div class="stat-box">
            <div class="stat-label">超额收益</div>
            <div class="stat-value ${excessUp ? 'text-up' : 'text-down'}" style="font-size:20px;font-weight:700;">
              ${excessUp ? '+' : ''}${res.excess_return}%
            </div>
          </div>
          <div class="stat-box">
            <div class="stat-label">最大回撤</div>
            <div class="stat-value text-down" style="font-size:20px;font-weight:700;">
              -${res.max_drawdown}%
            </div>
          </div>
          <div class="stat-box">
            <div class="stat-label">初始资金</div>
            <div class="stat-value" style="font-size:14px;font-weight:600;">¥${res.initial_capital.toLocaleString()}</div>
          </div>
          <div class="stat-box">
            <div class="stat-label">期末权益</div>
            <div class="stat-value" style="font-size:14px;font-weight:600;">¥${res.final_equity.toLocaleString()}</div>
          </div>
          <div class="stat-box">
            <div class="stat-label">交易次数</div>
            <div class="stat-value" style="font-size:14px;font-weight:600;">${res.total_trades} 次</div>
          </div>
          <div class="stat-box">
            <div class="stat-label">胜率</div>
            <div class="stat-value" style="font-size:14px;font-weight:600;">${res.win_rate}%</div>
          </div>
        </div>
      </div>

      <div class="card" style="margin-bottom:12px;">
        <h4 style="font-size:13px;font-weight:600;margin-bottom:8px;">权益曲线</h4>
        <div id="equity-chart" style="width:100%;height:240px;"></div>
      </div>

      <div class="card">
        <h4 style="font-size:13px;font-weight:600;margin-bottom:8px;">交易记录 (${res.trades.length})</h4>
        <div class="table-wrap" style="overflow-x:auto;max-height:300px;overflow-y:auto;">
          <table class="data-table" style="width:100%;font-size:12px;">
            <thead>
              <tr>
                <th style="text-align:left;">日期</th>
                <th style="text-align:left;">操作</th>
                <th style="text-align:right;">价格</th>
                <th style="text-align:right;">数量</th>
                <th style="text-align:right;">金额</th>
                <th style="text-align:right;">盈亏</th>
                <th style="text-align:right;">盈亏%</th>
              </tr>
            </thead>
            <tbody>
              ${res.trades.map(t => `
                <tr>
                  <td>${t.date}</td>
                  <td><span class="tag ${t.action === '买入' ? 'tag-red' : 'tag-green'}">${t.action}</span></td>
                  <td style="text-align:right;font-family:var(--font-mono);">${t.price}</td>
                  <td style="text-align:right;font-family:var(--font-mono);">${t.shares}</td>
                  <td style="text-align:right;font-family:var(--font-mono);">${(t.cost || t.revenue || 0).toLocaleString()}</td>
                  <td style="text-align:right;font-family:var(--font-mono);" class="${t.pnl != null ? (t.pnl >= 0 ? 'text-up' : 'text-down') : ''}">${t.pnl != null ? (t.pnl >= 0 ? '+' : '') + t.pnl.toLocaleString() : '--'}</td>
                  <td style="text-align:right;font-family:var(--font-mono);" class="${t.pnl_pct != null ? (t.pnl_pct >= 0 ? 'text-up' : 'text-down') : ''}">${t.pnl_pct != null ? (t.pnl_pct >= 0 ? '+' : '') + t.pnl_pct + '%' : '--'}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>

      <p style="font-size:11px;color:var(--text-tertiary);margin-top:8px;">${res.disclaimer}</p>
      <p style="font-size:11px;color:var(--text-tertiary);">回测区间: ${res.start_date} 至 ${res.end_date} ｜ K线根数: ${res.candle_count}</p>
    `;

    // 绘制权益曲线
    const chartEl = document.getElementById('equity-chart');
    if (chartEl && res.equity_curve && res.equity_curve.length > 0) {
      _equityChart = echarts.init(chartEl);
      _equityChart.setOption({
        tooltip: { trigger: 'axis', formatter: p => `${p[0].axisValue}<br/>权益: ¥${p[0].data.toLocaleString()}` },
        xAxis: { type: 'category', data: res.equity_curve.map(e => e.date), axisLabel: { fontSize: 10, rotate: 30 } },
        yAxis: { type: 'value', axisLabel: { fontSize: 10, formatter: v => (v / 10000).toFixed(0) + '万' } },
        series: [{
          type: 'line', data: res.equity_curve.map(e => e.equity),
          smooth: true, symbol: 'none',
          lineStyle: { width: 2, color: '#0a84ff' },
          areaStyle: { color: 'rgba(10, 132, 255, 0.1)' },
        }],
        grid: { left: 50, right: 20, top: 10, bottom: 30 },
      });
    }
  }
});
