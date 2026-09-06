/* 法律与合规 — 用户协议 / 隐私政策 / 风险揭示（公开可读，登录前后均可查看）。 */
(function () {
  ROX.register('/legal', async function (container, params) {
    const docId = (params && params.query && params.query.doc) || 'terms';
    const index = await ROX.api.get('/api/legal');
    const docs = (index && index.docs) || [];

    const render = async (id) => {
      container.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
      const doc = await ROX.api.get(`/api/legal/${id}`);
      if (!doc || doc.error) {
        container.innerHTML = '<div class="empty-state"><p>文档加载失败，请稍后重试。</p></div>';
        return;
      }
      const tabs = docs.map(d => `
        <button class="btn ${d.id === id ? 'btn-primary' : 'btn-secondary'} btn-sm" data-legal-doc="${d.id}">${ROX.escape(d.title)}</button>`).join('');
      const sections = (doc.sections || []).map(sec => `
        <div style="margin-bottom:18px;">
          <h3 style="font-size:14px;font-weight:600;margin:0 0 8px;color:var(--text-primary);">${ROX.escape(sec.heading)}</h3>
          ${sec.paragraphs.map(p => `<p style="font-size:13px;color:var(--text-secondary);line-height:1.9;margin:0 0 8px;">${ROX.escape(p)}</p>`).join('')}
        </div>`).join('');
      container.innerHTML = `
        <div class="page-header"><h2>法律与合规</h2></div>
        <div class="card" style="max-width:760px;margin:0 auto;padding:20px 24px;">
          <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:6px;">${tabs}</div>
          <div style="font-size:11px;color:var(--text-tertiary);margin-bottom:14px;">${ROX.escape(doc.title)} · ${ROX.escape(doc.version)} · 更新于 ${ROX.escape(doc.updated)}</div>
          <div>${sections}</div>
          <div style="font-size:11px;color:var(--text-tertiary);border-top:1px solid var(--border-default);padding-top:10px;">${ROX.escape(index.note || '')}</div>
        </div>`;
      container.querySelectorAll('[data-legal-doc]').forEach(btn => {
        btn.addEventListener('click', () => render(btn.dataset.legalDoc));
      });
    };

    await render(docId);
  });
})();
