# Product

<!-- impeccable:product-schema 1 -->

> Registro escrito sin ronda de entrevista: el init corrió dentro de un subagente sin herramienta de preguntas. Todo sale del brief del encargo; lo marcado *(inferido)* es decisión de diseño. La verdad de producto común (usuarios, consentimiento, privacidad, tono) vive en `../app-movil/PRODUCT.md` y aquí no se repite.

## Platform

web

Prototipo HTML de una aplicación de escritorio para **Windows**, dibujada dentro de una ventana de 960 × 640 con barra de título neutra.

## Stack

Delegado por el brief: HTML autocontenido con CSS y JS en línea, solo Google Fonts como recurso externo, íconos SVG en línea, sin servidor. Fuente en `.impeccable/src/` y compilación con `node .impeccable/src/build.js`.

## Users

- **Equipo del proyecto**: en la prueba piloto instala la webcam USB y el programa en la PC de la vivienda y deja un archivo de configuración fijo (vivienda, webcam, nombre inicial de la habitación).
- **Familiar o cuidador** (Carmen Huamán): no configura nada en la PC; abre la ventana solo para revisar por qué algo no envía (cable, internet, pausa, consentimiento).
- El adulto mayor (Rosa Huamán) no usa el programa.

## Product Purpose

**Te Tengo Captura** es el agente de captura: abre la **webcam USB** configurada en la PC de la vivienda (no admite cámaras IP) y envía su video cifrado a la nube de Te Tengo, donde se analiza. No analiza nada en la PC.

En la prueba piloto hace una sola cosa: **mostrar el estado** de esa webcam. La vivienda y la cámara aparecen en solo lectura, como «Configurada por el equipo del proyecto». **No vincula cámaras**: no hay códigos, ni elección entre webcams. Toda la gestión (nombre de la habitación, consentimiento, pausas, vista en vivo, alertas, familia, historial) vive en la app móvil Te Tengo.

## Operating Context

- La PC queda encendida en la vivienda. El programa se inicia con Windows, se reconecta solo y vive en la bandeja del sistema.
- No envía video si falta el consentimiento o si hay una pausa activa definida desde la app.
- Flujo del prototipo: ventana de arranque → ventana de estado → minimizar o cerrar a la bandeja (ícono con punto de estado y aviso del sistema) → abrir de nuevo desde el ícono.
- **Trabajo futuro (no incluido en el piloto):** la vinculación de varias cámaras con código `TTG-XXXX` y elección de webcam con vista previa se conserva en una galería aparte, `pantallas-trabajo-futuro.html` («Trabajo futuro · Vinculación de varias cámaras», 11 pantallas numeradas desde 01; exportaciones en `pantallas/trabajo-futuro/` y `figma/trabajo-futuro/`), fuera de `pantallas.html` y del prototipo navegable (`.impeccable/src/futuro.js`).

## Capabilities and Constraints

- Estados: Enviando, En pausa (hasta una hora, desde la app), Esperando consentimiento, Sin internet (reintentando, con cuenta regresiva) y Webcam desconectada (revisa el cable USB). La app móvil avisa a la familia de la desconexión.
- Una sola cámara; el nombre de la habitación (en la demo, «Sala») viene de la instalación y se cambia solo desde la app. Nunca baño.
- La miniatura de la cámara es una ilustración estilizada de la habitación, sin personas.
- Ventana de tamaño fijo *(inferido: maximizar desactivado, como en utilidades de bandeja)*.
- Cerrar o minimizar la ventana no detiene el programa.

## Brand Commitments

Hereda la marca Te Tengo. «Te Tengo» es lo que dices cuando sostienes a alguien que se cae: una promesa de sostén, no de vigilancia. Mismo tono (calma, claridad, nada de vigilancia), mismo logo («La T que sostiene», en `../marca/`; aquí se usa la versión `logotipo-captura.svg`), español peruano y ningún ID de historia de usuario ni etiqueta de prototipo en la interfaz.

Arranque: al encender la PC o abrir el programa aparece una ventana de inicio centrada, en morado de marca, con el símbolo que se arma, «Te Tengo Captura» y una barra de progreso («Iniciando…», «Abriendo la webcam configurada…», «Conectando con Te Tengo…»). Luego se abre la ventana de estado.
