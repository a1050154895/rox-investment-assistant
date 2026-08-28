/* ============================================
   视图 · 使用教程（分页：新手引导 / 功能说明 / FAQ / 术语表）
   ============================================ */

ROX.register('/guide', async function(container) {
  const data = await ROX.api.get('/api/guide/');
  if (!data) {
    container.innerHTML = '<div class="empty-state"><p>加载失败</p></div>';
    return;
  }

  const steps = data.onboarding_steps || [];
  const features = data.features || [];
  const faq = data.faq || [];
  const glossary = data.glossary || [];
  const shortcuts = data.shortcuts || [];

  const stepsHtml = steps.map(s => `
    <div style="display:flex;gap:12px;align-items:flex-start;">
      <div style="flex-shrink:0;width:26px;height:26px;border-radius:50%;background:var(--brand-blue-subtle);color:var(--brand-blue);display:flex;align-items:center;justify-content:center;font-family:var(--font-mono);font-size:12px;font-weight:600;">${s.step}</div>
      <div style="flex:1;min-width:0;">
        <div style="font-size:13px;font-weight:600;">${ROX.escape(s.title)}</div>
        <div style="font-size:12px;color:var(--text-secondary);line-height:1.7;margin-top:2px;">${ROX.escape(s.detail)}</div>
        ${s.route ? `<button class="btn btn-secondary btn-sm" style="margin-top:6px;" data-route="${s.route}">去使用</button>` : ''}
      </div>
    </div>
  `).join('');

  const featuresHtml = features.map(f => `
    <div style="background:var(--bg-secondary);border-radius:var(--radius-md);padding:12px;">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
        <span style="font-size:13px;font-weight:600;">${ROX.escape(f.name)}</span>
        ${f.route ? `<button class="btn btn-ghost btn-sm" data-route="${f.route}" style="margin-left:auto;">打开</button>` : `<span class="tag tag-gray" style="margin-left:auto;">设置/面板</span>`}
      </div>
      <div style="font-size:11px;color:var(--text-secondary);line-height:1.65;">
        <div><span style="color:var(--text-tertiary);">是什么：</span>${ROX.escape(f.what)}</div>
        <div><span style="color:var(--text-tertiary);">何时用：</span>${ROX.escape(f.when)}</div>
        <div><span style="color:var(--text-tertiary);">怎么用：</span>${ROX.escape(f.how)}</div>
      </div>
    </div>
  `).join('');

  const faqHtml = faq.map(f => `
    <div style="background:var(--bg-secondary);border-radius:var(--radius-md);padding:14px;">
      <div style="font-size:13px;font-weight:600;margin-bottom:6px;">${ROX.escape(f.q)}</div>
      <div style="font-size:12px;color:var(--text-secondary);line-height:1.7;">${ROX.escape(f.a)}</div>
    </div>
  `).join('');

  const glossaryHtml = glossary.map(g => `
    <div style="display:flex;gap:12px;align-items:flex-start;">
      <span style="flex-shrink:0;font-family:var(--font-mono);font-size:12px;font-weight:600;color:var(--brand-blue);min-width:90px;">${ROX.escape(g.term)}</span>
      <span style="font-size:12px;color:var(--text-secondary);line-height:1.7;">${ROX.escape(g.def)}</span>
    </div>
  `).join('');

  const shortcutsHtml = shortcuts.map(sc => `
    <div style="display:flex;gap:12px;align-items:center;">
      <kbd style="font-family:var(--font-mono);font-size:11px;padding:2px 8px;border:1px solid var(--border-color);border-radius:4px;background:var(--bg-secondary);">${ROX.escape(sc.key)}</kbd>
      <span style="font-size:12px;color:var(--text-secondary);">${ROX.escape(sc.desc)}</span>
    </div>
  `).join('');

  container.innerHTML = `
    <div style="display:flex;flex-direction:column;gap:16px;">
      <div style="display:flex;gap:6px;flex-wrap:wrap;" id="guide-tabs">
        <button class="btn btn-sm guide-tab-btn active" data-tab="onboard" style="font-size:12px;">新手引导</button>
        <button class="btn btn-sm btn-ghost guide-tab-btn" data-tab="features" style="font-size:12px;">功能说明</button>
        <button class="btn btn-sm btn-ghost guide-tab-btn" data-tab="faq" style="font-size:12px;">常见问题</button>
        <button class="btn btn-sm btn-ghost guide-tab-btn" data-tab="glossary" style="font-size:12px;">术语表</button>
      </div>

      <div id="guide-tab-onboard">
        <div class="card">
          <div class="card-header">
            <div><div class="card-title">使用教程</div><div class="card-subtitle">核心闭环：先定阶段 → 记决策 → 做体检 → 复盘</div></div>
          </div>
          <div style="display:flex;flex-direction:column;gap:14px;">${stepsHtml}</div>
        </div>
      </div>

      <div id="guide-tab-features" style="display:none;">
        <div class="card">
          <div class="card-header">
            <div><div class="card-title">功能说明</div><div class="card-subtitle">每个功能是什么、什么时候用、怎么用</div></div>
          </div>
          <div class="grid-2" style="gap:12px;">${featuresHtml}</div>
        </div>
      </div>

      <div id="guide-tab-faq" style="display:none;">
        <div class="card">
          <div class="card-header">
            <div><div class="card-title">常见问题</div><div class="card-subtitle">数据可信度、AI 边界与技术限制</div></div>
          </div>
          <div style="display:flex;flex-direction:column;gap:12px;">${faqHtml}</div>
        </div>
      </div>

      <div id="guide-tab-glossary" style="display:none;">
        <div class="card">
          <div class="card-header">
            <div><div class="card-title">术语表</div><div class="card-subtitle">核心概念和指标定义</div></div>
          </div>
          <div style="display:flex;flex-direction:column;gap:10px;">${glossaryHtml}</div>
        </div>
        ${shortcuts.length > 0 ? `
        <div class="card" style="margin-top:12px;">
          <div class="card-header">
            <div><div class="card-title">键盘快捷键</div></div>
          </div>
          <div style="display:flex;flex-direction:column;gap:8px;">${shortcutsHtml}</div>
        </div>` : ''}
      </div>
    </div>
  `;

  document.querySelectorAll('.guide-tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.guide-tab-btn').forEach(b => {
        b.classList.remove('active');
        b.classList.add('btn-ghost');
      });
      btn.classList.add('active');
      btn.classList.remove('btn-ghost');
      ['onboard', 'features', 'faq', 'glossary'].forEach(tab => {
        const el = document.getElementById(`guide-tab-${tab}`);
        if (el) el.style.display = tab === btn.dataset.tab ? '' : 'none';
      });
    });
  });
});
