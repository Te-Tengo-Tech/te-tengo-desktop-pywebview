/* ================= Te Tengo Captura · ventana de estado =================
   Port of the prototype (docs/references/desktop-prototype/src/core.js and proto.js): icons, brand,
   room illustration, title bar and the status screen. The state and its Spanish copy come from
   Python (te_tengo_captura/estado.py) through ttg.actualizar(); this file only renders it.
   The bridge is window.pywebview.api: estado(), minimizar(), cerrar(), buscarWebcam(),
   reintentarAhora(). */
(function(global){
  'use strict';

  /* ---------- íconos (core.js) ---------- */
  const P = {
    home:'<path d="M3.5 11 12 4l8.5 7"/><path d="M6 9.5V20h12V9.5"/>',
    pause:'<path d="M8.5 5v14M15.5 5v14" stroke-width="3"/>',
    wifiOff:'<path d="M3 3l18 18"/><path d="M8.6 16.3a4.9 4.9 0 0 1 6.3-.5"/><path d="M5 12.8a10 10 0 0 1 4.3-2.4M19 12.8a10 10 0 0 0-2.7-1.9"/><path d="M2 9.2a14.7 14.7 0 0 1 4.2-2.7M22 9.2A14.8 14.8 0 0 0 10.8 5"/><circle cx="12" cy="19.6" r="1.1" fill="currentColor" stroke="none"/>',
    check:'<path d="M4.5 12.5l5 5L20 7"/>',
    lock:'<rect x="5" y="10.5" width="14" height="10" rx="3"/><path d="M8.2 10.5V7.6a3.8 3.8 0 0 1 7.6 0v2.9"/>',
    info:'<circle cx="12" cy="12" r="8.5"/><path d="M12 11v5.5"/><circle cx="12" cy="7.8" r="1.1" fill="currentColor" stroke="none"/>',
    doc:'<path d="M6.5 3h8l4 4v14h-12V3Z"/><path d="M14.5 3v4h4M9.5 12h6M9.5 16h6"/>',
    refresh:'<path d="M20 12a8 8 0 1 1-2.4-5.7"/><path d="M20 4v4.5h-4.5"/>',
    usb:'<rect x="8.5" y="2.5" width="7" height="6" rx="1"/><path d="M10.8 5h0M13.2 5h0" stroke-width="2.2"/><path d="M6.5 8.5h11V13a5.5 5.5 0 0 1-11 0Z"/><path d="M12 18.5v3"/>',
    mobile:'<rect x="6.5" y="2.5" width="11" height="19" rx="3"/><path d="M10.5 18.5h3"/>',
    upload:'<path d="M12 15.5V4.5M7.5 9l4.5-4.5L16.5 9"/><path d="M4.5 14.5v3.5a2 2 0 0 0 2 2h11a2 2 0 0 0 2-2v-3.5"/>',
    videoOff:'<path d="M3 3l18 18"/><path d="M16 16v.5a2.5 2.5 0 0 1-2.5 2.5H5a2.5 2.5 0 0 1-2.5-2.5v-7A2.5 2.5 0 0 1 5 7h1"/><path d="M10 7h3.5A2.5 2.5 0 0 1 16 9.5v2l5.5-3v9"/>',
    power:'<path d="M12 3v8"/><path d="M6.6 6.6a7.5 7.5 0 1 0 10.8 0"/>'
  };
  function ic(n){ return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'+P[n]+'</svg>'; }
  const WG = {min:'<path d="M0 5.5h10"/>', max:'<rect x=".5" y=".5" width="9" height="9" rx="1.4"/>', close:'<path d="M.6.6l8.8 8.8M9.4.6.6 9.4"/>'};
  function wg(n){ return '<svg viewBox="0 0 10 10" fill="none" stroke="currentColor" stroke-width="1" aria-hidden="true">'+WG[n]+'</svg>'; }
  function esc(s){ return String(s==null?'':s).replace(/[&<>"]/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }

  /* ---------- marca: «La T que sostiene» (core.js) ---------- */
  const BRAND = {morado:'#4A2A85', coral:'#E8765A', durazno:'#FFB59C'};
  function symbolParts(stroke, dot){ return '<g fill="none" stroke="'+stroke+'" stroke-width="13" stroke-linecap="round"><path d="M60 60 V96"/><path d="M22 38 Q60 80 98 38"/></g><circle cx="60" cy="38" r="11" fill="'+dot+'"/>'; }
  const LOGO = '<svg viewBox="0 0 120 120" aria-hidden="true"><rect width="120" height="120" rx="28" fill="'+BRAND.morado+'"/>'+symbolParts('#FFFFFF', BRAND.durazno)+'</svg>';
  function appIcon(cls){ return '<span class="appicon'+(cls?' '+cls:'')+'">'+LOGO+'</span>'; }

  /* ---------- ilustración de habitación, sin personas (core.js) ---------- */
  function roomSVG(room){
    const wall='#E7E3EE', wall2='#DDD7E7', floor='#CFC7DC', f2='#C3BAD3', furn='#B3A8C7', furn2='#9E91B6', wood='#D9C1AE', win='#D5DDE8';
    let s='<svg class="room" viewBox="0 0 320 180" preserveAspectRatio="xMidYMid slice" aria-hidden="true">';
    s+='<rect width="320" height="180" fill="'+wall+'"/><rect width="320" height="10" fill="'+wall2+'"/>';
    s+='<path d="M0 138h320v42H0Z" fill="'+floor+'"/><path d="M0 138h320" stroke="'+f2+'" stroke-width="3"/>';
    if(room==='Sala'){
      s+='<rect x="150" y="26" width="86" height="60" rx="4" fill="'+win+'"/><path d="M193 26v60M150 56h86" stroke="#fff" stroke-width="3"/>';
      s+='<rect x="18" y="88" width="112" height="30" rx="10" fill="'+furn+'"/><rect x="12" y="110" width="124" height="28" rx="8" fill="'+furn2+'"/><rect x="18" y="136" width="6" height="8" fill="'+furn2+'"/><rect x="124" y="136" width="6" height="8" fill="'+furn2+'"/>';
      s+='<path d="M286 56v82" stroke="'+furn2+'" stroke-width="3"/><path d="M272 56h28l-6-20h-16Z" fill="'+wood+'"/><ellipse cx="286" cy="140" rx="14" ry="3" fill="'+f2+'"/>';
      s+='<ellipse cx="200" cy="162" rx="92" ry="12" fill="'+f2+'"/><rect x="176" y="118" width="54" height="8" rx="3" fill="'+wood+'"/><path d="M182 126v12M224 126v12" stroke="'+wood+'" stroke-width="3"/>';
    } else if(room==='Dormitorio'){
      s+='<rect x="206" y="24" width="74" height="58" rx="4" fill="'+win+'"/><path d="M243 24v58" stroke="#fff" stroke-width="3"/>';
      s+='<rect x="14" y="76" width="14" height="66" rx="4" fill="'+wood+'"/><rect x="24" y="102" width="138" height="30" rx="8" fill="#EDE9F3"/><rect x="24" y="120" width="138" height="20" rx="4" fill="'+furn2+'"/><rect x="30" y="94" width="40" height="14" rx="6" fill="#fff"/>';
      s+='<rect x="172" y="102" width="30" height="38" rx="4" fill="'+wood+'"/><path d="M187 102v-18" stroke="'+furn2+'" stroke-width="3"/><path d="M178 84h18l-4-14h-10Z" fill="'+furn+'"/>';
      s+='<rect x="236" y="96" width="62" height="44" rx="4" fill="'+furn+'"/><path d="M236 118h62" stroke="'+wall+'" stroke-width="2"/>';
    } else if(room==='Cocina'){
      s+='<rect x="0" y="24" width="150" height="38" rx="3" fill="'+furn+'"/><path d="M50 24v38M100 24v38" stroke="'+wall+'" stroke-width="2"/>';
      s+='<rect x="0" y="94" width="160" height="44" fill="'+furn2+'"/><rect x="0" y="90" width="164" height="8" rx="2" fill="'+wood+'"/><path d="M54 100v34M108 100v34" stroke="'+furn+'" stroke-width="2"/>';
      s+='<rect x="176" y="30" width="52" height="44" rx="4" fill="'+win+'"/><path d="M202 30v44" stroke="#fff" stroke-width="3"/>';
      s+='<rect x="252" y="38" width="54" height="100" rx="8" fill="#EEEAF4" stroke="'+furn+'" stroke-width="2"/><path d="M252 78h54M260 52v14M260 86v20" stroke="'+furn+'" stroke-width="3"/>';
    } else {
      s+='<rect x="30" y="34" width="54" height="104" rx="3" fill="'+wood+'"/><circle cx="74" cy="90" r="3" fill="'+furn2+'"/>';
      s+='<rect x="236" y="34" width="54" height="104" rx="3" fill="'+wood+'"/><circle cx="246" cy="90" r="3" fill="'+furn2+'"/>';
      s+='<rect x="128" y="44" width="64" height="42" rx="3" fill="#fff" stroke="'+furn+'" stroke-width="3"/><path d="M136 78l14-16 10 10 8-6 16 12" stroke="'+furn2+'" stroke-width="2.5" fill="none" stroke-linejoin="round"/>';
      s+='<path d="M110 180l20-42h60l20 42Z" fill="'+f2+'"/>';
    }
    return s+'</svg>';
  }

  /* ---------- ventana (core.js) ---------- */
  function titlebar(){
    return '<div class="tb pywebview-drag-region"><div class="tb-app">'+appIcon('xs')+'<span>Te Tengo Captura</span></div><div class="tb-btns">'+
      '<button class="tb-btn" data-act="minimize" aria-label="Minimizar" title="Minimizar">'+wg('min')+'</button>'+
      '<button class="tb-btn" aria-disabled="true" tabindex="-1" aria-label="Maximizar (no disponible)" title="Maximizar">'+wg('max')+'</button>'+
      '<button class="tb-btn close" data-act="close" aria-label="Cerrar" title="Cerrar">'+wg('close')+'</button></div></div>';
  }
  /* health(S): the banner. Its texts come from estado.py; titulo_html is already escaped. */
  function health(E){
    const h = E.health, a = h.accion;
    const btn = a ? '<button class="btn '+a.clase+' btn-sm" data-act="'+a.act+'">'+ic('refresh')+esc(a.texto)+'</button>' : '';
    return '<div class="health '+h.clase+'" role="status"><span class="st '+h.k+'">'+ic(h.icono)+'</span>'+
      '<div class="grow"><b data-r="ht">'+h.titulo_html+'</b><span data-r="hs">'+esc(h.detalle)+'</span></div>'+btn+'</div>';
  }
  function scrEstado(E, enter){
    const st = E.cam, home = E.home, conf = E.conf;
    return '<section class="scr estado'+(enter?' '+enter:'')+'" aria-labelledby="scr-h">'+
      '<header class="cam-head"><div><h1 class="t-title" id="scr-h" tabindex="-1">Vivienda de '+esc(home.who)+'</h1><p class="t-meta mt4">'+ic('home')+esc(home.addr)+'</p></div></header>'+
      health(E)+
      '<div class="est-grid">'+
        '<section class="card est-cam" aria-labelledby="cam-h"><span class="thumb art'+(st.k!=='send'?' dim':'')+'">'+roomSVG(E.room)+'</span>'+
          '<div class="est-cam-b"><p class="grp-l">Cámara de esta casa</p><h2 class="t-h2" id="cam-h">'+esc(E.room)+'</h2>'+
          '<p class="cam-dev">'+ic('usb')+esc(conf.webcam)+'</p>'+
          '<div class="cam-st"><span class="st '+st.k+'">'+ic(st.icono)+'</span><span class="grow"><b class="stx '+st.k+'">'+esc(st.titulo)+'</b><span class="t-meta" data-r="cs">'+st.detalle_html+'</span></span></div></div></section>'+
        '<section class="card est-conf" aria-labelledby="conf-h"><h2 class="conf-h" id="conf-h">'+ic('lock')+'Configurada por el equipo del proyecto</h2>'+
          '<dl class="conf-kv">'+
          '<div><dt>Vivienda</dt><dd>'+esc(home.who)+'</dd></div>'+
          '<div><dt>Webcam</dt><dd>'+esc(conf.webcam)+'<span>'+esc(conf.spec)+'</span></dd></div>'+
          '<div><dt>Habitación</dt><dd>'+esc(E.room)+'<span>El nombre se cambia en la app Te Tengo</span></dd></div>'+
          '<div><dt>Instalación</dt><dd>'+esc(conf.installed)+'</dd></div>'+
          '</dl><p class="conf-note">'+ic('info')+'<span>Solo lectura. Esta PC usa una configuración fija; si algo no funciona, avisa al equipo del proyecto.</span></p></section>'+
      '</div>'+
      '<p class="scr-foot">'+ic('mobile')+'Las pausas, el consentimiento, el nombre de la habitación y las alertas se gestionan en la app Te Tengo.<span class="sep"></span>'+ic('power')+'Se inicia con Windows</p></section>';
  }
  function win(E, enter, toast){
    const t = toast ? '<div class="wtoast '+toast.kind+'" role="status">'+ic(toast.icon)+'<span>'+esc(toast.text)+'</span></div>' : '';
    return titlebar()+'<div class="wb">'+scrEstado(E, enter)+t+'</div>';
  }

  /* ---------- avisos dentro de la ventana al cambiar el estado (proto.js) ---------- */
  function transition(prev, E){
    if(!prev || !prev.listo || !E.listo) return null;
    const a = prev.situacion, b = E.situacion;
    if(a === 'webcam_desconectada' && b !== a) return {kind:'ok', icon:'usb', text:'Se volvió a conectar la '+E.conf.webcam+'. El envío se reanudó.'};
    if(a === 'sin_internet' && b !== a && b !== 'webcam_desconectada') return {kind:'ok', icon:'check', text:'Conexión restablecida. El envío se reanudó.'};
    if(a === 'sin_consentimiento' && b === 'enviando') return {kind:'ok', icon:'check', text:'Consentimiento registrado en la app Te Tengo. Empezó el envío.'};
    if(a === 'enviando' && b === 'en_pausa') return {kind:'ok', icon:'pause', text:'La familia pausó la cámara desde la app Te Tengo hasta las '+E.pause+'.'};
    if(a === 'en_pausa' && b === 'enviando') return {kind:'ok', icon:'upload', text:'La pausa terminó: el envío se reanudó.'};
    if(prev.room !== E.room) return {kind:'ok', icon:'check', text:'La familia cambió el nombre de la habitación en la app: «'+E.room+'».'};
    return null;
  }
  /* What forces a full render; anything else only patches the [data-r] regions in place. */
  function structure(E){ return [E.situacion, E.room, E.home.who, E.home.addr, E.conf.webcam, E.conf.spec, E.conf.installed].join('\u0001'); }

  const api = { ic, esc, roomSVG, titlebar, health, scrEstado, win, transition, structure };

  /* ---------- DOM: render with focus preserved ---------- */
  if(typeof document === 'undefined'){ if(typeof module !== 'undefined') module.exports = api; return; }

  const $ = id => document.getElementById(id);
  let E = null, toast = null, toastTimer = null, first = true;
  const bridge = () => (global.pywebview && global.pywebview.api) || null;

  function snap(){
    const a = document.activeElement;
    if(!a || a === document.body || !$('app').contains(a)) return null;
    return {id:a.id, act:a.dataset && a.dataset.act};
  }
  function restore(f){
    if(!f) return;
    let el = f.id ? $(f.id) : null;
    if(!el && f.act) el = document.querySelector('#app [data-act="'+f.act+'"]');
    if(el && !el.disabled) el.focus({preventScroll:true});
  }
  function render(enter){
    const f = enter ? null : snap();
    $('app').innerHTML = win(E, enter, toast);
    if(enter){ const t = $('scr-h'); if(t) t.focus({preventScroll:true}); } else restore(f);
  }
  function patch(){
    const tpl = document.createElement('template');
    tpl.innerHTML = win(E, '', toast);
    tpl.content.querySelectorAll('[data-r]').forEach(nuevo => {
      const actual = document.querySelector('#app [data-r="'+nuevo.dataset.r+'"]');
      if(actual && actual.innerHTML !== nuevo.innerHTML) actual.innerHTML = nuevo.innerHTML;
    });
  }
  function showToast(t){
    toast = t; render();
    clearTimeout(toastTimer);
    toastTimer = setTimeout(()=>{ toast = null; render(); }, 3800);
  }
  function actualizar(nuevo){
    const prev = E; E = nuevo;
    const t = transition(prev, E);
    if(first){ first = false; render('enter'); }
    else if(t) showToast(t);
    else if(structure(prev) !== structure(E)) render();
    else patch();
  }

  /* ---------- acciones ---------- */
  function call(name){ const b = bridge(); return b && b[name] ? Promise.resolve(b[name]()) : Promise.resolve(null); }
  const ACT = {
    minimize(){ call('minimizar'); },
    close(){ call('cerrar'); },
    retryNow(){
      call('reintentarAhora').then(r => { if(r && !r.ok) showToast({kind:'warn', icon:'wifiOff', text:'Aún sin internet. Seguimos intentando.'}); });
    },
    rescan(el){
      el.classList.add('loading'); el.innerHTML = '<span class="spin"></span>Buscando…';
      call('buscarWebcam').then(r => {
        if(r && !r.ok) showToast({kind:'warn', icon:'videoOff', text:'No encontramos la webcam. Revisa el cable USB y vuelve a intentarlo.'});
        else render();
      });
    }
  };
  document.addEventListener('click', e => {
    const t = e.target.closest('[data-act]');
    if(t && ACT[t.dataset.act] && !t.disabled && t.getAttribute('aria-disabled') !== 'true'){ e.preventDefault(); ACT[t.dataset.act](t); }
  });

  global.ttg = { actualizar };
  global.addEventListener('pywebviewready', () => { call('estado').then(s => { if(s) actualizar(s); }); });
})(typeof window !== 'undefined' ? window : globalThis);
