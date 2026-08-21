/* ============================================
   视图4 · 认知框架
   ============================================ */

ROX.register('/framework', async function(container) {
  const data = await ROX.api.get('/api/framework/methodology');
  if (!data) {
    container.innerHTML = '<div class="empty-state"><p>数据加载失败</p></div>';
    return;
  }

  container.innerHTML = `
    <div style="display:flex;flex-direction:column;gap:16px;">
      <div class="tabs">
        <div class="tab active" data-fw-tab="methodology">方法论</div>
        <div class="tab" data-fw-tab="strategies">策略库</div>
        <div class="tab" data-fw-tab="knowledge">知识库</div>
      </div>
      <div id="fw-content"></div>
    </div>
  `;

  // Default: methodology
  renderMethodology(data);

  // Tab switching
  container.querySelectorAll('[data-fw-tab]').forEach(tab => {
    tab.addEventListener('click', () => {
      container.querySelectorAll('[data-fw-tab]').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      const target = tab.dataset.fwTab;
      if (target === 'methodology') renderMethodology(data);
      else if (target === 'strategies') renderStrategies();
      else if (target === 'knowledge') renderKnowledge();
    });
  });
});

function renderMethodology(data) {
  const el = document.getElementById('fw-content');

  // Find current stage info
  const cycleLayer = data.layers.find(l => l.level === 'L2');
  const contradictionLayer = data.layers.find(l => l.level === 'L3');
  const disciplineLayer = data.layers.find(l => l.level === 'L4');
  const scoreLayer = data.layers.find(l => l.level === 'L5');

  el.innerHTML = `
    <div class="grid-2" style="gap:16px;">
      ${data.layers.map(layer => `
        <div class="methodology-card">
          <div style="display:flex;align-items:center;gap:8px;">
            <span class="methodology-level">${layer.level}</span>
            <span class="tag tag-blue">${layer.name}</span>
          </div>
          <div class="methodology-title">${ROX.escape(layer.title)}</div>
          <div class="methodology-summary">${ROX.escape(layer.summary)}</div>
          <details class="methodology-detail" style="margin-top:10px;">
            <summary>展开完整框架</summary>
            <div class="methodology-detail-body">
              ${layer.rule ? `<div><strong>核心规则</strong><p>${ROX.escape(layer.rule)}</p></div>` : ''}
              ${layer.observation_targets ? `<div><strong>观察目标</strong><div class="methodology-observations">${layer.observation_targets.map(item => `<span class="tag tag-gray">${ROX.escape(item)}</span>`).join('')}</div></div>` : ''}
              ${layer.matrix ? `<div><strong>矩阵规则</strong><div class="methodology-rule-list">${layer.matrix.rules.map(item => `<div><b>${ROX.escape(item.cell)}</b><span>${ROX.escape(item.action)} · ${ROX.escape(item.desc)}</span></div>`).join('')}</div></div>` : ''}
              ${layer.contradiction_types ? `<div><strong>矛盾类型</strong><div class="methodology-rule-list">${layer.contradiction_types.map(item => `<div><b>${ROX.escape(item.name)}</b><span>${ROX.escape(item.desc)} · 例：${ROX.escape(item.example)}</span></div>`).join('')}</div></div>` : ''}
              ${layer.three_pools ? `<div><strong>三池分配</strong><div class="methodology-rule-list">${layer.three_pools.map(item => `<div><b>${ROX.escape(item.name)} ${ROX.escape(item.ratio)}</b><span>${ROX.escape(item.desc)} · ${ROX.escape(item.rule)}</span></div>`).join('')}</div></div>` : ''}
              ${layer.position_334 ? `<div><strong>三段建仓</strong><div class="methodology-rule-list">${layer.position_334.map(item => `<div><b>${ROX.escape(item.name)} ${ROX.escape(item.ratio)}</b><span>${ROX.escape(item.trigger)} · ${ROX.escape(item.rule)}</span></div>`).join('')}</div></div>` : ''}
              ${layer.dimensions ? `<div><strong>评分维度</strong><div class="methodology-rule-list">${layer.dimensions.map(item => `<div><b>${ROX.escape(item.name)} ${item.weight}%</b><span>${ROX.escape(item.desc)} · ${ROX.escape(item.scoring)}</span></div>`).join('')}</div></div>` : ''}
            </div>
          </details>

          ${layer.key_concepts ? `
            <div class="methodology-concepts">
              ${layer.key_concepts.map(c => `<span class="tag tag-gray">${c}</span>`).join('')}
            </div>
          ` : ''}

          ${layer.indicators ? `
            <div style="display:flex;flex-direction:column;gap:8px;margin-top:4px;">
              ${layer.indicators.map(ind => `
                <div>
                  <div style="display:flex;justify-content:space-between;font-size:11px;margin-bottom:3px;">
                    <span style="color:var(--text-secondary);">${ind.name}</span>
                    <span style="color:var(--text-tertiary);">${ind.value}${ind.score != null ? ` (${ind.score})` : ''}</span>
                  </div>
                  ${ind.score != null ? `<div class="progress"><div class="progress-fill amber" style="width:${ind.score}%"></div></div>` : `<div style="font-size:10px;color:var(--text-muted);">${ind.detail}</div>`}
                </div>
              `).join('')}
            </div>
          ` : ''}

          ${layer.stages ? `
            <div class="cycle-stages" style="margin-top:8px;">
              ${layer.stages.map((s, i) => `
                <div class="cycle-stage ${layer.current_stage != null && i === layer.current_stage ? 'active' : layer.current_stage != null && i < layer.current_stage ? 'passed' : ''}">
                  ${s.name}
                </div>
              `).join('')}
            </div>
            ${layer.current_stage != null ? `
              <div style="font-size:11px;color:var(--text-tertiary);margin-top:6px;">当前阶段：${layer.stages[layer.current_stage]?.name} — ${layer.stages[layer.current_stage]?.desc}</div>
              <div style="font-size:11px;color:var(--rox-primary);margin-top:4px;">策略建议：${layer.stages[layer.current_stage]?.strategy}</div>
            ` : `<div style="font-size:11px;color:var(--ink-warn);margin-top:6px;">当前阶段未评估：缺少可靠实时宏观数据</div>`}
          ` : ''}

          ${layer.current ? `
            <div style="display:flex;flex-direction:column;gap:6px;margin-top:4px;">
              ${layer.current.primary ? `
                <div>
                  <div style="font-size:11px;color:var(--text-secondary);">主要矛盾</div>
                  <div style="font-size:12px;color:var(--text-primary);">${layer.current.primary.name}</div>
                  <div class="progress" style="margin-top:3px;"><div class="progress-fill red" style="width:${layer.current.primary.intensity}%"></div></div>
                </div>
              ` : ''}
              ${layer.current.secondary ? `
                <div>
                  <div style="font-size:11px;color:var(--text-secondary);">次要矛盾</div>
                  <div style="font-size:12px;color:var(--text-primary);">${layer.current.secondary.name}</div>
                  <div class="progress" style="margin-top:3px;"><div class="progress-fill amber" style="width:${layer.current.secondary.intensity}%"></div></div>
                </div>
              ` : ''}
              ${layer.current.core ? `
                <div class="discipline-bar" style="margin-top:4px;">
                  <div class="discipline-segment discipline-core" style="width:${layer.current.core.actual}%;">核心 ${layer.current.core.actual}%</div>
                  <div class="discipline-segment discipline-satellite" style="width:${layer.current.satellite.actual}%;">卫星 ${layer.current.satellite.actual}%</div>
                  <div class="discipline-segment discipline-cash" style="width:${layer.current.cash.actual}%;">现金 ${layer.current.cash.actual}%</div>
                </div>
                <div style="font-size:10px;color:var(--text-tertiary);">基准：30% / 30% / 40%</div>
              ` : ''}
            </div>
          ` : ''}

          ${layer.dimensions ? `
            <div style="display:flex;flex-direction:column;gap:6px;margin-top:4px;">
              ${layer.dimensions.map(d => `
                <div style="display:flex;align-items:center;gap:8px;">
                  <span style="font-size:12px;color:var(--text-primary);min-width:80px;">${d.name}</span>
                  <div class="progress" style="flex:1;"><div class="progress-fill blue" style="width:${d.weight}%"></div></div>
                  <span style="font-size:11px;font-family:var(--font-mono);color:var(--text-tertiary);min-width:30px;text-align:right;">${d.weight}%</span>
                </div>
              `).join('')}
            </div>
          ` : ''}

          ${layer.skill ? `
            <details class="methodology-skill" style="margin-top:10px;">
              <summary style="cursor:pointer;font-size:11px;color:var(--text-secondary);font-weight:500;">执行方法 · 触发 · 边界</summary>
              <div style="margin-top:8px;display:flex;flex-direction:column;gap:6px;font-size:11px;line-height:1.6;">
                <div><span style="color:var(--text-tertiary);">触发：</span><span style="color:var(--text-primary);">${layer.skill.trigger}</span></div>
                <ol style="margin:0;padding-left:16px;color:var(--text-secondary);">
                  ${layer.skill.steps.map(st => `<li>${st}</li>`).join('')}
                </ol>
                <div><span style="color:var(--ink-warn);">边界：</span><span style="color:var(--text-secondary);">${layer.skill.boundary}</span></div>
              </div>
            </details>
          ` : ''}
        </div>
      `).join('')}
    </div>
  `;
}

async function renderStrategies() {
  const el = document.getElementById('fw-content');
  const data = await ROX.api.get('/api/framework/strategies');
  if (!data) { el.innerHTML = '<p>加载失败</p>'; return; }

  el.innerHTML = `
    <div style="display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap;">
      <button class="btn btn-secondary btn-sm fw-stage-filter" data-stage="">全部</button>
      <button class="btn btn-secondary btn-sm fw-stage-filter" data-stage="积累">积累</button>
      <button class="btn btn-secondary btn-sm fw-stage-filter" data-stage="集中">集中</button>
      <button class="btn btn-secondary btn-sm fw-stage-filter" data-stage="流转">流转</button>
      <button class="btn btn-secondary btn-sm fw-stage-filter" data-stage="分配">分配</button>
    </div>
    <div class="grid-2" id="strategies-grid">
      ${data.strategies.map(s => `
        <div class="card" style="cursor:pointer;">
          <div style="display:flex;justify-content:space-between;align-items:start;margin-bottom:8px;">
            <div style="font-size:14px;font-weight:600;">${s.name}</div>
            <span class="tag tag-blue">${s.stage}</span>
          </div>
          <div style="display:flex;gap:6px;margin-bottom:8px;">
            <span class="tag tag-gray">${s.style}</span>
            <span class="tag tag-gray">${s.targets} 只标的</span>
          </div>
          <div style="font-size:12px;color:var(--text-secondary);line-height:1.6;">${s.desc}</div>
        </div>
      `).join('')}
    </div>
  `;

  el.querySelectorAll('.fw-stage-filter').forEach(btn => {
    btn.addEventListener('click', async () => {
      const stage = btn.dataset.stage;
      const url = stage ? `/api/framework/strategies?stage=${encodeURIComponent(stage)}` : '/api/framework/strategies';
      const d = await ROX.api.get(url);
      if (!d) return;
      const grid = document.getElementById('strategies-grid');
      grid.innerHTML = d.strategies.map(s => `
        <div class="card" style="cursor:pointer;">
          <div style="display:flex;justify-content:space-between;align-items:start;margin-bottom:8px;">
            <div style="font-size:14px;font-weight:600;">${s.name}</div>
            <span class="tag tag-blue">${s.stage}</span>
          </div>
          <div style="display:flex;gap:6px;margin-bottom:8px;">
            <span class="tag tag-gray">${s.style}</span>
            <span class="tag tag-gray">${s.targets} 只标的</span>
          </div>
          <div style="font-size:12px;color:var(--text-secondary);line-height:1.6;">${s.desc}</div>
        </div>
      `).join('');
    });
  });
}

function articleCard(a) {
  const body = (a.content || []).map(p =>
    `<p style="margin:0;font-size:12px;color:var(--text-secondary);line-height:1.75;">${p}</p>`
  ).join('');
  return `
    <div class="card knowledge-card" data-article-id="${a.id}" style="margin-bottom:12px;cursor:pointer;">
      <div style="display:flex;justify-content:space-between;align-items:start;gap:12px;">
        <div style="flex:1;min-width:0;">
          <div style="font-size:14px;font-weight:600;margin-bottom:4px;">${a.title}</div>
          <div style="font-size:12px;color:var(--text-secondary);line-height:1.6;">${a.summary}</div>
        </div>
        <div style="display:flex;flex-direction:column;align-items:flex-end;gap:4px;flex-shrink:0;">
          <span class="tag tag-blue">${a.category}</span>
          <span style="font-size:10px;color:var(--text-tertiary);">${a.read_time}</span>
        </div>
      </div>
      <div class="knowledge-body" style="display:none;margin-top:12px;padding-top:12px;border-top:1px solid var(--border);flex-direction:column;gap:8px;">
        ${body}
      </div>
      <div class="knowledge-toggle" style="margin-top:8px;font-size:11px;color:var(--rox-primary);">阅读全文 ▾</div>
    </div>
  `;
}

async function renderKnowledge() {
  const el = document.getElementById('fw-content');
  const data = await ROX.api.get('/api/framework/knowledge');
  if (!data) { el.innerHTML = '<p>加载失败</p>'; return; }

  el.innerHTML = `
    <div style="display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap;">
      <button class="btn btn-secondary btn-sm fw-cat-filter active" data-cat="">全部</button>
      ${(data.categories||[]).map(c => `<button class="btn btn-secondary btn-sm fw-cat-filter" data-cat="${c}">${c}</button>`).join('')}
    </div>
    <div id="knowledge-list">
      ${data.articles.map(articleCard).join('')}
    </div>
  `;

  const list = document.getElementById('knowledge-list');
  list.addEventListener('click', (e) => {
    const card = e.target.closest('.knowledge-card');
    if (!card) return;
    const body = card.querySelector('.knowledge-body');
    const toggle = card.querySelector('.knowledge-toggle');
    const isOpen = body.style.display !== 'none';
    body.style.display = isOpen ? 'none' : 'flex';
    toggle.textContent = isOpen ? '阅读全文 ▾' : '收起全文 ▴';
  });

  el.querySelectorAll('.fw-cat-filter').forEach(btn => {
    btn.addEventListener('click', async () => {
      el.querySelectorAll('.fw-cat-filter').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const cat = btn.dataset.cat;
      const url = cat ? `/api/framework/knowledge?category=${encodeURIComponent(cat)}` : '/api/framework/knowledge';
      const d = await ROX.api.get(url);
      if (!d) return;
      list.innerHTML = d.articles.map(articleCard).join('');
    });
  });
}
