/* ================= Te Tengo Captura · ventana =================
   Port of the desktop prototype (docs/references/desktop-prototype/src/core.js and proto.js):
   icons, brand kit (two figures hugging), room illustrations, title bar, «Vincular esta PC»
   (QR and code), the result screens (vinculada, rechazada, quitada), the tab bar
   (Estado · Cámaras) and their panels, the dialogs, in-window notices and the splash.
   Every state-dependent text comes from Python (te_tengo_captura/estado.py) through
   ttg.actualizar(); this file renders it, keeps what only the window knows (the open tab, the
   selected camera, the folded sections) and calls the bridge window.pywebview.api:
   estado(), minimizar(), cerrar(), buscarWebcam(), reintentarAhora(), vistaPrevia(clave),
   otroCodigo(), vincularDeNuevo(), irAEstado(), desvincular(borrarDatos), and the updates of
   US-43: buscarActualizaciones(), descargarActualizacion(), cancelarActualizacion(),
   irALaDescarga(), actualizarAutomaticamente(activar). */
(function(global){
  'use strict';

  /* ---------- íconos (core.js) ---------- */
  const P = {
    home:'<path d="M3.5 11 12 4l8.5 7"/><path d="M6 9.5V20h12V9.5"/>',
    cam:'<rect x="4" y="3" width="16" height="12.5" rx="6.25"/><circle cx="12" cy="9.25" r="2.8"/><path d="M8.5 21h7M12 15.5V21"/>',
    pause:'<path d="M8.5 5v14M15.5 5v14" stroke-width="3"/>',
    wifiOff:'<path d="M3 3l18 18"/><path d="M8.6 16.3a4.9 4.9 0 0 1 6.3-.5"/><path d="M5 12.8a10 10 0 0 1 4.3-2.4M19 12.8a10 10 0 0 0-2.7-1.9"/><path d="M2 9.2a14.7 14.7 0 0 1 4.2-2.7M22 9.2A14.8 14.8 0 0 0 10.8 5"/><circle cx="12" cy="19.6" r="1.1" fill="currentColor" stroke="none"/>',
    wifi:'<path d="M2.5 9.2a14.5 14.5 0 0 1 19 0M5.5 12.6a10 10 0 0 1 13 0M8.6 16a5 5 0 0 1 6.8 0"/><circle cx="12" cy="19.4" r="1.1" fill="currentColor" stroke="none"/>',
    check:'<path d="M4.5 12.5l5 5L20 7"/>',
    x:'<path d="M6 6l12 12M18 6 6 18"/>',
    chevR:'<path d="M9 5l7 7-7 7"/>',
    chevUp:'<path d="M5 15l7-7 7 7"/>',
    chevDown:'<path d="M6 9l6 6 6-6"/>',
    back:'<path d="M20 12H5M11 5l-7 7 7 7"/>',
    lock:'<rect x="5" y="10.5" width="14" height="10" rx="3"/><path d="M8.2 10.5V7.6a3.8 3.8 0 0 1 7.6 0v2.9"/>',
    eye:'<path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12Z"/><circle cx="12" cy="12" r="3"/>',
    eyeOff:'<path d="M3 3l18 18"/><path d="M10.6 6A9.5 9.5 0 0 1 21.5 12a15 15 0 0 1-2.7 3.4M6.4 7.6A14.5 14.5 0 0 0 2.5 12S6 18.5 12 18.5a9 9 0 0 0 4-1"/><path d="M9.9 10a3 3 0 0 0 4.1 4.1"/>',
    plus:'<path d="M12 5v14M5 12h14"/>',
    clock:'<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>',
    help:'<circle cx="12" cy="12" r="8.5"/><path d="M9.6 9.4a2.5 2.5 0 0 1 4.85.85c0 1.7-2.45 2.2-2.45 3.75"/><circle cx="12" cy="17" r="1.1" fill="currentColor" stroke="none"/>',
    info:'<circle cx="12" cy="12" r="8.5"/><path d="M12 11v5.5"/><circle cx="12" cy="7.8" r="1.1" fill="currentColor" stroke="none"/>',
    warn:'<path d="M12 3.5 21.5 20h-19L12 3.5Z"/><path d="M12 9.5v5"/><circle cx="12" cy="17.3" r="1.1" fill="currentColor" stroke="none"/>',
    key:'<circle cx="8" cy="15" r="4.5"/><path d="M11.2 11.8 20 3M16.5 6.5l2.5 2.5M14 9l2 2"/>',
    doc:'<path d="M6.5 3h8l4 4v14h-12V3Z"/><path d="M14.5 3v4h4M9.5 12h6M9.5 16h6"/>',
    refresh:'<path d="M20 12a8 8 0 1 1-2.4-5.7"/><path d="M20 4v4.5h-4.5"/>',
    battery:'<rect x="2.5" y="7" width="17" height="10" rx="3"/><rect x="4.5" y="9" width="11" height="6" rx="1.5" fill="currentColor" stroke="none"/><path d="M21.5 10.5v3"/>',
    signal:'<path d="M4 18v-2M9 18v-5M14 18v-8M19 18V7" stroke-width="2.6"/>',
    usb:'<rect x="8.5" y="2.5" width="7" height="6" rx="1"/><path d="M10.8 5h0M13.2 5h0" stroke-width="2.2"/><path d="M6.5 8.5h11V13a5.5 5.5 0 0 1-11 0Z"/><path d="M12 18.5v3"/>',
    sun:'<circle cx="12" cy="12" r="4"/><path d="M12 2.5v2M12 19.5v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M2.5 12h2M19.5 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4"/>',
    monitor:'<rect x="2.5" y="4" width="19" height="12.5" rx="2.5"/><path d="M8.5 20.5h7M12 16.5v4"/>',
    mobile:'<rect x="6.5" y="2.5" width="11" height="19" rx="3"/><path d="M10.5 18.5h3"/>',
    upload:'<path d="M12 15.5V4.5M7.5 9l4.5-4.5L16.5 9"/><path d="M4.5 14.5v3.5a2 2 0 0 0 2 2h11a2 2 0 0 0 2-2v-3.5"/>',
    cloud:'<path d="M7 18.5h10.5a4 4 0 0 0 .6-7.95A6 6 0 0 0 6.6 9.1 4.7 4.7 0 0 0 7 18.5Z"/>',
    videoOff:'<path d="M3 3l18 18"/><path d="M16 16v.5a2.5 2.5 0 0 1-2.5 2.5H5a2.5 2.5 0 0 1-2.5-2.5v-7A2.5 2.5 0 0 1 5 7h1"/><path d="M10 7h3.5A2.5 2.5 0 0 1 16 9.5v2l5.5-3v9"/>',
    link:'<path d="M10 14a4.5 4.5 0 0 0 6.4 0l3-3a4.5 4.5 0 0 0-6.4-6.4l-1.2 1.2"/><path d="M14 10a4.5 4.5 0 0 0-6.4 0l-3 3a4.5 4.5 0 0 0 6.4 6.4l1.2-1.2"/>',
    unlink:'<path d="M14.8 6.3l1.4-1.4a4.5 4.5 0 0 1 6.4 6.4l-1.4 1.4" transform="translate(-1.6 0)"/><path d="M9.2 17.7l-1.4 1.4a4.5 4.5 0 0 1-6.4-6.4l1.4-1.4" transform="translate(1.6 0)"/><path d="M8.5 3v3M3 8.5h3M15.5 21v-3M21 15.5h-3"/>',
    power:'<path d="M12 3v8"/><path d="M6.6 6.6a7.5 7.5 0 1 0 10.8 0"/>',
    volume:'<path d="M4 9.5h3.5L12 5.5v13l-4.5-4H4Z"/><path d="M15.5 9a4.2 4.2 0 0 1 0 6M18.2 6.5a8 8 0 0 1 0 11"/>',
    folder:'<path d="M3 6.5a2 2 0 0 1 2-2h4.2l2 2.3H19a2 2 0 0 1 2 2v8.7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z"/>',
    pulse:'<path d="M3 12h4l2.5-6 4 12 2.5-6H21"/>',
    sliders:'<path d="M4 7h10M18 7h2M4 17h4M12 17h8"/><circle cx="16" cy="7" r="2.2"/><circle cx="10" cy="17" r="2.2"/>',
    search:'<circle cx="11" cy="11" r="6.5"/><path d="M16 16l4.5 4.5"/>',
    copy:'<rect x="8.5" y="8.5" width="11" height="11" rx="2.5"/><path d="M15.5 8.5V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v7.5a2 2 0 0 0 2 2h2.5"/>',
    play:'<path d="M8 5.5v13l10.5-6.5Z" fill="currentColor"/>',
    pauseF:'<rect x="6.5" y="5" width="4" height="14" rx="1.2" fill="currentColor" stroke="none"/><rect x="13.5" y="5" width="4" height="14" rx="1.2" fill="currentColor" stroke="none"/>',
    prev:'<path d="M6 5v14"/><path d="M18 6v12l-8.5-6Z" fill="currentColor"/>',
    next:'<path d="M18 5v14"/><path d="M6 6v12l8.5-6Z" fill="currentColor"/>',
    replay:'<path d="M3.5 12a8.5 8.5 0 1 0 2.5-6"/><path d="M3 4v4.5h4.5"/><path d="M12 8v4.5l3 1.8"/>',
    download:'<path d="M12 4v11M7.5 10.5 12 15l4.5-4.5"/><path d="M4.5 15.5v3a2 2 0 0 0 2 2h11a2 2 0 0 0 2-2v-3"/>',
    person:'<circle cx="12" cy="5.8" r="2.6"/><path d="M12 9.5v6M7.5 12.2 12 10l4.5 2.2M9.2 21l2.8-5.5 2.8 5.5"/>',
    arrowDown:'<path d="M12 4.5v15M6 13.5l6 6 6-6"/>',
    arrowUp:'<path d="M12 19.5v-15M6 10.5l6-6 6 6"/>',
    list:'<path d="M9 6.5h11M9 12h11M9 17.5h11"/><circle cx="4.5" cy="6.5" r="1.1" fill="currentColor"/><circle cx="4.5" cy="12" r="1.1" fill="currentColor"/><circle cx="4.5" cy="17.5" r="1.1" fill="currentColor"/>',
    terminal:'<rect x="3" y="4.5" width="18" height="15" rx="2.5"/><path d="M7 9.5l3 2.5-3 2.5M12.5 15h4.5"/>',
    gauge:'<path d="M4 17a8 8 0 1 1 16 0"/><path d="M12 17l4-5"/><circle cx="12" cy="17" r="1.4" fill="currentColor"/>',
    drive:'<rect x="3" y="13" width="18" height="7" rx="2"/><path d="M5 13l2.5-8h9L19 13"/><circle cx="17" cy="16.5" r="1" fill="currentColor"/>',
    trash:'<path d="M4.5 7h15M9.5 7V4.5h5V7M6.5 7l1 13h9l1-13"/>',
    qr:'<rect x="4" y="4" width="6" height="6" rx="1"/><rect x="14" y="4" width="6" height="6" rx="1"/><rect x="4" y="14" width="6" height="6" rx="1"/><path d="M14 14h2.5v2.5H14zM17.5 17.5H20V20h-2.5zM14 19.5h1.5M19.5 14v1.5"/>',
    cpu:'<rect x="6" y="6" width="12" height="12" rx="2"/><path d="M9.5 9.5h5v5h-5zM9 2.5V6M15 2.5V6M9 18v3.5M15 18v3.5M2.5 9H6M2.5 15H6M18 9h3.5M18 15h3.5"/>',
    layers:'<path d="M12 3.5 21 8.5l-9 5-9-5Z"/><path d="M3 12.5l9 5 9-5M3 16.5l9 5 9-5"/>',
    cube:'<path d="M12 3 20 7.5v9L12 21l-8-4.5v-9Z"/><path d="M4 7.5 12 12l8-4.5M12 12v9"/>',
    users:'<circle cx="9" cy="8" r="3.2"/><path d="M3 20a6 6 0 0 1 12 0"/><circle cx="17" cy="9" r="2.6"/><path d="M16 14.2A5 5 0 0 1 21.5 19"/>'
  };
  function ic(n, extra){ return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"'+(extra?' '+extra:'')+'>'+P[n]+'</svg>'; }
  const WG = {min:'<path d="M0 5.5h10"/>', max:'<rect x=".5" y=".5" width="9" height="9" rx="1.4"/>', close:'<path d="M.6.6l8.8 8.8M9.4.6.6 9.4"/>'};
  function wg(n){ return '<svg viewBox="0 0 10 10" fill="none" stroke="currentColor" stroke-width="1" aria-hidden="true">'+WG[n]+'</svg>'; }
  function esc(s){ return String(s==null?'':s).replace(/[&<>"]/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }
  /* ---------- help behind a «?» icon (core.js infoTip): a 24 px button (44 px to click) whose text shows in a
     card with role="tooltip". A click pins it; hovering with the mouse or keyboard focus shows it; Escape, a click
     outside or scrolling close it. k names the tip so it stays open across renders; up opens it upwards and
     end/start align it to an edge; it flips when it does not fit. ---------- */
  const ITIP = {open:null, pin:false, n:0, quiet:0, mute:null, on:false};
  function infoTip(text, label, o){ o = o||{}; const k = String(o.k||label), id = 'itip-'+k.replace(/[^a-z0-9]+/gi, '-')+'-'+(++ITIP.n), on = ITIP.open===k;
    return '<span class="itip'+(o.up?' up':'')+(o.end?' end':'')+(o.start?' start':'')+(o.cls?' '+o.cls:'')+(on?' open':'')+'" data-tip="'+esc(k)+'">'+
      '<button type="button" class="itip-b" aria-label="Más información: '+esc(label)+'" aria-expanded="'+on+'" aria-describedby="'+id+'">'+ic(o.icon||'help')+'</button>'+
      '<span class="itip-pop" role="tooltip" id="'+id+'">'+text+'</span></span>'; }

  /* ---------- marca Te Tengo: dos figuras abrazadas (core.js, kit de marca) ---------- */
  const BRAND={morado:'#4B2E83', coral:'#FF8F7E', durazno:'#FF8F7E', crema:'#FFF7F1'};
  /* Calcado del kit de marca (05-prototipos/marca/): cabeza y cuerpo de quien abraza (violeta) y de quien es abrazado (coral) */
  const MARK_VH=[47.7, 24.4, 17.6], MARK_CH=[80.9, 39.8, 15.4];
  const MARK_ARM='M20.4 35.9 C21.9 35.6 23.0 35.8 24.4 36.2 C25.8 36.6 25.5 35.8 28.6 38.2 C31.6 40.7 38.3 47.6 42.5 51.0 C46.7 54.3 50.3 56.5 53.8 58.2 C57.3 59.9 59.6 60.6 63.3 61.1 C67.0 61.6 73.8 61.1 75.9 61.1 C75.3 61.9 74.1 64.4 72.4 65.9 C70.7 67.4 68.1 69.0 65.5 70.2 C62.9 71.4 59.5 72.4 56.7 72.9 C54.0 73.4 51.4 73.5 49.0 73.3 C46.7 73.2 44.6 72.8 42.6 72.1 C40.5 71.4 38.5 70.5 36.7 69.2 C35.0 67.9 33.4 66.3 32.0 64.3 C30.6 62.3 29.1 58.4 28.2 57.0 C27.4 55.7 27.4 56.3 26.9 56.3 C26.5 56.2 26.2 56.1 25.7 56.6 C25.2 57.2 24.5 58.2 24.2 59.5 C23.8 60.9 23.4 62.0 23.7 64.5 C24.0 67.1 24.6 71.8 25.9 75.0 C27.2 78.2 29.3 81.2 31.6 83.8 C34.0 86.5 37.5 89.2 40.0 91.0 C42.5 92.8 44.1 93.5 46.5 94.5 C48.8 95.6 51.6 96.6 54.0 97.2 C56.5 97.9 58.3 98.4 61.0 98.7 C63.7 99.0 68.7 98.8 70.5 99.1 C72.3 99.3 71.7 99.9 72.0 100.0 C71.7 100.9 71.3 103.2 70.1 105.0 C68.9 106.9 66.5 109.5 64.8 111.2 C63.0 112.8 60.9 114.1 59.3 114.9 C57.7 115.6 57.2 115.8 55.1 115.5 C53.1 115.1 49.9 114.3 46.9 112.9 C43.8 111.6 39.7 109.4 36.7 107.5 C33.7 105.5 31.3 103.8 28.7 101.4 C26.1 99.0 23.2 95.9 20.9 93.1 C18.5 90.3 16.5 87.0 14.9 84.4 C13.3 81.8 12.5 80.1 11.4 77.5 C10.4 74.8 9.3 71.8 8.7 68.7 C8.0 65.6 7.5 61.9 7.5 58.9 C7.4 56.0 7.7 53.6 8.3 51.0 C8.9 48.4 9.8 45.2 11.0 43.1 C12.2 40.9 13.7 39.1 15.2 37.9 C16.8 36.7 18.8 36.1 20.4 35.9Z';
  const MARK_BODY='M96.0 52.7 C97.5 52.7 99.5 52.9 101.0 53.4 C102.5 53.8 103.6 54.4 104.9 55.4 C106.1 56.4 107.5 57.9 108.4 59.3 C109.3 60.7 109.9 62.2 110.3 63.7 C110.8 65.2 111.1 66.5 111.2 68.3 C111.3 70.2 111.2 72.9 110.9 74.8 C110.6 76.7 110.4 77.7 109.6 79.8 C108.8 81.9 107.7 84.8 106.1 87.6 C104.4 90.4 101.9 93.8 99.5 96.5 C97.1 99.2 94.6 101.5 91.9 103.7 C89.1 105.8 86.6 107.7 83.1 109.5 C79.6 111.4 73.1 113.9 70.9 114.7 C68.7 115.6 70.1 114.7 69.9 114.7 C69.9 114.6 69.1 115.0 70.0 114.0 C71.0 112.9 74.1 110.1 75.5 108.4 C77.0 106.7 77.9 105.4 78.8 103.7 C79.6 102.0 80.4 99.5 80.6 98.2 C80.9 96.9 80.5 96.4 80.1 95.7 C79.7 94.9 79.7 94.2 78.3 93.9 C76.9 93.6 75.2 93.8 71.9 93.7 C68.5 93.6 62.3 93.8 58.2 93.1 C54.1 92.4 50.5 91.1 47.2 89.4 C43.9 87.7 40.5 84.9 38.2 82.9 C36.0 81.0 34.8 79.0 33.9 77.6 C33.0 76.1 33.0 74.8 32.9 74.3 C33.1 74.2 32.8 73.6 34.2 74.1 C35.5 74.6 38.6 76.5 41.0 77.2 C43.4 78.0 46.1 78.5 48.7 78.7 C51.3 78.9 54.0 78.9 56.7 78.6 C59.5 78.2 62.6 77.4 65.0 76.6 C67.5 75.9 69.3 75.0 71.4 73.8 C73.4 72.7 74.5 72.7 77.2 69.7 C80.0 66.7 85.6 58.5 88.1 55.8 C90.6 53.1 90.8 54.0 92.1 53.5 C93.4 53.0 94.5 52.7 96.0 52.7Z';
  /* a = quien abraza (violeta o blanco), b = quien es abrazado (coral) */
  function symbolParts(a, b){ return '<circle class="mk-vh" cx="'+MARK_VH[0]+'" cy="'+MARK_VH[1]+'" r="'+MARK_VH[2]+'" fill="'+a+'"/><path class="mk-vb" d="'+MARK_ARM+'" fill="'+a+'"/><g class="mk-c"><circle cx="'+MARK_CH[0]+'" cy="'+MARK_CH[1]+'" r="'+MARK_CH[2]+'" fill="'+b+'"/><path d="'+MARK_BODY+'" fill="'+b+'"/></g>'; }
  function symbolSVG(dark, attrs){ return '<svg viewBox="0 0 122 122" aria-hidden="true"'+(attrs?' '+attrs:'')+'>'+symbolParts(dark?'#FFFFFF':BRAND.morado, BRAND.coral)+'</svg>'; }
  const LOGO = '<svg viewBox="0 0 122 122" aria-hidden="true"><rect width="122" height="122" rx="28" fill="'+BRAND.morado+'"/><g transform="translate(18 18) scale(.705)">'+symbolParts('#FFFFFF', BRAND.coral)+'</g></svg>';
  const WM_FONT='font-family="Poppins,system-ui,sans-serif" font-weight="700"';
  /* logotipo horizontal: símbolo + «Te Tengo» (+ «Captura» en el agente de escritorio) */
  function logotipo(dark, withCaptura, cls){
    const w = withCaptura ? 720 : 470;
    return '<svg class="logotipo'+(cls?' '+cls:'')+'" viewBox="0 0 '+w+' 122" role="img" aria-label="Te Tengo'+(withCaptura?' Captura':'')+'">'+
      symbolParts(dark?'#FFFFFF':BRAND.morado, BRAND.coral)+
      '<text x="138" y="84" '+WM_FONT+' font-size="66" letter-spacing="-1.5" fill="'+(dark?'#FFFFFF':BRAND.morado)+'">Te Tengo'+(withCaptura?'<tspan font-weight="500" fill="'+(dark?'rgba(255,255,255,.8)':'#5A4F70')+'"> Captura</tspan>':'')+'</text></svg>';
  }
  /* solo las letras, para el arranque */
  function wordmark(dark, withCaptura, cls){
    const w = withCaptura ? 584 : 320;
    return '<svg class="wordmark'+(cls?' '+cls:'')+'" viewBox="0 0 '+w+' 80" role="img" aria-label="Te Tengo'+(withCaptura?' Captura':'')+'">'+
      '<text x="2" y="62" '+WM_FONT+' font-size="66" letter-spacing="-1.5" fill="'+(dark?'#FFFFFF':BRAND.morado)+'">Te Tengo'+(withCaptura?'<tspan font-weight="500" fill="'+(dark?'rgba(255,255,255,.8)':'#5A4F70')+'"> Captura</tspan>':'')+'</text></svg>';
  }
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
    } else if(room==='Comedor'){
      s+='<rect x="40" y="26" width="70" height="56" rx="4" fill="'+win+'"/><path d="M75 26v56" stroke="#fff" stroke-width="3"/>';
      s+='<path d="M200 22v20" stroke="'+furn2+'" stroke-width="2"/><path d="M184 54h32l-6-12h-20Z" fill="'+wood+'"/>';
      s+='<rect x="128" y="98" width="144" height="10" rx="4" fill="'+wood+'"/><path d="M138 108v30M262 108v30" stroke="'+wood+'" stroke-width="4"/>';
      s+='<rect x="104" y="84" width="10" height="54" rx="3" fill="'+furn2+'"/><rect x="104" y="108" width="28" height="7" rx="2" fill="'+furn2+'"/>';
      s+='<rect x="286" y="84" width="10" height="54" rx="3" fill="'+furn2+'"/><rect x="268" y="108" width="28" height="7" rx="2" fill="'+furn2+'"/>';
      s+='<ellipse cx="200" cy="160" rx="100" ry="11" fill="'+f2+'"/>';
    } else {
      s+='<rect x="30" y="34" width="54" height="104" rx="3" fill="'+wood+'"/><circle cx="74" cy="90" r="3" fill="'+furn2+'"/>';
      s+='<rect x="236" y="34" width="54" height="104" rx="3" fill="'+wood+'"/><circle cx="246" cy="90" r="3" fill="'+furn2+'"/>';
      s+='<rect x="128" y="44" width="64" height="42" rx="3" fill="#fff" stroke="'+furn+'" stroke-width="3"/><path d="M136 78l14-16 10 10 8-6 16 12" stroke="'+furn2+'" stroke-width="2.5" fill="none" stroke-linejoin="round"/>';
      s+='<path d="M110 180l20-42h60l20 42Z" fill="'+f2+'"/>';
    }
    return s+'</svg>';
  }

  /* ---------- textos de la casa (core.js / proto.js) ---------- */
  const ROOM_ART = r => ({sala:'la Sala', dormitorio:'el Dormitorio', cocina:'la Cocina', comedor:'el Comedor', pasillo:'el Pasillo'})[String(r).trim().toLowerCase()] || '«'+r+'»';
  function pad2(n){ return String(n).padStart(2, '0'); }
  function mmss(s){ s = Math.max(0, s); return Math.floor(s/60) + ':' + pad2(s%60); }
  function listY(a){ return a.length < 2 ? a.join('') : a.slice(0, -1).join(', ') + ' y ' + a[a.length-1]; }

  /* ---------- ventana ---------- */
  function titlebar(){
    return '<div class="tb pywebview-drag-region"><div class="tb-app">'+appIcon('xs')+'<span>Te Tengo Captura</span></div><div class="tb-btns">'+
      '<button class="tb-btn" data-act="minimize" aria-label="Minimizar" title="Minimizar">'+wg('min')+'</button>'+
      '<button class="tb-btn" aria-disabled="true" tabindex="-1" aria-label="Maximizar (no disponible)" title="Maximizar">'+wg('max')+'</button>'+
      '<button class="tb-btn close" data-act="close" aria-label="Cerrar" title="Cerrar">'+wg('close')+'</button></div></div>';
  }
  function sec(cls, enter, inner){ return '<section class="scr'+(cls?' '+cls:'')+(enter?' '+enter:'')+'" aria-labelledby="scr-h">'+inner+'</section>'; }
  function det(U, k, cls, summary, body){
    return '<details class="inst'+(cls?' '+cls:'')+'" data-k="'+k+'"'+(U.open[k]?' open':'')+'><summary>'+summary+ic('chevDown')+'</summary>'+body+'</details>';
  }

  /* =================== Vincular esta PC (QR + código de 8 letras) =================== */
  function qrSVG(qr){
    const n = qr.n;
    return '<svg class="qr" viewBox="-2 -2 '+(n+4)+' '+(n+4)+'" role="img" aria-label="Código QR para vincular esta PC" shape-rendering="crispEdges"><rect x="-2" y="-2" width="'+(n+4)+'" height="'+(n+4)+'" fill="#fff"/>'+
      '<path d="'+esc(qr.d)+'" fill="#2B1D4E"/></svg>';
  }
  function pairCard(E){
    const p = E.pair;
    const off = (icon, t, s) => '<div class="card pair-card pair-off" role="status"><span class="ci lg aviso dash">'+ic(icon)+'</span><h2 class="t-h2">'+t+'</h2>'+
      '<p class="t-small">'+s+' Reintentamos en <span class="mono" id="retry" data-r="pr">'+mmss(p.retry)+'</span>.</p>'+
      '<button class="btn btn-secondary btn-sm" data-act="retryNow">'+ic('refresh')+'Reintentar ahora</button></div>';
    if(p.fase==='sin_internet') return off('wifiOff', 'Sin internet', 'Conecta esta PC a internet.');
    if(p.fase==='sin_servidor') return off('cloud', 'Te Tengo no responde', 'No tienes que hacer nada.');
    if(!p.code || !p.qr) return '<div class="card pair-card" role="status"><div class="pane-scan"><span class="spin"></span></div></div>';
    const spoken = p.code.replace('-', '').split('').join(' ').replace(/^(\S \S \S \S) /, '$1, guion, ');
    return '<div class="card pair-card'+(p.fresh?' fresh':'')+'">'+
      (p.renewed ? '<p class="renew">'+ic('refresh')+'Código nuevo · el anterior venció</p>' : '')+
      '<div class="qrwrap">'+qrSVG(p.qr)+'<span class="qr-logo" aria-hidden="true">'+LOGO+'</span></div>'+
      '<p class="t-meta">O escribe este código en la app:</p>'+
      '<p class="code-big"><span aria-hidden="true">'+esc(p.code)+'</span><span class="sr">'+esc(spoken)+'</span></p>'+
      '<p class="pair-url">'+esc(p.url)+'</p>'+
      '<p class="pair-left'+(p.left<=60?' low':'')+'" data-r="pl">'+ic('clock')+'Vence en <span class="mono" id="pair-left">'+mmss(p.left)+'</span></p>'+
      '<span class="sr" role="status" id="pair-ann">'+(p.renewed?'Código nuevo':'')+'</span></div>';
  }
  function scrVincular(E, U, enter){
    const p = E.pair, ok = p.fase==='codigo' || p.fase==='pidiendo';
    return sec('pair', enter,
      (p.re90 ? '<div class="notice warn band90" role="status">'+ic('clock')+'<div><b>Más de 90 días sin conexión</b><span>Vincúlala de nuevo.</span></div></div>' : '')+
      '<div class="pair-grid"><div class="pair-l">'+
        '<h1 class="t-title" id="scr-h" tabindex="-1">Vincula esta PC con tu celular</h1>'+
        '<ol class="steps2"><li><span class="n">1</span><span>Abre la app Te Tengo</span></li>'+
        '<li><span class="n">2</span><span class="path">Ajustes'+ic('chevR')+'PCs y cámaras'+ic('chevR')+'Agregar PC</span></li>'+
        '<li><span class="n">3</span><span>Escanea este código</span></li></ol>'+
        '<p class="pcname"><span class="ci">'+ic('monitor')+'</span><span>Esta PC: <b>'+esc(E.pcname)+'</b></span></p>'+
        det(U, 'help', 'phelp', ic('mobile')+'¿Error en el celular?',
          '<ul class="helplist"><li><b>«Este código ya venció o ya se usó»</b>Escanea el código nuevo.</li>'+
          '<li><b>«Demasiados intentos»</b>Espera la hora que indica el celular.</li></ul>')+
      '</div>'+pairCard(E)+'</div>'+
      '<div class="pair-foot">'+(ok ? '<p class="wait2" role="status"><span class="spin"></span>Esperando aprobación en el celular…</p>'
                                     : '<p class="wait2 stop"><span class="spin"></span>El código aparece con conexión</p>')+'</div>');
  }
  /* la PC informa las webcams que detectó; la familia las asigna desde la app */
  function foundList(E){
    const devs = E.devices;
    if(!devs.length) return '<div class="notice warn">'+ic('cam')+'<div><b>No encontramos cámaras</b><span>Conecta una webcam por USB.</span></div></div>';
    return '<div class="found"><p class="found-h">'+ic('usb')+'<b>Detectamos '+devs.length+(devs.length===1?' cámara':' cámaras')+'</b></p>'+
      '<ul class="found-l">'+devs.map(d => '<li><span class="thumb art'+(!d.connected?' dim':'')+'">'+roomSVG(d.room || '')+'</span><span class="grow"><b>'+esc(d.name)+'</b>'+devTag(d)+'</span></li>').join('')+'</ul></div>';
  }
  function scrVinculada(E, U, enter){
    const kept = E.cams.length;
    return sec('', enter, '<div class="result linked"><span class="ok-badge">'+ic('check')+'</span>'+
      '<h1 class="t-title" id="scr-h" tabindex="-1">Vinculada a la casa de '+esc(E.home.who)+'</h1>'+
      '<p class="t-lead">Aprobó '+esc(E.linkedBy || '')+' a las <span class="mono">'+esc(E.linkedAt)+'</span> · <b>'+esc(E.pc.nombre)+'</b></p>'+
      (kept ? '<div class="notice ok next">'+ic('check')+'<div><b>Las cámaras siguen en su habitación</b><span>'+esc(listY(E.cams.map(c => c.room)))+' · se cambian en la app</span></div></div>'
            : '<div class="notice info next">'+ic('mobile')+'<div><b>Ahora elige las cámaras en la app</b><span class="path">Ajustes'+ic('chevR')+'PCs y cámaras'+ic('chevR')+esc(E.pc.nombre)+'</span></div></div>')+
      foundList(E)+
      (!E.consent ? '<div class="notice warn">'+ic('doc')+'<div><b>Falta el consentimiento de '+esc(E.home.first)+'</b><span>Hasta registrarlo en la app, las cámaras no se usan.</span></div></div>' : '')+
      '<div class="actions"><button class="btn btn-primary btn-lg" data-act="toEstado">'+ic('pulse')+'Ir a Estado</button></div></div>');
  }
  function scrRechazada(E, U, enter){
    return sec('', enter, '<div class="result"><span class="ci lg pausa">'+ic('x')+'</span>'+
      '<h1 class="t-title" id="scr-h" tabindex="-1">No se vinculó esta PC</h1>'+
      '<p class="t-lead">Alguien eligió «No reconozco esta PC» en la app.</p>'+
      '<div class="actions"><button class="btn btn-primary btn-lg" data-act="otherCode">'+ic('qr')+'Mostrar otro código</button></div></div>');
  }
  function scrQuitada(E, U, enter){
    return sec('', enter, '<div class="result"><span class="ci lg pausa">'+ic('unlink')+'</span>'+
      '<h1 class="t-title" id="scr-h" tabindex="-1">'+(E.who ? 'Se quitó de la casa de '+esc(E.who) : 'Se quitó de la vivienda')+'</h1>'+
      '<p class="t-lead">La familia la quitó desde la app a las <span class="mono">'+esc(E.at)+'</span>.</p>'+
      '<div class="actions"><button class="btn btn-primary btn-lg" data-act="pairAgain">'+ic('link')+'Vincular de nuevo</button></div></div>');
  }

  /* ---------- barra de pestañas ---------- */
  function tabs(E){ return [['estado','pulse','Estado'], ['camaras','cam','Cámaras'], ['avanzado','sliders','Avanzado']]; }
  function tabbar(E, U){
    const t = x => '<button class="tab'+(U.tab===x[0]?' sel':'')+'" role="tab" id="tab-'+x[0]+'" aria-selected="'+(U.tab===x[0])+'" aria-controls="panel" tabindex="'+(U.tab===x[0]?0:-1)+'" data-act="tab" data-arg="'+x[0]+'">'+ic(x[1])+'<span>'+x[2]+'</span></button>';
    const u = E.upd, up = updAvail(E), ver = u ? u.ver : (E.version || '');
    const about = u ? '<button class="ab-open'+(up?' up':'')+'" id="sub-acerca" aria-pressed="'+(U.tab==='avanzado' && !(U.rp && U.rp.open) && U.adv.sub==='acerca')+'" data-act="toAbout" aria-label="Acerca de: versión '+esc(ver)+(up?', hay una versión nueva':'')+'" title="Acerca de · versión '+esc(ver)+'">'+ic('info')+'</button>' : '';
    return '<nav class="tabbar" aria-label="Te Tengo Captura"><div class="tabs" role="tablist" aria-label="Secciones">'+tabs(E).map(t).join('')+'</div>'+
      '<span class="tb-pc">'+ic('monitor')+'<span>Esta PC: <b>'+esc(E.pc.nombre)+'</b></span>'+about+'</span></nav>';
  }

  /* =================== Actualizaciones (US-43) ===================
     The band under the tabs (on every tab), «Avanzado › Acerca de» and the dialogs. Python
     (te_tengo_captura/actualizaciones/actualizador.py) decides; the copy is the prototype's. */
  const KEEP = 'Se mantienen la vinculación, las cámaras y los datos.';
  function updAvail(E){ const u = E.upd; return !!(u && (u.latest || u.minima)); }
  function updBtn(u, cls){ const ir = !u.download; return '<button class="btn btn-primary '+cls+'" data-act="updGo">'+ic(ir?'link':'download')+(ir?'Ir a la descarga':'Descargar')+'</button>'; }
  function updTitle(u){ return u.minima ? 'Actualiza Te Tengo para seguir recibiendo alertas' : 'Hay una versión nueva ('+esc(u.latest)+')'; }
  function updBand(E){
    const u = E.upd; if(!u || (!updAvail(E) && u.st!=='restart')) return '';
    const v = esc(u.latest || ''), ver = esc(u.ver);
    const B = (cls, icon, inner, btns) => '<div class="upband'+(cls?' '+cls:'')+'" role="status" id="upband"><span class="ub-i">'+icon+'</span>'+inner+(btns?'<div class="ub-btns">'+btns+'</div>':'')+'</div>';
    const notes = u.latest ? '<button class="btn btn-ghost btn-xs" data-act="updNotes">Qué cambió</button>' : '';
    const retry = '<button class="btn btn-secondary btn-xs" data-act="updGo">'+ic('refresh')+'Reintentar</button>';
    const kept = infoTip('Sigues con la versión '+ver+'. No se instaló nada.', 'versión actual', {k:'upd-kept', end:1});
    switch(u.st){
      case 'dl': return B('', ic('download'), '<div class="ub-p" data-r="ubp"><div class="grow"><b>Descargando la versión '+v+'…</b><div class="ub-bar" role="progressbar" aria-label="Descarga" aria-valuemin="0" aria-valuemax="100" aria-valuenow="'+u.pct+'"><i style="transform:scaleX('+(u.pct/100)+')"></i></div></div>'+
        '<span class="ub-n mono">'+u.pct+' %</span></div>'+(u.mb ? infoTip('La detección sigue mientras se descarga ('+u.mb+' MB).', 'descarga', {k:'upd-dl', end:1}) : ''), '<button class="btn btn-ghost btn-xs" data-act="updCancel">Cancelar</button>');
      case 'verify': return B('', '<span class="spin"></span>', '<div class="grow"><b>Verificando la descarga…</b></div>'+infoTip('Comprobamos que el archivo es el que publicó Te Tengo (suma SHA-256).', 'verificación', {k:'upd-sha', end:1}));
      case 'restart': return B('', '<span class="spin"></span>', '<div class="grow"><b>Reiniciando para actualizar…</b><span>'+KEEP+'</span></div>');
      case 'wait': return B('wait', ic('clock'), '<div class="grow"><b>Se actualizará cuando termine '+(u.why==='alerta' ? 'la alerta' : 'la vista en vivo')+'</b>'+(u.ready ? '<span>La versión '+v+' ya está descargada y verificada.</span>' : '')+'</div>', notes);
      case 'net': return B('warn', ic('wifiOff'), '<div class="grow"><b>Sin internet: no se puede descargar la versión '+v+'</b></div>'+kept, retry);
      case 'fail': return B('warn', ic('warn'), '<div class="grow"><b>No se pudo descargar la versión '+v+'</b></div>'+kept, retry);
      case 'bad': return B('warn', ic('warn'), '<div class="grow"><b>No se pudo verificar la descarga. No se instaló.</b></div>'+infoTip('Borramos el archivo y sigues con la versión '+ver+'. Inténtalo más tarde.', 'verificación', {k:'upd-bad', end:1}), retry);
      case 'disk': return B('warn', ic('drive'), '<div class="grow"><b>Falta espacio para la descarga</b>'+(u.free ? '<span>Libera '+u.free+' MB en el disco '+esc(u.drive)+'.</span>' : '')+'</div>', retry);
    }
    return B('', ic('download'), '<div class="grow"><b>'+updTitle(u)+'</b></div>', notes+updBtn(u, 'btn-xs'));
  }
  function aboutView(E, U){
    const u = E.upd; if(!u) return '';
    const up = updAvail(E), checking = u.checking || U.checking, busy = ['dl', 'verify', 'restart'].includes(u.st);
    let st;
    if(checking) st = '<p class="ab-st" role="status"><span class="spin"></span><b>Buscando actualizaciones…</b></p>';
    else if(up) st = '<p class="ab-st up" role="status"><span class="ci">'+ic('download')+'</span><b>'+updTitle(u)+'</b></p>';
    else st = '<p class="ab-st ok" role="status"><span class="ci calma">'+ic('check')+'</span><b>Tienes la última versión ('+esc(u.ver)+')</b></p>';
    const btns = '<div class="ab-btns">'+(up && !checking ? updBtn(u, 'btn-sm').replace('data-act="updGo"', 'data-act="updGo"'+(busy?' disabled':''))+(u.latest ? '<button class="btn btn-ghost btn-sm" data-act="updNotes">Qué cambió</button>' : '')
        : '<button class="btn btn-secondary btn-sm" data-act="updCheck"'+(checking||busy?' disabled':'')+'>'+ic('refresh')+'Buscar actualizaciones</button>')+'</div>';
    const auto = u.os==='mac'
      ? '<div class="card ab-card ab-mac"><span class="ci">'+ic('info')+'</span><div class="grow"><b>En Mac, por ahora se actualiza a mano</b><span>Es temporal, hasta que la app esté firmada por Apple.</span></div></div>'
      : u.os==='windows' ? '<div class="card ab-card"><span class="ci">'+ic('refresh')+'</span><div class="grow"><b id="upd-auto-l">Actualizar automáticamente</b><span>De madrugada, si no hay una alerta.</span></div>'+
          infoTip('Instala la versión nueva a las 03:00 si no hay una alerta ni una vista en vivo.', 'actualizar automáticamente', {k:'upd-auto', end:1, up:1})+sw(u.auto, 'updAuto', 'upd-auto-l')+'</div>' : '';
    const last = u.last ? u.last.replace(/ (\d\d:\d\d)$/, ' <span class="mono">$1</span>') : null;
    return '<div class="about"><div class="card ab-main"><span class="ab-icon">'+appIcon()+'</span><div class="grow"><h2 class="t-h2">Te Tengo Captura</h2><p class="t-meta">Versión <span class="mono">'+esc(u.ver)+'</span>'+(up ? ' · instalada' : '')+'</p>'+st+
        (last ? '<p class="t-meta ab-last"><span>Última búsqueda: '+last+'</span>'+infoTip('Busca sola al abrir el programa y una vez al día.', 'búsqueda de versiones', {k:'upd-when', start:1})+'</p>' : '')+'</div>'+btns+'</div>'+auto+'</div>';
  }
  function scrMain(E, U, enter){
    const tab = tabs(E).some(x => x[0]===U.tab) ? U.tab : 'estado';
    const replay = tab==='avanzado' && U.rp && U.rp.open;
    const panel = tab==='camaras' ? panelCamaras(E, U) : tab==='avanzado' ? (replay ? panelReplay(E, U) : panelAvanzado(E, U)) : panelEstado(E, U);
    return sec('main', enter, tabbar(E, Object.assign({}, U, {tab:tab}))+updBand(E)+'<div class="panel '+tab+(replay?' replay':'')+'" id="panel" role="tabpanel" aria-labelledby="tab-'+tab+'">'+panel+'</div>');
  }

  /* ---------- Estado: el resumen y una fila por cámara ---------- */
  function health(E){
    const h = E.health, a = h.accion;
    const btn = a ? '<button class="btn btn-secondary btn-sm" data-act="'+a.act+'">'+ic(a.icono)+esc(a.texto)+'</button>' : '';
    const tip = h.ayuda ? infoTip(esc(h.ayuda.texto), h.ayuda.tema, {k:h.ayuda.clave, end:1}) : '';
    return '<div class="health '+h.clase+'" role="status"><span class="st '+h.k+'">'+ic(h.icono)+'</span><div class="grow"><b>'+h.titulo_html+'</b><span data-r="hd">'+h.detalle_html+'</span></div>'+tip+btn+'</div>';
  }
  function camRow(c){
    const st = c.st;
    return '<li class="crow'+(st.k==='off'?' lost':'')+'"><span class="thumb art'+(st.k!=='send'&&st.k!=='live'?' dim':'')+'">'+roomSVG(c.room)+'</span>'+
      '<span class="crow-id"><b>'+esc(c.room)+'</b><span>'+ic('usb')+esc(c.device)+'</span></span>'+
      '<span class="cam-st"><span class="st '+st.k+'">'+ic(st.icono)+'</span><span class="grow"><b class="stx '+st.k+'">'+esc(st.titulo)+'</b>'+(st.detalle_html ? '<span class="t-meta">'+st.detalle_html+'</span>' : '')+'</span></span></li>';
  }
  function instData(E){
    const pc = E.pc;
    const origen = pc.vinculada_por
      ? '<div><dt>Vinculada</dt><dd>Por '+esc(pc.vinculada_por)+' el '+esc(pc.vinculada_el)+'</dd></div>'
      : '<div><dt>Instalación</dt><dd>'+esc(pc.instalada_el || '')+'</dd></div>';
    return '<dl class="conf-kv"><div><dt>Esta PC</dt><dd>'+esc(pc.nombre)+'</dd></div><div><dt>Sistema</dt><dd>'+esc(pc.sistema)+'</dd></div>'+
      origen+'<div><dt>Programa</dt><dd>'+esc(pc.programa)+'</dd></div></dl>';
  }
  /* the app asks for the preview of a webcam to choose its room: shown on the PC, as the live view */
  function peekNotice(E, here){
    const d = (E.devices || []).find(x => x.peek);
    if(!d) return '';
    return '<div class="notice info peek-n" role="status"><span class="led" aria-hidden="true"></span><div><b>'+(here ? 'Un familiar mira esta cámara para elegirla' : 'Un familiar mira la '+esc(d.name)+' para elegirla')+'</b></div>'+infoTip('No se graba. Queda en el registro de accesos que ve la familia en la app.','privacidad',{k:'peek',end:1})+'</div>';
  }
  function panelEstado(E, U){
    const list = E.cams.length ? '<ul class="crows" aria-label="Cámaras de esta PC">'+E.cams.map(camRow).join('')+'</ul>' : '';
    return '<header class="cam-head"><div><h1 class="t-title" id="scr-h" tabindex="-1">Vivienda de '+esc(E.home.who)+'</h1>'+(E.home.addr ? '<p class="t-meta mt4">'+ic('home')+esc(E.home.addr)+'</p>' : '')+'</div></header>'+
      health(E)+peekNotice(E)+list+
      '<div class="card instcard">'+det(U, 'inst', '', ic('lock')+'Datos de la instalación', instData(E))+'</div>'+
      '<p class="scr-foot">'+ic('mobile')+'<span class="ft">Cámaras, pausas, consentimiento y alertas: en la app</span><span class="sep"></span>'+ic('power')+'<span>Se inicia con Windows</span></p>';
  }

  /* ---------- Cámaras: las webcams de esta PC y su vista previa local ---------- */
  function devTag(d){
    if(!d.connected) return '<span class="ctag off">'+ic('videoOff')+'Desconectada'+(d.room?' · '+esc(d.room):'')+'</span>';
    if(d.busy) return '<span class="ctag busy">'+ic('warn')+'La usa otro programa</span>';
    if(d.room) return '<span class="ctag use">'+ic('check')+'En uso · '+esc(d.room)+'</span>';
    if(d.new) return '<span class="ctag new">'+ic('plus')+'Nueva · Sin usar</span>';
    return '<span class="ctag">Sin usar</span>';
  }
  function thisPc(E){
    if(!E.unlink) return '';
    return '<div class="thispc"><span class="ci">'+ic('monitor')+'</span><span class="grow"><b>Esta PC: '+esc(E.pc.nombre)+'</b><span>Vinculada por '+esc(E.pc.vinculada_por || '')+' el '+esc(E.pc.vinculada_el || '')+'</span></span>'+
      '<button class="btn btn-danger-ghost btn-xs" data-act="unlinkAsk">'+ic('unlink')+'Desvincular</button></div>';
  }
  function selDev(E, U){ return E.devices.find(d => d.id===U.sel) || E.devices[0] || null; }
  function camInfo(E, U, d){
    if(!d.connected) return '<div class="cpane"><div class="pane-empty" role="status">'+ic('videoOff')+'<h2 class="t-h2">No responde: revisa el cable USB</h2>'+
      '<p class="t-small">'+(d.room ? esc(d.room)+' sigue asignada a esta cámara. ' : '')+'Conéctala y pulsa Buscar de nuevo.</p><button class="btn btn-secondary" data-act="rescan">'+ic('refresh')+'Buscar de nuevo</button></div></div>';
    if(d.busy) return '<div class="cpane"><div class="pane-empty" role="status">'+ic('warn')+'<h2 class="t-h2">Otro programa usa esta cámara</h2>'+
      '<p class="t-small">Ciérralo y pulsa Buscar de nuevo.</p><button class="btn btn-secondary" data-act="rescan">'+ic('refresh')+'Buscar de nuevo</button></div></div>';
    const by = d.room ? (d.by==='pc' ? 'Elegida en esta PC' : d.by==='app' ? 'La eligió la familia en la app' : 'El nombre se cambia en la app Te Tengo') : 'Se elige en la app';
    return '<div class="cpane info"><figure class="pv2 art" id="pv" data-clave="'+esc(d.id)+'">'+roomSVG(d.room || '')+'<img class="pv-img" id="pv-img" alt="" hidden>'+
      '<figcaption class="pv-tag">'+ic('eye')+'Vista previa · '+esc(d.name)+'</figcaption>'+PV_TIP()+'</figure>'+
      (d.peek ? peekNotice(E, true) : '')+
      '<dl class="cinfo"><div><dt>Habitación</dt><dd><b>'+(d.room ? esc(d.room) : 'Sin usar')+'</b><span>'+by+'</span></dd></div>'+
      '<div><dt>Conexión</dt><dd><b class="ok">'+ic('check')+'Conectada</b><span>'+(d.new ? 'Nueva · por USB' : 'Por USB')+'</span></dd></div></dl>'+
      (E.unlink ? '<div class="pane-actions start"><button class="btn btn-ghost btn-sm" data-act="hereOn">'+ic('cam')+'Elegir aquí (si estás instalando)</button></div>' : '')+'</div>';
  }
  /* the lock over a local preview opens its help (core.js: 'pvlock' and 'skel-lock') */
  function PV_TIP(){ return infoTip('La vista previa solo se ve en esta PC: no se graba ni sale de la casa. Úsala para revisar el encuadre.','vista previa local',{k:'pvlock',icon:'lock',cls:'pv-lock',up:1,start:1}); }
  /* «Elegir aquí, si estás instalando» (CA-29.8): the same rules as the app */
  const ROOMS = ['Sala', 'Dormitorio', 'Cocina', 'Comedor', 'Pasillo'];
  function norm(s){ return String(s).toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').trim(); }
  function camPane(E, U, d){
    if(!d.connected || d.busy) return camInfo(E, U, d);
    const pk = U.pick, r = d.room;
    const amb = U.rooms || [];
    const nombres = ROOMS.slice(); amb.forEach(a => { if(!nombres.some(n => norm(n)===norm(a.nombre))) nombres.push(a.nombre); });
    const ocupada = n => { const a = amb.find(x => norm(x.nombre)===norm(n)); if(!a || !a.camaras.length) return null; if(r && norm(n)===norm(r)) return null; return a.camaras[0]; };
    const custom = r && !nombres.slice(0, 5).some(n => norm(n)===norm(r)) && !amb.some(a => norm(a.nombre)===norm(r));
    const otherOn = pk.otherOn;
    const room = otherOn ? pk.other : (pk.room!=null ? pk.room : r);
    const chips = nombres.map(x => {
      const o = ocupada(x);
      if(o) return '<button class="chip2" aria-disabled="true" title="'+(o.estaPc?'Ya tiene cámara en esta PC':'Ya tiene cámara en la PC '+esc(o.pc||''))+'"><span>'+esc(x)+'</span><small>Ya tiene cámara'+(!o.estaPc && o.pc?' · '+esc(o.pc):'')+'</small></button>';
      const on = !otherOn && room!=null && norm(room)===norm(x);
      return '<button class="chip2'+(on?' sel':'')+'" aria-pressed="'+on+'" data-act="pickRoom" data-arg="'+esc(x)+'">'+(on?ic('check'):'')+esc(x)+'</button>';
    }).join('') + '<button class="chip2'+(otherOn?' sel':'')+'" aria-pressed="'+otherOn+'" data-act="pickOther">'+(otherOn?ic('check'):'')+'Otra…</button>';
    const errs = {empty:'Escribe el nombre de la habitación.', bath:'Por privacidad, no se admiten cámaras en el baño.',
      dup:esc(pk.errRoom||'')+' ya tiene cámara (PC '+esc(pk.errPc||'')+'). Una cámara por habitación.',
      net:'Aún sin internet.'};
    const err = pk.err ? errs[pk.err] : '';
    const changed = r ? (room && norm(room)!==norm(r)) : (otherOn || !!room);
    const primary = '<button class="btn btn-primary" data-act="useCam"'+(changed && !U.busy?'':' disabled')+'>'+ic('check')+(r?'Guardar cambio':'Usar esta cámara')+'</button>';
    return '<div class="cpane"><figure class="pv2 art" id="pv" data-clave="'+esc(d.id)+'">'+roomSVG(d.room || '')+'<img class="pv-img" id="pv-img" alt="" hidden>'+
      '<figcaption class="pv-tag">'+ic('eye')+'Vista previa · '+esc(d.name)+'</figcaption>'+PV_TIP()+'</figure>'+
      '<span class="rooms-l"><span id="rooms-l">¿En qué habitación está?</span>'+infoTip('Por privacidad, no se admiten cámaras en el baño.','habitaciones',{k:'bath',start:1})+'</span><div class="chips2" role="group" aria-labelledby="rooms-l">'+chips+'</div>'+
      (otherOn ? '<div class="other-row field'+(err?' err':'')+'"><label class="sr" for="room-other">Nombre de la habitación</label><input class="input" id="room-other" value="'+esc(pk.other || (custom ? r : ''))+'" placeholder="Por ejemplo, Sala comedor" autocomplete="off"'+(err?' aria-invalid="true" aria-describedby="room-err"':'')+'></div>' : '')+
      (err ? '<p class="field-msg err-msg" id="room-err" role="alert">'+ic('warn')+'<span>'+err+'</span></p>' : '')+
      '<div class="pane-actions">'+(r ? '<button class="btn btn-danger-ghost btn-sm" data-act="unuse">Dejar de usar</button>' : '')+primary+'</div></div>';
  }
  function panelCamaras(E, U){
    const devs = E.devices, any = E.cams.length, here = U.here && E.unlink && devs.length;
    const meta = here ? 'Elige la habitación de cada cámara. La familia lo verá en la app.'
      : !devs.length || any ? 'Las habitaciones se eligen en la app.'
      : 'Detectamos '+devs.length+(devs.length===1?' cámara':' cámaras')+'. Elígelas en la app.';
    const head = '<header class="p-head"><div><h1 class="t-title" id="scr-h" tabindex="-1">'+(here?'Elegir aquí, si estás instalando':'Cámaras de esta PC')+'</h1><p class="t-meta">'+meta+'</p></div>'+
      (here ? '<button class="btn btn-secondary btn-sm" data-act="hereOff">'+ic('back')+'Volver</button>' : '')+'</header>';
    if(!devs.length) return head+'<div class="card empty-big" role="status"><span class="ci lg">'+ic('cam')+'</span><h2 class="t-h2">No encontramos cámaras</h2>'+
      '<p class="t-small">Conecta una webcam por USB.</p><button class="btn btn-secondary" data-act="rescan">'+ic('refresh')+'Buscar de nuevo</button></div>'+thisPc(E);
    const sel = selDev(E, U);
    const peekRow = d => !here && d.peek ? '<span class="peek"><span class="led" aria-hidden="true"></span><span>Un familiar la mira para elegirla</span></span>' : '';
    const rows = devs.map(d => '<button class="cpick'+(!d.connected?' lost':'')+(!here && d.peek?' peeking':'')+'" role="radio" aria-checked="'+(d===sel)+'" tabindex="'+(d===sel?0:-1)+'" data-act="selCam" data-arg="'+esc(d.id)+'">'+
      '<span class="thumb art'+(!d.connected||d.busy?' dim':'')+'">'+roomSVG(d.room || '')+'</span><span class="grow"><b>'+esc(d.name)+'</b>'+devTag(d)+'</span>'+peekRow(d)+'</button>').join('');
    const many = E.cams.length >= 3 ? infoTip('Si la detección va lenta, pasa alguna cámara a otra PC.','rendimiento',{k:'many',start:1}) : '';
    return head+'<div class="camgrid"><div class="clist"><p class="grp-l tip-l"><span id="g-cams">Cámaras conectadas</span>'+many+'</p><div class="clist-rows" role="radiogroup" aria-labelledby="g-cams">'+rows+'</div>'+
      '<div class="clist-tools"><button class="btn btn-ghost btn-sm" data-act="rescan">'+ic('refresh')+'Buscar de nuevo</button></div>'+thisPc(E)+'</div>'+(here ? camPane(E, U, sel) : camInfo(E, U, sel))+'</div>';
  }


  /* =================== Avanzado: registro en vivo, medidores y actividad =================== */
  function num(n, d){ return Number(n).toFixed(d).replace('.', ','); }
  function sw(on, act, lb, dis, compact){
    if(compact) return '<button class="switch" role="switch" aria-checked="'+(!!on && !dis)+'"'+(lb?' aria-labelledby="'+lb+'"':'')+(dis?' aria-disabled="true"':'')+' data-act="'+act+'"><i></i></button>';
    return '<span class="sw-l'+(on&&!dis?' on':'')+'"><button class="switch" role="switch" aria-checked="'+(!!on && !dis)+'"'+(lb?' aria-labelledby="'+lb+'"':'')+(dis?' aria-disabled="true"':'')+' data-act="'+act+'"><i></i></button>'+(on&&!dis?'Sí':'No')+'</span>';
  }
  const LOG_K = [['persona','person','Personas'], ['evento','warn','Eventos'], ['descarte','eyeOff','Descartadas'], ['conexion','wifi','Conexión'], ['programa','monitor','Programa']];
  function advCams(E){ return E.cams.map(c => ({id:c.id, room:c.room})); }
  function advCam(E, U){ const cs = advCams(E); return cs.find(c => c.id===U.adv.cam) || cs[0] || null; }
  function logLine(U, l){
    const open = U.log.open===l.id;
    return '<div class="lline '+(l.tone||'')+'"><time>'+esc(l.t)+'</time><span class="li">'+ic(l.i)+'</span><span class="msg">'+esc(l.m)+'</span>'+
      '<button class="tech-btn" aria-expanded="'+open+'" aria-controls="tx-'+l.id+'" data-act="techToggle" data-arg="'+l.id+'" aria-label="Ver línea técnica">Técnica'+ic('chevDown')+'</button></div>'+
      (open ? '<div class="ltech" id="tx-'+l.id+'"><span class="code">'+esc(l.x)+'</span><button class="btn btn-ghost btn-xs" data-act="copyTech" data-arg="'+l.id+'">'+ic('copy')+'Copiar</button></div>' : '');
  }
  function logRows(E, U, cam){
    const lg = U.log, all = lg.lines[cam.id] || [];
    const shown = lg.paused ? all.slice(0, lg.cut) : all;
    const q = norm(lg.q);
    const vis = shown.filter(l => lg.filters[l.k] && (!q || norm(l.m).includes(q)));
    const fila = E.cams.find(c => c.id===cam.id);
    const pin = fila && fila.pause ? '<div class="lline pin"><time></time><span class="li">'+ic('pause')+'</span><span class="msg">Cámara en pausa hasta las <span class="mono">'+esc(fila.pause)+'</span></span><span></span></div>' : '';
    const lost = fila && fila.st.k==='off' ? '<div class="lline aviso pin"><time></time><span class="li">'+ic('videoOff')+'</span><span class="msg">Cámara desconectada: revisa el cable USB</span><span></span></div>' : '';
    let body;
    if(!all.length) body = '<div class="logempty">'+ic('terminal')+'<b>Aún no pasa nada en esta cámara</b></div>';
    else if(!vis.length && q) body = '<div class="logempty">'+ic('search')+'<b>No hay líneas con «'+esc(lg.q)+'»</b></div>';
    else if(!vis.length) body = '<div class="logempty">'+ic('list')+'<b>No hay líneas de ese tipo</b></div>';
    else body = vis.map(l => logLine(U, l)).join('');
    return pin + lost + body;
  }
  function logView(E, U, cam){
    const lg = U.log, all = lg.lines[cam.id] || [], nNew = lg.paused ? all.length - lg.cut : 0;
    const cnt = {}; LOG_K.forEach(k => cnt[k[0]] = 0); (lg.paused ? all.slice(0, lg.cut) : all).forEach(l => { if(cnt[l.k]!=null) cnt[l.k]++; });
    return '<div class="logbar" role="toolbar" aria-label="Filtros del registro">'+LOG_K.map(k => '<button class="fchip" aria-pressed="'+lg.filters[k[0]]+'" data-act="logFilter" data-arg="'+k[0]+'">'+ic(k[1])+'<span class="lbl">'+k[2]+'</span><span class="cnt" id="cnt-'+k[0]+'">'+cnt[k[0]]+'</span></button>').join('')+
      '<label class="logsearch"><span class="sr">Buscar en el registro</span>'+ic('search')+'<input class="input" id="log-q" type="search" placeholder="Buscar" value="'+esc(lg.q)+'" autocomplete="off"></label>'+
      '<button class="btn btn-secondary btn-xs" data-act="logPause" aria-pressed="'+lg.paused+'">'+ic(lg.paused?'play':'pause')+(lg.paused?'Seguir':'Pausar')+'</button></div>'+
      (lg.paused ? '<div class="logband" id="log-band" role="status">'+ic('pause')+'<span class="grow">En pausa · <span id="log-new">'+nNew+' '+(nNew===1?'línea nueva':'líneas nuevas')+'</span></span><button class="btn btn-ghost btn-xs" data-act="logPause">'+ic('play')+'Seguir</button></div>' : '')+
      '<div class="logbox" id="logbox" role="log" aria-label="Registro en vivo de '+esc(cam.room)+'" aria-live="off" tabindex="0">'+logRows(E, U, cam)+'</div>'+
      '<span class="sr" role="status" id="log-ann"></span>';
  }
  const PHASES = [['De pie',''], ['Posible caída','inestable'], ['En el suelo','caida'], ['Caída confirmada','caida']];
  const SEG = [['h','sL'],['h','sR'],['sL','eL'],['eL','wL'],['sR','eR'],['eR','wR'],['sL','hL'],['sR','hR'],['hL','hR'],['hL','kL'],['kL','aL'],['hR','kR'],['kR','aR']];
  function skelReal(esq){
    const ks = Object.keys(esq||{}); if(!ks.length) return '';
    const xs = ks.map(k => esq[k][0]*4/3), ys = ks.map(k => esq[k][1]);
    const x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys);
    const esc_ = Math.min(200/Math.max(.05, x1-x0), 120/Math.max(.05, y1-y0));
    const P = k => [(120 + (esq[k][0]*4/3 - (x0+x1)/2)*esc_).toFixed(1), (132 - (y1 - esq[k][1])*esc_).toFixed(1)];
    let s = '<g class="skel">';
    SEG.forEach(([a,b]) => { if(esq[a] && esq[b]){ const A = P(a), B = P(b); s += '<line x1="'+A[0]+'" y1="'+A[1]+'" x2="'+B[0]+'" y2="'+B[1]+'" stroke="#2B1D4E" stroke-width="3" stroke-linecap="round"/>'; } });
    ks.forEach(k => { const a = P(k); s += '<circle cx="'+a[0]+'" cy="'+a[1]+'" r="'+(k==='h'?7.5:3.2)+'" fill="#fff" stroke="#2B1D4E" stroke-width="'+(k==='h'?2.8:1.9)+'"/>'; });
    return '<svg viewBox="0 0 240 150" preserveAspectRatio="xMidYMax meet" aria-hidden="true"><path d="M0 134H240" stroke="#D9D1E0" stroke-width="2"/>'+s+'</g></svg>';
  }
  function meterReason(E, M){
    if(!M) return {t:'Sin persona en la imagen', s:'Vuelven cuando la cámara vea a alguien.', i:'person', c:'pausa'};
    if(M.motivo==='desconectada') return {t:'Cámara desconectada', s:'Revisa el cable USB.', i:'videoOff', c:'aviso dash'};
    if(M.motivo==='pausa') return {t:'En pausa hasta las '+M.pausa, s:'La pausaron desde la app.', i:'pause', c:'pausa'};
    if(M.motivo==='consentimiento') return {t:'Cámara detenida', s:'Falta el consentimiento de '+E.home.first+'.', i:'doc', c:'aviso'};
    if(M.motivo==='sin_persona') return {t:'Sin persona en la imagen', s:'Vuelven cuando la cámara vea a alguien.', i:'person', c:'pausa'};
    return null;
  }
  function metersInner(E, M){
    const off = meterReason(E, M), D = v => off ? '—' : v, m = M || {};
    const meas = (title, val, unit, thr, si, pct, tp) => '<div class="mcard"><h3>'+title+'</h3><div class="mrow"><span class="mval">'+D(val)+(off?'':'<small>'+unit+'</small>')+'</span>'+
      (off ? '' : '<span class="yn'+(si?' si':'')+'">'+(si?ic('check')+'Sí':'No')+'</span>')+'</div>'+
      '<div class="mthr'+(si&&!off?' si':'')+'"><i style="width:'+(off?0:Math.max(0, Math.min(100, pct)))+'%"></i><b style="left:'+tp+'%"></b></div><p class="msub">'+thr+'</p></div>';
    const ph = off ? -1 : m.fase;
    const row1 = off
      ? '<div class="mcard mnote" role="status"><span class="ci '+off.c+'">'+ic(off.i)+'</span><div><b>'+esc(off.t)+'</b><span>'+esc(off.s)+'</span></div></div>'
      : '<div class="mcard"><h3>'+ic('gauge')+'Rendimiento</h3><span class="mval">'+num(m.fps, 1)+'<small>fps</small></span><p class="msub">Objetivo: 8 fps</p>'+
          '<div class="mkv"><div><span>Uso del procesador</span><b>'+Math.round(m.cpu||0)+' %</b></div><div><span>Demora del análisis</span><b>'+num(m.demora||0, 2)+' s</b></div></div></div>'+
        '<div class="mcard"><h3>'+ic('person')+'Persona</h3><p class="mperson"><span class="ci calma">'+ic('check')+'</span>Sí, una persona</p></div>'+
        '<div class="mcard"><h3>'+ic('clock')+'Temporizadores</h3>'+
          '<p class="timer">Ventana de caída <b>'+num(m.ventana, 2)+' s</b></p><div class="tbar"><i style="transform:scaleX('+(m.ventana/m.ventanaTotal).toFixed(3)+')"></i></div>'+
          '<p class="timer mt8">En el suelo <b>'+Math.round(m.suelo)+' de '+Math.round(m.confirmacion)+' s</b></p><div class="tbar"><i style="transform:scaleX('+Math.min(1, m.suelo/m.confirmacion).toFixed(3)+')"></i></div></div>';
    const vis = m.visibilidad || {Nariz:0, Hombros:0, Caderas:0, Tobillos:0};
    const bars = ['Nariz','Hombros','Caderas','Tobillos'].map(k => { const v = vis[k]||0, low = v < (m.umbralVisibilidad||.5);
      return '<div class="pbar'+(low&&!off?' low':'')+'"><span>'+k+'</span><span class="ptrack"><i style="width:'+(off?0:v*100)+'%"></i></span><b>'+(off?'—':(low?ic('warn'):'')+num(v, 2))+'</b></div>'; }).join('');
    const v = m.m1==null ? 0 : m.m1, th = m.m2==null ? 90 : m.m2, P = m.m3==null ? 0 : m.m3;
    const uv = m.umbralV || .01, ua = m.umbralAngulo || 45, ur = m.umbralRazon || 1;
    return row1+
      meas('Descenso de la cadera (M1)', m.m1==null ? '—' : num(v, 3), 'cuerpos/s', 'Avisa desde '+num(uv, 2).replace(/0+$/, '').replace(/,$/, ''), v >= uv, v/(uv*2)*100, 50)+
      meas('Inclinación del tronco (M2)', m.m2==null ? '—' : Math.round(th)+'°', '', 'Avisa por debajo de '+Math.round(ua)+'°', th < ua || !!m.cabezaBajoPies, (90-th)/90*100, 50)+
      meas('Forma del cuerpo, ancho/alto (M3)', m.m3==null ? '—' : num(P, 2), '', 'Avisa desde '+num(ur, 0), P >= ur || !!m.cabezaBajoPies, P/(ur*2)*100, 50)+
      '<div class="mcard mphase"><h3>'+ic('pulse')+'Fase'+infoTip('Avisa si sigue en el suelo tras 1,48 s; confirma a los 30 s.','fases',{k:'fase',start:1})+'</h3><div class="phs">'+PHASES.map((p, i) => (i?ic('chevR'):'')+'<span class="ph'+(i===ph?' cur '+p[1]:'')+'"'+(i===ph?' aria-current="step"':'')+'>'+(i===ph?ic('check'):'')+p[0]+'</span>').join('')+'</div>'+
        '</div>'+
      '<div class="mside"><div class="mcard"><h3>'+ic('person')+'Puntos del cuerpo'+infoTip('Visibilidad de 0 a 1. Por debajo de 0,5 el punto no cuenta.','visibilidad',{k:'plow',end:1})+'</h3><div class="pbars">'+bars+'</div></div>'+
        '<div class="mcard" style="flex:1;display:flex;flex-direction:column"><h3>'+ic('eye')+'Esqueleto</h3><div class="mskel">'+
          (off ? '' : skelReal(m.esqueleto))+infoTip('El esqueleto solo se ve en esta PC: no se graba ni sale de la casa.','vista local',{k:'skel-lock',icon:'lock',cls:'pv-lock',start:1})+'</div></div></div>';
  }
  function metersView(E, U, cam){ const M = U.meters[cam.id]; return '<div class="mgrid'+(meterReason(E, M)?' off':'')+'" id="meters" aria-label="Medidores de '+esc(cam.room)+'">'+metersInner(E, M)+'</div>'; }
  function actView(E, U){
    const rows = (U.acts || []);
    const days = [...new Set(rows.map(a => a.d))];
    const seg = '<div class="seg2 sm" role="radiogroup" aria-label="Qué actividad ver"><button role="radio" aria-checked="'+(U.actScope==='pc')+'" data-act="actScope" data-arg="pc">'+ic('monitor')+'Esta PC</button><button role="radio" aria-checked="'+(U.actScope==='casa')+'" data-act="actScope" data-arg="casa">'+ic('home')+'Toda la casa</button></div>';
    const av = w => w==='pc' ? '<span class="av pc">'+ic('monitor')+'</span>' : w==='app' ? '<span class="av pc">'+ic('mobile')+'</span>' : '<span class="av">'+esc(w)+'</span>';
    const body = rows.length ? days.map(d => '<h3 class="actday">'+esc(d)+'</h3>'+rows.filter(a => a.d===d).map(a =>
        '<div class="arow">'+av(a.who)+'<span>'+esc(a.m)+'</span><span class="when">'+(a.pend?'<span class="ptag">'+ic('clock')+'Pendiente de enviar</span>':'')+'<span class="mono">'+esc(a.t)+'</span></span></div>').join('')).join('')
      : '<div class="actempty">'+ic('list')+'<b>Aún no hay actividad</b><span class="t-meta">Aquí verás quién cambió qué y cuándo.</span></div>';
    return '<div class="advhead">'+seg+infoTip('Nadie puede editar ni borrar esta lista.','registro de actividad',{k:'act',start:1})+'</div><div class="actlist" id="actlist">'+body+'</div>';
  }

  /* ---------- almacenamiento en esta PC (US-38) ---------- */
  const RET = {mov:[7, 30, 90, 365, null], vid:[1, 7, 30, null], clip:[30, 90, 365, null], cap:[10, 25, 50, 100, 'otro']};
  function dias(v){ return v==null ? 'Nunca borrar' : v===365 ? '1 año' : v===1 ? '1 día' : v+' días'; }
  function gb(b){ return num((b||0)/1e9, 1); }
  function retPills(st, key, campo, cur, dis, label){
    return '<div class="ret'+(key==='cap'?' capret':'')+'" role="radiogroup" aria-label="'+label+'">'+RET[key].map(o => {
      const on = key==='cap' ? (o==='otro' ? ![10,25,50,100].includes(cur) : o===cur) : o===cur;
      const txt = key==='cap' ? (o==='otro' ? 'Otro' : o+' GB') : dias(o);
      return '<button role="radio" aria-checked="'+on+'"'+(dis?' aria-disabled="true"':'')+' data-act="ret" data-arg="'+campo+'|'+(o==null?'null':o)+'">'+txt+'</button>'; }).join('')+'</div>';
  }
  function storageView(E, U){
    const st = E.store; if(!st) return '';
    const a = st.ajustes, u = st.uso, cap = st.limite || 1, used = u.movimientos + u.video + u.clips, pct = v => (v/cap*100).toFixed(2);
    let band = '';
    if(st.estado==='lleno') band = '<div class="notice warn stband" role="alert">'+ic('folder')+'<div><b>No podemos guardar en la carpeta</b><span>Revisa el espacio del disco. Detección y avisos siguen.</span></div><button class="btn btn-secondary btn-sm" data-act="folderChange">Elegir otra carpeta</button></div>';
    else if(st.estado==='cerca') band = '<div class="notice warn stband" role="status">'+ic('drive')+'<div><b>Queda poco espacio: '+gb(used)+' GB de '+gb(cap)+' GB</b><span>Pronto borraremos el video más antiguo.</span></div></div>';
    else if(st.estado==='limite') band = '<div class="notice info stband" role="status">'+ic('trash')+'<div><b>Borramos el video del '+esc(st.liberado)+' para liberar espacio</b><span>La detección sigue.</span></div></div>';
    const mc = st.permisoMovimientos;
    const trow = (icon, id, name, sub, on, act, key, campo, cur, dis, why) => '<div class="trow"><div class="trow-h"><span class="ci">'+ic(icon)+'</span><span class="grow"><b id="'+id+'">'+name+'</b><span>'+sub+'</span></span>'+sw(on, act, id, dis)+'</div>'+
      retPills(st, key, campo, cur, dis || !on, 'Cuánto tiempo guardar: '+name)+(why?'<p class="why">'+ic('lock')+'<span>'+why+'</span></p>':'')+'</div>';
    const capOtro = ![10,25,50,100].includes(a.limite_gb);
    return band+'<div class="stwrap" id="stwrap"><div class="stgrid"><div class="stcol">'+
      '<div class="stcard"><h3>Uso</h3><p class="usage-n"><b>'+gb(used)+' GB</b><span>de '+gb(cap).replace(/,0$/, '')+' GB</span></p>'+
        '<div class="ubar" role="img" aria-label="Movimientos '+gb(u.movimientos)+' GB, video '+gb(u.video)+' GB, clips '+gb(u.clips)+' GB de '+gb(cap)+' GB"><i class="u-mov" style="width:'+pct(u.movimientos)+'%"></i><i class="u-vid" style="width:'+pct(u.video)+'%"></i><i class="u-clip" style="width:'+pct(u.clips)+'%"></i></div>'+
        '<p class="ulg"><span><i class="u-mov"></i>Movimientos <b>'+gb(u.movimientos)+' GB</b></span><span><i class="u-vid"></i>Video <b>'+gb(u.video)+' GB</b></span><span><i class="u-clip"></i>Clips <b>'+gb(u.clips)+' GB</b></span><span>Libre <b>'+gb(Math.max(0, cap-used))+' GB</b></span></p></div>'+
      '<div class="stcard"><h3>Carpeta</h3><div class="folder"><span class="code" title="'+esc(st.carpeta)+'">'+esc(st.carpeta)+'</span><button class="btn btn-secondary btn-xs" data-act="folderChange"'+(st.estado==='moviendo'?' disabled':'')+'>'+ic('folder')+'Cambiar carpeta</button></div>'+
        (st.estado==='moviendo' ? '<div class="moving" role="status">Moviendo '+gb(used)+' GB… La detección sigue.<div class="tbar"><i style="transform:scaleX(.45)"></i></div></div>' : '')+'</div>'+
      '<div class="stcard"><p class="irow"><span class="ci calma">'+ic('lock')+'</span><span><b>Datos cifrados</b>Solo Te Tengo Captura puede leerlos.</span></p></div>'+
      '<div class="stcard"><p class="irow"><span class="ci">'+ic('cloud')+'</span><span><b>En la nube</b>'+(st.nube ? 'Movimientos: '+dias(st.nube)+' (lo eligió la familia).' : 'Movimientos: desactivado.')+' Video: nunca.</span></p></div>'+
    '</div><div class="stcol">'+
      '<div class="stcard"><h3>Qué se guarda aquí</h3>'+
        trow('person', 'st-mov', 'Movimientos (puntos del cuerpo)', 'Sin imagen ni video', mc && a.movimientos, 'stMov', 'mov', 'dias_movimientos', a.dias_movimientos, !mc, mc ? '' : 'Requiere el permiso de '+esc(E.home.first)+' (se registra en la app).')+
        trow('cam', 'st-vid', 'Video continuo', 'Nunca se sube', a.video, 'stVid', 'vid', 'dias_video', a.dias_video, false, '')+
        trow('play', 'st-clip', 'Clips de los avisos', '12 s por aviso', a.clips, 'stClip', 'clip', 'dias_clips', a.dias_clips, false, '')+'</div>'+
      '<div class="stcard"><h3>Límite de espacio'+infoTip('Al llegar, borramos lo más antiguo: primero video, luego movimientos.','límite de espacio',{k:'cap',start:1,up:1})+'</h3>'+retPills(st, 'cap', 'limite_gb', a.limite_gb, false, 'Límite de espacio')+
        (capOtro || U.capOther ? '<div class="cap-other"><label class="sr" for="cap-val">Límite en GB</label><input class="input mono" id="cap-val" inputmode="numeric" value="'+esc(capOtro ? a.limite_gb : '')+'" placeholder="75"><span class="t-meta">GB</span></div>' : '')+
        '</div>'+
    '</div></div></div>';
  }
  function advSubs(E){ return (E.advanced ? [['registro','terminal','Registro en vivo'], ['medidores','gauge','Medidores']] : []).concat([['actividad','list','Actividad'], ['almacenamiento','drive','Almacenamiento']]); }
  function advSub(E, U){ const subs = advSubs(E); if(U.adv.sub==='acerca' && E.upd) return 'acerca'; return subs.some(x => x[0]===U.adv.sub) ? U.adv.sub : (E.advanced ? 'registro' : 'actividad'); }
  function panelAvanzado(E, U){
    const sub = advSub(E, U), on = !!E.advanced, cam = advCam(E, U), camSel = on && (sub==='registro' || sub==='medidores');
    const seg = '<div class="seg2" role="tablist" aria-label="Avanzado">'+advSubs(E).map(x => '<button role="tab" id="sub-'+x[0]+'" aria-selected="'+(x[0]===sub)+'" tabindex="'+(x[0]===sub?0:-1)+'" data-act="advSub" data-arg="'+x[0]+'">'+(on?'':ic(x[1]))+x[2]+'</button>').join('')+'</div>';
    const btns = '<div class="advbtns"><button class="btn btn-secondary btn-sm" data-act="replayOpen">'+ic('replay')+'Ver qué pasó</button>'+(on ? '<button class="btn btn-secondary btn-sm" data-act="diagOpen">'+ic('download')+'Exportar diagnóstico</button>' : '')+'</div>';
    const cams = advCams(E);
    const mode = on
      ? '<div class="card advstrip">'+sw(true, 'advToggle', 'adv-l')+'<span class="grow"><b id="adv-l">Modo avanzado</b></span>'+infoTip('Nada sale de esta PC: el registro y los medidores solo se ven aquí.','modo avanzado',{k:'adv',start:1})+
          (camSel && cams.length ? '<span class="cam-l" id="cam-l">Cámara</span><div class="seg2 sm" role="radiogroup" aria-labelledby="cam-l">'+cams.map(c => '<button role="radio" aria-checked="'+(cam && c.id===cam.id)+'" data-act="advCam" data-arg="'+esc(c.id)+'">'+esc(c.room)+'</button>').join('')+'</div>' : '')+'</div>'
      : '<div class="card advcard"><span class="ci lg">'+ic('sliders')+'</span><div class="grow"><b id="adv-l">Modo avanzado</b><span>Qué detecta cada cámara y por qué avisa. Nada sale de esta PC.</span></div>'+sw(false, 'advToggle', 'adv-l')+'</div>';
    const sinCamara = '<div class="logempty">'+ic('cam')+'<b>Aún no pasa nada en esta cámara</b></div>';
    const body = sub==='registro' ? (cam ? logView(E, U, cam) : sinCamara) : sub==='medidores' ? (cam ? metersView(E, U, cam) : sinCamara) : sub==='almacenamiento' ? storageView(E, U) : sub==='acerca' ? aboutView(E, U) : actView(E, U);
    return '<h1 class="sr" id="scr-h" tabindex="-1">Avanzado</h1><div class="advhead">'+seg+btns+'</div>'+mode+'<div class="advbody" role="tabpanel" aria-labelledby="sub-'+sub+'">'+body+'</div>';
  }

  /* =================== Ver qué pasó: repetición del movimiento (US-39) =================== */
  const SPEEDS = [.5, 1, 2, 4];
  const RP_FASES = [['De pie','','person'], ['Movimiento inestable','inestable','warn'], ['Posible caída','caida','warn'], ['En el suelo','caida','warn'], ['En el suelo · caída confirmada','caida','warn'], ['Se levantó','calma','arrowUp']];
  const RP_SEG = [['h','sL'],['h','sR'],['sL','eL'],['eL','wL'],['sR','eR'],['eR','wR'],['sL','hL'],['sR','hR'],['hL','hR'],['hL','kL'],['kL','aL'],['hR','kR'],['kR','aR']];
  function spTxt(v){ return String(v).replace('.', ',')+'×'; }
  function hmsMs(ms){ const d = new Date(ms); return pad2(d.getHours())+':'+pad2(d.getMinutes())+':'+pad2(d.getSeconds()); }
  function hmMs(ms){ return hmsMs(ms).slice(0, 5); }
  function rpSpan(rp){ return (rp.zoom==='60' ? 3600 : 600) * 1000; }
  function rpCamInfo(rp){ const cs = (rp.info && rp.info.camaras) || []; return cs.find(c => c.id===rp.cam) || cs[0] || null; }
  function rpGap(rp, t){ const w = rp.win; return w ? (w.huecos || []).find(g => t >= g.a && t < g.b) || null : null; }
  /* the row shown at t: the newest one at or before t, within half a second */
  function rpRow(rp, t){
    const p = rp.poses; if(!p || !p.t.length || t < p.desde || t > p.hasta) return null;
    let lo = 0, hi = p.t.length - 1, k = -1;
    while(lo <= hi){ const m = (lo+hi) >> 1; if(p.t[m] <= t){ k = m; lo = m+1; } else hi = m-1; }
    return k >= 0 && t - p.t[k] <= 500 ? k : null;
  }
  function rpPhase(rp, t){
    const g = rpGap(rp, t); if(g) return {label:g.motivo, tone:'gap', i:'person', p:null};
    const k = rpRow(rp, t), p = rp.poses;
    if(k==null) return {label:'Cargando…', tone:'gap', i:'clock', p:null};
    const f = RP_FASES[p.f[k]] || RP_FASES[0], pts = p.p[k];
    if(!pts) return {label:'Sin persona en la imagen', tone:'gap', i:'person', p:null};
    const pose = {}; p.claves.forEach((c, j) => pose[c] = [pts[2*j], pts[2*j+1]]);
    return {label:f[0], tone:f[1], i:f[2], p:pose};
  }
  /* the skeleton where it was in the image (4:3, the same box as the video under it) */
  function rpFig(rp, t){
    const r = rpPhase(rp, t), col = rp.video ? '#FFFFFF' : '#2B1D4E', fill = rp.video ? '#2B1D4E' : '#fff';
    let s = '';
    if(r.p){
      const P = k => [(r.p[k][0]*400).toFixed(1), (r.p[k][1]*300).toFixed(1)];
      RP_SEG.forEach(([a,b]) => { const A = P(a), B = P(b); s += '<line x1="'+A[0]+'" y1="'+A[1]+'" x2="'+B[0]+'" y2="'+B[1]+'" stroke="'+col+'" stroke-width="3.4" stroke-linecap="round"/>'; });
      Object.keys(r.p).forEach(k => { const a = P(k); s += '<circle cx="'+a[0]+'" cy="'+a[1]+'" r="'+(k==='h'?8:3.6)+'" fill="'+fill+'" stroke="'+col+'" stroke-width="'+(k==='h'?3:2)+'"/>'; });
    }
    return '<svg viewBox="0 0 400 300" preserveAspectRatio="xMidYMid meet" aria-hidden="true"><g class="skel">'+s+'</g></svg>';
  }
  function rpValText(rp, t){
    const e = ((rp.win && rp.win.eventos) || []).find(x => Math.abs(x.t-t) < 1500), g = rpGap(rp, t);
    return hmsMs(t)+(e ? ', '+e.l.toLowerCase() : g ? ', sin datos: '+g.corto.toLowerCase() : '');
  }
  function markSVG(k){
    const sh = k==='caida' ? '<path d="M10 2 18.6 17.2H1.4Z" style="fill:var(--caida)" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/>'
      : k==='inestable' ? '<path d="M10 1.4 18.6 10 10 18.6 1.4 10Z" style="fill:var(--inestable-deep)" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/>'
      : '<circle cx="10" cy="10" r="7.6" style="fill:var(--calma)" stroke="#fff" stroke-width="1.6"/>';
    return '<svg viewBox="0 0 20 20" aria-hidden="true">'+sh+'</svg>';
  }
  function timeline(rp){
    const a = rp.w0, b = rp.w0 + rpSpan(rp), span = b-a, P = t => ((t-a)/span*100).toFixed(2), t = rp.t, w = rp.win || {eventos:[], huecos:[]};
    const evs = w.eventos.filter(e => e.t >= a && e.t <= b), big = rp.zoom==='60';
    const gaps = w.huecos.filter(g => g.b > a && g.a < b).map(g => ({a:Math.max(a, g.a), b:Math.min(b, g.b), s:g.corto}));
    const step = (big ? 600 : 120)*1000, ticks = [];
    for(let x = Math.ceil(a/step)*step; x <= b; x += step) ticks.push(x);
    return '<div class="tl"><div class="tl-track" id="tl-track" role="slider" tabindex="0" aria-label="Línea de tiempo" aria-valuemin="'+Math.round(a/1000)+'" aria-valuemax="'+Math.round(b/1000)+'" aria-valuenow="'+Math.round(t/1000)+'" aria-valuetext="'+esc(rpValText(rp, t))+'">'+
      '<span class="tl-gaps" aria-hidden="true">'+gaps.map(g => '<i class="tl-gap" style="left:'+P(g.a)+'%;width:'+((g.b-g.a)/span*100).toFixed(2)+'%"></i>').join('')+'</span>'+
      evs.map(e => '<button class="tl-m" style="left:'+P(e.t)+'%" data-act="rpSeek" data-arg="'+e.t+'" aria-label="'+e.l+', '+hmsMs(e.t)+'" title="'+e.l+' · '+hmsMs(e.t)+'">'+markSVG(e.k)+'</button>').join('')+
      '<i class="tl-head" id="tl-head" style="left:'+P(Math.min(b, Math.max(a, t)))+'%"></i></div>'+
      '<div class="tl-labels" aria-hidden="true">'+ticks.map(x => '<span style="left:'+P(x)+'%">'+hmMs(x)+'</span>').join('')+
        (big ? '' : evs.map(e => '<span class="ev '+e.k+'" style="left:'+P(e.t)+'%">'+e.l+'</span>').join(''))+
        gaps.map(g => '<span class="ev gap" style="left:'+P((g.a+g.b)/2)+'%">'+esc(g.s)+'</span>').join('')+'</div></div>';
  }
  function rpForm(E, rp){
    const info = rp.info || {permitida:false, camaras:[]}, cam = rpCamInfo(rp), dis = !info.permitida, vOk = !!(rp.win && rp.win.video);
    const hoy = new Date(), iso = hoy.getFullYear()+'-'+pad2(hoy.getMonth()+1)+'-'+pad2(hoy.getDate());
    const dias = cam && cam.dias.length ? cam.dias : [{valor:iso, texto:'Hoy, '+pad2(hoy.getDate())+'/'+pad2(hoy.getMonth()+1)+'/'+hoy.getFullYear(), corto:''}];
    return '<div class="card rp-form'+(dis?' disabled':'')+'"><span class="label" id="rp-cl">Cámara</span><div class="seg2 sm" role="radiogroup" aria-labelledby="rp-cl">'+
        info.camaras.map(c => '<button role="radio" aria-checked="'+(cam && c.id===cam.id)+'" data-act="rpCam" data-arg="'+esc(c.id)+'"'+(dis?' disabled':'')+'>'+esc(c.room)+'</button>').join('')+'</div>'+
      '<label class="label" for="rp-day">Fecha</label><select class="input" id="rp-day"'+(dis?' disabled':'')+'>'+dias.map(d => '<option value="'+esc(d.valor)+'"'+(d.valor===rp.day?' selected':'')+'>'+esc(d.texto)+'</option>').join('')+'</select>'+
      '<label class="label" for="rp-hour">Hora</label><input class="input mono" id="rp-hour" value="'+esc(rp.hour)+'" inputmode="numeric" maxlength="5" autocomplete="off"'+(dis?' disabled':'')+'>'+
      '<div class="qchips">'+[['Hace 15 min','m15'], ['Hace 1 hora','h1'], ['Hoy 07:00','h7']].map(q => '<button data-act="rpQuick" data-arg="'+q[1]+'"'+(dis?' disabled':'')+'>'+q[0]+'</button>').join('')+'</div>'+
      '<button class="btn btn-primary btn-sm" data-act="rpGo"'+(dis?' disabled':'')+'>'+ic('replay')+'Ver</button>'+
      '<p class="t-meta">'+(dis || !cam || !cam.desde ? 'No hay movimientos guardados.' : 'Datos desde el '+esc(cam.desde)+'.')+'</p>'+
      '<div class="vtoggle mt12"><span><b><span id="rp-vl">Sobre el video guardado</span>'+(vOk ? infoTip('El video nunca sale de esta PC.','video guardado',{k:'rp-vid',start:1,up:1}) : '')+'</b>'+(vOk ? '' : '<span>No hay video de ese momento.</span>')+'</span>'+sw(rp.video && vOk, 'rpVideo', 'rp-vl', !vOk || dis, true)+'</div></div>';
  }
  function panelReplay(E, U){
    const rp = U.rp, info = rp.info || {permitida:false, camaras:[]}, cam = rpCamInfo(rp);
    const dia = cam && (cam.dias.find(d => d.valor===rp.day) || {}).corto;
    const head = '<div class="rp-head"><button class="back" data-act="replayClose">'+ic('back')+'Volver</button><h1 class="t-title" id="scr-h" tabindex="-1">Ver qué pasó</h1>'+
      '<span class="t-meta" id="rp-title">'+(cam ? esc(cam.room)+(dia ? ' · '+esc(dia) : '') : '')+'</span></div>';
    let main;
    if(!rp.info) main = '<div class="rp-main"><div class="card rp-block" role="status"><span class="spin"></span></div></div>';
    else if(!info.permitida) main = '<div class="rp-main"><div class="card rp-block"><div class="notice warn">'+ic('lock')+'<div><b>Falta el permiso de '+esc(E.home.first)+' para guardar movimientos</b><span>Se registra en la app: Privacidad › Guardar movimientos.</span></div></div></div></div>';
    else if(!cam || !cam.desde) main = '<div class="rp-main"><div class="card rp-block"><div class="notice info">'+ic('clock')+'<div><b>No hay movimientos guardados.</b></div></div></div></div>';
    else if(rp.state==='old') main = '<div class="rp-main"><div class="card rp-block"><div class="notice info">'+ic('clock')+'<div><b>Ya no hay movimientos de ese momento.</b><span>Hay datos desde el '+esc(cam.desde)+'. Elige otra fecha.</span></div></div></div></div>';
    else {
      const p = rpPhase(rp, rp.t), w = rp.win || {eventos:[]}, a = rp.w0, b = a + rpSpan(rp), evs = w.eventos.filter(e => e.t >= a && e.t <= b);
      const conVideo = rp.video && w.video;
      const strip = conVideo ? '<p class="rp-strip video">'+ic('lock')+'Video guardado solo en esta PC'+infoTip('El video nunca sale de esta PC. Ver la repetición queda en el registro de accesos.','privacidad',{k:'rp',start:1})+'</p>'
        : '<p class="rp-strip">'+ic('eye')+'Solo puntos del cuerpo, nunca video'+infoTip('Ver la repetición queda en el registro de accesos.','privacidad',{k:'rp',start:1})+'</p>';
      main = '<div class="rp-main">'+strip+
        '<div class="rp-canvas" id="rp-canvas">'+(conVideo ? '<div class="rp-vid"><img id="rp-img" alt="" style="position:absolute;inset:0;width:100%;height:100%;object-fit:contain" hidden></div>' : '')+
          '<div class="rp-fig" id="rp-fig">'+rpFig(rp, rp.t)+'</div><span class="rp-phase '+p.tone+'" id="rp-phase" aria-live="polite">'+ic(p.i)+esc(p.label)+'</span><span class="rp-clock" id="rp-clock">'+hmsMs(rp.t)+'</span></div>'+
        timeline(rp)+
        '<div class="rp-ctrl"><button class="ibtn" data-act="rpPrev" aria-label="Evento anterior" title="Evento anterior">'+ic('prev')+'</button>'+
          '<button class="ibtn play" data-act="rpPlay" aria-label="'+(rp.playing?'Pausar':'Reproducir')+'" title="'+(rp.playing?'Pausar':'Reproducir')+'">'+ic(rp.playing?'pauseF':'play')+'</button>'+
          '<button class="ibtn" data-act="rpNext" aria-label="Evento siguiente" title="Evento siguiente">'+ic('next')+'</button>'+
          '<span class="rp-time mono" id="rp-time">'+hmsMs(rp.t)+'</span>'+
          '<button class="ibtn speed" data-act="rpSpeed" aria-label="Velocidad: '+spTxt(rp.speed)+'" title="Cambiar la velocidad">'+spTxt(rp.speed)+'</button>'+
          '<div class="seg2 sm" role="radiogroup" aria-label="Rango de la línea de tiempo"><button role="radio" aria-checked="'+(rp.zoom==='10')+'" data-act="rpZoom" data-arg="10">10 min</button><button role="radio" aria-checked="'+(rp.zoom==='60')+'" data-act="rpZoom" data-arg="60">1 h</button></div></div>'+
        det(U, 'rpev', 'rp-ev', 'Eventos ('+evs.length+')', evs.length ? evs.map(e => '<button class="evrow" data-act="rpSeek" data-arg="'+e.t+'"><time class="mono">'+hmsMs(e.t)+'</time>'+markSVG(e.k)+'<span>'+e.l+' · '+esc(cam.room)+'</span></button>').join('') : '<p class="t-meta" style="padding:4px 0 8px">Sin eventos.</p>')+'</div>';
    }
    return head+'<div class="rp-grid">'+rpForm(E, rp)+main+'</div>';
  }

  /* =================== diálogos =================== */
  function dlgBox(id, icon, title, text, body, actions){
    return '<div class="dlg-back"><div class="dlg" role="dialog" aria-modal="true" aria-labelledby="'+id+'-t"'+(text?' aria-describedby="'+id+'-d"':'')+' id="'+id+'"><div class="dlg-h">'+icon+'<div><h2 id="'+id+'-t">'+title+'</h2>'+(text?'<p id="'+id+'-d">'+text+'</p>':'')+'</div></div>'+body+'<div class="dlg-actions">'+actions+'</div></div></div>';
  }
  function num1(n){ return n.toFixed(1).replace('.', ','); }
  function dialog(E, U){
    if(U.dlg==='unlink' && E.screen==='main'){
      const rooms = E.cams.map(c => c.room), gb = (E.dataBytes || 0) / 1e9;
      return dlgBox('dlg-unlink', '<span class="ci lg caida">'+ic('unlink')+'</span>', '¿Desvincular esta PC?',
        (rooms.length ? 'Se dejan de detectar caídas en '+esc(listY(rooms))+'. ' : '')+'La familia recibirá un aviso.',
        '<label class="checkrow"><input type="checkbox" id="unlink-wipe"'+(U.unlinkWipe?' checked':'')+'><span>Borrar también los datos de esta PC ('+num1(gb)+' GB)<span>Movimientos, video y clips.</span></span></label>',
        '<button class="btn btn-secondary" data-act="dlgClose">Cancelar</button><button class="btn btn-danger" data-act="unlinkDo"'+(U.busy?' disabled':'')+'>'+ic('unlink')+'Desvincular</button>');
    }
    if(U.dlg==='video') return dlgBox('dlg-video', '<span class="ci lg">'+ic('cam')+'</span>', '¿Guardar video continuo en esta PC?',
      'Se queda en esta PC, nunca se sube. 480p a 8 fps, en partes de 10 min. Ocupa mucho espacio.', '',
      '<button class="btn btn-secondary" data-act="dlgClose">Cancelar</button><button class="btn btn-primary" data-act="videoOn">Activar</button>');
    if(U.dlg==='revoke' || (E.store && E.store.revocado && E.screen==='main' && !U.dlg)){
      const mb = E.store ? gb(E.store.uso.movimientos) : '0,0';
      return dlgBox('dlg-revoke', '<span class="ci lg aviso">'+ic('person')+'</span>', '¿Borrar los movimientos de esta PC ('+mb+'&nbsp;GB)?',
        esc(E.home.first)+' ya no autoriza guardarlos (lo registró la familia). No guardamos nuevos y los de la nube se borran. Las alertas siguen.', '',
        '<button class="btn btn-secondary" data-act="revokeKeep">Conservar</button><button class="btn btn-danger" data-act="revokeWipe">'+ic('trash')+'Borrar</button>');
    }
    if(U.dlg==='updNotes' && E.upd && E.upd.latest){
      const u = E.upd, sub = [u.date ? 'Publicada el '+esc(u.date) : '', u.mb ? u.mb+' MB' : ''].filter(Boolean).join(' · ');
      return dlgBox('dlg-notes', '<span class="ci lg">'+ic('list')+'</span>', 'Qué cambió en la versión '+esc(u.latest), sub,
        '<ul class="notes">'+u.notes.map(x => '<li>'+ic('check')+esc(x)+'</li>').join('')+'</ul><p class="keep">'+ic('lock')+KEEP+'</p>',
        '<button class="btn btn-secondary" data-act="dlgClose">Cerrar</button>'+(!['dl','verify','restart','wait'].includes(u.st) ? updBtn(u, '') : ''));
    }
    if(U.dlg==='updMac' && E.upd && E.upd.latest){
      const u = E.upd;
      return dlgBox('dlg-mac', '<span class="ci lg">'+ic('download')+'</span>', 'Actualizar a la versión '+esc(u.latest), 'Abrimos <b>'+esc(u.page || '')+'</b> en tu navegador. Baja el archivo y:',
        '<ol class="macsteps"><li><span class="n">1</span><span>Abre <b class="code">'+esc(u.dmg)+'</b></span></li><li><span class="n">2</span><span>Arrastra Te Tengo Captura a <b>Aplicaciones</b></span></li><li><span class="n">3</span><span>Elige <b>Reemplazar</b></span></li></ol>'+
        '<p class="keep">'+ic('info')+'Es temporal, hasta que la app esté firmada por Apple. '+KEEP+'</p>',
        '<button class="btn btn-primary" data-act="dlgClose">Entendido</button>');
    }
    if(U.dlg==='diag'){
      const d = U.diag, nombre = d.nombre || '';
      const file = '<div class="filebox">'+ic('doc')+'<span class="code">'+esc(d.step==='done' ? d.ruta : nombre)+'</span>'+(d.step==='done' ? '<small>'+esc(d.tamano)+'</small>' : '')+'</div>';
      if(d.step==='busy') return dlgBox('dlg-diag', '<span class="ci lg">'+ic('download')+'</span>', 'Exportar diagnóstico', 'Un archivo para el equipo de soporte.',
        file+'<div class="prog" role="status"><div class="tbar"><i></i></div><p>Preparando el diagnóstico…</p></div>', '');
      if(d.step==='done') return dlgBox('dlg-diag', '<span class="ci lg calma">'+ic('check')+'</span>', 'Diagnóstico guardado · '+esc(d.tamano), 'Envíalo a soporte cuando te lo pidan.',
        file, '<button class="btn btn-secondary" data-act="diagShow">'+ic('folder')+'Mostrar en la carpeta</button><button class="btn btn-primary" data-act="dlgClose">Listo</button>');
      const lists = '<div class="inc"><div class="yes"><h3>Incluye</h3><ul>'+['Registros del programa', 'Versión y sistema operativo', 'Cámaras y habitaciones', 'Umbrales de detección'].map(x => '<li>'+ic('check')+x+'</li>').join('')+'</ul></div>'+
        '<div class="no"><h3>No incluye</h3><ul>'+['Contraseñas ni accesos', 'Imágenes ni video', 'Puntos del cuerpo'].map(x => '<li>'+ic('x')+x+'</li>').join('')+'</ul></div></div>';
      return dlgBox('dlg-diag', '<span class="ci lg">'+ic('download')+'</span>', 'Exportar diagnóstico', 'Un archivo para el equipo de soporte.',
        (d.step==='err' ? '<div class="notice err" role="alert">'+ic('warn')+'<div><b>No pudimos guardar en esa carpeta</b><span>No quedó ningún archivo. Elige otra.</span></div></div>' : lists)+file,
        '<button class="btn btn-secondary" data-act="dlgClose">Cancelar</button><button class="btn btn-primary" data-act="diagSave">'+ic('folder')+(d.step==='err'?'Elegir otra carpeta':'Elegir dónde guardar')+'</button>');
    }
    return '';
  }

  /* ---------- la ventana completa ---------- */
  function screen(E, U, enter){
    if(E.screen==='vincular') return scrVincular(E, U, enter);
    if(E.screen==='vinculada') return scrVinculada(E, U, enter);
    if(E.screen==='rechazada') return scrRechazada(E, U, enter);
    if(E.screen==='quitada') return scrQuitada(E, U, enter);
    return scrMain(E, U, enter);
  }
  function win(E, U, enter){
    const t = U.toast ? '<div class="wtoast '+U.toast.kind+'" role="status">'+ic(U.toast.icon||'check')+'<span>'+esc(U.toast.text)+'</span></div>' : '';
    return titlebar()+'<div class="wb">'+screen(E, U, enter)+t+dialog(E, U)+'</div>';
  }

  /* ---------- arranque: ventana de inicio (core.js) ---------- */
  const BOOT_STEPS = ['Iniciando…', 'Abriendo las cámaras…', 'Conectando con Te Tengo…', 'Terminando la actualización…'];
  function bootMark(){ return symbolSVG(false, 'class="sp-mark"'); }
  function bootWin(o){
    o = o||{}; const pct = o.pct==null ? 34 : o.pct, step = o.step||0;
    return '<div class="boot'+(o.play?' play':'')+'" role="dialog" aria-label="Te Tengo Captura se está iniciando">'+
      '<div class="boot-mark"><span class="sp-glow"></span>'+bootMark()+'</div>'+wordmark(false, true, 'boot-wm')+
      '<div class="boot-foot"><div class="boot-bar" role="progressbar" aria-label="Progreso del inicio" aria-valuemin="0" aria-valuemax="100" aria-valuenow="'+pct+'"><i style="transform:scaleX('+(pct/100)+')"></i></div>'+
      '<p class="boot-st"><span id="boot-st" aria-live="polite">'+BOOT_STEPS[step]+'</span><span class="boot-v">Versión '+esc(o.version||'')+'</span></p></div></div>';
  }

  /* ---------- avisos dentro de la ventana al cambiar el estado (proto.js) ---------- */
  function transition(prev, E){
    if(!prev || prev.screen!=='main' || E.screen!=='main' || !prev.listo || !E.listo) return null;
    const before = {}; prev.cams.forEach(c => before[c.id] = c);
    for(const c of E.cams){
      const p = before[c.id]; if(!p) continue;
      if(p.st.k==='off' && c.st.k!=='off') return {kind:'ok', icon:'usb', text:'La '+c.device+' volvió a responder.'};
      if(!p.pause && c.pause) return {kind:'ok', icon:'pause', text:'La familia pausó '+ROOM_ART(c.room)+' hasta las '+c.pause+'.'};
      if(p.pause && !c.pause && c.st.k!=='off') return {kind:'ok', icon:'check', text:'Pausa terminada: vuelve a cuidar '+ROOM_ART(c.room)+'.'};
      if(p.room!==c.room) return {kind:'ok', icon:'check', text:'Habitación renombrada en la app: «'+c.room+'».'};
    }
    const antes = {}; (prev.devices || []).forEach(d => antes[d.uid || d.id] = d);
    for(const d of (E.devices || [])){
      const a = antes[d.uid || d.id]; if(!a) continue;
      if(!a.room && d.room && d.by==='app') return {kind:'ok', icon:'mobile', text:'La familia eligió la '+d.name+' para '+ROOM_ART(d.room)};
      if(a.room && !d.room && a.by==='app') return {kind:'ok', icon:'mobile', text:'La familia dejó de usar la '+d.name+': ya no cuida '+ROOM_ART(a.room)+'.'};
    }
    if(!prev.online && E.online) return {kind:'ok', icon:'check', text:'Volvió internet. Avisos enviados.'};
    if(!prev.consent && E.consent) return {kind:'ok', icon:'check', text:'Consentimiento registrado en la app.'};
    if(prev.store && E.store && prev.store.estado==='moviendo' && E.store.estado!=='moviendo')
      return E.store.carpeta!==prev.store.carpeta ? {kind:'ok', icon:'folder', text:'Datos movidos a la carpeta nueva.'} : {kind:'warn', icon:'folder', text:'No pudimos mover los datos. Siguen en la carpeta anterior.'};
    return null;
  }
  /* What forces a full render; the countdown in the summary is only patched in place. */
  function structure(E){
    const o = Object.assign({}, E, {retry:0});
    if(E.health) o.health = Object.assign({}, E.health, {detalle_html:''});
    if(E.pair) o.pair = Object.assign({}, E.pair, {left:0, retry:0});
    if(E.upd) o.upd = Object.assign({}, E.upd, {pct:0});  // the download's progress is patched
    return JSON.stringify(o);
  }

  const api = { ITIP, infoTip, updBand, aboutView, dialog, panelReplay, rpPhase, timeline, storageView, panelAvanzado, metersInner, actView, ic, esc, roomSVG, titlebar, tabbar, health, camRow, panelEstado, panelCamaras, win, transition, structure, bootWin, BOOT_STEPS, listY, ROOM_ART, appIcon, LOGO, symbolSVG, mmss };

  /* ---------- DOM: render with focus, folded sections and scroll preserved ---------- */
  if(typeof document === 'undefined'){ if(typeof module !== 'undefined') module.exports = api; return; }

  const $ = id => document.getElementById(id);
  let E = null, first = true, toastTimer = null, preview = null, previewSrc = null;
  const U = {tab:'estado', sel:null, open:{}, toast:null, dlg:null, unlinkWipe:false, busy:false, here:false, rooms:null, pick:{room:null, otherOn:false, other:'', err:null},
    rp:{open:false}, adv:{sub:'actividad', cam:null}, checking:false, updToast:false, log:{filters:{persona:true, evento:true, descarte:true, conexion:true, programa:true}, q:'', paused:false, cut:0, open:null, lines:{}, ultimo:0}, meters:{}, acts:null, actScope:'pc', diag:{step:'intro'}};
  let opener = null;
  const bridge = () => (global.pywebview && global.pywebview.api) || null;

  /* ---------- help «?»: placement and the click, hover, focus, Escape and scroll behaviour (core.js itip*) ---------- */
  /* the visible box: the window clipped by every scrolling container */
  function itipBox(t){
    let r = {top:0, left:0, bottom:window.innerHeight, right:window.innerWidth};
    for(let e = t.parentElement; e && e !== document.body; e = e.parentElement){
      const cs = getComputedStyle(e);
      if(cs.overflow !== 'visible' || e.matches('.win,.wb')){ const b = e.getBoundingClientRect(); r = {top:Math.max(r.top, b.top), left:Math.max(r.left, b.left), bottom:Math.min(r.bottom, b.bottom), right:Math.min(r.right, b.right)}; }
      if(e.matches('.win')) break;
    }
    return r;
  }
  function itipPlace(t){
    const pop = t.querySelector('.itip-pop'); if(!pop) return;
    t.classList.remove('flip'); pop.style.removeProperty('--dx');
    const v = itipBox(t), b = t.getBoundingClientRect(), r = pop.getBoundingClientRect(), up = t.classList.contains('up'), M = 8;
    if(up ? (r.top < v.top+M && b.bottom+r.height+M <= v.bottom) : (r.bottom > v.bottom-M && b.top-r.height-M >= v.top)) t.classList.add('flip');
    let dx = 0;
    if(r.left < v.left+M) dx = v.left+M-r.left; else if(r.right > v.right-M) dx = v.right-M-r.right;
    if(dx) pop.style.setProperty('--dx', Math.round(dx)+'px');
  }
  function itipShow(t, pin){
    document.querySelectorAll('.itip.open').forEach(x => { if(x !== t) itipHide(x); });
    t.classList.add('open'); t.firstChild.setAttribute('aria-expanded', 'true'); ITIP.open = t.dataset.tip; ITIP.pin = !!pin; itipPlace(t);
  }
  function itipHide(t){ t.classList.remove('open', 'flip'); t.firstChild.setAttribute('aria-expanded', 'false'); if(ITIP.open === t.dataset.tip){ ITIP.open = null; ITIP.pin = false; } }
  function itipCloseAll(){ document.querySelectorAll('.itip.open').forEach(itipHide); ITIP.open = null; ITIP.pin = false; }
  /* after a render the open help is placed again; the scroll a render restores does not close it */
  function itipSync(){ ITIP.quiet = Date.now() + 200; document.querySelectorAll('.itip.open').forEach(itipPlace); }
  function itipInit(){
    if(ITIP.on) return; ITIP.on = true;
    const tipOf = e => { const b = e.target.closest && e.target.closest('.itip-b'); return b ? b.parentNode : null; };
    document.addEventListener('click', e => {
      const t = tipOf(e); ITIP.mute = null;
      if(t){ e.preventDefault(); if(t.classList.contains('open') && ITIP.pin) itipHide(t); else itipShow(t, true); return; }
      if(ITIP.open != null && !(e.target.closest && e.target.closest('.itip-pop'))) itipCloseAll();
    }, true);
    document.addEventListener('pointerover', e => { const t = tipOf(e); if(t && e.pointerType === 'mouse' && !t.classList.contains('open') && ITIP.mute !== t.dataset.tip) itipShow(t, false); });
    document.addEventListener('pointerout', e => {
      const t = e.target.closest && e.target.closest('.itip'); if(!t || t.contains(e.relatedTarget)) return;
      ITIP.mute = null;
      if(e.pointerType === 'mouse' && !ITIP.pin && t.classList.contains('open')) itipHide(t);
    });
    document.addEventListener('focusin', e => { const t = tipOf(e); if(t && e.target.matches(':focus-visible') && !t.classList.contains('open') && ITIP.mute !== t.dataset.tip) itipShow(t, false); });
    document.addEventListener('focusout', e => { const t = tipOf(e); if(t && !ITIP.pin && t.classList.contains('open')) itipHide(t); });
    document.addEventListener('keydown', e => {
      if(e.key === 'Tab') ITIP.mute = null;
      if(e.key === 'Escape' && document.querySelector('.itip.open')){ ITIP.mute = ITIP.open; itipCloseAll(); e.stopPropagation(); e.preventDefault(); }
    }, true);
    document.addEventListener('scroll', () => { if(ITIP.open != null && Date.now() > ITIP.quiet) itipCloseAll(); }, true);
    global.addEventListener('resize', () => itipSync());
  }
  itipInit();

  function snap(){
    const a = document.activeElement;
    if(!a || a === document.body || !$('app').contains(a)) return null;
    if(a.classList.contains('itip-b')) return {tip:a.parentNode.dataset.tip};
    return {id:a.id, act:a.dataset && a.dataset.act, arg:a.dataset && a.dataset.arg};
  }
  function restore(f){
    if(!f) return;
    let el = f.id ? $(f.id) : null;
    if(f.tip!=null) el = document.querySelector('#app .itip[data-tip="'+CSS.escape(f.tip)+'"] .itip-b');
    if(!el && f.act) el = document.querySelector('#app [data-act="'+f.act+'"]'+(f.arg!=null ? '[data-arg="'+CSS.escape(f.arg)+'"]' : '')) || document.querySelector('#app [data-act="'+f.act+'"]');
    if(el && !el.disabled) el.focus({preventScroll:true});
  }
  function render(enter){
    if(!E) return;
    const f = enter ? null : snap();
    const rows = document.querySelector('.clist-rows'), top = rows ? rows.scrollTop : 0;
    $('app').innerHTML = win(E, U, enter);
    const rows2 = document.querySelector('.clist-rows'); if(rows2) rows2.scrollTop = top;
    showPreview();
    const rpImg = $('rp-img'); if(rpImg && rpFrame){ rpImg.src = rpFrame; rpImg.hidden = false; }
    const d = document.querySelector('#app .dlg');
    if(d && !d.contains(document.activeElement)){ const b = d.querySelector('.dlg-actions .btn:not([disabled])'); if(b) b.focus({preventScroll:true}); }
    else if(enter){ const t = $('scr-h'); if(t) t.focus({preventScroll:true}); } else restore(f);
    itipSync();
  }
  function patch(){
    const tpl = document.createElement('template');
    tpl.innerHTML = win(E, U, '');
    tpl.content.querySelectorAll('[data-r]').forEach(nuevo => {
      const actual = document.querySelector('#app [data-r="'+nuevo.dataset.r+'"]');
      if(actual && actual.innerHTML !== nuevo.innerHTML) actual.innerHTML = nuevo.innerHTML;
      if(actual && actual.className !== nuevo.className) actual.className = nuevo.className;
    });
  }
  function toast(kind, icon, text){
    U.toast = {kind:kind, icon:icon, text:text}; render();
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { U.toast = null; render(); }, 3800);
  }
  function actualizar(nuevo){
    const prev = E; E = nuevo;
    const devs = E.devices || [];
    if(!devs.some(d => d.id===U.sel)) U.sel = devs.length ? devs[0].id : null;
    if(E.screen!=='main') U.dlg = null;
    if(prev && prev.advanced && !E.advanced){ U.log.lines = {}; U.log.ultimo = 0; U.meters = {}; }
    const t = transition(prev, E);
    if(first || prev.screen!==E.screen){ first = false; if(E.pair) E.pair.fresh = false; render('enter'); }
    else if(t) toast(t.kind, t.icon, t.text);
    else if(structure(prev) !== structure(E)){
      if(E.pair && prev.pair && E.pair.code !== prev.pair.code && E.pair.code){ E.pair.fresh = true; }
      render();
      if(E.pair && E.pair.renewed && E.pair.code !== (prev.pair && prev.pair.code)) announce('Código nuevo');
    }
    else patch();
    if(E.upd && E.upd.updated && !U.updToast && E.screen==='main'){ U.updToast = true; toast('ok', 'check', 'Te Tengo Captura se actualizó a '+E.upd.updated); }
    if(E.pair && prev && prev.pair && prev.pair.left > 60 && E.pair.left <= 60 && E.pair.left > 0) announce('El código vence en 1 minuto');
  }
  function announce(text){ const a = $('pair-ann'); if(a){ a.textContent = ''; setTimeout(() => { a.textContent = text; }, 30); } }

  /* ---------- vista previa local de la cámara elegida (solo en esta PC) ---------- */
  function showPreview(){
    const img = $('pv-img'), fig = $('pv');
    if(!img || !fig) return;
    const ok = previewSrc && previewSrc.clave === fig.dataset.clave;
    if(ok){ img.src = previewSrc.src; img.hidden = false; fig.classList.add('live'); }
  }
  function pollPreview(){
    const fig = $('pv');
    if(!fig || U.tab !== 'camaras' || document.hidden){ previewSrc = null; return; }
    const clave = fig.dataset.clave, b = bridge();
    if(!b || !b.vistaPrevia) return;
    Promise.resolve(b.vistaPrevia(clave)).then(r => {
      const img = $('pv-img'), f = $('pv');
      if(!img || !f || f.dataset.clave !== clave) return;
      if(r && r.jpeg){ previewSrc = {clave:clave, src:'data:image/jpeg;base64,'+r.jpeg}; img.src = previewSrc.src; img.hidden = false; f.classList.add('live'); }
      else { previewSrc = null; img.hidden = true; f.classList.remove('live'); }
    }).catch(() => {});
  }
  preview = setInterval(pollPreview, 250);

  /* ---------- acciones ---------- */
  function call(name, arg){
    const b = bridge(); if(!b || !b[name]) return Promise.resolve(null);
    return Promise.resolve(arg===undefined ? b[name]() : Array.isArray(arg) ? b[name](...arg) : b[name](arg));
  }
  const ACT = {
    minimize(){ call('minimizar'); },
    close(){ call('cerrar'); },
    tab(el){ if(U.rp.open && el.dataset.arg!=='avanzado') ACT.replayClose(); U.tab = el.dataset.arg; render(); const t = $('tab-'+U.tab); if(t) t.focus({preventScroll:true}); if(U.tab==='avanzado') loadActs(); },
    toCams(){ U.tab = 'camaras'; render(); const t = $('tab-camaras'); if(t) t.focus({preventScroll:true}); },
    selCam(el){ U.sel = el.dataset.arg; previewSrc = null; U.pick = {room:null, otherOn:false, other:'', err:null}; render(); },
    advToggle(){
      const activar = !E.advanced;
      call('modoAvanzado', activar).then(r => {
        E.advanced = !!(r && r.on); U.adv.sub = E.advanced ? 'registro' : 'actividad'; U.acts = null;
        toast('ok', 'sliders', E.advanced ? 'Modo avanzado activado.' : 'Modo avanzado desactivado.');
        loadActs();
      });
    },
    advSub(el){ U.adv.sub = el.dataset.arg; render(); if(U.adv.sub==='actividad') loadActs(); pollAdv(); },
    advCam(el){ U.adv.cam = el.dataset.arg; U.log.open = null; render(); pollAdv(); },
    logFilter(el){ const k = el.dataset.arg; U.log.filters[k] = !U.log.filters[k]; render(); },
    logPause(){ const lg = U.log, cam = advCam(E, U); lg.paused = !lg.paused; lg.cut = cam ? (lg.lines[cam.id] || []).length : 0; render(); },
    techToggle(el){ const id = Number(el.dataset.arg); U.log.open = U.log.open===id ? null : id; render(); },
    copyTech(el){
      const id = Number(el.dataset.arg), cam = advCam(E, U), l = cam && (U.log.lines[cam.id] || []).find(x => x.id===id);
      if(!l) return;
      const hecho = () => toast('ok', 'copy', 'Línea copiada');
      try{ navigator.clipboard.writeText(l.x).then(hecho, () => { copiarTexto(l.x); hecho(); }); }catch(e){ copiarTexto(l.x); hecho(); }
    },
    actScope(el){ U.actScope = el.dataset.arg; render(); },
    diagOpen(el){ opener = el; U.dlg = 'diag'; U.diag = {step:'intro', nombre:''}; render(); call('nombreDiagnostico').then(n => { U.diag.nombre = n || ''; render(); }); },
    diagSave(){
      U.diag.step = 'busy'; render();
      call('exportarDiagnostico').then(r => {
        if(r && r.ok){ U.diag = {step:'done', nombre:r.nombre, ruta:r.ruta, tamano:tamano(r.tamano)}; }
        else if(r && r.cancelado){ U.diag.step = 'intro'; }
        else { U.diag.step = 'err'; }
        render();
      });
    },
    stMov(){ const a = E.store.ajustes; guardarAlmacen({movimientos: !a.movimientos}, !a.movimientos ? 'Guardamos los movimientos en esta PC.' : 'Dejamos de guardar movimientos. Los guardados se borran a su plazo.'); },
    stVid(el){ const a = E.store.ajustes; if(!a.video){ opener = el; U.dlg = 'video'; render(); return; } guardarAlmacen({video:false}, 'Dejamos de guardar video. El guardado se borra a su plazo.'); },
    videoOn(){ U.dlg = null; guardarAlmacen({video:true}, 'Guardamos video continuo solo en esta PC.'); if(opener) restore({act:'stVid'}); },
    stClip(){ const a = E.store.ajustes; guardarAlmacen({clips: !a.clips}, !a.clips ? 'Guardamos los clips de los avisos en esta PC.' : 'Dejamos de guardar clips. La familia los ve en la app.'); },
    ret(el){
      const [campo, v] = el.dataset.arg.split('|');
      if(campo==='limite_gb'){
        if(v==='otro'){ U.capOther = true; render(); const i = $('cap-val'); if(i) i.focus(); return; }
        U.capOther = false; guardarAlmacen({limite_gb: Number(v)}, 'Límite de espacio: '+v+' GB.'); return;
      }
      const valor = v==='null' ? null : Number(v), nombres = {dias_movimientos:'los movimientos', dias_video:'el video', dias_clips:'los clips'};
      guardarAlmacen({[campo]: valor}, valor==null ? 'No borraremos '+nombres[campo]+'.' : 'Guardaremos '+nombres[campo]+' '+dias(valor)+'.');
    },
    folderChange(){ call('cambiarCarpeta').then(r => { if(r && r.ok){ render(); } }); },
    revokeKeep(){ U.dlg = null; call('conservarMovimientos').then(() => toast('ok', 'check', 'Conservamos los movimientos. No guardaremos nuevos.')); },
    revokeWipe(){ U.dlg = null; call('borrarMovimientos').then(() => toast('ok', 'trash', 'Borramos los movimientos de esta PC.')); },
    diagShow(){ call('mostrarEnCarpeta', U.diag.ruta || ''); closeDlg(); },
    hereOn(){ U.here = true; U.pick = {room:null, otherOn:false, other:'', err:null}; render(); call('ambientes').then(r => { U.rooms = r || []; render(); }); },
    hereOff(){ U.here = false; render(); },
    pickRoom(el){ U.pick = {room:el.dataset.arg, otherOn:false, other:'', err:null}; render(); },
    pickOther(){ U.pick = {room:null, otherOn:true, other:'', err:null}; render(); const i = $('room-other'); if(i) i.focus(); },
    useCam(){
      const d = E.devices.find(x => x.id===U.sel); if(!d) return;
      const pk = U.pick, nombre = pk.otherOn ? pk.other.trim() : pk.room;
      if(!nombre){ U.pick.err = 'empty'; render(); return; }
      if(/^(ba(n|ñ)o|wc|ss\.?\s?hh\.?|servicios? higi(e|é)nicos?|aseo)$/i.test(nombre.trim())){ U.pick.err = 'bath'; render(); return; }
      const amb = (U.rooms || []).find(a => norm(a.nombre)===norm(nombre));
      U.busy = true; render();
      call('usarAqui', [d.uid || d.id, amb ? amb.id : null, amb ? null : nombre]).then(r => {
        U.busy = false;
        if(r && r.ok){ U.pick = {room:null, otherOn:false, other:'', err:null}; toast('ok', 'check', d.name+' cuida ahora '+ROOM_ART(nombre)); call('ambientes').then(x => { U.rooms = x || []; }); return; }
        const c = r && r.codigo;
        U.pick.err = c==='AMBIENTE_OCUPADO' ? 'dup' : c==='AMBIENTE_NO_PERMITIDO' ? 'bath' : c==='AMBIENTE_NOMBRE_VACIO' ? 'empty' : 'net';
        U.pick.errRoom = r && r.ambiente || nombre; U.pick.errPc = r && r.pc || E.pc.nombre; render();
      });
    },
    unuse(){
      const d = E.devices.find(x => x.id===U.sel); if(!d || !d.room) return;
      U.busy = true; render();
      call('dejarDeUsar', d.id).then(r => { U.busy = false; if(r && r.ok) toast('ok', 'check', d.name+' ya no cuida '+ROOM_ART(d.room)+'.'); else { U.pick.err = 'net'; render(); } });
    },
    toEstado(){ U.tab = 'estado'; call('irAEstado').then(() => call('estado')).then(s => { if(s) actualizar(s); }); },
    otherCode(){ call('otroCodigo').then(() => call('estado')).then(s => { if(s) actualizar(s); }); },
    pairAgain(){ call('vincularDeNuevo').then(() => call('estado')).then(s => { if(s) actualizar(s); }); },
    unlinkAsk(el){ opener = el; U.dlg = 'unlink'; U.unlinkWipe = false; render(); },
    dlgClose(){ closeDlg(); },
    unlinkDo(){
      U.busy = true; render();
      const wipe = U.unlinkWipe;
      call('desvincular', wipe).then(r => {
        U.busy = false; U.dlg = null; opener = null;
        if(r && r.ok){ U.tab = 'estado'; toast('ok', 'unlink', wipe ? 'PC desvinculada y datos borrados. La familia recibió un aviso.' : 'PC desvinculada. La familia recibió un aviso.'); call('estado').then(s => { if(s) actualizar(s); }); }
        else render();
      });
    },
    toAbout(){ if(U.rp.open) ACT.replayClose(); U.tab = 'avanzado'; U.here = false; U.adv.sub = 'acerca'; render(); const b = $('sub-acerca'); if(b) b.focus({preventScroll:true}); },
    updNotes(el){ opener = el; U.dlg = 'updNotes'; render(); },
    updGo(){
      U.dlg = null;
      call('descargarActualizacion').then(r => {
        if(r && r.pagina){
          if(E.upd && E.upd.os==='mac') U.dlg = 'updMac';
          toast('ok', 'link', 'Abrimos '+r.pagina+' en el navegador.');
        } else refrescar();
      });
    },
    updCancel(){ call('cancelarActualizacion').then(r => { const v = (r && r.version) || (E.upd && E.upd.ver) || ''; refrescar(); toast('ok', 'x', 'Descarga cancelada. Sigues con la versión '+v+'.'); }); },
    updCheck(){
      U.checking = true; render();
      call('buscarActualizaciones').then(r => {
        U.checking = false;
        if(!r || !r.ok) toast('warn', 'wifiOff', 'Sin internet. No pudimos buscar.');
        else if(!r.nueva) toast('ok', 'check', 'Tienes la última versión ('+r.version+').');
        refrescar();
      });
    },
    updAuto(){
      call('actualizarAutomaticamente', !E.upd.auto).then(r => {
        E.upd.auto = !!(r && r.on); U.acts = null;
        toast('ok', 'refresh', E.upd.auto ? 'Se actualizará sola a las 03:00, si no hay una alerta.' : 'Las actualizaciones esperan a que elijas «Descargar».');
      });
    },
    retryNow(){
      call('reintentarAhora').then(r => { if(r && !r.ok) toast('warn', 'wifiOff', 'Aún sin internet.'); });
    },
    rescan(el){
      el.classList.add('loading'); el.innerHTML = '<span class="spin"></span>Buscando cámaras conectadas…';
      call('buscarWebcam').then(r => {
        if(r && !r.ok){ const d = E.devices.find(x => !x.connected) || E.devices[0]; toast('warn', 'videoOff', d ? 'No encontramos la '+d.name+'. Revisa el cable USB.' : 'No encontramos cámaras'); }
        else { const n = E.devices.length; toast('ok', 'check', n+(n===1?' cámara conectada.':' cámaras conectadas.')); }
      });
    }
  };
  document.addEventListener('click', e => {
    const t = e.target.closest('[data-act]');
    if(t && ACT[t.dataset.act] && !t.disabled && t.getAttribute('aria-disabled') !== 'true'){ e.preventDefault(); ACT[t.dataset.act](t); }
  });
  function refrescar(){ call('estado').then(s => { if(s) actualizar(s); }); }
  /* actions started outside the page (the tray menu): «Descargar la versión X», «Buscar actualizaciones» */
  function accion(nombre){
    if(!E || E.screen!=='main') return;
    if(nombre==='updCheck'){ ACT.toAbout(); ACT.updCheck(); }
    else if(nombre==='updGo') ACT.updGo();
  }
  function tamano(b){ b = Number(b) || 0; return b >= 1e6 ? num(b/1e6, 1)+' MB' : Math.max(1, Math.round(b/1e3))+' KB'; }
  function copiarTexto(texto){ const t = document.createElement('textarea'); t.value = texto; document.body.appendChild(t); t.select(); try{ document.execCommand('copy'); }catch(e){} t.remove(); }
  function loadActs(){ call('actividad').then(r => { U.acts = r || []; if(U.tab==='avanzado') render(); }); }
  /* the advanced mode: new log lines and the meters twice per second, only while shown */
  function pollAdv(){
    if(!E || E.screen!=='main' || U.tab!=='avanzado' || !E.advanced || document.hidden) return;
    const cam = advCam(E, U); if(!cam) return;
    const sub = advSub(E, U);
    if(sub==='registro'){
      const lg = U.log, mias = lg.lines[cam.id] || [], ultimo = mias.length ? mias[mias.length-1].id : 0;
      call('registro', [cam.id, ultimo]).then(nuevas => {
        if(!nuevas || !nuevas.length) return;
        lg.lines[cam.id] = mias.concat(nuevas).slice(-2000);
        const box = $('logbox'), abajo = !box || box.scrollHeight - box.scrollTop - box.clientHeight < 40;
        renderAdv();
        const b = $('logbox'); if(b && abajo && !lg.paused) b.scrollTop = b.scrollHeight;
        const ev = nuevas.filter(l => l.k==='evento').pop();
        if(ev && !lg.paused){ const a = $('log-ann'); if(a) a.textContent = ev.m; }
      });
    } else if(sub==='medidores'){
      call('medidores', cam.id).then(m => { U.meters[cam.id] = m; const g = $('meters'); if(g){ const f = snap(); g.outerHTML = metersView(E, U, cam); if(f && f.tip!=null) restore(f); itipSync(); } });
    }
  }
  function renderAdv(){
    const cam = advCam(E, U), box = $('logbox');
    if(!cam || !box){ render(); return; }
    if(U.log.paused){ const n = $('log-new'), all = U.log.lines[cam.id] || [], k = all.length - U.log.cut; if(n) n.textContent = k+' '+(k===1?'línea nueva':'líneas nuevas'); return; }
    ITIP.quiet = Date.now() + 200;
    const top = box.scrollTop; box.innerHTML = logRows(E, U, cam); box.scrollTop = top;
    LOG_K.forEach(k => { const c = $('cnt-'+k[0]); if(c) c.textContent = (U.log.lines[cam.id] || []).filter(l => l.k===k[0]).length; });
  }
  setInterval(pollAdv, 500);
  function guardarAlmacen(cambios, texto){
    call('cambiarAlmacenamiento', cambios).then(r => { if(r && r.ok){ Object.assign(E.store.ajustes, cambios); toast('ok', 'check', texto); } else render(); });
  }
  function closeDlg(){ U.dlg = null; render(); if(opener && document.body.contains(opener)) opener.focus({preventScroll:true}); else restore({act:'unlinkAsk'}); opener = null; }
  document.addEventListener('change', e => {
    if(e.target && e.target.id==='cap-val' && Number(e.target.value) > 0){ U.capOther = false; guardarAlmacen({limite_gb: Number(e.target.value)}, 'Límite de espacio: '+e.target.value+' GB.'); return; } if(e.target && e.target.id==='unlink-wipe') U.unlinkWipe = e.target.checked; });
  document.addEventListener('input', e => {
    if(e.target && e.target.id==='log-q'){ U.log.q = e.target.value; renderAdv(); return; }
    if(e.target && e.target.id==='cap-val'){ U.capVal = e.target.value; return; } if(e.target && e.target.id==='room-other'){ U.pick.other = e.target.value; if(U.pick.err){ U.pick.err = null; } const b = document.querySelector('#app [data-act="useCam"]'); if(b) b.disabled = !e.target.value.trim(); } });
  document.addEventListener('toggle', e => { const d = e.target; if(d && d.matches && d.matches('details[data-k]')) U.open[d.dataset.k] = d.open; }, true);
  document.addEventListener('keydown', e => {
    const t = e.target, role = t.getAttribute && t.getAttribute('role');
    if(e.key==='Enter' && t.id==='room-other'){ e.preventDefault(); ACT.useCam(); return; }
    if(U.dlg){
      if(e.key==='Escape'){ e.preventDefault(); if(!(U.dlg==='diag' && U.diag.step==='busy')) closeDlg(); return; }
      if(e.key==='Tab'){
        const d = document.querySelector('#app .dlg'); if(!d) return;
        const f = [...d.querySelectorAll('button:not([disabled]),input,select,[tabindex="0"]')];
        if(!f.length) return;
        if(e.shiftKey && document.activeElement===f[0]){ e.preventDefault(); f[f.length-1].focus(); }
        else if(!e.shiftKey && document.activeElement===f[f.length-1]){ e.preventDefault(); f[0].focus(); }
        else if(!d.contains(document.activeElement)){ e.preventDefault(); f[0].focus(); }
        return;
      }
    }
    if((role==='tab' || role==='radio') && /^Arrow(Left|Right|Up|Down)$/.test(e.key)){
      const group = t.closest('[role="tablist"],[role="radiogroup"]'); if(!group) return;
      const items = [...group.querySelectorAll('[role="tab"],[role="radio"]')].filter(x => !x.disabled && x.getAttribute('aria-disabled')!=='true');
      const i = items.indexOf(t), d = /Right|Down/.test(e.key) ? 1 : -1, n = items[(i+d+items.length) % items.length];
      if(n){ e.preventDefault(); n.click(); const again = n.id ? $(n.id) : document.querySelector('#app [data-act="'+n.dataset.act+'"][data-arg="'+CSS.escape(n.dataset.arg||'')+'"]'); if(again) again.focus(); }
    }
  });

  /* ---------- Ver qué pasó: datos, reproducción y búsqueda (proto.js) ---------- */
  const REDUCED = global.matchMedia && global.matchMedia('(prefers-reduced-motion: reduce)').matches;
  let rpTimer = 0, rpLast = 0, rpGapShown = null, rpPidiendo = false, rpVideoPidiendo = false, rpVideoT = null, rpDrag = false, rpFrame = null;
  function isoHoy(){ const d = new Date(); return d.getFullYear()+'-'+pad2(d.getMonth()+1)+'-'+pad2(d.getDate()); }
  function rpEn(dia, hora){ const [y, m, d] = dia.split('-').map(Number), [h, mi] = hora.split(':').map(Number); return new Date(y, m-1, d, h, mi, 0).getTime(); }
  function rpFit(t){
    const rp = U.rp, span = rpSpan(rp), ahora = Date.now();
    if(rp.w0==null || t < rp.w0 || t > rp.w0 + span){ rp.w0 = Math.min(Math.floor((t - span*.6)/60000)*60000, Math.ceil(ahora/60000)*60000 - span); return true; }
    return false;
  }
  function rpCargarVentana(){
    const rp = U.rp, cam = rpCamInfo(rp); if(!cam) return Promise.resolve();
    const desde = rp.w0, hasta = rp.w0 + rpSpan(rp);
    return call('repeticionVentana', [cam.id, desde, hasta]).then(w => { if(w && rp.w0===desde){ rp.win = w; } });
  }
  function rpCargarPoses(t){
    const rp = U.rp, cam = rpCamInfo(rp), p = rp.poses;
    if(!cam || rpPidiendo || (p && p.cam===cam.id && t >= p.desde && t <= p.hasta - 15000)) return;
    rpPidiendo = true;
    const desde = t - 10000, hasta = t + 110000;
    call('repeticionPoses', [cam.id, desde, hasta]).then(r => {
      rpPidiendo = false;
      if(r && r.t){ rp.poses = Object.assign(r, {cam:cam.id, desde:desde, hasta:hasta}); rpPintar(); }
    }, () => { rpPidiendo = false; });
  }
  function rpVideo(t){
    const rp = U.rp, cam = rpCamInfo(rp), img = $('rp-img');
    if(!img || !cam || rpVideoPidiendo || (rpVideoT!=null && Math.abs(rpVideoT - t) < 100)) return;
    rpVideoPidiendo = true;
    call('repeticionVideo', [cam.id, Math.round(t)]).then(r => {
      rpVideoPidiendo = false; rpVideoT = t;
      const i = $('rp-img'); if(!i) return;
      rpFrame = r && r.jpeg ? 'data:image/jpeg;base64,'+r.jpeg : null;
      if(rpFrame){ i.src = rpFrame; i.hidden = false; } else i.hidden = true;
    }, () => { rpVideoPidiendo = false; });
  }
  function rpPintar(){
    const rp = U.rp, fig = $('rp-fig'); if(!fig) return;
    const t = REDUCED ? Math.floor(rp.t/1000)*1000 : rp.t, p = rpPhase(rp, t), a = rp.w0, b = a + rpSpan(rp);
    fig.innerHTML = rpFig(rp, t);
    const ph = $('rp-phase'); if(ph && ph.dataset.l!==p.label){ ph.className = 'rp-phase '+p.tone; ph.innerHTML = ic(p.i)+esc(p.label); ph.dataset.l = p.label; }
    $('rp-clock').textContent = hmsMs(t); $('rp-time').textContent = hmsMs(t);
    $('tl-head').style.left = Math.max(0, Math.min(100, (t-a)/(b-a)*100))+'%';
    const tr = $('tl-track'); tr.setAttribute('aria-valuenow', Math.round(t/1000)); tr.setAttribute('aria-valuetext', rpValText(rp, t));
    rpCargarPoses(t);
    if(rp.video && rp.win && rp.win.video) rpVideo(t);
  }
  function rpStop(){ U.rp.playing = false; clearInterval(rpTimer); rpTimer = 0; rpLast = 0; }
  function rpStart(){
    const rp = U.rp, fin = rp.w0 + rpSpan(rp); if(rp.t >= fin - 500) rp.t = rp.w0;
    rp.playing = true; rp.visto = true; rpLast = performance.now(); rpGapShown = null; clearInterval(rpTimer); rpTimer = setInterval(rpPaso, REDUCED ? 250 : 40);
  }
  /* the replay clock follows real time (not the frames painted); stretches without data are skipped (CA-39.5) */
  function rpPaso(){
    const rp = U.rp; if(!rp.playing || !rp.open) return rpStop();
    const ahora = performance.now(), dt = (ahora - rpLast)*rp.speed; rpLast = ahora;
    let t = rp.t + dt;
    const g = rpGap(rp, t);
    if(g){ t = g.b; if(rpGapShown!==g){ rpGapShown = g; rp.t = t; toast('warn', 'clock', 'Sin datos de '+hmMs(g.a)+' a '+hmMs(g.b)+' · '+g.motivo); } }
    const fin = rp.w0 + rpSpan(rp);
    if(t >= fin){ rp.t = fin; rpStop(); render(); return; }
    rp.t = t; rpPintar();
  }
  /* CA-39.3: playing or moving along the timeline is what the access log records */
  function rpBuscar(t){ const rp = U.rp, a = rp.w0, b = a + rpSpan(rp); rp.visto = true; rp.t = Math.max(a, Math.min(b, t)); rpPintar(); }
  function rpIr(t){
    const rp = U.rp; rp.visto = true;
    if(rpFit(t)){ rp.t = t; rp.win = null; render(); rpCargarVentana().then(() => { render(); rpPintar(); }); }
    else { rp.t = t; render(); rpPintar(); }
  }
  /* the previous or next event, also outside the window (up to an hour away) */
  function rpEvento(dir){
    const rp = U.rp, cam = rpCamInfo(rp), t = rp.t;
    const elegir = evs => dir < 0 ? evs.filter(x => x.t < t - 600).pop() : evs.find(x => x.t > t + 600);
    const e = elegir((rp.win && rp.win.eventos) || []);
    if(e){ rpIr(e.t); return; }
    const vacio = () => toast('ok', 'info', dir < 0 ? 'No hay eventos antes.' : 'No hay más eventos.');
    if(!cam){ vacio(); return; }
    call('repeticionVentana', dir < 0 ? [cam.id, t - 3600000, t] : [cam.id, t, t + 3600000]).then(w => {
      const otro = w && elegir(w.eventos || []); if(otro) rpIr(otro.t); else vacio();
    });
  }
  function rpAbrirMomento(){
    const rp = U.rp, cam = rpCamInfo(rp);
    if(!cam){ render(); return; }
    let t = rpEn(rp.day, rp.hour); t = Math.min(t, Date.now());
    rpStop(); rp.state = cam.desdeMs!=null && t < cam.desdeMs - 60000 ? 'old' : null;  // CA-39.4
    if(cam.desdeMs!=null) t = Math.max(t, cam.desdeMs);
    rp.w0 = null; rp.win = null; rp.poses = null; rpVideoT = null; rpFrame = null;
    if(rp.state){ render(); return; }
    rpFit(t); rp.t = t; render();
    rpCargarVentana().then(() => { render(); rpPintar(); });
  }
  Object.assign(ACT, {
    replayOpen(){
      const ahora = new Date(Date.now() - 15*60000);
      U.rp = {open:true, info:null, cam:null, day:isoHoy(), hour:pad2(ahora.getHours())+':'+pad2(ahora.getMinutes()), zoom:'10', w0:null, t:Date.now(), playing:false, speed:1, video:false, state:null, win:null, poses:null, abierta:Date.now(), visto:false};
      render(true);
      call('repeticion').then(info => {
        const rp = U.rp; rp.info = info || {permitida:false, camaras:[]};
        const cs = rp.info.camaras, con = cs.find(c => c.desde) || cs[0];
        rp.cam = con ? con.id : null;
        if(con && con.dias.length && !con.dias.some(d => d.valor===rp.day)){ rp.day = con.dias[0].valor; rp.hour = '12:00'; }
        if(con && con.hastaMs!=null && rpEn(rp.day, rp.hour) > con.hastaMs){ const d = new Date(con.hastaMs - 5*60000); rp.day = d.getFullYear()+'-'+pad2(d.getMonth()+1)+'-'+pad2(d.getDate()); rp.hour = pad2(d.getHours())+':'+pad2(d.getMinutes()); }
        if(con && con.desdeMs!=null && rpEn(rp.day, rp.hour) < con.desdeMs){ const d = new Date(con.desdeMs); rp.day = d.getFullYear()+'-'+pad2(d.getMonth()+1)+'-'+pad2(d.getDate()); rp.hour = pad2(d.getHours())+':'+pad2(d.getMinutes()); }
        if(rp.info.permitida) rpAbrirMomento(); else render();
      });
    },
    replayClose(){
      const rp = U.rp, cam = rpCamInfo(rp); rpStop();
      U.rp = Object.assign({}, rp, {open:false});
      render();
      if(rp.visto && cam){
        call('cerrarRepeticion', [cam.id, rp.w0, rp.w0 + rpSpan(rp), (Date.now() - rp.abierta)/1000]).then(() => toast('ok', 'eye', 'Acceso registrado'));
      }
      const b = document.querySelector('#app [data-act="replayOpen"]'); if(b) b.focus({preventScroll:true});
    },
    rpPlay(){ if(U.rp.playing){ rpStop(); render(); } else { rpStart(); render(); } },
    rpPrev(){ rpEvento(-1); },
    rpNext(){ rpEvento(1); },
    rpSpeed(){ const rp = U.rp; rp.speed = SPEEDS[(SPEEDS.indexOf(rp.speed)+1) % SPEEDS.length]; render(); },
    rpZoom(el){ const rp = U.rp, z = el.dataset.arg; if(rp.zoom===z) return; rp.zoom = z; rp.w0 = null; rpFit(rp.t); rp.win = null; render(); rpCargarVentana().then(() => { render(); rpPintar(); }); },
    rpSeek(el){ rpIr(Number(el.dataset.arg)); },
    rpCam(el){ const rp = U.rp; rp.cam = el.dataset.arg; const c = rpCamInfo(rp); if(c && c.dias.length && !c.dias.some(d => d.valor===rp.day)) rp.day = c.dias[0].valor; rpAbrirMomento(); },
    rpQuick(el){
      const rp = U.rp, k = el.dataset.arg, d = new Date(Date.now() - (k==='m15' ? 15 : k==='h1' ? 60 : 0)*60000);
      rp.day = isoHoy(); rp.hour = k==='h7' ? '07:00' : pad2(d.getHours())+':'+pad2(d.getMinutes()); rpAbrirMomento();
    },
    rpGo(){
      const i = $('rp-hour'), v = i ? i.value : U.rp.hour, m = /^(\d{1,2}):(\d{2})$/.exec(String(v).trim());
      if(!m || +m[1] > 23 || +m[2] > 59){ toast('warn', 'clock', 'Escribe la hora así: 10:40.'); return; }
      U.rp.hour = pad2(+m[1])+':'+m[2]; rpAbrirMomento();
    },
    rpVideo(){ const rp = U.rp; rp.video = !rp.video; rpVideoT = null; render(); rpPintar(); }
  });
  document.addEventListener('change', e => { if(e.target && e.target.id==='rp-day' && U.rp){ U.rp.day = e.target.value; rpAbrirMomento(); } });
  function rpX(tr, x){ const r = tr.getBoundingClientRect(), a = U.rp.w0; rpBuscar(a + Math.max(0, Math.min(1, (x-r.left)/r.width))*rpSpan(U.rp)); }
  document.addEventListener('pointerdown', e => {
    const tr = e.target.closest && e.target.closest('#tl-track'); if(!tr || e.target.closest('.tl-m')) return;
    rpDrag = true; try{ tr.setPointerCapture(e.pointerId); }catch(err){} rpX(tr, e.clientX);
  });
  document.addEventListener('pointermove', e => { if(rpDrag){ const tr = $('tl-track'); if(tr) rpX(tr, e.clientX); } });
  document.addEventListener('pointerup', () => { rpDrag = false; });
  document.addEventListener('keydown', e => {
    const t = e.target; if(!U.rp || !U.rp.open) return;
    if(e.key==='Enter' && t.id==='rp-hour'){ e.preventDefault(); ACT.rpGo(); return; }
    if(t.id==='tl-track'){
      const rp = U.rp, big = e.shiftKey ? 10 : 1;
      const k = {ArrowRight:big, ArrowUp:big, ArrowLeft:-big, ArrowDown:-big, PageUp:60, PageDown:-60}[e.key];
      if(k!=null){ e.preventDefault(); rpBuscar(rp.t + k*1000); return; }
      if(e.key==='Home'){ e.preventDefault(); rpBuscar(rp.w0); return; }
      if(e.key==='End'){ e.preventDefault(); rpBuscar(rp.w0 + rpSpan(rp)); return; }
      if(e.key===' '){ e.preventDefault(); ACT.rpPlay(); }
    }
  });

  /* ---------- arranque: Python drives the progress with ttg.arranque(pct, paso) ---------- */
  function arranque(pct, step, version){
    const bar = document.querySelector('.boot-bar'); if(!bar) return;
    if(version != null) document.querySelector('.boot-v').textContent = 'Versión '+version;
    bar.querySelector('i').style.transform = 'scaleX('+(pct/100)+')';
    bar.setAttribute('aria-valuenow', pct);
    const txt = $('boot-st'); if(step != null && txt.textContent !== BOOT_STEPS[step]) txt.textContent = BOOT_STEPS[step];
  }
  function arranqueFin(){ const b = document.querySelector('.boot'); if(b) b.classList.add('out'); }

  global.ttg = { actualizar, arranque, arranqueFin, accion };
  if(document.body.dataset.pagina === 'arranque'){
    $('app').innerHTML = bootWin({play:true, pct:0, step:0});
  } else {
    global.addEventListener('pywebviewready', () => { call('estado').then(s => { if(s) actualizar(s); }); });
  }
})(typeof window !== 'undefined' ? window : globalThis);
