/* ============================================
   研究卡：ROX Loop 的核心工作流
   ============================================ */

function researchCardForm(card = {}) {
  const facts = (card.facts || []).join('\n');
  return `
    <form id="research-card-form" class="research-form">
      <div class="research-form-grid">
        <label class="form-group"><span class="form-label">研究标题 *</span><input class="form-input" name="title" required maxlength="120" value="${ROX.escape(card.title || '')}" placeholder="例如：宁德时代当前是否值得继续跟踪？"></label>
        <label class="form-group"><span class="form-label">股票代码</span><input class="form-input" name="code" maxlength="10" value="${ROX.escape(card.code || '')}" placeholder="如 300750"></label>
        <label class="form-group"><span class="form-label">股票名称</span><input class="form-input" name="stock" maxlength="30" value="${ROX.escape(card.stock || '')}" placeholder="如 宁德时代"></label>
        <label class="form-group"><span class="form-label">动作</span><select class="form-input" name="action"><option ${card.action === '观察' || !card.action ? 'selected' : ''}>观察</option><option ${card.action === '买入' ? 'selected' : ''}>买入</option><option ${card.action === '持有' ? 'selected' : ''}>持有</option><option ${card.action === '减仓' ? 'selected' : ''}>减仓</option><option ${card.action === '卖出' ? 'selected' : ''}>卖出</option></select></label>
      </div>
      <label class="form-group"><span class="form-label">研究问题</span><textarea class="form-input" name="question" rows="2" placeholder="我现在到底要验证什么？">${ROX.escape(card.question || '')}</textarea></label>
      <label class="form-group"><span class="form-label">核心假设</span><textarea class="form-input" name="hypothesis" rows="3" placeholder="我认为……因为……">${ROX.escape(card.hypothesis || '')}</textarea></label>
      <label class="form-group"><span class="form-label">关键事实（每行一条，标注来源/日期）</span><textarea class="form-input" name="facts" rows="4" placeholder="公司公告：……（来源/日期）\n行情数据：……（数据日期）">${ROX.escape(facts)}</textarea></label>
      <div class="research-form-grid">
        <label class="form-group"><span class="form-label">反证</span><textarea class="form-input" name="counter_evidence" rows="3" placeholder="哪些事实不支持我的观点？">${ROX.escape(card.counter_evidence || '')}</textarea></label>
        <label class="form-group"><span class="form-label">失效条件</span><textarea class="form-input" name="invalidation" rows="3" placeholder="什么发生时，我必须承认判断失效？">${ROX.escape(card.invalidation || '')}</textarea></label>
      </div>
      <div class="research-form-grid">
        <label class="form-group"><span class="form-label">仓位计划</span><input class="form-input" name="position_plan" value="${ROX.escape(card.position_plan || '')}" placeholder="如：试仓不超过总资产10%"></label>
        <label class="form-group"><span class="form-label">止损价（可选）</span><input class="form-input" type="number" step="0.01" name="stop_loss" value="${card.stop_loss ?? ''}" placeholder="仅作纪律记录"></label>
        <label class="form-group"><span class="form-label">持有周期</span><input class="form-input" name="holding_period" value="${ROX.escape(card.holding_period || '')}" placeholder="如：3-6个月"></label>
        <label class="form-group"><span class="form-label">状态</span><select class="form-input" name="status"><option value="draft" ${card.status !== 'ready' ? 'selected' : ''}>草稿</option><option value="ready" ${card.status === 'ready' ? 'selected' : ''}>待决策</option><option value="archived" ${card.status === 'archived' ? 'selected' : ''}>归档</option></select></label>
      </div>
      <div class="research-form-actions"><button type="button" class="btn btn-secondary" id="research-risk-check">先做风控检查</button><button type="submit" class="btn btn-primary">保存研究卡</button></div>
      <div id="research-risk-result" class="research-risk-result" aria-live="polite"></div>
    </form>`;
}

function researchPayload(form) {
  const data = Object.fromEntries(new FormData(form).entries());
  data.facts = (data.facts || '').split('\n').map(item => item.trim()).filter(Boolean);
  data.stop_loss = data.stop_loss ? Number(data.stop_loss) : null;
  return data;
}

function renderRiskResult(result, target) {
  if (!target || !result) return;
  target.innerHTML = `<div class="research-risk-title">${result.status === 'ready' ? '✓ 可以进入决策' : '还需要补齐研究链'}</div><div class="research-checks">${(result.checks || []).map(item => `<span class="research-check ${item.passed ? 'passed' : 'failed'}">${item.passed ? '✓' : '○'} ${ROX.escape(item.label)}</span>`).join('')}</div><div class="research-risk-message">${ROX.escape(result.message || '')}</div>`;
}

ROX.register('/research', async function(container, params) {
  let cardId = params.id;
  let card = null;
  if (cardId) {
    const data = await ROX.api.get(`/api/research/${cardId}`);
    card = data?.card || null;
  }
  const query = params.query || {};
  const seed = card || (query.code ? {
    title: `${query.stock || query.code}：是否值得继续研究？`,
    code: query.code,
    stock: query.stock,
    question: `${query.stock || query.code} 当前是否满足我的研究条件？`,
    facts: [`行情：${query.price || '--'}；数据状态：${query.data_status || '未标注'}；来源：${query.data_source || '未标注'}；截至：${query.as_of || '未标注'}`],
  } : {});
  container.innerHTML = `<div class="research-page"><div class="research-page-head"><div><div class="eyebrow">ROX LOOP / RESEARCH</div><h2 class="research-page-title">${card ? '继续完善研究卡' : '把一个想法变成可验证判断'}</h2><p class="research-page-subtitle">先写清事实、假设和反证，再决定是否行动。</p></div><button class="btn btn-secondary" data-route="/">回到今日</button></div><div class="card research-card-shell">${researchCardForm(seed)}${cardId ? `<div class="research-decision-footer"><div><strong>研究链已保存</strong><span>准备好后再记录正式决策，决策会保留这张研究卡的关联。</span></div><button class="btn btn-primary" data-action="record-card-decision" data-card-id="${cardId}" data-code="${ROX.escape(card.code || '')}" data-name="${ROX.escape(card.stock || '')}">记录关联决策</button></div>` : ''}</div></div>`;

  const form = document.getElementById('research-card-form');
  const riskButton = document.getElementById('research-risk-check');
  const riskResult = document.getElementById('research-risk-result');
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
      const risk = await ROX.api.get(`/api/research/${cardId}/risk-check`);
      renderRiskResult(risk, riskResult);
    } else {
      ROX.toast(result?.detail || '保存失败，请重试', 'error');
    }
  });
  container.querySelectorAll('[data-route]').forEach(button => button.addEventListener('click', () => ROX.navigate(button.dataset.route)));
});
