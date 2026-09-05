/* 重置密码 / 邮箱验证 — 邮件链接落地页。
   两个路由均从邮件深链接进入（后端 catch-all 会把任意路径交给 SPA 外壳），
   令牌只通过 query 参数传递，一次性使用，不在本地存储。 */
(function () {
  const TOKEN_RE = /^[A-Za-z0-9_\-]{16,200}$/;

  function pageShell(title, bodyHtml) {
    return `
      <div class="page-header"><h2>${ROX.escape(title)}</h2></div>
      <div class="card" style="max-width:480px;margin:0 auto;">${bodyHtml}</div>`;
  }

  function honestError(title, message, backLabel) {
    return `
      ${pageShell(title, `
        <div class="empty-state" style="padding:28px 20px;">
          <p style="margin:0 0 6px;">${ROX.escape(message)}</p>
          <p style="font-size:12px;color:var(--text-tertiary);margin:0 0 16px;">链接为一次性使用，且有时效限制。</p>
          <button class="btn btn-secondary" data-route="/">${ROX.escape(backLabel || '返回首页')}</button>
        </div>`)}`;
  }

  ROX.register('/reset-password', async function (container, params) {
    const token = (params && params.query && params.query.token) || '';
    if (!TOKEN_RE.test(token)) {
      container.innerHTML = honestError('重置密码', '重置链接无效或已过期，请重新发起找回密码。');
      return;
    }

    container.innerHTML = pageShell('设置新密码', `
      <div style="display:flex;flex-direction:column;gap:14px;padding:4px;">
        <p style="font-size:13px;color:var(--text-secondary);line-height:1.7;margin:0;">请为新密码设置至少 6 位字符。重置成功后，其他已登录设备将需要重新登录。</p>
        <div class="form-group">
          <label class="form-label" for="reset-password-input">新密码</label>
          <input class="form-input" type="password" id="reset-password-input" placeholder="至少 6 位" autocomplete="new-password">
        </div>
        <div class="form-group">
          <label class="form-label" for="reset-password-confirm">确认新密码</label>
          <input class="form-input" type="password" id="reset-password-confirm" placeholder="再次输入新密码" autocomplete="new-password">
        </div>
        <div id="reset-error" class="auth-error" style="display:none;"></div>
        <button class="btn btn-primary" id="reset-submit">确认重置</button>
      </div>`);

    const button = document.getElementById('reset-submit');
    const errEl = document.getElementById('reset-error');
    const showError = (msg) => { if (errEl) { errEl.textContent = msg; errEl.style.display = 'block'; } };

    button.addEventListener('click', async () => {
      const pwd = document.getElementById('reset-password-input')?.value || '';
      const confirm = document.getElementById('reset-password-confirm')?.value || '';
      if (pwd.length < 6) { showError('密码至少 6 位'); return; }
      if (pwd !== confirm) { showError('两次输入的密码不一致'); return; }
      button.disabled = true;
      button.textContent = '提交中…';
      const res = await ROX.api.post('/api/auth/reset-password', { token, new_password: pwd });
      if (res && res.success) {
        container.innerHTML = pageShell('密码已重置', `
          <div class="empty-state" style="padding:28px 20px;">
            <p style="margin:0 0 16px;">${ROX.escape(res.message || '密码已重置，请使用新密码登录。')}</p>
            <button class="btn btn-primary" data-action="open-login">去登录</button>
          </div>`);
      } else {
        button.disabled = false;
        button.textContent = '确认重置';
        const detail = res && res.detail;
        showError(typeof detail === 'string' ? detail : '重置失败，请重新发起找回密码');
      }
    });
  });

  ROX.register('/verify-email', async function (container, params) {
    const token = (params && params.query && params.query.token) || '';
    if (!TOKEN_RE.test(token)) {
      container.innerHTML = honestError('邮箱验证', '验证链接无效或已过期，请登录后在「设置 → 账户」重新发送验证邮件。');
      return;
    }

    container.innerHTML = pageShell('邮箱验证', '<div class="loading"><div class="spinner"></div></div>');
    const res = await ROX.api.post('/api/auth/email/verify', { token });
    if (res && res.success) {
      container.innerHTML = pageShell('邮箱验证成功', `
        <div class="empty-state" style="padding:28px 20px;">
          <p style="margin:0 0 6px;">${ROX.escape(res.message || '邮箱验证成功，找回密码功能已可用。')}</p>
          <p style="font-size:12px;color:var(--text-tertiary);margin:0 0 16px;">忘记密码时，可通过该邮箱自助找回账号。</p>
          <button class="btn btn-primary" data-action="open-login">去登录</button>
        </div>`);
    } else {
      const detail = res && res.detail;
      container.innerHTML = honestError(
        '邮箱验证',
        typeof detail === 'string' ? detail : '验证失败，请登录后在「设置 → 账户」重新发送验证邮件。',
        '返回首页'
      );
    }
  });
})();
