/* ================= Te Tengo Captura · prototipo navegable =================
   Arranque → Vincular esta PC (QR + código) → Vinculada (la PC informa sus webcams; la familia las asigna desde la app) → ventana de tres pestañas
   (Estado · Cámaras · Avanzado) → minimizar o cerrar a la bandeja (ícono con punto de estado y avisos de Windows).
   El panel de demostración simula lo que pasa fuera de la ventana: el celular, la PC, las webcams y el disco. */
(function(){
  'use strict';
  const $ = id => document.getElementById(id);
  const REDUCED = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  let S, closed, osKind, enterCls, toastTimer, osTimer, booting = false, bootTimers = [], rescanT = null, diagT = null, moveT = null;
  let assignT = [], fallTimers = [], falling = false, rafId = 0, lastTs = 0, drag = false, opener = null, liveIdx = 0, gapShown = null;
  function unpaired(s){ s.screen = 'vincular'; s.linked = false; s.cams = []; return s; }
  function init(){
    S = unpaired(baseState());
    S.log.clock = T('10:44:10');
    closed = false; osKind = null; enterCls = '';
    [toastTimer, osTimer, rescanT, diagT, moveT].forEach(clearTimeout);
    fallTimers.forEach(clearTimeout); fallTimers = []; falling = false; stopPlay(); stopAssign();
  }
  function stopAssign(){ assignT.forEach(clearTimeout); assignT = []; }
  const ROOM_ART = r => ({Sala:'la Sala', Dormitorio:'el Dormitorio', Cocina:'la Cocina', Comedor:'el Comedor', Pasillo:'el Pasillo'})[r] || '«'+r+'»';
  function act(m){ S.acts.unshift({t:'10:42', m:m, pend:!S.online}); }

  /* ---------- render con foco, plegables y desplazamiento preservados ---------- */
  function snap(){
    const a = document.activeElement;
    if(!a || a===document.body || !$('winslot').contains(a) && !$('tbwrap').contains(a)) return null;
    return {id:a.id, act:a.dataset && a.dataset.act, arg:a.dataset && a.dataset.arg};
  }
  function restore(f){
    if(!f) return;
    let el = f.id ? $(f.id) : null;
    if(!el && f.act) el = document.querySelector('#winslot [data-act="'+f.act+'"]'+(f.arg!=null ? '[data-arg="'+CSS.escape(f.arg)+'"]' : '')) || document.querySelector('#winslot [data-act="'+f.act+'"]');
    if(el && !el.disabled) el.focus({preventScroll:true});
  }
  const SCROLLERS = ['actlist', 'stwrap'];
  function render(focusScreen){
    const f = focusScreen ? null : snap();
    const slot = $('winslot');
    const sc = {}; SCROLLERS.forEach(id => { const e = $(id); if(e) sc[id] = e.scrollTop; });
    const lb = $('logbox'), logBottom = !lb || lb.scrollHeight - lb.scrollTop - lb.clientHeight < 40, logTop = lb ? lb.scrollTop : 0;
    slot.innerHTML = win(S, {enter:enterCls});
    enterCls = '';
    SCROLLERS.forEach(id => { const e = $(id); if(e && sc[id]!=null) e.scrollTop = sc[id]; });
    const lb2 = $('logbox'); if(lb2) lb2.scrollTop = (logBottom && !S.log.paused) ? lb2.scrollHeight : logTop;
    const rows = slot.querySelector('.clist-rows'), cur = rows && rows.querySelector('[aria-checked="true"]');
    if(cur && (cur.offsetTop < rows.scrollTop || cur.offsetTop + cur.offsetHeight > rows.scrollTop + rows.clientHeight)) rows.scrollTop = cur.offsetTop;
    slot.classList.toggle('hidden', closed || booting);
    slot.setAttribute('aria-hidden', closed || booting ? 'true' : 'false');
    $('tbwrap').innerHTML = taskbar(S, {open:!closed, hl:!!osKind});
    $('ostoast').innerHTML = osKind ? osToast(S, osKind) : '';
    renderDemo();
    if(S.dlg && !closed && !booting){
      const d = slot.querySelector('.dlg');
      if(d && !d.contains(document.activeElement)){ const b = d.querySelector('.dlg-actions .btn:not([disabled])'); if(b) b.focus({preventScroll:true}); }
      else restore(f);
    }
    else if(focusScreen && !closed && !booting){ const t = $('scr-h'); if(t) t.focus({preventScroll:true}); }
    else restore(f);
  }
  function toast(kind, icon, text){
    S.toast = {kind, icon, text}; render();
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { S.toast = null; render(); }, 3800);
  }
  function osNotify(kind){
    osKind = kind; render();
    clearTimeout(osTimer); osTimer = setTimeout(() => { osKind = null; render(); }, 8000);
  }
  function openDlg(name){ opener = snap(); S.dlg = name; render(); }
  function closeDlg(){ S.dlg = null; S.diag = {step:'intro'}; clearTimeout(diagT); render(); restore(opener); opener = null; }

  /* ---------- pintado parcial: registro, medidores, repetición y cuenta regresiva ---------- */
  function paintLog(){
    const box = $('logbox'); if(!box) return;
    const atBottom = box.scrollHeight - box.scrollTop - box.clientHeight < 40;
    box.innerHTML = logRows(S);
    const c = logCounts(S); LOG_K.forEach(k => { const e = $('cnt-'+k[0]); if(e) e.textContent = c[k[0]]; });
    const n = $('log-new'); if(n){ const k = logAll(S, S.adv.cam).length - S.log.cut; n.textContent = k+' '+(k===1 ? 'línea nueva' : 'líneas nuevas'); }
    if(!S.log.paused && atBottom) box.scrollTop = box.scrollHeight;
  }
  function paintMeters(){ const m = $('meters'); if(m){ m.className = 'mgrid'+(meterReason(S) ? ' off' : ''); m.innerHTML = metersInner(S); } }
  function paintReplay(){
    const fig = $('rp-fig'); if(!fig) return;
    const t = REDUCED ? Math.floor(S.rp.t) : S.rp.t, p = rpPose(S, t), w = rpWin(S);
    fig.innerHTML = rpFig(S, t);
    const ph = $('rp-phase'); if(ph && ph.dataset.l!==p.label){ ph.className = 'rp-phase '+p.tone; ph.innerHTML = ic(p.i)+p.label; ph.dataset.l = p.label; }
    $('rp-clock').textContent = hms(t); $('rp-time').textContent = hms(t);
    $('tl-head').style.left = Math.max(0, Math.min(100, (t-w[0])/(w[1]-w[0])*100))+'%';
    const tr = $('tl-track'); tr.setAttribute('aria-valuenow', Math.round(t)); tr.setAttribute('aria-valuetext', rpValText(S, t));
  }
  function announce(id, text){ const e = $(id); if(e){ e.textContent = ''; setTimeout(() => { e.textContent = text; }, 30); } }

  /* ---------- repetición: reproducir, saltar tramos sin datos, buscar ---------- */
  function stopPlay(){ if(S) S.rp.playing = false; clearInterval(rafId); rafId = 0; lastTs = 0; }
  function startPlay(){
    const w = rpWin(S); if(S.rp.t >= w[1]-.5) S.rp.t = w[0];
    S.rp.playing = true; lastTs = performance.now(); gapShown = null; clearInterval(rafId); rafId = setInterval(step, REDUCED ? 250 : 40);
  }
  /* reloj de la reproducción: avanza según el tiempo real transcurrido (no depende de los cuadros pintados) */
  function step(){
    if(!S.rp.playing) return stopPlay();
    const now = performance.now(), dt = (now - lastTs)/1000*S.rp.speed; lastTs = now;
    let t = S.rp.t + dt;
    const g = rpGap(t);
    if(g){ t = g.b; if(gapShown!==g){ gapShown = g; S.rp.t = t; toast('warn', 'clock', 'Sin datos de '+hm(g.a)+' a '+hm(g.b)+' · '+g.why); } }
    const w = rpWin(S);
    if(t >= w[1]){ S.rp.t = w[1]; stopPlay(); render(); return; }
    S.rp.t = t; paintReplay();
  }
  function fitWin(t){
    const span = S.rp.zoom==='60' ? 3600 : 600, w = rpWin(S);
    if(t < w[0] || t > w[1]) S.rp.w0 = Math.min(Math.floor((t - span*.6)/60)*60, RP_END - span);
  }
  function seek(t){ const w = rpWin(S); S.rp.t = Math.max(w[0], Math.min(w[1], t)); paintReplay(); }

  /* ---------- arranque: ventana de inicio y luego la ventana ---------- */
  function boot(){
    bootTimers.forEach(clearTimeout); bootTimers = [];
    booting = true; render();
    const bs = $('bootslot');
    bs.innerHTML = bootWin({play:true, pct:0, step:0});
    const bar = bs.querySelector('.boot-bar'), fill = bar.querySelector('i'), txt = $('boot-st');
    const at = (ms, fn) => bootTimers.push(setTimeout(fn, ms));
    const set = (p, k) => { fill.style.transform = 'scaleX('+(p/100)+')'; bar.setAttribute('aria-valuenow', p); if(k!=null) txt.textContent = BOOT_STEPS[k]; };
    at(80, () => set(22));
    at(720, () => set(54, 1));
    at(1340, () => set(86, 2));
    at(1820, () => set(100));
    at(2060, () => { const b = bs.querySelector('.boot'); if(b) b.classList.add('out'); });
    at(2240, () => { bs.innerHTML = ''; booting = false; enterCls = 'enter'; render(true); });
  }

  /* ---------- ventana y bandeja ---------- */
  function hideWindow(){ closed = true; stopPlay(); osNotify('closed'); }
  function openWindow(){ closed = false; osKind = null; clearTimeout(osTimer); render(true); }
  function newCode(){ S.pair = {code:(S.pair.code+1) % CODES.length, left:600, renewed:false, re90:false, fresh:true}; setTimeout(() => { S.pair.fresh = false; }, 600); }

  /* ---------- acciones de la interfaz ---------- */
  function validName(id){
    const ps = pickState(S, id), name = (ps.otherOn ? S.pick.other : ps.room || '').trim();
    if(!name) return {err:'empty'};
    if(/\bbano\b|banio/.test(norm(name))) return {err:'bath'};
    const taken = takenRooms(S, id), key = Object.keys(taken).find(k => norm(k)===norm(name));
    if(key) return {err:'dup', errRoom:key, errPc:taken[key]};
    return {name: ROOMS.find(r => norm(r)===norm(name)) || cap1(name)};
  }
  const ORDER = ['d1','d2','d3','d4'];
  const ACT = {
    tab(arg){ if(S.tab===arg) return; stopPlay(); S.tab = arg; if(arg!=='camaras') S.here = false; render(); },
    toCams(){ S.screen = 'main'; S.linked = true; S.tab = 'camaras'; S.here = false; if(S.cams.length===0) S.pick = {sel:'d1', room:null, otherOn:false, other:'', err:null}; enterCls = 'enter'; render(true); },
    toEstado(){ S.screen = 'main'; S.linked = true; S.tab = 'estado'; S.here = false; enterCls = 'enter'; render(true); },
    toHere(){ ACT.toCams(); ACT.hereOn(); },
    /* «Elegir aquí (si estás instalando)»: el selector de siempre, como opción secundaria */
    hereOn(){ S.here = true; S.pick = {sel:selDev(S), room:null, otherOn:false, other:'', err:null}; render(true); },
    hereOff(){ S.here = false; S.pick = {sel:selDev(S), room:null, otherOn:false, other:'', err:null}; render(true); },
    pairAgain(){ S.screen = 'vincular'; S.linked = false; newCode(); enterCls = 'enter'; render(true); },
    retryNow(){
      if(S.screen==='vincular'){ S.retry = 25; toast('warn', S.online ? 'cloud' : 'wifiOff', S.online ? 'Te Tengo sigue sin responder.' : 'Aún sin internet.'); }
      else { S.retry = 10; toast('warn', 'wifiOff', 'Aún sin internet.'); }
    },
    rescan(){
      if(S.tab==='camaras'){ S.scan = true; render(); }
      else { const b = document.querySelector('#winslot [data-act="rescan"]'); if(b){ b.classList.add('loading'); b.innerHTML = '<span class="spin"></span>Buscando…'; } }
      clearTimeout(rescanT); rescanT = setTimeout(() => {
        S.scan = false;
        if(S.lost) toast('warn', 'videoOff', 'No encontramos la '+DEVS.d3.name+'. Revisa el cable USB.');
        else if(S.busy) toast('warn', 'warn', 'Otro programa sigue usando la '+DEVS.d2.name+'.');
        else toast('ok', 'check', connected(S).length+' cámaras conectadas.');
      }, 900);
    },
    selCam(id){ S.pick = {sel:id, room:null, otherOn:false, other:'', err:null}; render(); },
    pickRoom(r){ S.pick.room = r; S.pick.otherOn = false; S.pick.err = null; render(); },
    pickOther(){ const ps = pickState(S, selDev(S)); S.pick.otherOn = true; S.pick.room = null; S.pick.other = ps.otherVal || ''; S.pick.err = null; render(); const i = $('room-other'); if(i) i.focus(); },
    useCam(){
      const id = selDev(S), v = validName(id), D = DEVS[id];
      if(v.err){ Object.assign(S.pick, {err:v.err, errRoom:v.errRoom, errPc:v.errPc}); render(); const i = $('room-other'); if(i) i.focus(); return; }
      const c = S.cams.find(x => x.id===id), was = c ? c.room : null;
      if(c){ c.room = v.name; c.by = 'pc'; } else { S.cams.push({id:id, room:v.name, by:'pc'}); S.cams.sort((a, b) => ORDER.indexOf(a.id)-ORDER.indexOf(b.id)); }
      if(S.peek===id) S.peek = null;
      S.pick = {sel:id, room:null, otherOn:false, other:'', err:null};
      if(!S.cams.some(x => x.room===S.adv.cam)) S.adv.cam = S.cams[0].room;
      act('Desde esta PC: la cámara '+D.name+' pasó '+(was ? 'de '+was+' a ' : 'a ')+v.name);
      toast('ok', 'check', D.name+' cuida ahora '+ROOM_ART(v.name));
    },
    unuse(){
      const id = selDev(S), c = S.cams.find(x => x.id===id); if(!c) return;
      S.cams = S.cams.filter(x => x.id!==id); S.pick = {sel:id, room:null, otherOn:false, other:'', err:null};
      if(S.cams.length && !S.cams.some(x => x.room===S.adv.cam)) S.adv.cam = S.cams[0].room;
      act('Desde esta PC: la cámara '+DEVS[id].name+' dejó de usarse en '+c.room);
      toast('ok', 'check', DEVS[id].name+' ya no cuida '+ROOM_ART(c.room)+'.');
    },
    unlinkAsk(){ S.unlinkWipe = false; openDlg('unlink'); },
    dlgClose(){ closeDlg(); },
    unlinkDo(){
      const wipe = S.unlinkWipe; S.dlg = null; stopPlay();
      S.screen = 'vincular'; S.linked = false; S.cams = []; S.adv.on = false; S.replay = false; S.tab = 'estado'; S.here = false; S.peek = null; stopAssign(); newCode();
      if(wipe){ S.store.movKept = false; S.store.videoStored = false; }
      enterCls = 'enter';
      toast('ok', 'unlink', wipe ? 'PC desvinculada y datos borrados. La familia recibió un aviso.' : 'PC desvinculada. La familia recibió un aviso.');
      const t = $('scr-h'); if(t) t.focus({preventScroll:true});
    },
    advToggle(){
      S.adv.on = !S.adv.on;
      if(S.adv.on){ S.adv.sub = 'registro'; if(!S.cams.some(c => c.room===S.adv.cam) && S.cams.length) S.adv.cam = S.cams[0].room; act('Desde esta PC: se activó el modo avanzado'); toast('ok', 'sliders', 'Modo avanzado activado.'); }
      else { if(S.adv.sub==='registro' || S.adv.sub==='medidores') S.adv.sub = 'actividad'; act('Desde esta PC: se desactivó el modo avanzado'); toast('ok', 'sliders', 'Modo avanzado desactivado.'); }
    },
    advSub(arg){ S.adv.sub = arg; render(); },
    advCam(arg){ S.adv.cam = arg; S.log.open = null; if(S.log.paused) S.log.cut = logAll(S, arg).length; render(); },
    logFilter(k){ S.log.filters[k] = !S.log.filters[k]; render(); },
    logPause(){ S.log.paused = !S.log.paused; if(S.log.paused) S.log.cut = logAll(S, S.adv.cam).length; render(); if(!S.log.paused){ const b = $('logbox'); if(b) b.scrollTop = b.scrollHeight; } },
    techToggle(id){ S.log.open = S.log.open===id ? null : id; render(); },
    copyTech(id){ const l = logAll(S, S.adv.cam).find(x => x.id===id); try{ const pr = navigator.clipboard && navigator.clipboard.writeText(techLine(l)); if(pr && pr.catch) pr.catch(() => {}); }catch(e){} toast('ok', 'copy', 'Línea copiada'); },
    actScope(arg){ S.actScope = arg; render(); },
    ret(arg){
      const p = arg.split('|'), key = p[0], v = p[1], st = S.store;
      if(key==='cap'){
        if(v==='Otro'){ st.capOther = true; render(); const i = $('cap-val'); if(i) i.focus(); return; }
        if(!st.capOther && st.cap===v) return;
        act('Desde esta PC: el límite de espacio pasó de '+(st.capOther ? (st.capVal||'otro')+' GB' : st.cap)+' a '+v); st.cap = v; st.capOther = false;
        return toast('ok', 'drive', 'Límite de espacio: '+v+'.');
      }
      const F = {mov:['retMov','los movimientos'], vid:['retVid','el video'], clip:['retClip','los clips']}[key];
      if(st[F[0]]===v) return;
      act('Desde esta PC: '+F[1]+' pasaron de '+st[F[0]]+' a '+v.toLowerCase());
      st[F[0]] = v;
      toast('ok', 'check', v==='Nunca borrar' ? 'No borraremos '+F[1]+'.' : 'Guardaremos '+F[1]+' '+v+'.');
    },
    stMov(){ S.store.moves = !S.store.moves; act('Desde esta PC: '+(S.store.moves ? 'se activó' : 'se desactivó')+' el guardado de movimientos'); toast('ok', 'check', S.store.moves ? 'Guardamos los movimientos en esta PC.' : 'Dejamos de guardar movimientos. Los guardados se borran a su plazo.'); },
    stVid(){
      if(!S.store.video) return openDlg('video');
      S.store.video = false; act('Desde esta PC: se desactivó el video continuo');
      toast('ok', 'check', 'Dejamos de guardar video. El guardado se borra a su plazo.');
    },
    videoOn(){ S.store.video = true; S.dlg = null; act('Desde esta PC: se activó el video continuo'); toast('ok', 'cam', 'Guardamos video continuo solo en esta PC.'); restore(opener); },
    stClip(){ S.store.clips = !S.store.clips; act('Desde esta PC: '+(S.store.clips ? 'se activó' : 'se desactivó')+' el guardado de clips'); toast('ok', 'check', S.store.clips ? 'Guardamos los clips de los avisos en esta PC.' : 'Dejamos de guardar clips. La familia los ve en la app.'); },
    folderChange(){
      S.store.state = 'moving'; render(); clearTimeout(moveT);
      moveT = setTimeout(() => { S.store.state = null; S.store.path = 1 - S.store.path; act('Desde esta PC: se cambió la carpeta de los datos'); toast('ok', 'folder', 'Datos movidos a la carpeta nueva.'); }, 2200);
    },
    revokeKeep(){ S.dlg = null; toast('ok', 'check', 'Conservamos los movimientos. No guardaremos nuevos.'); },
    revokeWipe(){ S.dlg = null; S.store.movKept = false; act('Desde esta PC: se borraron los movimientos guardados'); toast('ok', 'trash', 'Borramos los movimientos de esta PC.'); },
    replayOpen(){ S.replay = true; S.rp.state = null; render(true); },
    replayClose(){ stopPlay(); S.replay = false; toast('ok', 'eye', 'Acceso registrado'); const t = document.querySelector('#winslot [data-act="replayOpen"]'); if(t) t.focus({preventScroll:true}); },
    rpPlay(){ if(S.rp.playing){ stopPlay(); render(); } else { startPlay(); render(); } },
    rpPrev(){ const e = rpEvents(S).filter(x => x.t < S.rp.t-.6).pop(); if(e){ fitWin(e.t); S.rp.t = e.t; render(); } else toast('ok', 'info', 'No hay eventos antes.'); },
    rpNext(){ const e = rpEvents(S).find(x => x.t > S.rp.t+.6); if(e){ fitWin(e.t); S.rp.t = e.t; render(); } else toast('ok', 'info', 'No hay más eventos.'); },
    rpSpeed(){ S.rp.speed = SPEEDS[(SPEEDS.indexOf(S.rp.speed)+1) % SPEEDS.length]; render(); },
    rpZoom(z){ if(S.rp.zoom===z) return; S.rp.zoom = z; S.rp.w0 = null; const w = rpWin(S); if(S.rp.t < w[0] || S.rp.t > w[1]) fitWin(S.rp.t); render(); },
    rpSeek(t){ t = Number(t); fitWin(t); S.rp.t = t; render(); },
    rpCam(r){ S.rp.cam = r; render(); },
    rpQuick(h){ S.rp.hour = h; ACT.rpGo(); },
    rpGo(){
      const m = /^(\d{1,2}):(\d{2})$/.exec(String(S.rp.hour).trim());
      if(!m || +m[1] > 23 || +m[2] > 59) return toast('warn', 'clock', 'Escribe la hora así: 10:40.');
      stopPlay(); S.rp.state = null;
      const t = Math.min(T(pad2(+m[1])+':'+m[2]+':00'), RP_END);
      S.rp.w0 = null; fitWin(t); S.rp.t = t; render();
    },
    rpVideo(){ S.rp.video = !S.rp.video; render(); },
    diagOpen(){ S.diag = {step:'intro'}; openDlg('diag'); },
    diagSave(){ S.diag.step = 'busy'; render(); clearTimeout(diagT); diagT = setTimeout(() => { S.diag.step = S.failFolder ? 'err' : 'done'; render(); }, 1700); },
    diagCancel(){ clearTimeout(diagT); closeDlg(); toast('ok', 'x', 'No se guardó ningún archivo.'); },
    diagShow(){ closeDlg(); toast('ok', 'folder', 'Abrimos la carpeta '+DIAG.dir+'.'); },
    minimize: hideWindow, close: hideWindow,
    trayOpen: openWindow,
    toastClose(){ osKind = null; clearTimeout(osTimer); render(); }
  };
  document.addEventListener('click', e => {
    const t = e.target.closest('[data-act]');
    if(t && ACT[t.dataset.act] && !t.disabled && t.getAttribute('aria-disabled')!=='true'){ e.preventDefault(); ACT[t.dataset.act](t.dataset.arg); return; }
    const d = e.target.closest('[data-demo]');
    if(d && !d.disabled && d.getAttribute('aria-disabled')!=='true') DEMO[d.dataset.demo]();
  });
  /* plegables: recordar cuáles están abiertos al volver a pintar */
  document.addEventListener('toggle', e => { const d = e.target; if(d && d.matches && d.matches('details[data-k]')) S.open[d.dataset.k] = d.open; }, true);
  /* campos */
  document.addEventListener('input', e => {
    const id = e.target.id, v = e.target.value;
    if(id==='log-q'){ S.log.q = v; paintLog(); }
    else if(id==='room-other'){ S.pick.other = v; if(S.pick.err){ S.pick.err = null; const m = $('room-err'); if(m) m.remove(); e.target.removeAttribute('aria-invalid'); e.target.closest('.field').classList.remove('err'); } }
    else if(id==='rp-hour') S.rp.hour = v;
    else if(id==='cap-val') S.store.capVal = v.replace(/\D/g, '').slice(0, 4);
  });
  document.addEventListener('change', e => {
    const id = e.target.id;
    if(id==='unlink-wipe') S.unlinkWipe = e.target.checked;
    else if(id==='rp-day'){ stopPlay(); S.rp.day = e.target.value==='old' ? 'hoy' : e.target.value; S.rp.state = null; render(); }
    else if(id==='cap-val' && Number(S.store.capVal) > 0){ act('Desde esta PC: el límite de espacio pasó a '+S.store.capVal+' GB'); toast('ok', 'drive', 'Límite de espacio: '+S.store.capVal+' GB.'); }
  });
  /* línea de tiempo: arrastrar para buscar */
  function seekX(tr, x){ const r = tr.getBoundingClientRect(), w = rpWin(S); seek(w[0] + Math.max(0, Math.min(1, (x-r.left)/r.width))*(w[1]-w[0])); }
  document.addEventListener('pointerdown', e => {
    const tr = e.target.closest && e.target.closest('#tl-track'); if(!tr || e.target.closest('.tl-m')) return;
    drag = true; try{ tr.setPointerCapture(e.pointerId); }catch(err){} seekX(tr, e.clientX);
  });
  document.addEventListener('pointermove', e => { if(drag){ const tr = $('tl-track'); if(tr) seekX(tr, e.clientX); } });
  document.addEventListener('pointerup', () => { drag = false; });
  /* teclado */
  document.addEventListener('keydown', e => {
    const t = e.target;
    if(e.key==='Escape'){
      if(S.dlg){ e.preventDefault(); if(S.dlg==='diag' && S.diag.step==='busy') ACT.diagCancel(); else if(S.dlg==='revoke') ACT.revokeKeep(); else closeDlg(); return; }
      if(osKind){ ACT.toastClose(); return; }
    }
    if(e.key==='Tab' && S.dlg){
      const d = document.querySelector('#winslot .dlg'); if(!d) return;
      const f = [...d.querySelectorAll('button:not([disabled]),input,select,[tabindex="0"]')];
      if(!f.length) return;
      if(e.shiftKey && document.activeElement===f[0]){ e.preventDefault(); f[f.length-1].focus(); }
      else if(!e.shiftKey && document.activeElement===f[f.length-1]){ e.preventDefault(); f[0].focus(); }
      else if(!d.contains(document.activeElement)){ e.preventDefault(); f[0].focus(); }
      return;
    }
    if(e.key==='Enter'){
      if(t.id==='room-other'){ e.preventDefault(); ACT.useCam(); return; }
      if(t.id==='rp-hour'){ e.preventDefault(); ACT.rpGo(); return; }
    }
    if(t.id==='tl-track'){
      const w = rpWin(S), big = e.shiftKey ? 10 : 1;
      const k = {ArrowRight:big, ArrowUp:big, ArrowLeft:-big, ArrowDown:-big, PageUp:60, PageDown:-60}[e.key];
      if(k!=null){ e.preventDefault(); seek(S.rp.t + k); return; }
      if(e.key==='Home'){ e.preventDefault(); seek(w[0]); return; }
      if(e.key==='End'){ e.preventDefault(); seek(w[1]); return; }
      if(e.key===' '){ e.preventDefault(); ACT.rpPlay(); return; }
    }
    /* pestañas y grupos de opción: flechas */
    const role = t.getAttribute && t.getAttribute('role');
    if((role==='tab' || role==='radio') && /^Arrow(Left|Right|Up|Down)$/.test(e.key)){
      const group = t.closest('[role="tablist"],[role="radiogroup"]'); if(!group) return;
      const items = [...group.querySelectorAll('[role="tab"],[role="radio"]')].filter(x => !x.disabled && x.getAttribute('aria-disabled')!=='true');
      const i = items.indexOf(t), d = /Right|Down/.test(e.key) ? 1 : -1, n = items[(i+d+items.length) % items.length];
      if(n){ e.preventDefault(); n.click(); const again = n.id ? $(n.id) : document.querySelector('#winslot [data-act="'+n.dataset.act+'"][data-arg="'+CSS.escape(n.dataset.arg||'')+'"]'); if(again) again.focus(); }
    }
  });

  /* ---------- panel de demostración: lo que pasa fuera de la ventana ---------- */
  const salaCam = () => S.cams.find(c => c.id==='d1');
  function addLine(cam, l){
    const list = S.log.extra[cam] || (S.log.extra[cam] = []);
    S.log.clock += 2 + (liveIdx % 3); liveIdx++;
    const line = Object.assign({t:hms(S.log.clock)}, l); list.push(line);
    S.log.fresh = cam+'-x'+(list.length-1);
    if(S.tab==='avanzado' && !S.replay && advSub(S)==='registro' && S.adv.cam===cam){ paintLog(); if(l.k==='evento' && !S.log.paused) announce('log-ann', l.m); }
  }
  function fallStep(fn, ms){ fallTimers.push(setTimeout(() => { fn(); if(S.tab==='avanzado' && advSub(S)==='medidores') paintMeters(); renderDemo(); }, ms)); }
  function simulateFall(){
    falling = true; const m = S.m, cam = salaCam().room;
    Object.assign(m, {phase:1, m1:.034, m2:38.2, m3:.84, win:1.48, pose:'falling'});
    addLine(cam, LOG_FALL[0]); addLine(cam, LOG_FALL[1]);
    if(S.tab==='avanzado' && advSub(S)==='medidores') paintMeters();
    for(let i = 1; i <= 5; i++) fallStep(() => { m.win = Math.max(0, 1.48 - i*.3); }, i*300);
    fallStep(() => { Object.assign(m, {phase:2, pose:'caida', m2:9, m3:2.4, win:0, ground:0}); addLine(cam, LOG_FALL[2]); }, 1600);
    for(let s = 1; s <= 30; s++) fallStep(() => { m.ground = s; }, 1600 + s*1000);
    fallStep(() => { m.phase = 3; addLine(cam, LOG_FALL[3]); }, 31700);
    fallStep(() => { Object.assign(m, {phase:0, pose:'pie', m1:.004, m2:72, m3:.62, win:1.48, ground:0}); addLine(cam, LOG_FALL[4]); falling = false; }, 36500);
  }
  const PLAN_ROOMS = {d1:'Sala', d2:'Dormitorio', d3:'Pasillo', d4:'Comedor'};
  function assignPlan(){
    if(!S.linked || !['main', 'vinculada'].includes(S.screen)) return [];
    const used = S.cams.map(c => c.room), out = [];
    connected(S).filter(id => !isLost(S, id) && !S.cams.some(c => c.id===id)).forEach(id => {
      const room = [PLAN_ROOMS[id], 'Sala', 'Dormitorio', 'Pasillo', 'Comedor'].find(r => !used.includes(r) && !OTHER_ROOMS[r]);
      if(room){ used.push(room); out.push({id, room}); }
    });
    return out;
  }
  function phoneAssign(id, room){
    if(!S.linked || S.screen!=='main' || S.cams.some(c => c.id===id || c.room===room) || !connected(S).includes(id)) return;
    S.cams.push({id:id, room:room, by:'app'}); S.cams.sort((a, b) => ORDER.indexOf(a.id)-ORDER.indexOf(b.id));
    if(S.peek===id) S.peek = null;
    if(S.here && selDev(S)===id) S.pick = {sel:id, room:null, otherOn:false, other:'', err:null};
    if(!S.cams.some(x => x.room===S.adv.cam)) S.adv.cam = S.cams[0].room;
    S.acts.unshift({t:'10:42', who:'CH', m:'Carmen eligió desde la app la '+DEVS[id].name+' para '+deRoomD(room)});
    if(closed) return render();
    toast('ok', 'mobile', 'Carmen eligió la '+DEVS[id].name+' para '+ROOM_ART(room));
  }
  function linkedState(){ const s = baseState(); s.log.clock = T('10:44:10'); s.acts = S.acts; return s; }
  const DEMO = {
    approve(){
      const prev = S.prevCams; S.screen = 'vinculada'; S.linked = true; S.cams = prev || []; S.prevCams = null; S.pair.re90 = false;
      if(!S.acts.some(a => /vinculó/.test(a.m))) S.acts.unshift({t:'10:42', who:'CH', m:'Carmen vinculó la PC Sala-Rosa', pend:false});
      if(closed){ render(); return; }
      enterCls = 'enter'; render(true);
    },
    reject(){ S.screen = 'rechazada'; enterCls = 'enter'; closed ? render() : render(true); },
    expire(){ const re = S.pair.re90; newCode(); S.pair.renewed = true; S.pair.re90 = re; render(); announce('pair-ann', 'Código nuevo'); },
    re90(){ S.prevCams = S.cams; S.screen = 'vincular'; S.linked = false; S.cams = []; S.here = false; S.peek = null; stopAssign(); S.adv.on = false; S.replay = false; stopPlay(); newCode(); S.pair.re90 = true; enterCls = 'enter'; closed ? render() : render(true); },
    net(){
      S.online = !S.online; S.retry = S.screen==='vincular' ? 25 : 8;
      if(S.linked && salaCam()) addLine(salaCam().room, S.online ? LOG_NET_OK : LOG_NET);
      if(closed || S.screen!=='main') return render();
      if(S.online) toast('ok', 'check', 'Volvió internet. Avisos enviados.'); else render();
    },
    server(){ S.server = !S.server; S.retry = 25; render(); },
    usb(){
      S.lost = !S.lost; clearTimeout(rescanT);
      const assigned = S.cams.some(c => c.id==='d3');
      if(S.lost){ if(closed && assigned) osNotify('lost'); else render(); }
      else { if(closed) render(); else toast('ok', 'usb', 'La '+DEVS.d3.name+' volvió a responder.'); }
    },
    extra(){ S.extra = !S.extra; if(closed) return render(); if(S.extra) toast('ok', 'usb', 'Webcam nueva: HD USB Camera.'); else render(); },
    busy(){ S.busy = !S.busy; render(); },
    full(){ S.store.state = S.store.state==='full' ? null : 'full'; if(closed) return render(); if(S.store.state) toast('warn', 'folder', 'No podemos guardar en la carpeta. La detección sigue.'); else toast('ok', 'check', 'Hay espacio otra vez.'); },
    near(){ S.store.state = S.store.state==='near' ? null : 'near'; S.store.video = S.store.videoStored = S.store.state==='near' || S.store.videoStored; if(closed) return render(); if(S.store.state) toast('warn', 'drive', 'Queda poco espacio.'); else render(); },
    live(){
      const r = (S.cams.find(c => c.room==='Dormitorio') || S.cams[0]).room;
      S.live = S.live ? null : {who:'Carmen', since:'10:42', room:r};
      if(S.live && closed) return osNotify('live');
      render();
    },
    pause(){
      S.pause = S.pause ? null : '11:42';
      if(S.pause) act('Luis pausó la cámara de '+ROOM_ART(salaCam().room)+' hasta las 11:42'.replace('Desde esta PC: ', ''));
      if(S.pause) S.acts[0].who = 'LH';
      if(closed) return render();
      if(S.pause) toast('ok', 'pause', 'Luis pausó '+ROOM_ART(salaCam().room)+' hasta las 11:42.');
      else toast('ok', 'check', 'Pausa terminada: vuelve a cuidar '+ROOM_ART(salaCam().room)+'.');
    },
    consent(){
      S.consent = !S.consent;
      if(closed) return render();
      if(S.consent) toast('ok', 'check', 'Consentimiento registrado en la app.'); else render();
    },
    rename(){
      const c = salaCam(); c.room = c.room==='Sala' ? 'Sala comedor' : 'Sala';
      if(S.adv.cam==='Sala' || S.adv.cam==='Sala comedor') S.adv.cam = c.room;
      if(S.rp.cam==='Sala' || S.rp.cam==='Sala comedor') S.rp.cam = c.room;
      S.acts.unshift({t:'10:42', who:'CH', m:'Carmen cambió el nombre de la habitación en la app: «'+c.room+'»'});
      if(closed) return render();
      toast('ok', 'check', 'Habitación renombrada en la app: «'+c.room+'».');
    },
    /* la familia asigna las cámaras desde la app: la PC se actualiza sola, una cámara tras otra */
    assign(){
      const plan = assignPlan(); if(!plan.length) return;
      stopAssign();
      if(S.screen==='vinculada'){ S.screen = 'main'; S.tab = 'estado'; S.here = false; if(!closed){ enterCls = 'enter'; render(true); } }
      plan.forEach((p, i) => assignT.push(setTimeout(() => { assignT.shift(); phoneAssign(p.id, p.room); renderDemo(); }, 250 + i*1700)));
      renderDemo();
    },
    unassign(){
      stopAssign();
      const c = S.cams[S.cams.length-1]; if(!c) return;
      S.cams = S.cams.filter(x => x!==c);
      if(S.cams.length && !S.cams.some(x => x.room===S.adv.cam)) S.adv.cam = S.cams[0].room;
      if(S.live && S.live.room===c.room) S.live = null;
      S.acts.unshift({t:'10:42', who:'CH', m:'Carmen dejó de usar desde la app la '+DEVS[c.id].name+' '+delRoom(c.room)});
      if(closed) return render();
      toast('ok', 'mobile', 'Carmen dejó de usar la '+DEVS[c.id].name+': ya no cuida '+ROOM_ART(c.room)+'.');
    },
    peek(){
      if(S.peek){ S.peek = null; return render(); }
      const free = connected(S).filter(id => !isLost(S, id) && !S.cams.some(c => c.id===id));
      S.peek = free[0] || connected(S).find(id => !isLost(S, id)) || null;
      if(S.tab==='camaras' && !S.here && S.peek) S.pick = {sel:S.peek, room:null, otherOn:false, other:'', err:null};
      render();
    },
    removed(){
      S.dlg = null; stopPlay(); stopAssign(); S.screen = 'quitada'; S.linked = false; S.cams = []; S.here = false; S.peek = null; S.adv.on = false; S.replay = false; S.live = null; S.pause = null;
      if(closed) return osNotify('removed');
      enterCls = 'enter'; render(true);
    },
    revoke(){
      S.moveConsent = !S.moveConsent;
      if(!S.moveConsent){ S.rp.video = false; stopPlay(); S.acts.unshift({t:'10:42', who:'CH', m:'Carmen registró que Rosa ya no autoriza guardar sus movimientos'}); if(S.store.movKept && S.screen==='main'){ if(closed){ S.dlg = 'revoke'; render(); } else openDlg('revoke'); } else render(); }
      else { S.acts.unshift({t:'10:42', who:'CH', m:'Carmen registró el permiso de Rosa para guardar movimientos'}); if(closed) return render(); toast('ok', 'check', 'Permiso para guardar movimientos registrado.'); }
    },
    fall(){ simulateFall(); renderDemo(); if(!closed && !(S.tab==='avanzado' && S.adv.on)) toast('ok', 'info', 'Míralo en Avanzado.'); },
    noPerson(){ S.m.person = !S.m.person; if(S.tab==='avanzado' && advSub(S)==='medidores') paintMeters(); renderDemo(); },
    videoStored(){ S.store.videoStored = !S.store.videoStored; if(S.store.videoStored) S.store.video = true; else S.rp.video = false; render(); },
    failFolder(){ S.failFolder = !S.failFolder; renderDemo(); },
    linked(){
      init(); S = linkedState(); closed = false; enterCls = 'enter';
      bootTimers.forEach(clearTimeout); booting = false; $('bootslot').innerHTML = ''; render(true);
    },
    reset(){ init(); boot(); }
  };
  /* ---------- panel de demostración: secciones plegables y ayudas «i» ---------- */
  const DP = {
    tipText: c => c.tip[0] + ' ' + c.tip[1],
    /* una fila: acción + botón «i» con su ayuda (role=tooltip, también como title nativo) */
    row(key, c, extra){
      const tid = 'dp-tip-' + key, wid = 'dp-why-' + key;
      return '<div class="dp-row"><button type="button" class="dp-b" data-demo="' + key + '" aria-describedby="' + wid + ' ' + tid + '" title="' + esc(DP.tipText(c)) + '"' + (c.sw ? ' aria-pressed="false"' : '') + '>' +
        (c.icon ? ic(c.icon) : '') + '<span class="dp-lbl"><span class="dp-l">' + c.l + '</span><span class="dp-why" id="' + wid + '"></span></span>' + (c.sw ? '<span class="dp-sw" aria-hidden="true"></span>' : '') + '</button>' +
        '<button type="button" class="dp-i" data-tip="' + key + '" aria-label="Qué hace: ' + esc(c.l) + '" aria-describedby="' + tid + '">' + ic('info') + '</button>' +
        '<span class="dp-tip" role="tooltip" id="' + tid + '"><b>' + c.tip[0] + '</b>' + c.tip[1] + '<span class="dp-tip-why"></span></span></div>' + (extra || '');
    },
    section(s, body){
      const bid = 'dp-b-' + s.id;
      return '<section class="dp-sec"><h3><button type="button" class="dp-sec-h" data-sec="' + s.id + '" aria-expanded="' + (s.open !== false) + '" aria-controls="' + bid + '">' +
        '<span class="dp-sec-i">' + ic(s.icon) + '</span><span class="dp-sec-t">' + s.t + '</span>' + ic('chevR', 'class="dp-chev"') + '</button></h3>' +
        '<div class="dp-sec-b" id="' + bid + '"' + (s.open === false ? ' hidden' : '') + '>' + body + '</div></section>';
    },
    /* activa o desactiva una acción y explica por qué */
    disable(root, key, why, c){
      const b = root.querySelector('[data-demo="' + key + '"]'); if(!b) return;
      b.setAttribute('aria-disabled', why ? 'true' : 'false');
      const w = b.querySelector('.dp-why'); if(w.textContent !== (why || '')) w.textContent = why || '';
      const row = b.closest('.dp-row'), tw = row.querySelector('.dp-tip-why');
      tw.textContent = why ? 'Ahora no está disponible: ' + why : '';
      b.title = (why ? 'Ahora no está disponible: ' + why + ' ' : '') + DP.tipText(c);
    },
    init(root, store){
      let saved = {};
      try { saved = JSON.parse(sessionStorage.getItem(store) || '{}') || {}; } catch(e) {}
      const setSec = (h, open) => { h.setAttribute('aria-expanded', open); const b = document.getElementById(h.getAttribute('aria-controls')); if(b) b.hidden = !open; };
      root.querySelectorAll('.dp-sec-h').forEach(h => {
        const id = h.dataset.sec; if(id in saved) setSec(h, !!saved[id]);
        h.addEventListener('click', () => { const open = h.getAttribute('aria-expanded') !== 'true'; setSec(h, open); saved[id] = open; try { sessionStorage.setItem(store, JSON.stringify(saved)); } catch(e) {} });
      });
      /* ayudas: se abren con el cursor encima, con el foco del teclado o con un toque (que las fija) */
      const ST = new WeakMap();
      const get = r => { let s = ST.get(r); if(!s){ s = {}; ST.set(r, s); } return s; };
      const place = row => {
        const tip = row.querySelector('.dp-tip'); tip.classList.remove('up');
        const sc = row.closest('.dp-scroll'), r = row.getBoundingClientRect(), h = tip.offsetHeight + 12;
        const top = sc ? Math.max(0, sc.getBoundingClientRect().top) : 0, bottom = Math.min(window.innerHeight, sc ? sc.getBoundingClientRect().bottom : window.innerHeight);
        if(r.bottom + h > bottom && r.top - h >= top) tip.classList.add('up');
      };
      const closeAll = except => root.querySelectorAll('.dp-row.tip-open').forEach(r => { if(r !== except){ ST.set(r, {}); r.classList.remove('tip-open'); } });
      const upd = row => { const s = get(row), on = !!(s.hover || s.focus || s.pin); if(on){ closeAll(row); place(row); } row.classList.toggle('tip-open', on); };
      root.addEventListener('pointerover', e => { const b = e.target.closest('.dp-i'); if(b && e.pointerType === 'mouse'){ const r = b.closest('.dp-row'); get(r).hover = true; upd(r); } });
      root.addEventListener('pointerout', e => { const b = e.target.closest('.dp-i'); if(b && e.pointerType === 'mouse' && !b.contains(e.relatedTarget)){ const r = b.closest('.dp-row'); get(r).hover = false; upd(r); } });
      root.addEventListener('focusin', e => { const b = e.target.closest('.dp-i'); if(b && b.matches(':focus-visible')){ const r = b.closest('.dp-row'); get(r).focus = true; upd(r); } });
      root.addEventListener('focusout', e => { const b = e.target.closest('.dp-i'); if(b){ const r = b.closest('.dp-row'); ST.set(r, {}); upd(r); } });
      root.addEventListener('click', e => { const b = e.target.closest('.dp-i'); if(!b) return; const r = b.closest('.dp-row'), s = get(r);
        if(s.pin){ ST.set(r, {}); } else s.pin = true; upd(r); });
      document.addEventListener('click', e => { if(!e.target.closest || !e.target.closest('.dp-i')) closeAll(null); });
      document.addEventListener('keydown', e => { if(e.key === 'Escape' && root.querySelector('.dp-row.tip-open')){ closeAll(null); } });
      const sc = root.querySelector('.dp-scroll'); if(sc) sc.addEventListener('scroll', () => closeAll(null), {passive: true});
    }
  };


  const CTRL = {
    approve: {l:'El celular aprobó la vinculación', icon:'check', tip:['Carmen aprueba en la app.', 'La PC muestra la casa y las webcams detectadas.']},
    reject: {l:'El celular rechazó la vinculación', icon:'x', tip:['«No reconozco esta PC» en la app.', 'La PC ofrece otro código.']},
    expire: {l:'Código vencido', icon:'clock', tip:['Pasan 10 minutos sin aprobación.', 'Aparece un código nuevo solo.']},
    re90: {l:'Más de 90 días sin conexión', icon:'clock', tip:['La PC estuvo 90 días sin internet.', 'Pide vincular de nuevo; conserva sus cámaras.']},
    net: {l:'Sin internet en la casa', sw:true, tip:['Se corta internet.', 'Se sigue detectando; los avisos esperan.']},
    server: {l:'Te Tengo no responde', sw:true, tip:['El servidor no está disponible.', 'Al vincular, la PC reintenta sola.']},
    usb: {l:'Se desconectó la cámara del Pasillo', sw:true, tip:['Se suelta el cable USB.', 'Queda punteada; con la ventana cerrada, aviso de Windows.']},
    extra: {l:'Se conectó otra webcam', sw:true, tip:['Se enchufa la HD USB Camera.', 'Aparece «Nueva · Sin usar»; las demás no cambian.']},
    busy: {l:'Otro programa usa una webcam', sw:true, tip:['Una videollamada abre la Logitech C920.', 'Cámaras pide cerrar ese programa.']},
    full: {l:'Disco lleno', sw:true, tip:['La carpeta elegida se llena.', 'Almacenamiento pide revisar el disco.']},
    near: {l:'Queda poco espacio', sw:true, tip:['Se llega al 90 % del límite.', 'Avisa que borrará el video más antiguo.']},
    live: {l:'Carmen ve una cámara en vivo', sw:true, tip:['Un familiar abre la vista en vivo.', 'Estado dice quién mira; punto morado.']},
    pause: {l:'Luis pausa la Sala hasta las 11:42', sw:true, tip:['Pausa desde la app.', 'Esa cámara no analiza; las demás siguen.']},
    consent: {l:'Falta el consentimiento', sw:true, tip:['El consentimiento de Rosa no está registrado.', 'Ninguna cámara se usa.']},
    rename: {l:'Sala renombrada a «Sala comedor»', sw:true, tip:['Carmen renombra la habitación en la app.', 'La PC muestra el nombre nuevo.']},
    assign: {l:'Carmen eligió las cámaras desde la app', icon:'cam', tip:['Carmen asigna cada webcam a una habitación.', 'La PC se actualiza sola, un aviso por cámara.']},
    unassign: {l:'Carmen dejó de usar una cámara', icon:'x', tip:['Carmen deja de usar la última cámara.', 'Vuelve a «Sin usar».']},
    peek: {l:'Carmen mira una cámara para elegirla', sw:true, tip:['Carmen pide la vista previa en la app.', 'Luz violeta «No se graba»; punto morado.']},
    removed: {l:'Carmen quitó esta PC desde la app', icon:'unlink', tip:['El titular elige «Quitar esta PC».', 'La PC deja de capturar y ofrece vincular de nuevo.']},
    revoke: {l:'Rosa ya no autoriza guardar movimientos', sw:true, tip:['Rosa revoca el permiso.', 'La PC pregunta si borra los movimientos guardados.']},
    fall: {l:'Rosa se cae frente a la Sala', icon:'warn', tip:['Simula una caída en la Sala.', 'Se ve en Avanzado: registro y medidores.']},
    noPerson: {l:'Nadie frente a la cámara de la Sala', sw:true, tip:['Rosa sale de la imagen.', 'Los medidores dicen «Sin persona en la imagen».']},
    videoStored: {l:'Hay video guardado de hoy', sw:true, tip:['El video continuo estuvo activo.', '«Ver qué pasó» puede mostrar el video.']},
    failFolder: {l:'La carpeta no permite guardar', sw:true, tip:['Sin espacio o permiso en la carpeta.', 'El diagnóstico falla sin dejar archivo.']},
    linked: {l:'Empezar con la PC ya vinculada', icon:'link', tip:['Salta la vinculación.', 'Sala, Dormitorio y Pasillo ya cuidando.']},
    reset: {l:'Reiniciar la demo', icon:'refresh', tip:['Vuelve al estado inicial.', 'Arranque y PC sin vincular.']}
  };
  const PANEL = [
    {id:'vin', t:'Vinculación', icon:'link', items:['approve', 'reject', 'expire', 're90']},
    {id:'pc', t:'Estado de la PC', icon:'monitor', items:['net', 'server', 'usb', 'extra', 'busy', 'full', 'near']},
    {id:'app', t:'Desde la app Te Tengo', icon:'mobile', items:['assign', 'unassign', 'peek', 'live', 'pause', 'consent', 'rename', 'removed', 'revoke']},
    {id:'adv', t:'Avanzado y repetición', icon:'sliders', open:false, items:['fall', 'noPerson', 'videoStored', 'failFolder']},
    {id:'go', t:'Atajos', icon:'refresh', open:false, items:['linked']}
  ];
  (function buildPanel(){
    const root = $('demo');
    root.innerHTML = '<div class="dp-scroll"><header class="dp-head"><h2 id="dp-h">Panel de demostración</h2><p>Simula el celular, la PC, las webcams y el disco.</p></header>' +
      '<dl class="dp-status" aria-label="Estado de la demostración"><div><dt>Hora</dt><dd class="mono">10:42</dd></div><div><dt>Ventana</dt><dd id="dp-win">Iniciando</dd></div>' +
      '<div class="wide"><dt>Bandeja</dt><dd id="dp-tray"><i class="dp-dot" aria-hidden="true"></i><span>Sin vincular</span></dd></div></dl>' +
      '<div class="dp-secs">' + PANEL.map(s => DP.section(s, s.items.map(k => DP.row(k, CTRL[k])).join(''))).join('') + '</div>' +
      '<p class="dp-hint">' + ic('info') + '<span>Al cerrar, sigue en la bandeja junto al reloj. Tócalo para abrir.</span></p></div>' +
      '<div class="dp-foot">' + DP.row('reset', CTRL.reset) + '</div>';
    DP.init(root, 'tt-demo-escritorio-2');
  })();
  function renderDemo(){
    const root = $('demo');
    const set = (k, on) => { const b = root.querySelector('[data-demo="' + k + '"]'); if(b) b.setAttribute('aria-pressed', !!on); };
    set('net', !S.online); set('server', !S.server); set('usb', S.lost); set('extra', S.extra); set('busy', S.busy); set('full', S.store.state==='full'); set('near', S.store.state==='near');
    set('live', !!S.live); set('pause', !!S.pause); set('consent', !S.consent); set('rename', salaCam() && salaCam().room!=='Sala'); set('revoke', !S.moveConsent);
    set('peek', !!S.peek);
    set('noPerson', !S.m.person); set('videoStored', S.store.videoStored); set('failFolder', !!S.failFolder);
    const pairing = S.screen==='vincular', canPair = pairing && S.online && S.server, main = S.screen==='main' && S.linked;
    const notPair = pairing ? (S.online ? (S.server ? '' : 'Te Tengo no responde: no hay código.') : 'Sin internet: no hay código.') : 'La PC no espera una vinculación.';
    const D = (k, why) => DP.disable(root, k, why, CTRL[k]);
    D('approve', canPair ? '' : notPair); D('reject', canPair ? '' : notPair); D('expire', canPair ? '' : notPair);
    D('re90', main ? '' : 'Funciona con la PC vinculada.');
    D('server', pairing ? '' : 'Solo se nota al vincular.');
    D('usb', ''); D('extra', S.extra && S.cams.some(c => c.id==='d4') ? 'Ya cuida una habitación: primero «Dejar de usar».' : '');
    D('busy', S.cams.some(c => c.id==='d2') ? 'La Logitech C920 ya cuida el Dormitorio.' : '');
    D('full', S.linked ? '' : 'Primero vincula la PC.'); D('near', S.linked ? '' : 'Primero vincula la PC.');
    const noCams = !main ? 'Primero vincula la PC.' : !S.cams.length ? 'Primero elige las cámaras.' : '';
    D('live', noCams); D('consent', main ? '' : 'Primero vincula la PC.');
    D('pause', noCams || (salaCam() ? '' : 'La cámara de la Sala no está en uso.'));
    D('rename', noCams || (salaCam() ? '' : 'La cámara de la Sala no está en uso.'));
    D('removed', S.linked ? '' : 'Esta PC no está vinculada.');
    const linkedNow = S.linked && ['main', 'vinculada'].includes(S.screen);
    D('assign', !linkedNow ? 'Primero vincula la PC.' : assignT.length ? 'La app está eligiendo las cámaras.' : !assignPlan().length ? (connected(S).length ? 'Todas ya tienen habitación.' : 'La PC no detecta ninguna cámara.') : '');
    D('unassign', !linkedNow ? 'Primero vincula la PC.' : S.cams.length ? '' : 'Ninguna cámara tiene habitación.');
    D('peek', !linkedNow ? 'Primero vincula la PC.' : connected(S).some(id => !isLost(S, id)) ? '' : 'La PC no detecta ninguna cámara.');
    D('revoke', S.linked ? '' : 'Primero vincula la PC.');
    D('fall', falling ? 'Ya hay una caída en curso.' : noCams || (!salaCam() ? 'La cámara de la Sala no está en uso.' : !S.consent ? 'Falta el consentimiento.' : S.pause ? 'La cámara de la Sala está en pausa.' : !S.m.person ? 'No hay nadie frente a la cámara.' : ''));
    D('noPerson', falling ? 'Hay una caída en curso.' : '');
    D('videoStored', S.linked ? '' : 'Primero vincula la PC.');
    D('linked', '');
    const t = trayState(S);
    $('dp-win').textContent = booting ? 'Iniciando' : closed ? 'En la bandeja' : 'Abierta';
    const v = '<i class="dp-dot ' + t.k + '" aria-hidden="true"></i><span>' + esc(t.label.charAt(0).toUpperCase() + t.label.slice(1)) + '</span>';
    if($('dp-tray').innerHTML !== v) $('dp-tray').innerHTML = v;
  }

  /* ---------- relojes: reintento, cuenta regresiva del código, registro y medidores en vivo ---------- */
  setInterval(() => {
    if(!S) return;
    if(!S.online || (S.screen==='vincular' && !S.server)){
      const ms = S.screen==='vincular', max = ms ? 25 : 10;
      S.retry = S.retry <= 1 ? max : S.retry - 1;
      const r = $('retry'); if(r) r.textContent = r.dataset.fmt==='ms' ? mmss(S.retry) : S.retry;
    }
    if(S.screen==='vincular' && S.online && S.server && !booting){
      S.pair.left--;
      if(S.pair.left===60) announce('pair-ann', 'El código vence en 1 minuto');
      if(S.pair.left <= 0){ const re = S.pair.re90; newCode(); S.pair.renewed = true; S.pair.re90 = re; render(); announce('pair-ann', 'Código nuevo'); return; }
      const e = $('pair-left'); if(e){ e.textContent = mmss(S.pair.left); e.parentNode.classList.toggle('low', S.pair.left <= 60); }
    }
  }, 1000);
  setInterval(() => {
    if(!S || !S.adv.on || falling || closed) return;
    const m = S.m, j = (a, b) => a + Math.random()*(b-a);
    m.fps = j(7.6, 8); m.cpu = j(30, 40); m.lat = j(.08, .11); m.m1 = j(.002, .006); m.m2 = j(70, 75); m.m3 = j(.58, .66);
    for(const k in m.vis) m.vis[k] = Math.max(.2, Math.min(.98, m.vis[k] + j(-.02, .02)));
    if(S.tab==='avanzado' && !S.replay && advSub(S)==='medidores') paintMeters();
  }, 500);
  setInterval(() => {
    if(!S || !S.linked || S.screen!=='main' || falling || !S.consent || !S.m.person) return;
    const c = salaCam(); if(!c || S.pause) return;
    addLine(c.room, LOG_LIVE[liveIdx % LOG_LIVE.length]);
  }, 2600);

  /* ---------- escala del escritorio ---------- */
  function fit(){
    const narrow = window.innerWidth <= 900;
    const availW = narrow ? window.innerWidth - 40 : window.innerWidth - 40 - 24 - 320;
    const availH = narrow ? Infinity : window.innerHeight - 40;
    const s = Math.min(1, availW/1120, availH/760);
    $('fit').style.zoom = s;
  }
  window.addEventListener('resize', fit);

  init(); fit(); boot();
})();
