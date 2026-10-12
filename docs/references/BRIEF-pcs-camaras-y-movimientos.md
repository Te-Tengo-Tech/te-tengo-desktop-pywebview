# Brief de diseño: PCs, cámaras y datos de movimiento

**Para:** la sesión de diseño de `05-prototipos/app-movil/` (app Te Tengo) y `05-prototipos/app-escritorio/` (Te Tengo Captura)
**Historias:** US-28 a US-40 del [Product Backlog](../03-product-backlog/PRODUCT_BACKLOG.md) (EP06, EP07, EP08 y US-40 en EP03)
**Decisiones de fondo:** [solicitud de cambio](../01-project-charter/solicitud-de-cambio-pcs-camaras-y-movimientos.md) (pendiente de aprobación del equipo y del asesor)
**Fecha:** 10/10/2026 · **Día de los ejemplos:** miércoles 23/09/2026, el día de demostración del prototipo móvil

> **Cambio aprobado (10/10/2026):** las webcams se asignan a las habitaciones **desde el celular del titular** («Elige las cámaras», M-29.1), con una vista previa tratada como vista en vivo. La PC conserva lo que necesita a alguien en la casa (código QR, conectar webcams, estado, modo avanzado) y su «Elegir cámaras» queda como respaldo del instalador (D-29.1; decidido el 10/10/2026, CA-29.8). Si la asignación cambia casi al mismo tiempo en el celular y en la PC, queda el último cambio guardado y Actividad muestra ambos con su origen (CA-29.10).

> Este brief sirve para diseñar las pantallas **antes** de escribir código. Todo el texto de interfaz que aparece aquí es **borrador de copy — revisar**: el copy de producto necesita aprobación. Donde ya existe una frase en los prototipos, se reutiliza. Los ID de historias y criterios (US-xx, CA-xx.x) son solo para trazabilidad: **nunca aparecen en la interfaz**.

## Índice

1. [Reglas que se heredan](#1-reglas-que-se-heredan)
2. [Datos de ejemplo](#2-datos-de-ejemplo)
3. [Mapa de navegación](#3-mapa-de-navegación)
4. [Orden de diseño](#4-orden-de-diseño)
5. [App móvil](#5-app-móvil)
6. [Te Tengo Captura (escritorio)](#6-te-tengo-captura-escritorio)
7. [Estados transversales](#7-estados-transversales)
8. [Fuera de alcance y trabajo futuro](#8-fuera-de-alcance-y-trabajo-futuro)
9. [Trazabilidad](#9-trazabilidad)

---

## 1. Reglas que se heredan

Fuentes: `app-movil/PRODUCT.md`, `app-movil/DESIGN.md`, `app-escritorio/PRODUCT.md`, `app-escritorio/DESIGN.md` y las galerías `pantallas.html` y `pantallas-trabajo-futuro.html` de cada app.

- **Copy como producto terminado, en lenguaje de la casa.** Español peruano, frases cortas, «tú». El estado se dice una sola vez (escritorio: «Te Tengo está cuidando la sala · Todo funciona bien»). Nada de jerga técnica fuera del modo avanzado; dentro de él, la jerga va detrás de «Ver línea técnica».
- **Cuidar, no vigilar.** Nada remite a una cámara de seguridad. Los clips, la vista en vivo y la repetición se muestran como ilustración o esqueleto, nunca como fotos de la persona. Cada acceso que muestra a Rosa queda registrado y es visible para toda la familia.
- **Síntesis móvil.** Primero lo que decide la acción, en una o dos frases; el detalle va plegado con `more()` o `fold()` (`<details>`, 48 px de zona táctil, chevrón que gira).
- **Titular e invitado.** Solo el titular cambia PCs, cámaras, consentimientos y retención. El invitado ve lo mismo en solo lectura: aviso neutro con candado «Solo Carmen (titular) puede…», etiqueta `.ro-tag` «Solo ver», acciones de administración ocultas.
- **Estado nunca solo por color.** Ícono + texto + trazo o patrón (rayado para pausa, punteado para desconexión). Rojo (`--caida`) y mostaza (`--inestable`) solo para eventos reales; ámbar (`--aviso`) para problemas; morado para marca y acción principal; gris azulado (`--pausa`) para pausa.
- **Accesibilidad.** Objetivos táctiles de 48 dp en móvil; texto legible con la letra del celular al 200 % (`.screen.big`); foco visible (`--focus`); `role="status"` en estados y cuentas regresivas sin mover el foco; hojas y diálogos atrapan el Tab y cierran con Escape; modo oscuro (`.screen.dark`).
- **Marca.** Te Tengo (dos palabras), Te Tengo Captura en la PC. Rige el kit de marca que ya está en el código (`app-movil/DESIGN.md` y la sección «Kit de marca» de `app.css`): logo de dos figuras abrazadas (la violeta abraza, la coral es abrazada), fondo crema, tarjetas blancas con borde lila, Poppins, violeta para la acción, coral para íconos y rellenos, íconos en círculos tintados y fotos solo para identificar a las personas; arranque sobre crema. Coral nunca marca un estado.
- **Video en la PC.** El video se procesa en la PC de la casa ([registro de decisiones](../04-arquitectura/registro-de-decisiones.md), entrada 1 y entrada 8). Ningún texto dice que el video va a la nube: solo salen los avisos, el clip de cada alerta y la vista en vivo mientras alguien la mira.
- **Vocabulario nuevo.** El backlog usa **ambiente** (Sala, Dormitorio, Cocina, Comedor, Pasillo) como término técnico. **Decidido (10/10/2026): la interfaz dice «habitación»**, en las pantallas nuevas y en las existentes. Ya está en más de cien pantallas y en cada alerta («Posible caída en la Sala»), es la palabra de la casa y «ambiente» se lee como *environment*. Donde este brief dice «ambiente» en el copy, las pantallas dicen «habitación» (por ejemplo, «Ya hay una cámara en la Sala. Por ahora, cada habitación usa una sola cámara.»). «PC» siempre en mayúsculas; «la PC de la casa» cuando hay una sola. «Puntos del cuerpo» en vez de *landmarks*. «Movimientos» para los puntos guardados.
- **Galería de trabajo futuro.** Las pantallas de `pantallas-trabajo-futuro.html` (código `TTG-XXXX` generado en la app y escrito en la PC, «Pendiente de conectar») quedan **superadas**: el nuevo flujo va al revés (la PC muestra el código y el celular lo escanea o lo escribe). Se pueden reutilizar sus componentes: `.code-box` con cuenta regresiva, fila de espera `.wait`, pasos numerados `.steps`, opción de webcam con vista previa y lista de varias cámaras.

## 2. Datos de ejemplo

Valores realistas para todas las pantallas. Son **de ejemplo**: no salen de mediciones.

| Dato | Valor |
|---|---|
| Adulto mayor | Rosa Huamán, 78 años; Jr. Los Pinos 482, San Miguel, Lima |
| Familia | Carmen Huamán (hija, titular, contacto principal); Luis Huamán (hijo, invitado, contacto secundario); Milagros Quispe (sobrina, invitación pendiente) |
| PC 1 | «Sala-Rosa» · Windows 11 Home · Te Tengo Captura 0.5.0 · 3 cámaras |
| Cámaras de Sala-Rosa | «Webcam USB HD» → Sala; «Logitech C920» → Dormitorio; «USB2.0 PC Camera» → Pasillo |
| PC 2 | «Cocina-Rosa» · Windows 10 Pro · Te Tengo Captura 0.5.0 · 1 cámara («HD Pro Webcam» → Cocina) |
| Vinculación | Sala-Rosa el 03/08/2026 (instalación del piloto) y Cocina-Rosa el 22/09/2026, ambas por Carmen |
| Webcam nueva | «Logitech C270», conectada después a Sala-Rosa; ve el Comedor |
| Cámara en pausa | Pasillo, hasta las 11:42 (pausada por Luis a las 10:42) |
| Código de vinculación | `KQWT-MXHD` (solo letras de `BCDFGHJKLMNPQRSTVWXZ`; no usar dígitos ni vocales) |
| URL de vinculación | `tetengo.pe/vincular` *(ejemplo; dominio por confirmar)* |
| Horas | Hoy, miércoles 23/09/2026; ahora 10:42; caída a las 10:41:52; última señal «hace 6 s»; Cocina-Rosa sin conexión desde las 09:58 |
| Almacenamiento en la PC | «3,2 GB de 50 GB» (movimientos 1,1 GB, video 1,9 GB, clips 0,2 GB); carpeta `C:\Users\Rosa\AppData\Local\TeTengo\Datos` |
| Movimientos en la nube | Plazo 30 días; datos desde el 24/08/2026; «unos 40 a 80 MB por cámara al día (estimado)» |
| Diagnóstico | `te-tengo-diagnostico-Sala-Rosa-2026-09-23.zip` · 1,4 MB |
| Consentimiento de movimientos | Otorgado por Rosa Huamán, registrado por Carmen Huamán el 24/08/2026 a las 10:15 |

> El código de ejemplo que se pidió originalmente, `KQ7T-MX4D`, lleva dígitos; el alfabeto de la RFC 8628 que adoptamos no los tiene. Por eso se usa `KQWT-MXHD`.

## 3. Mapa de navegación

### 3.1. App móvil

La barra inferior no cambia: **Inicio · Historial · Familia · Ajustes**. Las pantallas nuevas cuelgan así (**nuevo** en negrita):

```
Arranque → Bienvenida / Iniciar sesión
Crear cuenta (no es un paso numerado)
Configuración (5 pasos)
  1 Persona cuidada · 2 Consentimiento · 3 **PC de la casa** (reemplaza «Tu cámara ya está lista»):
      **Vincula la PC de la casa** → Escanear / Escribir el código → Aprobar → **PC vinculada** → **Elige las cámaras**
  · 4 Familia · 5 Avisos
Inicio
  ├─ Tarjeta de estado de Rosa
  ├─ Sección «Cámaras» (**una fila por cámara, agrupada por PC si hay más de una**; sin cámaras: «Falta elegir las cámaras» › **Elige las cámaras**)
  │    └─ Detalle de cámara
  │         ├─ Ver en vivo
  │         ├─ **Ver qué pasó** (repetición del movimiento)
  │         ├─ **¿Hubo una caída y no avisó?**
  │         └─ **Dejar de usar esta cámara** (titular)
  └─ Esta semana
Historial
  ├─ Alerta → Clip (**interruptor «Puntos del cuerpo»**) · **Ver antes y después** (repetición)
  └─ **¿Hubo una caída y no avisó?** (enlace al pie)
Familia (sin cambios)
Ajustes
  ├─ Rosa Huamán
  ├─ **PCs y cámaras** (reemplaza «Cámara · Sala»)
  │    ├─ **Agregar PC** → Escanear QR / Escribir el código → Aprobar → PC vinculada → **Elige las cámaras**
  │    ├─ «Falta elegir las cámaras» / «N cámaras sin usar» → **Elige las cámaras**
  │    │    └─ **Vista previa** (hoja; como la vista en vivo, no se graba, queda en el registro de accesos)
  │    └─ **Detalle de la PC** → **Elige las cámaras** · Quitar esta PC
  ├─ Orden de aviso y espera
  ├─ Notificaciones
  ├─ Privacidad y consentimiento
  │    ├─ Constancia de consentimiento (existente)
  │    ├─ **Guardar movimientos** (consentimiento aparte) → Constancia / Revocar
  │    ├─ **Movimientos en la nube** (plazo)
  │    └─ Registro de accesos (**ahora incluye las repeticiones y las vistas previas**)
  ├─ **Actividad**
  └─ Tu cuenta · Cerrar sesión
```

### 3.2. Te Tengo Captura

Hoy es una sola ventana de estado. Se propone una navegación superior de tres pestañas dentro de la ventana de 960 × 640:

```
Arranque (480 × 300, morado)
  ├─ Sin vincular → **Vincular esta PC** (QR + código) → **Vinculada** («Carmen elige ahora las cámaras desde su celular»)
  └─ Vinculada → Ventana principal
        ├─ Estado (ventana actual, ahora con una fila por cámara)
        ├─ **Cámaras** (webcams conectadas y su estado, «Buscar de nuevo») · Esta PC → **Desvincular esta PC**
        │    └─ **Elegir cámaras** (respaldo del instalador: vista previa local y habitación, mismas reglas que M-29.1)
        └─ **Avanzado**
              ├─ Interruptor «Modo avanzado» (apagado por defecto)
              ├─ **Registro en vivo**   (requiere el modo avanzado)
              ├─ **Medidores**          (requiere el modo avanzado)
              ├─ **Actividad**          (siempre disponible)
              ├─ **Almacenamiento**     (siempre disponible)
              ├─ **Ver qué pasó**       (repetición, botón en la cabecera)
              └─ **Exportar diagnóstico** (botón en la cabecera)
Bandeja del sistema (sin cambios; nuevo aviso «Esta PC se quitó de la vivienda»)
```

## 4. Orden de diseño

Primero lo Must, luego Should y al final Could (prioridad MoSCoW del backlog).

| Orden | Historia | Plataforma | Prioridad | Por qué en este orden |
|---|---|---|---|---|
| 1 | US-28 Vinculación de la PC | Escritorio y móvil | Must | Sin vincular no hay nada más |
| 2 | US-29 Cámaras y ambientes | Móvil (respaldo del instalador en escritorio) | Must | Sigue a la vinculación |
| 3 | US-31 Desvincular una PC | Ambas | Must | Cierra el ciclo de la PC |
| 4 | US-35 Consentimiento para guardar movimientos | Móvil (y aviso en escritorio) | Must si se hace US-37 o US-38 | Condición de US-36 a US-39 |
| 5 | US-40 «¿Hubo una caída y no avisó?» | Móvil | Must | Única pantalla de US-40; el resto es un informe |
| 6 | US-30 Varias PCs | Móvil | Should | Extiende la lista de US-29 |
| 7 | US-37 Movimientos en la nube | Móvil | Should | Plazo de retención |
| 8 | US-38 Almacenamiento en la PC | Escritorio | Should | |
| 9 | US-32 Modo avanzado (registro y medidores) | Escritorio | Should | |
| 10 | US-33 Actividad | Ambas | Should | |
| 11 | US-39 Ver qué pasó (repetición) | Ambas | Could | La pantalla más compleja |
| 12 | US-36 Puntos del cuerpo en el clip | Móvil | Could | Un interruptor en el clip existente |
| 13 | US-34 Exportar diagnóstico | Escritorio | Could | Un diálogo |

---

## 5. App móvil

Numeración de pantallas: **M-xx.n** (xx = historia). Componentes citados: `appbar`, `notice`, `camRow`, `camHead`, `more()`, `fold()`, `kv`, `.list`/`.row`, `.chips`, `.code-box`, `.wait`, `.steps`, `.btn-primary`/`.btn-secondary`/`.btn-ghost`/`.btn-danger-ghost`, `lockNote`, `.ro-tag`, `constancia`, `clipBlock`, toasts y hojas inferiores.

### 5.1. US-28 · Agregar PC (vincular)

**Objetivo.** El titular vincula la PC de la casa en menos de un minuto, sin escribir contraseñas en la PC.
**Entradas.** Paso 3 de la configuración («Vincula la PC de la casa»); Ajustes › PCs y cámaras › «Agregar PC»; Inicio sin PCs (tarjeta «Aún no hay una PC vinculada»).
**Flujo.** M-28.1 Antes de empezar → M-28.2 Escanear → (M-28.3 Escribir el código) → M-28.4 Aprobar → M-28.5 PC vinculada → M-29.1 Elige las cámaras. Rechazo: M-28.6.

#### M-28.1 · Antes de empezar

- **Propósito.** Que el titular tenga la PC lista antes de abrir la cámara del celular.
- **Bloques.** Título; pasos numerados `.steps`; botón principal; enlace secundario.
- **Copy (borrador de copy — revisar).**
  - Título: «Vincula la PC de la casa»
  - Paso 1: «Instala Te Tengo Captura en la PC» · ayuda: «Descárgalo en tetengo.pe/captura desde esa PC.»
  - Paso 2: «Ábrelo. Verás un código QR y un código de 8 letras»
  - Paso 3: «Escanea el QR con este celular»
  - Principal: «Escanear el código QR» · Secundario: «Escribir el código»
- **Estados.** Invitado: no llega aquí; en Ajustes ve `lockNote` «Solo Carmen (titular) puede agregar una PC». Sin internet: banner existente «Sin internet» y botones deshabilitados.
- **Accesibilidad.** Pasos como lista ordenada (`<ol>`).

#### M-28.2 · Escanear el código QR

- **Propósito.** Leer el QR de la PC.
- **Bloques.** Visor de cámara a pantalla completa con marco cuadrado; texto arriba; botón inferior «Escribir el código»; botón de linterna.
- **Copy.** «Apunta al código QR que muestra la PC» · inferior: «¿No puedes escanearlo? Escribir el código».
- **Estados.**
  - *Permiso de cámara pendiente:* antes del diálogo del sistema, explicar por qué: «Para escanear el código, Te Tengo necesita usar la cámara de este celular. No guardamos ninguna imagen.» → «Permitir».
  - *Permiso denegado:* `notice('warn')` «La cámara del celular está bloqueada para Te Tengo» + «Abrir los ajustes del celular» y, como principal, «Escribir el código».
  - *QR que no es de Te Tengo:* toast «Ese código no es de Te Tengo Captura».
  - *Leyendo:* el marco se pone verde y se pasa a M-28.4 con un indicador de carga («Buscando la PC…»).
- **Accesibilidad.** El visor no es usable con lector de pantalla: el foco inicial va a «Escribir el código» si el lector está activo.

#### M-28.3 · Escribir el código

- **Propósito.** Respaldo cuando no se puede escanear (CA-28.2).
- **Bloques.** Título; campo único con máscara `XXXX-XXXX` en Atkinson Hyperlegible Mono (como `.code-box`); ayuda; botón «Continuar».
- **Copy.** Título «Escribe el código de la PC» · ayuda «Son 8 letras. Lo ves debajo del código QR en Te Tengo Captura.» · placeholder `XXXX-XXXX`.
- **Comportamiento.** Acepta minúsculas y con o sin guion; convierte a mayúsculas e inserta el guion. Solo admite las letras del código: si se escribe una vocal o un dígito, se ignora y aparece la ayuda «El código solo lleva consonantes, sin números».
- **Estados y errores** (`field-msg` con ícono `warn`):
  - *Incompleto:* botón deshabilitado hasta 8 letras.
  - *Incorrecto:* «Ese código no existe. Revísalo letra por letra.» (CA-28.6 cuenta el intento).
  - *Vencido o usado:* «Este código ya venció o ya se usó. La PC ya muestra uno nuevo: escríbelo o escanéalo.» (CA-28.3)
  - *Bloqueado:* tras 5 intentos fallidos, `notice('warn','clock')` «Demasiados intentos. Podrás volver a intentarlo a las 10:57.» y campo deshabilitado (CA-28.6, igual que CA-02.3).
  - *Sin internet:* «Sin internet. Revisa tu conexión y vuelve a intentarlo.»
- **Accesibilidad.** `inputmode="text"`, `autocapitalize="characters"`, `autocomplete="one-time-code"`; el lector anuncia «K Q W T, guion, M X H D».

#### M-28.4 · Aprobar la PC

- **Propósito.** Que el titular confirme que es **su** PC antes de vincularla (CA-28.4; defensa contra la aprobación de una PC ajena, RFC 8628 §5.4).
- **Bloques (en orden).**
  1. Ícono de PC en morado suave y título.
  2. Tarjeta con `kv`: Nombre de la PC «Sala-Rosa» · Sistema «Windows 11 Home» · Programa «Te Tengo Captura 0.5.0» · Código «KQWT-MXHD».
  3. «Si la apruebas, esta PC podrá:» lista con íconos: «Usar sus cámaras para detectar caídas y movimientos inestables» · «Enviar a Te Tengo los avisos y los clips de 12 segundos» · «Mostrar la vista en vivo cuando un familiar la abra».
  4. Aviso neutro: «Apruébala solo si estás frente a la PC de la casa de Rosa o si tú la instalaste.»
  5. Botones: principal «Aprobar» · secundario `btn-danger-ghost` «No reconozco esta PC».
- **Copy.** Título: «¿Vinculamos esta PC a la casa de Rosa?»
- **Estados.**
  - *Invitado (CA-28.5):* sin botón «Aprobar»; `lockNote` «Solo Carmen (titular) puede vincular una PC. Pídele que escanee el código.»
  - *Código vence mientras decide:* al pulsar «Aprobar», mensaje de CA-28.3 y vuelta a M-28.2.
  - *Aprobando:* botón con carga «Vinculando…».
  - *Error de red:* `notice('warn')` «No pudimos vincular la PC. Revisa tu conexión y vuelve a intentarlo.»

#### M-28.5 · PC vinculada

- **Propósito.** Confirmar y llevar al siguiente paso, que ocurre en el mismo celular: elegir las cámaras (M-29.1, US-29). En la configuración sigue siendo el paso 3.
- **Bloques.** Ícono `check` en `--calma-soft` (como «La cámara de la sala está conectada» de trabajo futuro); título; texto; tarjeta de la PC con su estado («Falta elegir las cámaras»); botones.
- **Copy.** «La PC Sala-Rosa está vinculada» · «Ahora elige desde aquí qué cámaras usar y en qué habitación está cada una. No hace falta ir a la PC.» · principal «Elegir las cámaras» (M-29.1) · `btn-ghost` «Hacerlo después» con la nota «Sin cámaras elegidas no detectamos caídas.»
- **Estados.** *Sin consentimiento:* aviso «Falta el consentimiento de Rosa» · «Las cámaras no enviarán nada hasta que registres el consentimiento.» con «Completar el consentimiento». *Cámaras ya elegidas* (por ejemplo, por el instalador en la PC): «Sus cámaras ya están elegidas.», la lista de cámaras «En línea» y el botón «Listo» (en la configuración, «Continuar»).

#### M-28.6 · No reconozco esta PC

- **Copy.** Hoja inferior: «No vinculamos la PC» · «Si alguien te pidió escanear un código que no es de la casa de Rosa, no lo hagas. La PC no tendrá acceso.» · «Entendido».
- **Efecto.** La PC recibe el rechazo (`access_denied`) y muestra D-28.5.

#### Wireframe · M-28.2, M-28.3 y M-28.4

```
┌──────────────────────────┐ ┌──────────────────────────┐ ┌──────────────────────────┐
│ ←  Agregar PC            │ │ ←  Agregar PC            │ │ ←  Aprobar la PC         │
│ Apunta al código QR que  │ │ Escribe el código de     │ │  [PC]                    │
│ muestra la PC            │ │ la PC                    │ │ ¿Vinculamos esta PC a    │
│ ┌──────────────────────┐ │ │ ┌──────────────────────┐ │ │ la casa de Rosa?         │
│ │                      │ │ │ │   K Q W T - M X H D  │ │ │ ┌──────────────────────┐ │
│ │    ┌──────────┐      │ │ │ └──────────────────────┘ │ │ │ Nombre     Sala-Rosa │ │
│ │    │  marco   │      │ │ │ Son 8 letras. Lo ves     │ │ │ Sistema  Windows 11  │ │
│ │    │   QR     │      │ │ │ debajo del código QR en  │ │ │ Programa  Captura 0.5│ │
│ │    └──────────┘      │ │ │ Te Tengo Captura.        │ │ │ Código    KQWT-MXHD  │ │
│ │          (linterna)  │ │ │                          │ │ └──────────────────────┘ │
│ └──────────────────────┘ │ │ ⚠ Ese código no existe.  │ │ Si la apruebas, podrá:   │
│                          │ │   Revísalo letra por     │ │ ▸ Usar sus cámaras…      │
│ ¿No puedes escanearlo?   │ │   letra.                 │ │ ▸ Enviar avisos y clips  │
│ [ Escribir el código ]   │ │ [      Continuar       ] │ │ ▸ Mostrar la vista en …  │
└──────────────────────────┘ └──────────────────────────┘ │ ⓘ Apruébala solo si …    │
                                                          │ [       Aprobar        ] │
                                                          │ [ No reconozco esta PC ] │
                                                          └──────────────────────────┘
```

### 5.2. US-29 y US-30 · PCs y cámaras

**Objetivo.** Elegir desde el celular qué webcams de cada PC cuidan la casa y en qué habitación está cada una, y ver de un vistazo qué PCs y cámaras cuidan la casa y en qué estado están.
**Entradas.** M-28.5 › «Elegir las cámaras»; Ajustes › «PCs y cámaras» (fila con resumen «2 PCs · 4 cámaras»); Inicio › sección «Cámaras» › «Ver todas».
**Flujo.** M-29.1 Elige las cámaras (con M-29.2 Vista previa y M-29.3 Dejar de usar) · M-30.1 Lista → M-30.2 Detalle de la PC → Detalle de cámara (existente, ampliado).

#### M-29.1 · Elige las cámaras

- **Propósito.** Que el titular diga, sin ir a la PC, qué webcams usar y en qué habitación está cada una (CA-29.1, CA-29.2). En la configuración va después de M-28.5, dentro del paso 3 de 5.
- **Entradas.** M-28.5 › «Elegir las cámaras»; M-30.2 › «Elegir las cámaras» (sub «1 cámara sin usar» o «Usa otra cámara o deja de usar una»); M-30.1 › aviso «Falta elegir las cámaras» › «Elegir las cámaras» o fila «1 cámara sin usar»; Inicio y tarjeta de Rosa sin cámaras › «Elegir las cámaras».
- **Bloques.** `appbar` con el nombre de la PC (en la configuración, la cabecera del paso 3); título «Elige las cámaras»; frase «La PC Sala-Rosa encontró 3 cámaras. Dinos en qué habitación está cada una; por ahora, cada habitación usa una sola cámara.»; una tarjeta por webcam detectada, abierta de a una (al llegar, la primera sin usar):
  - *Cabecera:* ícono de estado, nombre del dispositivo («Webcam USB HD») y estado con texto: «Sin usar», «En uso · Sala», «En uso · Sala · en pausa», «Desconectada» o «Desconectada · Pasillo».
  - *Sin usar y conectada:* «Ver vista previa» (M-29.2) con «No se graba. Queda en el registro de la familia.»; «¿En qué habitación está?» con chips Sala, Dormitorio, Cocina, Comedor, Pasillo y «Otra…» (abre el campo «Nombre de la habitación»); nota fija «Por privacidad, Te Tengo no admite cámaras en el baño.»; principal «Usar esta cámara» (deshabilitado hasta elegir).
  - *En uso:* «Ver vista previa» y `btn-danger-ghost` «Dejar de usar» (M-29.3).
  - Debajo de la lista: «¿Falta una cámara? Pide que la conecten por USB a la PC.» con «Buscar de nuevo»; botón «Listo» (en la configuración, «Continuar», que lleva a Familia).
- **Validaciones** (como CA-29.2 y CA-29.3). *Habitación con cámara en cualquier PC:* chip deshabilitado, legible, con «Ya tiene cámara». *Nombre escrito repetido:* «Ya hay una cámara en la Cocina (PC Cocina-Rosa). Por ahora, cada habitación usa una sola cámara.» *Baño:* «Por privacidad, Te Tengo no admite cámaras en el baño.» *Nombre vacío:* «Escribe el nombre de la habitación.»
- **Estados.**
  - *Guardado:* toast «La cámara Webcam USB HD cuida ahora la Sala» · «Las próximas alertas dirán «en la Sala».»; se abre la siguiente webcam sin usar; Inicio y M-30.1 muestran la cámara; Actividad registra «Carmen eligió la cámara Webcam USB HD para la Sala».
  - *Cámara asignada desconectada (CA-29.5):* tarjeta con borde discontinuo, «Desconectada · Pasillo» y «Revisa el cable USB. Pasillo sigue con esta cámara: no pasa a otra.»; se puede «Dejar de usar».
  - *Webcam sin usar desconectada:* «Pide a alguien en la casa que la conecte por USB a la PC.»
  - *Otra webcam conectada (CA-29.4):* aparece «Sin usar»; las asignaciones existentes no cambian. No se manda aviso: en M-30.1 y M-30.2 aparece la fila «1 cámara sin usar».
  - *Buscando:* `.wait` «Buscando cámaras en la PC Sala-Rosa…».
  - *Sin cámaras (CA-29.6):* «No encontramos cámaras en la PC Sala-Rosa» · «Pide a alguien en la casa que conecte una webcam por USB a la PC.» · «Buscar de nuevo».
  - *PC sin conexión (CA-30.3):* sin lista; `notice('warn')` «La PC Cocina-Rosa no responde» · «Sin conexión desde las 09:58. Cuando vuelva, verás aquí sus cámaras.» y «Qué revisar».
  - *Sin consentimiento (CA-05.2):* aviso «Falta el consentimiento de Rosa» · «Puedes elegir las cámaras, pero no habrá vista previa ni detección hasta que lo registres.»
  - *Invitado (CA-08.4):* tarjetas cerradas en solo lectura y `lockNote` «Solo Carmen (titular) puede elegir las cámaras».
  - *Muchas cámaras:* desde la tercera en uso en una PC, nota neutra «Cada cámara usa más la PC. Si la detección se vuelve lenta, conecta algunas cámaras a otra PC.» (sin cifras).
- **Accesibilidad.** Cabeceras de tarjeta como botones con `aria-expanded`; chips con `aria-pressed` dentro de un grupo con nombre («¿En qué habitación está?»); el chip deshabilitado lleva su razón como texto, no solo opacidad.

#### M-29.2 · Vista previa

- **Propósito.** Reconocer qué habitación ve cada webcam antes de elegirla (CA-29.1). Se trata como la vista en vivo: la cubre la cláusula de vista en vivo del consentimiento (CA-05.4), no se graba y cada apertura queda en el registro de accesos (CA-24.1).
- **Bloques.** Hoja inferior: «Vista previa · Webcam USB HD» · «Así sabes qué habitación ve esta cámara.»; imagen 4:3 con la etiqueta «● VISTA PREVIA · 0:12» (cuenta regresiva de 15 s); «No se graba. Tu acceso queda en el registro de la familia.» · «Es como la vista en vivo: Rosa la autorizó en su consentimiento. Se cierra sola a los 15 s.»; botón «Cerrar».
- **En el prototipo.** Ilustración de la habitación que ve esa webcam, sin personas (regla de los prototipos); en el producto, la imagen real, que sale de la casa solo mientras se mira, como la vista en vivo.
- **Al cerrar** (cuenta a cero, «Cerrar», tocar fuera o Escape): toast «Acceso registrado» · «Viste la vista previa de Webcam USB HD durante 15 s.» y fila en el registro de accesos «Vista previa al elegir cámaras · Webcam USB HD» · «Carmen (tú) · Empezó a las 10:44 · duró 15 s».
- **No disponible** (en lugar de la imagen, con el motivo): «La PC Cocina-Rosa no responde»; «La cámara está desconectada» · «Pide a alguien en la casa que revise el cable USB.»; «Falta el consentimiento de Rosa» · «Sin el consentimiento de Rosa no hay video, tampoco para la vista previa.»; «La cámara está en pausa» · «Hasta las 11:42. Reanúdala para ver la vista previa.»

#### M-29.3 · Dejar de usar una cámara

- **Entradas.** M-29.1 › «Dejar de usar»; Detalle de cámara › «Dejar de usar esta cámara» (solo titular).
- **Hoja.** «¿Dejar de usar la cámara USB2.0 PC Camera?» · «Dejaremos de detectar caídas en el Pasillo. La cámara sigue conectada a la PC y puedes volver a elegirla.» · `btn-danger` «Dejar de usar» · «Cancelar».
- **Resultado.** Toast «Dejamos de usar la cámara USB2.0 PC Camera» · «Ya no detectamos caídas en el Pasillo.»; la webcam vuelve a «Sin usar»; Actividad registra «Carmen dejó de usar la cámara USB2.0 PC Camera del Pasillo».

#### M-30.1 · PCs y cámaras

- **Bloques.** `appbar('PCs y cámaras')`; banner de consentimiento si falta (`consentLock`); una tarjeta por PC; botón «Agregar PC» (solo titular).
- **Tarjeta de PC.** Cabecera: ícono de PC, nombre («Sala-Rosa»), estado con ícono y texto («En línea · última señal hace 6 s» en verde, o «Sin conexión desde las 09:58» en ámbar punteado), y versión en `t-meta` («Te Tengo Captura 0.5.0»). Debajo, `camRow` por cámara: ambiente, estado (En línea, Desconectada, Detección no confiable, En pausa hasta las 11:42, Detenida) y última señal. Toda la cabecera abre M-30.2.
- **Estados.**
  - *Cargando:* dos tarjetas esqueleto.
  - *Sin PCs:* ilustración de PC, «Aún no hay una PC vinculada» · «Vincula la PC de la casa para empezar a cuidar a Rosa.» · «Agregar PC» (titular) o `lockNote` (invitado).
  - *PC sin cámaras elegidas:* `notice('info','cam')` «Falta elegir las cámaras» · «Elige qué cámaras de la PC usar y en qué habitación está cada una.» con «Elegir las cámaras» (M-29.1; solo titular).
  - *Webcam sin usar en una PC:* fila «1 cámara sin usar» · «Elige en qué habitación está» bajo sus cámaras (M-29.1).
  - *PC sin conexión (CA-30.3):* tarjeta en ámbar punteado, cámaras en gris con «Sin conexión», y `more()` «Qué revisar»: «Que la PC esté encendida» · «Que tenga internet» · «Que Te Tengo Captura esté abierto (ícono junto al reloj)». Las demás PCs siguen normales.
  - *Invitado:* sin «Agregar PC»; `.ro-tag` «Solo ver» en la cabecera.
- **Con una sola PC**, la lista no muestra la cabecera de la PC como tarjeta aparte: muestra las cámaras y una fila «PC de la casa · Sala-Rosa».

#### M-30.2 · Detalle de la PC

- **Bloques.** Cabecera con nombre y estado; `kv`: Sistema «Windows 11 Home» · Programa «Te Tengo Captura 0.5.0» · Vinculada «03/08/2026 por Carmen» · Última señal «10:42»; lista de cámaras y, al final, la fila «Elegir las cámaras» (M-29.1; sub «1 cámara sin usar» o «Usa otra cámara o deja de usar una»); sección «Quitar» (solo titular) con texto y `btn-danger-ghost` «Quitar esta PC» (US-31).
- **Estados.** Invitado: sin «Elegir las cámaras» ni sección «Quitar»; `lockNote` «Solo Carmen (titular) puede elegir las cámaras o quitar esta PC» (CA-31.5).

#### Detalle de cámara (existente, `S.camara`) · cambios

- `camHead` agrega «En la PC Sala-Rosa» en «Datos de la instalación» (plegado) y reemplaza «Equipo de Te Tengo» por «Elegida el 03/08/2026».
- Acciones nuevas debajo de «Ver en vivo»: «Ver qué pasó» (US-39) y enlace «¿Hubo una caída y no avisó?» (US-40).
- «Nombre de la habitación» sigue igual (la interfaz dice «habitación», §1), con los mismos chips (Sala, Sala comedor, Comedor, Dormitorio, Cocina, Pasillo) y la validación «Escribe el nombre de la habitación.». Si el nombre ya lo usa otra cámara: «Ya hay una cámara en la Sala. Por ahora, cada habitación usa una sola cámara.» (CA-29.3).
- Al final, solo para el titular: `btn-danger-ghost` «Dejar de usar esta cámara» con «Deja de detectar caídas en la Sala. La cámara sigue conectada a la PC.» (M-29.3).

#### Inicio · sección «Cámaras»

- Con varias cámaras: hasta 4 filas `camRow` y «Ver todas (4)». Con varias PCs, cada fila dice el ambiente y, en `sub`, la PC solo si hay ambientes repetidos entre PCs (no debería ocurrir por CA-29.3).
- La tarjeta de estado de Rosa resume: «Todo tranquilo · 4 cámaras cuidando» o, con problema, «1 cámara no responde · Cocina» (franja ámbar).

#### Wireframe · M-30.1

```
┌──────────────────────────────┐
│ ←  PCs y cámaras             │
│ ┌──────────────────────────┐ │
│ │ [PC] Sala-Rosa         › │ │
│ │ ● En línea · hace 6 s    │ │
│ │ Te Tengo Captura 0.5.0   │ │
│ │──────────────────────────│ │
│ │ [cám] Sala       En línea│ │
│ │ [cám] Dormitorio En línea│ │
│ │ [▥]  Pasillo  En pausa   │ │
│ │       hasta las 11:42    │ │
│ └──────────────────────────┘ │
│ ┌┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┐ │
│ ┆ [PC] Cocina-Rosa       › ┆ │
│ ┆ ⚠ Sin conexión desde     ┆ │
│ ┆   las 09:58              ┆ │
│ ┆ [cám] Cocina Sin conexión┆ │
│ ┆ ▸ Qué revisar            ┆ │
│ └┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┘ │
│ [ + Agregar PC             ] │
└──────────────────────────────┘
```

### 5.3. US-31 · Quitar una PC

**Entrada.** M-30.2 › «Quitar esta PC» (solo titular).

- **M-31.1 · Confirmación (hoja inferior).** «¿Quitar la PC Sala-Rosa?» · «Dejaremos de detectar caídas en Sala, Dormitorio y Pasillo. La PC borrará su acceso y volverá a mostrar el código QR.» · `btn-danger` «Quitar la PC» · «Cancelar» (CA-31.4: cancelar no cambia nada).
- **M-31.2 · Resultado.** Toast «Quitamos la PC Sala-Rosa» y vuelta a M-30.1 sin esa PC. Si estaba sin conexión (CA-31.2): toast «Quitamos la PC Sala-Rosa. Dejará de capturar en cuanto se conecte.»
- **Aviso a la familia** cuando se desvincula desde la PC (CA-31.3): notificación no urgente «La PC Sala-Rosa se desvinculó desde la propia PC. Ya no detecta caídas en Sala, Dormitorio y Pasillo.» con «Ver PCs y cámaras».
- **Si era la única PC:** la tarjeta de estado de Rosa pasa a «Sin cámaras» (gris, candado) y el Inicio muestra «Agregar PC».

### 5.4. US-35 · Guardar movimientos (consentimiento aparte)

**Objetivo.** Registrar, con la información que pide la ley, si Rosa acepta que se guarden sus movimientos. Es opcional y no afecta las alertas.
**Entradas.** Ajustes › Privacidad › «Guardar movimientos» (sub: «No autorizado» o «Vigente desde el 24/08/2026»); cualquier opción desactivada por falta de este consentimiento («Requiere el permiso de Rosa para guardar movimientos» › «Ver»).

#### M-35.1 · ¿Guardamos los movimientos de Rosa?

- **Bloques (en orden).**
  1. Título y una frase: «Guardar los movimientos de Rosa es opcional. Las alertas funcionan igual si no lo aceptas.»
  2. Ilustración: esqueleto de puntos sobre fondo neutro (nunca una foto).
  3. Resumen en filas `fold()` (como el consentimiento de monitoreo):
     - **Para qué** · «Para que la familia pueda ver qué pasó antes y después de un aviso, y para mejorar la detección.»
     - **Qué guardamos** · «Solo los puntos del cuerpo que el programa calcula (hombros, caderas, rodillas…), sin imagen ni video.»
     - **Dónde** · «En la PC de la casa y, si lo eliges, en la nube de Te Tengo. La nube usa servidores fuera del Perú.»
     - **Cuánto tiempo** · «Tú eliges el plazo: en la nube, de 7 días a 1 año; en la PC, también puedes no borrarlos.»
     - **Quién puede verlos** · «Solo los familiares vinculados. Cada vez que alguien repite un momento, queda en el registro de accesos.»
     - **Sus derechos** · «Rosa puede pedir ver, corregir, borrar sus datos u oponerse a su uso en privacidad@tetengo.pe (Ley N.° 29733).»
  4. ¿Quién da el permiso? (radio): «Rosa, en persona» · «Su representante» (campo de nombre).
  5. Casilla: «Rosa aceptó que se guarden sus movimientos para estos fines.»
  6. Botones: «Registrar el permiso» (deshabilitado sin la casilla) · `btn-ghost` «Ahora no».
  7. Enlace «Leer el documento completo» (`docPage`, un solo texto como `CONSENT_SEC`).
- **Estados.**
  - *Sin consentimiento de monitoreo:* `consentLock` primero; esta pantalla no se puede usar.
  - *Invitado:* lectura de este resumen y `lockNote` «Solo Carmen (titular) puede registrar este permiso».
  - *Registrado (CA-35.2):* M-35.2.
  - *Error de red:* `notice('warn')` «No pudimos registrar el permiso. Nada se guardó todavía.»
- **Accesibilidad.** La casilla y los radios con nombre accesible completo; filas plegables con estado expandido anunciado.

#### M-35.2 · Constancia del permiso

- Reutilizar `constancia`: banda verde, «Permiso para guardar movimientos», «Otorgado por Rosa Huamán», «Registrado por Carmen Huamán», «24/08/2026 · 10:15», «Versión del texto: 1», mención a la Ley N.° 29733.
- Debajo: «Movimientos en la nube» (fila a M-37.1) y «Dejar de guardar movimientos» (`btn-danger-ghost`, solo titular).

#### M-35.3 · Dejar de guardar movimientos (CA-35.4)

- Hoja: «¿Dejar de guardar los movimientos de Rosa?» · «Borraremos los movimientos guardados en la nube. En la PC de la casa te preguntaremos si también quieres borrarlos. Las alertas siguen igual.» · `btn-danger` «Dejar de guardar» · «Cancelar».
- Progreso (como «Eliminando las grabaciones»): «Borrando los movimientos de la nube…» → «Listo. Ya no guardamos los movimientos de Rosa.» (notificación al terminar).

#### Wireframe · M-35.1

```
┌──────────────────────────────┐
│ ←  Guardar movimientos       │
│ ¿Guardamos los movimientos   │
│ de Rosa?                     │
│ Es opcional. Las alertas     │
│ funcionan igual si no lo     │
│ aceptas.                     │
│        o                     │
│       /|\    (esqueleto)     │
│       / \                    │
│ ▸ Para qué                   │
│ ▸ Qué guardamos   sin imagen │
│ ▸ Dónde   PC y nube (fuera…) │
│ ▸ Cuánto tiempo              │
│ ▸ Quién puede verlos         │
│ ▸ Sus derechos               │
│ ¿Quién da el permiso?        │
│ (•) Rosa, en persona         │
│ ( ) Su representante         │
│ [✓] Rosa aceptó que se       │
│     guarden sus movimientos… │
│ [   Registrar el permiso   ] │
│ [         Ahora no         ] │
│ Leer el documento completo   │
└──────────────────────────────┘
```

### 5.5. US-37 · Movimientos en la nube

**Entrada.** Ajustes › Privacidad › «Movimientos en la nube» (sub: «Desactivado» o «Se guardan 30 días»); M-35.2.

#### M-37.1 · Plazo en la nube

- **Bloques.** Título; frase «Elige cuánto tiempo guardamos los movimientos de Rosa en la nube. Se borran solos al cumplirse el plazo.»; lista de opciones (radio, 48 dp):
  - «No guardar en la nube» (opción inicial, CA-37.1)
  - «7 días»
  - «30 días»
  - «90 días»
  - «1 año» con etiqueta «Máximo recomendado»
- Debajo: `kv` «Espacio aproximado: 40 a 80 MB por cámara al día (estimado)» · «Hay movimientos desde: 24/08/2026» · «Cámaras: 4»; nota «Nunca guardamos video en la nube.»
- **Confirmación al acortar (CA-37.4).** Hoja: «¿Guardar solo 7 días?» · «Borraremos los movimientos anteriores al 16/09/2026. No se pueden recuperar.» · «Guardar 7 días» · «Cancelar».
- **Estados.** *Sin permiso de movimientos:* opciones deshabilitadas con borde punteado y `notice` «Primero registra el permiso de Rosa para guardar movimientos» → M-35.1. *Invitado:* solo lectura con `.ro-tag`. *Sin internet:* «No pudimos guardar el cambio. Revisa tu conexión.» y la opción vuelve a la anterior. *PC sin internet:* nota «La PC Cocina-Rosa tiene movimientos pendientes de subir; se subirán cuando vuelva la conexión.» (CA-37.3).

#### Wireframe · M-37.1

```
┌──────────────────────────────┐
│ ←  Movimientos en la nube    │
│ Elige cuánto tiempo los      │
│ guardamos. Se borran solos.  │
│ ( ) No guardar en la nube    │
│ ( ) 7 días                   │
│ (•) 30 días                  │
│ ( ) 90 días                  │
│ ( ) 1 año   [Máximo recom.]  │
│ ──────────────────────────── │
│ Espacio aprox.  40–80 MB por │
│                 cámara al día│
│ Hay datos desde  24/08/2026  │
│ ⓘ Nunca guardamos video en   │
│   la nube.                   │
└──────────────────────────────┘
```

### 5.6. US-36 · Puntos del cuerpo en el clip

- **Dónde.** `clipBlock` de la alerta (detalle e historial), en la barra de controles junto a la velocidad.
- **Control.** Interruptor con texto «Puntos del cuerpo» (no solo ícono). Activo: el esqueleto se dibuja sincronizado sobre la ilustración del clip; inactivo: el clip sin esqueleto. *Nota:* hoy el prototipo ya dibuja el esqueleto dentro de la ilustración; el diseño debe separar ilustración y capa de puntos para que el interruptor tenga efecto visible.
- **Estados (CA-36.2).** Sin permiso de movimientos o sin archivo: interruptor deshabilitado y debajo «Los puntos del cuerpo no están disponibles: falta el permiso de Rosa para guardar movimientos» o «…: este clip no los tiene». Clip eliminado por retención: mensaje existente «La grabación ya no está disponible» (CA-26.3), sin interruptor.
- **Pantalla completa.** El interruptor se mantiene en la barra horizontal.

### 5.7. US-39 · Ver qué pasó (repetición del movimiento)

**Objetivo.** Ver, como esqueleto animado, qué pasó en una cámara en un momento dado, con los eventos marcados.
**Entradas.** Detalle de cámara › «Ver qué pasó»; alerta › «Ver antes y después» (abre en la cámara y la hora del evento, 1 minuto antes); registro de accesos (fila de una repetición › «Abrir de nuevo»).
**Flujo.** M-39.1 Elegir momento → M-39.2 Repetición.

#### M-39.1 · Elegir el momento

- **Bloques.** Cámara (chips por ambiente: Sala, Dormitorio, Pasillo, Cocina); fecha (selector de día con los días disponibles marcados); hora (selector HH:MM) y atajos en chips «Hace 15 min», «Hace 1 hora», «Hoy 07:00»; botón «Ver».
- **Texto de contexto.** «Hay movimientos desde el 24/08/2026 hasta hace 5 minutos.» (los últimos 5 minutos aún se están subiendo).
- **Estados.** *Sin permiso:* `notice` «Para ver qué pasó, Rosa debe aceptar que se guarden sus movimientos.» → «Ver el permiso». *Sin movimientos en la nube (plazo desactivado):* «No guardamos movimientos en la nube. Puedes activarlo en Movimientos en la nube.» *Fuera del plazo (CA-39.4):* días fuera del plazo deshabilitados; si se llega por un enlace antiguo: «Ya no hay movimientos de ese momento. Hay datos desde el 24/08/2026.»

#### M-39.2 · Repetición

- **Bloques (en orden).**
  1. `appbar` «Sala · miércoles 23/09 · 10:41:52» (hora actual de la reproducción en Mono).
  2. Franja de privacidad, siempre visible: ícono de ojo + «Solo puntos del cuerpo, nunca video · Esta repetición queda en el registro de accesos».
  3. Lienzo: esqueleto animado sobre fondo neutro con línea de piso; sin ilustración de la habitación ni imagen.
  4. Etiqueta de fase en lenguaje sencillo, encima del lienzo: «De pie», «Posible caída», «En el suelo», «Se levantó».
  5. Línea de tiempo (rango de 10 minutos, desplazable; zoom «10 min · 1 h»): marcas de eventos con forma + color + texto (triángulo rojo «Caída», rombo mostaza «Inestable», círculo verde «Se levantó») y tramos sin datos con rayado gris («Sin persona», «En pausa», «PC apagada»).
  6. Controles (48 dp): «Evento anterior», «Reproducir/Pausar», «Evento siguiente», velocidad en ciclo «0,5× · 1× · 2× · 4×» (como el clip, más 4× para recorrer tramos largos).
  7. Lista plegable «Eventos de este tramo»: «10:41:52 · Caída · Sala» › salta a ese punto.
- **Comportamiento.** La reproducción salta los tramos sin datos y muestra un toast breve «Sin datos de 10:20 a 10:35 · Sin persona en la imagen» (CA-39.5).
- **Estados.**
  - *Cargando:* lienzo con indicador «Preparando la repetición…».
  - *Sin internet:* «Sin internet. La repetición necesita conexión.»
  - *Permiso revocado mientras se mira:* se detiene y muestra «Rosa ya no autoriza guardar sus movimientos. Los borramos de la nube.»
  - *Al cerrar (CA-39.3):* toast «Acceso registrado», igual que la vista en vivo.
- **Accesibilidad.** La línea de tiempo es un `slider` con valor textual («10:41:52, caída»); las marcas son botones con nombre; con lector de pantalla, la lista «Eventos de este tramo» es el camino principal; respetar `prefers-reduced-motion` (sin interpolación, pasos por fotograma).

#### Registro de accesos (existente) · cambios

- Filas de dos tipos con ícono distinto: «Vista en vivo · Sala» y «Repetición · Sala, 23/09 10:41». Texto: «Carmen · Empezó a las 10:45 · duró 2 min 10 s».
- Filtro en chips «Todo · Vista en vivo · Repeticiones». Vacío: «Aún no hay accesos registrados».

#### Wireframe · M-39.2

```
┌──────────────────────────────┐
│ ←  Sala · mié 23/09 10:41:52 │
│ (ojo) Solo puntos del cuerpo,│
│ nunca video · Queda en el    │
│ registro de accesos          │
│ ┌──────────────────────────┐ │
│ │  Posible caída           │ │
│ │            o             │ │
│ │           /|\            │ │
│ │           / \            │ │
│ │ ──────────────── (piso)  │ │
│ └──────────────────────────┘ │
│ 10:35      10:40       10:45 │
│ ▒▒▒▒▒|────◆──▲───●────|────  │
│ sin    inest caída se        │
│ persona            levantó   │
│ [10 min] [1 h]               │
│  |◀   ▶ Reproducir   ▶|  1×  │
│ ▸ Eventos de este tramo (3)  │
└──────────────────────────────┘
```

### 5.8. US-33 · Actividad

**Entrada.** Ajustes › «Actividad» (sub: «Último cambio: hoy 10:31»).

- **Bloques.** Filtro en chips por PC («Todas · Sala-Rosa · Cocina-Rosa»); lista agrupada por día («Hoy», «Ayer», «21/09/2026»); filas con avatar o ícono de PC, frase y hora.
- **Ejemplos de filas (borrador de copy — revisar).**
  - Hoy · «Luis pausó la cámara del Pasillo hasta las 11:42» · 10:42
  - Hoy · «Desde la PC Sala-Rosa: la cámara Logitech C920 pasó a Dormitorio» · 10:33 (respaldo del instalador, hecho en la PC)
  - Hoy · «Desde la PC Sala-Rosa: se activó el modo avanzado» · 10:12
  - Ayer · «Carmen eligió la cámara HD Pro Webcam para la Cocina» · 18:44 (desde el celular, lo normal)
  - Ayer · «Carmen vinculó la PC Cocina-Rosa» · 18:40
  - 21/09/2026 · «Carmen cambió los movimientos en la nube de 7 a 30 días» · 12:20
  - 24/08/2026 · «Carmen registró el permiso de Rosa para guardar movimientos» · 10:15
- **Detalle (toque en la fila).** Hoja con `kv`: Quién · Desde (celular de Carmen / PC Sala-Rosa) · Antes · Después · Fecha y hora.
- **Estados.** *Vacío (CA-33.4):* «Aún no hay actividad registrada». *Cargando:* filas esqueleto. *Invitado:* ve lo mismo (CA-33.2). Nadie puede borrar filas: no hay acción de borrar.

### 5.9. US-40 · ¿Hubo una caída y no avisó?

**Objetivo.** Que la familia pueda decir que hubo una caída sin alerta, para revisarla.
**Entradas.** Historial (enlace al pie, siempre visible); detalle de cámara (enlace); opcionalmente, «Más detalles» de una alerta de movimiento inestable («¿Terminó en caída y no avisamos?»).

#### M-40.1 · Contarnos qué pasó

- **Bloques (en orden).**
  1. `notice('danger')` arriba, siempre: «Si Rosa necesita ayuda ahora, llama al SAMU · 106» con botón de llamada (como la tarjeta «¿Rosa no contesta?»).
  2. Título: «¿Hubo una caída y no te avisamos?» · frase: «Cuéntanos dónde y a qué hora. Lo revisaremos para mejorar la detección.»
  3. Ambiente (chips): Sala, Dormitorio, Pasillo, Cocina, «No sé».
  4. Fecha y hora aproximada (selectores, por defecto hoy y la hora actual redondeada).
  5. «¿Qué pasó?» (texto opcional, 300 caracteres, con ejemplo «Se resbaló al salir de la cama»).
  6. Nota: con permiso de movimientos, «Revisaremos los movimientos de ese momento»; sin él, «No tenemos movimientos guardados de ese momento; revisaremos lo que nos cuentes.»
  7. Botón «Enviar».
- **M-40.2 · Enviado.** «Gracias, Carmen. Lo revisaremos.» · «Esto no genera una alerta ni avisa a la familia.» · «Volver al historial».
- **Estados.** *Sin internet:* «No pudimos enviarlo. Lo guardamos y lo enviaremos cuando vuelva la conexión.» *Hora en el futuro:* «Elige una hora que ya pasó.» *Invitado:* puede enviarlo (no cambia la configuración).

---

## 6. Te Tengo Captura (escritorio)

Numeración: **D-xx.n**. Ventana de 960 × 640 con barra de título de 36 px; tarjetas de 18 px y controles de 12 px; cuerpo de 15–16 px; datos en Atkinson Hyperlegible Mono. Componentes: tarjeta de estado con franja superior, tarjeta de cámara con miniatura ilustrada, `role="status"`, avisos de Windows en la bandeja.

### 6.1. US-28 · Vincular esta PC

**Objetivo.** Que la PC recién instalada se vincule sin escribir nada en ella.
**Entradas.** Primer arranque; después de desvincular (US-31); cuando pasaron 90 días o más sin conexión (CA-28.7).
**Flujo.** D-28.1 Código → (D-28.2 código renovado) → D-28.4 Vinculada. Las cámaras se eligen en el celular (M-29.1); D-29.1 es el respaldo del instalador.

#### D-28.1 · Vincular esta PC

- **Bloques (dos columnas).**
  - *Izquierda:* título «Vincula esta PC con tu celular»; pasos: «1. Abre la app Te Tengo en tu celular» · «2. Ve a Ajustes › PCs y cámaras › Agregar PC» · «3. Escanea este código»; nombre de la PC: «Esta PC se llama Sala-Rosa».
  - *Derecha:* tarjeta con el QR (240 px), debajo «¿No puedes escanearlo? Escribe este código en la app:» y `.code-box` con `KQWT-MXHD` en Mono grande, la URL `tetengo.pe/vincular` y la cuenta regresiva «Vence en 9:41».
  - *Pie:* `.wait` «Esperando la aprobación en el celular…».
- **Comportamiento.** Al vencer, se pide un código nuevo sin intervención (CA-28.3): el QR y el código cambian con una transición corta y `role="status"` anuncia «Código nuevo». La PC no sabe si alguien escaneó: la espera es la misma hasta la aprobación o el rechazo.
- **Estados.**
  - *Sin internet:* sin QR; tarjeta en tinta oscura «Sin internet» · «Conecta esta PC a internet para vincularla. Reintentamos en 0:25.» · «Reintentar ahora» (mismo patrón que el estado «Sin internet» actual).
  - *Servidor no disponible:* «No pudimos conectar con Te Tengo. Reintentamos en 0:25.»
  - *Rechazada (D-28.5):* ver abajo.
  - *Re-vinculación tras 90 días:* banda ámbar arriba «Esta PC estuvo más de 90 días sin conexión. Vuelve a vincularla.»
- **Accesibilidad.** QR con `alt` «Código QR para vincular esta PC»; el código con `aria-label` letra por letra; la cuenta regresiva no mueve el foco y se anuncia solo al faltar 1 minuto.

#### D-28.4 · Vinculada

- «Esta PC quedó vinculada a la casa de Rosa Huamán» · «Aprobada por Carmen desde su celular a las 10:31.» · «Carmen elige ahora las cámaras desde su celular. Si alguna no aparece, conéctala por USB.» · enlace secundario «Elegir las cámaras aquí» (D-29.1, para el instalador).
- Sin consentimiento de monitoreo: nota ámbar «Falta el consentimiento de Rosa. Las cámaras no enviarán nada hasta que la familia lo registre en la app.»

#### D-28.5 · Vinculación rechazada

- «No se vinculó esta PC» · «Alguien eligió "No reconozco esta PC" en la app.» · «Mostrar otro código».

#### Wireframe · D-28.1

```
┌─ Te Tengo Captura ───────────────────────────────────────────────── _ □ × ┐
│                                                                           │
│  Vincula esta PC con tu celular            ┌───────────────────────────┐  │
│                                            │   ▄▄▄▄▄▄▄  ▄ ▄  ▄▄▄▄▄▄▄   │  │
│  1  Abre la app Te Tengo en tu celular     │   █ ▄▄▄ █ ▀█▄█ █ ▄▄▄ █    │  │
│  2  Ve a Ajustes › PCs y cámaras ›         │   █ ███ █ ▄▀ ▀ █ ███ █    │  │
│     Agregar PC                             │   █▄▄▄▄▄█ █ ▄ █ █▄▄▄▄▄█   │  │
│  3  Escanea este código                    │        (código QR)        │  │
│                                            │ ¿No puedes escanearlo?    │  │
│  Esta PC se llama  Sala-Rosa               │ Escribe en la app:        │  │
│                                            │  ┌─────────────────────┐  │  │
│                                            │  │    KQWT - MXHD      │  │  │
│                                            │  └─────────────────────┘  │  │
│                                            │ tetengo.pe/vincular       │  │
│                                            │ [reloj] Vence en 9:41     │  │
│                                            └───────────────────────────┘  │
│  ◌ Esperando la aprobación en el celular…                                 │
└───────────────────────────────────────────────────────────────────────────┘
```

### 6.2. US-29 · Cámaras de esta PC (respaldo del instalador)

**Reparto.** El titular elige las cámaras y su habitación **en el celular** (M-29.1). La PC hace solo lo que necesita a alguien en la casa: mostrar el código, detectar las webcams que se conectan por USB y mostrar su estado. Su «Elegir cámaras» queda como **respaldo del instalador** (por ejemplo, el equipo que instala el piloto sin el celular del titular), con las mismas reglas.
**Entradas.** Pestaña «Cámaras»; D-28.4 › «Elegir las cámaras aquí».
**Flujo.** D-29.1 Lista de webcams y estado → (respaldo) vista previa local → habitación → guardado.

#### D-29.1 · Cámaras de esta PC

- **Bloques.**
  - *Izquierda (lista):* una fila por cámara detectada, con miniatura, nombre del dispositivo y etiqueta de estado: «En uso · Sala», «Sin usar», «Desconectada» (punteado). Botón «Buscar de nuevo». Nota fija: «Las cámaras se eligen en la app Te Tengo, desde el celular de Carmen.»
  - *Derecha (respaldo, detrás de «Elegir cámaras aquí»):* vista previa grande con la etiqueta fija «La vista previa solo se ve en esta PC»; «¿En qué habitación está?» con chips (Sala, Dormitorio, Cocina, Comedor, Pasillo, Otra → campo); ayuda «Por privacidad, Te Tengo no admite cámaras en el baño.»; botones «Usar esta cámara» y, si ya está en uso, «Dejar de usar». Lo elegido aquí aparece en el celular y queda en Actividad como «Desde la PC Sala-Rosa: …».
- **Vista previa en el prototipo.** Como regla de los prototipos, se dibuja con la ilustración estilizada del ambiente, sin personas; en el producto es la imagen real, solo local.
- **Validaciones** (las mismas de M-29.1). *Nombre vacío:* «Escribe el nombre de la habitación.» *Habitación ocupada (CA-29.3):* chip deshabilitado con «Ya tiene cámara» y, si se escribe a mano, «Ya hay una cámara en la Sala (PC Sala-Rosa). Por ahora, cada habitación usa una sola cámara.»
- **Estados.**
  - *Sin cámaras (CA-29.6):* «No encontramos cámaras en esta PC» · «Conecta una webcam por USB y pulsa Buscar de nuevo.» (en el celular: M-29.1, «Pide a alguien en la casa…»).
  - *Cámara asignada desconectada (CA-29.5):* fila punteada «Desconectada · Sala» con «Revisa el cable USB»; el ambiente no pasa a otra cámara.
  - *Cámara ocupada por otro programa:* «Otro programa está usando esta cámara. Ciérralo y pulsa Buscar de nuevo.»
  - *Guardado:* toast «La cámara Webcam USB HD cuida ahora la Sala».
  - *Cambio a la vez en el celular y en la PC (CA-29.10):* queda el último cambio guardado; la PC y el celular muestran esa asignación y Actividad registra ambos cambios con su origen, quién y cuándo («Carmen eligió… desde el celular» y «Desde la PC Sala-Rosa: …»).
  - *Muchas cámaras:* a partir de la tercera cámara en uso, nota neutra: «Cada cámara usa más la PC. Si la detección se vuelve lenta, conecta algunas cámaras a otra PC.» (sin cifras).
- **Identificación.** Si se conecta otra webcam o se reinicia la PC, la asignación no cambia (CA-29.4); no se diseña ningún aviso para eso. La webcam nueva aparece «Sin usar», aquí y en el celular.

#### Wireframe · D-29.1

```
┌─ Te Tengo Captura ────────────────────────────────────────────── _ □ × ┐
│  Estado    [Cámaras]    Avanzado                                       │
│ ┌────────────────────────────┐ ┌─────────────────────────────────────┐ │
│ │ [▣] Webcam USB HD          │ │ ┌─────────────────────────────────┐ │ │
│ │     En uso · Sala          │ │ │                                 │ │ │
│ │ [▣] Logitech C920        ◀ │ │ │   (vista previa ilustrada)      │ │ │
│ │     Sin usar               │ │ │                                 │ │ │
│ │ [▢] USB2.0 PC Camera       │ │ └─────────────────────────────────┘ │ │
│ │ ┄┄  Desconectada · Pasillo │ │ Respaldo del instalador · la vista  │ │
│ │ [ Buscar de nuevo ]        │ │ previa solo se ve en esta PC        │ │
│ │ Se eligen en el celular    │ │ ¿En qué habitación está?            │ │
│ │ de Carmen.                 │ │ (Sala·Ya tiene) (Dormitorio) (Cocina│ │
│ │ Esta PC: Sala-Rosa         │ │ (Comedor) (Pasillo·Ya tiene) (Otra) │ │
│ │ Desvincular esta PC        │ │ Por privacidad, no se admiten       │ │
│ └────────────────────────────┘ │ cámaras en el baño.                 │ │
│                                │ [ Usar esta cámara ]                │ │
│                                └─────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────────┘
```

#### Estado (ventana actual) · cambios

- La tarjeta de estado resume todas las cámaras: «Te Tengo está cuidando 3 ambientes · Todo funciona bien» o «2 de 3 cámaras funcionan · Pasillo no responde».
- La tarjeta única de cámara pasa a una lista de tarjetas (una por cámara) con miniatura, ambiente, dispositivo y estado; la vista en vivo dice qué cámara está viendo el familiar: «Carmen está viendo el Dormitorio en vivo · Desde las 10:42».
- «Datos de la instalación» cambia «Configurada por el equipo del proyecto» por «Vinculada por Carmen el 03/08/2026».

### 6.3. US-31 · Desvincular esta PC

- **Entrada.** Pestaña «Cámaras» › «Esta PC: Sala-Rosa» › «Desvincular esta PC».
- **D-31.1 · Confirmación (diálogo).** «¿Desvincular esta PC?» · «Dejaremos de detectar caídas en Sala, Dormitorio y Pasillo. Esta PC borrará su acceso y la familia recibirá un aviso.» · «Desvincular» (rojo) · «Cancelar». Casilla propuesta: «Borrar también los datos guardados en esta PC (3,2 GB)» *(propuesta de diseño; no está en los criterios)*.
- **D-31.2 · Quitada desde el celular (CA-31.1 y CA-31.2).** Pantalla completa: «Esta PC se quitó de la casa de Rosa Huamán» · «Carmen la quitó desde la app a las 11:20. Ya no usa las cámaras.» · «Vincular de nuevo» (D-28.1). Con la ventana cerrada, aviso de Windows: «Te Tengo Captura · Esta PC se quitó de la casa de Rosa Huamán».

### 6.4. US-32 · Avanzado: registro en vivo y medidores

**Objetivo.** Explicar en lenguaje sencillo qué ve y decide el sistema, sin que nada salga de la PC.
**Entrada.** Pestaña «Avanzado».

#### D-32.0 · Activar el modo avanzado

- Apagado (CA-32.1): tarjeta «Modo avanzado» con interruptor y texto «Muestra, cámara por cámara, lo que detecta el programa y por qué avisa o no avisa. Sirve para revisar la instalación. Nada de esto sale de esta PC.»
- Al activar: confirmación breve «Activamos el modo avanzado. Queda anotado en la actividad.» Aparecen las pestañas «Registro en vivo» y «Medidores».
- Las pestañas «Actividad» y «Almacenamiento» se ven siempre.
- Cabecera de la pestaña: selector de cámara (segmentado: Sala · Dormitorio · Pasillo) y botones «Ver qué pasó» y «Exportar diagnóstico».

#### D-32.1 · Registro en vivo

- **Barra de herramientas.** Filtros en chips (con conteo): «Personas», «Eventos», «Imágenes descartadas», «Conexión», «Programa»; búsqueda; «Pausar» / «Seguir».
- **Líneas.** Hora en Mono (`10:41:52`), ícono por tipo, mensaje. Colores (siempre con ícono y texto): eventos de caída en `--caida`, inestable en `--inestable`, «Se levantó» en `--calma`, descartes y conexión en `--aviso`, programa en tinta neutra.
- **Ejemplos (borrador de copy — revisar).**
  - `10:41:50` · Persona detectada en la Sala
  - `10:41:51` · Bajó rápido la cadera (descenso por encima del umbral)
  - `10:41:51` · Posible caída: esperando que quede en el suelo (1,48 s)
  - `10:41:52` · Caída: quedó en el suelo. Aviso enviado a la familia
  - `10:42:22` · Caída confirmada: sigue en el suelo después de 30 s
  - `10:43:05` · Se levantó
  - `10:44:10` · Imagen descartada: no se ven los tobillos
  - `10:45:00` · Sin internet. Los avisos esperan en la cola
- **«Ver línea técnica».** Cada línea se expande y muestra el texto técnico en Mono, por ejemplo: `2026-09-23T10:41:51.482-05:00 INFO clasificador fase=INICIO_CAIDA v=0.034 theta=38.2 P=0.84 M1=1 M2=1 M3=0`, con «Copiar».
- **Estados.** *Pausado:* banda «En pausa · 12 líneas nuevas» y «Seguir». *Vacío:* «Aún no pasa nada en esta cámara». *Búsqueda sin resultados:* «No hay líneas con "tobillos"». *Cámara en pausa:* primera línea fija «Cámara en pausa hasta las 11:42».
- **Accesibilidad.** Contenedor `role="log"` con `aria-live="polite"` que anuncia solo los eventos (no cada línea); navegación por teclado línea a línea; la pausa detiene también los anuncios.

#### D-32.2 · Medidores

- **Bloques (cuadrícula de tarjetas).**
  - *Rendimiento:* «7,9 fps» (objetivo 8); si baja de 6 fps durante un minuto, ámbar: «La PC no da abasto. Prueba con menos cámaras en esta PC.» *(umbral de ejemplo)*.
  - *Persona:* «Sí, se ve a una persona» / «Sin persona en la imagen».
  - *Puntos del cuerpo:* barras con texto para nariz, hombros, caderas y tobillos (visibilidad 0 a 1; mínimo 0,5).
  - *Tres medidas frente a su umbral*, cada una con valor, umbral y Sí/No:
    - Descenso de la cadera (M1): «0,004 cuerpos/s · avisa desde 0,01»
    - Inclinación del tronco (M2): «72° · avisa por debajo de 45°»
    - Forma del cuerpo, ancho/alto (M3): «0,62 · avisa desde 1»
  - *Fase:* pasos «De pie → Posible caída → En el suelo → Caída confirmada», con la ventana de 1,48 s (barra que se vacía) y la cuenta de 30 s en el suelo.
  - *Esqueleto:* los puntos dibujados sobre fondo neutro; etiqueta «Solo se ve en esta PC».
- **Estados (CA-32.4).** Sin persona, en pausa o desconectada: tarjetas en gris sin valores, con «Sin persona en la imagen», «En pausa hasta las 11:42» o «Cámara desconectada».
- **Accesibilidad.** Cada medidor tiene su valor en texto (no solo la barra); actualización como máximo 2 veces por segundo; sin animación con `prefers-reduced-motion`.

#### Wireframe · D-32.1 y D-32.2

```
┌─ Te Tengo Captura ────────────────────────────────────────────── _ □ × ┐
│  Estado    Cámaras    [Avanzado]          [Ver qué pasó] [Exportar…]   │
│  Modo avanzado [● Sí]   Cámara: [Sala] Dormitorio  Pasillo             │
│  [Registro en vivo]  Medidores   Actividad   Almacenamiento            │
│  (Personas 42)(Eventos 3)(Descartadas 7)(Conexión 1)(Programa) [buscar]│
│                                                        [Pausar ||]     │
│  10:41:50  ● Persona detectada en la Sala                              │
│  10:41:51  ▼ Bajó rápido la cadera                                     │
│  10:41:51  ▲ Posible caída: esperando que quede en el suelo (1,48 s)   │
│  10:41:52  ▲ Caída: quedó en el suelo. Aviso enviado a la familia      │
│            └ Ver línea técnica                                         │
│  10:42:22  ▲ Caída confirmada: sigue en el suelo después de 30 s       │
│  10:43:05  ● Se levantó                                                │
│  10:44:10  ◌ Imagen descartada: no se ven los tobillos                 │
└────────────────────────────────────────────────────────────────────────┘
┌─ Medidores ────────────────────────────────────────────────────────────┐
│ ┌ Rendimiento ┐ ┌ Persona ─────┐ ┌ Puntos del cuerpo ───────────────┐  │
│ │ 7,9 fps     │ │ Sí, se ve a  │ │ Nariz    ████████░ 0,92          │  │
│ │ objetivo 8  │ │ una persona  │ │ Caderas  ██████░░░ 0,71          │  │
│ └─────────────┘ └──────────────┘ │ Tobillos ███░░░░░░ 0,38  (<0,5)  │  │
│ ┌ Descenso (M1) ┐┌ Tronco (M2) ┐┌ Ancho/alto (M3) ┐ └───────────────┘  │
│ │ 0,004  No     ││ 72°   No    ││ 0,62   No       │ ┌ Esqueleto ────┐  │
│ │ avisa ≥ 0,01  ││ avisa < 45° ││ avisa ≥ 1       │ │      o        │  │
│ └───────────────┘└─────────────┘└─────────────────┘ │     /|\       │  │
│  Fase: [De pie] → Posible caída → En el suelo →     │     / \       │  │
│        Caída confirmada   ventana 1,48 s · 30 s     │ Solo en esta PC│ │
│                                                     └───────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
```

### 6.5. US-33 · Actividad (escritorio)

- Misma lista que M-33 (por día, del más reciente al más antiguo), filtrada a esta PC por defecto, con «Ver toda la casa».
- Las filas hechas sin internet llevan la etiqueta «Pendiente de enviar» (gris, ícono de reloj) hasta sincronizarse (CA-33.3).
- Vacío: «Aún no hay actividad registrada». Sin edición ni borrado.

### 6.6. US-38 · Almacenamiento

**Objetivo.** Decidir qué se guarda en la PC, dónde, cuánto tiempo y con qué límite, sin detener la detección.

#### D-38.1 · Almacenamiento

- **Bloques (en orden).**
  1. **Uso:** barra segmentada por tipo con leyenda en texto: «3,2 GB de 50 GB» · Movimientos 1,1 GB · Video 1,9 GB · Clips 0,2 GB.
  2. **Carpeta:** ruta en Mono `C:\Users\Rosa\AppData\Local\TeTengo\Datos` · «Cambiar carpeta» (diálogo del sistema).
  3. **Por tipo** (una fila cada uno, con interruptor y plazo):
     - *Movimientos (puntos del cuerpo):* interruptor; plazo 7 días · 30 días · 90 días · 1 año · Nunca borrar. Deshabilitado sin permiso: «Requiere el permiso de Rosa para guardar movimientos. Se registra en la app Te Tengo.» (CA-35.3).
     - *Video continuo:* **apagado por defecto** (CA-38.2); al activarlo, diálogo: «El video se guarda solo en esta PC, nunca se sube a la nube. 480p, 8 imágenes por segundo, en partes de 10 minutos. Puede ocupar mucho espacio.» · «Activar» · «Cancelar». Plazo: 1 día · 7 días · 30 días · Nunca borrar.
     - *Clips de los avisos:* plazo 30 días · 90 días · 1 año · Nunca borrar.
  4. **Límite de espacio:** selector 10 GB · 25 GB · 50 GB · 100 GB · «Otro»; ayuda: «Al llegar al límite, borramos primero el video más antiguo y luego los movimientos más antiguos. La detección nunca se detiene.»
  5. **Cifrado:** fila informativa con candado: «Los datos de esta carpeta están cifrados. Solo Te Tengo Captura puede leerlos.»
  6. **En la nube** (solo lectura): «Movimientos en la nube: 30 días · lo eligió Carmen en la app».
- **Estados.**
  - *Cerca del límite (90 %):* banda ámbar «Queda poco espacio: 45,1 GB de 50 GB. Pronto borraremos el video más antiguo.»
  - *Límite alcanzado (CA-38.3):* aviso «Borramos el video del 14/09 para liberar espacio. La detección sigue funcionando.»
  - *Carpeta no disponible o disco lleno (CA-38.5):* banda ámbar «No podemos guardar en la carpeta elegida. Revisa que el disco tenga espacio o elige otra carpeta. La detección y los avisos siguen funcionando.» · «Elegir otra carpeta».
  - *Cambio de carpeta:* progreso «Moviendo 3,2 GB…» con la detección activa.

#### Wireframe · D-38.1

```
┌─ Avanzado › Almacenamiento ────────────────────────────────────────────┐
│ Uso   ███████▓▓▓▓░░░░░░░░░░░░░░░░░░░░  3,2 GB de 50 GB                 │
│       Movimientos 1,1 GB · Video 1,9 GB · Clips 0,2 GB                 │
│ Carpeta  C:\Users\Rosa\AppData\Local\TeTengo\Datos   [Cambiar carpeta] │
│ ────────────────────────────────────────────────────────────────────── │
│ Movimientos (puntos del cuerpo)   [● Sí]   Plazo [ 90 días       ▾ ]   │
│ Video continuo · solo en esta PC  [○ No]   Plazo [ 7 días        ▾ ]   │
│ Clips de los avisos                        Plazo [ Nunca borrar  ▾ ]   │
│ ────────────────────────────────────────────────────────────────────── │
│ Límite de espacio  [ 50 GB ▾ ]                                         │
│ Al llegar al límite, borramos primero el video más antiguo y luego     │
│ los movimientos. La detección nunca se detiene.                        │
│ [candado] Los datos de esta carpeta están cifrados.                    │
│ En la nube: 30 días · lo eligió Carmen en la app                       │
└────────────────────────────────────────────────────────────────────────┘
```

### 6.7. US-39 · Ver qué pasó (escritorio)

- Igual que M-39.1 y M-39.2 en una sola pantalla: selector de cámara, fecha y hora a la izquierda; lienzo y línea de tiempo a la derecha; misma franja «Esta repetición queda en el registro de accesos».
- **Diferencia (CA-39.2):** interruptor «Ver sobre el video guardado en esta PC», disponible solo si hay video continuo de ese momento; si no: deshabilitado con «No se guardó video de ese momento». Con el video activo, la franja dice «Video guardado solo en esta PC · nunca se sube».
- Fuente de datos: los movimientos de la PC (incluido «Nunca borrar»), no los de la nube.
- Estados iguales a M-39 (sin permiso, fuera del plazo, tramos sin datos).

### 6.8. US-34 · Exportar diagnóstico

- **D-34.1 · Diálogo.** «Exportar diagnóstico» · «Crea un archivo para enviarlo al equipo de soporte.» Dos listas: **Incluye:** registros del programa, versión, sistema operativo, cámaras y ambientes, umbrales. **No incluye:** contraseñas ni accesos, imágenes, video, puntos del cuerpo. Botón «Elegir dónde guardar» (diálogo de Windows con el nombre `te-tengo-diagnostico-Sala-Rosa-2026-09-23.zip`).
- **D-34.2 · Listo.** Toast «Diagnóstico guardado · 1,4 MB» · «Mostrar en la carpeta».
- **Error (CA-34.3).** «No pudimos guardar el archivo en esa carpeta. Elige otra.» Sin archivos incompletos.
- **Generando:** barra de progreso «Preparando el diagnóstico…».

---

## 7. Estados transversales

| Situación | App móvil | Te Tengo Captura |
|---|---|---|
| Titular / invitado | Invitado: solo lectura, `lockNote`, `.ro-tag`; puede ver repeticiones, actividad y enviar «¿Hubo una caída y no avisó?» | No distingue usuarios: lo hecho en la PC se registra como «Desde la PC Sala-Rosa» |
| Sin consentimiento de monitoreo | `consentLock` en PCs y cámaras; las cámaras no envían | «Falta el consentimiento de Rosa» (estado actual) |
| Sin permiso de movimientos | Opciones de puntos, repetición y nube deshabilitadas con el motivo y enlace a M-35.1 | «Movimientos» deshabilitado en Almacenamiento |
| Permiso revocado | Los movimientos de la nube se borran; aviso al terminar | Pregunta: «¿Borrar también los movimientos guardados en esta PC (1,1 GB)?» · «Borrar» · «Conservar» |
| Sin internet | Banner «Sin internet»; acciones que necesitan red deshabilitadas | La detección sigue; avisos, clips y movimientos esperan en la cola; actividad «Pendiente de enviar» |
| Código vencido | Mensaje de CA-28.3 | Código nuevo automático |
| Vista previa de una cámara | Como la vista en vivo: consentimiento, sin grabar, «Acceso registrado» al cerrar (M-29.2) | Solo en el respaldo del instalador, local: «La vista previa solo se ve en esta PC» |
| Disco lleno | — | Banda ámbar de CA-38.5 |
| Fuera del plazo | Días deshabilitados; «Hay datos desde…» | Igual |
| Cargando | Esqueletos de filas y tarjetas | Barra de progreso o indicador en la tarjeta |

## 8. Fuera de alcance y trabajo futuro

- **Varias cámaras en un mismo ambiente** con detección independiente y eventos deduplicados (opción B), y **fusión de vistas** con reconstrucción 3D a partir de varias cámaras (opción C). El modelo de datos ya admite varias cámaras por ambiente, pero la interfaz impide asignarlas (CA-29.3).
- **Varias personas** en la imagen o en la vivienda: no se distingue a Rosa de otras personas (no hay reconocimiento facial, por alcance del Charter).
- **Renombrar la PC** desde la app y **mover una cámara** de una PC a otra sin desvincular.
- **Cámaras IP o de red**: solo webcams USB.
- **Video en la nube**: nunca, ni continuo ni de repetición.
- **Versión web** del producto.
- Pantallas de `pantallas-trabajo-futuro.html` con el código `TTG-XXXX` generado en la app: superadas por este flujo; conviene archivarlas o marcarlas como reemplazadas cuando se diseñe US-28.

## 9. Trazabilidad

| Pantalla | Historia | Criterios |
|---|---|---|
| M-28.1 a M-28.6 · D-28.1 a D-28.5 | US-28 | CA-28.1 a CA-28.7 |
| M-29.1 a M-29.3 · D-29.1 (respaldo del instalador) · Estado (cambios) · Detalle de cámara (habitación, dejar de usar) | US-29 | CA-29.1 a CA-29.10 |
| M-29.2 (vista previa) · Registro de accesos | US-24 | CA-24.1, CA-24.2 |
| M-30.1 · M-30.2 · Inicio (Cámaras) | US-30 | CA-30.1 a CA-30.3 |
| M-31.1 · M-31.2 · D-31.1 · D-31.2 | US-31 | CA-31.1 a CA-31.5 |
| D-32.0 · D-32.1 · D-32.2 | US-32 | CA-32.1 a CA-32.4 |
| M-33 · D-33 | US-33 | CA-33.1 a CA-33.4 |
| D-34.1 · D-34.2 | US-34 | CA-34.1 a CA-34.3 |
| M-35.1 a M-35.3 · Estados transversales | US-35 | CA-35.1 a CA-35.4 |
| Clip con «Puntos del cuerpo» | US-36 | CA-36.1 a CA-36.3 |
| M-37.1 | US-37 | CA-37.1, CA-37.3 y CA-37.4 (CA-37.2 no tiene pantalla) |
| D-38.1 | US-38 | CA-38.1 a CA-38.5 |
| M-39.1 · M-39.2 · Registro de accesos · Ver qué pasó (escritorio) | US-39 | CA-39.1 a CA-39.5 |
| M-40.1 · M-40.2 | US-40 | CA-40.4 (CA-40.1 a CA-40.3 son del informe de evaluación, sin pantalla) |

Las pantallas móviles ya están diseñadas: la tabla de cada pantalla de la galería (`app-movil/pantallas.html`, de la 120 a la 283, más las 22 a 25 y 76 a 77 reemplazadas; «Elegir las cámaras desde el celular» es de la 250 a la 283) con sus historias y criterios está en [`app-movil/PRODUCT.md`](app-movil/PRODUCT.md#trazabilidad-de-las-pantallas-nuevas).

Al terminar las pantallas, actualizar `app-movil/PRODUCT.md` y `app-escritorio/PRODUCT.md` (hoy dicen «27 historias, 85 criterios», «sin vinculación» y «una sola cámara») si el cambio se aprueba.
