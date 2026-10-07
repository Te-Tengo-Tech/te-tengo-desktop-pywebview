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
  folder:'<path d="M3 6.5a2 2 0 0 1 2-2h4.2l2 2.3H19a2 2 0 0 1 2 2v8.7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z"/>'
};
function ic(n, extra){ return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"'+(extra?' '+extra:'')+'>'+P[n]+'</svg>'; }
const WG = {min:'<path d="M0 5.5h10"/>', max:'<rect x=".5" y=".5" width="9" height="9" rx="1.4"/>', close:'<path d="M.6.6l8.8 8.8M9.4.6.6 9.4"/>'};
function wg(n){ return '<svg viewBox="0 0 10 10" fill="none" stroke="currentColor" stroke-width="1" aria-hidden="true">'+WG[n]+'</svg>'; }
function esc(s){ return String(s==null?'':s).replace(/[&<>"]/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }
/* ---------- Marca Te Tengo: «La T que sostiene» (archivos fuente en 05-prototipos/marca/) ---------- */
const BRAND={morado:'#4A2A85', coral:'#E8765A', durazno:'#FFB59C',
  te:'M138.16 80L138.16 46.85L124.52 46.85L124.52 37.25L162.67 37.25L162.67 46.85L149.04 46.85L149.04 80L138.16 80ZM178.09 80.77Q172.91 80.77 168.91 78.78Q164.91 76.8 162.64 73.02Q160.36 69.25 160.36 63.87Q160.36 58.82 162.73 55.1Q165.1 51.39 169.04 49.34Q172.97 47.3 177.64 47.3Q181.61 47.3 184.78 48.7Q187.95 50.11 190.16 52.7Q192.36 55.3 193.42 58.88Q194.48 62.46 194.16 66.88L170.6 66.88Q170.99 68.35 171.66 69.44Q172.33 70.53 173.26 71.26Q174.19 72 175.34 72.35Q176.49 72.7 177.77 72.7Q179.95 72.7 181.55 72.1Q183.15 71.49 183.98 70.46L192.24 73.54Q189.61 77.31 185.74 79.04Q181.87 80.77 178.09 80.77ZM170.54 60.74L184.56 60.74Q184.36 58.75 183.47 57.5Q182.57 56.26 181.13 55.65Q179.69 55.04 177.96 55.04Q176.24 55.04 174.7 55.62Q173.16 56.19 172.08 57.44Q170.99 58.69 170.54 60.74Z',
  tengo:'M229.93 80L229.93 46.85L216.3 46.85L216.3 37.25L254.44 37.25L254.44 46.85L240.81 46.85L240.81 80L229.93 80ZM269.87 80.77Q264.68 80.77 260.68 78.78Q256.68 76.8 254.41 73.02Q252.14 69.25 252.14 63.87Q252.14 58.82 254.51 55.1Q256.88 51.39 260.81 49.34Q264.75 47.3 269.42 47.3Q273.39 47.3 276.56 48.7Q279.72 50.11 281.93 52.7Q284.14 55.3 285.2 58.88Q286.25 62.46 285.93 66.88L262.38 66.88Q262.76 68.35 263.44 69.44Q264.11 70.53 265.04 71.26Q265.96 72 267.12 72.35Q268.27 72.7 269.55 72.7Q271.72 72.7 273.32 72.1Q274.92 71.49 275.76 70.46L284.01 73.54Q281.39 77.31 277.52 79.04Q273.64 80.77 269.87 80.77ZM262.32 60.74L276.33 60.74Q276.14 58.75 275.24 57.5Q274.35 56.26 272.91 55.65Q271.47 55.04 269.74 55.04Q268.01 55.04 266.48 55.62Q264.94 56.19 263.85 57.44Q262.76 58.69 262.32 60.74ZM290.48 80L290.48 48.26L299.88 48.26L301.04 52.35Q301.74 51.26 303.12 50.08Q304.49 48.9 306.48 48.1Q308.46 47.3 310.83 47.3Q314.73 47.3 317.1 48.7Q319.47 50.11 320.56 52.9Q321.64 55.68 321.64 59.71L321.64 80L311.08 80L311.08 61.89Q311.08 59.65 310.6 58.21Q310.12 56.77 309.13 56.06Q308.14 55.36 306.54 55.36Q303.6 55.36 302.32 57.54Q301.04 59.71 301.04 63.87L301.04 80L290.48 80ZM344.04 93.12Q341.42 93.12 338.67 92.48Q335.92 91.84 333.55 90.27Q331.18 88.7 329.58 85.95L337.84 82.18Q338.73 83.52 340.24 84.38Q341.74 85.25 344.24 85.25Q345.64 85.25 347.02 84.74Q348.4 84.22 349.29 82.94Q350.19 81.66 350.19 79.42L350.19 73.86Q348.01 76.42 345.32 77.57Q342.64 78.72 340.14 78.72Q336.75 78.72 333.58 76.86Q330.41 75.01 328.43 71.58Q326.44 68.16 326.44 63.36Q326.44 57.73 328.43 54.18Q330.41 50.62 333.48 48.93Q336.56 47.23 339.76 47.23Q342.64 47.23 345.48 48.54Q348.33 49.86 350.19 52.48L351.47 48.26L360.68 48.26L360.68 77.31Q360.68 83.01 358.6 86.5Q356.52 89.98 352.78 91.55Q349.04 93.12 344.04 93.12ZM343.98 70.59Q345.77 70.59 347.28 69.92Q348.78 69.25 349.71 67.62Q350.64 65.98 350.64 63.1Q350.64 60.16 349.71 58.46Q348.78 56.77 347.28 56.06Q345.77 55.36 343.98 55.36Q341.36 55.36 339.34 57.09Q337.32 58.82 337.32 62.78Q337.32 66.75 339.34 68.67Q341.36 70.59 343.98 70.59ZM382.57 80.77Q379.24 80.77 376.17 79.74Q373.1 78.72 370.67 76.64Q368.24 74.56 366.86 71.39Q365.48 68.22 365.48 63.94Q365.48 59.65 366.86 56.51Q368.24 53.38 370.67 51.33Q373.1 49.28 376.17 48.29Q379.24 47.3 382.57 47.3Q385.96 47.3 389 48.29Q392.04 49.28 394.48 51.33Q396.91 53.38 398.28 56.51Q399.66 59.65 399.66 63.94Q399.66 68.22 398.28 71.39Q396.91 74.56 394.48 76.64Q392.04 78.72 389 79.74Q385.96 80.77 382.57 80.77ZM382.57 72.7Q384.49 72.7 385.9 71.71Q387.31 70.72 388.11 68.77Q388.91 66.82 388.91 63.94Q388.91 60.99 388.08 59.1Q387.24 57.22 385.84 56.29Q384.43 55.36 382.57 55.36Q380.78 55.36 379.34 56.29Q377.9 57.22 377.07 59.1Q376.24 60.99 376.24 63.94Q376.24 66.82 377.04 68.77Q377.84 70.72 379.28 71.71Q380.72 72.7 382.57 72.7Z',
  captura:'M445.42 80.77Q438.95 80.77 434.38 78.02Q429.8 75.26 427.34 70.27Q424.87 65.28 424.87 58.62Q424.87 51.84 427.43 46.88Q429.99 41.92 434.7 39.2Q439.4 36.48 445.74 36.48Q451.56 36.48 455.98 39.07Q460.39 41.66 462.7 46.27L455.34 48.96Q453.93 46.21 451.34 44.8Q448.75 43.39 445.42 43.39Q442.15 43.39 439.43 45.15Q436.71 46.91 435.15 50.3Q433.58 53.7 433.58 58.62Q433.58 63.49 435.11 66.88Q436.65 70.27 439.4 72.06Q442.15 73.86 445.61 73.86Q447.72 73.86 449.64 73.28Q451.56 72.7 453.13 71.46Q454.7 70.21 455.66 68.29L462.95 70.98Q460.52 75.65 455.91 78.21Q451.31 80.77 445.42 80.77ZM477.1 80.77Q474.09 80.77 471.59 79.65Q469.1 78.53 467.59 76.48Q466.09 74.43 466.09 71.55Q466.09 67.78 468.75 65.47Q471.4 63.17 476.27 61.92Q481.13 60.67 487.72 60.1L487.72 59.26Q487.72 56.32 486.12 54.72Q484.52 53.12 481.32 53.12Q478.95 53.12 477.29 54.21Q475.63 55.3 475.11 57.41L468.2 55.04Q469.67 51.65 473.16 49.6Q476.65 47.55 481.51 47.55Q488.3 47.55 491.72 50.62Q495.15 53.7 495.15 60.61L495.15 67.78Q495.15 70.08 495.31 72.35Q495.47 74.62 495.72 76.58Q495.98 78.53 496.3 80L489.07 80L487.85 75.97Q486.25 78.4 483.56 79.58Q480.87 80.77 477.1 80.77ZM479.72 75.14Q481.96 75.14 483.75 74.4Q485.55 73.66 486.63 71.87Q487.72 70.08 487.72 66.94L487.72 65.22Q481.39 65.73 477.9 67.04Q474.41 68.35 474.41 71.1Q474.41 72.9 475.85 74.02Q477.29 75.14 479.72 75.14ZM503.15 90.37L503.15 48.26L509.61 48.26L511.02 52.86Q511.98 51.14 513.55 49.95Q515.11 48.77 517 48.16Q518.89 47.55 520.94 47.55Q524.84 47.55 527.98 49.54Q531.11 51.52 532.94 55.23Q534.76 58.94 534.76 64.19Q534.76 69.38 532.94 73.09Q531.11 76.8 527.98 78.78Q524.84 80.77 520.94 80.77Q518.89 80.77 517 80.13Q515.11 79.49 513.55 78.27Q511.98 77.06 511.02 75.33L511.02 90.37L503.15 90.37ZM518.57 74.5Q521.96 74.5 524.2 71.84Q526.44 69.18 526.44 64.19Q526.44 59.26 524.2 56.54Q521.96 53.82 518.57 53.82Q515.18 53.82 512.94 56.32Q510.7 58.82 510.7 64.06Q510.7 69.25 512.94 71.87Q515.18 74.5 518.57 74.5ZM551.85 80Q548.33 80 546.31 79.36Q544.3 78.72 543.47 76.86Q542.63 75.01 542.63 71.49L542.63 54.34L537.32 54.34L537.32 48.26L542.63 48.26L542.63 40.32L550.51 40.32L550.51 48.26L557.23 48.26L557.23 54.34L550.51 54.34L550.51 69.63Q550.51 72.06 551.24 72.77Q551.98 73.47 554.22 73.47L557.23 73.47L557.23 80L551.85 80ZM573.93 80.77Q569.9 80.77 567.56 79.2Q565.23 77.63 564.23 74.72Q563.24 71.81 563.24 67.84L563.24 48.26L571.11 48.26L571.11 65.79Q571.11 68.1 571.43 70.08Q571.75 72.06 572.94 73.25Q574.12 74.43 576.75 74.43Q580.14 74.43 581.77 72.19Q583.4 69.95 583.4 65.28L583.4 48.26L591.27 48.26L591.27 80L584.75 80L583.4 75.46Q582.06 77.82 579.88 79.3Q577.71 80.77 573.93 80.77ZM599.15 80L599.15 48.26L605.23 48.26L606.95 54.08Q607.98 51.84 609.51 50.37Q611.05 48.9 613.1 48.16Q615.15 47.42 617.64 47.55L617.64 55.42Q613.93 55.17 611.56 56.16Q609.19 57.15 608.11 59.36Q607.02 61.57 607.02 65.02L607.02 80L599.15 80ZM630.76 80.77Q627.75 80.77 625.26 79.65Q622.76 78.53 621.26 76.48Q619.75 74.43 619.75 71.55Q619.75 67.78 622.41 65.47Q625.07 63.17 629.93 61.92Q634.79 60.67 641.39 60.1L641.39 59.26Q641.39 56.32 639.79 54.72Q638.19 53.12 634.99 53.12Q632.62 53.12 630.95 54.21Q629.29 55.3 628.78 57.41L621.87 55.04Q623.34 51.65 626.83 49.6Q630.31 47.55 635.18 47.55Q641.96 47.55 645.39 50.62Q648.81 53.7 648.81 60.61L648.81 67.78Q648.81 70.08 648.97 72.35Q649.13 74.62 649.39 76.58Q649.64 78.53 649.96 80L642.73 80L641.51 75.97Q639.91 78.4 637.23 79.58Q634.54 80.77 630.76 80.77ZM633.39 75.14Q635.63 75.14 637.42 74.4Q639.21 73.66 640.3 71.87Q641.39 70.08 641.39 66.94L641.39 65.22Q635.05 65.73 631.56 67.04Q628.07 68.35 628.07 71.1Q628.07 72.9 629.51 74.02Q630.95 75.14 633.39 75.14Z'};
function symbolParts(stroke, dot){ return '<g fill="none" stroke="'+stroke+'" stroke-width="13" stroke-linecap="round"><path d="M60 60 V96"/><path d="M22 38 Q60 80 98 38"/></g><circle cx="60" cy="38" r="11" fill="'+dot+'"/>'; }
function symbolSVG(dark, attrs){ return '<svg viewBox="0 0 120 120" aria-hidden="true"'+(attrs?' '+attrs:'')+'>'+symbolParts(dark?'#FFFFFF':BRAND.morado, dark?BRAND.durazno:BRAND.coral)+'</svg>'; }
const LOGO = '<svg viewBox="0 0 120 120" aria-hidden="true"><rect width="120" height="120" rx="28" fill="'+BRAND.morado+'"/>'+symbolParts('#FFFFFF', BRAND.durazno)+'</svg>';
/* logotipo horizontal: símbolo + «Te Tengo» (+ «Captura» en el agente de escritorio) */
function logotipo(dark, withCaptura, cls){
  const w = withCaptura ? 638.91 : 387.45;
  return '<svg class="logotipo'+(cls?' '+cls:'')+'" viewBox="15.5 27 '+w+' 75.5" role="img" aria-label="Te Tengo'+(withCaptura?' Captura':'')+'">'+
    symbolParts(dark?'#FFFFFF':BRAND.morado, dark?BRAND.durazno:BRAND.coral)+
    '<path fill="'+(dark?'#FFFFFF':BRAND.morado)+'" d="'+BRAND.te+'"/><path fill="'+(dark?BRAND.durazno:BRAND.coral)+'" d="'+BRAND.tengo+'"/>'+
    (withCaptura?'<path fill="'+(dark?'rgba(255,255,255,.8)':'#4F4766')+'" d="'+BRAND.captura+'"/>':'')+'</svg>';
}
/* solo las letras, para el arranque */
function wordmark(dark, withCaptura, cls){
  const w = withCaptura ? 529.91 : 278.45;
  return '<svg class="wordmark'+(cls?' '+cls:'')+'" viewBox="124.5 37 '+w+' 57" role="img" aria-label="Te Tengo'+(withCaptura?' Captura':'')+'">'+
    '<path fill="'+(dark?'#FFFFFF':BRAND.morado)+'" d="'+BRAND.te+'"/><path fill="'+(dark?BRAND.durazno:BRAND.coral)+'" d="'+BRAND.tengo+'"/>'+
    (withCaptura?'<path fill="'+(dark?'rgba(255,255,255,.8)':'#4F4766')+'" d="'+BRAND.captura+'"/>':'')+'</svg>';
}
function appIcon(cls){ return '<span class="appicon'+(cls?' '+cls:'')+'">'+LOGO+'</span>'; }

/* ---------- datos: prueba piloto ----------
   Una sola webcam USB, instalada y configurada por el equipo del proyecto. La configuración vive en un
   archivo fijo en esta PC; el programa no vincula cámaras. El nombre de la habitación,
   las pausas y el consentimiento se gestionan en la app Te Tengo. */
const HOME = {who:'Rosa Huamán', fam:'Carmen Huamán', addr:'Jr. Los Pinos 482, San Miguel, Lima'};
const CONF = {webcam:'Webcam USB HD (1080p)', spec:'USB · 1920 × 1080', installed:'22/09/2026'};
function enRoom(r){ return ({Sala:'en la sala',Dormitorio:'en el dormitorio',Cocina:'en la cocina',Pasillo:'en el pasillo'})[r] || 'en '+String(r).toLowerCase(); }

function baseState(){
  return {screen:'estado', room:'Sala', online:true, consent:true, pause:null, lost:false, retry:8, ago:2, toast:null};
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
  } else {
    s+='<rect x="30" y="34" width="54" height="104" rx="3" fill="'+wood+'"/><circle cx="74" cy="90" r="3" fill="'+furn2+'"/>';
    s+='<rect x="236" y="34" width="54" height="104" rx="3" fill="'+wood+'"/><circle cx="246" cy="90" r="3" fill="'+furn2+'"/>';
    s+='<rect x="128" y="44" width="64" height="42" rx="3" fill="#fff" stroke="'+furn+'" stroke-width="3"/><path d="M136 78l14-16 10 10 8-6 16 12" stroke="'+furn2+'" stroke-width="2.5" fill="none" stroke-linejoin="round"/>';
    s+='<path d="M110 180l20-42h60l20 42Z" fill="'+f2+'"/>';
  }
  return s+'</svg>';
}

/* ---------- ventana ---------- */
function titlebar(){
  return '<div class="tb"><div class="tb-app">'+appIcon('xs')+'<span>Te Tengo Captura</span></div><div class="tb-btns">'+
    '<button class="tb-btn" data-act="minimize" aria-label="Minimizar" title="Minimizar">'+wg('min')+'</button>'+
    '<button class="tb-btn" aria-disabled="true" tabindex="-1" aria-label="Maximizar (no disponible)" title="Maximizar">'+wg('max')+'</button>'+
    '<button class="tb-btn close" data-act="close" aria-label="Cerrar" title="Cerrar">'+wg('close')+'</button></div></div>';
}
function win(S, o){
  o = o||{};
  const toast = S.toast ? '<div class="wtoast '+S.toast.kind+'" role="status">'+ic(S.toast.icon||'check')+'<span>'+S.toast.text+'</span></div>' : '';
  return '<div class="win'+(o.flat?' flat':'')+'" aria-label="Te Tengo Captura">'+titlebar()+'<div class="wb">'+scrEstado(S, o.enter||'')+toast+'</div></div>';
}

/* ---------- estado del equipo (única pantalla de la ventana) ---------- */
function camState(S){
  if(S.lost) return {k:'off', t:'Sin conexión', s:'Webcam desconectada: revisa el cable USB', i:'videoOff'};
  if(!S.online) return {k:'off', t:'Sin conexión', s:'Esperando internet', i:'wifiOff'};
  if(!S.consent) return {k:'consent', t:'Esperando consentimiento', s:'No se envía video', i:'doc'};
  if(S.pause) return {k:'pause', t:'En pausa', s:'Hasta las <span class="mono">'+S.pause+'</span> · desde la app', i:'pause'};
  return {k:'send', t:'Enviando', s:'Hace '+S.ago+' s', i:'upload'};
}
function health(S){
  const H=(cls,k,icon,t,s,extra)=>'<div class="health '+cls+'" role="status"><span class="st '+k+'">'+ic(icon)+'</span><div class="grow"><b>'+t+'</b><span>'+s+'</span></div>'+(extra||'')+'</div>';
  if(S.lost) return H('warn lost','off','videoOff','Webcam desconectada: revisa el cable USB','Dejamos de recibir imagen de la '+CONF.webcam+'. Conéctala de nuevo al mismo puerto USB; el envío se reanuda solo.',
    '<button class="btn btn-secondary btn-sm" data-act="rescan">'+ic('refresh')+'Buscar de nuevo</button>');
  if(!S.online) return H('dark','off','wifiOff','Sin internet · reintentando en <span class="mono" id="retry">'+S.retry+'</span> s','La webcam sigue conectada a esta PC. El envío se reanuda solo cuando vuelva la conexión.',
    '<button class="btn btn-ondark btn-sm" data-act="retryNow">'+ic('refresh')+'Reintentar ahora</button>');
  if(!S.consent) return H('warn','consent','doc','Esperando consentimiento','La cámara no envía video hasta que la familia registre el consentimiento de '+HOME.who.split(' ')[0]+' en la app Te Tengo.');
  if(S.pause) return H('idle','pause','pause','En pausa hasta las <span class="mono">'+S.pause+'</span>','La familia pausó la cámara desde la app Te Tengo. El envío se reanuda solo a esa hora.');
  return H('ok','send','upload','Enviando video · conectado','Video cifrado · último envío hace '+S.ago+' s');
}
function scrEstado(S, enter){
  const st=camState(S);
  return sec('estado', enter,
    '<header class="cam-head"><div><h1 class="t-title" id="scr-h" tabindex="-1">Vivienda de '+HOME.who+'</h1><p class="t-meta mt4">'+ic('home')+HOME.addr+'</p></div></header>'+
    health(S)+
    '<div class="est-grid">'+
      '<section class="card est-cam" aria-labelledby="cam-h"><span class="thumb art'+(st.k!=='send'?' dim':'')+'">'+roomSVG(S.room)+'</span>'+
        '<div class="est-cam-b"><p class="grp-l">Cámara de esta casa</p><h2 class="t-h2" id="cam-h">'+esc(S.room)+'</h2>'+
        '<p class="cam-dev">'+ic('usb')+esc(CONF.webcam)+'</p>'+
        '<div class="cam-st"><span class="st '+st.k+'">'+ic(st.i)+'</span><span class="grow"><b class="stx '+st.k+'">'+st.t+'</b><span class="t-meta">'+st.s+'</span></span></div></div></section>'+
      '<section class="card est-conf" aria-labelledby="conf-h"><h2 class="conf-h" id="conf-h">'+ic('lock')+'Configurada por el equipo del proyecto</h2>'+
        '<dl class="conf-kv">'+
        '<div><dt>Vivienda</dt><dd>'+HOME.who+'</dd></div>'+
        '<div><dt>Webcam</dt><dd>'+CONF.webcam+'<span>'+CONF.spec+'</span></dd></div>'+
        '<div><dt>Habitación</dt><dd>'+esc(S.room)+'<span>El nombre se cambia en la app Te Tengo</span></dd></div>'+
        '<div><dt>Instalación</dt><dd>'+CONF.installed+'</dd></div>'+
        '</dl><p class="conf-note">'+ic('info')+'<span>Solo lectura. Esta PC usa una configuración fija; si algo no funciona, avisa al equipo del proyecto.</span></p></section>'+
    '</div>'+
    '<p class="scr-foot">'+ic('mobile')+'Las pausas, el consentimiento, el nombre de la habitación y las alertas se gestionan en la app Te Tengo.<span class="sep"></span>'+ic('power')+'Se inicia con Windows</p>');
}
function sec(cls, enter, inner){ return '<section class="scr'+(cls?' '+cls:'')+(enter?' '+enter:'')+'" aria-labelledby="scr-h">'+inner+'</section>'; }

/* ---------- arranque: ventana de inicio centrada, como en las utilidades de Windows ---------- */
const BOOT_STEPS = ['Iniciando…', 'Abriendo la webcam configurada…', 'Conectando con Te Tengo…'];
/* El símbolo por partes: los brazos se abren, el punto cae y lo reciben; luego se dibuja el fuste. */
function bootMark(){
  return '<svg class="sp-mark" viewBox="0 0 120 120" aria-hidden="true"><g fill="none" stroke="#FFFFFF" stroke-width="13" stroke-linecap="round">'+
    '<path class="sp-stem" pathLength="1" d="M60 60 V96"/>'+
    '<g class="sp-catch"><path class="sp-arm" pathLength="1" d="M60 59 Q41 59 22 38"/><path class="sp-arm" pathLength="1" d="M60 59 Q79 59 98 38"/>'+
    '<circle class="sp-dot" cx="60" cy="38" r="11" fill="'+BRAND.durazno+'" stroke="none"/></g></g></svg>';
}
function bootWin(o){
  o = o||{}; const pct = o.pct==null ? 34 : o.pct, step = o.step||0;
  return '<div class="boot'+(o.play?' play':'')+'" role="dialog" aria-label="Te Tengo Captura se está iniciando">'+
    '<div class="boot-mark">'+bootMark()+'</div>'+wordmark(true, true, 'boot-wm')+
    '<div class="boot-foot"><div class="boot-bar" role="progressbar" aria-label="Progreso del inicio" aria-valuemin="0" aria-valuemax="100" aria-valuenow="'+pct+'"><i style="transform:scaleX('+(pct/100)+')"></i></div>'+
    '<p class="boot-st"><span id="boot-st" aria-live="polite">'+BOOT_STEPS[step]+'</span><span class="boot-v">Versión 1.0</span></p></div></div>';
}
function desktopBoot(S){ return '<div class="desk corner" aria-label="Escritorio de Windows">'+bootWin()+taskbar(S,{open:true})+'</div>'; }

/* ---------- escritorio: barra de tareas, bandeja y avisos del sistema ---------- */
function trayState(S){
  if(S.lost) return {k:'warn', label:'webcam desconectada'};
  if(!S.online) return {k:'warn', label:'sin internet, reintentando'};
  if(!S.consent) return {k:'warn', label:'esperando consentimiento'};
  if(S.pause) return {k:'idle', label:'en pausa hasta las '+S.pause};
  return {k:'ok', label:'enviando video de la cámara '+(S.room==='Sala'?'de la sala':'de '+S.room)};
}
function taskbar(S, o){
  o=o||{}; const st=trayState(S);
  return '<div class="taskbar"><div class="tk-mid"><span class="tk-app" aria-hidden="true">'+ic('folder')+'</span>'+
    '<button class="tk-app'+(o.open?' open':'')+'" data-act="trayOpen" aria-label="Te Tengo Captura">'+appIcon('sm')+'</button></div>'+
    '<div class="tray"><span class="tray-i" aria-hidden="true">'+ic('chevUp')+'</span>'+
    '<button class="tray-i tray-app'+(o.hl?' hl':'')+'" data-act="trayOpen" aria-label="Abrir Te Tengo Captura: '+st.label+'" title="Te Tengo Captura · '+st.label+'">'+appIcon('xs')+'<i class="tdot '+st.k+'"></i></button>'+
    '<span class="tray-i" aria-hidden="true">'+ic(S.online?'wifi':'wifiOff')+'</span><span class="tray-i" aria-hidden="true">'+ic('volume')+'</span>'+
    '<span class="tk-clock"><span>10:42</span><span>24/09/2026</span></span></div></div>';
}
/* aviso del sistema: al cerrar o minimizar la ventana (kind 'closed') o si la webcam se desconecta con la ventana cerrada (kind 'lost') */
function osToast(S, kind){
  let t, sub;
  if(kind==='lost'){ t='La webcam se desconectó'; sub='Revisa que el cable USB de la '+CONF.webcam+' esté bien conectado. Mientras tanto no se envía video.'; }
  else { t='Te Tengo Captura sigue funcionando en segundo plano';
    if(S.lost) sub='La webcam está desconectada: revisa el cable USB. Ábrelo desde su ícono, junto al reloj.';
    else if(!S.online) sub='Seguirá intentando conectarse a internet. Ábrelo desde su ícono, junto al reloj.';
    else if(!S.consent) sub='Empezará a enviar cuando la familia complete el consentimiento en la app Te Tengo.';
    else if(S.pause) sub='La cámara está en pausa hasta las '+S.pause+'. Ábrelo desde su ícono, junto al reloj.';
    else sub='Sigue enviando el video de la cámara. Ábrelo desde su ícono, junto al reloj.'; }
  return '<div class="os-toast'+(kind==='lost'?' warn':'')+'" role="status"><div class="os-h">'+appIcon('xs')+'<span class="os-t">Te Tengo Captura</span><button class="os-x" data-act="toastClose" aria-label="Cerrar aviso">'+ic('x')+'</button></div>'+
    '<b>'+(kind==='lost'?ic('videoOff'):'')+t+'</b><p>'+sub+'</p></div>';
}
function desktopCorner(S, kind){ return '<div class="desk corner" aria-label="Escritorio de Windows">'+taskbar(S,{hl:true})+osToast(S, kind)+'</div>'; }

/* ---------- estados de la galería ---------- */
function mk(o){ const S=baseState(); for(const k in o) S[k]=o[k]; return S; }
const PRESETS = [
  {g:'Arranque', slug:'00-pantalla-de-arranque', name:'Pantalla de arranque', desc:'Ventana de inicio al encender la PC o abrir el programa: el símbolo se arma, abre la webcam configurada y se conecta con Te Tengo.', S:mk({screen:'arranque'})},
  {g:'Estado del equipo', slug:'01-enviando-video', name:'Enviando video', desc:'Ventana principal: la vivienda y la cámara, de solo lectura, configuradas por el equipo del proyecto; la webcam envía su video cifrado.', S:mk({})},
  {g:'Estado del equipo', slug:'02-en-pausa', name:'En pausa hasta una hora', desc:'La familia pausó la cámara desde la app: no se envía video hasta las 15:00 y luego se reanuda solo.', S:mk({pause:'15:00'})},
  {g:'Estado del equipo', slug:'03-esperando-consentimiento', name:'Esperando consentimiento', desc:'Sin el consentimiento registrado en la app, la webcam no envía video.', S:mk({consent:false})},
  {g:'Estado del equipo', slug:'04-sin-internet', name:'Sin internet, reintentando', desc:'La webcam sigue conectada; el envío se reanuda solo cuando vuelve la conexión.', S:mk({online:false, retry:8})},
  {g:'Estado del equipo', slug:'05-webcam-desconectada', name:'Webcam desconectada', desc:'La webcam USB dejó de responder: se pide revisar el cable. La app avisa a la familia.', S:mk({lost:true})},
  {g:'Segundo plano', slug:'06-aviso-al-cerrar', name:'Aviso al cerrar o minimizar', desc:'La ventana se cierra y el programa sigue en la bandeja, junto al reloj, con un punto de estado.', S:mk({screen:'cerrado'})},
  {g:'Segundo plano', slug:'07-aviso-webcam-desconectada', name:'Aviso: webcam desconectada', desc:'Con la ventana cerrada, un aviso del sistema indica que la webcam se desconectó; el punto de la bandeja pasa a ámbar.', S:mk({screen:'cerrado', lost:true, kind:'lost'})}
];
function renderPreset(p, o){ return p.S.screen==='cerrado' ? desktopCorner(p.S, p.S.kind) : p.S.screen==='arranque' ? desktopBoot(p.S) : win(p.S, o); }

if(typeof module!=='undefined') module.exports = {PRESETS, renderPreset, win, baseState, logotipo};
