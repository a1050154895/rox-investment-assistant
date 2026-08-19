/* ============================================
   视图 · 使用教程与功能说明
   ============================================ */

ROX.register('/guide', async function(container) {
  const data = await ROX.api.get('/api/guide/');
  if (!data) {
    container.innerHTML = '<div class="empty-state"><p>加载失败</p></div>';
    return;
  }

  const steps = data.onboarding_steps || [];
  const features = data.features || [];

  container.innerHTML = `
    <div style="display:flex;flex-direction:column;gap:16px;">
      <div class="card">
        <div class="card-header">
          <div><div class="card-title">使用教程</div><div class="card-subtitle">核心闭环：先定阶段 → 记决策 → 做体检 → 复盘</div></div>
        </div>
        <div style="display:flex;flex-direction:column;gap:14px;">
          ${steps.map(s => `
            <div style="display:flex;gap:12px;align-items:flex-start;">
              <div style="flex-shrink:0;width:26px;height:26px;border-radius:50%;background:var(--brand-blue-subtle);color:var(--brand-blue);display:flex;align-items:center;justify-content:center;font-family:var(--font-mono);font-size:12px;font-weight:600;">${s.step}</div>
              <div style="flex:1;min-width:0;">
                <div style="font-size:13px;font-weight:600;">${ROX.escape(s.title)}</div>
                <div style="font-size:12px;color:var(--text-secondary);line-height:1.7;margin-top:2px;">${ROX.escape(s.detail)}</div>
                ${s.route ? `<button class="btn btn-secondary btn-sm" style="margin-top:6px;" data-route="${s.route}">去使用</button>` : ''}
              </div>
            </div>
          `).join('')}
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <div><div class="card-title">功能说明</div><div class="card-subtitle">每个功能是什么、什么时候用、怎么用</div></div>
        </div>
        <div class="grid-2" style="gap:12px;">
          ${features.map(f => `
            <div style="background:var(--bg-secondary);border-radius:var(--radius-md);padding:12px;">
              <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
                <span style="font-size:13px;font-weight:600;">${ROX.escape(f.name)}</span>
                ${f.route ? `<button class="btn btn-ghost btn-sm" data-route="${f.route}" style="margin-left:auto;">打开</button>` : `<span class="tag tag-gray" style="margin-left:auto;">暂不可用</span>`}
              </div>
              <div style="font-size:11px;color:var(--text-secondary);line-height:1.65;">
                <div><span style="color:var(--text-tertiary);">是什么：</span>${ROX.escape(f.what)}</div>
                <div><span style="color:var(--text-tertiary);">何时用：</span>${ROX.escape(f.when)}</div>
                <div><span style="color:var(--text-tertiary);">怎么用：</span>${ROX.escape(f.how)}</div>
              </div>
            </div>
          `).join('')}
        </div>
      </div>
    </div>
  `;
});
