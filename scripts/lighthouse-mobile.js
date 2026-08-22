const fs = require('node:fs');
const lighthouseModule = require('lighthouse');
const lighthouse = lighthouseModule.default || lighthouseModule;
const chromeLauncher = require('chrome-launcher');

(async () => {
  const port = Number(process.env.LH_PORT || 8783);
  const outputDir = process.env.LH_OUTPUT_DIR || 'lighthouse-report';
  fs.mkdirSync(outputDir, { recursive: true });
  const chrome = await chromeLauncher.launch({ chromeFlags: ['--headless', '--no-sandbox', '--disable-gpu'] });
  try {
    const result = await lighthouse(`http://127.0.0.1:${port}/`, {
      port: chrome.port,
      output: ['json', 'html'],
      logLevel: 'error',
      onlyCategories: ['accessibility', 'best-practices', 'performance'],
      formFactor: 'mobile',
      screenEmulation: { mobile: true, width: 390, height: 844, deviceScaleFactor: 2 },
      throttlingMethod: 'simulate',
    });
    const reports = result.report;
    const json = typeof reports[0] === 'string' ? reports[0] : JSON.stringify(reports[0]);
    fs.writeFileSync(`${outputDir}/mobile.json`, json);
    fs.writeFileSync(`${outputDir}/mobile.html`, reports[1] || '');
    const scores = result.lhr.categories;
    const summary = {
      accessibility: scores.accessibility?.score,
      bestPractices: scores['best-practices']?.score,
      performance: scores.performance?.score,
    };
    console.log(JSON.stringify(summary, null, 2));
    if ((summary.accessibility ?? 0) < 0.85 || (summary.bestPractices ?? 0) < 0.85) process.exitCode = 1;
  } finally {
    await chrome.kill();
  }
})();
