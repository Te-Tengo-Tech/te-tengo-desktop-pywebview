// Screenshots the real window page in Chromium for each state (JSON on stdin) at 2x, like the
// prototype PNGs. Usage: node pantallas.js <playwright> <chromium> <index.html> <out dir>
const [playwright, chromium, index, salida] = process.argv.slice(2);
const estados = JSON.parse(require('node:fs').readFileSync(0, 'utf8'));
(async () => {
  const browser = await require(playwright).chromium.launch({ executablePath: chromium });
  const page = await browser.newPage({ viewport: { width: 960, height: 640 }, deviceScaleFactor: 2, reducedMotion: 'reduce' });
  for (const [nombre, estado] of Object.entries(estados)) {
    await page.goto('file://' + index);
    await page.evaluate(e => window.ttg.actualizar(e), estado);
    await page.evaluate(() => document.fonts.ready);
    await page.waitForTimeout(200);
    await page.screenshot({ path: salida + '/' + nombre + '.png' });
  }
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
