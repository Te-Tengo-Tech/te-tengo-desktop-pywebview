// Renders the window with app.js under Node and checks the markup of the prototype's screens.
// Usage: node app.test.js <app.js>  (the states come as JSON on stdin, from test_puente.py)
const assert = require('node:assert/strict');
const ui = require(process.argv[2]);
const E = JSON.parse(require('node:fs').readFileSync(0, 'utf8'));
const U = (o) => Object.assign({tab:'estado', sel:null, open:{}, toast:null, adv:{sub:'actividad', cam:null}, log:{filters:{}, q:'', paused:false, cut:0, open:null, lines:{}}, meters:{}, acts:[], actScope:'pc', diag:{step:'intro'}}, o || {});

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
assert.match(mirando, /Un familiar la mira para elegirla · No se graba/);
assert.match(ui.win(E.pcMirando, U(), ''), /Un familiar mira la Logitech C920 para elegirla/);
assert.match(mirando, /data-act="hereOn">.*Elegir aquí \(si estás instalando\)/);
const aqui = ui.win(E.pcPrincipal, U({tab:'camaras', here:true, sel:'id-2', rooms:[{id:'a-1', nombre:'Cocina', camaras:[{id:'x', pc:'Cocina-Rosa', estaPc:false}]}], pick:{room:'Sala', otherOn:false, other:'', err:null}}), '');
assert.match(aqui, /Elegir aquí, si estás instalando/);
assert.match(aqui, /Elige la habitación de cada cámara\. La familia lo verá en la app\./);
assert.match(aqui, /data-act="hereOff">.*Volver/);
assert.match(aqui, /¿En qué habitación está\?/);
assert.match(aqui, /aria-disabled="true" title="Ya tiene cámara en la PC Cocina-Rosa"><span>Cocina<\/span><small>Ya tiene cámara · Cocina-Rosa<\/small>/);
assert.match(aqui, /class="chip2 sel" aria-pressed="true" data-act="pickRoom" data-arg="Sala"/);
assert.match(aqui, /data-act="useCam">.*Usar esta cámara/);
assert.match(aqui, /Por privacidad, no se admiten cámaras en el baño\./);
const duplicada = ui.win(E.pcPrincipal, U({tab:'camaras', here:true, sel:'id-2', rooms:[], pick:{room:null, otherOn:true, other:'sala', err:'dup', errRoom:'Sala', errPc:'Sala-Rosa'}}), '');
assert.match(duplicada, /Sala ya tiene cámara \(PC Sala-Rosa\)\. Una cámara por habitación\./);
assert.match(duplicada, /id="room-other" value="sala"/);
const listo = o => Object.assign({}, o, {listo: true});
assert.equal(ui.transition(listo(E.pcPrincipal), listo(E.pcConSala)).text, 'La familia eligió la Webcam USB HD para la Sala');
assert.equal(ui.transition(listo(E.pcConSala), listo(E.pcPrincipal)).text, 'La familia dejó de usar la Webcam USB HD: ya no cuida la Sala.');
// Avanzado (US-32 to US-34): off by default, then the live log, the meters and the activity.
const apagado = ui.win(E.avanzadoApagado, U({tab:'avanzado'}), '');
assert.match(apagado, /id="tab-avanzado" aria-selected="true"/);
assert.match(apagado, /Qué detecta cada cámara y por qué avisa\. Nada sale de esta PC\./);
assert.match(apagado, /role="switch" aria-checked="false" aria-labelledby="adv-l" data-act="advToggle"/);
assert.doesNotMatch(apagado, /Registro en vivo/);
assert.doesNotMatch(apagado, /Exportar diagnóstico/);
assert.match(apagado, /Aún no hay actividad<\/b>/);
const ADV = o => U(Object.assign({tab:'avanzado', adv:{sub:'registro', cam:'c1'}, log:{filters:{persona:true, evento:true, descarte:true, conexion:true, programa:true}, q:'', paused:false, cut:0, open:null, lines:{}}, meters:{}, acts:[], actScope:'pc', diag:{step:'intro'}}, o||{}));
const lineas = [{id:1, t:'10:41:50', k:'persona', tone:'persona', i:'person', m:'Persona detectada en la Sala', x:'2026-09-23T10:41:50.111-05:00 INFO pose persona=1'},
  {id:2, t:'10:41:52', k:'evento', tone:'caida', i:'warn', m:'Caída: en el suelo. Aviso enviado', x:'2026-09-23T10:41:52.000-05:00 WARN clasificador fase=CAIDA'}];
const vacio = ui.win(E.avanzado, ADV(), '');
assert.match(vacio, /Modo avanzado<\/b> · Nada sale de esta PC\./);
assert.match(vacio, /Aún no pasa nada en esta cámara/);
assert.match(vacio, /data-act="diagOpen">.*Exportar diagnóstico/);
assert.match(vacio, /role="radiogroup" aria-labelledby="cam-l"><button role="radio" aria-checked="true" data-act="advCam" data-arg="c1">Sala/);
const conLineas = ui.win(E.avanzado, ADV({log:{filters:{persona:true, evento:true, descarte:true, conexion:true, programa:true}, q:'', paused:false, cut:0, open:2, lines:{c1:lineas}}}), '');
assert.match(conLineas, /role="log" aria-label="Registro en vivo de Sala"/);
assert.match(conLineas, /<div class="lline caida"><time>10:41:52<\/time>/);
assert.match(conLineas, /<span class="code">2026-09-23T10:41:52\.000-05:00 WARN clasificador fase=CAIDA<\/span>/);
assert.match(conLineas, /data-act="copyTech" data-arg="2">.*Copiar/);
assert.match(conLineas, /aria-label="Ver línea técnica">Técnica/);
assert.match(conLineas, /<span class="cnt" id="cnt-evento">1<\/span>/);
const buscada = ui.win(E.avanzado, ADV({log:{filters:{persona:true, evento:true, descarte:true, conexion:true, programa:true}, q:'escalera', paused:false, cut:0, open:null, lines:{c1:lineas}}}), '');
assert.match(buscada, /No hay líneas con «escalera»/);
const pausada = ui.win(E.avanzado, ADV({log:{filters:{persona:true, evento:true, descarte:true, conexion:true, programa:true}, q:'', paused:true, cut:1, open:null, lines:{c1:lineas}}}), '');
assert.match(pausada, /En pausa · <span id="log-new">1 línea nueva<\/span>/);
const medidores = ui.win(E.avanzado, ADV({adv:{sub:'medidores', cam:'c1'}, meters:{c1:{motivo:null, fps:7.9, cpu:34, demora:0.09, persona:true, m1:0.034, m2:38.2, m3:0.84, umbralV:0.01, umbralAngulo:45, umbralRazon:1, umbralVisibilidad:0.5, fase:1, ventana:0.62, ventanaTotal:1.48, suelo:0, confirmacion:30, visibilidad:{Nariz:0.9, Hombros:0.86, Caderas:0.74, Tobillos:0.38}, esqueleto:{h:[0.5,0.2], aL:[0.48,0.8], aR:[0.52,0.8], hL:[0.48,0.5], hR:[0.52,0.5]}}}}), '');
assert.match(medidores, /7,9<small>fps<\/small>/);
assert.match(medidores, /Objetivo: 8 fps/);
assert.match(medidores, /<span>Uso del procesador<\/span><b>34 %<\/b>/);
assert.match(medidores, /Descenso de la cadera \(M1\).*0,034<small>cuerpos\/s<\/small>/);
assert.match(medidores, /Avisa por debajo de 45°/);
assert.match(medidores, /class="ph cur inestable" aria-current="step">.*Posible caída/);
assert.match(medidores, /Ventana de caída <b>0,62 s<\/b>/);
assert.match(medidores, /class="pbar low"><span>Tobillos<\/span>/);
assert.match(medidores, /Solo se ve en esta PC/);
assert.match(medidores, /<g class="skel">/);
const sinPersona = ui.win(E.avanzado, ADV({adv:{sub:'medidores', cam:'c1'}, meters:{c1:{motivo:'sin_persona'}}}), '');
assert.match(sinPersona, /Sin persona en la imagen/);
assert.match(sinPersona, /Vuelven cuando la cámara vea a alguien\./);
assert.match(ui.win(E.avanzado, ADV({adv:{sub:'medidores', cam:'c1'}, meters:{c1:{motivo:'pausa', pausa:'11:42'}}}), ''), /En pausa hasta las 11:42/);
const actividad = ui.win(E.avanzado, ADV({adv:{sub:'actividad', cam:'c1'}, acts:[{d:'Hoy', t:'10:42', m:'Desde esta PC: se activó el modo avanzado', who:'pc', pend:true}]}), '');
assert.match(actividad, /<h3 class="actday">Hoy<\/h3>/);
assert.match(actividad, /Pendiente de enviar/);
assert.match(actividad, /Nadie puede editar ni borrar esta lista\.<\/p>/);
const diag = ui.win(E.avanzado, ADV({dlg:'diag', diag:{step:'intro', nombre:'te-tengo-diagnostico-Sala-Rosa-2026-09-23.zip'}}), '');
assert.match(diag, /Un archivo para el equipo de soporte\./);
assert.match(diag, /Contraseñas ni accesos/);
assert.match(diag, /Puntos del cuerpo/);
assert.match(diag, /te-tengo-diagnostico-Sala-Rosa-2026-09-23\.zip/);
assert.match(ui.win(E.avanzado, ADV({dlg:'diag', diag:{step:'done', ruta:'/Docs/x.zip', tamano:'1,4 MB'}}), ''), /Diagnóstico guardado · 1,4 MB/);
assert.match(ui.win(E.avanzado, ADV({dlg:'diag', diag:{step:'err', nombre:'x.zip'}}), ''), /No pudimos guardar en esa carpeta<\/b><span>No quedó ningún archivo\. Elige otra\./);
// «Almacenamiento» (US-38, US-35): always visible, video off, the consent gates movements.
const store = {carpeta:'C:\\Users\\Rosa\\AppData\\Local\\TeTengoCaptura\\Datos', uso:{movimientos:1.1e9, video:0, clips:0.2e9}, limite:50e9, estado:null, liberado:null,
  ajustes:{carpeta:null, movimientos:true, dias_movimientos:90, video:false, dias_video:7, clips:true, dias_clips:null, limite_gb:50}, permisoMovimientos:true, nube:30, revocado:false, hayVideo:false};
const conStore = o => Object.assign({}, E.avanzadoApagado, {store: Object.assign({}, store, o || {})});
const ST = o => U(Object.assign({tab:'avanzado', adv:{sub:'almacenamiento', cam:'c1'}, log:{filters:{}, q:'', paused:false, cut:0, open:null, lines:{}}, meters:{}, acts:[], actScope:'pc'}, o||{}));
const almacen = ui.win(conStore(), ST(), '');
assert.match(almacen, /data-act="advSub" data-arg="almacenamiento"/);
assert.match(almacen, /<b>1,3 GB<\/b><span>de 50 GB<\/span>/);
assert.match(almacen, /Movimientos: 30 días \(lo eligió la familia\)\. Video: nunca\./);
assert.match(almacen, /Qué se guarda aquí/);
assert.match(almacen, /Solo Te Tengo Captura puede leerlos\./);
assert.match(almacen, /role="switch" aria-checked="false" aria-labelledby="st-vid" data-act="stVid"/);
assert.match(almacen, /aria-checked="true"[^>]*data-arg="dias_clips\|null">Nunca borrar/);
assert.match(almacen, /Al llegar, borramos lo más antiguo: primero video, luego movimientos\./);
const sinPermiso = ui.win(conStore({permisoMovimientos:false, nube:null}), ST(), '');
assert.match(sinPermiso, /Requiere el permiso de Rosa \(se registra en la app\)\./);
assert.match(sinPermiso, /Movimientos: desactivado\. Video: nunca\./);
assert.match(ui.win(conStore({estado:'lleno'}), ST(), ''), /No podemos guardar en la carpeta<\/b><span>Revisa el espacio del disco\. Detección y avisos siguen\./);
assert.match(ui.win(conStore({estado:'limite', liberado:'01/10'}), ST(), ''), /Borramos el video del 01\/10 para liberar espacio/);
assert.match(ui.win(conStore({revocado:true}), ST(), ''), /¿Borrar los movimientos de esta PC \(1,1&nbsp;GB\)\?/);
assert.match(ui.win(conStore(), ST({dlg:'video'}), ''), /Se queda en esta PC, nunca se sube\. 480p a 8 fps, en partes de 10 min\. Ocupa mucho espacio\./);
const movida = ui.transition(conStore({estado:'moviendo'}), conStore({carpeta:'D:\\TeTengo\\Datos'}));
assert.equal(movida.text, 'Datos movidos a la carpeta nueva.');
// «Ver qué pasó» (US-39): skeleton from the PC's movements, events on the timeline, stretches without data.
const T0 = new Date(2026, 8, 23, 10, 40, 0).getTime();
const poseDePie = [0.5,0.2, 0.47,0.3, 0.53,0.3, 0.46,0.4, 0.54,0.4, 0.45,0.5, 0.55,0.5, 0.48,0.55, 0.52,0.55, 0.48,0.7, 0.52,0.7, 0.48,0.85, 0.52,0.85];
const rpBase = {open:true, cam:'c1', day:'2026-09-23', hour:'10:40', zoom:'10', w0:T0 - 360000, t:T0, playing:false, speed:1, video:false, state:null,
  info:{permitida:true, camaras:[{id:'c1', room:'Sala', dias:[{valor:'2026-09-23', texto:'Hoy, 23/09/2026', corto:'miércoles 23/09'}], desde:'24/08/2026', desdeMs:T0 - 30*86400000, hastaMs:T0 + 60000}]},
  win:{desde:T0 - 360000, hasta:T0 + 240000, hayDatos:true, video:false, eventos:[{t:T0 + 72000, k:'caida', l:'Caída'}],
    huecos:[{a:T0 - 300000, b:T0 - 120000, motivo:'Sin persona en la imagen', corto:'Sin persona'}]},
  poses:{desde:T0 - 10000, hasta:T0 + 110000, t:[T0], p:[poseDePie], f:[0], claves:['h','sL','sR','eL','eR','wL','wR','hL','hR','kL','kR','aL','aR']}};
const RP = o => ADV({rp:Object.assign({}, rpBase, o||{})});
const rep = ui.win(E.avanzado, RP(), '');
assert.match(rep, /Ver qué pasó<\/h1>/);
assert.match(rep, /Sala · miércoles 23\/09/);
assert.match(rep, /Solo puntos del cuerpo, nunca video<span>· Queda en el registro de accesos/);
assert.match(rep, /class="rp-phase " id="rp-phase" aria-live="polite">.*De pie/);
assert.match(rep, /<g class="skel"><line /);
assert.match(rep, /aria-label="Caída, 10:41:12"/);
assert.match(rep, /<span class="ev gap"[^>]*>Sin persona<\/span>/);
assert.match(rep, /Datos desde el 24\/08\/2026\./);
assert.match(rep, /Eventos \(1\)/);
assert.match(rep, /data-act="rpSpeed" aria-label="Velocidad: 1×"/);
assert.match(ui.win(E.avanzado, RP({t:T0 - 200000}), ''), /class="rp-phase gap"[^>]*>.*Sin persona en la imagen/);
assert.match(ui.win(E.avanzado, RP({state:'old'}), ''), /Ya no hay movimientos de ese momento\.<\/b><span>Hay datos desde el 24\/08\/2026\. Elige otra fecha\./);
assert.match(ui.win(E.avanzado, RP({info:{permitida:false, camaras:[]}}), ''), /Falta el permiso de Rosa para guardar movimientos<\/b><span>Se registra en la app: Privacidad › Guardar movimientos\./);
assert.match(ui.win(E.avanzado, ADV(), ''), /data-act="replayOpen">.*Ver qué pasó/);
console.log('ok');
