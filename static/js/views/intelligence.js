/* ============================================
   视图5 · 宏观情报
   公开资讯 → 传导路径 → 交叉验证
   ============================================ */

ROX.register('/intelligence', async function(container) {
  const data = await ROX.api.get('/api/intelligence/brief');
  if (!data) {
    container.innerHTML = '<div class="empty-state"><p>情报简报加载失败，请稍后刷新。</p></div>';
    return;
  }

  const directionClass = direction => ({ positive: 'tag-red', warning: 'tag-amber', neutral: 'tag-gray' }[direction] || 'tag-gray');
  const flowClass = flow => flow === 'inflow' ? 'text-up' : 'text-down';

  container.innerHTML = `
    <div style="display:flex;flex-direction:column;gap:16px;">
      <div class="card intelligence-lead">
        <div class="card-header">
          <div>
            <div class="card-title">宏观情报工作台</div>
            <div class="card-subtitle">公开资讯 · 政策传导 · 全球宏观 · 行业资金流</div>
          </div>
          <button class="btn btn-secondary btn-sm" data-action="refresh-intelligence">刷新资讯</button>
        </div>
        <div class="intelligence-disclaimer">${data.disclaimer}</div>
        <div style="margin-top:10px;font-size:11px;color:var(--text-tertiary);">数据状态：${data.source_status} · 更新于 ${new Date(data.updated_at).toLocaleString('zh-CN')}</div>
      </div>

      <div class="grid-2">
        <div class="card">
          <div class="card-header"><div class="card-title">全球宏观风险地图</div><span class="tag tag-amber">传导观察</span></div>
          <div class="risk-list">
            ${data.global_risk.map(item => `
              <div class="risk-row">
                <div class="risk-score ${item.direction}">${item.score}</div>
                <div style="min-width:0;flex:1;">
                  <div style="display:flex;justify-content:space-between;gap:8px;"><span class="risk-factor">${item.factor}</span><span class="tag ${directionClass(item.direction)}">${item.status}</span></div>
                  <div class="risk-transmission">${item.transmission}</div>
                  <div class="risk-watch">观察：${item.watch}</div>
                </div>
              </div>`).join('')}
          </div>
        </div>
        <div class="card">
          <div class="card-header"><div class="card-title">政策传导跟踪</div><span class="tag tag-blue">公开信息</span></div>
          <div style="display:flex;flex-direction:column;gap:10px;">
            ${data.policy_tracker.map(item => `
              <div class="policy-row">
                <div style="display:flex;justify-content:space-between;gap:8px;"><span class="policy-topic">${item.topic}</span><span class="tag ${item.signal === '正向' ? 'tag-red' : 'tag-amber'}">${item.stage}</span></div>
                <div class="policy-affected">影响行业：${item.affected.join('、')}</div>
                <div class="policy-method">研判方法：${item.method}</div>
              </div>`).join('')}
          </div>
        </div>
      </div>

      <div class="grid-2">
        <div class="card">
          <div class="card-header"><div class="card-title">行业资金与景气线索</div><span class="tag tag-gray">需交叉确认</span></div>
          <div style="display:flex;flex-direction:column;gap:2px;">
            ${data.sector_flow.map(item => `
              <div class="sector-flow-row">
                <div><div class="stock-name">${item.sector}</div><div class="stock-code">${item.driver}</div></div>
                <div class="${flowClass(item.trend)}" style="font-family:var(--font-mono);font-weight:600;">${item.flow > 0 ? '+' : ''}${item.flow.toFixed(1)} 亿</div>
              </div>`).join('')}
          </div>
        </div>
        <div class="card">
          <div class="card-header"><div class="card-title">资讯研判纪律</div><span class="tag tag-green">方法优先</span></div>
          <ol class="intelligence-method">
            ${data.method.map((item, index) => `<li><span>${String(index + 1).padStart(2, '0')}</span>${item}</li>`).join('')}
          </ol>
        </div>
      </div>

      <div class="card">
        <div class="card-header"><div class="card-title">资讯与事件线索</div><span class="tag tag-blue">${data.news.length} 条</span></div>
        <div class="news-list">
          ${data.news.map(item => `
            <article class="news-row">
              <div class="news-meta"><span class="tag ${directionClass(item.direction)}">${item.category}</span><span>${item.fact_or_view}</span></div>
              <div class="news-title">${item.title}</div>
              <div class="news-detail">传导方向：${item.channels.join('、')} · ${item.evidence}</div>
              <div class="news-source">${item.source} · ${new Date(item.published_at).toLocaleString('zh-CN')}</div>
            </article>`).join('')}
        </div>
      </div>
    </div>`;
});
