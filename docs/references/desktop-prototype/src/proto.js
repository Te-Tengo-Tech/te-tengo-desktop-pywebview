/* ================= Te Tengo Captura · prototipo navegable (prueba piloto) =================
   Arranque → ventana de estado de la única webcam, configurada por el equipo del proyecto →
   minimizar o cerrar a la bandeja (ícono con punto de estado y aviso del sistema). Sin vinculación de cámaras. */
(function(){
  'use strict';
  const $ = id => document.getElementById(id);

  let S, closed, osKind, enterCls, toastTimer, osTimer, booting = false, bootTimers = [], rescanT = null;
  function init(){
    S = baseState();
    closed = false; osKind = null; enterCls = '';
    clearTimeout(toastTimer); clearTimeout(osTimer); clearTimeout(rescanT);
  }

  /* ---------- render con foco preservado ---------- */
  function snap(){
    const a = document.activeElement;
    if(!a || a===document.body || !$('winslot').contains(a) && !$('tbwrap').contains(a)) return null;
    return {id:a.id, act:a.dataset && a.dataset.act};
  }
  function restore(f){
    if(!f) return;
    let el = f.id ? $(f.id) : null;
    if(!el && f.act) el = document.querySelector('#winslot [data-act="'+f.act+'"]');
    if(el && !el.disabled) el.focus({preventScroll:true});
  }
  function render(focusScreen){
    const f = focusScreen ? null : snap();
    const slot = $('winslot');
    slot.innerHTML = win(S, {enter:enterCls});
    enterCls = '';
    slot.classList.toggle('hidden', closed || booting);
    slot.setAttribute('aria-hidden', closed || booting ? 'true' : 'false');
    $('tbwrap').innerHTML = taskbar(S, {open:!closed, hl:!!osKind});
    $('ostoast').innerHTML = osKind ? osToast(S, osKind) : '';
    renderDemo();
    if(focusScreen && !closed && !booting){ const t = $('scr-h'); if(t) t.focus({preventScroll:true}); }
    else restore(f);
  }
  function toast(kind, icon, text){
    S.toast = {kind, icon, text}; render();
    clearTimeout(toastTimer);
    toastTimer = setTimeout(()=>{ S.toast = null; render(); }, 3800);
  }
  function osNotify(kind){
    osKind = kind; render();
    clearTimeout(osTimer); osTimer = setTimeout(()=>{ osKind = null; render(); }, 8000);
  }

  /* ---------- arranque: ventana de inicio y luego la ventana de estado ---------- */
  function boot(){
    bootTimers.forEach(clearTimeout); bootTimers = [];
    booting = true; render();
    const bs = $('bootslot');
    bs.innerHTML = bootWin({play:true, pct:0, step:0});
    const bar = bs.querySelector('.boot-bar'), fill = bar.querySelector('i'), txt = $('boot-st');
    const at = (ms, fn) => bootTimers.push(setTimeout(fn, ms));
    const set = (p, k) => { fill.style.transform = 'scaleX('+(p/100)+')'; bar.setAttribute('aria-valuenow', p); if(k!=null) txt.textContent = BOOT_STEPS[k]; };
    at(80, ()=>set(22));
    at(720, ()=>set(54, 1));
    at(1340, ()=>set(86, 2));
    at(1820, ()=>set(100));
    at(2060, ()=>{ const b = bs.querySelector('.boot'); if(b) b.classList.add('out'); });
    at(2240, ()=>{ bs.innerHTML = ''; booting = false; enterCls = 'enter'; render(true); });
  }

  /* ---------- ventana y bandeja ---------- */
  function hideWindow(){ closed = true; osNotify('closed'); }
  function openWindow(){ closed = false; osKind = null; clearTimeout(osTimer); render(true); }

  /* ---------- acciones de la interfaz ---------- */
  const ACT = {
    retryNow(){ S.retry = 10; toast('warn','wifiOff','Aún sin internet. Seguimos intentando.'); },
    rescan(){
      const b = document.querySelector('#winslot [data-act="rescan"]'); if(b){ b.classList.add('loading'); b.innerHTML = '<span class="spin"></span>Buscando…'; }
      clearTimeout(rescanT); rescanT = setTimeout(()=>{ toast('warn','videoOff','No encontramos la webcam. Revisa el cable USB y vuelve a intentarlo.'); }, 900);
    },
    minimize: hideWindow, close: hideWindow,
    trayOpen: openWindow,
    toastClose(){ osKind = null; clearTimeout(osTimer); render(); }
  };
  document.addEventListener('click', e=>{
    const t = e.target.closest('[data-act]');
    if(t && ACT[t.dataset.act] && !t.disabled && t.getAttribute('aria-disabled')!=='true'){ e.preventDefault(); ACT[t.dataset.act](t.dataset.arg); return; }
    const d = e.target.closest('[data-demo]');
    if(d && !d.disabled) DEMO[d.dataset.demo]();
  });
  document.addEventListener('keydown', e=>{ if(e.key==='Escape' && osKind){ ACT.toastClose(); } });

  /* ---------- panel de demostración: lo que pasa fuera de la ventana ---------- */
  const DEMO = {
    pause(){
      S.pause = S.pause ? null : '15:00';
      if(closed) return render();
      if(S.pause) toast('ok','pause','La familia pausó la cámara desde la app Te Tengo hasta las 15:00.');
      else toast('ok','upload','La pausa terminó: el envío se reanudó.');
    },
    consent(){
      S.consent = !S.consent;
      if(closed) return render();
      if(S.consent) toast('ok','check','Consentimiento registrado en la app Te Tengo. Empezó el envío.');
      else render();
    },
    net(){
      S.online = !S.online; S.retry = 8;
      if(closed) return render();
      if(S.online) toast('ok','check','Conexión restablecida. El envío se reanudó.');
      else render();
    },
    usb(){
      S.lost = !S.lost; clearTimeout(rescanT);
      if(S.lost){ if(closed) osNotify('lost'); else render(); }
      else { if(closed) render(); else toast('ok','usb','Se volvió a conectar la '+CONF.webcam+'. El envío se reanudó.'); }
    },
    rename(){
      S.room = S.room==='Sala' ? 'Sala comedor' : 'Sala';
      if(closed) return render();
      toast('ok','check','La familia cambió el nombre de la habitación en la app: «'+S.room+'».');
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
    net: {l:'Sin internet en la casa', sw:true, tip:['Se corta la conexión a internet de la PC.', 'La ventana muestra «Sin internet, reintentando» con una cuenta regresiva y el punto de la bandeja pasa a ámbar. Vuelve a tocar para restablecerla.']},
    usb: {l:'Webcam USB desconectada', sw:true, tip:['Se suelta el cable USB de la webcam.', 'La ventana pide revisar el cable y ofrece «Buscar de nuevo». Con la ventana cerrada, aparece un aviso de Windows junto al reloj.']},
    pause: {l:'Cámara en pausa hasta las 15:00', sw:true, tip:['Un familiar pausa la cámara desde la app Te Tengo.', 'La ventana muestra «En pausa» con la hora en que se reanuda, no se envía video y el punto de la bandeja pasa a gris.']},
    consent: {l:'Falta el consentimiento', sw:true, tip:['El consentimiento de Rosa todavía no está registrado en la app.', 'La webcam no envía video y la ventana explica que se espera el consentimiento. Al registrarlo, el envío empieza solo.']},
    rename: {l:'Habitación renombrada a «Sala comedor»', sw:true, tip:['Carmen cambia el nombre de la habitación en la app.', 'La ventana muestra el nombre nuevo en la cámara y en la configuración. Vuelve a tocar para llamarla «Sala» otra vez.']},
    reset: {l:'Reiniciar la demo', icon:'refresh', tip:['Vuelve todo al estado inicial.', 'Se repite la ventana de arranque y luego la cámara aparece enviando video.']}
  };
  const PANEL = [
    {id:'pc', t:'Estado de la PC', icon:'monitor', items:['net', 'usb']},
    {id:'app', t:'Desde la app Te Tengo', icon:'mobile', items:['pause', 'consent', 'rename']}
  ];
  (function buildPanel(){
    const root = $('demo');
    root.innerHTML = '<div class="dp-scroll"><header class="dp-head"><h2 id="dp-h">Panel de demostración</h2><p>Simula lo que pasa fuera de esta ventana: la PC, la webcam y la app de la familia.</p></header>' +
      '<dl class="dp-status" aria-label="Estado de la demostración"><div><dt>Hora</dt><dd class="mono">10:42</dd></div><div><dt>Ventana</dt><dd id="dp-win">Iniciando</dd></div>' +
      '<div class="wide"><dt>Bandeja</dt><dd id="dp-tray"><i class="dp-dot" aria-hidden="true"></i><span>Enviando video</span></dd></div></dl>' +
      '<div class="dp-secs">' + PANEL.map(s => DP.section(s, s.items.map(k => DP.row(k, CTRL[k])).join(''))).join('') + '</div>' +
      '<p class="dp-hint">' + ic('info') + '<span>Cierra o minimiza la ventana: el programa sigue en la bandeja, junto al reloj. Toca su ícono para abrirla otra vez. Si desconectas la webcam con la ventana cerrada, aparece un aviso de Windows.</span></p></div>' +
      '<div class="dp-foot">' + DP.row('reset', CTRL.reset) + '</div>';
    DP.init(root, 'tt-demo-escritorio');
  })();
  function renderDemo(){
    const set = (k, on) => { const b = document.querySelector('#demo [data-demo="' + k + '"]'); if(b) b.setAttribute('aria-pressed', !!on); };
    set('pause', !!S.pause); set('consent', !S.consent); set('net', !S.online); set('usb', S.lost); set('rename', S.room !== 'Sala');
    const t = trayState(S);
    $('dp-win').textContent = booting ? 'Iniciando' : closed ? 'En la bandeja' : 'Abierta';
    const v = '<i class="dp-dot ' + t.k + '" aria-hidden="true"></i><span>' + esc(t.label.charAt(0).toUpperCase() + t.label.slice(1)) + '</span>';
    if($('dp-tray').innerHTML !== v) $('dp-tray').innerHTML = v;
  }

  /* ---------- cuenta regresiva de reconexión ---------- */
  setInterval(()=>{
    if(S.online) return;
    S.retry = S.retry<=1 ? 10 : S.retry-1;
    const r = $('retry'); if(r) r.textContent = S.retry;
  }, 1000);

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
