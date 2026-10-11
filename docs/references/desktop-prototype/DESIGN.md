# Design

<!-- impeccable:design-schema 1 -->

> **Extensión del sistema de Te Tengo**, no un mundo nuevo. El kit de marca (tokens, color, tipografía, logo y reglas de estado) viene de `../app-movil/DESIGN.md`, `../app-movil/.impeccable/src/app.css` y `../marca/README.md`. Aquí solo se documenta lo que cambia para una utilidad de bandeja de Windows. Modo: **Operate**. Fuente: `.impeccable/src/` (compilar con `node .impeccable/src/build.js`; exportar con `node .impeccable/src/export.mjs "$PWD"`).

## Visual direction

El mismo mundo cálido de la app Te Tengo, en una ventana pequeña que casi nadie abre: fondo crema, tarjetas blancas con borde lila de 1 px y sombra violeta muy suave, Poppins y solo tres colores de marca (violeta, coral y crema). El estado se dice una sola vez, en un bloque tintado con su ícono dentro de un círculo; el resto de la ventana es neutro. Nada de estética de vigilancia: la vista previa de cada cámara es la ilustración de su habitación, sin personas, y la repetición y los medidores muestran solo el esqueleto de puntos del cuerpo.

La ventana tiene **tres pestañas: Estado · Cámaras · Avanzado**. Antes de vincularse muestra una sola pantalla, «Vincula esta PC con tu celular», con el QR y el código; después de vincularse, la barra de pestañas. **Las cámaras se asignan desde el celular:** la PC informa las webcams que detecta, dice que la familia las elige en la app y se actualiza sola cuando lo hace; asignar en la PC es una opción secundaria para quien instala. Avanzado reúne lo técnico: el registro en vivo y los medidores (solo con el modo avanzado), la actividad, el almacenamiento, «Ver qué pasó» y «Exportar diagnóstico».

## Color

Mismos tokens que la app móvil. Cambios en el escritorio: `--caida` pasa a `#D63B2F` (el rojo de alarma de la app) y se agregan `--inestable` (`#F1B42F`, `-deep #D99A12`, `-soft #FDF3DB`, `-ink #6E4B00`) para los eventos del registro y de la línea de tiempo.

| Token | Valor | Uso en el escritorio |
|---|---|---|
| `--ground` | `#FFF7F1` (crema) | Fondo de la ventana y de la ventana de arranque |
| `--ground-2` | `#F7F2F5` (lila base) | Pie de la ventana, controles segmentados, lienzo de la repetición, fondo de la línea técnica |
| `--card` | `#FFFFFF` | Barra de título, barra de pestañas, tarjetas, diálogos y aviso del sistema |
| `--ink` / `--ink-2` / `--ink-3` | `#2B1D4E` / `#5A4F70` / `#6E6585` | Texto primario, secundario y terciario; chips elegidos y pasos numerados en `--ink` |
| `--morado` (+ `-soft`) | `#4B2E83` / `#F1EBF8` | Marca, botones, ícono de la pestaña activa, código de vinculación, «viendo en vivo», barras de medidores |
| `--coral` (+ `-soft`, `-ink`) | `#FF8F7E` / `#FFEDE8` / `#A8402F` | Logo, halo del arranque, **subrayado de la pestaña activa** y segmento «Clips» del uso de disco. Nunca texto blanco sobre coral y nunca marca un problema |
| `--caida` / `--inestable` / `--calma` | rojo / mostaza / verde | Solo eventos reales: líneas del registro, marcas de la línea de tiempo y fase de los medidores, siempre con forma, ícono y texto |
| `--aviso` | `#8F5400` | Problemas: cámara desconectada (punteado), sin internet, disco lleno, imagen descartada |

Estados del equipo (bloque tintado + círculo sólido con ícono blanco + título y frase; nunca solo color): cuidando (verde, check), viendo en vivo (violeta, ojo), una cámara en pausa (gris azulado, pausa), falta el consentimiento (ámbar, documento), sin internet (ámbar, wi-fi tachado, cuenta regresiva y «Reintentar ahora»), una cámara no responde (blanco con contorno ámbar punteado, cámara tachada, «Buscar de nuevo») y falta elegir las cámaras en la app (neutro, celular, cuántas detectó e «Ir a Cámaras»). Cuando la app mira una cámara para elegirla, una franja violeta con luz debajo del estado.

Punto de la bandeja: verde (cuidando), gris (pausa), ámbar (problema o falta elegir las cámaras en la app), violeta (alguien mira en vivo o mira una cámara para elegirla) y anillo gris vacío (sin vincular o quitada). Contraste comprobado: todo el texto ≥ 4,5:1; texto sobre mostaza en tinta, nunca blanco; blanco sobre `--caida-deep` y `--calma` ≥ 5,3:1.

## Brand

- **Logo: dos figuras abrazadas** (`../marca/`), con los mismos trazos que la app móvil (`MARK_VH`, `MARK_CH`, `MARK_ARM`, `MARK_BODY`, `symbolParts` en `core.js`): la violeta abraza, la coral es abrazada.
- **Ícono de la app** (`LOGO`): cuadrado violeta redondeado con la figura blanca y la coral. Va en la barra de título, la barra de tareas, la bandeja, el aviso de Windows y **en el centro del código QR** de vinculación.
- **Logotipo** (`logotipo(false, true)`): cabecera de las galerías. `wordmark()` en la ventana de arranque.

## Typography

- **Poppins** en toda la interfaz: 700 en títulos, 600 en botones, títulos de estado y filas, 400 en el cuerpo. Horas y números con cifras tabulares.
- **Texto técnico** (`--code`: `ui-monospace`, Cascadia Mono, Consolas): solo en «Ver línea técnica», la ruta de la carpeta, el nombre del archivo de diagnóstico y el identificador del dispositivo. Es la fuente monoespaciada del sistema; no se descarga ninguna familia nueva.
- Escala de escritorio: título 23–28 px, estado 17 px, cuerpo 14–15 px, metadatos 12,5–13,5 px.

## Shape and depth

- Ventana de 960 × 640 con radio 10 y barra de título blanca de 36 px (minimizar, maximizar desactivado y cerrar), seguida de la barra de pestañas blanca de 50 px.
- Radios del kit: tarjetas y bloques 20 px (16 px en las tarjetas compactas de Avanzado), controles 14 px (12 px en los pequeños), píldoras redondas.
- Tarjetas blancas con `--shadow-1`; diálogos con `--shadow-2` sobre un velo violeta translúcido. Sin franjas de color sobre las tarjetas.
- Movimiento de 150 a 250 ms con `cubic-bezier(.16,1,.3,1)`; se desactiva con `prefers-reduced-motion` y con la clase `.static` de las exportaciones. La repetición, con movimiento reducido, avanza por pasos de un segundo.

## Components

- **Barra de pestañas** (`tabbar`): pestañas con ícono y texto (Estado, Cámaras, Avanzado), `role="tablist"` con flechas; la activa en tinta 700, ícono violeta y subrayado coral de 3 px. A la derecha, «Esta PC: Sala-Rosa».
- **Tarjeta de vinculación** (`pairCard`): QR de 188 px con el ícono de la app al centro, «¿No puedes escanearlo? Escribe este código en la app:», el código de 8 letras en violeta sobre `--morado-soft` (letra por letra para el lector de pantalla), la URL y «Vence en 9:41» con reloj (ámbar en el último minuto, anuncio sin mover el foco). Al vencer, la tarjeta se renueva con una transición corta y la etiqueta verde «Código nuevo · el anterior venció». Sin internet o sin servidor, la tarjeta cambia a círculo ámbar punteado, frase y «Reintentar ahora». A la izquierda, pasos numerados (`.steps2`), el nombre de la PC y la ayuda plegable «¿El celular muestra un error?»; abajo, la píldora de espera `.wait2`.
- **Pantallas de resultado** (`.result`): vinculada (`.result.linked`: check verde, vivienda y nombre de la PC, aviso violeta con el celular «Listo. Ahora elige las cámaras desde la app Te Tengo, en tu celular.» y la ruta en la app, la lista `.found` «Detectamos 3 cámaras» con miniatura y etiqueta, «Ir a Estado» y, en fantasma, «Elegir aquí (si estás instalando)»; si vuelve a vincularse con cámaras ya asignadas, «Las cámaras siguen en su habitación»), rechazada y quitada (círculo gris con ícono, una frase y una acción).
- **Estado con varias cámaras**: el bloque de estado resume todas las cámaras («Te Tengo está cuidando 3 habitaciones», «2 de 3 cámaras funcionan · Pasillo no responde») y debajo una fila por cámara (`.crow`): miniatura ilustrada, habitación, dispositivo y estado (círculo + texto), con contorno punteado si está desconectada. «Datos de la instalación» queda plegado.
- **Cámaras informativa con vista previa local** (`panelCamaras` + `camInfo`): lista a la izquierda (`.cpick`, `role="radiogroup"`) con miniatura, nombre y etiqueta de estado (`.ctag`: en uso, sin usar, nueva, desconectada punteada, la usa otro programa) y «Buscar de nuevo»; al pie, «Esta PC» con «Desvincular esta PC» (respaldo; lo normal es quitarla desde la app). A la derecha (`.cpane.info`), la vista previa ilustrada con «La vista previa solo se ve en esta PC», que solo sirve para revisar el encuadre, dos datos en `.cinfo` (Habitación: «Sala · La eligió Carmen en la app» o «Sin usar»; Conexión: «Conectada»), dos ayudas («Usa la vista previa…», «La habitación… se elige desde la app») y, abajo a la izquierda, el botón fantasma «Elegir aquí (si estás instalando)». Con el modo avanzado, el identificador del dispositivo.
- **Luz «está viendo para elegirla»** (`.led`, `.peek`, `.peek-n`): cuando la app pide la vista previa de una cámara, su fila suma una franja violeta a todo el ancho con un punto violeta que late suave y «Carmen está viendo esta cámara para elegirla · No se graba»; el panel y Estado repiten el aviso en `.notice.info`. Es el violeta de la vista en vivo (`--morado`), y el punto de la bandeja pasa a violeta. Sin animación con movimiento reducido.
- **Elegir aquí, para quien instala** (`camPane`, `S.here`): el selector de siempre detrás de la entrada secundaria, con título «Elegir aquí, si estás instalando» y «Volver»: chips de habitación (`.chip2`; las ocupadas punteadas con «Ya tiene cámara», también de otra PC), «Otra…» con campo, mensaje de error y «Usar esta cámara» / «Guardar cambio» / «Dejar de usar». Lo guardado aquí se anota «Desde esta PC» y la habitación dice «Elegida desde esta PC».
- **Interruptor** (`.switch`): el de la app móvil a 48 × 28, siempre con «Sí» o «No» al lado (salvo en espacios mínimos, donde manda la posición del círculo); deshabilitado con borde y su motivo debajo.
- **Controles segmentados** (`.seg2`): subpestañas de Avanzado, selector de cámara, rango de la línea de tiempo y «Esta PC · Toda la casa».
- **Registro en vivo** (`logView`): filtros en píldoras con ícono y conteo (tachados al apagarlos), búsqueda, «Pausar / Seguir» y banda «En pausa · N líneas nuevas». Cada línea: hora tabular, ícono en círculo tintado por tipo y mensaje (rojo y en negrita para caídas, verde para «Se levantó»), con «Ver línea técnica» que abre el texto técnico en `--code` y «Copiar». Contenedor `role="log"`; solo los eventos se anuncian.
- **Medidores** (`metersView`): cuadrícula de tarjetas compactas: rendimiento, persona, temporizadores (ventana de 1,48 s y suelo de 30 s), las tres medidas con valor, «Sí/No» y barra con la raya del umbral, la fase en pasos y, a la derecha, puntos del cuerpo (barras con la raya del mínimo; bajo el mínimo, ámbar con ícono) y el esqueleto «Solo se ve en esta PC». Sin datos, una tarjeta con el motivo reemplaza la primera fila y los valores pasan a «—».
- **Línea de tiempo con marcas de eventos** (`timeline`): pista blanca de 30 px (`role="slider"`, flechas, Inicio, Fin, Espacio), cabezal en tinta, marcas como botones con forma + color + texto (triángulo rojo «Caída», rombo mostaza «Inestable», círculo verde «Se levantó») y tramos sin datos rayados con su motivo. Rango de 10 min o 1 h. Debajo, controles de 42–46 px (evento anterior, reproducir, evento siguiente, hora, velocidad 0,5×–4×) y «Eventos de este tramo» plegado.
- **Repetición** (`panelReplay`): formulario a la izquierda (cámara, fecha, hora, atajos, «Ver», interruptor «Ver sobre el video guardado»), franja de privacidad, lienzo con el esqueleto sobre fondo neutro (o sobre la ilustración cuando hay video guardado), etiqueta de fase y reloj.
- **Selector de plazo** (`retPills`): píldoras de radio (7 días … «Nunca borrar»; 10 GB … «Otro»), la elegida en tinta; deshabilitadas punteadas.
- **Barra de uso del disco** (`.ubar`): segmentos por tipo (movimientos violeta, video lila, clips coral) sobre lila, con leyenda en texto y GB de cada tipo y libre.
- **Diálogos** (`dlgBox`): círculo de ícono, título, frase y acciones a la derecha; atrapan el Tab, cierran con Escape y devuelven el foco. Desvincular (rojo, con casilla opcional), activar video continuo, borrar movimientos de la PC y exportar diagnóstico (incluye / no incluye, archivo, progreso, guardado y error).
- **Aviso dentro de la ventana** (`.wtoast`): píldora oscura abajo al centro, con el ícono en un círculo translúcido. Cuando la familia asigna o deja de usar una cámara desde la app, el aviso lleva el ícono del celular («Carmen eligió la Webcam USB HD para la Sala»), uno por cámara.
- **Barra de tareas, bandeja y avisos de Windows**: como antes, con el aviso nuevo «Esta PC se quitó de la vivienda» (círculo gris con el ícono de desvincular).
- **Ventana de arranque (pantalla 00)**: sin cambios de diseño; pasos «Iniciando…», «Abriendo las cámaras…», «Conectando con Te Tengo…» y «Versión 0.5.0».
- **Trabajo futuro** (solo `pantallas-trabajo-futuro.html`, `futuro.js`): reutiliza el núcleo (`core.js`) para mostrar dos cámaras en una habitación, la vista combinada en 3D y varias personas, cada pantalla con la etiqueta «Trabajo futuro». La vinculación anterior (código `TTG-XXXX` escrito en la PC, «Pendiente de conectar», varias cámaras por código) se retiró porque la reemplaza la vinculación con QR.

## Accessibility

- Contraste AA en todo el texto; foco visible con `--focus` (violeta), también dentro de la barra de pestañas y la línea de tiempo.
- El estado nunca depende solo del color: ícono + texto y, según el caso, contorno punteado (desconectada), tachado (filtro apagado), rayado (tramo sin datos) o forma (marcas de eventos).
- `role="status"` en estados, cuentas regresivas y avisos; la cuenta regresiva del código solo se anuncia al faltar un minuto y al renovarse. Pestañas y grupos de opción con flechas; la línea de tiempo es un `slider` con valor en texto («10:41:52, caída»).
- Al volver a pintar, el foco regresa al control que se tocó, los plegables conservan su estado y las listas su desplazamiento.

## Not canonized

- El detector marca un «glow» por las sombras violetas sobre la píldora oscura del aviso: es la sombra `--shadow-2` del kit, con desplazamiento y difuminado, no un halo.
- El detector marca «rayas decorativas» en `.tl-gap`: es el **rayado de tramo sin datos** que pide el brief (§5.7) para «Sin persona», «En pausa» o «PC apagada», y lleva su motivo en texto debajo. No es decoración.
- Los avisos de «tarjeta dentro de tarjeta» corresponden al marco de la ventana y a los diálogos sobre el contenido.
