# Especificación de la clasificación cinemática

Este documento explica **qué calcula** el Servicio de clasificación cinemática, **por qué** y **de dónde sale** cada fórmula y cada umbral. El código no cita autores: cada función nombra la regla (R1–R8) o la adaptación (A1–A5) que implementa, y aquí se detalla con sus fuentes.

Código: [`src/detection_worker/clasificacion/`](../src/detection_worker/clasificacion) · Pruebas: [`tests/clasificacion/`](../tests/clasificacion)

**Cómo leer el origen de cada valor**

| Marca | Significa |
|---|---|
| **Fuente** | Lo dice una publicación. Se indican la sección, la ecuación o la figura. |
| **Backlog** | Viene de un criterio de aceptación del product backlog del proyecto. |
| **Adaptación** | Decisión propia para llevar el método a MediaPipe y a una sola cámara. **Debe validarse.** |
| **Propuesta** | Regla propia que combina fuentes; todavía **no tiene validación**. |

---

## 1. Datos de entrada

**MediaPipe Pose Landmarker** entrega, por cada persona, 33 landmarks:
- `x` e `y` van de 0 a 1, divididas entre el ancho y el alto de la imagen, e `y` crece hacia abajo.
- `visibility` es la probabilidad de que el punto esté visible en la imagen.
- También entrega *world landmarks* en metros, pero **con el centro de la cadera como origen** (Google, s.f.-b).

El método de referencia (Chen et al., 2020) usa un esqueleto de **14 puntos**, s₀ a s₁₃, numerados en su Figura 4. Los que se usan aquí son:

| Punto del método de referencia | Landmark de MediaPipe (Google, s.f.-a) | Uso |
|---|---|---|
| s₀ cabeza | 0 nariz (**Adaptación A2**) | Extremo superior de la línea central |
| s₈ cadera derecha · s₁₁ cadera izquierda | 24 · 23 | Centro de la cadera |
| s₁₀ tobillo derecho · s₁₃ tobillo izquierdo | 28 · 27 | Extremo inferior de la línea central |

### Adaptaciones de la entrada

| ID | Adaptación | Motivo |
|---|---|---|
| **A1** | Todas las coordenadas se pasan a píxeles (`x · ancho`, `y · alto`) antes de calcular. | Con una imagen de 640 × 480, las coordenadas normalizadas deforman los ángulos y la razón ancho/alto. |
| **A2** | La nariz reemplaza a la «cabeza». | MediaPipe no tiene un punto cabeza; la nariz es el punto central de la cabeza más estable. |
| **A3** | La velocidad tiene signo (solo cuenta la bajada), se divide entre la mediana del largo de la línea central de los últimos 2 s y es la mayor bajada por segundo frente a cualquier muestra entre 0,25 y 1 s atrás. | Una cámara 2D no mide metros, y las *world landmarks* no sirven porque su origen es la propia cadera. La ventana de 1 s tolera los fotogramas que MediaPipe pierde durante la caída y cubre su duración (583 ± 255 ms hasta el impacto de la pelvis; Choi et al., 2015, como se citó en Traverso et al., 2024). Ver la validación. |
| **A4** | Δt es la diferencia real entre las marcas de tiempo de las muestras. | El agente envía de 5 a 10 fps, no una tasa fija. |
| **A6** | La velocidad (R1) y el estado «erguido» (R5 y R7) solo se calculan con la nariz, las caderas y los tobillos visibles (≥ 0,5). M2 y M3 sí usan poses con puntos poco visibles. | Con puntos poco visibles, MediaPipe estima posiciones poco fiables: la cadera «salta» y genera velocidades imposibles, y una persona tendida puede parecer de pie. Es preferible una falsa alarma a perder una caída, pero no una falsa recuperación. |
| **A7** | Si la cabeza queda más abajo que los pies en la imagen, se cumplen M2 y M3 y la persona no está erguida. | Con la cámara elevada, al caer hacia la cámara el cuerpo se ve acortado: el ángulo con valor absoluto sale «casi vertical» y la razón no supera 1. De pie, la cabeza nunca está bajo los pies. Ver la validación. |
| **A8** | La recuperación exige verse erguido durante 1 s seguido. | MediaPipe a veces estima «de pie» a una persona tendida durante un fotograma. 1 s es el menor valor que eliminó las recuperaciones falsas en las 30 caídas de URFD. |
| **A5** | Solo entran al rectángulo del cuerpo los landmarks con visibilidad ≥ 0,5. | Los puntos ocultos «inventados» por el modelo agrandan el rectángulo. Se toma 0,5 por ser el valor por defecto de los umbrales de confianza de MediaPipe (Google, s.f.-a). |

---

## 2. Condiciones por fotograma

### R1. Velocidad de descenso del centro de la cadera → condición M1

**Qué mide.** Qué tan rápido baja el centro de la cadera, que el método de referencia usa como representante del centro de gravedad. En una caída repentina, el centro de gravedad cambia bruscamente en la vertical.

**Fuente.** Chen et al. (2020), sección 3.2, ecuaciones 1 a 3:

```
ȳ(t) = ( y_t,8 + y_t,11 ) / 2               centro de la cadera
Δt   = t₂ − t₁                               se evalúa cada 5 fotogramas, 0,25 s
v    = | ȳ(t₂) − ȳ(t₁) | / Δt
M1   = 1  si  v ≥ v̄
```

**El umbral publicado es contradictorio:** v̄ = 0,009 m/s en la sección 3.2, y 0,09 m/s en la sección 4.2 y la Figura 9.

**Implementación (A3, A4, A6).**
```
v(t) = máx  [ ȳ(t) − ȳ(tᵢ) ] / (t − tᵢ) / L̃        para cada muestra tᵢ ∈ [t − 1 s, t − 0,25 s]
L̃    = mediana del largo de la línea central en los últimos 2 s
```
- **Con signo:** es positiva cuando la cadera baja; levantarse rápido no cuenta.
- **Unidad:** cuerpos por segundo.
- **Solo fotogramas fiables:** se usan los fotogramas con los puntos clave visibles.
- **Umbral calibrado: 0,01 cuerpos/s** ([validacion.md](validacion.md)). Es casi «la cadera bajó algo». A 8 fps y en 2D, la velocidad aporta poco por sí sola, porque MediaPipe pierde parte de los fotogramas del descenso.

### R2. Ángulo de la línea central con el suelo → condición M2

**Qué mide.** Cuánto se inclinó el cuerpo. Al caer, el cuerpo se inclina cada vez más y pierde la vertical.

**Fuente.** Chen et al. (2020), sección 3.3, ecuación 4 y Figura 6:

```
s̄(t) = ( s₁₀ + s₁₃ ) / 2                    punto medio de los tobillos
L    = segmento de s₀ (cabeza) a s̄
θₜ   = arctan | ( y_t,0 − ȳₜ ) / ( x_t,0 − x̄ₜ ) |
M2   = 1  si  θ < θ₀ ,  θ₀ = 45°
```

**Implementación.** `θ = atan2(|Δy|, |Δx|)` da el mismo resultado sin dividir entre cero cuando la persona está totalmente vertical. Además, M2 se cumple si la cabeza queda bajo los pies (A7).

**Nota sobre la fuente.** El texto de la sección 3.3 dice «punto medio de s₁₂ y s₁₃», pero la ecuación y la Figura 6 usan s₁₀ y s₁₃, los dos tobillos. Se sigue la ecuación, porque s₁₂ es una rodilla.

### R3. Razón ancho/alto del rectángulo del cuerpo → condición M3

**Qué mide.** La forma final del cuerpo: de pie es angosto y alto; tendido es ancho y bajo. La razón no cambia con la distancia a la cámara, a diferencia del ancho o el alto por separado.

**Fuente.** Chen et al. (2020), sección 3.4, ecuación 5 y Figura 7:

```
P  = Ancho / Alto
M3 = 1  si  P ≥ T ,  T = 1         al caminar P < 1; al caer P > 1
```

**Implementación (A1, A5).** El rectángulo se arma con los landmarks visibles, en píxeles. Si la altura es 0, P = ∞. M3 también se cumple si la cabeza queda bajo los pies (A7).

---

## 3. Reglas de eventos

```
                 M1 y M2                          M3 dentro de la ventana
   NORMAL ─────────────────► INICIO_CAÍDA ─────────────────────────────► EN_EL_SUELO
     ▲  ▲                      │       │                                   │      │
     │  └─ vence la ventana ───┘       │ vuelve a estar erguido             │      │ 30 s
     │     (sin evento)                ▼                                   │      ▼
     │                    R7 movimiento_inestable                          │  R6 caida_confirmada
     └──────────── vuelve a estar erguido: R5 recuperacion ◄───────────────┘
                                     (al entrar a EN_EL_SUELO: R4 caida)
```

«Erguido» significa θ > 45° y P < 1, la condición de R5.

| ID | Evento | Regla | Origen |
|---|---|---|---|
| **R4** | `caida` | M1 y M2, y luego M3 dentro de la ventana de reacción (1,48 s) | **Fuente:** Chen et al. (2020), Figura 2, que evalúa M1 → M2 → M3 en secuencia. **Adaptación:** como no ocurren en el mismo fotograma, se espera M3 dentro de la ventana. |
| **R5** | `recuperacion` | Estando en el suelo, erguido (θ > 45°, P < 1, cabeza sobre los pies y puntos visibles) durante 1 s | **Fuente:** Chen et al. (2020), sección 3.5 y Figura 12: levantarse es el proceso inverso de la caída, y se reconoce cuando el ángulo vuelve a superar 45° y la razón queda bajo 1 «durante un periodo». El artículo no da su duración; el valor de 1 s es la adaptación A8, calibrada. |
| **R6** | `caida_confirmada` | Sigue en `EN_EL_SUELO` 30 s. Si no se ve a la persona, el tiempo sigue contando. | **Backlog:** US-13, «Confirmación por permanencia en el suelo». |
| **R7** | `movimiento_inestable` | M1 y M2 sin llegar a M3, y la persona vuelve a estar erguida dentro de la ventana | **Propuesta** (ver abajo). |
| **R8** | `deteccion_no_confiable` | 300 s seguidos sin una pose válida. Se avisa una vez, hasta volver a ver a la persona. | **Backlog:** US-15, «Condiciones de captura». |

### Ventana de reacción: 1,48 s
Gutiérrez et al. (2023) modelan el cuerpo como un péndulo invertido. Con la altura del centro de masa de adultos mayores (0,974 m en hombres y 0,930 m en mujeres), calculan que una caída sin reacción tarda **entre 1,0 y 1,48 s**. Se usa el límite superior como tiempo máximo entre el inicio de la caída y la postura horizontal.

### Por qué R7 exige M1 y M2 a la vez (propuesta)
En los resultados de Chen et al. (2020), sección 4.2:
- **Figura 9:** solo caer y agacharse superan el umbral de velocidad.
- **Figura 10:** solo caer e inclinarse bajan de 45°.
- **Figura 11:** solo la caída supera la razón 1.

Por eso, exigir M1 **y** M2 descarta agacharse (solo M1) e inclinarse (solo M2). Caminar y sentarse no cumplen ninguna. Si después no llega M3 y la persona vuelve a estar erguida, el sistema lo trata como una pérdida de equilibrio recuperada.

**Límite:** no detecta un balanceo leve de pie ni un apoyo brusco sin inclinarse. La búsqueda de fuentes para esos casos está en curso.

### Validación con datasets
Las adaptaciones A3, A6, A7 y A8 y el umbral de velocidad salieron de validar con URFD y CAUCAFall. Resultado en condiciones de producción (8 fps, JPEG, dejando un grupo fuera): **sensibilidad 81,2 %, especificidad 81,1 %, exactitud 81,2 %** y ninguna recuperación falsa. Detalle, protocolo y límites en [validacion.md](validacion.md).

---

## 4. Tabla de umbrales

| Variable (`TT_CLASIFICACION__…`) | Valor | Regla | Origen |
|---|---|---|---|
| `VELOCIDAD_DESCENSO_MIN` | 0,01 (en `.env`; el código no trae valor por defecto) | R1 | Calibrado con URFD y CAUCAFall ([validacion.md](validacion.md)) |
| `INTERVALO_VELOCIDAD_S` | 0,25 s | R1 | Chen et al. (2020), secc. 3.2 |
| `VENTANA_VELOCIDAD_S` | 1 s | R1 | Adaptación A3 (duración del descenso: Choi et al., 2015, en Traverso et al., 2024) |
| `PERSISTENCIA_ERGUIDO_S` | 1 s | R5 | Adaptación A8, calibrado con URFD |
| `ANGULO_LINEA_CENTRAL_MAX_GRADOS` | 45° | R2, R5 | Chen et al. (2020), secc. 3.3 |
| `RAZON_ANCHO_ALTO_MIN` | 1 | R3, R5 | Chen et al. (2020), secc. 3.4 |
| `VENTANA_REACCION_S` | 1,48 s | R4, R7 | Gutiérrez et al. (2023) |
| `CONFIRMACION_SUELO_S` | 30 s | R6 | Backlog, US-13 |
| `SIN_DETECCION_CONFIABLE_S` | 300 s | R8 | Backlog, US-15 |
| `VISIBILIDAD_MIN` | 0,5 | A5 | Valor por defecto de MediaPipe (Google, s.f.-a); se calibra |

---

## 5. Evidencia y limitaciones del método de referencia

| Aspecto | Lo que reporta Chen et al. (2020) | Implicancia para Te Tengo |
|---|---|---|
| Validación | 10 voluntarios (163–183 cm), 100 acciones en laboratorio: 60 de caída y 40 de no caída (secc. 4.1, Tablas 3 y 4) | No son adultos mayores; hay que validar con datasets y grabaciones propias |
| Resultados | Sensibilidad 98,3 %, especificidad 95 % y exactitud 97 % (Tabla 6) | Son la meta de comparación, no un resultado garantizado |
| Errores | Dos «inclinarse» se confundieron con caída (Tabla 5). Los autores lo atribuyen a puntos faltantes, umbrales no óptimos y caídas simuladas con autoprotección (secc. 4.2) | Calibrar los umbrales; R7 reduce la confusión con inclinarse |
| Vista | Solo se reconoció la acción vista de costado (trabajo futuro b) | Probar caídas hacia la cámara, alejándose y en diagonal |
| Oclusión | No resuelta (trabajo futuro a) | R6 sigue contando aunque no se vea a la persona; evaluar oclusiones |

---

## 6. Cómo se prueba cada regla

| Regla | Prueba |
|---|---|
| R1–R3 | `tests/clasificacion/test_parametros.py` |
| R4–R8 | `tests/clasificacion/test_estados.py`: caída, confirmación, recuperación, tambaleo recuperado, tambaleo que termina en caída, agacharse, inclinarse, marcha y 5 min sin persona |

---

## Referencias

Chen, W., Jiang, Z., Guo, H., & Ni, X. (2020). Fall detection based on key points of human-skeleton using OpenPose. *Symmetry, 12*(5), 744. https://doi.org/10.3390/sym12050744

Google. (s.f.-a). *Pose landmark detection guide*. Google AI Edge. https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker

Google. (s.f.-b). *Pose landmark detection guide for Python*. Google AI Edge. https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker/python

Traverso, A., Bayram, A., Rossettini, G., Chiappinotto, S., Galazzi, A., & Palese, A. (2024). Investigating the biomechanics of falls in older adults in long-term care using a video camera: A scoping review. *BMC Geriatrics, 24*, 810. https://doi.org/10.1186/s12877-024-05395-2

Gutiérrez, J., Martin, S., & Rodriguez, V. (2023). Human stability assessment and fall detection based on dynamic descriptors. *IET Image Processing, 17*(11), 3177–3195. https://doi.org/10.1049/ipr2.12847

Gutierrez Soto, J. O., & Riva Rodriguez, E. A. (2026). *Product backlog del sistema basado en estimación de pose para la detección de caídas* [Documento interno del proyecto]. Universidad Peruana de Ciencias Aplicadas.
