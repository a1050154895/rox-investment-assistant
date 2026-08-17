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
          <div class="methodology-title">${layer.title}</div>
          <div class="methodology-summary">${layer.summary}</div>

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
            <details style="margin-top:10px;">
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
      ${data.articles.map(a => `
        <div class="card" style="margin-bottom:12px;cursor:pointer;">
          <div style="display:flex;justify-content:space-between;align-items:start;">
            <div style="flex:1;">
              <div style="font-size:14px;font-weight:600;margin-bottom:4px;">${a.title}</div>
              <div style="font-size:12px;color:var(--text-secondary);line-height:1.6;">${a.summary}</div>
            </div>
            <div style="display:flex;flex-direction:column;align-items:flex-end;gap:4px;margin-left:16px;">
              <span class="tag tag-blue">${a.category}</span>
              <span style="font-size:10px;color:var(--text-tertiary);">${a.read_time}</span>
            </div>
          </div>
        </div>
      `).join('')}
    </div>
  `;

  el.querySelectorAll('.fw-cat-filter').forEach(btn => {
    btn.addEventListener('click', async () => {
      el.querySelectorAll('.fw-cat-filter').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const cat = btn.dataset.cat;
      const url = cat ? `/api/framework/knowledge?category=${encodeURIComponent(cat)}` : '/api/framework/knowledge';
      const d = await ROX.api.get(url);
      if (!d) return;
      const list = document.getElementById('knowledge-list');
      list.innerHTML = d.articles.map(a => `
        <div class="card" style="margin-bottom:12px;cursor:pointer;">
          <div style="display:flex;justify-content:space-between;align-items:start;">
            <div style="flex:1;">
              <div style="font-size:14px;font-weight:600;margin-bottom:4px;">${a.title}</div>
              <div style="font-size:12px;color:var(--text-secondary);line-height:1.6;">${a.summary}</div>
            </div>
            <div style="display:flex;flex-direction:column;align-items:flex-end;gap:4px;margin-left:16px;">
              <span class="tag tag-blue">${a.category}</span>
              <span style="font-size:10px;color:var(--text-tertiary);">${a.read_time}</span>
            </div>
          </div>
        </div>
      `).join('');
    });
  });
}
