/* ============================================
   研究工作台：把发现、研究、验证和复盘组织成任务入口
   ============================================ */

ROX.register('/workbench', async function(container) {
  const [research, ai] = await Promise.all([
    ROX.api.get('/api/research/today'),
    ROX.api.get('/api/ai/status'),
  ]);
  const cards = research?.cards || [];
  const due = research?.due_review_cards || [];
  const aiState = ai && !ai.error ? `${ai.configured ? '已配置' : '未配置'} · ${ai.mode === 'off' ? '无 AI 模式' : ai.mode === 'byok' ? '自带模型' : '平台 AI'}` : '登录后查看';
  container.innerHTML = `
    <div class="research-page workbench-page">
      <div class="research-page-head">
        <div><div class="eyebrow">ROX / RESEARCH WORKBENCH</div><h2 class="research-page-title">研究工作台</h2><p class="research-page-subtitle">从一个对象或主题开始，进入证据、假设、反证、决策和复盘。</p></div>
        <button class="btn btn-primary" data-route="/research/new">+ 新建研究卡</button>
      </div>
      <div class="workbench-hero card">
        <div><span class="tag tag-blue">今日队列</span><h3>${ROX.escape(research?.next_action || '创建第一张研究卡')}</h3><p>AI 只负责整理、追问和归纳；行情、事实与风控仍以系统真实数据和你的核验为准。</p></div>
        <div class="workbench-hero-stats"><div><strong>${cards.length}</strong><span>进行中</span></div><div><strong>${due.length}</strong><span>待复核</span></div><div><strong>${ROX.escape(aiState)}</strong><span>AI状态</span></div></div>
      </div>
      <section class="workbench-section"><div class="section-heading"><div><span class="eyebrow">TASKS</span><h3>研究任务</h3></div><span>选择一个动作开始</span></div>
        <div class="workbench-task-grid">
          <button class="card workbench-task" data-route="/stock"><span class="task-kicker">ONE PAGE</span><strong>标的一页通</strong><small>行情、K线、基本面、研究卡和决策记录</small></button>
          <button class="card workbench-task" data-route="/intelligence"><span class="task-kicker">THEME</span><strong>主题研究</strong><small>主题主线、传导路径、行业影响和待验证问题</small></button>
          <button class="card workbench-task" data-route="/research/new?template=serenity_chain"><span class="task-kicker">CHAIN</span><strong>产业链三问</strong><small>把行业机会拆成可验证的研究问题</small></button>
          <button class="card workbench-task" data-route="/research/new?template=discipline_guard"><span class="task-kicker">COUNTER</span><strong>反模式自查</strong><small>主动寻找反证，检查仓位和退出条件</small></button>
          <button class="card workbench-task" data-route="/review"><span class="task-kicker">REVIEW</span><strong>复盘研究判断</strong><small>查看假设验证率、关联决策和错误模式</small></button>
          <button class="card workbench-task" data-route="/guide"><span class="task-kicker">EVIDENCE</span><strong>研究资料与方法</strong><small>查看研究方法、证据边界和数据可信规则</small></button>
        </div>
      </section>
      <section class="workbench-section"><div class="section-heading"><div><span class="eyebrow">AI ASSIST</span><h3>研究助手</h3></div><span>模型辅助，不是事实来源</span></div>
        <div class="card workbench-ai-card"><label class="form-group"><span class="form-label">你现在想验证什么？</span><textarea id="workbench-ai-input" class="form-textarea" rows="3" placeholder="例如：我想判断某行业景气是否能传导到目标公司的盈利"></textarea></label><div class="workbench-ai-actions"><select id="workbench-ai-action" class="form-select"><option value="question">改写为可验证问题</option><option value="counter">生成反证角度</option><option value="classify">拆分事实与观点</option></select><button class="btn btn-secondary" data-action="workbench-ai">运行研究辅助</button></div><div id="workbench-ai-result" class="research-ai-result" aria-live="polite"></div></div>
      </section>
      <section class="workbench-section"><div class="section-heading"><div><span class="eyebrow">QUEUE</span><h3>继续研究</h3></div><button class="btn btn-ghost btn-sm" data-route="/research">查看全部</button></div><div class="workbench-queue">${cards.length ? cards.slice(0, 4).map(card => `<button class="card workbench-queue-item" data-route="/research/${card.id}"><strong>${ROX.escape(card.title)}</strong><span>${ROX.escape(card.status_label || card.status)} · ${ROX.escape(card.targets?.map(t => t.name || t.code).join('、') || card.stock || '未绑定标的')}</span></button>`).join('') : '<div class="empty-state">还没有研究卡，从一个具体问题开始。</div>'}</div></section>
    </div>`;
  container.querySelectorAll('[data-route]').forEach(item => item.addEventListener('click', () => ROX.navigate(item.dataset.route)));
  container.querySelector('[data-action="workbench-ai"]')?.addEventListener('click', async () => {
    const input = document.getElementById('workbench-ai-input');
    const result = document.getElementById('workbench-ai-result');
    const content = input?.value.trim();
    if (!content) { ROX.toast('请先输入要验证的问题', 'warn'); return; }
    result.innerHTML = '<div class="loading"><div class="spinner"></div></div><span>研究辅助生成中…</span>';
    const response = await ROX.api.post('/api/ai/research-assist', { action: document.getElementById('workbench-ai-action').value, content });
    if (response?.output) result.innerHTML = `<div class="research-ai-output">${ROX.escape(response.output).replace(/\n/g, '<br>')}</div><div class="research-ai-note">${ROX.escape(response.ai_note || '')}</div>`;
    else result.innerHTML = `<div class="research-ai-note">${ROX.escape(typeof response?.detail === 'string' ? response.detail : response?.detail?.message || 'AI 辅助暂不可用')}</div>`;
  });
});
