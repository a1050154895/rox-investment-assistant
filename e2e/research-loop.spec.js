const { test, expect } = require('@playwright/test');

async function register(page) {
  const username = `e2e_${Date.now()}`;
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

  await page.goto('/research');
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
  await page.getByLabel('状态').selectOption('ready');
  await page.getByRole('button', { name: '保存研究卡', exact: true }).click();
  await expect(page.getByText('研究卡已保存')).toBeVisible();

  await page.goto('/review');
  await expect(page.locator('.research-review-card')).toBeVisible();
  await expect(page.getByText('研究卡复盘')).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(await page.evaluate(() => innerWidth));
});
