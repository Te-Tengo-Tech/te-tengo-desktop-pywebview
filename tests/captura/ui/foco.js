// The retry countdown updates in place: the focused «Reintentar ahora» keeps the focus.
// Usage: node foco.js <playwright> <chromium> <index.html>  (state 04 as JSON on stdin)
const [playwright, chromium, index] = process.argv.slice(2);
const E = JSON.parse(require('node:fs').readFileSync(0, 'utf8'));
(async () => {
  const browser = await require(playwright).chromium.launch({ executablePath: chromium });
  const page = await browser.newPage({ viewport: { width: 960, height: 640 } });
  await page.goto('file://' + index);
  await page.evaluate(e => window.ttg.actualizar(e), E);
  await page.focus('[data-act="retryNow"]');
  for (const n of [7, 6, 5]) {
    const e = {...E, retry: n, health: {...E.health, titulo_html: E.health.titulo_html.replace(/>\d+</, '>' + n + '<')}};
    await page.evaluate(e => window.ttg.actualizar(e), e);
  }
  const r = await page.evaluate(() => ({act: document.activeElement.dataset.act, retry: document.getElementById('retry').textContent, status: document.querySelector('.health').getAttribute('role')}));
  await browser.close();
  if (r.act !== 'retryNow' || r.retry !== '5' || r.status !== 'status') { console.error(JSON.stringify(r)); process.exit(1); }
})().catch(e => { console.error(e); process.exit(1); });
