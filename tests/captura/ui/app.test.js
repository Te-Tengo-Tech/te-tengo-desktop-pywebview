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
assert.match(html, /Te Tengo cuida 3 habitaciones/);
assert.match(html, /<span data-r=\"hd\">Todo funciona bien\.<\/span>/);
assert.equal((html.match(/class="crow"/g) || []).length, 3);
assert.match(html, /<b class="stx send">En línea<\/b><\/span>/);
assert.match(html, /Logitech C920/);
assert.match(html, /Datos de la instalación/);
assert.match(html, /<dt>Instalación<\/dt><dd>22\/09\/2026<\/dd>/);
assert.match(html, /<dt>Programa<\/dt><dd>Te Tengo Captura 0\.5\.0<\/dd>/);
assert.match(html, /Cámaras, pausas, consentimiento y alertas: en la app/);
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
assert.match(internet, /<span data-r="hd">Las cámaras siguen cuidando; los avisos esperan\. Reintento en <span class="mono" id="retry">8<\/span> s\.<\/span>/);
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
assert.match(camaras, /Las habitaciones se eligen en la app\./);
assert.match(camaras, /role="radiogroup" aria-labelledby="g-cams"/);
assert.match(camaras, /aria-checked="true" tabindex="0" data-act="selCam" data-arg="dormitorio"/);
assert.match(camaras, /En uso · Dormitorio/);
assert.match(camaras, /id="pv" data-clave="dormitorio"/);
assert.match(camaras, /Solo se ve en esta PC/);
assert.match(camaras, /Usa la vista previa para revisar el encuadre\./);
assert.match(camaras, /Si la detección va lenta, pasa alguna cámara a otra PC\./);
const desconectada = ui.win(E.perdida, U({tab:'camaras', sel:'sala'}), '');
assert.match(desconectada, /Desconectada · Sala/);
assert.match(desconectada, /No responde: revisa el cable USB/);
assert.match(desconectada, /Sala sigue asignada a esta cámara\. Conéctala y pulsa Buscar de nuevo\./);

// In-window notices when the state changes (proto.js).
assert.equal(ui.transition(null, E.tres), null);
assert.equal(ui.transition(E.internet, E.tres).text, 'Volvió internet. Avisos enviados.');
assert.equal(ui.transition(E.perdida, E.uno).text, 'La Webcam USB HD volvió a responder.');
assert.match(ui.transition(E.uno, E.pausa).text, /^La familia pausó la Sala hasta las \d\d:\d\d\.$/);
assert.equal(ui.transition(E.pausa, E.uno).text, 'Pausa terminada: vuelve a cuidar la Sala.');
assert.equal(ui.transition(E.consentimiento, E.uno).text, 'Consentimiento registrado en la app.');
assert.equal(ui.transition(E.uno, E.renombrada).text, 'Habitación renombrada en la app: «Sala comedor».');
assert.equal(ui.transition(Object.assign({}, E.internet, {listo:false}), E.uno), null);

// The splash (screen 00).
const boot = ui.bootWin({pct: 34, step: 1, version: '0.5.0'});
assert.match(boot, /Abriendo las cámaras…/);
assert.match(boot, /Versión 0\.5\.0/);
assert.match(boot, /aria-valuenow="34"/);
assert.match(boot, /class="sp-mark"/);
// Vincular esta PC (D-28.1): QR, the code letter by letter, countdown; offline; 90 days.
const vincular = ui.win(E.vincular, U(), '');
assert.match(vincular, /Vincula esta PC con tu celular/);
assert.match(vincular, /Abre la app Te Tengo<\/span>/);
assert.match(vincular, /Ajustes.*PCs y cámaras.*Agregar PC/);
assert.match(vincular, /Escanea este código/);
assert.match(vincular, /Esta PC: <b>Sala-Rosa<\/b>/);
assert.match(vincular, /<svg class="qr" viewBox="-2 -2 \d+ \d+" role="img" aria-label="Código QR para vincular esta PC"/);
assert.match(vincular, /class="qr-logo"/);
assert.match(vincular, /O escribe este código en la app:/);
assert.match(vincular, /<span aria-hidden="true">KQWT-MXHD<\/span><span class="sr">K Q W T, guion, M X H D<\/span>/);
assert.match(vincular, /app\.tetengo\.reqsai\.tech\/vincular/);
assert.match(vincular, /Vence en <span class="mono" id="pair-left">9:41<\/span>/);
assert.match(vincular, /Esperando aprobación en el celular…/);
assert.match(vincular, /¿Error en el celular\?/);
assert.doesNotMatch(vincular, /class="tabbar"/);
const renovado = ui.win(E.renovado, U(), '');
assert.match(renovado, /Código nuevo · el anterior venció/);
assert.match(renovado, /class="pair-left low"/);
const sinInternet = ui.win(E.sinInternet, U(), '');
assert.match(sinInternet, /Conecta esta PC a internet\. Reintentamos en <span class="mono" id="retry" data-r="pr">0:25<\/span>\./);
assert.match(sinInternet, /El código aparece con conexión/);
assert.doesNotMatch(sinInternet, /class="qr"/);
assert.match(ui.win(E.noventa, U(), ''), /Más de 90 días sin conexión<\/b><span>Vincúlala de nuevo\./);
assert.equal(ui.structure(E.vincular), ui.structure(Object.assign({}, E.vincular, {pair: Object.assign({}, E.vincular.pair, {left: 100})})));

// Vinculada (D-28.4), rechazada (D-28.5), quitada (D-31.2).
const vinculada = ui.win(E.vinculada, U(), '');
assert.match(vinculada, /Vinculada a la casa de Rosa Huamán/);
assert.match(vinculada, /Aprobó Carmen a las <span class="mono">10:31<\/span> · <b>Sala-Rosa<\/b>/);
assert.match(vinculada, /Ahora elige las cámaras en la app<\/b>/);
assert.match(vinculada, /Detectamos 3 cámaras/);
assert.match(vinculada, /Falta el consentimiento de Rosa/);
assert.match(vinculada, /data-act="toEstado"/);
const rechazada = ui.win(E.rechazada, U(), '');
assert.match(rechazada, /No se vinculó esta PC/);
assert.match(rechazada, /Alguien eligió «No reconozco esta PC» en la app\./);
assert.match(rechazada, /data-act="otherCode">.*Mostrar otro código/);
const quitada = ui.win(E.quitada, U(), '');
assert.match(quitada, /Se quitó de la casa de Rosa Huamán/);
assert.match(quitada, /La familia la quitó desde la app a las <span class="mono">11:20<\/span>\.<\/p>/);
assert.match(quitada, /data-act="pairAgain">.*Vincular de nuevo/);

// A linked PC: «Desvincular esta PC» in «Cámaras» and its dialog (CA-31.4, CA-31.6).
const pcCamaras = ui.win(E.pcPrincipal, U({tab:'camaras'}), '');
assert.match(pcCamaras, /Esta PC: Sala-Rosa/);
assert.match(pcCamaras, /Vinculada por Carmen el 23\/09\/2026/);
assert.match(pcCamaras, /data-act="unlinkAsk">.*Desvincular<\/button>/);
assert.match(pcCamaras, /Sin usar/);
assert.doesNotMatch(ui.win(E.tres, U({tab:'camaras'}), ''), /unlinkAsk/);  // an installation
const dialogo = ui.win(E.pcPrincipal, U({tab:'camaras', dlg:'unlink'}), '');
assert.match(dialogo, /role="dialog" aria-modal="true"/);
assert.match(dialogo, /¿Desvincular esta PC\?/);
assert.match(dialogo, /La familia recibirá un aviso\./);
assert.match(dialogo, /Borrar también los datos de esta PC \(3,2 GB\)/);
assert.match(dialogo, /Movimientos, video y clips\.<\/span>/);
assert.match(dialogo, /data-act="dlgClose">Cancelar/);
assert.match(dialogo, /data-act="unlinkDo">.*Desvincular<\/button>/);
assert.equal(ui.transition(E.vinculada, E.pcPrincipal), null);

// Several cameras: the violet light while the app previews a webcam (CA-29.7), «Elegir aquí».
const mirando = ui.win(E.pcMirando, U({tab:'camaras'}), '');
assert.match(mirando, /class="cpick peeking"/);
assert.match(mirando, /Un familiar está viendo esta cámara para elegirla · No se graba/);
assert.match(ui.win(E.pcMirando, U(), ''), /Un familiar está viendo la Logitech C920 para elegirla/);
assert.match(mirando, /data-act="hereOn">.*Elegir aquí \(si estás instalando\)/);
const aqui = ui.win(E.pcPrincipal, U({tab:'camaras', here:true, sel:'id-2', rooms:[{id:'a-1', nombre:'Cocina', camaras:[{id:'x', pc:'Cocina-Rosa', estaPc:false}]}], pick:{room:'Sala', otherOn:false, other:'', err:null}}), '');
assert.match(aqui, /Elegir aquí, si estás instalando/);
assert.match(aqui, /Elige cada cámara, mira su vista previa y di en qué habitación está\. La familia lo verá en la app\./);
assert.match(aqui, /data-act="hereOff">.*Volver/);
assert.match(aqui, /¿En qué habitación está\?/);
assert.match(aqui, /aria-disabled="true" title="Ya tiene cámara en la PC Cocina-Rosa"><span>Cocina<\/span><small>Ya tiene cámara · Cocina-Rosa<\/small>/);
assert.match(aqui, /class="chip2 sel" aria-pressed="true" data-act="pickRoom" data-arg="Sala"/);
assert.match(aqui, /data-act="useCam">.*Usar esta cámara/);
assert.match(aqui, /Por privacidad, Te Tengo no admite cámaras en el baño\./);
const duplicada = ui.win(E.pcPrincipal, U({tab:'camaras', here:true, sel:'id-2', rooms:[], pick:{room:null, otherOn:true, other:'sala', err:'dup', errRoom:'Sala', errPc:'Sala-Rosa'}}), '');
assert.match(duplicada, /Ya hay una cámara en la habitación Sala \(PC Sala-Rosa\)\. Por ahora, cada habitación usa una sola cámara\./);
assert.match(duplicada, /id="room-other" value="sala"/);
const listo = o => Object.assign({}, o, {listo: true});
assert.equal(ui.transition(listo(E.pcPrincipal), listo(E.pcConSala)).text, 'La familia eligió la Webcam USB HD para la Sala');
assert.equal(ui.transition(listo(E.pcConSala), listo(E.pcPrincipal)).text, 'La familia dejó de usar la Webcam USB HD: ya no cuida la Sala.');
console.log('ok');
