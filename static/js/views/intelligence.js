/* ============================================
   视图5 · 宏观情报
   公开资讯 → 传导路径 → 交叉验证
   ============================================ */

ROX.register('/intelligence', async function(container) {
  let data = await ROX.api.get('/api/intelligence/feed');
  if (!data || data.error) data = await ROX.api.get('/api/intelligence/brief');
  if (!data) {
    container.innerHTML = '<div class="empty-state"><p>情报简报加载失败，请稍后刷新。</p></div>';
    return;
  }

  const directionClass = direction => ({ positive: 'tag-red', warning: 'tag-amber', neutral: 'tag-gray' }[direction] || 'tag-gray');
  const flowClass = flow => flow === 'inflow' ? 'text-up' : 'text-down';

  container.innerHTML = `
    <div class="intelligence-page" style="display:flex;flex-direction:column;gap:16px;">
      <div class="card intelligence-lead">
        <div class="card-header">
          <div>
            <div class="card-title">宏观情报工作台</div>
            <div class="card-subtitle">公开资讯 · 政策传导 · 全球宏观 · 行业资金流</div>
          </div>
          <button class="btn btn-secondary btn-sm" data-action="refresh-intelligence">刷新资讯</button>
        </div>
        <div class="intelligence-disclaimer">${data.disclaimer}</div>
        <div class="intelligence-source-line"><span class="evidence-badge is-live"><i></i>公开信息</span><span>来源：${data.source_status}</span><span>更新于 ${new Date(data.updated_at).toLocaleString('zh-CN')}</span></div>
      </div>

      <div class="card intelligence-map-card">
        <div class="card-header"><div><div class="card-title">一条线看懂当前情报</div><div class="card-subtitle">事件 → 传导 → 行业 → 验证动作</div></div><span class="tag tag-gray">研究连接器</span></div>
        <div class="intelligence-map">
          <div><b>事实线索</b><span>政策、全球变量、资讯</span></div><i>→</i>
          <div><b>传导路径</b><span>利率 / 汇率 / 能源 / 订单</span></div><i>→</i>
          <div><b>行业影响</b><span>盈利、估值、资金流</span></div><i>→</i>
          <div><b>验证动作</b><span>至少两项独立数据确认</span></div>
        </div>
      </div>

      ${(data.themes?.length || 0) > 1 ? `
      <div class="card intelligence-theme-card">
        <div class="card-header">
          <div><div class="card-title">主题主线</div><div class="card-subtitle">同一主题的资讯按时间线聚合：起因 → 发展 → 当前 · ${ROX.escape(data.sort_rule || '按重要度排序，无情绪分')}</div></div>
          <span class="tag tag-gray">${data.themes.length} 个主题</span>
        </div>
        <div class="intelligence-theme-grid">
          ${data.themes.slice(0, 6).map(theme => `
            <details class="intelligence-theme"${theme.has_breaking ? ' data-breaking="1"' : ''}>
              <summary>
                <span class="intelligence-theme-name">${ROX.escape(theme.name)}</span>
                <span class="intelligence-theme-badges">
                  ${theme.has_breaking ? '<span class="tag tag-red">突发</span>' : ''}
                  ${theme.research_hits ? `<span class="tag tag-blue">研究相关 ×${theme.research_hits}</span>` : ''}
                  <span class="tag tag-gray">${theme.count} 条</span>
                </span>
              </summary>
              <div class="intelligence-theme-body">
                <div class="intelligence-theme-meta">影响行业：${theme.industries.slice(0, 6).map(i => ROX.escape(i)).join('、') || '未归类'}${theme.newest_hours != null ? ` · 最近更新 ${theme.newest_hours} 小时前` : ''}</div>
                <ol class="intelligence-theme-timeline">
                  ${theme.timeline.map(item => `<li><span class="intelligence-theme-time">${ROX.escape(String(item.published_at || '').slice(5, 16))}</span><span>${ROX.escape(item.title)}</span></li>`).join('')}
                </ol>
                <div class="intelligence-theme-verify">仍需验证：${ROX.escape(theme.verify_question)}</div>
                ${theme.policy_topics?.length ? `<div class="intelligence-theme-meta">关联政策：${[...new Set(theme.policy_topics)].map(t => ROX.escape(t)).join('、')}</div>` : ''}
                <button class="evidence-add-btn" data-action="open-evidence-drawer" data-title="${ROX.escape(`主题：${theme.name}`)}" data-content="${ROX.escape(`主题线索：${theme.name}（${theme.count} 条资讯聚合，影响行业：${theme.industries.slice(0, 4).join('、')}）`)}" data-source="${ROX.escape(data.source_status || '主题主线')}" data-as-of="${ROX.escape(String(data.updated_at || '').slice(0, 16))}">＋ 把主题加入研究卡</button>
              </div>
            </details>`).join('')}
        </div>
      </div>` : ''}

      <div class="grid-2 intelligence-section-grid">
        <div class="card">
          <div class="card-header"><div><div class="card-title">全球宏观风险地图</div><div class="card-subtitle">外部变量如何进入行业利润</div></div><span class="tag tag-amber">传导观察</span></div>
          <div class="risk-list">
            ${data.global_risk.map(item => `
              <div class="risk-row">
                <div class="risk-score ${item.direction}">${item.score}</div>
                <div style="min-width:0;flex:1;">
                  <div style="display:flex;justify-content:space-between;gap:8px;"><span class="risk-factor">${item.factor}</span><span class="tag ${directionClass(item.direction)}">${item.status}</span></div>
                  <div class="risk-transmission">${item.transmission}</div>
                  <div class="risk-watch">观察：${item.watch}</div>
                  <button class="evidence-add-btn" data-action="open-evidence-drawer" data-title="${ROX.escape(item.factor)}" data-content="${ROX.escape(`${item.factor}：${item.transmission}（观察：${item.watch}）`)}" data-source="${ROX.escape(data.source_status || '宏观情报')}" data-as-of="${ROX.escape(new Date(data.updated_at).toLocaleString('zh-CN'))}">＋ 加入研究卡</button>
                </div>
              </div>`).join('')}
          </div>
        </div>
        <div class="card">
          <div class="card-header"><div><div class="card-title">政策传导跟踪</div><div class="card-subtitle">政策状态 → 受影响行业 → 验证方法</div></div><span class="tag tag-blue">事实线索</span></div>
          <div style="display:flex;flex-direction:column;gap:10px;">
            ${data.policy_tracker.map(item => `
              <div class="policy-row">
                <div style="display:flex;justify-content:space-between;gap:8px;"><span class="policy-topic">${item.topic}</span><span class="tag ${item.signal === '正向' ? 'tag-red' : 'tag-amber'}">${item.stage}</span></div>
                <div class="policy-affected">影响行业：${item.affected.join('、')}</div>
                <div class="policy-method">研判方法：${item.method}</div>
                <button class="evidence-add-btn" data-action="open-evidence-drawer" data-title="${ROX.escape(item.topic)}" data-content="${ROX.escape(`政策线索：${item.topic}（${item.stage}，影响行业：${item.affected.join('、')}）`)}" data-source="${ROX.escape(data.source_status || '政策跟踪')}" data-as-of="${ROX.escape(new Date(data.updated_at).toLocaleString('zh-CN'))}">＋ 加入研究卡</button>
              </div>`).join('')}
          </div>
        </div>
      </div>

      <div class="grid-2 intelligence-section-grid">
        <div class="card">
          <div class="card-header"><div><div class="card-title">行业资金与景气线索</div><div class="card-subtitle">资金变化不是结论，需要第二证据</div></div><span class="tag tag-amber">待验证</span></div>
          <div style="display:flex;flex-direction:column;gap:2px;">
            ${data.sector_flow.map(item => `
              <div class="sector-flow-row">
                <div><div class="stock-name">${item.sector}</div><div class="stock-code">${item.driver}</div></div>
                <div style="display:flex;align-items:center;gap:8px;">
                  <div class="${flowClass(item.trend)}" style="font-family:var(--font-mono);font-weight:600;">${item.flow > 0 ? '+' : ''}${item.flow.toFixed(1)} 亿</div>
                  <button class="evidence-add-btn" style="margin-top:0;" data-action="open-evidence-drawer" data-title="${ROX.escape(item.sector)}" data-content="${ROX.escape(`行业资金流：${item.sector} ${item.flow > 0 ? '+' : ''}${item.flow.toFixed(1)} 亿（驱动：${item.driver}）`)}" data-source="${ROX.escape(data.source_status || '行业资金流')}" data-as-of="${ROX.escape(new Date(data.updated_at).toLocaleString('zh-CN'))}">＋</button>
                </div>
              </div>`).join('')}
          </div>
        </div>
        <div class="card">
          <div class="card-header"><div><div class="card-title">资讯研判纪律</div><div class="card-subtitle">把资讯转成可执行验证</div></div><span class="tag tag-green">行动规则</span></div>
          <ol class="intelligence-method">
            ${data.method.map((item, index) => `<li><span>${String(index + 1).padStart(2, '0')}</span>${item}</li>`).join('')}
          </ol>
        </div>
      </div>

      <div class="card intelligence-news-card">
        <div class="card-header"><div><div class="card-title">资讯与事件线索</div><div class="card-subtitle">原始标题只生成假设，不直接生成结论 · 突发=36小时内命中关键事件词，仅提示核对</div></div><span class="tag tag-blue">${data.news.length} 条</span></div>
        <div class="news-list">
          ${data.news.map(item => `
            <article class="news-row ${item.is_breaking ? 'news-breaking' : ''}">
              <div class="news-meta">
                ${item.is_breaking ? '<span class="tag tag-red">突发</span>' : ''}
                ${item.research_relevant?.length ? `<span class="tag tag-blue">研究相关：${item.research_relevant.map(ROX.escape).join('、')}</span>` : ''}
                <span class="tag ${directionClass(item.direction)}">${item.category}</span><span>${item.fact_or_view}</span>
              </div>
              <div class="news-title">${item.title}</div>
              <div class="news-detail">传导方向：${item.channels.join('、')} · ${item.evidence}</div>
              <div class="news-source">${item.source} · ${new Date(item.published_at).toLocaleString('zh-CN')}</div>
              <button class="evidence-add-btn" data-action="open-evidence-drawer" data-title="${ROX.escape(item.title)}" data-content="${ROX.escape(`${item.title}（${item.fact_or_view}；传导：${item.channels.join('、')}）`)}" data-source="${ROX.escape(item.source || '')}" data-as-of="${ROX.escape(new Date(item.published_at).toLocaleString('zh-CN'))}">＋ 加入研究卡（事实/反证/待验证）</button>
            </article>`).join('')}
        </div>
      </div>
    </div>`;
});
