/* ================= Te Tengo Captura · ventana =================
   Port of the desktop prototype (docs/references/desktop-prototype/src/core.js and proto.js):
   icons, brand kit (two figures hugging), room illustrations, title bar, «Vincular esta PC»
   (QR and code), the result screens (vinculada, rechazada, quitada), the tab bar
   (Estado · Cámaras) and their panels, the dialogs, in-window notices and the splash.
   Every state-dependent text comes from Python (te_tengo_captura/estado.py) through
   ttg.actualizar(); this file renders it, keeps what only the window knows (the open tab, the
   selected camera, the folded sections) and calls the bridge window.pywebview.api:
   estado(), minimizar(), cerrar(), buscarWebcam(), reintentarAhora(), vistaPrevia(clave),
   otroCodigo(), vincularDeNuevo(), irAEstado(), desvincular(borrarDatos). */
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
    if(p.fase==='sin_internet') return off('wifiOff', 'Sin internet', 'Conecta esta PC a internet para vincularla.');
    if(p.fase==='sin_servidor') return off('cloud', 'No pudimos conectar con Te Tengo', 'Puede ser un problema nuestro: no tienes que hacer nada.');
    if(!p.code || !p.qr) return '<div class="card pair-card" role="status"><div class="pane-scan"><span class="spin"></span></div></div>';
    const spoken = p.code.replace('-', '').split('').join(' ').replace(/^(\S \S \S \S) /, '$1, guion, ');
    return '<div class="card pair-card'+(p.fresh?' fresh':'')+'">'+
      (p.renewed ? '<p class="renew">'+ic('refresh')+'Código nuevo · el anterior venció</p>' : '')+
      '<div class="qrwrap">'+qrSVG(p.qr)+'<span class="qr-logo" aria-hidden="true">'+LOGO+'</span></div>'+
      '<p class="t-meta">¿No puedes escanearlo? Escribe este código en la app:</p>'+
      '<p class="code-big"><span aria-hidden="true">'+esc(p.code)+'</span><span class="sr">'+esc(spoken)+'</span></p>'+
      '<p class="pair-url">'+esc(p.url)+'</p>'+
      '<p class="pair-left'+(p.left<=60?' low':'')+'" data-r="pl">'+ic('clock')+'Vence en <span class="mono" id="pair-left">'+mmss(p.left)+'</span></p>'+
      '<span class="sr" role="status" id="pair-ann">'+(p.renewed?'Código nuevo':'')+'</span></div>';
  }
  function scrVincular(E, U, enter){
    const p = E.pair, ok = p.fase==='codigo' || p.fase==='pidiendo';
    return sec('pair', enter,
      (p.re90 ? '<div class="notice warn band90" role="status">'+ic('clock')+'<div><b>Esta PC estuvo más de 90 días sin conexión</b><span>Vuelve a vincularla con tu celular.</span></div></div>' : '')+
      '<div class="pair-grid"><div class="pair-l">'+
        '<h1 class="t-title" id="scr-h" tabindex="-1">Vincula esta PC con tu celular</h1>'+
        '<ol class="steps2"><li><span class="n">1</span><span>Abre la app Te Tengo en tu celular</span></li>'+
        '<li><span class="n">2</span><span class="path">Ajustes'+ic('chevR')+'PCs y cámaras'+ic('chevR')+'Agregar PC</span></li>'+
        '<li><span class="n">3</span><span>Escanea este código</span></li></ol>'+
        '<p class="pcname"><span class="ci">'+ic('monitor')+'</span><span>Esta PC se llama <b>'+esc(E.pcname)+'</b></span></p>'+
        det(U, 'help', 'phelp', ic('mobile')+'¿El celular muestra un error?',
          '<ul class="helplist"><li><b>«Este código ya venció o ya se usó»</b>Escanea otra vez: esta PC ya muestra un código nuevo.</li>'+
          '<li><b>«Demasiados intentos»</b>Espera hasta la hora que indica el celular y vuelve a intentarlo. Esta PC seguirá mostrando un código válido.</li></ul>')+
      '</div>'+pairCard(E)+'</div>'+
      '<div class="pair-foot">'+(ok ? '<p class="wait2" role="status"><span class="spin"></span>Esperando la aprobación en el celular…</p>'
                                     : '<p class="wait2 stop"><span class="spin"></span>El código aparece cuando haya conexión</p>')+'</div>');
  }
  /* la PC informa las webcams que detectó; la familia las asigna desde la app */
  function foundList(E){
    const devs = E.devices;
    if(!devs.length) return '<div class="notice warn">'+ic('cam')+'<div><b>No encontramos cámaras en esta PC</b><span>Conecta una webcam por USB y pulsa Buscar de nuevo.</span></div></div>';
    return '<div class="found"><p class="found-h">'+ic('usb')+'<b>Detectamos '+devs.length+(devs.length===1?' cámara':' cámaras')+'</b><span>La familia las ve en la app con su nombre.</span></p>'+
      '<ul class="found-l">'+devs.map(d => '<li><span class="thumb art'+(!d.connected?' dim':'')+'">'+roomSVG(d.room || '')+'</span><span class="grow"><b>'+esc(d.name)+'</b>'+devTag(d)+'</span></li>').join('')+'</ul></div>';
  }
  function scrVinculada(E, U, enter){
    const kept = E.cams.length;
    return sec('', enter, '<div class="result linked"><span class="ok-badge">'+ic('check')+'</span>'+
      '<h1 class="t-title" id="scr-h" tabindex="-1">Esta PC quedó vinculada a la casa de '+esc(E.home.who)+'</h1>'+
      '<p class="t-lead">Aprobada por '+esc(E.linkedBy || '')+' desde su celular a las <span class="mono">'+esc(E.linkedAt)+'</span> · Esta PC: <b>'+esc(E.pc.nombre)+'</b></p>'+
      (kept ? '<div class="notice ok next">'+ic('check')+'<div><b>Las cámaras siguen en su habitación</b><span>'+esc(listY(E.cams.map(c => c.room)))+'. Se cambian desde la app Te Tengo, en tu celular.</span></div></div>'
            : '<div class="notice info next">'+ic('mobile')+'<div><b>Listo. Ahora elige las cámaras desde la app Te Tengo, en tu celular.</b><span class="path">Ajustes'+ic('chevR')+'PCs y cámaras'+ic('chevR')+esc(E.pc.nombre)+' · esta PC se actualiza sola.</span></div></div>')+
      foundList(E)+
      (!E.consent ? '<div class="notice warn">'+ic('doc')+'<div><b>Falta el consentimiento de '+esc(E.home.first)+'</b><span>Las cámaras no enviarán nada hasta que la familia lo registre en la app.</span></div></div>' : '')+
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
      '<h1 class="t-title" id="scr-h" tabindex="-1">'+(E.who ? 'Esta PC se quitó de la casa de '+esc(E.who) : 'Esta PC se quitó de la vivienda')+'</h1>'+
      '<p class="t-lead">La familia la quitó desde la app a las <span class="mono">'+esc(E.at)+'</span>. Ya no usa las cámaras.</p>'+
      '<div class="actions"><button class="btn btn-primary btn-lg" data-act="pairAgain">'+ic('link')+'Vincular de nuevo</button></div></div>');
  }

  /* ---------- barra de pestañas ---------- */
  function tabs(E){ return [['estado','pulse','Estado'], ['camaras','cam','Cámaras']]; }
  function tabbar(E, U){
    const t = x => '<button class="tab'+(U.tab===x[0]?' sel':'')+'" role="tab" id="tab-'+x[0]+'" aria-selected="'+(U.tab===x[0])+'" aria-controls="panel" tabindex="'+(U.tab===x[0]?0:-1)+'" data-act="tab" data-arg="'+x[0]+'">'+ic(x[1])+'<span>'+x[2]+'</span></button>';
    return '<nav class="tabbar" aria-label="Te Tengo Captura"><div class="tabs" role="tablist" aria-label="Secciones">'+tabs(E).map(t).join('')+'</div>'+
      '<span class="tb-pc">'+ic('monitor')+'<span>Esta PC: <b>'+esc(E.pc.nombre)+'</b></span></span></nav>';
  }
  function scrMain(E, U, enter){
    const tab = tabs(E).some(x => x[0]===U.tab) ? U.tab : 'estado';
    const panel = tab==='camaras' ? panelCamaras(E, U) : panelEstado(E, U);
    return sec('main', enter, tabbar(E, Object.assign({}, U, {tab:tab}))+'<div class="panel '+tab+'" id="panel" role="tabpanel" aria-labelledby="tab-'+tab+'">'+panel+'</div>');
  }

  /* ---------- Estado: el resumen y una fila por cámara ---------- */
  function health(E){
    const h = E.health, a = h.accion;
    const btn = a ? '<button class="btn btn-secondary btn-sm" data-act="'+a.act+'">'+ic(a.icono)+esc(a.texto)+'</button>' : '';
    return '<div class="health '+h.clase+'" role="status"><span class="st '+h.k+'">'+ic(h.icono)+'</span><div class="grow"><b>'+h.titulo_html+'</b><span data-r="hd">'+h.detalle_html+'</span></div>'+btn+'</div>';
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
  function panelEstado(E, U){
    const list = E.cams.length ? '<ul class="crows" aria-label="Cámaras de esta PC">'+E.cams.map(camRow).join('')+'</ul>' : '';
    return '<header class="cam-head"><div><h1 class="t-title" id="scr-h" tabindex="-1">Vivienda de '+esc(E.home.who)+'</h1>'+(E.home.addr ? '<p class="t-meta mt4">'+ic('home')+esc(E.home.addr)+'</p>' : '')+'</div></header>'+
      health(E)+list+
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
      '<button class="btn btn-danger-ghost btn-xs" data-act="unlinkAsk">'+ic('unlink')+'Desvincular esta PC</button></div>';
  }
  function selDev(E, U){ return E.devices.find(d => d.id===U.sel) || E.devices[0] || null; }
  function camInfo(E, U, d){
    if(!d.connected) return '<div class="cpane"><div class="pane-empty" role="status">'+ic('videoOff')+'<h2 class="t-h2">No responde: revisa el cable USB</h2>'+
      '<p class="t-small">'+(d.room ? esc(d.room)+' sigue asignada a esta cámara. ' : '')+'Conéctala y pulsa Buscar de nuevo.</p><button class="btn btn-secondary" data-act="rescan">'+ic('refresh')+'Buscar de nuevo</button></div></div>';
    if(d.busy) return '<div class="cpane"><div class="pane-empty" role="status">'+ic('warn')+'<h2 class="t-h2">Otro programa usa esta cámara</h2>'+
      '<p class="t-small">Ciérralo y pulsa Buscar de nuevo.</p><button class="btn btn-secondary" data-act="rescan">'+ic('refresh')+'Buscar de nuevo</button></div></div>';
    const by = d.room ? (d.by==='pc' ? 'Elegida en esta PC' : d.by==='app' ? 'La eligió la familia en la app' : 'El nombre se cambia en la app Te Tengo') : 'Se elige en la app';
    return '<div class="cpane info"><figure class="pv2 art" id="pv" data-clave="'+esc(d.id)+'">'+roomSVG(d.room || '')+'<img class="pv-img" id="pv-img" alt="" hidden>'+
      '<figcaption class="pv-tag">'+ic('eye')+'Vista previa · '+esc(d.name)+'</figcaption><span class="pv-lock">'+ic('lock')+'Solo se ve en esta PC</span></figure>'+
      '<dl class="cinfo"><div><dt>Habitación</dt><dd><b>'+(d.room ? esc(d.room) : 'Sin usar')+'</b><span>'+by+'</span></dd></div>'+
      '<div><dt>Conexión</dt><dd><b class="ok">'+ic('check')+'Conectada</b><span>'+(d.new ? 'Nueva · por USB' : 'Por USB')+'</span></dd></div></dl>'+
      '<p class="help-l">'+ic('eye')+'Usa la vista previa para revisar el encuadre.</p>'+
      (E.cams.length >= 3 ? '<p class="help-l">'+ic('info')+'Si la detección va lenta, pasa alguna cámara a otra PC.</p>' : '')+'</div>';
  }
  function panelCamaras(E, U){
    const devs = E.devices, any = E.cams.length;
    const meta = !devs.length || any ? 'Las habitaciones se eligen en la app.'
      : 'Detectamos '+devs.length+(devs.length===1?' cámara':' cámaras')+'. Elígelas en la app.';
    const head = '<header class="p-head"><div><h1 class="t-title" id="scr-h" tabindex="-1">Cámaras de esta PC</h1><p class="t-meta">'+meta+'</p></div></header>';
    if(!devs.length) return head+'<div class="card empty-big" role="status"><span class="ci lg">'+ic('cam')+'</span><h2 class="t-h2">No encontramos cámaras</h2>'+
      '<p class="t-small">Conecta una webcam por USB.</p><button class="btn btn-secondary" data-act="rescan">'+ic('refresh')+'Buscar de nuevo</button></div>'+thisPc(E);
    const sel = selDev(E, U);
    const rows = devs.map(d => '<button class="cpick'+(!d.connected?' lost':'')+'" role="radio" aria-checked="'+(d===sel)+'" tabindex="'+(d===sel?0:-1)+'" data-act="selCam" data-arg="'+esc(d.id)+'">'+
      '<span class="thumb art'+(!d.connected||d.busy?' dim':'')+'">'+roomSVG(d.room || '')+'</span><span class="grow"><b>'+esc(d.name)+'</b>'+devTag(d)+'</span></button>').join('');
    return head+'<div class="camgrid"><div class="clist"><p class="grp-l" id="g-cams">Cámaras conectadas</p><div class="clist-rows" role="radiogroup" aria-labelledby="g-cams">'+rows+'</div>'+
      '<div class="clist-tools"><button class="btn btn-ghost btn-sm" data-act="rescan">'+ic('refresh')+'Buscar de nuevo</button></div>'+thisPc(E)+'</div>'+camInfo(E, U, sel)+'</div>';
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
        (rooms.length ? 'Dejaremos de detectar caídas en '+esc(listY(rooms))+'. ' : '')+'Esta PC borrará su acceso y la familia recibirá un aviso.',
        '<label class="checkrow"><input type="checkbox" id="unlink-wipe"'+(U.unlinkWipe?' checked':'')+'><span>Borrar también los datos guardados en esta PC ('+num1(gb)+' GB)<span>Movimientos, video y clips de la carpeta de Te Tengo.</span></span></label>',
        '<button class="btn btn-secondary" data-act="dlgClose">Cancelar</button><button class="btn btn-danger" data-act="unlinkDo"'+(U.busy?' disabled':'')+'>'+ic('unlink')+'Desvincular</button>');
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
  const BOOT_STEPS = ['Iniciando…', 'Abriendo las cámaras…', 'Conectando con Te Tengo…'];
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
    if(!prev.online && E.online) return {kind:'ok', icon:'check', text:'Volvió internet. Avisos enviados.'};
    if(!prev.consent && E.consent) return {kind:'ok', icon:'check', text:'Consentimiento registrado en la app.'};
    return null;
  }
  /* What forces a full render; the countdown in the summary is only patched in place. */
  function structure(E){
    const o = Object.assign({}, E, {retry:0});
    if(E.health) o.health = Object.assign({}, E.health, {detalle_html:''});
    if(E.pair) o.pair = Object.assign({}, E.pair, {left:0, retry:0});
    return JSON.stringify(o);
  }

  const api = { ic, esc, roomSVG, titlebar, tabbar, health, camRow, panelEstado, panelCamaras, win, transition, structure, bootWin, BOOT_STEPS, listY, ROOM_ART, appIcon, LOGO, symbolSVG, mmss };

  /* ---------- DOM: render with focus, folded sections and scroll preserved ---------- */
  if(typeof document === 'undefined'){ if(typeof module !== 'undefined') module.exports = api; return; }

  const $ = id => document.getElementById(id);
  let E = null, first = true, toastTimer = null, preview = null, previewSrc = null;
  const U = {tab:'estado', sel:null, open:{}, toast:null, dlg:null, unlinkWipe:false, busy:false};
  let opener = null;
  const bridge = () => (global.pywebview && global.pywebview.api) || null;

  function snap(){
    const a = document.activeElement;
    if(!a || a === document.body || !$('app').contains(a)) return null;
    return {id:a.id, act:a.dataset && a.dataset.act, arg:a.dataset && a.dataset.arg};
  }
  function restore(f){
    if(!f) return;
    let el = f.id ? $(f.id) : null;
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
    const d = document.querySelector('#app .dlg');
    if(d && !d.contains(document.activeElement)){ const b = d.querySelector('.dlg-actions .btn:not([disabled])'); if(b) b.focus({preventScroll:true}); }
    else if(enter){ const t = $('scr-h'); if(t) t.focus({preventScroll:true}); } else restore(f);
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
    const t = transition(prev, E);
    if(first || prev.screen!==E.screen){ first = false; if(E.pair) E.pair.fresh = false; render('enter'); }
    else if(t) toast(t.kind, t.icon, t.text);
    else if(structure(prev) !== structure(E)){
      if(E.pair && prev.pair && E.pair.code !== prev.pair.code && E.pair.code){ E.pair.fresh = true; }
      render();
      if(E.pair && E.pair.renewed && E.pair.code !== (prev.pair && prev.pair.code)) announce('Código nuevo');
    }
    else patch();
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
  function call(name, arg){ const b = bridge(); return b && b[name] ? Promise.resolve(arg===undefined ? b[name]() : b[name](arg)) : Promise.resolve(null); }
  const ACT = {
    minimize(){ call('minimizar'); },
    close(){ call('cerrar'); },
    tab(el){ U.tab = el.dataset.arg; render(); const t = $('tab-'+U.tab); if(t) t.focus({preventScroll:true}); },
    toCams(){ U.tab = 'camaras'; render(); const t = $('tab-camaras'); if(t) t.focus({preventScroll:true}); },
    selCam(el){ U.sel = el.dataset.arg; previewSrc = null; render(); },
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
        if(r && r.ok){ U.tab = 'estado'; toast('ok', 'unlink', wipe ? 'Esta PC se desvinculó y borró sus datos. La familia recibió un aviso.' : 'Esta PC se desvinculó. La familia recibió un aviso.'); call('estado').then(s => { if(s) actualizar(s); }); }
        else render();
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
  function closeDlg(){ U.dlg = null; render(); if(opener && document.body.contains(opener)) opener.focus({preventScroll:true}); else restore({act:'unlinkAsk'}); opener = null; }
  document.addEventListener('change', e => { if(e.target && e.target.id==='unlink-wipe') U.unlinkWipe = e.target.checked; });
  document.addEventListener('toggle', e => { const d = e.target; if(d && d.matches && d.matches('details[data-k]')) U.open[d.dataset.k] = d.open; }, true);
  document.addEventListener('keydown', e => {
    const t = e.target, role = t.getAttribute && t.getAttribute('role');
    if(U.dlg){
      if(e.key==='Escape'){ e.preventDefault(); closeDlg(); return; }
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

  /* ---------- arranque: Python drives the progress with ttg.arranque(pct, paso) ---------- */
  function arranque(pct, step, version){
    const bar = document.querySelector('.boot-bar'); if(!bar) return;
    if(version != null) document.querySelector('.boot-v').textContent = 'Versión '+version;
    bar.querySelector('i').style.transform = 'scaleX('+(pct/100)+')';
    bar.setAttribute('aria-valuenow', pct);
    const txt = $('boot-st'); if(step != null && txt.textContent !== BOOT_STEPS[step]) txt.textContent = BOOT_STEPS[step];
  }
  function arranqueFin(){ const b = document.querySelector('.boot'); if(b) b.classList.add('out'); }

  global.ttg = { actualizar, arranque, arranqueFin };
  if(document.body.dataset.pagina === 'arranque'){
    $('app').innerHTML = bootWin({play:true, pct:0, step:0});
  } else {
    global.addEventListener('pywebviewready', () => { call('estado').then(s => { if(s) actualizar(s); }); });
  }
})(typeof window !== 'undefined' ? window : globalThis);
