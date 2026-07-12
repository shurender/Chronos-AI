// Capture script used in the Codex in-app browser Node REPL.
// It assumes `browser`, `tab`, and the browser runtime have been initialized.
// Output directory: hackathon-demo/assets/screens

var fs = await import('node:fs/promises');
var outDir = 'D:/Chronos-AI Hackathon/Chronos-AI/hackathon-demo/assets/screens';
var viewportCap = await browser.capabilities.get('viewport');
await viewportCap.set({ width: 1920, height: 1080 });

async function saveShot(name) {
  const bytes = await tab.screenshot({ fullPage: false });
  await fs.writeFile(`${outDir}/${name}.png`, Buffer.from(bytes));
}

await tab.goto('http://localhost:5173/');
await tab.playwright.waitForLoadState({ state: 'domcontentloaded', timeoutMs: 10000 });
await tab.playwright.waitForTimeout(3500);
await saveShot('01-landing');

await tab.playwright.getByRole('button', { name: 'Launch Program' }).first().click({ timeoutMs: 10000 });
await tab.playwright.waitForTimeout(2200);
await saveShot('02-connect-data');

await tab.playwright.getByText('Use sample demo data', { exact: true }).click({ timeoutMs: 10000 });
await tab.playwright.waitForTimeout(3000);
await saveShot('03-ingesting');

for (let i = 0; i < 70; i++) {
  await tab.playwright.waitForTimeout(1500);
  const body = await tab.playwright.locator('body').innerText({ timeoutMs: 10000 });
  if (body.includes('Define Your Decision')) break;
}
await saveShot('04-define-empty');

await tab.playwright.getByPlaceholder('What decision are you facing?').fill('Should I position my portfolio toward AI product engineering roles or full-stack software engineering roles?', { timeoutMs: 10000 });
await tab.playwright.getByPlaceholder('What does success look like?').fill('Maximize internship and job opportunities while showcasing my strongest technical projects.', { timeoutMs: 10000 });
await tab.playwright.getByPlaceholder('e.g. limited runway').fill('Limited time before applications; need a polished portfolio and clear positioning.', { timeoutMs: 10000 });
await tab.playwright.getByPlaceholder('e.g. remote, US-based').fill('Remote or US/EU early-career software and AI product roles.', { timeoutMs: 10000 });
var textInputs = await tab.playwright.locator('input[type="text"]').all();
await textInputs[3].fill('Position as AI product engineering', { timeoutMs: 10000 });
await textInputs[4].fill('Position as full-stack software engineering', { timeoutMs: 10000 });
await textInputs[5].fill('Keep the portfolio broad and project-focused', { timeoutMs: 10000 });
await saveShot('05-define-filled');

await tab.playwright.getByRole('button', { name: 'Run Simulation' }).click({ timeoutMs: 10000 });
await tab.playwright.waitForTimeout(2500);
await saveShot('06-simulating');

for (let i = 0; i < 70; i++) {
  await tab.playwright.waitForTimeout(1500);
  const body = await tab.playwright.locator('body').innerText({ timeoutMs: 10000 });
  if (body.includes('Simulated Futures')) break;
}
await saveShot('07-timelines');

await tab.playwright.getByRole('button', { name: 'Memory Graph' }).click({ timeoutMs: 10000 });
await tab.playwright.waitForTimeout(2500);
await saveShot('08-memory-graph');

await tab.playwright.getByRole('button', { name: 'Timeline Branches' }).click({ timeoutMs: 10000 });
await tab.playwright.waitForTimeout(700);
await tab.playwright.getByRole('button', { name: 'Talk to Future Self' }).click({ timeoutMs: 10000 });
await tab.playwright.waitForTimeout(1200);
await saveShot('09-future-self-empty');

await tab.playwright.getByPlaceholder('Ask your future self…').fill('Based on my portfolio evidence and this simulation, what should I prioritize next?', { timeoutMs: 10000 });
await tab.playwright.getByRole('button', { name: 'Send' }).click({ timeoutMs: 10000 });
for (let i = 0; i < 70; i++) {
  await tab.playwright.waitForTimeout(1500);
  const body = await tab.playwright.locator('body').innerText({ timeoutMs: 10000 });
  if (body.includes('FUTURE_SELF')) break;
}
await saveShot('10-future-self-answer');
