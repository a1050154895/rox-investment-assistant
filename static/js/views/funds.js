/* ============================================
   基金/ETF研究透视
   ============================================ */

let _fundChart = null;

ROX.register('/funds', async function(container, params) {
  const code = params.code || '510300';
  const [fund, kline] = await Promise.all([
    ROX.api.get(`/api/funds/${code}`),
    ROX.api.get(`/api/funds/${code}/kline`),
  ]);
  if (!fund || fund.error) {
    container.innerHTML = `<div class="empty-state"><p>${ROX.escape(fund?.error || '基金数据加载失败')}</p></div>`;
    return;
  }
  const q = fund.quote || {};
  container.innerHTML = `
    <div class="fund-page">
      <div class="fund-page-head"><div><div class="eyebrow">ROX / FUND RESEARCH</div><h2>${ROX.escape(fund.name)}</h2><p>${ROX.escape(fund.code)} · ${ROX.escape(fund.category)} · 跟踪 ${ROX.escape(fund.tracking)}</p></div><button class="btn btn-primary" data-action="create-research-card" data-code="${fund.code}" data-name="${ROX.escape(fund.name)}" data-price="${q.price ?? ''}" data-data-status="${ROX.escape(fund.data_status || '')}" data-data-source="${ROX.escape(fund.data_source || '')}" data-as-of="${ROX.escape(fund.as_of || '')}">开始研究</button></div>
      <div class="fund-evidence-strip"><span class="evidence-badge ${fund.stale ? 'is-stale' : 'is-live'}"><i></i>${fund.stale ? '历史快照' : '实时行情'} · ${ROX.escape(fund.as_of || '时间未知')}</span><span>来源：${ROX.escape(fund.data_source || '不可用')}</span><span>行情价格不等于基金净值</span></div>
      <div class="fund-summary-grid">
        <div class="card fund-price-card"><span>场内价格</span><strong>${ROX.fmt.num(q.price)}</strong><em class="${ROX.fmt.color(q.change_pct || 0)}">${ROX.fmt.pct(q.change_pct)}</em><small>仅表示交易价格，净值待接入</small></div>
        <div class="card fund-meta-card"><span>跟踪标的</span><strong>${ROX.escape(fund.tracking)}</strong><small>${ROX.escape(fund.fund_type)} · ${ROX.escape(fund.category)}</small><small>跟踪误差：暂不可用</small></div>
      </div>
      <div class="card fund-chart-card"><div class="card-header"><div><div class="card-title">价格观察</div><div class="card-subtitle">用于观察交易价格波动，不替代净值分析</div></div><span class="tag ${fund.stale ? 'tag-amber' : 'tag-green'}">${fund.stale ? '快照' : '实时'}</span></div><div id="fund-kline" class="fund-kline"></div>${kline?.metrics ? `<div class="fund-risk-metrics"><div><span>区间收益</span><strong>${ROX.fmt.pct(kline.metrics.period_return_pct)}</strong></div><div><span>最大回撤</span><strong>${ROX.fmt.pct(kline.metrics.max_drawdown_pct)}</strong></div><div><span>波动代理</span><strong>${ROX.fmt.num(kline.metrics.volatility_proxy_pct)}%</strong></div><div><span>样本</span><strong>${kline.metrics.sample_count}根</strong></div></div><div class="fund-metric-note">${ROX.escape(kline.metrics.note)}</div>` : ''}</div>
      <div class="card fund-disclosure-card"><div class="card-header"><div class="card-title">还需要补齐的基金证据</div><span class="tag tag-gray">不虚构</span></div><div class="fund-disclosure-list">${Object.entries(fund.disclosures || {}).map(([key, item]) => `<div><strong>${key === 'nav' ? '基金净值' : key === 'holdings' ? '持仓披露' : '跟踪误差'}</strong><span>${ROX.escape(item.message)}</span></div>`).join('')}</div></div>
    </div>`;
  if (kline?.candles?.length && window.LightweightCharts) {
    const el = document.getElementById('fund-kline');
    _fundChart = LightweightCharts.createChart(el, { layout:{background:{color:'transparent'},textColor:'#948d83'}, grid:{vertLines:{color:'rgba(224,211,191,.06)'},horzLines:{color:'rgba(224,211,191,.06)'}}, rightPriceScale:{borderColor:'rgba(224,211,191,.1)'}, timeScale:{borderColor:'rgba(224,211,191,.1)'} });
    const series = _fundChart.addAreaSeries({ lineColor:'#c65a43', topColor:'rgba(198,90,67,.24)', bottomColor:'rgba(198,90,67,0)' });
    series.setData(kline.candles.map(c => ({time:c.date,value:c.close})));
    _fundChart.timeScale().fitContent();
  } else {
    document.getElementById('fund-kline').innerHTML = '<div class="empty-state"><p>可靠K线数据暂不可用</p></div>';
  }
});
