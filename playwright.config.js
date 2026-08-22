const { defineConfig, devices } = require('@playwright/test');
const python = process.env.PYTHON_BIN || '.venv/bin/python';

module.exports = defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  fullyParallel: true,
  reporter: [['list'], ['html', { outputFolder: 'playwright-report', open: 'never' }]],
  use: {
    baseURL: 'http://127.0.0.1:8783',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  webServer: {
    command: `ENVIRONMENT=test SECRET_KEY=$E2E_SECRET_KEY DATABASE_URL=sqlite:///data/e2e.db ${python} -m uvicorn app.main:app --host 127.0.0.1 --port 8783`,
    url: 'http://127.0.0.1:8783/health',
    reuseExistingServer: false,
    timeout: 120_000,
  },
  projects: [
    { name: 'chromium-mobile', use: { ...devices['Pixel 5'] } },
  ],
});
