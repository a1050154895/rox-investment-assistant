/* ============================================
   研究卡：ROX Loop 的核心工作流
   ============================================ */

const CARD_STATUS_OPTIONS = [
  ['draft', '草稿'], ['researching', '研究中'], ['to_verify', '待验证'], ['ready', '待决策'],
  ['watching', '观察中'], ['reviewed', '已复盘'], ['invalidated', '已失效'], ['archived', '已归档'],
];

const HYPOTHESIS_STATUS_OPTIONS = [['', '未设置'], ['未验证', '未验证'], ['成立', '成立'], ['部分成立', '部分成立'], ['失效', '失效']];

function researchCardForm(card = {}) {
  const facts = (card.facts || []).join('\n');
  return `
    <form id="research-card-form" class="research-form">
      <div class="research-step" data-step="1">
      <div class="research-step-label">1 / 4 · 先定义研究对象</div><div class="research-form-grid">
        <label class="form-group"><span class="form-label">研究标题 *</span><input class="form-input" name="title" required maxlength="120" value="${ROX.escape(card.title || '')}" placeholder="例如：宁德时代当前是否值得继续跟踪？"></label>
        <label class="form-group"><span class="form-label">研究目标</span><input class="form-input" id="research-target-search" autocomplete="off" placeholder="搜索股票代码或名称"><div id="research-target-results" class="search-results"></div><div id="research-target-list" class="research-target-list"></div><input type="hidden" name="code" value="${ROX.escape(card.code || '')}"><input type="hidden" name="stock" value="${ROX.escape(card.stock || '')}"><input type="hidden" name="targets" value=""></label>
        <label class="form-group"><span class="form-label">动作</span><select class="form-input" name="action"><option ${card.action === '观察' || !card.action ? 'selected' : ''}>观察</option><option ${card.action === '买入' ? 'selected' : ''}>买入</option><option ${card.action === '持有' ? 'selected' : ''}>持有</option><option ${card.action === '减仓' ? 'selected' : ''}>减仓</option><option ${card.action === '卖出' ? 'selected' : ''}>卖出</option></select></label>
      </div>
      </div>
      <div class="research-step" data-step="2">
      <div class="research-step-label">2 / 4 · 写清你的判断</div>
      <label class="form-group"><span class="form-label">研究问题</span><textarea class="form-input" name="question" rows="2" placeholder="我现在到底要验证什么？">${ROX.escape(card.question || '')}</textarea></label>
      <label class="form-group"><span class="form-label">核心假设</span><textarea class="form-input" name="hypothesis" rows="3" placeholder="我认为……因为……">${ROX.escape(card.hypothesis || '')}</textarea></label>
      <label class="form-group"><span class="form-label">关键事实（每行一条，标注来源/日期）</span><textarea class="form-input" name="facts" rows="4" placeholder="公司公告：……（来源/日期）\n行情数据：……（数据日期）">${ROX.escape(facts)}</textarea></label>
      </div>
      <div class="research-step" data-step="3">
      <div class="research-step-label">3 / 4 · 主动找反证</div>
      <div class="research-ai-bar">
        <span class="research-ai-label">AI 辅助</span>
        <button type="button" class="btn btn-secondary btn-sm" data-action="ai-assist" data-kind="question">改写研究问题</button>
        <button type="button" class="btn btn-secondary btn-sm" data-action="ai-assist" data-kind="counter">反证提示</button>
        <button type="button" class="btn btn-secondary btn-sm" data-action="ai-assist" data-kind="classify">事实/观点拆分</button>
      </div>
      <div id="research-ai-result" class="research-ai-result" aria-live="polite"></div>
      <div class="research-form-grid">
        <label class="form-group"><span class="form-label">反证</span><textarea class="form-input" name="counter_evidence" rows="3" placeholder="哪些事实不支持我的观点？">${ROX.escape(card.counter_evidence || '')}</textarea></label>
        <label class="form-group"><span class="form-label">失效条件</span><textarea class="form-input" name="invalidation" rows="3" placeholder="什么发生时，我必须承认判断失效？">${ROX.escape(card.invalidation || '')}</textarea></label>
      </div>
      </div>
      <div class="research-step" data-step="4">
      <div class="research-step-label">4 / 4 · 设定纪律与状态</div>
      <div class="research-form-grid">
        <label class="form-group"><span class="form-label">仓位计划</span><input class="form-input" name="position_plan" value="${ROX.escape(card.position_plan || '')}" placeholder="如：试仓不超过总资产10%"></label>
        <label class="form-group"><span class="form-label">止损价（可选）</span><input class="form-input" type="number" step="0.01" name="stop_loss" value="${card.stop_loss ?? ''}" placeholder="仅作纪律记录"></label>
        <label class="form-group"><span class="form-label">持有周期</span><input class="form-input" name="holding_period" value="${ROX.escape(card.holding_period || '')}" placeholder="如：3-6个月"></label>
        <label class="form-group"><span class="form-label">下次复核日期</span><input class="form-input" type="date" name="next_review_at" value="${ROX.escape(card.next_review_at || '')}"></label>
        <label class="form-group"><span class="form-label">状态</span><select class="form-input" name="status">${CARD_STATUS_OPTIONS.map(([value, label]) => `<option value="${value}" ${(card.status || 'draft') === value ? 'selected' : ''}>${label}</option>`).join('')}</select></label>
        <label class="form-group"><span class="form-label">假设状态</span><select class="form-input" name="hypothesis_status">${HYPOTHESIS_STATUS_OPTIONS.map(([value, label]) => `<option value="${value}" ${(card.hypothesis_status || '') === value ? 'selected' : ''}>${label}</option>`).join('')}</select></label>
      </div>
      </div>
      <div class="research-step-actions"><button type="button" class="btn btn-secondary" id="research-step-prev">上一步</button><span id="research-step-status">第 1 步 / 4</span><button type="button" class="btn btn-primary" id="research-step-next">下一步</button></div>
      <div class="research-form-actions"><button type="button" class="btn btn-secondary" id="research-risk-check">先做风控检查</button><button type="submit" class="btn btn-primary">保存研究卡</button></div>
      <div id="research-risk-result" class="research-risk-result" aria-live="polite"></div>
    </form>`;
}

function researchPayload(form) {
  const data = Object.fromEntries(new FormData(form).entries());
  data.facts = (data.facts || '').split('\n').map(item => item.trim()).filter(Boolean);
  data.stop_loss = data.stop_loss ? Number(data.stop_loss) : null;
  data.hypothesis_status = data.hypothesis_status || null;
  try { data.targets = JSON.parse(form.querySelector('[name="targets"]')?.value || '[]'); } catch (_) { data.targets = []; }
  return data;
}

function setResearchTargets(form, targets) {
  const list = form.querySelector('#research-target-list');
  const hidden = form.querySelector('[name="targets"]');
  if (!list || !hidden) return;
  hidden.value = JSON.stringify(targets);
  const code = form.querySelector('[name="code"]');
  const stock = form.querySelector('[name="stock"]');
  if (code) code.value = targets[0]?.code || '';
  if (stock) stock.value = targets[0]?.name || '';
  list.innerHTML = targets.map((target, index) => `<span class="tag tag-blue">${ROX.escape(target.name || target.code)} <button type="button" data-remove-target="${index}" aria-label="移除研究目标">×</button></span>`).join('');
}

async function bindResearchTargetPicker(form, seed) {
  const input = form.querySelector('#research-target-search');
  const results = form.querySelector('#research-target-results');
  if (!input || !results) return;
  let targets = Array.isArray(seed.targets) && seed.targets.length ? seed.targets : (seed.code ? [{ code: seed.code, name: seed.stock, type: 'stock' }] : []);
  setResearchTargets(form, targets);
  input.addEventListener('input', async () => {
    const query = input.value.trim();
    if (!query) { results.classList.remove('show'); return; }
    const data = await ROX.api.get(`/api/stock/search?q=${encodeURIComponent(query)}`);
    results.innerHTML = (data?.results || []).slice(0, 8).map(item => `<button type="button" class="search-result-item" data-target-code="${ROX.escape(item.code)}" data-target-name="${ROX.escape(item.name)}">${ROX.escape(item.name)} <span>${ROX.escape(item.code)}</span></button>`).join('') || '<div class="search-result-item">无匹配结果</div>';
    results.classList.add('show');
  });
  results.addEventListener('click', (event) => {
    const item = event.target.closest('[data-target-code]');
    if (!item) return;
    if (!targets.some(target => target.code === item.dataset.targetCode)) targets.push({ code: item.dataset.targetCode, name: item.dataset.targetName, type: 'stock' });
    setResearchTargets(form, targets);
    input.value = '';
    results.classList.remove('show');
  });
  form.addEventListener('click', (event) => {
    const remove = event.target.closest('[data-remove-target]');
    if (remove) { targets.splice(Number(remove.dataset.removeTarget), 1); setResearchTargets(form, targets); }
  });
}

async function renderResearchList(container) {
  const data = await ROX.api.get('/api/research/');
  const cards = data?.cards || [];
  container.innerHTML = `<div class="research-page"><div class="research-page-head"><div><div class="eyebrow">ROX LOOP / RESEARCH</div><h2 class="research-page-title">研究卡</h2><p class="research-page-subtitle">把事实、假设、反证和决策放在同一条可复盘链路上。</p></div><button class="btn btn-primary" data-route="/research/new">+ 新建研究卡</button></div><div class="research-card-list">${cards.length ? cards.map(card => `<button class="card research-list-item" data-route="/research/${card.id}"><div><strong>${ROX.escape(card.title)}</strong><div class="research-queue-meta">${ROX.escape(card.targets?.map(t => t.name || t.code).join('、') || card.stock || '未绑定标的')}</div></div><span class="tag tag-blue">${ROX.escape(card.status_label || card.status)}</span></button>`).join('') : '<div class="empty-state">还没有研究卡，先建立第一个可验证问题。</div>'}</div></div>`;
  container.querySelectorAll('[data-route]').forEach(item => item.addEventListener('click', () => ROX.navigate(item.dataset.route)));
}

function renderRiskResult(result, target) {
  if (!target || !result) return;
  target.innerHTML = `<div class="research-risk-title">${result.status === 'ready' ? '✓ 可以进入决策' : '还需要补齐研究链'}</div><div class="research-checks">${(result.checks || []).map(item => `<span class="research-check ${item.passed ? 'passed' : 'failed'}">${item.passed ? '✓' : '○'} ${ROX.escape(item.label)}</span>`).join('')}</div><div class="research-risk-message">${ROX.escape(result.message || '')}</div>`;
}

function renderResearchTimeline(events) {
  const labels = { created: '创建', updated: '更新', evidence: '证据', decision: '决策' };
  if (!events?.length) return '<div class="research-timeline-empty">保存研究卡后，证据与决策会按时间沉淀在这里。</div>';
  return `<div class="research-timeline">${events.map(event => `
    <div class="research-timeline-item research-timeline-${ROX.escape(event.event_type || 'updated')}">
      <div class="research-timeline-marker" aria-hidden="true"></div>
      <div class="research-timeline-body">
        <div class="research-timeline-head"><strong>${ROX.escape(event.title || labels[event.event_type] || '研究事件')}</strong><time>${ROX.escape((event.created_at || '').replace('T', ' ').slice(0, 16))}</time></div>
        ${event.detail ? `<p>${ROX.escape(event.detail)}</p>` : ''}
        ${event.source ? `<span class="research-timeline-source">来源：${ROX.escape(event.source)}</span>` : ''}
      </div>
    </div>`).join('')}</div>`;
}

async function loadCardArchive(cardId, mount) {
  const data = await ROX.api.get(`/api/research/${cardId}/detail`);
  if (!data || data.error || !mount) return;
  const card = data.card;
  const stats = data.decision_stats || {};
  const counts = card.evidence_counts || {};
  const flags = [];
  if (data.review_due) flags.push(`<span class="tag tag-amber">复核已到期（${ROX.escape(card.next_review_at || '')}）</span>`);
  if (!counts.counter) flags.push('<span class="tag tag-gray">尚无反证</span>');
  if (counts.pending_verify) flags.push(`<span class="tag tag-blue">${counts.pending_verify} 条待验证</span>`);
  const hypTag = card.hypothesis_status
    ? `<span class="tag ${card.hypothesis_status === '成立' ? 'tag-green' : card.hypothesis_status === '失效' ? 'tag-red' : 'tag-amber'}">假设${ROX.escape(card.hypothesis_status)}</span>`
    : '<span class="tag tag-gray">假设未验证</span>';
  mount.innerHTML = `
    <div class="research-archive">
      <div class="card-header"><div><div class="card-title">研究档案</div><div class="card-subtitle">这张卡片的证据、决策与结果放在同一条链上</div></div>${hypTag}</div>
      <div class="research-archive-flags">${flags.length ? flags.join('') : '<span class="tag tag-green">状态正常</span>'}<span class="tag tag-gray">风控 ${data.risk?.passed ?? 0}/${data.risk?.total ?? 5}</span></div>
      <div class="research-archive-stats">
        <div><span>关联决策</span><strong>${stats.total ?? 0}</strong></div>
        <div><span>已了结</span><strong>${stats.settled ?? 0}</strong></div>
        <div><span>胜率</span><strong>${stats.win_rate != null ? stats.win_rate + '%' : '--'}</strong></div>
        <div><span>平均盈亏</span><strong>${stats.avg_result_pct != null ? ROX.fmt.pct(stats.avg_result_pct) : '--'}</strong></div>
      </div>
      <div class="research-archive-section"><div class="research-archive-section-title">研究时间线</div>${renderResearchTimeline(data.timeline)}</div>
      ${(data.notes || []).length ? `
      <div class="research-archive-section">
        <div class="research-archive-section-title">关联速记</div>
        ${(data.notes || []).map(n => `
          <div style="background:var(--bg-secondary);border-radius:var(--radius-md);padding:10px 14px;margin-bottom:8px;">
            <div style="font-size:12px;line-height:1.6;white-space:pre-wrap;word-break:break-word;">${n.pinned ? '📌 ' : ''}${ROX.escape(n.content)}</div>
            <div style="font-size:10px;color:var(--text-tertiary);margin-top:4px;font-family:var(--font-mono);">${ROX.escape((n.created_at || '').slice(0, 16).replace('T', ' '))}${n.tag ? ` · ${ROX.escape(n.tag)}` : ''}</div>
          </div>
        `).join('')}
      </div>` : ''}
      ${stats.total ? `<div class="research-archive-decisions">${(data.decisions || []).map(d => `
        <div class="research-archive-decision">
          <div><span class="tag ${ROX.fmt.actionTag(d.action)}">${ROX.escape(d.action)}</span><span class="research-archive-decision-date">${ROX.escape(d.date)}</span></div>
          <div class="research-archive-decision-meta">${ROX.escape(d.stage || '')} · 一致性 ${d.consistency_score ?? '--'} · 结果 ${ROX.escape(d.result)}${d.result_pct != null ? `（${ROX.fmt.pct(d.result_pct)}）` : ''}</div>
        </div>`).join('')}</div>` : '<div class="research-archive-empty">还没有关联决策。研究链完备后，用下方按钮记录第一条决策。</div>'}
    </div>`;
}

ROX.register('/research', async function(container, params) {
  if (!params.id && !params.newCard && !Object.keys(params.query || {}).length) { await renderResearchList(container); return; }
  let cardId = params.id;
  let card = null;
  if (cardId) {
    const data = await ROX.api.get(`/api/research/${cardId}`);
    card = data?.card || null;
  }
  const query = params.query || {};
  let seed = card || (query.code ? {
    title: `${query.stock || query.code}：是否值得继续研究？`,
    code: query.code,
    stock: query.stock,
    question: `${query.stock || query.code} 当前是否满足我的研究条件？`,
    facts: [`行情：${query.price || '--'}；数据状态：${query.data_status || '未标注'}；来源：${query.data_source || '未标注'}；截至：${query.as_of || '未标注'}`],
  } : {});
  const templateLoader = async () => {
    if (card || !query.template) return;
    const res = await ROX.api.get(`/api/research/templates/${encodeURIComponent(query.template)}`);
    if (!res || res.error || !res.seed) return;
    const form = document.getElementById('research-card-form');
    if (!form) return;
    const seedData = res.seed;
    for (const [key, value] of Object.entries(seedData)) {
      const el = form.querySelector(`[name="${key}"]`);
      if (!el) continue;
      if (key === 'facts') el.value = (value || []).join('\n');
      else el.value = String(value || '');
    }
    ROX.toast(`已套用模板：${res.name}`, 'info');
  };
  container.innerHTML = `<div class="research-page"><div class="research-page-head"><div><div class="eyebrow">ROX LOOP / RESEARCH</div><h2 class="research-page-title">${card ? '继续完善研究卡' : '把一个想法变成可验证判断'}</h2><p class="research-page-subtitle">先写清事实、假设和反证，再决定是否行动。</p></div><button class="btn btn-secondary" data-route="/research?template=serenity_chain">产业链三问</button><button class="btn btn-secondary" data-route="/research?template=discipline_guard">反模式自查</button><button class="btn btn-secondary" data-route="/research?template=capital_flow_discipline">三流纪律</button><button class="btn btn-secondary" data-route="/">回到今日</button></div><div class="research-context-strip"><span class="research-context-mark">证</span><div><strong>这不是荐股表单</strong><span>把一个判断拆成证据、假设、反证和纪律，留下可复盘的依据。</span></div></div><div id="research-archive-mount"></div><div class="card research-card-shell">${researchCardForm(seed)}${cardId ? `<div class="research-decision-footer"><div><strong>研究链已保存</strong><span>准备好后再记录正式决策，决策会保留这张研究卡的关联。</span></div><button class="btn btn-primary" data-action="record-card-decision" data-card-id="${cardId}" data-code="${ROX.escape(card.code || '')}" data-name="${ROX.escape(card.stock || '')}">记录关联决策</button></div>` : ''}</div></div>`;

  const form = document.getElementById('research-card-form');
  await bindResearchTargetPicker(form, seed);
  templateLoader();
  const archiveMount = document.getElementById('research-archive-mount');
  if (cardId) loadCardArchive(cardId, archiveMount);
  const riskButton = document.getElementById('research-risk-check');
  const riskResult = document.getElementById('research-risk-result');
  let currentStep = 1;
  const steps = [...form.querySelectorAll('.research-step')];
  const prevStep = document.getElementById('research-step-prev');
  const nextStep = document.getElementById('research-step-next');
  const stepStatus = document.getElementById('research-step-status');
  function updateStep() {
    const mobile = window.matchMedia('(max-width: 760px)').matches;
    steps.forEach(step => { step.hidden = mobile && Number(step.dataset.step) !== currentStep; });
    prevStep.disabled = currentStep === 1;
    nextStep.textContent = currentStep === steps.length ? '完成检查' : '下一步';
    stepStatus.textContent = `第 ${currentStep} 步 / ${steps.length}`;
  }
  prevStep?.addEventListener('click', () => { currentStep = Math.max(1, currentStep - 1); updateStep(); });
  nextStep?.addEventListener('click', () => { currentStep = Math.min(steps.length, currentStep + 1); updateStep(); });
  window.addEventListener('resize', updateStep, { once: true });
  updateStep();
  riskButton?.addEventListener('click', async () => {
    const payload = researchPayload(form);
    if (!payload.title) { form.reportValidity(); return; }
    if (!cardId) {
      const created = await ROX.api.post('/api/research/', payload);
      if (!created?.card) { ROX.toast('请先保存研究卡，再做风控检查', 'warn'); return; }
      cardId = created.card.id;
    } else {
      await ROX.api.put(`/api/research/${cardId}`, payload);
    }
    const result = await ROX.api.get(`/api/research/${cardId}/risk-check`);
    renderRiskResult(result, riskResult);
  });
  form?.addEventListener('submit', async (event) => {
    event.preventDefault();
    const payload = researchPayload(form);
    if (!form.reportValidity()) return;
    const result = cardId ? await ROX.api.put(`/api/research/${cardId}`, payload) : await ROX.api.post('/api/research/', payload);
    if (result?.card) {
      card = result.card;
      cardId = card.id;
      ROX.toast('研究卡已保存', 'success');
      loadCardArchive(cardId, archiveMount);
      const risk = await ROX.api.get(`/api/research/${cardId}/risk-check`);
      renderRiskResult(risk, riskResult);
    } else {
      ROX.toast(result?.detail || '保存失败，请重试', 'error');
    }
  });
  container.querySelectorAll('[data-route]').forEach(button => button.addEventListener('click', () => ROX.navigate(button.dataset.route)));
});
