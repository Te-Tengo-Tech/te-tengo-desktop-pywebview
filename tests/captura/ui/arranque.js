// Screenshots the splash page at 2x (480 × 300 window) with the bar at 34 % and «Iniciando…».
// Usage: node arranque.js <playwright> <chromium> <arranque.html> <out.png>
const [playwright, chromium, pagina, salida] = process.argv.slice(2);
(async () => {
  const browser = await require(playwright).chromium.launch({ executablePath: chromium });
  const page = await browser.newPage({ viewport: { width: 480, height: 300 }, deviceScaleFactor: 2, reducedMotion: 'reduce' });
  await page.goto('file://' + pagina);
  await page.evaluate(() => window.ttg.arranque(34, 0, '1.0'));
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(1800);  // the symbol assembles in about 1.5 s
  await page.screenshot({ path: salida });
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
