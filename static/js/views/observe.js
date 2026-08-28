/* 研究对象观察台：自选、行情、研究卡与决策流联动。 */

let _observeChart = null;

function disposeObserveChart() {
  _observeChart?.remove?.();
  _observeChart?.dispose?.();
  _observeChart = null;
}

window.addEventListener('resize', () => {
  const el = document.getElementById('observe-chart');
  if (!_observeChart || !el) return;
  if (typeof _observeChart.resize === 'function') _observeChart.resize(el.clientWidth, el.clientHeight);
});

function observeListHTML(items, selectedCode) {
  if (!items.length) {
    return `<div class="observe-empty">
      <p>还没有观察对象。</p>
      <button class="btn btn-secondary btn-sm" data-route="/stock">先从个股页加入自选</button>
    </div>`;
  }
  return items.map(item => {
    const active = item.code === selectedCode;
    const changed = item.change_pct ?? 0;
    return `<button class="observe-item${active ? ' active' : ''}" data-code="${ROX.escape(item.code)}">
      <span class="observe-item-name">${ROX.escape(item.price_name || item.name)}</span>
      <span class="observe-item-code">${ROX.escape(item.code)}</span>
      <span class="observe-item-price">${item.price != null ? ROX.fmt.num(item.price) : '--'}</span>
      <span class="observe-item-change">${item.change_pct != null ? ROX.fmt.pct(changed) : '--'}</span>
    </button>`;
  }).join('');
}

function observeResearchHTML(data) {
  const cards = data?.cards || [];
  const decisions = data?.decisions || [];
  const cardItems = cards.length ? cards.slice(0, 5).map(card => `
    <button class="observe-stream-item" data-route="/research/${card.id}">
      <strong>${ROX.escape(card.title)}</strong>
      <span>${ROX.escape(card.status_label || card.status)} · 证据 ${card.evidence_counts?.facts ?? 0} / 反证 ${card.evidence_counts?.counter ?? 0}</span>
    </button>`).join('') : '<div class="observe-stream-empty">暂无关联研究卡</div>';
  const decisionItems = decisions.length ? decisions.slice(0, 5).map(item => `
    <button class="observe-stream-item" data-route="/journal">
      <strong>${ROX.escape(item.date)} · ${ROX.escape(item.action)}</strong>
      <span>${ROX.escape(item.result)}${item.result_pct != null ? ` · ${ROX.fmt.pct(item.result_pct)}` : ''}</span>
    </button>`).join('') : '<div class="observe-stream-empty">暂无关联决策</div>';
  return `
    <div class="observe-stream-section"><div class="observe-stream-title">研究卡 <b>${cards.length}</b></div>${cardItems}</div>
    <div class="observe-stream-section"><div class="observe-stream-title">决策流 <b>${decisions.length}</b></div>${decisionItems}</div>
  `;
}

function renderObserveChart(candles) {
  const el = document.getElementById('observe-chart');
  if (!el) return;
  disposeObserveChart();
  if (!window.LightweightCharts || !candles?.length) {
    el.innerHTML = '<div class="empty-state"><p>可靠K线数据暂不可用</p></div>';
    return;
  }
  _observeChart = LightweightCharts.createChart(el, {
    layout: { background: { color: 'transparent' }, textColor: ROX.chartTheme().text },
    grid: { vertLines: { color: ROX.chartTheme().grid }, horzLines: { color: ROX.chartTheme().grid } },
    rightPriceScale: { borderColor: ROX.chartTheme().border },
    timeScale: { borderColor: ROX.chartTheme().border, timeVisible: false },
    crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
  });
  const series = _observeChart.addAreaSeries({ lineWidth: 2 });
  series.setData(candles.map(item => ({ time: item.date, value: item.close })));
  _observeChart.timeScale().fitContent();
  requestAnimationFrame(() => _observeChart?.resize(el.clientWidth, el.clientHeight));
}

ROX.register('/observe', async function(container, params) {
  container.innerHTML = '<div class="observe-page"><div class="loading"><div class="spinner"></div></div></div>';
  const watchData = await ROX.api.get('/api/watchlist/');
  const items = watchData?.watchlist || [];
  const selected = items.find(item => item.code === params.query?.code) || items[0];

  if (!selected) {
    container.innerHTML = `
      <div class="observe-page">
        <div class="research-page-head"><div><div class="eyebrow">ROX / WATCHDECK</div>
          <h2 class="research-page-title">研究对象观察台</h2>
          <p class="research-page-subtitle">把自选对象、价格事实、研究卡和决策放在同一屏。</p></div></div>
        <div class="card observe-empty-state">${observeListHTML([], '')}</div>
      </div>`;
    return;
  }

  container.innerHTML = `
    <div class="observe-page">
      <div class="research-page-head">
        <div><div class="eyebrow">ROX / WATCHDECK</div>
          <h2 class="research-page-title">研究对象观察台</h2>
          <p class="research-page-subtitle">从观察对象进入研究，不让行情和判断分开。</p></div>
        <button class="btn btn-secondary" data-route="/research">研究卡列表</button>
      </div>
      <div class="observe-layout">
        <aside class="observe-side card" aria-label="观察对象"><div class="observe-side-title">观察对象 <b>${items.length}</b></div>${observeListHTML(items, selected.code)}</aside>
        <main class="observe-main">
          <section class="card observe-hero">
            <div class="observe-hero-main">
              <div><div class="observe-name">${ROX.escape(selected.price_name || selected.name)}</div>
                <div class="observe-code">${ROX.escape(selected.code)}</div></div>
              <div class="observe-price"><strong>${selected.price != null ? ROX.fmt.num(selected.price) : '--'}</strong>
                <span>${selected.change_pct != null ? ROX.fmt.pct(selected.change_pct) : '--'}</span></div>
            </div>
            <div class="observe-hero-actions">
              <button class="btn btn-primary btn-sm" data-action="create-research-card" data-code="${ROX.escape(selected.code)}" data-name="${ROX.escape(selected.name)}">开始研究</button>
              <button class="btn btn-secondary btn-sm" data-action="add-decision" data-code="${ROX.escape(selected.code)}" data-name="${ROX.escape(selected.name)}">记录决策</button>
              <button class="btn btn-secondary btn-sm" data-route="/stock/${ROX.escape(selected.code)}">完整透视</button>
            </div>
          </section>
          <section class="card observe-chart-card"><div class="observe-panel-title">价格观察</div><div id="observe-chart" class="observe-chart"></div><div class="observe-chart-note">K线为真实市场数据；不可用时不会用估算值填充。</div></section>
        </main>
        <aside class="observe-stream card" aria-label="研究与决策"><div class="observe-side-title">研究与决策</div><div id="observe-stream"><div class="loading"><div class="spinner"></div></div></div></aside>
      </div>
    </div>`;

  const loadDetail = async () => {
    const [research, kline] = await Promise.all([
      ROX.api.get(`/api/research/related/${encodeURIComponent(selected.code)}`),
      ROX.api.get(`/api/stock/${encodeURIComponent(selected.code)}/kline`),
    ]);
    document.getElementById('observe-stream').innerHTML = observeResearchHTML(research);
    renderObserveChart(kline?.candles || []);
  };
  await loadDetail();

  container.querySelectorAll('.observe-item').forEach(button => {
    button.addEventListener('click', () => ROX.navigate(`/observe?code=${encodeURIComponent(button.dataset.code)}`));
  });
  container.querySelectorAll('[data-route]').forEach(button => button.addEventListener('click', () => ROX.navigate(button.dataset.route)));
});
