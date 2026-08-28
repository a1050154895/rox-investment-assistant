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
  const coverage = fund.evidence_coverage || {};
  const coverageList = Object.entries(coverage);
  const coverageAvailable = coverageList.filter(([, item]) => item.status && item.status !== 'unavailable').length;
  container.innerHTML = `
    <div class="fund-page">
      <div class="fund-page-head"><div><div class="eyebrow">ROX / FUND RESEARCH</div><h2>${ROX.escape(fund.name)}</h2><p>${ROX.escape(fund.code)} · ${ROX.escape(fund.category)} · 跟踪 ${ROX.escape(fund.tracking)}</p><div class="fund-search"><input class="form-input" id="fund-search-input" placeholder="搜索基金代码或名称" autocomplete="off"><div id="fund-search-results" class="search-results"></div></div></div><button class="btn btn-primary" data-action="create-research-card" data-code="${fund.code}" data-name="${ROX.escape(fund.name)}" data-price="${q.price ?? ''}" data-data-status="${ROX.escape(fund.data_status || '')}" data-data-source="${ROX.escape(fund.data_source || '')}" data-as-of="${ROX.escape(fund.as_of || '')}">开始研究</button><button class="btn btn-secondary" data-action="open-evidence-drawer" data-title="${ROX.escape(fund.name)}" data-content="${ROX.escape(`场内价格：${fund.name} ${ROX.fmt.num(q.price)}（${ROX.fmt.pct(q.change_pct || 0)}），仅交易价格、非净值`)}" data-source="${ROX.escape(fund.data_source || '')}" data-as-of="${ROX.escape(fund.as_of || '')}" data-code="${fund.code}" data-stock="${ROX.escape(fund.name)}">存为证据</button></div>
      <div class="fund-evidence-strip"><span class="evidence-badge ${fund.stale ? 'is-stale' : 'is-live'}"><i></i>${fund.stale ? '历史快照' : '实时行情'} · ${ROX.escape(fund.as_of || '时间未知')}</span><span>来源：${ROX.escape(fund.data_source || '不可用')}</span><span>行情价格不等于基金净值</span></div>
      <div class="fund-summary-grid">
        <div class="card fund-price-card"><span>场内价格</span><strong>${ROX.fmt.num(q.price)}</strong><em class="${ROX.fmt.color(q.change_pct || 0)}">${ROX.fmt.pct(q.change_pct)}</em><small>仅表示交易价格，净值待接入</small></div>
        <div class="card fund-meta-card"><span>跟踪标的</span><strong>${ROX.escape(fund.tracking)}</strong><small>${ROX.escape(fund.fund_type)} · ${ROX.escape(fund.category)}</small><small>${coverage.tracking_error?.proxy ? `跟踪误差代理：年化 ${coverage.tracking_error.proxy.tracking_error_annualized_pct}%（价格口径，${coverage.tracking_error.proxy.sample_days} 日）` : '跟踪误差：待指数样本可用后计算'}</small></div>
      </div>
      <div class="card fund-chart-card"><div class="card-header"><div><div class="card-title">价格观察</div><div class="card-subtitle">用于观察交易价格波动，不替代净值分析</div></div><span class="tag ${fund.stale ? 'tag-amber' : 'tag-green'}">${fund.stale ? '快照' : '实时'}</span></div><div id="fund-kline" class="fund-kline"></div>${kline?.metrics ? `<div class="fund-risk-metrics"><div><span>区间收益</span><strong>${ROX.fmt.pct(kline.metrics.period_return_pct)}</strong></div><div><span>最大回撤</span><strong>${ROX.fmt.pct(kline.metrics.max_drawdown_pct)}</strong></div><div><span>波动代理</span><strong>${ROX.fmt.num(kline.metrics.volatility_proxy_pct)}%</strong></div><div><span>样本</span><strong>${kline.metrics.sample_count}根</strong></div></div><div class="fund-metric-note">${ROX.escape(kline.metrics.note)}</div>` : ''}</div>
      <div class="card fund-coverage-card"><div class="card-header"><div><div class="card-title">数据覆盖矩阵</div><div class="card-subtitle">每个字段都标注来源、时间和状态；缺失不伪造，不把价格冒充净值。</div></div><span class="tag tag-gray">已覆盖 ${coverageAvailable}/${coverageList.length}</span></div><div class="fund-coverage-grid">${coverageList.map(([key, item]) => `<div class="${item.status && item.status !== 'unavailable' ? 'covered' : 'missing'}"><div class="fund-coverage-head"><strong>${({market_price:'场内价格', kline:'价格K线', nav:'基金净值', iopv:'IOPV/参考净值', premium_discount:'折溢价', holdings:'持仓披露', tracking_error:'跟踪误差'}[key] || key)}</strong><span class="tag ${item.status && item.status !== 'unavailable' ? 'tag-green' : 'tag-gray'}">${({available: '可用', realtime: '实时', snapshot: '快照', partial: '部分可用'}[item.status]) || '不可用'}</span></div><span class="fund-coverage-msg">${ROX.escape(item.message || '')}</span><span class="fund-coverage-meta">来源 ${ROX.escape(item.source || '未接入')} · ${ROX.escape(item.as_of || '无时间')}</span></div>`).join('')}</div></div>
      <div class="fund-decision-bar"><button class="btn btn-secondary" data-action="add-decision" data-code="${fund.code}" data-name="${ROX.escape(fund.name)}">记录关联决策</button><span>研究卡保存后，再据此记录买卖或持有决策</span></div>
      <div class="card" id="fund-research-links" style="padding:12px;"><div class="loading"><div class="spinner"></div></div></div>
    </div>`;
  if (kline?.candles?.length && window.LightweightCharts) {
    const el = document.getElementById('fund-kline');
    const ct = ROX.chartTheme();
    _fundChart = LightweightCharts.createChart(el, { layout:{background:{color:'transparent'},textColor:ct.text}, grid:{vertLines:{color:ct.grid},horzLines:{color:ct.grid}}, rightPriceScale:{borderColor:ct.border}, timeScale:{borderColor:ct.border} });
    const series = _fundChart.addAreaSeries({ lineColor:'#c65a43', topColor:'rgba(198,90,67,.24)', bottomColor:'rgba(198,90,67,0)' });
    series.setData(kline.candles.map(c => ({time:c.date,value:c.close})));
    _fundChart.timeScale().fitContent();
  } else {
    document.getElementById('fund-kline').innerHTML = '<div class="empty-state"><p>可靠K线数据暂不可用</p></div>';
  }
  loadFundRelatedResearch(fund.code, document.getElementById('fund-research-links'));
  const fundInput = document.getElementById('fund-search-input');
  const fundResults = document.getElementById('fund-search-results');
  let fundSearchTimer;
  fundInput?.addEventListener('input', () => {
    clearTimeout(fundSearchTimer);
    const query = fundInput.value.trim();
    if (!query) { fundResults.classList.remove('show'); return; }
    fundSearchTimer = setTimeout(async () => {
      const data = await ROX.api.get(`/api/funds/search?q=${encodeURIComponent(query)}`);
      fundResults.innerHTML = (data?.results || []).map(item => `<button type="button" class="search-result-item" data-fund-code="${ROX.escape(item.code)}">${ROX.escape(item.name || item.code)} <span>${ROX.escape(item.code)}</span></button>`).join('') || '<div class="search-result-item">无匹配基金</div>';
      fundResults.classList.add('show');
    }, 250);
  });
  fundResults?.addEventListener('click', event => {
    const item = event.target.closest('[data-fund-code]');
    if (item) ROX.navigate(`/funds/${item.dataset.fundCode}`);
  });
});

async function loadFundRelatedResearch(code, mount) {
  if (!mount) return;
  const data = await ROX.api.get(`/api/research/related/${encodeURIComponent(code)}`);
  if (!data || data.error) { mount.innerHTML = '<div class="empty-state"><p>关联研究数据暂不可用</p></div>'; return; }
  mount.innerHTML = `<div class="card-header"><div><div class="card-title">研究与决策关联</div><div class="card-subtitle">${data.cards.length} 张研究卡 · ${data.decisions.length} 条决策</div></div><button class="btn btn-secondary btn-sm" data-route="/research/new">新建研究卡</button></div>${data.cards.length ? data.cards.map(card => `<button class="research-link-item" data-route="/research/${card.id}"><strong>${ROX.escape(card.title)}</strong><span>${ROX.escape(card.status_label)}</span></button>`).join('') : '<div class="empty-state"><p>暂无关联研究卡</p></div>'}`;
  mount.querySelectorAll('[data-route]').forEach(item => item.addEventListener('click', () => ROX.navigate(item.dataset.route)));
}
