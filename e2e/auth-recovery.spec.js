// 找回密码 / 邮箱验证 — 移动端关键路径回归。
// E2E 环境未配置 SMTP：忘记密码入口应如实说明；坏令牌落地页应诚实报错。
import { test, expect } from '@playwright/test';

async function register(page) {
  const username = `e2e_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
  await page.goto('/');
  await page.getByText('注册', { exact: true }).click();
  await page.getByLabel('用户名', { exact: true }).fill(username);
  await page.getByLabel('密码', { exact: true }).fill('E2ePassword123!');
  await page.getByRole('button', { name: '注册并进入', exact: true }).click();
  await expect(page.locator('#auth-gate')).toBeHidden();
  return username;
}

test.describe('auth recovery', () => {
  test('login gate shows forgot-password entry and register shows optional email', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('#auth-gate')).toBeVisible();
    await expect(page.locator('#auth-forgot')).toBeVisible();
    await expect(page.locator('#auth-email-group')).toBeHidden();

    await page.getByText('注册', { exact: true }).click();
    await expect(page.locator('#auth-email-group')).toBeVisible();
    await expect(page.locator('#auth-forgot')).toBeHidden();
    await expect(await page.evaluate(() => document.documentElement.scrollWidth))
      .toBeLessThanOrEqual(await page.evaluate(() => innerWidth));
  });

  test('forgot password without mail service explains honestly', async ({ page }) => {
    await page.goto('/');
    await page.locator('#auth-forgot').click();
    await expect(page.locator('#modal-overlay')).toHaveClass(/open/);
    // E2E 服务器未配置 SMTP，必须如实说明而不是提供假入口
    await expect(page.getByText('未配置邮件通道')).toBeVisible();
    await page.locator('#modal-overlay button[data-action="close-modal"]').first().click();
    await expect(page.locator('#modal-overlay')).not.toHaveClass(/open/);
  });

  test('reset-password with malformed token shows honest error', async ({ page }) => {
    await page.goto('/reset-password?token=bad');
    await expect(page.getByText('重置链接无效或已过期')).toBeVisible();
    await expect(await page.evaluate(() => document.documentElement.scrollWidth))
      .toBeLessThanOrEqual(await page.evaluate(() => innerWidth));
  });

  test('reset-password with unknown token reports backend error on submit', async ({ page }) => {
    const fakeToken = 'x'.repeat(43);
    await page.goto(`/reset-password?token=${fakeToken}`);
    await page.getByLabel('新密码', { exact: true }).fill('E2eNewPass123!');
    await page.getByLabel('确认新密码', { exact: true }).fill('E2eNewPass123!');
    await page.getByRole('button', { name: '确认重置', exact: true }).click();
    await expect(page.locator('#reset-error')).toBeVisible();
    await expect(page.locator('#reset-error')).toContainText('重置链接无效或已过期');
  });

  test('verify-email with unknown token shows honest error', async ({ page }) => {
    const fakeToken = 'y'.repeat(43);
    await page.goto(`/verify-email?token=${fakeToken}`);
    await expect(page.getByText('验证链接无效或已过期')).toBeVisible();
    await expect(await page.evaluate(() => document.documentElement.scrollWidth))
      .toBeLessThanOrEqual(await page.evaluate(() => innerWidth));
  });
});
