const { test, expect } = require('@playwright/test');

async function register(page) {
  const username = `e2e_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
  await page.goto('/');
  await page.getByText('注册', { exact: true }).click();
  await page.getByLabel('用户名', { exact: true }).fill(username);
  await page.getByLabel('密码', { exact: true }).fill('E2ePassword123!');
  await page.getByRole('button', { name: '注册并进入', exact: true }).click();
  await expect(page.locator('#auth-gate')).toBeHidden();
}

test('mobile research loop reaches review statistics', async ({ page }) => {
  await register(page);
  await page.locator('#onboarding-overlay').evaluate((node) => node.classList.remove('onboarding-open'));

  await page.goto('/research/new');
  await expect(page.locator('#research-card-form')).toBeVisible();
  await expect(page.locator('.research-step')).toHaveCount(4);
  await expect(page.locator('.research-step').filter({ visible: true })).toHaveCount(1);

  await page.getByLabel('研究标题 *').fill('E2E 研究卡');
  await page.getByRole('button', { name: '下一步', exact: true }).click();
  await expect(page.locator('#research-step-status')).toHaveText('第 2 步 / 4');
  await page.getByLabel('研究问题').fill('核心问题是什么？');
  await page.getByLabel('核心假设').fill('假设可以被验证');
  await page.getByRole('button', { name: '下一步', exact: true }).click();
  await page.getByLabel('反证').fill('需求可能低于预期');
  await page.getByLabel('失效条件').fill('盈利预期下修');
  await page.getByRole('button', { name: '下一步', exact: true }).click();
  await page.locator('select[name="status"]').selectOption('ready');
  await page.getByRole('button', { name: '保存研究卡', exact: true }).click();
  await expect(page.getByText('研究卡已保存')).toBeVisible();

  await page.goto('/review');
  await expect(page.locator('.research-review-card')).toBeVisible({ timeout: 20_000 });
  await expect(page.getByText('研究卡复盘')).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(await page.evaluate(() => innerWidth));
});

test('observation deck remains usable without watchlist', async ({ page }) => {
  await register(page);
  await page.locator('#onboarding-overlay').evaluate((node) => node.classList.remove('onboarding-open'));
  await page.goto('/observe');
  await expect(page.getByText('研究对象观察台')).toBeVisible();
  await expect(page.getByText('还没有观察对象。')).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(await page.evaluate(() => innerWidth));
});

test('observation deck links watchlist, chart, research and decisions', async ({ page }) => {
  await register(page);
  await page.route('**/api/watchlist/**', route => route.fulfill({
    contentType: 'application/json',
    body: JSON.stringify({ watchlist: [
      { id: 1, code: '600519', name: '贵州茅台', price_name: '贵州茅台', price: 1520, change_pct: 1.25 },
      { id: 2, code: '510300', name: '沪深300ETF', price_name: '沪深300ETF', price: 4.12, change_pct: -0.48 },
    ], count: 2 }),
  }));
  await page.route('**/api/research/related/**', route => route.fulfill({
    contentType: 'application/json',
    body: JSON.stringify({
      cards: [{ id: 9, title: '估值跟踪', status_label: '研究中', evidence_counts: { facts: 2, counter: 1 } }],
      decisions: [{ date: '2026-08-28', action: '持有', result: '待观察', result_pct: null }],
    }),
  }));
  await page.route('**/api/stock/**/kline*', route => route.fulfill({
    contentType: 'application/json',
    body: JSON.stringify({ candles: [
      { date: '2026-08-26', close: 1500 },
      { date: '2026-08-27', close: 1512 },
      { date: '2026-08-28', close: 1520 },
    ] }),
  }));

  await page.goto('/observe');
  await expect(page.locator('.observe-item').first()).toContainText('贵州茅台');
  await expect(page.locator('.observe-price strong')).toHaveText('1520.00');
  await expect(page.locator('#observe-chart canvas').first()).toBeVisible();
  await expect(page.locator('#observe-stream')).toContainText('估值跟踪');
  await expect(page.locator('#observe-stream')).toContainText('持有');
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(await page.evaluate(() => innerWidth));
});
