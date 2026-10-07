# Design

<!-- impeccable:design-schema 1 -->

> **Extensión del sistema de Te Tengo**, no un mundo nuevo. Tokens, color, tipografía y reglas de estado vienen de `../app-movil/DESIGN.md` y `../app-movil/.impeccable/src/app.css`. Aquí solo se documenta lo que cambia para una ventana de escritorio de Windows. Modo: **Operate**. Fuente: `.impeccable/src/` (compilar con `node .impeccable/src/build.js`).

## Visual direction

Es la misma calma de Te Tengo, pero en una utilidad de bandeja. Fondo neutro `--ground`, tarjetas blancas y el color semántico reservado para el estado. Nada de estética de vigilancia: la vista previa de la cámara es la ilustración estilizada de la habitación, sin personas, la misma de los clips de la app móvil. En la prueba piloto la ventana es una sola: el **estado de la única webcam**, con la vivienda y la configuración en solo lectura («Configurada por el equipo del proyecto»). No hay pasos de vinculación. El celular en miniatura y el campo de código quedan en la galería de trabajo futuro (`pantallas-trabajo-futuro.html`).

## Color

Todos los tokens se heredan sin cambios (`--morado`, `--calma`, `--aviso`, `--pausa`, `--caida`, `--ink*`, `--line*`). Estados de cámara en el escritorio:

| Estado | Color | Forma |
|---|---|---|
| Enviando | `--calma` / `--calma-soft` | Ícono de subida |
| En pausa | `--pausa`, rayado diagonal | Ícono de pausa |
| Esperando consentimiento | `--aviso` / `--aviso-soft` | Ícono de documento |
| Sin internet | tinta oscura (`--ink`), ámbar en el ícono | Wi-Fi tachado, cuenta regresiva y «Reintentar ahora» |
| Webcam desconectada | `--aviso-soft`, franja ámbar discontinua, contorno punteado | Cámara tachada, «revisa el cable USB» y «Buscar de nuevo» |

El rojo `--caida` no aparece en el piloto: aquí no hay alertas de caída (en la galería de trabajo futuro lo usan los errores de validación del código).

## Typography

- Atkinson Hyperlegible Next en toda la interfaz; Atkinson Hyperlegible Mono en las horas y los números (y en el código de vinculación de la galería de trabajo futuro).
- Escala de escritorio, más compacta que la móvil: título de inicio 34 px, títulos 26 px, cuerpo 15–16 px y datos secundarios 13,5 px.

## Shape and depth

- Ventana de 960 × 640, radio de 10 px y barra de título neutra de 36 px (minimizar, maximizar desactivado y cerrar).
- Radios adaptados a la densidad de escritorio: tarjetas de 18 px y controles de 12 px (en la app móvil son 22 y 16).
- Sombras `--shadow-1` y `--shadow-2` heredadas.
- Movimiento de 150 a 250 ms con `cubic-bezier(.16,1,.3,1)`. Se desactiva con `prefers-reduced-motion` y con la clase `.static` de las exportaciones.

## Components

- **Ventana de estado** (única pantalla): título «Vivienda de Rosa Huamán» con la dirección, tarjeta de estado y dos tarjetas: la cámara y la configuración.
- **Tarjeta de estado del equipo**, con la franja superior del color del estado (igual que la tarjeta «Todo tranquilo» de la app). Variantes: enviando (verde), en pausa hasta una hora (rayado gris azulado), esperando consentimiento (ámbar), sin internet (tinta oscura, con cuenta regresiva y «Reintentar ahora») y webcam desconectada (ámbar con franja discontinua y «Buscar de nuevo»).
- **Tarjeta de cámara**: miniatura ilustrada de la habitación (en gris si no envía), «Cámara de esta casa», nombre de la habitación, webcam y estado (ícono, texto y detalle).
- **Tarjeta de configuración**, solo lectura, con candado: «Configurada por el equipo del proyecto»; vivienda, webcam, habitación («El nombre se cambia en la app Te Tengo») y fecha de instalación, más la nota de configuración fija.
- **Barra de tareas y bandeja**: ícono de Te Tengo Captura con un punto de estado (verde enviando, gris en pausa, ámbar con problema) y avisos del sistema: al cerrar o minimizar («sigue funcionando en segundo plano») y si la webcam se desconecta con la ventana cerrada.
- **Trabajo futuro** (solo `pantallas-trabajo-futuro.html`, `futuro.js`): campo de código `TTG-` con validación en vivo, opción de webcam con vista previa, celular en miniatura y lista de varias cámaras, en una galería aparte numerada desde 01, con borde discontinuo y nota «No incluido en la prueba piloto». `pantallas.html` solo tiene las pantallas 00–07 del piloto.

- **Marca:** ícono de la app (`LOGO`, cuadrado morado con «La T que sostiene») en la barra de título, la barra de tareas, la bandeja y el aviso del sistema; `logotipo-captura.svg` (símbolo + «Te Tengo» + «Captura» en 600) en la cabecera de la galería.
- **Ventana de arranque (pantalla 00):** ventana de 480 × 300 centrada sobre el escritorio, sin barra de título, en `--morado`. El símbolo se arma igual que en la app móvil (brazos, punto que cae y es recibido, fuste), debajo va «Te Tengo Captura» y al pie una barra de progreso blanca de 4 px con el paso actual («Iniciando…», «Abriendo la webcam configurada…», «Conectando con Te Tengo…») y la versión. Dura unos 2,2 s y da paso a la ventana de estado.

## Accessibility

- Contraste AA en todo el texto; el foco visible usa `--focus`.
- El estado nunca depende solo del color: siempre lleva ícono, texto y un patrón (rayado o punteado).
- Los mensajes de estado usan `role="status"`; la cuenta regresiva de reconexión se actualiza sin mover el foco.

## Not canonized

La franja superior de 5 px en la tarjeta de estado y el rayado de pausa son rasgos propios de Te Tengo. Por eso se conservan aunque el detector los marque. Los avisos de «tarjeta dentro de tarjeta» del detector corresponden al marco de la ventana y al celular en miniatura, no a tarjetas anidadas reales.
