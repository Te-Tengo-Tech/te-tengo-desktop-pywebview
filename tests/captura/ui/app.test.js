// Renders the status window with app.js under Node and checks the markup of screens 01–05.
// Usage: node app.test.js <app.js>  (the states come as JSON on stdin, from test_puente.py)
const assert = require('node:assert/strict');
const ui = require(process.argv[2]);
const E = JSON.parse(require('node:fs').readFileSync(0, 'utf8'));

const html = ui.win(E.enviando, '', null);
assert.match(html, /<span>Te Tengo Captura<\/span>/);
assert.match(html, /aria-label="Minimizar"/);
assert.match(html, /aria-disabled="true" tabindex="-1" aria-label="Maximizar \(no disponible\)"/);
assert.match(html, /data-act="close" aria-label="Cerrar"/);
assert.match(html, /pywebview-drag-region/);
assert.match(html, /Vivienda de Rosa Huamán/);
assert.match(html, /Jr\. Los Pinos 482, San Miguel, Lima/);
assert.match(html, /class="health ok" role="status"/);
assert.match(html, /Enviando video · conectado/);
assert.match(html, /Video cifrado · último envío hace 2 s/);
assert.match(html, /Cámara de esta casa/);
assert.match(html, /<b class="stx send">Enviando<\/b><span class="t-meta" data-r="cs">Hace 2 s<\/span>/);
assert.match(html, /Configurada por el equipo del proyecto/);
assert.match(html, /<dt>Webcam<\/dt><dd>Webcam USB HD \(1080p\)<span>USB · 1920 × 1080<\/span>/);
assert.match(html, /El nombre se cambia en la app Te Tengo/);
assert.match(html, /<dt>Instalación<\/dt><dd>22\/09\/2026<\/dd>/);
assert.match(html, /Solo lectura\. Esta PC usa una configuración fija; si algo no funciona, avisa al equipo del proyecto\./);
assert.match(html, /Las pausas, el consentimiento, el nombre de la habitación y las alertas se gestionan en la app Te Tengo\./);
assert.match(html, /Se inicia con Windows/);
assert.doesNotMatch(html, /class="thumb art dim"/);

const pausa = ui.win(E.pausa, '', null);
assert.match(pausa, /class="health idle"/);
assert.match(pausa, /En pausa hasta las <span class="mono">\d\d:\d\d<\/span>/);
assert.match(pausa, /class="thumb art dim"/);

const consentimiento = ui.win(E.consentimiento, '', null);
assert.match(consentimiento, /class="health warn"/);
assert.match(consentimiento, /consentimiento de Rosa en la app Te Tengo\./);
assert.doesNotMatch(consentimiento, /<button class="btn/);

const internet = ui.win(E.internet, '', null);
assert.match(internet, /class="health dark"/);
assert.match(internet, /reintentando en <span class="mono" id="retry">8<\/span> s/);
assert.match(internet, /<button class="btn btn-ondark btn-sm" data-act="retryNow">.*Reintentar ahora<\/button>/);
assert.match(internet, /<b class="stx off">Sin conexión<\/b><span class="t-meta" data-r="cs">Esperando internet/);

const webcam = ui.win(E.webcam, '', null);
assert.match(webcam, /class="health warn lost"/);
assert.match(webcam, /<button class="btn btn-secondary btn-sm" data-act="rescan">.*Buscar de nuevo<\/button>/);

// User-provided values are escaped.
const dormitorio = ui.win(E.dormitorio, '', null);
assert.match(dormitorio, /Dormitorio &lt;b&gt;/);
assert.doesNotMatch(dormitorio, /Dormitorio <b>/);

// The countdown only changes a [data-r] region: no full render, so focus stays put.
const despues = {...E.internet, retry: 7, health: {...E.internet.health, titulo_html: E.internet.health.titulo_html.replace('>8<', '>7<')}};
assert.equal(ui.structure(E.internet), ui.structure(despues));
assert.equal(ui.transition(E.internet, despues), null);

// Notices when the state changes, verbatim from proto.js.
assert.equal(ui.transition(E.webcam, E.enviando).text, 'Se volvió a conectar la Webcam USB HD (1080p). El envío se reanudó.');
assert.equal(ui.transition(E.internet, E.enviando).text, 'Conexión restablecida. El envío se reanudó.');
assert.equal(ui.transition(E.consentimiento, E.enviando).text, 'Consentimiento registrado en la app Te Tengo. Empezó el envío.');
assert.match(ui.transition(E.enviando, E.pausa).text, /^La familia pausó la cámara desde la app Te Tengo hasta las \d\d:\d\d\.$/);
assert.equal(ui.transition(E.pausa, E.enviando).text, 'La pausa terminó: el envío se reanudó.');
assert.equal(ui.transition(E.enviando, {...E.enviando, room: 'Sala comedor'}).text, 'La familia cambió el nombre de la habitación en la app: «Sala comedor».');
assert.equal(ui.transition(null, E.enviando), null);
assert.equal(ui.transition({...E.consentimiento, listo: false}, E.enviando), null);

// The in-window toast.
assert.match(ui.win(E.enviando, '', {kind: 'warn', icon: 'wifiOff', text: 'Aún sin internet. Seguimos intentando.'}), /<div class="wtoast warn" role="status">.*Aún sin internet\. Seguimos intentando\./);

// Every room of the prototype has its illustration, without people.
for (const room of ['Sala', 'Dormitorio', 'Cocina', 'Pasillo']) assert.match(ui.roomSVG(room), /^<svg class="room"/);
console.log('ok');
