/* 管理员 · 用户反馈查看（仅 ADMIN_USERNAMES 中的账号可用，服务端强制校验）。 */
(function () {
  ROX.register('/admin/feedback', async function (container) {
    container.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
    const data = await ROX.api.get('/api/feedback');

    if (!data || data.error) {
      const detail = data && data.detail;
      container.innerHTML = `<div class="empty-state"><p>${ROX.escape(typeof detail === 'string' ? detail : '加载失败，请稍后重试。')}</p></div>`;
      return;
    }

    const rows = (data.items || []).map(item => `
      <tr style="border-top:1px solid var(--border-default);">
        <td style="padding:8px 10px;white-space:nowrap;font-family:var(--font-mono);font-size:11px;color:var(--text-tertiary);">${ROX.escape((item.created_at || '').replace('T', ' ').slice(0, 16))}</td>
        <td style="padding:8px 10px;font-weight:600;">${ROX.escape(item.username)}</td>
        <td style="padding:8px 10px;font-size:12px;color:var(--text-secondary);line-height:1.7;min-width:200px;">${ROX.escape(item.content)}</td>
        <td style="padding:8px 10px;font-size:11px;color:var(--text-tertiary);">${ROX.escape(item.contact || '—')}</td>
        <td style="padding:8px 10px;font-size:11px;color:var(--text-tertiary);font-family:var(--font-mono);">${ROX.escape(item.page || '—')}</td>
      </tr>`).join('');

    container.innerHTML = `
      <div class="page-header"><h2>用户反馈</h2></div>
      <div class="card" style="padding:16px 20px;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
          <div style="font-size:12px;color:var(--text-tertiary);">共 ${data.total} 条 · 按时间倒序 · 仅管理员可见</div>
          <button class="btn btn-secondary btn-sm" id="fb-refresh">刷新</button>
        </div>
        ${data.total ? `
        <div class="table-wrap" style="overflow-x:auto;">
          <table style="width:100%;border-collapse:collapse;font-size:13px;">
            <thead><tr style="color:var(--text-tertiary);text-align:left;">
              <th style="padding:6px 10px;">时间</th><th style="padding:6px 10px;">用户</th>
              <th style="padding:6px 10px;">内容</th><th style="padding:6px 10px;">联系方式</th>
              <th style="padding:6px 10px;">页面</th>
            </tr></thead>
            <tbody>${rows}</tbody>
          </table>
        </div>` : `
        <div class="empty-state" style="padding:24px;"><p>还没有收到反馈。</p><p style="font-size:12px;margin:6px 0 0;">用户通过「设置 → 账户 → 意见反馈」提交的内容会出现在这里。</p></div>`}
      </div>`;

    container.querySelector('#fb-refresh')?.addEventListener('click', () => ROX.render('/admin/feedback'));
  });
})();
