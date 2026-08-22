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

test('mobile drawer navigation opens, navigates and closes', async ({ page }) => {
  await register(page);
  await page.locator('#onboarding-overlay').evaluate((node) => node.classList.remove('onboarding-open'));

  // 抽屉默认收起，导航项不可见（对键盘/读屏不可达）
  await expect(page.locator("#app-sidebar .nav-item[data-route='/research']")).toBeHidden();

  // 打开抽屉
  await page.getByRole('button', { name: '打开导航' }).click();
  await expect(page.locator('#app-sidebar')).toHaveClass(/nav-open/);
  await expect(page.locator("#app-sidebar .nav-item[data-route='/research']")).toBeVisible();

  // 点导航项：跳转并自动收起
  await page.locator("#app-sidebar .nav-item[data-route='/research']").click();
  await expect(page.locator('#research-card-form')).toBeVisible();
  await expect(page.locator('#app-sidebar')).not.toHaveClass(/nav-open/);
});

test('drawer closes via backdrop and escape', async ({ page }) => {
  await register(page);
  await page.locator('#onboarding-overlay').evaluate((node) => node.classList.remove('onboarding-open'));

  // 遮罩关闭
  await page.getByRole('button', { name: '打开导航' }).click();
  await page.locator('#nav-backdrop').click({ position: { x: 350, y: 100 } });
  await expect(page.locator('#app-sidebar')).not.toHaveClass(/nav-open/);

  // ESC 关闭
  await page.getByRole('button', { name: '打开导航' }).click();
  await page.keyboard.press('Escape');
  await expect(page.locator('#app-sidebar')).not.toHaveClass(/nav-open/);
});

test('theme switches between dark and light and persists', async ({ page }) => {
  await register(page);
  await page.locator('#onboarding-overlay').evaluate((node) => node.classList.remove('onboarding-open'));

  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');

  // 从抽屉打开设置（应自动收起抽屉且面板可点）
  await page.getByRole('button', { name: '打开导航' }).click();
  await page.locator("#app-sidebar .sidebar-bottom .nav-item[data-action='open-settings']").click();
  await expect(page.locator('#app-sidebar')).not.toHaveClass(/nav-open/);
  await expect(page.locator('#settings-panel')).toHaveClass(/open/);

  await page.locator("[data-settings-tab='interface']").click();
  await page.locator('#set-theme').selectOption('light');
  await page.locator("#settings-body button[data-action='save-settings']").click();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');

  // 刷新后浅色持久
  await page.reload();
  await page.locator('#onboarding-overlay').evaluate((node) => node.classList.remove('onboarding-open'));
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');
});
