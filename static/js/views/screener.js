/* ============================================
   视图6 · 选股筛选
   ============================================ */

ROX.register('/screener', async function(container) {
  const [presetsRes] = await Promise.all([
    ROX.api.get('/api/screener/presets'),
  ]);

  if (presetsRes?.status === 'disabled') {
    container.innerHTML = ROX.disabledState(presetsRes?.reason);
    return;
  }

  const presets = presetsRes?.presets || [];

  container.innerHTML = `
    <div class="screener-layout">
      <!-- 条件面板 -->
      <div class="card screener-filters">
        <h3 style="font-size:15px;font-weight:600;margin-bottom:12px;">筛选条件</h3>

        <div class="screener-presets" style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:16px;">
          <button class="btn btn-sm btn-secondary preset-btn active" data-preset="">全部</button>
          ${presets.map(p => `<button class="btn btn-sm btn-secondary preset-btn" data-preset="${p.id}" title="${p.description}">${p.name}</button>`).join('')}
        </div>

        <div class="form-group" style="margin-bottom:10px;">
          <label class="form-label">行业</label>
          <select class="form-input" id="filter-industry">
            <option value="">全部行业</option>
          </select>
        </div>

        <div class="filter-row" style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:10px;">
          <div class="form-group">
            <label class="form-label">PE 下限</label>
            <input class="form-input" type="number" id="filter-pe-min" placeholder="0" step="0.1">
          </div>
          <div class="form-group">
            <label class="form-label">PE 上限</label>
            <input class="form-input" type="number" id="filter-pe-max" placeholder="100" step="0.1">
          </div>
        </div>

        <div class="filter-row" style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:10px;">
          <div class="form-group">
            <label class="form-label">PB 下限</label>
            <input class="form-input" type="number" id="filter-pb-min" placeholder="0" step="0.1">
          </div>
          <div class="form-group">
            <label class="form-label">PB 上限</label>
            <input class="form-input" type="number" id="filter-pb-max" placeholder="20" step="0.1">
          </div>
        </div>

        <div class="filter-row" style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:10px;">
          <div class="form-group">
            <label class="form-label">市值下限(亿)</label>
            <input class="form-input" type="number" id="filter-mc-min" placeholder="0">
          </div>
          <div class="form-group">
            <label class="form-label">市值上限(亿)</label>
            <input class="form-input" type="number" id="filter-mc-max" placeholder="20000">
          </div>
        </div>

        <div class="filter-row" style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:10px;">
          <div class="form-group">
            <label class="form-label">换手率下限(%)</label>
            <input class="form-input" type="number" id="filter-turn-min" placeholder="0" step="0.01">
          </div>
          <div class="form-group">
            <label class="form-label">涨跌幅上限(%)</label>
            <input class="form-input" type="number" id="filter-chg-max" placeholder="10" step="0.01">
          </div>
        </div>

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:12px;">
          <select class="form-input" id="filter-sort">
            <option value="market_cap">按市值排序</option>
            <option value="change_pct">按涨跌幅排序</option>
            <option value="turnover">按换手率排序</option>
            <option value="pe">按PE排序</option>
            <option value="pb">按PB排序</option>
          </select>
          <select class="form-input" id="filter-order">
            <option value="desc">降序</option>
            <option value="asc">升序</option>
          </select>
        </div>

        <button class="btn btn-primary" id="screener-run" data-action="run-screener" style="width:100%;">开始筛选</button>
      </div>

      <!-- 结果区域 -->
      <div class="screener-results" id="screener-results">
        <div class="empty-state">
          <p>设置筛选条件后点击「开始筛选」</p>
          <p style="font-size:12px;color:var(--text-tertiary);">数据源：腾讯自选股公开行情 ｜ 股票池约 70 只热门 A 股</p>
        </div>
      </div>
    </div>
  `;

  // 加载行业列表
  const scanRes = await ROX.api.post('/api/screener/scan', {});
  if (scanRes && scanRes.industries) {
    const sel = document.getElementById('filter-industry');
    scanRes.industries.forEach(ind => {
      const opt = document.createElement('option');
      opt.value = ind; opt.textContent = ind;
      sel.appendChild(opt);
    });
    // 直接展示首次扫描结果
    renderResults(scanRes);
  }

  // 预设按钮
  let activePreset = '';
  document.querySelectorAll('.preset-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      activePreset = btn.dataset.preset;
    });
  });

  // 运行筛选
  const runBtn = document.getElementById('screener-run');
  if (runBtn) {
    runBtn.addEventListener('click', async () => {
      runBtn.disabled = true;
      runBtn.textContent = '筛选中…';
      document.getElementById('screener-results').innerHTML = '<div class="loading"><div class="spinner"></div></div>';

      const filters = {};
      const fi = id => { const v = document.getElementById(id)?.value; return v === '' || v === undefined ? null : parseFloat(v); };
      const peMin = fi('filter-pe-min'); if (peMin !== null) filters.pe_min = peMin;
      const peMax = fi('filter-pe-max'); if (peMax !== null) filters.pe_max = peMax;
      const pbMin = fi('filter-pb-min'); if (pbMin !== null) filters.pb_min = pbMin;
      const pbMax = fi('filter-pb-max'); if (pbMax !== null) filters.pb_max = pbMax;
      const mcMin = fi('filter-mc-min'); if (mcMin !== null) filters.market_cap_min = mcMin;
      const mcMax = fi('filter-mc-max'); if (mcMax !== null) filters.market_cap_max = mcMax;
      const turnMin = fi('filter-turn-min'); if (turnMin !== null) filters.turnover_min = turnMin;
      const chgMax = fi('filter-chg-max'); if (chgMax !== null) filters.change_pct_max = chgMax;
      const industry = document.getElementById('filter-industry')?.value;
      if (industry) filters.industry = industry;

      const sortBy = document.getElementById('filter-sort')?.value || 'market_cap';
      const sortDesc = document.getElementById('filter-order')?.value === 'desc';

      const params = new URLSearchParams();
      if (activePreset) params.set('preset', activePreset);
      params.set('sort_by', sortBy);
      params.set('sort_desc', sortDesc);
      params.set('limit', '50');

      const res = await ROX.api.post(`/api/screener/scan?${params}`, filters);
      runBtn.disabled = false;
      runBtn.textContent = '开始筛选';

      if (res && !res.error) {
        renderResults(res);
      } else {
        document.getElementById('screener-results').innerHTML = '<div class="empty-state"><p>筛选失败，请重试</p></div>';
      }
    });
  }

  function renderResults(res) {
    const el = document.getElementById('screener-results');
    if (!res.results || res.results.length === 0) {
      el.innerHTML = '<div class="empty-state"><p>没有符合条件的股票</p><p style="font-size:12px;color:var(--text-tertiary);">尝试放宽筛选条件</p></div>';
      return;
    }

    el.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
        <span style="font-size:13px;color:var(--text-secondary);">共 ${res.total} 只符合条件（股票池 ${res.pool_size} 只）</span>
        <span style="font-size:11px;color:var(--text-tertiary);">${res.data_source}</span>
      </div>
      <div class="table-wrap" style="overflow-x:auto;">
        <table class="data-table" style="width:100%;font-size:13px;">
          <thead>
            <tr>
              <th style="text-align:left;">名称/代码</th>
              <th style="text-align:right;">最新价</th>
              <th style="text-align:right;">涨跌幅</th>
              <th style="text-align:right;">PE</th>
              <th style="text-align:right;">PB</th>
              <th style="text-align:right;">市值(亿)</th>
              <th style="text-align:right;">换手率</th>
              <th style="text-align:left;">行业</th>
            </tr>
          </thead>
          <tbody>
            ${res.results.map(s => `
              <tr class="screener-row" data-code="${s.code}" style="cursor:pointer;">
                <td>
                  <div style="font-weight:600;">${ROX.escape(s.name)}</div>
                  <div style="font-size:11px;color:var(--text-tertiary);font-family:var(--font-mono);">${s.code}</div>
                </td>
                <td style="text-align:right;font-family:var(--font-mono);">${ROX.fmt.num(s.price)}</td>
                <td style="text-align:right;font-family:var(--font-mono);" class="${ROX.fmt.color(s.change_pct)}">${ROX.fmt.pct(s.change_pct)}</td>
                <td style="text-align:right;font-family:var(--font-mono);">${s.pe > 0 ? ROX.fmt.num(s.pe, 1) : '--'}</td>
                <td style="text-align:right;font-family:var(--font-mono);">${s.pb > 0 ? ROX.fmt.num(s.pb, 2) : '--'}</td>
                <td style="text-align:right;font-family:var(--font-mono);">${ROX.fmt.num(s.market_cap, 0)}</td>
                <td style="text-align:right;font-family:var(--font-mono);">${ROX.fmt.num(s.turnover)}%</td>
                <td><span class="tag tag-gray">${ROX.escape(s.industry || '--')}</span></td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
      <p style="font-size:11px;color:var(--text-tertiary);margin-top:8px;">${res.disclaimer}</p>
    `;

    // 行点击进入个股页
    el.querySelectorAll('.screener-row').forEach(row => {
      row.addEventListener('click', () => {
        const code = row.dataset.code;
        if (code) ROX.navigate(`/stock/${code}`);
      });
    });
  }
});
