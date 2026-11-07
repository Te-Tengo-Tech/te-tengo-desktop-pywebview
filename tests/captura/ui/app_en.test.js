// Renders the window in English with app.js under Node: the tabs, the Cameras tab, the dialogs
// and the splash use the English catalog of textos.js, with no Spanish left from app.js.
// Usage: node app_en.test.js <app.js>  (the states come as JSON on stdin, from test_textos_web.py)
const assert = require('node:assert/strict');
const ui = require(process.argv[2]);
const E = JSON.parse(require('node:fs').readFileSync(0, 'utf8'));
const U = (o) => Object.assign({tab:'estado', sel:null, open:{}, toast:null, adv:{sub:'actividad', cam:null}, log:{filters:{}, q:'', paused:false, cut:0, open:null, lines:{}}, meters:{}, acts:[], actScope:'pc', diag:{step:'intro'}}, o || {});
// The words app.js itself writes in Spanish; Python sends its own texts already in English.
const ESPANOL = ['Cámaras', 'Estado', 'Avanzado', 'Habitación', 'Conexión', 'Buscar de nuevo', 'Vista previa', 'Esqueleto',
  'Esta PC', 'Vivienda de', 'Datos de la instalación', 'Minimizar', 'Cerrar', 'Secciones', 'Más información', 'Sin usar', 'En uso'];
const sinEspanol = (html, donde) => ESPANOL.forEach(p => assert.ok(!html.includes(p), donde+': «'+p+'» quedó en español'));

assert.equal(ui.setIdioma('en'), 'en');
const estado = ui.win(E.uno, U(), '');
assert.match(estado, /<span>Status<\/span>/);
assert.match(estado, /<span>Cameras<\/span>/);
assert.match(estado, /<span>Advanced<\/span>/);
assert.match(estado, /This PC: <b>Sala-Rosa<\/b>/);
assert.match(estado, /Rosa Huamán's home/);
assert.match(estado, /Installation details/);
assert.match(estado, /aria-label="Minimize"/);
sinEspanol(estado, 'Status');

// The Cameras tab with the preview of a camera in use and «What's shown» (Video, Skeleton).
const conEsqueleto = Object.assign({}, E.uno, {devices:E.uno.devices.map(d => Object.assign({}, d, {skel:true}))});
const camaras = ui.win(conEsqueleto, U({tab:'camaras'}), '');
assert.match(camaras, /Cameras on this PC<\/h1><p class="t-meta">Rooms are chosen in the app\.<\/p>/);
assert.match(camaras, /Connected cameras/);
assert.match(camaras, /In use · Sala/);
assert.match(camaras, /Search again/);
assert.match(camaras, /Preview · Webcam USB HD/);
assert.match(camaras, /aria-label="What's shown"/);
assert.match(camaras, /<span>Video<\/span>.*<span>Skeleton<\/span>/);
assert.match(camaras, /<dt>Room<\/dt><dd><b>Sala<\/b><span>Rename it in the Te Tengo app<\/span>/);
assert.match(camaras, /<dt>Connection<\/dt><dd><b class="ok">.*Connected<\/b><span>Over USB<\/span>/);
sinEspanol(camaras, 'Cameras');

// Advanced, the pairing screen, a dialog and the splash.
const avanzado = ui.win(Object.assign({}, E.uno, {advanced:false}), U({tab:'avanzado'}), '');
assert.match(avanzado, /Advanced mode/);
assert.match(avanzado, /See what happened/);
sinEspanol(avanzado, 'Advanced');
const vincular = ui.win(E.vincular, U(), '');
assert.match(vincular, /Link this PC with your phone/);
assert.match(vincular, /Expires in <span class="mono" id="pair-left">9:41<\/span>/);
assert.match(vincular, /K, Q, W, T, dash, M X H D|K Q W T, dash, M X H D/);
const salir = ui.dialog(E.tres, U({dlg:'salir'}));
assert.match(salir, /Quit Te Tengo Captura\?/);
assert.match(salir, /Falls stop being detected in Sala, Dormitorio and Pasillo\./);
assert.match(ui.bootWin({step:0, version:'1.0'}), /Starting….*Version 1\.0/);
assert.equal(ui.BOOT_STEPS[3], 'Finishing the update…');

// Numbers and dates follow the language: a point for decimals in English.
const reset = ui.dialog(Object.assign({}, E.tres, {dataBytes:3.2e9, upd:{ver:'0.5.0', os:'windows', notes:[]}}), U({dlg:'reset'}));
assert.match(reset, /Movements, video and clips \(3\.2 GB\)/);
assert.equal(ui.t('fmt.fecha', {d:'07', dd:7, m:'10', mes:ui.t('fmt.mes.9'), y:2026}), 'Oct 7, 2026');

// Back to Spanish: the same screen is the original one.
assert.equal(ui.setIdioma('es'), 'es');
assert.match(ui.win(E.uno, U({tab:'camaras'}), ''), /Cámaras de esta PC<\/h1><p class="t-meta">Las habitaciones se eligen en la app\.<\/p>/);
assert.equal(ui.setIdioma('fr'), 'es');  // anything else is Spanish
console.log('ok');
