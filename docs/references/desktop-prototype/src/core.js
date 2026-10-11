/* ================= Te Tengo Captura · núcleo compartido ================= */
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
/* ---------- Marca Te Tengo: dos figuras abrazadas (kit de marca; archivos en 05-prototipos/marca/) ---------- */
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

/* ---------- datos de ejemplo (BRIEF-pcs-camaras-y-movimientos.md, §2) ----------
   La PC se vincula desde la app (QR o código de 8 letras) e informa las webcams que detecta; la familia asigna
   cada cámara a una habitación desde la app (en la PC queda «Elegir aquí» para quien instala).
   La detección corre en esta PC: el video sale de ella solo mientras un familiar mira en vivo. */
const HOME = {who:'Rosa Huamán', first:'Rosa', fam:'Carmen Huamán', addr:'Jr. Los Pinos 482, San Miguel, Lima'};
const PC = {name:'Sala-Rosa', os:'Windows 11 Home', app:'Te Tengo Captura 0.5.0', by:'Carmen', on:'23/09/2026', at:'10:31'};
const OTHER_ROOMS = {Cocina:'Cocina-Rosa'};           /* habitaciones con cámara en otra PC de la casa */
const CODES = ['KQWT-MXHD', 'PJZD-RNCV', 'BXRT-NWLD']; /* solo consonantes de BCDFGHJKLMNPQRSTVWXZ */
const URL_V = 'tetengo.pe/vincular';
const DEVS = {
  d1:{name:'Webcam USB HD', view:'Sala', uid:'USB\\VID_0C45&PID_6366\\5&2A91F0C&0&3'},
  d2:{name:'Logitech C920', view:'Dormitorio', uid:'USB\\VID_046D&PID_082D\\8A3F21C0'},
  d3:{name:'USB2.0 PC Camera', view:'Pasillo', uid:'USB\\VID_1908&PID_2311\\6&1B3E7A&0&4'},
  d4:{name:'HD USB Camera', view:'Comedor', uid:'USB\\VID_32E4&PID_9230\\7&3C02D1&0&2'}
};
const ROOMS = ['Sala', 'Dormitorio', 'Cocina', 'Comedor', 'Pasillo'];
const STORE = {path:'C:\\Users\\Rosa\\AppData\\Local\\TeTengo\\Datos', path2:'D:\\TeTengo\\Datos', mov:1.1, vid:1.9, clip:0.2};
const DIAG = {file:'te-tengo-diagnostico-Sala-Rosa-2026-09-23.zip', size:'1,4 MB', dir:'Documentos'};
const DAY = 'miércoles 23/09';
const CAMS3 = [{id:'d1', room:'Sala'}, {id:'d2', room:'Dormitorio'}, {id:'d3', room:'Pasillo'}];

function cap1(s){ return s.charAt(0).toUpperCase() + s.slice(1); }
function delRoom(r){ return deRoomD(r).replace(/^el /, 'del ').replace(/^la /, 'de la ').replace(/^(?!del |de la )/, 'de '); }
function deRoomD(r){ return ({Sala:'la sala',Dormitorio:'el dormitorio',Cocina:'la cocina',Comedor:'el comedor',Pasillo:'el pasillo'})[r] || 'la habitación «'+r+'»'; }
function enRoom(r){ return ({Sala:'en la sala',Dormitorio:'en el dormitorio',Cocina:'en la cocina',Comedor:'en el comedor',Pasillo:'en el pasillo'})[r] || 'en '+r; }
function listY(a){ return a.length < 2 ? a.join('') : a.slice(0, -1).join(', ') + ' y ' + a[a.length-1]; }
function T(h){ const p = h.split(':').map(Number); return p[0]*3600 + p[1]*60 + (p[2]||0); }
function pad2(n){ return String(n).padStart(2, '0'); }
function hms(s){ s = Math.max(0, Math.round(s)); return pad2(Math.floor(s/3600)) + ':' + pad2(Math.floor(s%3600/60)) + ':' + pad2(s%60); }
function hm(s){ return hms(s).slice(0, 5); }
function mmss(s){ s = Math.max(0, s); return Math.floor(s/60) + ':' + pad2(s%60); }
function num(n, d){ return n.toFixed(d).replace('.', ','); }
function norm(s){ return String(s).toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').trim(); }

function baseState(){
  return {screen:'main', tab:'estado', linked:true, online:true, server:true, consent:true, moveConsent:true,
    pause:null, pauseBy:'Luis', live:null, retry:8, toast:null, open:{},
    cams:CAMS3.map(c => ({id:c.id, room:c.room, by:'app'})), lost:false, busy:false, extra:false, noCams:false, scan:false,
    here:false, peek:null,
    pick:{sel:'d1', room:null, otherOn:false, other:'', err:null},
    pair:{code:0, left:581, renewed:false, re90:false, fresh:false},
    adv:{on:false, sub:'actividad', cam:'Sala'},
    log:{filters:{persona:true, evento:true, descarte:true, conexion:true, programa:true}, q:'', paused:false, cut:0, open:null, extra:{Sala:[], Dormitorio:[], Pasillo:[]}, fresh:null},
    m:{person:true, phase:0, m1:.004, m2:72, m3:.62, win:1.48, ground:0, fps:7.9, cpu:34, lat:.09, pose:'pie', vis:{Nariz:.92, Hombros:.88, Caderas:.71, Tobillos:.38}},
    acts:[], actScope:'pc', actsEmpty:false,
    store:{video:false, videoStored:false, moves:true, clips:true, movKept:true, retMov:'90 días', retVid:'7 días', retClip:'Nunca borrar', cap:'50 GB', capOther:false, capVal:'', state:null, path:0},
    replay:false, rp:{cam:'Sala', day:'hoy', hour:'10:40', zoom:'10', t:T('10:40:52'), playing:false, speed:1, video:false, state:null},
    dlg:null, unlinkWipe:false, diag:{step:'intro'}
  };
}

/* ---------- cámaras de esta PC ---------- */
function connected(S){ if(S.noCams) return []; const d = ['d1','d2','d3']; if(S.extra) d.push('d4'); return d; }
function roomOf(S, id){ const c = S.cams.find(x => x.id===id); return c ? c.room : null; }
function isLost(S, id){ return S.lost && id==='d3'; }
function isBusy(S, id){ return S.busy && id==='d2'; }
function pausedRoom(S){ return S.pause ? roomOf(S, 'd1') : null; }
function takenRooms(S, id){
  const t = {}; S.cams.forEach(c => { if(c.id!==id) t[c.room] = PC.name; });
  for(const r in OTHER_ROOMS) t[r] = OTHER_ROOMS[r];
  return t;
}
function camStatus(S, c){
  if(isLost(S, c.id)) return {k:'off', t:'Desconectada', s:'Revisa el cable USB', i:'videoOff'};
  if(!S.consent) return {k:'consent', t:'Detenida', s:'Falta el consentimiento', i:'doc'};
  if(pausedRoom(S)===c.room) return {k:'pause', t:'En pausa', s:'Hasta las <span class="mono">'+S.pause+'</span>', i:'pause'};
  if(S.live && S.live.room===c.room) return {k:'live', t:'En vivo', s:esc(S.live.who)+' mira', i:'eye'};
  if(!S.online) return {k:'warn', t:'Sin internet', s:'Los avisos esperan', i:'wifiOff'};
  return {k:'send', t:'En línea', s:'', i:'check'};
}

/* ---------- ilustración de habitación (sin personas) ---------- */
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

/* ---------- esqueleto: puntos del cuerpo, nunca una foto (mismas posturas que la app móvil) ---------- */
const POSES = {
  pie:{h:[0,-106],n:[0,-96],sL:[-11,-92],sR:[11,-92],eL:[-15,-72],eR:[15,-72],wL:[-17,-54],wR:[17,-54],hL:[-7,-52],hR:[7,-52],kL:[-8,-26],kR:[8,-26],aL:[-9,0],aR:[9,0]},
  inestable:{h:[8,-104],n:[6,-94],sL:[-6,-90],sR:[15,-92],eL:[-24,-82],eR:[30,-104],wL:[-38,-88],wR:[40,-118],hL:[-4,-52],hR:[10,-52],kL:[-12,-27],kR:[14,-26],aL:[-20,0],aR:[12,1]},
  caida:{h:[-62,-10],n:[-50,-9],sL:[-44,-15],sR:[-44,-4],eL:[-30,-24],eR:[-34,6],wL:[-16,-28],wR:[-22,10],hL:[-6,-11],hR:[-6,-5],kL:[18,-18],kR:[16,-4],aL:[42,-12],aR:[40,2]},
  sentado:{h:[-6,-66],n:[-5,-56],sL:[-15,-52],sR:[5,-52],eL:[-22,-34],eR:[12,-34],wL:[-26,-16],wR:[16,-18],hL:[-10,-12],hR:[4,-12],kL:[18,-26],kR:[26,-20],aL:[34,-2],aR:[42,0]}
};
function lerpPose(a, b, k){ const A = POSES[a], B = POSES[b], o = {}; k = Math.max(0, Math.min(1, k)); for(const j in A) o[j] = [A[j][0]+(B[j][0]-A[j][0])*k, A[j][1]+(B[j][1]-A[j][1])*k]; return o; }
function skelG(p, x, y, col, sc){
  sc = sc||1; col = col||'#2B1D4E';
  const J = k => [(x+p[k][0]*sc).toFixed(1), (y+p[k][1]*sc).toFixed(1)];
  const seg = [['n','sL'],['n','sR'],['sL','eL'],['eL','wL'],['sR','eR'],['eR','wR'],['sL','hL'],['sR','hR'],['hL','hR'],['hL','kL'],['kL','aL'],['hR','kR'],['kR','aR']];
  let s = '<g class="skel">';
  seg.forEach(([a,b]) => { const A = J(a), B = J(b); s += '<line x1="'+A[0]+'" y1="'+A[1]+'" x2="'+B[0]+'" y2="'+B[1]+'" stroke="'+col+'" stroke-width="'+(3.2*sc).toFixed(1)+'" stroke-linecap="round"/>'; });
  const H = J('h'); s += '<circle cx="'+H[0]+'" cy="'+H[1]+'" r="'+(8*sc).toFixed(1)+'" fill="#fff" stroke="'+col+'" stroke-width="'+(3*sc).toFixed(1)+'"/>';
  ['n','sL','sR','eL','eR','wL','wR','hL','hR','kL','kR','aL','aR'].forEach(k => { const a = J(k); s += '<circle cx="'+a[0]+'" cy="'+a[1]+'" r="'+(3.4*sc).toFixed(1)+'" fill="#fff" stroke="'+col+'" stroke-width="'+(2*sc).toFixed(1)+'"/>'; });
  return s+'</g>';
}
function floorSVG(inner, w, h, fy){ return '<svg viewBox="0 0 '+w+' '+h+'" preserveAspectRatio="xMidYMax meet" aria-hidden="true"><path d="M0 '+fy+'H'+w+'" stroke="#D9D1E0" stroke-width="2"/>'+inner+'</svg>'; }

/* ---------- código QR de vinculación (ilustrativo: lleva el código de la PC) ---------- */
function qrSVG(code){
  const N = 25; let seed = 7;
  for(const ch of code) seed = (Math.imul(seed, 31) + ch.charCodeAt(0)) >>> 0;
  const rnd = () => { seed ^= seed << 13; seed >>>= 0; seed ^= seed >>> 17; seed ^= seed << 5; seed >>>= 0; return seed / 4294967296; };
  const fin = (x, y) => (x < 8 && y < 8) || (x >= N-8 && y < 8) || (x < 8 && y >= N-8);
  const mid = (x, y) => x >= 9 && x <= 15 && y >= 9 && y <= 15;
  let d = '';
  for(let y = 0; y < N; y++) for(let x = 0; x < N; x++){
    if(fin(x, y) || mid(x, y)) continue;
    const on = (x===6 || y===6) ? ((x+y) % 2 === 0) : rnd() < .48;
    if(on) d += 'M'+x+' '+y+'h1v1h-1z';
  }
  const F = (x, y) => 'M'+x+' '+y+'h7v7h-7zM'+(x+1)+' '+(y+1)+'v5h5v-5zM'+(x+2)+' '+(y+2)+'h3v3h-3z';
  return '<svg class="qr" viewBox="-2 -2 29 29" role="img" aria-label="Código QR para vincular esta PC" shape-rendering="crispEdges"><rect x="-2" y="-2" width="29" height="29" fill="#fff"/>'+
    '<path d="'+d+'" fill="#2B1D4E"/><path d="'+F(0,0)+F(N-7,0)+F(0,N-7)+'" fill="#2B1D4E" fill-rule="evenodd"/></svg>';
}

/* ---------- ventana ---------- */
function titlebar(){
  return '<div class="tb"><div class="tb-app">'+appIcon('xs')+'<span>Te Tengo Captura</span></div><div class="tb-btns">'+
    '<button class="tb-btn" data-act="minimize" aria-label="Minimizar" title="Minimizar">'+wg('min')+'</button>'+
    '<button class="tb-btn" aria-disabled="true" tabindex="-1" aria-label="Maximizar (no disponible)" title="Maximizar">'+wg('max')+'</button>'+
    '<button class="tb-btn close" data-act="close" aria-label="Cerrar" title="Cerrar">'+wg('close')+'</button></div></div>';
}
const PRE_SCREENS = ['vincular', 'vinculada', 'rechazada', 'quitada'];
function win(S, o){
  o = o||{};
  let scr;
  if(S.screen==='vincular') scr = scrVincular(S, o.enter||'');
  else if(S.screen==='vinculada') scr = scrVinculada(S, o.enter||'');
  else if(S.screen==='rechazada') scr = scrRechazada(S, o.enter||'');
  else if(S.screen==='quitada') scr = scrQuitada(S, o.enter||'');
  else scr = scrMain(S, o.enter||'');
  const toast = S.toast ? '<div class="wtoast '+S.toast.kind+'" role="status">'+ic(S.toast.icon||'check')+'<span>'+S.toast.text+'</span></div>' : '';
  return '<div class="win'+(o.flat?' flat':'')+'" aria-label="Te Tengo Captura">'+titlebar()+'<div class="wb">'+scr+toast+dialog(S)+'</div></div>';
}
function sec(cls, enter, inner){ return '<section class="scr'+(cls?' '+cls:'')+(enter?' '+enter:'')+'" aria-labelledby="scr-h">'+inner+'</section>'; }
function det(S, k, cls, summary, body){
  return '<details class="inst'+(cls?' '+cls:'')+'" data-k="'+k+'"'+(S.open && S.open[k]?' open':'')+'><summary>'+summary+ic('chevDown')+'</summary>'+body+'</details>';
}
function sw(on, act, lb, dis, compact){
  if(compact) return '<button class="switch" role="switch" aria-checked="'+(!!on && !dis)+'"'+(lb?' aria-labelledby="'+lb+'"':'')+(dis?' aria-disabled="true"':'')+' data-act="'+act+'"><i></i></button>';
  return '<span class="sw-l'+(on&&!dis?' on':'')+'"><button class="switch" role="switch" aria-checked="'+(!!on && !dis)+'"'+(lb?' aria-labelledby="'+lb+'"':'')+(dis?' aria-disabled="true"':'')+' data-act="'+act+'"><i></i></button>'+(on&&!dis?'Sí':'No')+'</span>';
}

/* =================== Vincular esta PC (QR + código de 8 letras) =================== */
function pairCard(S){
  const p = S.pair;
  const off = (icon, t, s) => '<div class="card pair-card pair-off" role="status"><span class="ci lg aviso dash">'+ic(icon)+'</span><h2 class="t-h2">'+t+'</h2>'+
    '<p class="t-small">'+s+' Reintentamos en <span class="mono" id="retry" data-fmt="ms">'+mmss(S.retry)+'</span>.</p>'+
    '<button class="btn btn-secondary btn-sm" data-act="retryNow">'+ic('refresh')+'Reintentar ahora</button></div>';
  if(!S.online) return off('wifiOff', 'Sin internet', 'Conecta esta PC a internet.');
  if(!S.server) return off('cloud', 'Te Tengo no responde', 'No tienes que hacer nada.');
  const code = CODES[p.code % CODES.length];
  const spoken = code.replace('-', '').split('').join(' ').replace(/^(\S \S \S \S) /, '$1, guion, ');
  return '<div class="card pair-card'+(p.fresh?' fresh':'')+'">'+
    (p.renewed ? '<p class="renew">'+ic('refresh')+'Código nuevo · el anterior venció</p>' : '')+
    '<div class="qrwrap">'+qrSVG(code)+'<span class="qr-logo" aria-hidden="true">'+LOGO+'</span></div>'+
    '<p class="t-meta">O escribe este código en la app:</p>'+
    '<p class="code-big"><span aria-hidden="true">'+code+'</span><span class="sr">'+spoken+'</span></p>'+
    '<p class="pair-url">'+URL_V+'</p>'+
    '<p class="pair-left'+(p.left<=60?' low':'')+'">'+ic('clock')+'Vence en <span class="mono" id="pair-left">'+mmss(p.left)+'</span></p>'+
    '<span class="sr" role="status" id="pair-ann">'+(p.renewed?'Código nuevo':'')+'</span></div>';
}
function scrVincular(S, enter){
  const ok = S.online && S.server;
  return sec('pair', enter,
    (S.pair.re90 ? '<div class="notice warn band90" role="status">'+ic('clock')+'<div><b>Más de 90 días sin conexión</b><span>Vincúlala de nuevo.</span></div></div>' : '')+
    '<div class="pair-grid"><div class="pair-l">'+
      '<h1 class="t-title" id="scr-h" tabindex="-1">Vincula esta PC con tu celular</h1>'+
      '<ol class="steps2"><li><span class="n">1</span><span>Abre la app Te Tengo</span></li>'+
      '<li><span class="n">2</span><span class="path">Ajustes'+ic('chevR')+'PCs y cámaras'+ic('chevR')+'Agregar PC</span></li>'+
      '<li><span class="n">3</span><span>Escanea este código</span></li></ol>'+
      '<p class="pcname"><span class="ci">'+ic('monitor')+'</span><span>Esta PC: <b>'+PC.name+'</b></span></p>'+
      det(S, 'help', 'phelp', ic('mobile')+'¿Error en el celular?',
        '<ul class="helplist"><li><b>«Este código ya venció o ya se usó»</b>Escanea el código nuevo.</li>'+
        '<li><b>«Demasiados intentos»</b>Espera la hora que indica el celular.</li></ul>')+
    '</div>'+pairCard(S)+'</div>'+
    '<div class="pair-foot">'+(ok ? '<p class="wait2" role="status"><span class="spin"></span>Esperando aprobación en el celular…</p>'
                                   : '<p class="wait2 stop"><span class="spin"></span>El código aparece con conexión</p>')+'</div>');
}
/* la PC informa las webcams que detectó; la familia las asigna desde la app */
function foundList(S){
  const devs = connected(S);
  if(!devs.length) return '<div class="notice warn">'+ic('cam')+'<div><b>No encontramos cámaras</b><span>Conecta una webcam por USB.</span></div></div>';
  return '<div class="found"><p class="found-h">'+ic('usb')+'<b>Detectamos '+devs.length+(devs.length===1?' cámara':' cámaras')+'</b></p>'+
    '<ul class="found-l">'+devs.map(id => '<li><span class="thumb art'+(isLost(S, id)?' dim':'')+'">'+roomSVG(DEVS[id].view)+'</span><span class="grow"><b>'+esc(DEVS[id].name)+'</b>'+devTag(S, id)+'</span></li>').join('')+'</ul></div>';
}
function scrVinculada(S, enter){
  const kept = S.cams.length;
  return sec('', enter, '<div class="result linked"><span class="ok-badge">'+ic('check')+'</span>'+
    '<h1 class="t-title" id="scr-h" tabindex="-1">Vinculada a la casa de '+HOME.who+'</h1>'+
    '<p class="t-lead">Aprobó '+PC.by+' a las <span class="mono">'+PC.at+'</span> · <b>'+PC.name+'</b></p>'+
    (kept ? '<div class="notice ok next">'+ic('check')+'<div><b>Las cámaras siguen en su habitación</b><span>'+listY(S.cams.map(c => esc(c.room)))+' · se cambian en la app</span></div></div>'
          : '<div class="notice info next">'+ic('mobile')+'<div><b>Ahora elige las cámaras en la app</b><span class="path">Ajustes'+ic('chevR')+'PCs y cámaras'+ic('chevR')+PC.name+'</span></div></div>')+
    foundList(S)+
    (!S.consent ? '<div class="notice warn">'+ic('doc')+'<div><b>Falta el consentimiento de '+HOME.first+'</b><span>Hasta registrarlo en la app, las cámaras no se usan.</span></div></div>' : '')+
    '<div class="actions"><button class="btn btn-primary btn-lg" data-act="toEstado">'+ic('pulse')+'Ir a Estado</button>'+
    (kept ? '' : '<button class="btn btn-ghost" data-act="toHere">'+ic('cam')+'Elegir aquí (si estás instalando)</button>')+'</div></div>');
}
function scrRechazada(S, enter){
  return sec('', enter, '<div class="result"><span class="ci lg pausa">'+ic('x')+'</span>'+
    '<h1 class="t-title" id="scr-h" tabindex="-1">No se vinculó esta PC</h1>'+
    '<p class="t-lead">Alguien eligió «No reconozco esta PC» en la app.</p>'+
    '<div class="actions"><button class="btn btn-primary btn-lg" data-act="pairAgain">'+ic('qr')+'Mostrar otro código</button></div></div>');
}
function scrQuitada(S, enter){
  return sec('', enter, '<div class="result"><span class="ci lg pausa">'+ic('unlink')+'</span>'+
    '<h1 class="t-title" id="scr-h" tabindex="-1">Se quitó de la casa de '+HOME.who+'</h1>'+
    '<p class="t-lead">'+PC.by+' la quitó desde la app a las <span class="mono">11:20</span>.</p>'+
    '<div class="actions"><button class="btn btn-primary btn-lg" data-act="pairAgain">'+ic('link')+'Vincular de nuevo</button></div></div>');
}

/* =================== Ventana principal: Estado · Cámaras · Avanzado =================== */
function tabbar(S){
  const t = (id, icon, l) => '<button class="tab'+(S.tab===id?' sel':'')+'" role="tab" id="tab-'+id+'" aria-selected="'+(S.tab===id)+'" aria-controls="panel" tabindex="'+(S.tab===id?0:-1)+'" data-act="tab" data-arg="'+id+'">'+ic(icon)+'<span>'+l+'</span></button>';
  return '<nav class="tabbar" aria-label="Te Tengo Captura"><div class="tabs" role="tablist" aria-label="Secciones">'+t('estado','pulse','Estado')+t('camaras','cam','Cámaras')+t('avanzado','sliders','Avanzado')+'</div>'+
    '<span class="tb-pc">'+ic('monitor')+'<span>Esta PC: <b>'+PC.name+'</b></span></span></nav>';
}
function scrMain(S, enter){
  let panel;
  if(S.tab==='camaras') panel = panelCamaras(S);
  else if(S.tab==='avanzado') panel = S.replay ? panelReplay(S) : panelAvanzado(S);
  else panel = panelEstado(S);
  return sec('main', enter, tabbar(S)+'<div class="panel '+S.tab+(S.replay&&S.tab==='avanzado'?' replay':'')+'" id="panel" role="tabpanel" aria-labelledby="tab-'+S.tab+'">'+panel+'</div>');
}

/* ---------- Estado: resumen y una fila por cámara ---------- */
function health(S){
  const H = (cls, k, icon, t, s, extra) => '<div class="health '+cls+'" role="status"><span class="st '+k+'">'+ic(icon)+'</span><div class="grow"><b>'+t+'</b><span>'+s+'</span></div>'+(extra||'')+'</div>';
  const cams = S.cams, rooms = cams.map(c => c.room);
  if(!connected(S).length) return H('none', 'none', 'cam', 'No encontramos cámaras', 'Conecta una webcam por USB.', '<button class="btn btn-secondary btn-sm" data-act="toCams">'+ic('cam')+'Ir a Cámaras</button>');
  if(!cams.length){ const n = connected(S).length;
    return H('none', 'none', 'mobile', 'Falta elegir las cámaras en la app', 'Detectamos '+n+(n===1?' cámara':' cámaras')+'. Mientras tanto, no cuida ninguna habitación.', '<button class="btn btn-secondary btn-sm" data-act="toCams">'+ic('cam')+'Ir a Cámaras</button>'); }
  const lost = cams.find(c => isLost(S, c.id));
  if(lost) return H('warn lost', 'off', 'videoOff', esc(lost.room)+' no responde', 'Revisa el cable USB · '+(cams.length-1)+' de '+cams.length+' cámaras funcionan',
    '<button class="btn btn-secondary btn-sm" data-act="rescan">'+ic('refresh')+'Buscar de nuevo</button>');
  if(!S.online) return H('offline', 'off', 'wifiOff', 'Sin internet', 'Las cámaras siguen cuidando; los avisos esperan. Reintento en <span class="mono" id="retry">'+S.retry+'</span> s.',
    '<button class="btn btn-secondary btn-sm" data-act="retryNow">'+ic('refresh')+'Reintentar ahora</button>');
  if(!S.consent) return H('warn', 'consent', 'doc', 'Falta el consentimiento de '+HOME.first, 'Hasta registrarlo en la app, las cámaras no se usan.');
  const pr = pausedRoom(S);
  if(pr){ const others = rooms.filter(r => r!==pr);
    return H('idle', 'pause', 'pause', cap1(deRoomD(pr))+' está en pausa hasta las <span class="mono">'+S.pause+'</span>', (others.length ? listY(others)+(others.length>1?' siguen':' sigue')+' cuidando · ' : '')+'la pausó '+esc(S.pauseBy||'la familia')+' desde la app'); }
  if(S.live) return H('live', 'live', 'eye', esc(S.live.who)+' está viendo '+deRoomD(S.live.room)+' en vivo', 'Desde las <span class="mono">'+S.live.since+'</span> · no se graba · queda registrado');
  return H('ok', 'send', 'check', cams.length===1 ? 'Te Tengo cuida '+deRoomD(rooms[0]) : 'Te Tengo cuida '+cams.length+' habitaciones', 'Todo funciona bien.');
}
function camRowE(S, c){
  const st = camStatus(S, c), D = DEVS[c.id];
  return '<li class="crow'+(st.k==='off'?' lost':'')+'"><span class="thumb art'+(st.k!=='send'&&st.k!=='live'?' dim':'')+'">'+roomSVG(D.view)+'</span>'+
    '<span class="crow-id"><b>'+esc(c.room)+'</b><span>'+ic('usb')+esc(D.name)+'</span></span>'+
    '<span class="cam-st"><span class="st '+st.k+'">'+ic(st.i)+'</span><span class="grow"><b class="stx '+st.k+'">'+st.t+'</b>'+(st.s?'<span class="t-meta">'+st.s+'</span>':'')+'</span></span></li>';
}
/* la app pide la vista previa de una cámara para elegir su habitación: se avisa en la PC, como la vista en vivo */
function peekNotice(S, here){
  if(!S.peek || !connected(S).includes(S.peek)) return '';
  return '<div class="notice info peek-n" role="status"><span class="led" aria-hidden="true"></span><div><b>'+(here ? PC.by+' mira esta cámara para elegirla' : PC.by+' mira la '+esc(DEVS[S.peek].name)+' para elegirla')+'</b><span>No se graba · queda registrado</span></div></div>';
}
function panelEstado(S){
  const list = S.cams.length ? '<ul class="crows" aria-label="Cámaras de esta PC">'+S.cams.map(c => camRowE(S, c)).join('')+'</ul>' : '';
  return '<header class="cam-head"><div><h1 class="t-title" id="scr-h" tabindex="-1">Vivienda de '+HOME.who+'</h1><p class="t-meta mt4">'+ic('home')+HOME.addr+'</p></div></header>'+
    health(S)+peekNotice(S)+list+
    '<div class="card instcard">'+det(S, 'inst', '', ic('lock')+'Datos de la instalación',
      '<dl class="conf-kv"><div><dt>Esta PC</dt><dd>'+PC.name+'</dd></div><div><dt>Sistema</dt><dd>'+PC.os+'</dd></div>'+
      '<div><dt>Vinculada</dt><dd>Por '+PC.by+' el '+PC.on+'</dd></div><div><dt>Programa</dt><dd>'+PC.app+'</dd></div></dl>')+'</div>'+
    '<p class="scr-foot">'+ic('mobile')+'<span class="ft">Cámaras, pausas, consentimiento y alertas: en la app</span><span class="sep"></span>'+ic('power')+'<span>Se inicia con Windows</span></p>';
}

/* ---------- Cámaras: elegir cámaras y habitaciones, con vista previa local ---------- */
function devTag(S, id){
  const r = roomOf(S, id);
  if(isLost(S, id)) return '<span class="ctag off">'+ic('videoOff')+'Desconectada'+(r?' · '+esc(r):'')+'</span>';
  if(isBusy(S, id)) return '<span class="ctag busy">'+ic('warn')+'La usa otro programa</span>';
  if(r) return '<span class="ctag use">'+ic('check')+'En uso · '+esc(r)+'</span>';
  if(id==='d4') return '<span class="ctag new">'+ic('plus')+'Nueva · Sin usar</span>';
  return '<span class="ctag">Sin usar</span>';
}
function thisPc(){
  return '<div class="thispc"><span class="ci">'+ic('monitor')+'</span><span class="grow"><b>Esta PC: '+PC.name+'</b><span>Vinculada por '+PC.by+' el '+PC.on+'</span></span>'+
    '<button class="btn btn-danger-ghost btn-xs" data-act="unlinkAsk">'+ic('unlink')+'Desvincular</button></div>';
}
function selDev(S){ const d = connected(S); return d.includes(S.pick.sel) ? S.pick.sel : d[0]; }
function pickState(S, id){
  const r = roomOf(S, id), pk = S.pick;
  const custom = r && !ROOMS.includes(r);
  const otherOn = pk.otherOn || (pk.room==null && custom);
  const room = otherOn ? (pk.otherOn ? pk.other : (pk.other || r)) : (pk.room!=null ? pk.room : r);
  return {r, otherOn, room, otherVal: pk.otherOn ? pk.other : (custom ? r : '')};
}
function camPane(S, id){
  const D = DEVS[id], pk = S.pick, ps = pickState(S, id), r = ps.r;
  if(S.scan) return '<div class="cpane"><div class="pane-scan" role="status"><span class="spin"></span>Buscando cámaras conectadas…</div></div>';
  if(isLost(S, id)) return '<div class="cpane"><div class="pane-empty" role="status">'+ic('videoOff')+'<h2 class="t-h2">No responde: revisa el cable USB</h2>'+
    '<p class="t-small">'+(r ? esc(r)+' sigue asignada a esta cámara. ' : '')+'Conéctala y pulsa Buscar de nuevo.</p><button class="btn btn-secondary" data-act="rescan">'+ic('refresh')+'Buscar de nuevo</button></div></div>';
  if(isBusy(S, id)) return '<div class="cpane"><div class="pane-empty" role="status">'+ic('warn')+'<h2 class="t-h2">Otro programa usa esta cámara</h2>'+
    '<p class="t-small">Ciérralo y pulsa Buscar de nuevo.</p><button class="btn btn-secondary" data-act="rescan">'+ic('refresh')+'Buscar de nuevo</button></div></div>';
  const taken = takenRooms(S, id);
  const chips = ROOMS.map(x => {
    if(taken[x]) return '<button class="chip2" aria-disabled="true" title="'+(taken[x]===PC.name?'Ya tiene cámara en esta PC':'Ya tiene cámara en la PC '+taken[x])+'"><span>'+x+'</span><small>Ya tiene cámara'+(taken[x]!==PC.name?' · '+taken[x]:'')+'</small></button>';
    const on = !ps.otherOn && ps.room===x;
    return '<button class="chip2'+(on?' sel':'')+'" aria-pressed="'+on+'" data-act="pickRoom" data-arg="'+x+'">'+(on?ic('check'):'')+x+'</button>';
  }).join('') + '<button class="chip2'+(ps.otherOn?' sel':'')+'" aria-pressed="'+ps.otherOn+'" data-act="pickOther">'+(ps.otherOn?ic('check'):'')+'Otra…</button>';
  const errs = {empty:'Escribe el nombre de la habitación.', bath:'Por privacidad, no se admiten cámaras en el baño.',
    dup:esc(pk.errRoom||'')+' ya tiene cámara (PC '+esc(pk.errPc||PC.name)+'). Una cámara por habitación.'};
  const err = pk.err ? errs[pk.err] : '';
  const changed = r ? (ps.room && norm(ps.room)!==norm(r)) : (ps.otherOn || !!ps.room);
  const primary = r ? '<button class="btn btn-primary" data-act="useCam"'+(changed?'':' disabled')+'>'+ic('check')+'Guardar cambio</button>'
                    : '<button class="btn btn-primary" data-act="useCam"'+(changed?'':' disabled')+'>'+ic('check')+'Usar esta cámara</button>';
  return '<div class="cpane"><figure class="pv2 art">'+roomSVG(D.view)+'<figcaption class="pv-tag">'+ic('eye')+'Vista previa · '+esc(D.name)+'</figcaption><span class="pv-lock">'+ic('lock')+'Solo se ve en esta PC</span></figure>'+
    (S.adv.on ? '<p class="devid">'+ic('usb')+'<span>Identificador:</span><span class="code">'+esc(D.uid)+'</span></p>' : '')+
    '<span class="rooms-l" id="rooms-l">¿En qué habitación está?</span><div class="chips2" role="group" aria-labelledby="rooms-l">'+chips+'</div>'+
    (ps.otherOn ? '<div class="other-row field'+(err?' err':'')+'"><label class="sr" for="room-other">Nombre de la habitación</label><input class="input" id="room-other" value="'+esc(ps.otherVal)+'" placeholder="Por ejemplo, Sala comedor" autocomplete="off"'+(err?' aria-invalid="true" aria-describedby="room-err"':'')+'></div>' : '')+
    (err ? '<p class="field-msg err-msg" id="room-err" role="alert">'+ic('warn')+'<span>'+err+'</span></p>' : '')+
    '<p class="help-l">'+ic('info')+'Por privacidad, no se admiten cámaras en el baño.</p>'+
    '<div class="pane-actions">'+(r ? '<button class="btn btn-danger-ghost btn-sm" data-act="unuse">Dejar de usar</button>' : '')+primary+'</div></div>';
}
/* vista informativa de una cámara: vista previa para revisar el encuadre, habitación (elegida en la app) y conexión */
function camInfo(S, id){
  const D = DEVS[id], c = S.cams.find(x => x.id===id);
  if(S.scan || isLost(S, id) || isBusy(S, id)) return camPane(S, id);
  const by = c ? (c.by==='pc' ? 'Elegida en esta PC' : 'La eligió '+PC.by+' en la app') : 'Se elige en la app';
  return '<div class="cpane info"><figure class="pv2 art">'+roomSVG(D.view)+'<figcaption class="pv-tag">'+ic('eye')+'Vista previa · '+esc(D.name)+'</figcaption><span class="pv-lock">'+ic('lock')+'Solo se ve en esta PC</span></figure>'+
    peekNotice(S, true)+
    '<dl class="cinfo"><div><dt>Habitación</dt><dd><b>'+(c ? esc(c.room) : 'Sin usar')+'</b><span>'+by+'</span></dd></div>'+
    '<div><dt>Conexión</dt><dd><b class="ok">'+ic('check')+'Conectada</b><span>'+(id==='d4' ? 'Nueva · por USB' : 'Por USB')+'</span></dd></div></dl>'+
    (S.adv.on ? '<p class="devid">'+ic('usb')+'<span>Identificador:</span><span class="code">'+esc(D.uid)+'</span></p>' : '')+
    '<p class="help-l">'+ic('eye')+'Usa la vista previa para revisar el encuadre.</p>'+
    (S.cams.length >= 3 ? '<p class="help-l">'+ic('info')+'Si la detección va lenta, pasa alguna cámara a otra PC.</p>' : '')+
    '<div class="pane-actions start"><button class="btn btn-ghost btn-sm" data-act="hereOn">'+ic('cam')+'Elegir aquí (si estás instalando)</button></div></div>';
}
function panelCamaras(S){
  const devs = connected(S), any = S.cams.length, here = S.here && devs.length;
  const meta = here ? 'Elige la habitación de cada cámara. La familia lo verá en la app.'
    : !devs.length || any ? 'Las habitaciones se eligen en la app.'
    : 'Detectamos '+devs.length+(devs.length===1?' cámara':' cámaras')+'. Elígelas en la app.';
  const head = '<header class="p-head"><div><h1 class="t-title" id="scr-h" tabindex="-1">'+(here?'Elegir aquí, si estás instalando':'Cámaras de esta PC')+'</h1>'+
    '<p class="t-meta">'+meta+'</p></div>'+(here ? '<button class="btn btn-secondary btn-sm" data-act="hereOff">'+ic('back')+'Volver</button>' : '')+'</header>';
  if(!devs.length) return head+'<div class="card empty-big" role="status"><span class="ci lg">'+ic('cam')+'</span><h2 class="t-h2">No encontramos cámaras</h2>'+
    '<p class="t-small">Conecta una webcam por USB.</p><button class="btn btn-secondary" data-act="rescan">'+ic('refresh')+'Buscar de nuevo</button></div>'+thisPc();
  const sel = selDev(S);
  const peekRow = id => !here && S.peek===id ? '<span class="peek"><span class="led" aria-hidden="true"></span><span>'+PC.by+' la mira para elegirla · No se graba</span></span>' : '';
  const rows = devs.map(id => '<button class="cpick'+(isLost(S,id)?' lost':'')+(!here && S.peek===id?' peeking':'')+'" role="radio" aria-checked="'+(id===sel)+'" tabindex="'+(id===sel?0:-1)+'" data-act="selCam" data-arg="'+id+'">'+
    '<span class="thumb art'+(isLost(S,id)||isBusy(S,id)?' dim':'')+'">'+roomSVG(DEVS[id].view)+'</span><span class="grow"><b>'+esc(DEVS[id].name)+'</b>'+devTag(S, id)+'</span>'+peekRow(id)+'</button>').join('');
  const many = here && S.cams.length >= 3 ? '<p class="many">'+ic('info')+'<span>Si la detección va lenta, pasa alguna cámara a otra PC.</span></p>' : '';
  return head+'<div class="camgrid"><div class="clist"><p class="grp-l" id="g-cams">Cámaras conectadas</p><div class="clist-rows" role="radiogroup" aria-labelledby="g-cams">'+rows+'</div>'+
    '<div class="clist-tools"><button class="btn btn-ghost btn-sm" data-act="rescan">'+ic('refresh')+'Buscar de nuevo</button></div>'+many+thisPc()+'</div>'+(here ? camPane(S, sel) : camInfo(S, sel))+'</div>';
}

/* =================== Avanzado: registro en vivo, medidores, actividad y almacenamiento =================== */
/* k = filtro (persona, evento, descarte, conexion, programa); tone = color con ícono y texto */
const LOG = {
  Sala:[
    {t:'10:38:02', k:'programa', tone:'', i:'monitor', m:'Se abrió la cámara de la Sala (Webcam USB HD)', x:'INFO camara abierta id=USB\\VID_0C45&PID_6366 nombre="Webcam USB HD" 1280x720@8fps'},
    {t:'10:38:04', k:'persona', tone:'persona', i:'person', m:'Persona detectada en la Sala', x:'INFO pose persona=1 puntos=33 visibilidad_media=0.81'},
    {t:'10:39:10', k:'evento', tone:'inestable', i:'warn', m:'Inestable: recuperó el equilibrio', x:'WARN clasificador evento=inestable theta=31.5 recuperado=1'},
    {t:'10:40:30', k:'descarte', tone:'aviso', i:'eyeOff', m:'Imagen descartada: no se ven los tobillos', x:'DEBUG calidad descartada=1 motivo=tobillos_no_visibles vis_tobillo=0.38 min=0.5'},
    {t:'10:41:50', k:'persona', tone:'persona', i:'person', m:'Persona detectada en la Sala', x:'INFO pose persona=1 puntos=33 visibilidad_media=0.84'},
    {t:'10:41:51', k:'evento', tone:'inestable', i:'arrowDown', m:'La cadera bajó rápido (sobre el umbral)', x:'INFO clasificador M1=1 v_cadera=0.034 umbral_v=0.01'},
    {t:'10:41:51', k:'evento', tone:'caida', i:'warn', m:'Posible caída: ventana de 1,48 s', x:'INFO clasificador fase=INICIO_CAIDA v=0.034 theta=38.2 P=0.84 M1=1 M2=1 M3=0', ms:482},
    {t:'10:41:52', k:'evento', tone:'caida', i:'warn', m:'Caída: en el suelo. Aviso enviado', x:'WARN clasificador fase=CAIDA en_suelo=1 evento=caida aviso=encolado'},
    {t:'10:42:22', k:'evento', tone:'caida', i:'warn', m:'Caída confirmada: 30 s en el suelo', x:'WARN clasificador fase=CAIDA_CONFIRMADA t_suelo=30.0'},
    {t:'10:43:05', k:'evento', tone:'calma', i:'arrowUp', m:'Se levantó', x:'INFO clasificador fase=DE_PIE evento=se_levanto'},
    {t:'10:44:10', k:'descarte', tone:'aviso', i:'eyeOff', m:'Imagen descartada: no se ven los tobillos', x:'DEBUG calidad descartada=1 motivo=tobillos_no_visibles vis_tobillo=0.41 min=0.5'}
  ],
  Dormitorio:[
    {t:'10:38:02', k:'programa', tone:'', i:'monitor', m:'Se abrió la cámara del Dormitorio (Logitech C920)', x:'INFO camara abierta id=USB\\VID_046D&PID_082D nombre="Logitech C920" 1280x720@8fps'},
    {t:'10:38:03', k:'persona', tone:'', i:'person', m:'Sin persona en la imagen', x:'INFO pose persona=0'}
  ],
  Pasillo:[]
};
const LOG_LIVE = [
  {k:'persona', tone:'persona', i:'person', m:'Se ve a la persona de pie', x:'INFO clasificador fase=DE_PIE theta=74.0 razon=0.61'},
  {k:'descarte', tone:'aviso', i:'eyeOff', m:'Imagen descartada: no se ven los tobillos', x:'DEBUG calidad descartada=1 motivo=tobillos_no_visibles vis_tobillo=0.44 min=0.5'},
  {k:'persona', tone:'', i:'person', m:'Sin persona en la imagen', x:'INFO pose persona=0'},
  {k:'persona', tone:'persona', i:'person', m:'Persona detectada en la Sala', x:'INFO pose persona=1 puntos=33 visibilidad_media=0.80'}
];
const LOG_FALL = [
  {k:'evento', tone:'inestable', i:'arrowDown', m:'La cadera bajó rápido (sobre el umbral)', x:'INFO clasificador M1=1 v_cadera=0.034 umbral_v=0.01'},
  {k:'evento', tone:'caida', i:'warn', m:'Posible caída: ventana de 1,48 s', x:'INFO clasificador fase=INICIO_CAIDA v=0.034 theta=38.2 P=0.84 M1=1 M2=1 M3=0'},
  {k:'evento', tone:'caida', i:'warn', m:'Caída: en el suelo. Aviso enviado', x:'WARN clasificador fase=CAIDA en_suelo=1 evento=caida aviso=encolado'},
  {k:'evento', tone:'caida', i:'warn', m:'Caída confirmada: 30 s en el suelo', x:'WARN clasificador fase=CAIDA_CONFIRMADA t_suelo=30.0'},
  {k:'evento', tone:'calma', i:'arrowUp', m:'Se levantó', x:'INFO clasificador fase=DE_PIE evento=se_levanto'}
];
const LOG_NET = {k:'conexion', tone:'aviso', i:'wifiOff', m:'Sin internet: avisos en cola', x:'WARN conexion estado=sin_red cola_avisos=0 reintento=8s'};
const LOG_NET_OK = {k:'conexion', tone:'calma', i:'wifi', m:'Volvió internet: avisos enviados', x:'INFO conexion estado=en_linea cola_avisos=0'};
const LOG_K = [['persona','person','Personas'], ['evento','warn','Eventos'], ['descarte','eyeOff','Descartadas'], ['conexion','wifi','Conexión'], ['programa','monitor','Programa']];
function logAll(S, cam){ return (LOG[cam]||[]).map((l, i) => Object.assign({id:cam+'-'+i}, l)).concat((S.log.extra[cam]||[]).map((l, i) => Object.assign({id:cam+'-x'+i}, l))); }
function techLine(l){ return '2026-09-23T'+l.t+'.'+String(l.ms!=null?l.ms:(Number(l.t.slice(-2))*37+111)%1000).padStart(3,'0')+'-05:00 '+l.x; }
function logLine(S, l){
  const open = S.log.open===l.id, isNew = S.log.fresh===l.id;
  return '<div class="lline '+(l.tone||'')+(isNew?' new':'')+'"><time>'+l.t+'</time><span class="li">'+ic(l.i)+'</span><span class="msg">'+l.m+'</span>'+
    '<button class="tech-btn" aria-expanded="'+open+'" aria-controls="tx-'+l.id+'" data-act="techToggle" data-arg="'+l.id+'" aria-label="Ver línea técnica">Técnica'+ic('chevDown')+'</button></div>'+
    (open ? '<div class="ltech" id="tx-'+l.id+'"><span class="code">'+esc(techLine(l))+'</span><button class="btn btn-ghost btn-xs" data-act="copyTech" data-arg="'+l.id+'">'+ic('copy')+'Copiar</button></div>' : '');
}
function logRows(S){
  const cam = S.adv.cam, all = logAll(S, cam), lg = S.log;
  const shown = lg.paused ? all.slice(0, lg.cut) : all;
  const q = norm(lg.q);
  const vis = shown.filter(l => lg.filters[l.k] && (!q || norm(l.m).includes(q)));
  const pin = pausedRoom(S)===cam ? '<div class="lline pin"><time>'+hm(T('10:42:00'))+'</time><span class="li">'+ic('pause')+'</span><span class="msg">Cámara en pausa hasta las <span class="mono">'+S.pause+'</span></span><span></span></div>' : '';
  const lost = S.lost && roomOf(S, 'd3')===cam ? '<div class="lline aviso pin"><time>10:42</time><span class="li">'+ic('videoOff')+'</span><span class="msg">Cámara desconectada: revisa el cable USB</span><span></span></div>' : '';
  let body;
  if(!all.length) body = '<div class="logempty">'+ic('terminal')+'<b>Aún no pasa nada en esta cámara</b></div>';
  else if(!vis.length && q) body = '<div class="logempty">'+ic('search')+'<b>No hay líneas con «'+esc(lg.q)+'»</b></div>';
  else if(!vis.length) body = '<div class="logempty">'+ic('list')+'<b>No hay líneas de ese tipo</b></div>';
  else body = vis.map(l => logLine(S, l)).join('');
  return pin + lost + body;
}
function logCounts(S){ const all = logAll(S, S.adv.cam), c = {}; LOG_K.forEach(k => c[k[0]] = 0); (S.log.paused ? all.slice(0, S.log.cut) : all).forEach(l => c[l.k]++); return c; }
function logView(S){
  const lg = S.log, all = logAll(S, S.adv.cam), cnt = logCounts(S), nNew = lg.paused ? all.length - lg.cut : 0;
  return '<div class="logbar" role="toolbar" aria-label="Filtros del registro">'+LOG_K.map(k => '<button class="fchip" aria-pressed="'+lg.filters[k[0]]+'" data-act="logFilter" data-arg="'+k[0]+'">'+ic(k[1])+'<span class="lbl">'+k[2]+'</span><span class="cnt" id="cnt-'+k[0]+'">'+cnt[k[0]]+'</span></button>').join('')+
    '<label class="logsearch"><span class="sr">Buscar en el registro</span>'+ic('search')+'<input class="input" id="log-q" type="search" placeholder="Buscar" value="'+esc(lg.q)+'" autocomplete="off"></label>'+
    '<button class="btn btn-secondary btn-xs" data-act="logPause" aria-pressed="'+lg.paused+'">'+ic(lg.paused?'play':'pause')+(lg.paused?'Seguir':'Pausar')+'</button></div>'+
    (lg.paused ? '<div class="logband" id="log-band" role="status">'+ic('pause')+'<span class="grow">En pausa · <span id="log-new">'+nNew+' '+(nNew===1?'línea nueva':'líneas nuevas')+'</span></span><button class="btn btn-ghost btn-xs" data-act="logPause">'+ic('play')+'Seguir</button></div>' : '')+
    '<div class="logbox" id="logbox" role="log" aria-label="Registro en vivo de '+deRoomD(S.adv.cam)+'" aria-live="off" tabindex="0">'+logRows(S)+'</div>'+
    '<span class="sr" role="status" id="log-ann"></span>';
}

/* ---------- medidores ---------- */
function meterReason(S){
  const cam = S.adv.cam;
  if(S.lost && roomOf(S, 'd3')===cam) return {t:'Cámara desconectada', s:'Revisa el cable USB.', i:'videoOff', c:'aviso dash'};
  if(pausedRoom(S)===cam) return {t:'En pausa hasta las '+S.pause, s:'La pausaron desde la app.', i:'pause', c:'pausa'};
  if(!S.consent) return {t:'Cámara detenida', s:'Falta el consentimiento de '+HOME.first+'.', i:'doc', c:'aviso'};
  if(cam!=='Sala' || !S.m.person) return {t:'Sin persona en la imagen', s:'Vuelven cuando la cámara vea a alguien.', i:'person', c:'pausa'};
  return null;
}
const PHASES = [['De pie',''], ['Posible caída','inestable'], ['En el suelo','caida'], ['Caída confirmada','caida']];
function metersInner(S){
  const m = S.m, off = meterReason(S), D = v => off ? '—' : v;
  const meas = (title, val, unit, thr, si, pct, tp) => '<div class="mcard"><h3>'+title+'</h3><div class="mrow"><span class="mval">'+D(val)+(off?'':'<small>'+unit+'</small>')+'</span>'+
    (off ? '' : '<span class="yn'+(si?' si':'')+'">'+(si?ic('check')+'Sí':'No')+'</span>')+'</div>'+
    '<div class="mthr'+(si&&!off?' si':'')+'"><i style="width:'+(off?0:Math.min(100, pct))+'%"></i><b style="left:'+tp+'%"></b></div><p class="msub">'+thr+'</p></div>';
  const ph = off ? -1 : m.phase;
  const row1 = off
    ? '<div class="mcard mnote" role="status"><span class="ci '+off.c+'">'+ic(off.i)+'</span><div><b>'+off.t+'</b><span>'+off.s+'</span></div></div>'
    : '<div class="mcard"><h3>'+ic('gauge')+'Rendimiento</h3><span class="mval">'+num(m.fps, 1)+'<small>fps</small></span><p class="msub">Objetivo: 8 fps</p>'+
        '<div class="mkv"><div><span>Uso del procesador</span><b>'+Math.round(m.cpu)+' %</b></div><div><span>Demora del análisis</span><b>'+num(m.lat, 2)+' s</b></div></div></div>'+
      '<div class="mcard"><h3>'+ic('person')+'Persona</h3><p class="mperson"><span class="ci calma">'+ic('check')+'</span>Sí, una persona</p></div>'+
      '<div class="mcard"><h3>'+ic('clock')+'Temporizadores</h3>'+
        '<p class="timer">Ventana de caída <b>'+num(m.win, 2)+' s</b></p><div class="tbar"><i style="transform:scaleX('+(m.win/1.48).toFixed(3)+')"></i></div>'+
        '<p class="timer mt8">En el suelo <b>'+Math.round(m.ground)+' de 30 s</b></p><div class="tbar"><i style="transform:scaleX('+(m.ground/30).toFixed(3)+')"></i></div></div>';
  const vis = m.vis, bars = Object.keys(vis).map(k => { const v = vis[k], low = v < .5;
    return '<div class="pbar'+(low&&!off?' low':'')+'"><span>'+k+'</span><span class="ptrack"><i style="width:'+(off?0:v*100)+'%"></i></span><b>'+(off?'—':(low?ic('warn'):'')+num(v, 2))+'</b></div>'; }).join('');
  const pose = m.pose==='falling' ? lerpPose('pie', 'caida', .55) : POSES[m.pose] || POSES.pie;
  const fx = m.pose==='caida' ? 128 : 120;
  return row1+
    meas('Descenso de la cadera (M1)', num(m.m1, 3), 'cuerpos/s', 'Avisa desde 0,01', m.m1 >= .01, m.m1/.02*100, 50)+
    meas('Inclinación del tronco (M2)', Math.round(m.m2)+'°', '', 'Avisa por debajo de 45°', m.m2 < 45, (90-m.m2)/90*100, 50)+
    meas('Forma del cuerpo, ancho/alto (M3)', num(m.m3, 2), '', 'Avisa desde 1', m.m3 >= 1, m.m3/2*100, 50)+
    '<div class="mcard mphase"><h3>'+ic('pulse')+'Fase</h3><div class="phs">'+PHASES.map((p, i) => (i?ic('chevR'):'')+'<span class="ph'+(i===ph?' cur '+p[1]:'')+'"'+(i===ph?' aria-current="step"':'')+'>'+(i===ph?ic('check'):'')+p[0]+'</span>').join('')+'</div>'+
      '<p class="msub mt8">Avisa si sigue en el suelo tras 1,48 s; confirma a los 30 s.</p></div>'+
    '<div class="mside"><div class="mcard"><h3>'+ic('person')+'Puntos del cuerpo</h3><div class="pbars">'+bars+'</div><p class="plow">Visibilidad 0–1 · mínimo 0,5</p></div>'+
      '<div class="mcard" style="flex:1;display:flex;flex-direction:column"><h3>'+ic('eye')+'Esqueleto</h3><div class="mskel">'+
        (off ? '' : floorSVG(skelG(pose, fx, 132, '#2B1D4E', .95), 240, 150, 134))+'<span class="pv-lock">'+ic('lock')+'Solo se ve en esta PC</span></div></div></div>';
}
function metersView(S){ return '<div class="mgrid'+(meterReason(S)?' off':'')+'" id="meters" aria-label="Medidores de '+deRoomD(S.adv.cam)+'">'+metersInner(S)+'</div>'; }

/* ---------- actividad ---------- */
const ACTS0 = [
  {d:'Hoy', t:'10:33', who:'CH', m:'Carmen eligió desde la app la Logitech C920 para el Dormitorio', scope:'pc'},
  {d:'Hoy', t:'10:31', who:'CH', m:'Carmen vinculó la PC Sala-Rosa', scope:'pc'},
  {d:'Hoy', t:'10:20', who:'CH', m:'Carmen cambió los movimientos en la nube de 7 a 30 días', scope:'casa'},
  {d:'Hoy', t:'10:15', who:'CH', m:'Carmen registró el permiso de Rosa para guardar movimientos', scope:'casa'},
  {d:'Ayer · 22/09/2026', t:'18:05', who:'CH', m:'Carmen eligió desde la app la HD Pro Webcam de la PC Cocina-Rosa para la Cocina', scope:'casa'}
];
function actView(S){
  const rows = S.actsEmpty ? [] : S.acts.map(a => Object.assign({d:'Hoy', scope:'pc', who:'pc'}, a)).concat(ACTS0).filter(a => S.actScope==='casa' || a.scope==='pc');
  const days = [...new Set(rows.map(a => a.d))];
  const seg = '<div class="seg2 sm" role="radiogroup" aria-label="Qué actividad ver"><button role="radio" aria-checked="'+(S.actScope==='pc')+'" data-act="actScope" data-arg="pc">'+ic('monitor')+'Esta PC</button><button role="radio" aria-checked="'+(S.actScope==='casa')+'" data-act="actScope" data-arg="casa">'+ic('home')+'Toda la casa</button></div>';
  const av = w => w==='pc' ? '<span class="av pc">'+ic('monitor')+'</span>' : '<span class="av">'+w+'</span>';
  const body = rows.length ? days.map(d => '<h3 class="actday">'+d+'</h3>'+rows.filter(a => a.d===d).map(a =>
      '<div class="arow">'+av(a.who)+'<span>'+a.m+'</span><span class="when">'+(a.pend?'<span class="ptag">'+ic('clock')+'Pendiente de enviar</span>':'')+'<span class="mono">'+a.t+'</span></span></div>').join('')).join('')
    : '<div class="actempty">'+ic('list')+'<b>Aún no hay actividad</b><span class="t-meta">Aquí verás quién cambió qué y cuándo.</span></div>';
  return '<div class="advhead">'+seg+'</div><div class="actlist" id="actlist">'+body+'</div><p class="actfoot">'+ic('lock')+'Nadie puede editar ni borrar esta lista.</p>';
}

/* ---------- almacenamiento en esta PC ---------- */
const RET = {mov:['7 días','30 días','90 días','1 año','Nunca borrar'], vid:['1 día','7 días','30 días','Nunca borrar'], clip:['30 días','90 días','1 año','Nunca borrar'], cap:['10 GB','25 GB','50 GB','100 GB','Otro']};
function storeNums(S){
  const st = S.store;
  if(st.state==='near' || st.state==='limit' || st.state==='full') return {mov:1.1, vid:43.8, clip:0.2};
  return {mov: st.movKept ? STORE.mov : 0, vid: st.videoStored ? STORE.vid : 0, clip: STORE.clip};
}
function capGB(S){ const st = S.store; return st.capOther && Number(st.capVal) > 0 ? Number(st.capVal) : Number(String(st.cap).replace(/\D/g, '')) || 50; }
function retPills(S, key, cur, dis, label){
  return '<div class="ret'+(key==='cap'?' capret':'')+'" role="radiogroup" aria-label="'+label+'">'+RET[key].map(o => {
    const on = key==='cap' ? (S.store.capOther ? o==='Otro' : o===cur) : o===cur;
    return '<button role="radio" aria-checked="'+on+'"'+(dis?' aria-disabled="true"':'')+' data-act="ret" data-arg="'+key+'|'+o+'">'+o+'</button>'; }).join('')+'</div>';
}
function storageView(S){
  const st = S.store, n = storeNums(S), capv = capGB(S), used = n.mov+n.vid+n.clip, pct = v => (v/capv*100).toFixed(2);
  let band = '';
  if(st.state==='full') band = '<div class="notice warn stband" role="alert">'+ic('folder')+'<div><b>No podemos guardar en la carpeta</b><span>Revisa el espacio del disco. Detección y avisos siguen.</span></div><button class="btn btn-secondary btn-sm" data-act="folderChange">Elegir otra carpeta</button></div>';
  else if(st.state==='near') band = '<div class="notice warn stband" role="status">'+ic('drive')+'<div><b>Queda poco espacio: '+num(used, 1)+' GB de '+capv+' GB</b><span>Pronto borraremos el video más antiguo.</span></div></div>';
  else if(st.state==='limit') band = '<div class="notice info stband" role="status">'+ic('trash')+'<div><b>Borramos el video del 01/10 para liberar espacio</b><span>La detección sigue.</span></div></div>';
  const mc = S.moveConsent;
  const trow = (icon, id, name, sub, on, act, key, cur, dis, why) => '<div class="trow"><div class="trow-h"><span class="ci">'+ic(icon)+'</span><span class="grow"><b id="'+id+'">'+name+'</b><span>'+sub+'</span></span>'+sw(on, act, id, dis)+'</div>'+
    retPills(S, key, cur, dis || !on, 'Cuánto tiempo guardar: '+name)+(why?'<p class="why">'+ic('lock')+'<span>'+why+'</span></p>':'')+'</div>';
  return band+'<div class="stwrap" id="stwrap"><div class="stgrid"><div class="stcol">'+
    '<div class="stcard"><h3>Uso</h3><p class="usage-n"><b>'+num(used, 1)+' GB</b><span>de '+capv+' GB</span></p>'+
      '<div class="ubar" role="img" aria-label="Movimientos '+num(n.mov,1)+' GB, video '+num(n.vid,1)+' GB, clips '+num(n.clip,1)+' GB de '+capv+' GB"><i class="u-mov" style="width:'+pct(n.mov)+'%"></i><i class="u-vid" style="width:'+pct(n.vid)+'%"></i><i class="u-clip" style="width:'+pct(n.clip)+'%"></i></div>'+
      '<p class="ulg"><span><i class="u-mov"></i>Movimientos <b>'+num(n.mov,1)+' GB</b></span><span><i class="u-vid"></i>Video <b>'+num(n.vid,1)+' GB</b></span><span><i class="u-clip"></i>Clips <b>'+num(n.clip,1)+' GB</b></span><span>Libre <b>'+num(Math.max(0, capv-used),1)+' GB</b></span></p></div>'+
    '<div class="stcard"><h3>Carpeta</h3><div class="folder"><span class="code" title="'+esc(st.path?STORE.path2:STORE.path)+'">'+esc(st.path?STORE.path2:STORE.path)+'</span><button class="btn btn-secondary btn-xs" data-act="folderChange"'+(st.state==='moving'?' disabled':'')+'>'+ic('folder')+'Cambiar carpeta</button></div>'+
      (st.state==='moving' ? '<div class="moving" role="status">Moviendo '+num(used,1)+' GB… La detección sigue.<div class="tbar"><i style="transform:scaleX(.45)"></i></div></div>' : '')+'</div>'+
    '<div class="stcard"><p class="irow"><span class="ci calma">'+ic('lock')+'</span><span><b>Datos cifrados</b>Solo Te Tengo Captura puede leerlos.</span></p></div>'+
    '<div class="stcard"><p class="irow"><span class="ci">'+ic('cloud')+'</span><span><b>En la nube</b>'+(mc?'Movimientos: 30 días (lo eligió Carmen).':'Movimientos: desactivado.')+' Video: nunca.</span></p></div>'+
  '</div><div class="stcol">'+
    '<div class="stcard"><h3>Qué se guarda aquí</h3>'+
      trow('person', 'st-mov', 'Movimientos (puntos del cuerpo)', 'Sin imagen ni video', mc && st.moves, 'stMov', 'mov', st.retMov, !mc, mc ? '' : 'Requiere el permiso de '+HOME.first+' (se registra en la app).')+
      trow('cam', 'st-vid', 'Video continuo', 'Nunca se sube', st.video, 'stVid', 'vid', st.retVid, false, '')+
      trow('play', 'st-clip', 'Clips de los avisos', '12 s por aviso', st.clips, 'stClip', 'clip', st.retClip, false, '')+'</div>'+
    '<div class="stcard"><h3>Límite de espacio</h3>'+retPills(S, 'cap', st.cap, false, 'Límite de espacio')+
      (st.capOther ? '<div class="cap-other"><label class="sr" for="cap-val">Límite en GB</label><input class="input mono" id="cap-val" inputmode="numeric" value="'+esc(st.capVal)+'" placeholder="75"><span class="t-meta">GB</span></div>' : '')+
      '<p class="capnote">Al llegar, borramos lo más antiguo: primero video, luego movimientos.</p></div>'+
  '</div></div></div>';
}

/* ---------- pestaña Avanzado ---------- */
function advSubs(S){ return (S.adv.on ? [['registro','terminal','Registro en vivo'], ['medidores','gauge','Medidores']] : []).concat([['actividad','list','Actividad'], ['almacenamiento','drive','Almacenamiento']]); }
function advSub(S){ const subs = advSubs(S); return subs.some(x => x[0]===S.adv.sub) ? S.adv.sub : (S.adv.on ? 'registro' : 'actividad'); }
function panelAvanzado(S){
  const a = S.adv, sub = advSub(S), camSel = a.on && (sub==='registro' || sub==='medidores');
  const rooms = S.cams.map(c => c.room);
  const seg = '<div class="seg2" role="tablist" aria-label="Avanzado">'+advSubs(S).map(x => '<button role="tab" id="sub-'+x[0]+'" aria-selected="'+(x[0]===sub)+'" tabindex="'+(x[0]===sub?0:-1)+'" data-act="advSub" data-arg="'+x[0]+'">'+(S.adv.on?'':ic(x[1]))+x[2]+'</button>').join('')+'</div>';
  const btns = '<div class="advbtns"><button class="btn btn-secondary btn-sm" data-act="replayOpen">'+ic('replay')+'Ver qué pasó</button>'+(a.on ? '<button class="btn btn-secondary btn-sm" data-act="diagOpen">'+ic('download')+'Exportar diagnóstico</button>' : '')+'</div>';
  const mode = a.on
    ? '<div class="card advstrip">'+sw(true, 'advToggle', 'adv-l')+'<span class="grow"><b id="adv-l">Modo avanzado</b> · Nada sale de esta PC.</span>'+
        (camSel && rooms.length ? '<span class="cam-l" id="cam-l">Cámara</span><div class="seg2 sm" role="radiogroup" aria-labelledby="cam-l">'+rooms.map(r => '<button role="radio" aria-checked="'+(r===a.cam)+'" data-act="advCam" data-arg="'+esc(r)+'">'+esc(r)+'</button>').join('')+'</div>' : '')+'</div>'
    : '<div class="card advcard"><span class="ci lg">'+ic('sliders')+'</span><div class="grow"><b id="adv-l">Modo avanzado</b><span>Qué detecta cada cámara y por qué avisa. Nada sale de esta PC.</span></div>'+sw(false, 'advToggle', 'adv-l')+'</div>';
  const body = sub==='registro' ? logView(S) : sub==='medidores' ? metersView(S) : sub==='almacenamiento' ? storageView(S) : actView(S);
  return '<h1 class="sr" id="scr-h" tabindex="-1">Avanzado</h1><div class="advhead">'+seg+btns+'</div>'+mode+'<div class="advbody" role="tabpanel" aria-labelledby="sub-'+sub+'">'+body+'</div>';
}

/* =================== Ver qué pasó: repetición del movimiento =================== */
const RP_EV = [{t:T('10:39:10'), k:'inestable', l:'Inestable'}, {t:T('10:41:52'), k:'caida', l:'Caída'}, {t:T('10:43:05'), k:'calma', l:'Se levantó'}];
const RP_GAP = [{a:T('10:20:00'), b:T('10:35:00'), why:'Sin persona en la imagen', s:'Sin persona'}];
const RP_END = T('10:44:00');
const RP_DAYS = [['hoy','Hoy, 23/09/2026','miércoles 23/09'], ['ayer','Ayer, 22/09/2026','martes 22/09'], ['2109','Lunes 21/09/2026','lunes 21/09'], ['2408','Lunes 24/08/2026','lunes 24/08']];
const SPEEDS = [.5, 1, 2, 4];
function spTxt(v){ return String(v).replace('.', ',')+'×'; }
function rpWin(S){ const span = S.rp.zoom==='60' ? 3600 : 600; const w0 = S.rp.w0!=null ? S.rp.w0 : RP_END-span; return [w0, w0+span]; }
function rpEvents(S){ return S.rp.day==='hoy' && S.rp.cam===roomOf(S, 'd1') ? RP_EV : []; }
function rpGap(t){ return RP_GAP.find(g => t >= g.a && t < g.b); }
function rpPose(S, t){
  const g = rpGap(t); if(g) return {p:null, label:g.why, tone:'gap', i:'person'};
  const sway = Math.sin(t*1.7)*1.5;
  if(rpEvents(S).length){
    const I = T('10:39:10'), F = T('10:41:50'), G = T('10:41:52'), C = T('10:42:22'), U = T('10:42:56'), S2 = T('10:43:03'), L = T('10:43:05');
    if(t >= I-4 && t < I+4) return {p:lerpPose('pie', 'inestable', 1-Math.abs(t-I)/4), label:'Movimiento inestable', tone:'inestable', i:'warn'};
    if(t >= F && t < G) return {p:lerpPose('pie', 'caida', (t-F)/2), label:'Posible caída', tone:'caida', i:'warn'};
    if(t >= G && t < U) return {p:POSES.caida, label:t >= C ? 'En el suelo · caída confirmada' : 'En el suelo', tone:'caida', i:'warn'};
    if(t >= U && t < S2) return {p:lerpPose('caida', 'sentado', (t-U)/(S2-U)), label:'En el suelo', tone:'caida', i:'warn'};
    if(t >= S2 && t < L) return {p:lerpPose('sentado', 'pie', (t-S2)/(L-S2)), label:'Se levantó', tone:'calma', i:'arrowUp'};
    if(t >= L && t < L+12) return {p:POSES.pie, label:'Se levantó', tone:'calma', i:'arrowUp', sway:sway};
  }
  return {p:POSES.pie, label:'De pie', tone:'', i:'person', sway:sway};
}
function rpFig(S, t){ const r = rpPose(S, t); return floorSVG(r.p ? skelG(r.p, 200+(r.sway||0), 176, S.rp.video ? '#1E1438' : '#2B1D4E', 1.08) : '', 400, 200, 178); }
function rpValText(S, t){ const e = rpEvents(S).find(x => Math.abs(x.t-t) < 1.5), g = rpGap(t); return hms(t)+(e ? ', '+e.l.toLowerCase() : g ? ', sin datos: '+g.s.toLowerCase() : ''); }
function markSVG(k){
  const sh = k==='caida' ? '<path d="M10 2 18.6 17.2H1.4Z" style="fill:var(--caida)" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/>'
    : k==='inestable' ? '<path d="M10 1.4 18.6 10 10 18.6 1.4 10Z" style="fill:var(--inestable-deep)" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/>'
    : '<circle cx="10" cy="10" r="7.6" style="fill:var(--calma)" stroke="#fff" stroke-width="1.6"/>';
  return '<svg viewBox="0 0 20 20" aria-hidden="true">'+sh+'</svg>';
}
function timeline(S){
  const w = rpWin(S), a = w[0], b = w[1], span = b-a, P = t => ((t-a)/span*100).toFixed(2), t = S.rp.t;
  const evs = rpEvents(S).filter(e => e.t >= a && e.t <= b), big = S.rp.zoom==='60';
  const gaps = RP_GAP.filter(g => g.b > a && g.a < b).map(g => ({a:Math.max(a, g.a), b:Math.min(b, g.b), s:g.s}));
  const step = big ? 600 : 120, first = Math.ceil(a/step)*step, ticks = [];
  for(let x = first; x <= b; x += step) ticks.push(x);
  return '<div class="tl"><div class="tl-track" id="tl-track" role="slider" tabindex="0" aria-label="Línea de tiempo" aria-valuemin="'+a+'" aria-valuemax="'+b+'" aria-valuenow="'+Math.round(t)+'" aria-valuetext="'+rpValText(S, t)+'">'+
    '<span class="tl-gaps" aria-hidden="true">'+gaps.map(g => '<i class="tl-gap" style="left:'+P(g.a)+'%;width:'+((g.b-g.a)/span*100).toFixed(2)+'%"></i>').join('')+'</span>'+
    evs.map(e => '<button class="tl-m" style="left:'+P(e.t)+'%" data-act="rpSeek" data-arg="'+e.t+'" aria-label="'+e.l+', '+hms(e.t)+'" title="'+e.l+' · '+hms(e.t)+'">'+markSVG(e.k)+'</button>').join('')+
    '<i class="tl-head" id="tl-head" style="left:'+P(Math.min(b, Math.max(a, t)))+'%"></i></div>'+
    '<div class="tl-labels" aria-hidden="true">'+ticks.map(x => '<span style="left:'+P(x)+'%">'+hm(x)+'</span>').join('')+
      (big ? '' : evs.map(e => '<span class="ev '+e.k+'" style="left:'+P(e.t)+'%">'+e.l+'</span>').join(''))+
      gaps.map(g => '<span class="ev gap" style="left:'+P((g.a+g.b)/2)+'%">'+g.s+'</span>').join('')+'</div></div>';
}
function rpForm(S){
  const dis = !S.moveConsent, r = S.rp, vOk = S.store.videoStored;
  const days = RP_DAYS.concat(r.state==='old' ? [['old','Lunes 01/09/2026','lunes 01/09']] : []);
  return '<div class="card rp-form'+(dis?' disabled':'')+'"><span class="label" id="rp-cl">Cámara</span><div class="seg2 sm" role="radiogroup" aria-labelledby="rp-cl">'+
      S.cams.map(c => '<button role="radio" aria-checked="'+(c.room===r.cam)+'" data-act="rpCam" data-arg="'+esc(c.room)+'"'+(dis?' disabled':'')+'>'+esc(c.room)+'</button>').join('')+'</div>'+
    '<label class="label" for="rp-day">Fecha</label><select class="input" id="rp-day"'+(dis?' disabled':'')+'>'+days.map(d => '<option value="'+d[0]+'"'+(d[0]===(r.state==='old'?'old':r.day)?' selected':'')+'>'+d[1]+'</option>').join('')+'</select>'+
    '<label class="label" for="rp-hour">Hora</label><input class="input mono" id="rp-hour" value="'+esc(r.hour)+'" inputmode="numeric" maxlength="5" autocomplete="off"'+(dis?' disabled':'')+'>'+
    '<div class="qchips">'+[['Hace 15 min','10:27'], ['Hace 1 hora','09:42'], ['Hoy 07:00','07:00']].map(q => '<button data-act="rpQuick" data-arg="'+q[1]+'"'+(dis?' disabled':'')+'>'+q[0]+'</button>').join('')+'</div>'+
    '<button class="btn btn-primary btn-sm" data-act="rpGo"'+(dis?' disabled':'')+'>'+ic('replay')+'Ver</button>'+
    '<p class="t-meta">'+(dis ? 'No hay movimientos guardados.' : 'Datos desde el 24/08/2026.')+'</p>'+
    '<div class="vtoggle mt12"><span><b id="rp-vl">Sobre el video guardado</b><span>'+(vOk ? 'Nunca sale de esta PC.' : 'No hay video de ese momento.')+'</span></span>'+sw(r.video && vOk, 'rpVideo', 'rp-vl', !vOk || dis, true)+'</div></div>';
}
function panelReplay(S){
  const r = S.rp, day = (RP_DAYS.find(d => d[0]===r.day) || RP_DAYS[0])[2];
  const head = '<div class="rp-head"><button class="back" data-act="replayClose">'+ic('back')+'Volver</button><h1 class="t-title" id="scr-h" tabindex="-1">Ver qué pasó</h1>'+
    '<span class="t-meta" id="rp-title">'+esc(r.cam)+' · '+(r.state==='old' ? 'lunes 01/09' : day)+'</span></div>';
  let main;
  if(!S.moveConsent) main = '<div class="rp-main"><div class="card rp-block"><div class="notice warn">'+ic('lock')+'<div><b>Falta el permiso de '+HOME.first+' para guardar movimientos</b><span>Se registra en la app: Privacidad › Guardar movimientos.</span></div></div></div></div>';
  else if(r.state==='old') main = '<div class="rp-main"><div class="card rp-block"><div class="notice info">'+ic('clock')+'<div><b>Ya no hay movimientos de ese momento.</b><span>Hay datos desde el 24/08/2026. Elige otra fecha.</span></div></div></div></div>';
  else {
    const p = rpPose(S, r.t), evs = rpEvents(S).filter(e => { const w = rpWin(S); return e.t >= w[0] && e.t <= w[1]; });
    const strip = r.video && S.store.videoStored ? '<p class="rp-strip video">'+ic('lock')+'Video guardado solo en esta PC<span>· Queda en el registro de accesos</span></p>'
      : '<p class="rp-strip">'+ic('eye')+'Solo puntos del cuerpo, nunca video<span>· Queda en el registro de accesos</span></p>';
    main = '<div class="rp-main">'+strip+
      '<div class="rp-canvas" id="rp-canvas">'+(r.video && S.store.videoStored ? '<div class="rp-vid">'+roomSVG(DEVS[S.cams.find(c => c.room===r.cam) ? S.cams.find(c => c.room===r.cam).id : 'd1'].view)+'</div>' : '')+
        '<div class="rp-fig" id="rp-fig">'+rpFig(S, r.t)+'</div><span class="rp-phase '+p.tone+'" id="rp-phase" aria-live="polite">'+ic(p.i)+p.label+'</span><span class="rp-clock" id="rp-clock">'+hms(r.t)+'</span></div>'+
      timeline(S)+
      '<div class="rp-ctrl"><button class="ibtn" data-act="rpPrev" aria-label="Evento anterior" title="Evento anterior">'+ic('prev')+'</button>'+
        '<button class="ibtn play" data-act="rpPlay" aria-label="'+(r.playing?'Pausar':'Reproducir')+'" title="'+(r.playing?'Pausar':'Reproducir')+'">'+ic(r.playing?'pauseF':'play')+'</button>'+
        '<button class="ibtn" data-act="rpNext" aria-label="Evento siguiente" title="Evento siguiente">'+ic('next')+'</button>'+
        '<span class="rp-time mono" id="rp-time">'+hms(r.t)+'</span>'+
        '<button class="ibtn speed" data-act="rpSpeed" aria-label="Velocidad: '+spTxt(r.speed)+'" title="Cambiar la velocidad">'+spTxt(r.speed)+'</button>'+
        '<div class="seg2 sm" role="radiogroup" aria-label="Rango de la línea de tiempo"><button role="radio" aria-checked="'+(r.zoom==='10')+'" data-act="rpZoom" data-arg="10">10 min</button><button role="radio" aria-checked="'+(r.zoom==='60')+'" data-act="rpZoom" data-arg="60">1 h</button></div></div>'+
      det(S, 'rpev', 'rp-ev', 'Eventos ('+evs.length+')', evs.length ? evs.map(e => '<button class="evrow" data-act="rpSeek" data-arg="'+e.t+'"><time class="mono">'+hms(e.t)+'</time>'+markSVG(e.k)+'<span>'+e.l+' · '+esc(r.cam)+'</span></button>').join('') : '<p class="t-meta" style="padding:4px 0 8px">Sin eventos.</p>')+'</div>';
  }
  return head+'<div class="rp-grid">'+rpForm(S)+main+'</div>';
}

/* =================== diálogos =================== */
function dlgBox(id, icon, title, text, body, actions){
  return '<div class="dlg-back"><div class="dlg" role="dialog" aria-modal="true" aria-labelledby="'+id+'-t"'+(text?' aria-describedby="'+id+'-d"':'')+' id="'+id+'"><div class="dlg-h">'+icon+'<div><h2 id="'+id+'-t">'+title+'</h2>'+(text?'<p id="'+id+'-d">'+text+'</p>':'')+'</div></div>'+body+'<div class="dlg-actions">'+actions+'</div></div></div>';
}
function dialog(S){
  if(!S.dlg) return '';
  const rooms = S.cams.map(c => c.room), n = storeNums(S), total = n.mov+n.vid+n.clip;
  if(S.dlg==='unlink') return dlgBox('dlg-unlink', '<span class="ci lg caida">'+ic('unlink')+'</span>', '¿Desvincular esta PC?',
    (rooms.length ? 'Se dejan de detectar caídas en '+listY(rooms)+'. ' : '')+'La familia recibirá un aviso.',
    '<label class="checkrow"><input type="checkbox" id="unlink-wipe"'+(S.unlinkWipe?' checked':'')+'><span>Borrar también los datos de esta PC ('+num(total, 1)+' GB)<span>Movimientos, video y clips.</span></span></label>',
    '<button class="btn btn-secondary" data-act="dlgClose">Cancelar</button><button class="btn btn-danger" data-act="unlinkDo">'+ic('unlink')+'Desvincular</button>');
  if(S.dlg==='video') return dlgBox('dlg-video', '<span class="ci lg">'+ic('cam')+'</span>', '¿Guardar video continuo en esta PC?',
    'Se queda en esta PC, nunca se sube. 480p a 8 fps, en partes de 10 min. Ocupa mucho espacio.', '',
    '<button class="btn btn-secondary" data-act="dlgClose">Cancelar</button><button class="btn btn-primary" data-act="videoOn">Activar</button>');
  if(S.dlg==='revoke') return dlgBox('dlg-revoke', '<span class="ci lg aviso">'+ic('person')+'</span>', '¿Borrar los movimientos de esta PC ('+num(STORE.mov, 1)+'&nbsp;GB)?',
    HOME.first+' ya no autoriza guardarlos (lo registró '+HOME.fam.split(' ')[0]+'). No guardamos nuevos y los de la nube se borran. Las alertas siguen.', '',
    '<button class="btn btn-secondary" data-act="revokeKeep">Conservar</button><button class="btn btn-danger" data-act="revokeWipe">'+ic('trash')+'Borrar</button>');
  if(S.dlg==='diag'){
    const d = S.diag;
    const file = '<div class="filebox">'+ic('doc')+'<span class="code">'+(d.step==='done' ? DIAG.dir+'\\' : '')+DIAG.file+'</span>'+(d.step==='done' ? '<small>'+DIAG.size+'</small>' : '')+'</div>';
    if(d.step==='busy') return dlgBox('dlg-diag', '<span class="ci lg">'+ic('download')+'</span>', 'Exportar diagnóstico', 'Un archivo para el equipo de soporte.',
      file+'<div class="prog" role="status"><div class="tbar"><i></i></div><p>Preparando el diagnóstico…</p></div>', '<button class="btn btn-secondary" data-act="diagCancel">Cancelar</button>');
    if(d.step==='done') return dlgBox('dlg-diag', '<span class="ci lg calma">'+ic('check')+'</span>', 'Diagnóstico guardado · '+DIAG.size, 'Envíalo a soporte cuando te lo pidan.',
      file, '<button class="btn btn-secondary" data-act="diagShow">'+ic('folder')+'Mostrar en la carpeta</button><button class="btn btn-primary" data-act="dlgClose">Listo</button>');
    const lists = '<div class="inc"><div class="yes"><h3>Incluye</h3><ul>'+['Registros del programa', 'Versión y sistema operativo', 'Cámaras y habitaciones', 'Umbrales de detección'].map(x => '<li>'+ic('check')+x+'</li>').join('')+'</ul></div>'+
      '<div class="no"><h3>No incluye</h3><ul>'+['Contraseñas ni accesos', 'Imágenes ni video', 'Puntos del cuerpo'].map(x => '<li>'+ic('x')+x+'</li>').join('')+'</ul></div></div>';
    return dlgBox('dlg-diag', '<span class="ci lg">'+ic('download')+'</span>', 'Exportar diagnóstico', 'Un archivo para el equipo de soporte.',
      (d.step==='err' ? '<div class="notice err" role="alert">'+ic('warn')+'<div><b>No pudimos guardar en esa carpeta</b><span>No quedó ningún archivo. Elige otra.</span></div></div>' : lists)+file,
      '<button class="btn btn-secondary" data-act="dlgClose">Cancelar</button><button class="btn btn-primary" data-act="diagSave">'+ic('folder')+(d.step==='err'?'Elegir otra carpeta':'Elegir dónde guardar')+'</button>');
  }
  return '';
}

/* ---------- arranque: ventana de inicio centrada, como en las utilidades de Windows ---------- */
const BOOT_STEPS = ['Iniciando…', 'Abriendo las cámaras…', 'Conectando con Te Tengo…'];
function bootMark(){ return symbolSVG(false, 'class="sp-mark"'); }
function bootWin(o){
  o = o||{}; const pct = o.pct==null ? 34 : o.pct, step = o.step||0;
  return '<div class="boot'+(o.play?' play':'')+'" role="dialog" aria-label="Te Tengo Captura se está iniciando">'+
    '<div class="boot-mark"><span class="sp-glow"></span>'+bootMark()+'</div>'+wordmark(false, true, 'boot-wm')+
    '<div class="boot-foot"><div class="boot-bar" role="progressbar" aria-label="Progreso del inicio" aria-valuemin="0" aria-valuemax="100" aria-valuenow="'+pct+'"><i style="transform:scaleX('+(pct/100)+')"></i></div>'+
    '<p class="boot-st"><span id="boot-st" aria-live="polite">'+BOOT_STEPS[step]+'</span><span class="boot-v">Versión 0.5.0</span></p></div></div>';
}
function desktopBoot(S){ return '<div class="desk corner" aria-label="Escritorio de Windows">'+bootWin()+taskbar(S, {open:true})+'</div>'; }

/* ---------- escritorio: barra de tareas, bandeja y avisos del sistema ---------- */
function trayState(S){
  const peeking = S.peek && connected(S).includes(S.peek) && (S.screen==='main' || S.screen==='vinculada');
  if(peeking) return {k:'live', label:PC.by+' mira una cámara para elegirla'};
  if(!S.linked || PRE_SCREENS.includes(S.screen)) return S.screen==='vinculada' ? {k:'warn', label:'falta elegir las cámaras en la app'} : {k:'off', label:S.screen==='quitada' ? 'se quitó de la vivienda' : 'sin vincular'};
  if(!S.cams.length) return {k:'warn', label:'falta elegir las cámaras en la app'};
  if(S.cams.some(c => isLost(S, c.id))) return {k:'warn', label:'una cámara no responde'};
  if(!S.online) return {k:'warn', label:'sin internet, reintentando'};
  if(!S.consent) return {k:'warn', label:'esperando consentimiento'};
  if(S.live) return {k:'live', label:S.live.who+' está viendo en vivo'};
  if(S.pause) return {k:'idle', label:deRoomD(pausedRoom(S))+' en pausa hasta las '+S.pause};
  return {k:'ok', label:S.cams.length===1 ? 'cuidando '+deRoomD(S.cams[0].room) : 'cuidando '+S.cams.length+' habitaciones'};
}
function taskbar(S, o){
  o = o||{}; const st = trayState(S);
  return '<div class="taskbar"><div class="tk-mid"><span class="tk-app" aria-hidden="true">'+ic('folder')+'</span>'+
    '<button class="tk-app'+(o.open?' open':'')+'" data-act="trayOpen" aria-label="Te Tengo Captura">'+appIcon('sm')+'</button></div>'+
    '<div class="tray"><span class="tray-i" aria-hidden="true">'+ic('chevUp')+'</span>'+
    '<button class="tray-i tray-app'+(o.hl?' hl':'')+'" data-act="trayOpen" aria-label="Abrir Te Tengo Captura: '+st.label+'" title="Te Tengo Captura · '+st.label+'">'+appIcon('xs')+'<i class="tdot '+st.k+'"></i></button>'+
    '<span class="tray-i" aria-hidden="true">'+ic(S.online?'wifi':'wifiOff')+'</span><span class="tray-i" aria-hidden="true">'+ic('volume')+'</span>'+
    '<span class="tk-clock"><span>10:42</span><span>23/09/2026</span></span></div></div>';
}
function osToast(S, kind){
  let t, sub, icon = '';
  const lostCam = S.cams.find(c => isLost(S, c.id));
  if(kind==='lost'){ t = 'La cámara '+(lostCam ? delRoom(lostCam.room)+' ' : '')+'no responde'; sub = 'Revisa el cable USB.'; icon = 'videoOff'; }
  else if(kind==='live'){ t = (S.live ? S.live.who : 'Un familiar')+' está viendo '+deRoomD(S.live ? S.live.room : 'Sala')+' en vivo'; sub = 'No se graba · queda registrado.'; icon = 'eye'; }
  else if(kind==='removed'){ t = 'Esta PC se quitó de la vivienda'; sub = PC.by+' la quitó a las 11:20. Ábrela para vincularla de nuevo.'; icon = 'unlink'; }
  else { t = 'Sigue funcionando en segundo plano';
    if(!S.linked || PRE_SCREENS.includes(S.screen)) sub = 'Ábrelo junto al reloj para vincular esta PC.';
    else if(!S.cams.length) sub = 'Falta elegir las cámaras en la app.';
    else if(lostCam) sub = 'La cámara '+delRoom(lostCam.room)+' está desconectada: revisa el cable USB.';
    else if(!S.online) sub = 'Sin internet: las cámaras siguen cuidando.';
    else if(!S.consent) sub = 'Empieza cuando la familia registre el consentimiento.';
    else if(S.pause) sub = cap1(deRoomD(pausedRoom(S)))+' en pausa hasta las '+S.pause+'.';
    else sub = 'Cuida '+(S.cams.length===1 ? deRoomD(S.cams[0].room) : S.cams.length+' habitaciones')+'. Ábrelo junto al reloj.'; }
  const cls = kind==='lost' ? ' warn' : kind==='live' ? ' live' : kind==='removed' ? ' removed' : '';
  return '<div class="os-toast'+cls+'" role="status"><div class="os-h">'+appIcon('xs')+'<span class="os-t">Te Tengo Captura</span><button class="os-x" data-act="toastClose" aria-label="Cerrar aviso">'+ic('x')+'</button></div>'+
    '<b>'+(icon ? ic(icon) : '')+t+'</b><p>'+sub+'</p></div>';
}
function desktopCorner(S, kind){ return '<div class="desk corner" aria-label="Escritorio de Windows">'+taskbar(S, {hl:true})+osToast(S, kind)+'</div>'; }

/* =================== estados de la galería =================== */
function mk(o){
  const S = baseState();
  for(const k in o){
    if(o[k] && typeof o[k]==='object' && !Array.isArray(o[k]) && S[k] && typeof S[k]==='object' && !Array.isArray(S[k])) S[k] = Object.assign({}, S[k], o[k]);
    else S[k] = o[k];
  }
  return S;
}
const UNL = {screen:'vincular', linked:false, cams:[]};
const ADV = (sub, x) => Object.assign({tab:'avanzado'}, x||{}, {adv:Object.assign({on:true, sub:sub, cam:'Sala'}, (x&&x.adv)||{})});
const ST = x => ADV('almacenamiento', Object.assign({adv:{on:false}}, x||{}));
const RPL = x => Object.assign({tab:'avanzado', replay:true}, x||{}, {rp:Object.assign({cam:'Sala', day:'hoy', hour:'10:40', zoom:'10', t:T('10:41:51'), playing:false, speed:1, video:false, state:null}, (x&&x.rp)||{})});
const DG = step => ADV('registro', {dlg:'diag', diag:{step:step}});
const G = {
  boot:'Arranque', est:'Estado del equipo', bg:'Segundo plano', live:'Vista en vivo',
  vin:'Vincular esta PC', cam:'Cámaras y habitaciones', unl:'Desvincular esta PC', adv:'Avanzado: registro en vivo y medidores',
  act:'Actividad', st:'Almacenamiento en esta PC', rp:'Ver qué pasó', dg:'Exportar diagnóstico'
};
const PRESETS = [
  {g:G.boot, slug:'00-pantalla-de-arranque', name:'Pantalla de arranque', desc:'Al encender la PC: abre las cámaras y se conecta con Te Tengo.', S:mk({screen:'arranque'})},
  {g:G.est, slug:'01-enviando-video', name:'Todo funciona', desc:'Una franja de estado y una fila por cámara.', S:mk({})},
  {g:G.est, slug:'02-en-pausa', name:'Una cámara en pausa', desc:'Luis pausó la Sala desde la app hasta las 11:42; las demás siguen.', S:mk({pause:'11:42'})},
  {g:G.est, slug:'03-esperando-consentimiento', name:'Esperando consentimiento', desc:'Sin consentimiento registrado, ninguna cámara se usa.', S:mk({consent:false})},
  {g:G.est, slug:'04-sin-internet', name:'Sin internet, reintentando', desc:'Se sigue detectando; los avisos esperan la conexión.', S:mk({online:false, retry:8})},
  {g:G.est, slug:'05-webcam-desconectada', name:'Una cámara no responde', desc:'El Pasillo no responde: revisar el cable USB.', S:mk({lost:true})},
  {g:G.bg, slug:'06-aviso-al-cerrar', name:'Aviso al cerrar o minimizar', desc:'Al cerrar, sigue en la bandeja con un punto de estado.', S:mk({screen:'cerrado'})},
  {g:G.bg, slug:'07-aviso-webcam-desconectada', name:'Aviso: cámara desconectada', desc:'Aviso de Windows con la cámara desconectada; punto ámbar.', S:mk({screen:'cerrado', lost:true, kind:'lost'})},
  {g:G.live, slug:'08-viendo-en-vivo', name:'Un familiar ve en vivo', desc:'Carmen mira el Dormitorio: nombre, habitación y hora; punto morado.', S:mk({live:{who:'Carmen', since:'10:42', room:'Dormitorio'}})},
  {g:G.live, slug:'09-aviso-vista-en-vivo', name:'Aviso: un familiar ve en vivo', desc:'Aviso de Windows: quién mira y qué habitación.', S:mk({screen:'cerrado', kind:'live', live:{who:'Carmen', since:'10:42', room:'Dormitorio'}})},

  {g:G.vin, slug:'10-vincular-esta-pc', name:'Vincular esta PC', desc:'QR y código de 8 letras, con 10 minutos de vigencia.', S:mk(UNL)},
  {g:G.vin, slug:'11-codigo-nuevo', name:'Código nuevo al vencer', desc:'El código venció: aparece otro solo.', S:mk(Object.assign({}, UNL, {pair:{code:1, left:600, renewed:true}}))},
  {g:G.vin, slug:'12-errores-en-el-celular', name:'Ayuda: errores en el celular', desc:'Qué hacer si el celular muestra un error.', S:mk(Object.assign({}, UNL, {open:{help:true}}))},
  {g:G.vin, slug:'13-vincular-sin-internet', name:'Sin internet al vincular', desc:'Sin conexión no hay código; se reintenta solo.', S:mk(Object.assign({}, UNL, {online:false, retry:25}))},
  {g:G.vin, slug:'14-te-tengo-no-responde', name:'Te Tengo no responde', desc:'Servidor caído: nada que hacer en la casa; se reintenta solo.', S:mk(Object.assign({}, UNL, {server:false, retry:25}))},
  {g:G.vin, slug:'15-volver-a-vincular', name:'Volver a vincular tras 90 días', desc:'Tras 90 días sin conexión, pide vincular de nuevo.', S:mk(Object.assign({}, UNL, {pair:{re90:true}}))},
  {g:G.vin, slug:'16-vinculacion-rechazada', name:'Vinculación rechazada', desc:'«No reconozco esta PC» en la app: ofrece otro código.', S:mk({screen:'rechazada', linked:false, cams:[]})},
  {g:G.vin, slug:'17-pc-vinculada', name:'PC vinculada', desc:'A qué casa quedó vinculada y qué webcams detectó.', S:mk({screen:'vinculada', cams:[]})},
  {g:G.vin, slug:'18-vinculada-sin-consentimiento', name:'Vinculada sin consentimiento', desc:'Sin consentimiento, las cámaras esperan.', S:mk({screen:'vinculada', cams:[], consent:false})},

  {g:G.cam, slug:'19-camaras-detectadas', name:'Cámaras detectadas', desc:'Webcams «Sin usar»; se asignan en la app.', S:mk({tab:'camaras', cams:[], pick:{sel:'d1'}})},
  {g:G.cam, slug:'20-camaras-de-esta-pc', name:'Cámaras de esta PC', desc:'Tres cámaras con su habitación, elegida en la app.', S:mk({tab:'camaras', pick:{sel:'d2'}})},
  {g:G.cam, slug:'21-viendo-para-elegir', name:'Carmen mira una cámara para elegirla', desc:'Carmen pide la vista previa: luz violeta «No se graba».', S:mk({tab:'camaras', cams:[], peek:'d2', pick:{sel:'d2'}})},
  {g:G.cam, slug:'22-camara-elegida-en-la-app', name:'La PC se actualiza sola', desc:'Carmen eligió una cámara: aviso y fila nueva en Estado.', S:mk({cams:[{id:'d1', room:'Sala', by:'app'}], toast:{kind:'ok', icon:'mobile', text:'Carmen eligió la Webcam USB HD para la Sala'}})},
  {g:G.cam, slug:'23-camara-desconectada', name:'Cámara desconectada', desc:'Punteada; su habitación no pasa a otra cámara.', S:mk({tab:'camaras', lost:true, pick:{sel:'d3'}})},
  {g:G.cam, slug:'24-sin-camaras', name:'Sin cámaras conectadas', desc:'Conectar una webcam y buscar de nuevo.', S:mk({tab:'camaras', cams:[], noCams:true})},
  {g:G.cam, slug:'25-camara-ocupada', name:'Cámara ocupada por otro programa', desc:'Otro programa usa la Logitech C920: cerrarlo.', S:mk({tab:'camaras', cams:[{id:'d1', room:'Sala', by:'app'}], busy:true, pick:{sel:'d2'}})},
  {g:G.cam, slug:'26-se-conecto-otra-webcam', name:'Se conectó otra webcam', desc:'Aparece «Nueva · Sin usar»; las demás se reconocen por su identificador.', S:mk({tab:'camaras', extra:true, pick:{sel:'d4'}})},
  {g:G.cam, slug:'27-elegir-aqui', name:'Elegir aquí, si estás instalando', desc:'Para quien instala: el selector con sus reglas. Aquí, una habitación repetida.', S:mk({tab:'camaras', here:true, cams:[{id:'d1', room:'Sala', by:'app'}, {id:'d2', room:'Dormitorio', by:'app'}], pick:{sel:'d3', otherOn:true, other:'sala', err:'dup', errRoom:'Sala', errPc:'Sala-Rosa'}})},
  {g:G.cam, slug:'28-falta-elegir-camaras', name:'Estado: falta elegir las cámaras en la app', desc:'Vinculada sin cámaras asignadas: se eligen en la app.', S:mk({cams:[]})},

  {g:G.unl, slug:'29-desvincular-esta-pc', name:'Desvincular esta PC', desc:'Confirma qué habitaciones pierden detección; borrar datos es opcional.', S:mk({tab:'camaras', pick:{sel:'d1'}, dlg:'unlink'})},
  {g:G.unl, slug:'30-pc-quitada-desde-el-celular', name:'Quitada desde el celular', desc:'Carmen la quitó desde la app: ofrece vincular de nuevo.', S:mk({screen:'quitada', linked:false, cams:[]})},
  {g:G.unl, slug:'31-aviso-pc-quitada', name:'Aviso: PC quitada', desc:'Aviso de Windows: la PC se quitó de la vivienda.', S:mk({screen:'cerrado', kind:'removed', linked:false, cams:[]})},

  {g:G.adv, slug:'32-modo-avanzado-apagado', name:'Modo avanzado apagado', desc:'Apagado por defecto. Actividad y Almacenamiento siempre visibles.', S:mk({tab:'avanzado'})},
  {g:G.adv, slug:'33-registro-en-vivo', name:'Registro en vivo', desc:'Lo que detecta cada cámara, con ícono, color y filtros.', S:mk(ADV('registro'))},
  {g:G.adv, slug:'34-ver-linea-tecnica', name:'Ver línea técnica', desc:'La línea técnica, solo si se pide, con «Copiar».', S:mk(ADV('registro', {log:Object.assign(baseState().log, {open:'Sala-6'})}))},
  {g:G.adv, slug:'35-registro-en-pausa', name:'Registro en pausa', desc:'Las líneas nuevas esperan y se cuentan.', S:mk(ADV('registro', {log:Object.assign(baseState().log, {paused:true, cut:8})}))},
  {g:G.adv, slug:'36-registro-sin-resultados', name:'Búsqueda sin resultados', desc:'La búsqueda no encontró líneas.', S:mk(ADV('registro', {log:Object.assign(baseState().log, {q:'escalera'})}))},
  {g:G.adv, slug:'37-medidores', name:'Medidores', desc:'Rendimiento, medidas frente a su umbral, fase y esqueleto local.', S:mk(ADV('medidores'))},
  {g:G.adv, slug:'38-medidores-posible-caida', name:'Medidores: posible caída', desc:'Dos medidas pasan su umbral; corre la ventana de 1,48 s.', S:mk(ADV('medidores', {m:Object.assign(baseState().m, {phase:1, m1:.034, m2:38.2, m3:.84, win:.62, pose:'falling', vis:{Nariz:.9, Hombros:.86, Caderas:.74, Tobillos:.55}})}))},
  {g:G.adv, slug:'39-medidores-sin-persona', name:'Medidores sin persona', desc:'Sin nadie en la imagen, sin valores y con el motivo.', S:mk(ADV('medidores', {adv:{cam:'Dormitorio'}}))},
  {g:G.adv, slug:'40-medidores-camara-en-pausa', name:'Medidores con la cámara en pausa', desc:'En pausa: dice a qué hora vuelve.', S:mk(ADV('medidores', {pause:'11:42'}))},

  {g:G.act, slug:'41-actividad', name:'Actividad', desc:'Quién cambió qué y cuándo. Nadie puede borrar filas.', S:mk(ADV('actividad', {acts:[{t:'10:42', m:'Desde esta PC: se activó el modo avanzado'}]}))},
  {g:G.act, slug:'42-actividad-pendiente-de-enviar', name:'Actividad pendiente de enviar', desc:'Sin internet, las filas quedan «Pendiente de enviar».', S:mk(ADV('actividad', {online:false, acts:[{t:'10:42', m:'Desde esta PC: se activó el video continuo', pend:true}, {t:'10:42', m:'Desde esta PC: se activó el modo avanzado', pend:true}]}))},
  {g:G.act, slug:'43-actividad-toda-la-casa', name:'Actividad de toda la casa', desc:'Suma lo hecho en la app y en la otra PC.', S:mk(ADV('actividad', {actScope:'casa'}))},
  {g:G.act, slug:'44-actividad-vacia', name:'Sin actividad', desc:'Todavía no hay cambios.', S:mk(ADV('actividad', {adv:{on:false}, actsEmpty:true}))},

  {g:G.st, slug:'45-almacenamiento', name:'Almacenamiento', desc:'Uso, carpeta, qué se guarda y por cuánto tiempo. Video apagado.', S:mk(ST())},
  {g:G.st, slug:'46-activar-video-continuo', name:'Activar el video continuo', desc:'El video se queda en la PC y nunca se sube.', S:mk(ST({dlg:'video'}))},
  {g:G.st, slug:'47-almacenamiento-con-video', name:'Con video guardado', desc:'Con video continuo: 3,2 GB de 50 GB.', S:mk(ST({store:{video:true, videoStored:true}}))},
  {g:G.st, slug:'48-queda-poco-espacio', name:'Queda poco espacio', desc:'Al 90 % del límite, avisa que borrará el video más antiguo.', S:mk(ST({store:{video:true, videoStored:true, state:'near'}}))},
  {g:G.st, slug:'49-limite-alcanzado', name:'Límite alcanzado', desc:'Se borró el video más antiguo; la detección sigue.', S:mk(ST({store:{video:true, videoStored:true, state:'limit'}}))},
  {g:G.st, slug:'50-disco-lleno', name:'Disco lleno o carpeta no disponible', desc:'No se puede guardar: revisar el disco u otra carpeta.', S:mk(ST({store:{video:true, videoStored:true, state:'full'}}))},
  {g:G.st, slug:'51-moviendo-la-carpeta', name:'Cambiando de carpeta', desc:'Los datos se mueven con la detección activa.', S:mk(ST({store:{state:'moving'}}))},
  {g:G.st, slug:'52-sin-permiso-de-movimientos', name:'Sin permiso para guardar movimientos', desc:'Sin el permiso de Rosa, «Movimientos» queda desactivado.', S:mk(ST({moveConsent:false, store:{movKept:false}}))},
  {g:G.st, slug:'53-borrar-movimientos-de-esta-pc', name:'Permiso revocado: ¿borrar en esta PC?', desc:'Rosa revocó el permiso: ¿borrar también aquí?', S:mk(ST({moveConsent:false, dlg:'revoke'}))},

  {g:G.rp, slug:'54-ver-que-paso', name:'Ver qué pasó', desc:'Esqueleto animado con línea de tiempo y eventos marcados.', S:mk(RPL())},
  {g:G.rp, slug:'55-ver-sobre-el-video', name:'Sobre el video guardado', desc:'El esqueleto sobre el video guardado, que nunca se sube.', S:mk(RPL({store:Object.assign(baseState().store, {video:true, videoStored:true}), rp:{video:true, t:T('10:42:10')}}))},
  {g:G.rp, slug:'56-tramo-sin-datos', name:'Tramo sin datos', desc:'Vista de 1 hora: el tramo sin persona va rayado y se salta.', S:mk(RPL({rp:{zoom:'60', w0:T('09:44:00'), t:T('10:35:00')}, toast:{kind:'warn', icon:'clock', text:'Sin datos de 10:20 a 10:35 · Sin persona en la imagen'}}))},
  {g:G.rp, slug:'57-repeticion-sin-permiso', name:'Sin permiso de movimientos', desc:'Sin el permiso de Rosa no hay qué repetir.', S:mk(RPL({moveConsent:false}))},
  {g:G.rp, slug:'58-fuera-del-plazo', name:'Fuera del plazo', desc:'Ya no hay datos de ese momento; dice desde cuándo hay.', S:mk(RPL({rp:{state:'old'}}))},
  {g:G.rp, slug:'59-acceso-registrado', name:'Acceso registrado', desc:'Al cerrar, confirma que quedó en el registro de accesos.', S:mk({tab:'avanzado', toast:{kind:'ok', icon:'eye', text:'Acceso registrado'}})},

  {g:G.dg, slug:'60-exportar-diagnostico', name:'Exportar diagnóstico', desc:'Qué incluye y qué no, antes de guardar.', S:mk(DG('intro'))},
  {g:G.dg, slug:'61-preparando-diagnostico', name:'Preparando el diagnóstico', desc:'Barra de progreso.', S:mk(DG('busy'))},
  {g:G.dg, slug:'62-diagnostico-guardado', name:'Diagnóstico guardado', desc:'Nombre, tamaño y «Mostrar en la carpeta».', S:mk(DG('done'))},
  {g:G.dg, slug:'63-error-al-guardar', name:'Error al guardar', desc:'No queda archivo a medias; se elige otra carpeta.', S:mk(DG('err'))}
];
function renderPreset(p, o){ return p.S.screen==='cerrado' ? desktopCorner(p.S, p.S.kind) : p.S.screen==='arranque' ? desktopBoot(p.S) : win(p.S, o); }

if(typeof module!=='undefined') module.exports = {PRESETS, renderPreset, win, baseState, logotipo, G,
  ic, esc, appIcon, LOGO, titlebar, tabbar, roomSVG, POSES, lerpPose, skelG, floorSVG, sw, DEVS, HOME, PC, num, T, hms, sec, det, mk};
