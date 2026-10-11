// Renders the window with app.js under Node and checks the markup of the prototype's screens.
// Usage: node app.test.js <app.js>  (the states come as JSON on stdin, from test_puente.py)
const assert = require('node:assert/strict');
const ui = require(process.argv[2]);
const E = JSON.parse(require('node:fs').readFileSync(0, 'utf8'));
const U = (o) => Object.assign({tab:'estado', sel:null, open:{}, toast:null}, o || {});

// 01 Todo funciona: the title bar, the tab bar, one summary and a row per camera.
const html = ui.win(E.tres, U(), '');
assert.match(html, /<span>Te Tengo Captura<\/span>/);
assert.match(html, /pywebview-drag-region/);
assert.match(html, /aria-label="Minimizar"/);
assert.match(html, /aria-disabled="true" tabindex="-1" aria-label="Maximizar \(no disponible\)"/);
assert.match(html, /data-act="close" aria-label="Cerrar"/);
assert.match(html, /role="tablist" aria-label="Secciones"/);
assert.match(html, /id="tab-estado" aria-selected="true"/);
assert.match(html, /id="tab-camaras" aria-selected="false"/);
assert.match(html, /Esta PC: <b>Sala-Rosa<\/b>/);
assert.match(html, /Vivienda de Rosa Huamán/);
assert.match(html, /Jr\. Los Pinos 482, San Miguel, Lima/);
assert.match(html, /class="health ok" role="status"/);
assert.match(html, /Te Tengo está cuidando 3 habitaciones/);
assert.match(html, /Sala, Dormitorio y Pasillo · Todo funciona bien\./);
assert.equal((html.match(/class="crow"/g) || []).length, 3);
assert.match(html, /<b class="stx send">En línea<\/b><span class="t-meta">Todo funciona bien<\/span>/);
assert.match(html, /Logitech C920/);
assert.match(html, /Datos de la instalación/);
assert.match(html, /<dt>Instalación<\/dt><dd>22\/09\/2026<\/dd>/);
assert.match(html, /<dt>Programa<\/dt><dd>Te Tengo Captura 0\.5\.0<\/dd>/);
assert.match(html, /Las cámaras, las pausas, el consentimiento y las alertas se gestionan en la app Te Tengo\./);
assert.match(html, /Se inicia con Windows/);
assert.doesNotMatch(html, /details class="inst" data-k="inst" open/);  // folded by default
assert.match(ui.win(E.tres, U({open:{inst:true}}), ''), /data-k="inst" open/);

// 02 Una cámara en pausa.
const pausa = ui.win(E.pausa, U(), '');
assert.match(pausa, /class="health idle"/);
assert.match(pausa, /La sala está en pausa hasta las <span class="mono">\d\d:\d\d<\/span>/);
assert.match(pausa, /class="thumb art dim"/);

// 03 Esperando consentimiento: no button.
const consentimiento = ui.win(E.consentimiento, U(), '');
assert.match(consentimiento, /class="health warn"/);
assert.match(consentimiento, /Falta el consentimiento de Rosa/);
assert.doesNotMatch(consentimiento.split('class="health')[1].split('</div></div>')[0], /<button/);

// 04 Sin internet: the countdown is a patchable region with «Reintentar ahora».
const internet = ui.win(E.internet, U(), '');
assert.match(internet, /class="health offline"/);
assert.match(internet, /<span data-r="hd">Las cámaras siguen cuidando y los avisos esperan\. Volvemos a intentar en <span class="mono" id="retry">8<\/span> s\.<\/span>/);
assert.match(internet, /data-act="retryNow">.*Reintentar ahora<\/button>/);
assert.equal(ui.structure(E.internet), ui.structure(Object.assign({}, E.internet, {retry: 7, health: Object.assign({}, E.internet.health, {detalle_html: 'x'})})));

// 05 Una cámara no responde.
const perdida = ui.win(E.perdida, U(), '');
assert.match(perdida, /class="health warn lost"/);
assert.match(perdida, /class="crow lost"/);
assert.match(perdida, /data-act="rescan">.*Buscar de nuevo<\/button>/);

// 08 Un familiar ve en vivo.
const vivo = ui.win(E.vivo, U(), '');
assert.match(vivo, /class="health live"/);
assert.match(vivo, /Un familiar está viendo la sala en vivo/);
assert.match(vivo, /<b class="stx live">En vivo<\/b>/);

// Names from the API are escaped.
assert.match(ui.win(E.html, U(), ''), /Dormitorio &lt;b&gt;/);

// Cámaras: the webcams of this PC with their local preview.
const camaras = ui.win(E.tres, U({tab:'camaras', sel:'dormitorio'}), '');
assert.match(camaras, /id="tab-camaras" aria-selected="true"/);
assert.match(camaras, /Cámaras de esta PC/);
assert.match(camaras, /Cada cámara con su habitación\. Las habitaciones se eligen desde la app Te Tengo, en tu celular\./);
assert.match(camaras, /role="radiogroup" aria-labelledby="g-cams"/);
assert.match(camaras, /aria-checked="true" tabindex="0" data-act="selCam" data-arg="dormitorio"/);
assert.match(camaras, /En uso · Dormitorio/);
assert.match(camaras, /id="pv" data-clave="dormitorio"/);
assert.match(camaras, /La vista previa solo se ve en esta PC/);
assert.match(camaras, /Usa la vista previa para revisar que la cámara vea bien la habitación\./);
assert.match(camaras, /Cada cámara usa más la PC\. Si la detección se vuelve lenta, conecta algunas cámaras a otra PC\./);
const desconectada = ui.win(E.perdida, U({tab:'camaras', sel:'sala'}), '');
assert.match(desconectada, /Desconectada · Sala/);
assert.match(desconectada, /La cámara no responde: revisa el cable USB/);
assert.match(desconectada, /Sala sigue asignada a esta cámara y no pasa a otra\./);

// In-window notices when the state changes (proto.js).
assert.equal(ui.transition(null, E.tres), null);
assert.equal(ui.transition(E.internet, E.tres).text, 'Volvió internet. Se enviaron los avisos pendientes.');
assert.equal(ui.transition(E.perdida, E.uno).text, 'La Webcam USB HD volvió a responder.');
assert.match(ui.transition(E.uno, E.pausa).text, /^La familia pausó la cámara de la Sala desde la app hasta las \d\d:\d\d\.$/);
assert.equal(ui.transition(E.pausa, E.uno).text, 'La pausa terminó. Te Tengo vuelve a cuidar la Sala.');
assert.equal(ui.transition(E.consentimiento, E.uno).text, 'La familia registró el consentimiento en la app Te Tengo.');
assert.equal(ui.transition(E.uno, E.renombrada).text, 'La familia cambió el nombre de la habitación en la app: «Sala comedor».');
assert.equal(ui.transition(Object.assign({}, E.internet, {listo:false}), E.uno), null);

// The splash (screen 00).
const boot = ui.bootWin({pct: 34, step: 1, version: '0.5.0'});
assert.match(boot, /Abriendo las cámaras…/);
assert.match(boot, /Versión 0\.5\.0/);
assert.match(boot, /aria-valuenow="34"/);
assert.match(boot, /class="sp-mark"/);
console.log('ok');
