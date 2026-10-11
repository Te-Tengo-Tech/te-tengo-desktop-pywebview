# Product

<!-- impeccable:product-schema 1 -->

> Registro escrito sin ronda de entrevista: sale del [brief de PCs, cámaras y datos de movimiento](../BRIEF-pcs-camaras-y-movimientos.md), de las historias US-28 a US-40 del [Product Backlog](../../03-product-backlog/PRODUCT_BACKLOG.md), de la [solicitud de cambio](../../01-project-charter/solicitud-de-cambio-pcs-camaras-y-movimientos.md) y de la entrada 8 del [registro de decisiones](../../04-arquitectura/registro-de-decisiones.md). Todo eso está **pendiente de aprobación** del equipo y del asesor. Lo marcado *(inferido)* es decisión de diseño. La verdad de producto común (usuarios, consentimiento, privacidad, tono) vive en `../app-movil/PRODUCT.md` y aquí no se repite.

## Platform

web

Prototipo HTML de una aplicación de escritorio para **Windows**, dibujada dentro de una ventana de 960 × 640 con barra de título neutra.

## Stack

HTML autocontenido con CSS y JS en línea, solo Google Fonts como recurso externo, íconos SVG en línea, sin servidor. Fuente en `.impeccable/src/` y compilación con `node .impeccable/src/build.js` (la misma que usa `../build-sitio.sh`); exportación a PNG con `node .impeccable/src/export.mjs "$PWD"`.

## Users

- **Familiar titular** (Carmen Huamán): instala Te Tengo Captura, la vincula desde su celular con el código QR o el código de 8 letras y **elige desde la app** qué webcam cuida cada habitación (la PC solo informa las cámaras que detecta). Puede desvincular la PC desde la app o, como respaldo, desde la PC.
- **Quien instala** (Carmen u otro familiar frente a la PC): revisa el encuadre con la vista previa local y, si hace falta, asigna las cámaras en la PC con «Elegir aquí (si estás instalando)».
- **Familiar o cuidador** (Carmen, Luis): abre la ventana para revisar el estado, la actividad, el almacenamiento o, con el modo avanzado, por qué el sistema avisó o no avisó. La PC no distingue usuarios: lo hecho en ella se anota «Desde esta PC».
- **Equipo de soporte**: recibe el archivo de diagnóstico, sin datos privados.
- El adulto mayor (Rosa Huamán) no usa el programa.

## Product Purpose

**Te Tengo Captura** es el agente de la PC de la vivienda. Detecta las **webcams USB** conectadas y se las informa a la app, donde la familia elige qué cámara cuida cada habitación (una por habitación; no admite cámaras IP), estima la pose y clasifica el movimiento en la CPU de la PC y envía a Te Tengo solo los avisos, los clips de 12 segundos y, si hay permiso, los movimientos (puntos del cuerpo, sin imagen). **El video sale de la PC solo mientras un familiar mira en vivo** ([decisión del 07/10/2026](../../04-arquitectura/decision-procesamiento-en-pc.md)); el video continuo, si se activa, se guarda solo en la PC y nunca se sube. Ningún texto nuevo dice que el video se envía a la nube.

## Operating Context

- Flujo del prototipo: arranque → **Vincular esta PC** (QR + código `KQWT-MXHD`, cuenta regresiva, código nuevo al vencer) → **Vinculada** («Listo. Ahora elige las cámaras desde la app Te Tengo, en tu celular.» y la lista de webcams detectadas) → ventana de tres pestañas **Estado · Cámaras · Avanzado**, con «Falta elegir las cámaras en la app» hasta que el celular asigna → la PC se actualiza sola (aviso «Carmen eligió la Webcam USB HD para la Sala» y aparecen las filas) → minimizar o cerrar a la bandeja (punto de estado y avisos de Windows) → abrir de nuevo desde el ícono.
- Camino secundario para quien instala: Vinculada o Cámaras → «Elegir aquí (si estás instalando)» → el selector de siempre, con sus reglas → «Volver».
- La PC queda encendida, se inicia con Windows y se reconecta sola; solo pide vincularla otra vez si se desvinculó o pasó 90 días o más sin conexión.
- Sin internet, la detección sigue en la PC: los avisos, los clips y los movimientos esperan en la cola y la actividad se marca «Pendiente de enviar».
- Si falta el consentimiento o una cámara está en pausa desde la app, esa cámara no analiza nada.
- El panel de demostración simula el celular (aprobar, rechazar, «Carmen eligió las cámaras desde la app», «Carmen dejó de usar una cámara», «Carmen mira una cámara para elegirla», pausar, ver en vivo, quitar la PC, revocar el permiso de movimientos), la PC (internet, servidor, webcams, disco) y una caída frente a la Sala. Atajo: «Empezar con la PC ya vinculada».

## Vocabulary

- **«habitación», no «ambiente».** Decisión tomada: la interfaz dice «habitación» en todas las pantallas y avisos, porque es la palabra de la casa y «ambiente» se lee como «entorno». El backlog sigue diciendo «ambiente»; los criterios se cumplen igual (CA-29.2 y CA-29.3).
- «PC» siempre en mayúsculas. «Puntos del cuerpo» en vez de *landmarks*. «Movimientos» para los puntos guardados.
- Lenguaje de la casa fuera del modo avanzado; la jerga técnica (FPS, M1–M3, la línea de registro, el identificador USB) vive solo dentro del modo avanzado y detrás de «Ver línea técnica».

## Capabilities and Constraints

- **Vincular esta PC (US-28):** QR de 188 px con el logo, código de 8 consonantes en grande, URL `tetengo.pe/vincular` y «Vence en 9:41»; al vencer, código nuevo sin intervención y anuncio «Código nuevo»; sin internet o sin servidor, reintento con cuenta regresiva; aviso de re-vinculación tras 90 días; rechazo desde la app; ayuda para los errores del celular («ya venció o ya se usó», «demasiados intentos»).
- **Cámaras (US-29):** la PC **informa las webcams que detecta** y la app las asigna; la pestaña es sobre todo informativa: lista con miniatura, nombre del dispositivo y estado (En uso · habitación, Sin usar, Nueva, Desconectada punteada, La usa otro programa) y «Buscar de nuevo»; al elegir una, vista previa local ilustrada («La vista previa solo se ve en esta PC»), que solo sirve para revisar el encuadre, con la habitación («La eligió Carmen en la app» o «Sin usar») y la conexión. Cuando la app pide la vista previa de una cámara para elegirla, su fila muestra una luz violeta «Carmen está viendo esta cámara para elegirla · No se graba» y el punto de la bandeja pasa a morado, como en la vista en vivo. La asignación en la PC queda detrás de **«Elegir aquí (si estás instalando)»**: habitación en chips (Sala, Dormitorio, Cocina, Comedor, Pasillo, Otra…) con las ocupadas deshabilitadas («Ya tiene cámara», también en otra PC); una cámara por habitación; nombre vacío y «baño» rechazados. El identificador del dispositivo aparece solo con el modo avanzado; conectar otra webcam no cambia las asignaciones.
- **Estado:** resumen en una franja y una fila por cámara; vista en vivo con nombre, habitación y hora. Sin cámaras asignadas, «Falta elegir las cámaras en la app» con cuántas detectó; al asignarlas desde el celular, la PC se actualiza sola.
- **Desvincular (US-31):** diálogo con las habitaciones que pierden detección; cancelar no cambia nada; casilla opcional para borrar los datos de la PC *(propuesta, no está en los criterios)*; desvinculada desde la app → pantalla «Esta PC se quitó…» y aviso de Windows «Esta PC se quitó de la vivienda».
- **Avanzado (US-32):** interruptor apagado por defecto; registro en vivo con filtros, búsqueda, pausa y «Ver línea técnica» con «Copiar»; medidores de rendimiento, persona, puntos del cuerpo, M1–M3 frente a su umbral, fase, temporizadores y esqueleto; sin valores y con el motivo cuando no hay persona, la cámara está en pausa o desconectada.
- **Actividad (US-33):** por día, filtro «Esta PC · Toda la casa», «Pendiente de enviar» sin internet, sin edición ni borrado.
- **Almacenamiento (US-38):** uso por tipo, carpeta, interruptor y plazo por tipo con «Nunca borrar», límite de espacio, cifrado y plazo en la nube (solo lectura). **Video continuo apagado por defecto**, con diálogo antes de activarlo. Estados: poco espacio, límite alcanzado, disco lleno o carpeta no disponible, cambio de carpeta, sin permiso de movimientos, permiso revocado.
- **Ver qué pasó (US-39):** cámara, fecha y hora; esqueleto animado que de verdad se reproduce, busca y salta; línea de tiempo de 10 min o 1 h con eventos por forma, color y texto y tramos sin datos rayados que la reproducción salta; velocidades 0,5× a 4×; esqueleto sobre el video guardado solo si hay video de ese momento; al cerrar, «Acceso registrado».
- **Exportar diagnóstico (US-34):** qué incluye y qué no, nombre del archivo, progreso, guardado con nombre y tamaño, y error sin archivo a medias.
- Ventana de tamaño fijo *(inferido)*. Cerrar o minimizar no detiene el programa.

## Reflejo de la solicitud de cambio

El prototipo ya muestra el comportamiento nuevo que la solicitud pide reflejar en criterios existentes:

| Criterio actual | Comportamiento nuevo en estas pantallas |
|---|---|
| CA-06.1 («el equipo del proyecto instaló y configuró la cámara») | El familiar titular vincula la PC (QR o código) y elige las cámaras desde la app; la PC solo informa las que detecta. «Datos de la instalación» dice «Vinculada por Carmen el 23/09/2026». |
| CA-29.1 (la PC lista las cámaras y se elige cada una) | La PC informa las webcams detectadas («Detectamos 3 cámaras») y **el celular asigna** cada una a su habitación; en la PC la asignación queda como opción secundaria, «Elegir aquí (si estás instalando)». |
| CA-11.4 («sin guardar video salvo el clip del evento») | Video continuo opcional, solo en la PC, apagado por defecto y nunca subido. |
| US-06 («Nombre de la habitación de la cámara») | La habitación se asigna y se renombra desde la app; la PC muestra el nombre nuevo (y, para quien instala, también se puede asignar en la PC). |
| CA-08.4 (solo lectura del invitado) | La PC no distingue titular e invitado; en la app, «PCs y cámaras» se ve en solo lectura (pantallas móviles). |
| CA-09.1 («programa la eliminación de las grabaciones») | La eliminación incluye movimientos, video y clips de la PC: plazos por tipo, borrado al llegar al límite y casilla al desvincular. |

## Brand Commitments

Hereda la marca Te Tengo: «Te Tengo» es lo que dices cuando sostienes a alguien que se cae, una promesa de sostén y no de vigilancia. Mismo kit (crema, violeta y coral; Poppins; logo de dos figuras abrazadas en `../marca/`), español peruano y ningún ID de historia ni etiqueta de prototipo en la interfaz. La vista previa, la vista en vivo y la repetición son ilustración o esqueleto, nunca una foto.

## Datos de ejemplo usados

Los del brief (§2): Rosa Huamán, Carmen y Luis, PC «Sala-Rosa» (Windows 11 Home, Te Tengo Captura 0.5.0) con Webcam USB HD → Sala, Logitech C920 → Dormitorio y USB2.0 PC Camera → Pasillo; «Cocina-Rosa» con la Cocina; código `KQWT-MXHD`; «3,2 GB de 50 GB» (1,1 · 1,9 · 0,2); carpeta `C:\Users\Rosa\AppData\Local\TeTengo\Datos`; diagnóstico `te-tengo-diagnostico-Sala-Rosa-2026-09-23.zip` · 1,4 MB; 10:42, caída a las 10:41:52, vinculada a las 10:31, quitada a las 11:20. El brief dice «viernes 10/10»; el fecha que el prototipo cambió al día de ejemplo del móvil, **miércoles 23/09/2026** (todas las fechas se movieron 17 días).

Valores **de relleno**, sin respaldo en el brief (ninguno es final): códigos renovados `PJZD-RNCV` y `BXRT-NWLD`; la cuarta webcam «HD USB Camera» (Comedor); los identificadores USB; «Uso del procesador 34 %» y «Demora del análisis 0,09 s»; las horas 10:20 (cambio de plazo en la nube) y «Ayer 18:05» en la actividad; la carpeta nueva `D:\TeTengo\Datos`; el reparto de «45,1 GB» (1,1 · 43,8 · 0,2); «el video del 01/10»; la fecha fuera de plazo «01/09/2026»; el tramo sin persona de 10:20 a 10:35 en la repetición y el evento inestable de las 10:39:10.

## Copy en borrador (revisar)

Todas estas etiquetas son nuevas y necesitan aprobación de copy (las que vienen del brief también eran borrador). Nunca se muestran ID ni la palabra «borrador» en la interfaz. 291 etiquetas en total; las del cambio «las cámaras se eligen desde el celular» van marcadas con *(cámaras desde la app)*.

- **Ventana y bandeja (14):** «Estado» · «Cámaras» · «Avanzado» · «Esta PC: Sala-Rosa» · «Abriendo las cámaras…» · «Versión 0.5.0» · bandeja «Sin vincular» · «Falta elegir las cámaras en la app» *(cámaras desde la app)* · bandeja «Carmen está viendo una cámara para elegirla» *(cámaras desde la app)* · aviso al cerrar «Falta elegir las cámaras desde la app Te Tengo, en tu celular. Esta PC se actualiza sola.» *(cámaras desde la app)* · «Una cámara no responde» · «Cuidando 3 habitaciones» · «La sala en pausa hasta las 11:42» · «Se quitó de la vivienda».
- **Vincular esta PC (37):** «Vincula esta PC con tu celular» · «Abre la app Te Tengo en tu celular» · «Ajustes › PCs y cámaras › Agregar PC» · «Escanea este código» · «Esta PC se llama Sala-Rosa» · «¿No puedes escanearlo? Escribe este código en la app:» · «Vence en 9:41» · «Esperando la aprobación en el celular…» · «Código nuevo · el anterior venció» · anuncio «Código nuevo» · anuncio «El código vence en 1 minuto» · «¿El celular muestra un error?» · «Escanea otra vez: esta PC ya muestra un código nuevo.» · «Espera hasta la hora que indica el celular y vuelve a intentarlo. Esta PC seguirá mostrando un código válido.» · «Sin internet» · «Conecta esta PC a internet para vincularla.» · «Reintentamos en 0:25.» · «No pudimos conectar con Te Tengo» · «Puede ser un problema nuestro: no tienes que hacer nada.» · «El código aparece cuando haya conexión» · «Esta PC estuvo más de 90 días sin conexión» · «Vuelve a vincularla con tu celular.» · «Esta PC quedó vinculada a la casa de Rosa Huamán» · «Aprobada por Carmen desde su celular a las 10:31 · Esta PC: Sala-Rosa» · *(cámaras desde la app)* «Listo. Ahora elige las cámaras desde la app Te Tengo, en tu celular.» · «Ajustes › PCs y cámaras › Sala-Rosa · esta PC se actualiza sola.» · «Detectamos 3 cámaras» · «La familia las ve en la app con su nombre.» · «Ir a Estado» · «Elegir aquí (si estás instalando)» · «Las cámaras siguen en su habitación» · «Sala, Dormitorio y Pasillo. Se cambian desde la app Te Tengo, en tu celular.» · «Las cámaras no enviarán nada hasta que la familia lo registre en la app.» · «No se vinculó esta PC» · «Alguien eligió «No reconozco esta PC» en la app.» · «Mostrar otro código» · «Vincular de nuevo».
- **Estado (22):** «Te Tengo está cuidando 3 habitaciones» · «Sala, Dormitorio y Pasillo · Todo funciona bien.» · «2 de 3 cámaras funcionan · Pasillo no responde» · «Revisa el cable USB de la USB2.0 PC Camera. Las demás cámaras siguen cuidando.» · «Las cámaras siguen cuidando y los avisos esperan. Volvemos a intentar en 8 s.» · «Mientras tanto, las cámaras no se usan.» · «La sala está en pausa hasta las 11:42» · «Dormitorio y Pasillo siguen cuidando. Luis la pausó desde la app Te Tengo; vuelve sola a esa hora.» · «Carmen está viendo el dormitorio en vivo» · *(cámaras desde la app)* «Falta elegir las cámaras en la app» · «Detectamos 3 cámaras. Elígelas desde la app Te Tengo, en tu celular. Mientras tanto, esta PC no cuida ninguna habitación.» · «Conecta una webcam por USB. Luego la familia elige su habitación desde la app Te Tengo.» · «Carmen está viendo la Webcam USB HD para elegirla» (con «No se graba y queda en el registro de la familia.», de la vista en vivo) · «Ir a Cámaras» · fila «En línea · Todo funciona bien» · «Desconectada · Revisa el cable USB» · «Detenida · Falta el consentimiento» · «En pausa · Hasta las 11:42 · desde la app» · «En vivo · Carmen está mirando» · «Sin internet · Detecta igual; los avisos esperan» · «Vinculada: Por Carmen el 23/09/2026» · «Las cámaras, las pausas, el consentimiento y las alertas se gestionan en la app Te Tengo.» *(cámaras desde la app)*.
- **Cámaras (54):** «Cámaras de esta PC» · *(cámaras desde la app)* «Detectamos 3 cámaras. Elígelas desde la app Te Tengo, en tu celular.» · «Cada cámara con su habitación. Las habitaciones se eligen desde la app Te Tengo, en tu celular.» · «Las habitaciones se eligen desde la app Te Tengo, en tu celular.» · «Habitación» · «Conexión» · «Conectada» · «Por USB» · «Nueva · por USB» · «La eligió Carmen en la app» · «Elegida desde esta PC» · «Falta elegir su habitación en la app» · «Usa la vista previa para revisar que la cámara vea bien la habitación.» · «La habitación de cada cámara se elige desde la app Te Tengo, en tu celular.» · luz «Carmen está viendo esta cámara para elegirla · No se graba» · «Carmen está viendo esta cámara para elegirla» · aviso «Carmen eligió la Webcam USB HD para la Sala» · aviso «Carmen dejó de usar la USB2.0 PC Camera: ya no cuida el Pasillo.» · «Elegir aquí, si estás instalando» · «Elige cada cámara, mira su vista previa y di en qué habitación está. La familia lo verá en la app.» · «Volver» (de la repetición) · «Cámaras conectadas a esta PC» · «En uso · Sala» · «Sin usar» · «Nueva · Sin usar» · «Desconectada · Pasillo» · «La usa otro programa» · «Vista previa · Webcam USB HD» · «La vista previa solo se ve en esta PC» · «Identificador del dispositivo:» · «¿En qué habitación está?» · «Otra…» · «Ya tiene cámara» · «Ya tiene cámara · Cocina-Rosa» · «Por ejemplo, Sala comedor» · «Escribe el nombre de la habitación.» · «Ya hay una cámara en la habitación Sala (PC Sala-Rosa). Por ahora, cada habitación usa una sola cámara.» · «Por privacidad, Te Tengo no admite cámaras en el baño.» · «Usar esta cámara» · «Guardar cambio» · «Dejar de usar» · «Buscando cámaras conectadas…» · «Cada cámara usa más la PC. Si la detección se vuelve lenta, conecta algunas cámaras a otra PC.» · «La cámara no responde: revisa el cable USB» · «Pasillo sigue asignada a esta cámara y no pasa a otra. Conéctala de nuevo y pulsa Buscar de nuevo.» · «Otro programa está usando esta cámara» · «Ciérralo y pulsa Buscar de nuevo.» · «No encontramos cámaras en esta PC» · «Conecta una webcam por USB y pulsa Buscar de nuevo.» · «Vinculada por Carmen el 23/09/2026» · «Desvincular esta PC» · aviso «La cámara Webcam USB HD cuida ahora la Sala» · «La cámara … ya no cuida la Sala.» · «Encontramos 3 cámaras conectadas.» · «No encontramos la USB2.0 PC Camera. Revisa el cable USB.».
- **Desvincular (11):** «¿Desvincular esta PC?» · «Dejaremos de detectar caídas en Sala, Dormitorio y Pasillo. Esta PC borrará su acceso y la familia recibirá un aviso.» · «Borrar también los datos guardados en esta PC (3,2 GB)» · «Movimientos, video y clips de la carpeta de Te Tengo.» · «Desvincular» · «Esta PC se desvinculó. La familia recibió un aviso.» · «Esta PC se desvinculó y borró sus datos. La familia recibió un aviso.» · «Esta PC se quitó de la casa de Rosa Huamán» · «Carmen la quitó desde la app a las 11:20. Ya no usa las cámaras.» · aviso de Windows «Esta PC se quitó de la vivienda» + «Ábrela para vincularla de nuevo.».
- **Avanzado y registro en vivo (38):** «Registro en vivo» · «Medidores» · «Actividad» · «Almacenamiento» · «Ver qué pasó» · «Exportar diagnóstico» · «Modo avanzado» · «Muestra, cámara por cámara, lo que detecta el programa y por qué avisa o no avisa. Sirve para revisar la instalación. Nada de esto sale de esta PC.» · «Nada de esto sale de esta PC.» · «Cámara» · «Sí» / «No» del interruptor · «Activamos el modo avanzado. Queda anotado en la actividad.» · «Desactivamos el modo avanzado.» · «Personas» · «Eventos» · «Descartadas» · «Conexión» · «Programa» · «Buscar» · «Pausar» · «Seguir» · «En pausa · 3 líneas nuevas» · «Ver línea técnica» · «Copiar» · «Línea copiada» · «Se abrió la cámara de la Sala (Webcam USB HD)» · «Movimiento inestable: se balanceó y recuperó el equilibrio» · «Sin persona en la imagen» · «Se ve a la persona de pie» · «Volvió internet. Se enviaron los avisos pendientes» · «Cámara en pausa hasta las 11:42» · «Cámara desconectada: revisa el cable USB» · «Aún no pasa nada en esta cámara» · «Las líneas aparecen aquí apenas el programa detecta algo.» · «No hay líneas con «escalera»» · «No hay líneas de ese tipo» · «Activa otro filtro para ver más.» · las líneas del brief (persona detectada, bajó la cadera, posible caída, caída, caída confirmada, se levantó, imagen descartada, sin internet).
- **Medidores (24):** «Rendimiento» · «Objetivo: 8 fps» · «Uso del procesador» · «Demora del análisis» · «Persona» · «Sí, se ve a una persona» · «Una sola persona en la imagen» · «Temporizadores» · «Ventana de caída» · «En el suelo 0 de 30 s» · «Descenso de la cadera (M1)» · «Inclinación del tronco (M2)» · «Forma del cuerpo, ancho/alto (M3)» · «Avisa desde 0,01» · «Avisa por debajo de 45°» · «Avisa desde 1» · «Fase» · «Avisa si queda en el suelo después de la ventana de 1,48 s; la caída se confirma a los 30 s.» · «Puntos del cuerpo» · «Visibilidad de 0 a 1 · mínimo 0,5 (la raya)» · «Esqueleto» · «Solo se ve en esta PC» · «Los medidores vuelven solos cuando la cámara vea a alguien.» (y sus variantes de pausa, desconexión y «Cámara detenida»).
- **Actividad (15):** «Esta PC» · «Toda la casa» · «Pendiente de enviar» · «Aún no hay actividad registrada» · «Aquí verás quién vinculó la PC, cambió una cámara o cómo se guardan los datos.» · «Nadie puede editar ni borrar esta lista. Lo que se hace en esta PC se anota como «Desde esta PC».» · «Desde esta PC: se activó el modo avanzado» (y «se desactivó») · «Desde esta PC: se activó el video continuo» · «Desde esta PC: la cámara … pasó de … a …» · «Desde esta PC: los movimientos pasaron de 90 días a 30 días» · «Desde esta PC: el límite de espacio pasó de 50 GB a 25 GB» · «Desde esta PC: se cambió la carpeta de los datos» · *(cámaras desde la app)* «Carmen eligió desde la app la Logitech C920 para el Dormitorio» · «Carmen eligió desde la app la HD Pro Webcam de la PC Cocina-Rosa para la Cocina» · «Carmen dejó de usar desde la app la … del …».
- **Almacenamiento (32):** «Uso» · «de 50 GB» · «Libre» · «Carpeta» · «Cambiar carpeta» · «Moviendo 3,2 GB… La detección sigue funcionando.» · «Datos cifrados» · «Los datos de esta carpeta están cifrados. Solo Te Tengo Captura puede leerlos.» · «En la nube» · «Movimientos en la nube: 30 días · lo eligió Carmen en la app.» · «Movimientos en la nube: desactivado.» · «Qué se guarda en esta PC» · «Movimientos (puntos del cuerpo)» · «Sin imagen ni video» · «Video continuo» · «Solo en esta PC · nunca se sube» · «Clips de los avisos» · «Los 12 segundos de cada aviso» · «Nunca borrar» · «Requiere el permiso de Rosa para guardar movimientos. Se registra en la app Te Tengo.» · «Límite de espacio» · «Otro» · «Al llegar al límite, borramos primero el video más antiguo y luego los movimientos más antiguos. La detección nunca se detiene.» · «No podemos guardar en la carpeta elegida» · «Elegir otra carpeta» · «Queda poco espacio: 45,1 GB de 50 GB» · «Borramos el video del 01/10 para liberar espacio» · «¿Guardar video continuo en esta PC?» · «Activar» · «¿Borrar también los movimientos guardados en esta PC (1,1 GB)?» · «Conservar» · «Borrar».
- **Ver qué pasó (28):** «Volver» · «Sala · miércoles 23/09» · «Fecha» · «Hora» · «Hace 15 min» · «Hace 1 hora» · «Hoy 07:00» · «Ver» · «Hay movimientos guardados en esta PC desde el 24/08/2026.» · «Ver sobre el video guardado» · «El video nunca sale de esta PC.» · «No se guardó video de ese momento.» · «Solo puntos del cuerpo, nunca video · Esta repetición queda en el registro de accesos» · «Video guardado solo en esta PC · nunca se sube · Queda en el registro de accesos» · fases «De pie», «Movimiento inestable», «Posible caída», «En el suelo · caída confirmada», «Se levantó» · «Evento anterior» / «Evento siguiente» · «10 min» / «1 h» · «Eventos de este tramo (3)» · «Sin datos de 10:20 a 10:35 · Sin persona en la imagen» · «Escribe la hora así: 10:40.» · «Para ver qué pasó, Rosa debe aceptar que se guarden sus movimientos.» · «Ya no hay movimientos de ese momento.».

- **Diagnóstico (16):** «Crea un archivo para enviarlo al equipo de soporte.» · «Incluye» · «Registros del programa» · «Versión y sistema operativo» · «Cámaras y habitaciones» · «Umbrales de detección» · «No incluye» · «Contraseñas ni accesos» · «Imágenes ni video» · «Puntos del cuerpo» · «Elegir dónde guardar» · «Preparando el diagnóstico…» · «Diagnóstico guardado · 1,4 MB» · «Envíalo al equipo de soporte cuando te lo pidan.» · «Mostrar en la carpeta» · «No pudimos guardar el archivo en esa carpeta. Elige otra.».

## Decisiones de producto pendientes

1. **Errores del celular en la PC.** La PC no sabe si alguien escaneó ni si el celular se bloqueó: «código ya usado» y «demasiados intentos» se resuelven en la PC con un código nuevo automático y una ayuda plegable, no con un estado propio. Confirmar.
2. **Exportar diagnóstico solo con el modo avanzado** (como dice CA-34.1); «Ver qué pasó» siempre disponible en Avanzado. Confirmar.
3. **Clips de los avisos con interruptor** en Almacenamiento (CA-38.1 pide uno por tipo; el wireframe del brief no lo tenía). Apagarlo solo deja de guardar la copia local.
4. **Video continuo apagado por defecto** (CA-38.2), mientras los datos de ejemplo dicen 1,9 GB de video: el prototipo arranca en 1,3 GB y muestra 3,2 GB con «Hay video guardado de hoy».
5. **Casilla «Borrar también los datos guardados en esta PC»** al desvincular: propuesta de diseño, fuera de los criterios.
6. **«Diagnóstico guardado»** se confirma dentro del diálogo (con «Mostrar en la carpeta»), no en un aviso breve como sugería el brief.
7. **Rendimiento:** el brief solo pide fps; se agregaron uso del procesador y demora del análisis como valores de ejemplo, y no se muestra el umbral «menos de 6 fps» hasta definirlo.
8. Fecha: unificada con el móvil y el brief en el día de ejemplo **miércoles 23/09/2026**; las demás fechas se movieron 17 días (datos guardados desde el 24/08/2026).
9. **Cámaras desde el celular (decidido el 10/10/2026, ya en el backlog):** la PC informa las webcams y la app las asigna. La PC conserva «Elegir aquí (si estás instalando)» con las mismas reglas (CA-29.8). Si la familia elige a la vez en la app y en la PC, queda el último cambio guardado y la actividad muestra ambos con su origen, quién y cuándo (CA-29.10).

## Trazabilidad

Pantallas de `pantallas.html` (nombre de la galería) → historias y criterios. Los ID nunca aparecen en la interfaz. **CA-29.1 ahora se lee así:** la PC informa las cámaras que detecta y el celular asigna cada una a su habitación (la regla de «Falta el nombre» de CA-29.2 sigue en el prototipo, dentro de «Elegir aquí»).

| Pantalla | Historia | Criterios |
|---|---|---|
| 00 Pantalla de arranque | — | — |
| 01 Todo funciona · 08 Un familiar ve en vivo · 09 Aviso: un familiar ve en vivo | US-29 (Estado) | CA-29.1, CA-29.2 |
| 02 Una cámara en pausa | US-29 (Estado) | CA-29.1 |
| 03 Esperando consentimiento | US-28 | CA-28.1 |
| 04 Sin internet, reintentando | US-33 (sin internet) | CA-33.3 |
| 05 Una cámara no responde · 07 Aviso: cámara desconectada | US-29 | CA-29.5 |
| 06 Aviso al cerrar o minimizar | — | — |
| 10 Vincular esta PC | US-28 | CA-28.1, CA-28.2 |
| 11 Código nuevo al vencer | US-28 | CA-28.3 |
| 12 Ayuda: errores en el celular | US-28 | CA-28.3, CA-28.6 |
| 13 Sin internet al vincular · 14 Te Tengo no responde | US-28 | CA-28.1 |
| 15 Volver a vincular tras 90 días | US-28 | CA-28.7 |
| 16 Vinculación rechazada | US-28 | CA-28.4 |
| 17 PC vinculada · 18 Vinculada sin consentimiento | US-28 · US-29 | CA-28.1, CA-29.1 (la PC informa las cámaras detectadas) |
| 19 Cámaras detectadas · 20 Cámaras de esta PC | US-29 | CA-29.1 (la PC informa; el celular asigna), CA-29.2 |
| 21 Carmen mira una cámara para elegirla | US-29 | CA-29.1 |
| 22 La PC se actualiza sola | US-29 | CA-29.1, CA-29.2 |
| 23 Cámara desconectada | US-29 | CA-29.5 |
| 24 Sin cámaras conectadas | US-29 | CA-29.6 |
| 25 Cámara ocupada por otro programa | US-29 | CA-29.1 |
| 26 Se conectó otra webcam | US-29 | CA-29.4 |
| 27 Elegir aquí, si estás instalando | US-29 | CA-29.2, CA-29.3 |
| 28 Estado: falta elegir las cámaras en la app | US-29 | CA-29.1 |
| 29 Desvincular esta PC | US-31 | CA-31.3, CA-31.4 |
| 30 Quitada desde el celular · 31 Aviso: PC quitada | US-31 | CA-31.1, CA-31.2 |
| 32 Modo avanzado apagado | US-32 | CA-32.1 |
| 33 Registro en vivo · 34 Ver línea técnica · 35 Registro en pausa · 36 Búsqueda sin resultados | US-32 | CA-32.2 |
| 37 Medidores · 38 Medidores: posible caída | US-32 | CA-32.3 |
| 39 Medidores sin persona · 40 Medidores con la cámara en pausa | US-32 | CA-32.4 |
| 41 Actividad · 43 Actividad de toda la casa | US-33 | CA-33.1, CA-33.2 |
| 42 Actividad pendiente de enviar | US-33 | CA-33.3 |
| 44 Sin actividad | US-33 | CA-33.4 |
| 45 Almacenamiento · 47 Con video guardado | US-38 | CA-38.1, CA-38.4 |
| 46 Activar el video continuo | US-38 | CA-38.2 |
| 48 Queda poco espacio · 49 Límite alcanzado | US-38 | CA-38.3 |
| 50 Disco lleno o carpeta no disponible | US-38 | CA-38.5 |
| 51 Cambiando de carpeta | US-38 | CA-38.1 |
| 52 Sin permiso para guardar movimientos | US-35 · US-38 | CA-35.3 |
| 53 Permiso revocado: ¿borrar en esta PC? | US-35 | CA-35.4 |
| 54 Ver qué pasó | US-39 | CA-39.1, CA-39.2 |
| 55 Sobre el video guardado | US-39 | CA-39.2 |
| 56 Tramo sin datos | US-39 | CA-39.5 |
| 57 Sin permiso de movimientos · 58 Fuera del plazo | US-39 | CA-39.4 |
| 59 Acceso registrado | US-39 | CA-39.3 |
| 60 Exportar diagnóstico | US-34 | CA-34.1, CA-34.2 |
| 61 Preparando el diagnóstico · 62 Diagnóstico guardado | US-34 | CA-34.1 |
| 63 Error al guardar | US-34 | CA-34.3 |

Trabajo futuro (`pantallas-trabajo-futuro.html`, fuera de alcance según el brief, §8): 01 Dos cámaras en la misma habitación y 02 Vista combinada en 3D (opciones B y C de varias cámaras por habitación; hoy lo impide CA-29.3), 03 y 04 Varias personas.
