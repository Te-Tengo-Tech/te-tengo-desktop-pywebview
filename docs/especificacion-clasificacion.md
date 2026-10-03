# Especificación de la clasificación cinemática

Este documento describe qué calcula el **Servicio de clasificación cinemática** y de dónde sale cada fórmula y cada umbral. Cada valor se marca con su origen:

- **[Chen]**: Chen et al. (2020), el método elegido en el benchmarking IB3.
- **[Gutiérrez]**: Gutiérrez et al. (2023), estudio de la revisión sistemática (P3).
- **[Backlog]**: criterios de aceptación del product backlog.
- **[Adaptación]**: decisión propia para pasar el método a MediaPipe. Debe validarse.

Código: [`src/detection_worker/clasificacion/`](../src/detection_worker/clasificacion).

## 1. Puntos del cuerpo

Chen et al. usan un esqueleto de 14 puntos (s₀ a s₁₃, su Figura 4). MediaPipe entrega 33 landmarks, con `x` e `y` normalizados entre 0 y 1 por el ancho y el alto de la imagen, e `y` creciendo hacia abajo (Google, s.f.).

| Chen et al. (2020) | MediaPipe | Uso |
|---|---|---|
| s₀ cabeza | 0 nariz **[Adaptación]**: MediaPipe no tiene un punto «cabeza» | Extremo superior de la línea central |
| s₈ cadera derecha, s₁₁ cadera izquierda | 24, 23 | Centro de la cadera |
| s₁₀ tobillo derecho, s₁₃ tobillo izquierdo | 28, 27 | Extremo inferior de la línea central |

**[Adaptación]** Todas las coordenadas se pasan a píxeles (`x · ancho`, `y · alto`) antes de calcular. Si no se hace, las razones y los ángulos salen deformados cuando la imagen no es cuadrada (480p = 640 × 480).

## 2. Parámetros

### 2.1. Velocidad de descenso del centro de la cadera: condición M₁ [Chen, secc. 3.2, ec. 1–3]

```
ȳ(t)  = ( y_t,8 + y_t,11 ) / 2
Δt    = t₂ − t₁                       (Chen: cada 5 fotogramas, 0,25 s)
v     = | ȳ(t₂) − ȳ(t₁) | / Δt
M₁    = 1  si  v ≥ v̄
```

- **El umbral del artículo es contradictorio:** dice 0,009 m/s en la sección 3.2 y 0,09 m/s en la sección 4.2 y la Figura 9.
- **[Adaptación]** Una sola cámara 2D no mide metros. Las *world landmarks* de MediaPipe sí están en metros, pero **su origen es el centro de la cadera** (Google, s.f.), así que la cadera nunca «baja» en ellas.
- **[Adaptación]** Por eso la velocidad se divide entre la longitud de la línea central del fotograma anterior: `v = |Δȳ| / Δt / L(t₁)`. La unidad queda en *longitudes de línea central por segundo* y no depende de la distancia a la cámara.
- **[Adaptación]** Δt es la diferencia real entre las marcas de tiempo de las muestras, no un número fijo de fotogramas, porque el agente envía de 5 a 10 fps.
- **El umbral `velocidad_descenso_min` no tiene valor por defecto: se calibra con pruebas.**
- Como en el artículo, se usa el **valor absoluto**.

### 2.2. Ángulo de la línea central con el suelo: condición M₂ [Chen, secc. 3.3, ec. 4]

```
s̄(t)  = ( s₁₀ + s₁₃ ) / 2                       punto medio de los tobillos
L     = recta de s₀ (cabeza) a s̄
θₜ    = arctan | ( y_t,0 − ȳₜ ) / ( x_t,0 − x̄ₜ ) |
M₂    = 1  si  θ < θ₀ ,  θ₀ = 45°
```

- **[Adaptación]** Se calcula con `atan2(|Δy|, |Δx|)`, que da el mismo valor y no divide entre cero cuando la persona está totalmente vertical.
- **Nota:** el texto de la sección 3.3 del artículo dice «punto medio de s₁₂ y s₁₃», pero la ecuación y la Figura 6 usan s₁₀ y s₁₃ (los dos tobillos). Se sigue la ecuación, porque s₁₂ es una rodilla.

### 2.3. Razón ancho/alto del rectángulo del cuerpo: condición M₃ [Chen, secc. 3.4, ec. 5]

```
P   = Ancho / Alto
M₃  = 1  si  P ≥ T ,  T = 1       (caminando P < 1; al caer P > 1)
```

**[Adaptación]** El rectángulo se arma con los landmarks cuya visibilidad es ≥ `visibilidad_min` (0,5, el mismo valor que los umbrales por defecto de MediaPipe). Si la altura es 0, P = ∞.

## 3. Estados y eventos

```
                    M₁ y M₂                         M₃ dentro de la ventana de reacción
   NORMAL ──────────────────────► INICIO_CAÍDA ─────────────────────────────────► EN_EL_SUELO
     ▲  ▲                            │      │                                        │   │
     │  └── vence la ventana ────────┘      │ erguido (θ > 45° y P < 1)              │   │ 30 s
     │      (sin evento)                    ▼                                        │   ▼
     │                          evento MOVIMIENTO_INESTABLE                          │ evento CAIDA_CONFIRMADA
     └──────────────────── erguido (θ > 45° y P < 1): evento RECUPERACION ◄──────────┘
```

| Evento | Regla | Origen |
|---|---|---|
| `caida` | M₁ y M₂, y luego M₃ dentro de `ventana_reaccion_s` | **[Chen]** Figura 2. **[Adaptación]**: las tres condiciones no ocurren en el mismo instante, así que se espera M₃ dentro de la ventana. |
| `caida_confirmada` | Sigue en `EN_EL_SUELO` durante 30 s. Si no se ve a la persona, el tiempo sigue contando. | **[Backlog]** US-13 |
| `recuperacion` | Después de una caída, θ > 45° y P < 1 | **[Chen]** secc. 3.5 (regla inversa). El artículo no fija cuánto debe durar; aquí basta un fotograma. |
| `movimiento_inestable` | M₁ y M₂ sin llegar a M₃, y la persona vuelve a estar erguida dentro de la ventana | **[Adaptación] PROPUESTA pendiente de validación.** Exigir M₁ y M₂ a la vez excluye agacharse (solo M₁) e inclinarse (solo M₂), según las Figuras 9 y 10 de Chen. |
| `deteccion_no_confiable` | 300 s seguidos sin una pose válida; se avisa una vez hasta volver a ver a la persona | **[Backlog]** US-15 |

`ventana_reaccion_s = 1,48 s` es el límite superior del tiempo de caída de 1,0 a 1,48 s que calculan **[Gutiérrez]** con el modelo del péndulo invertido para adultos mayores.

## 4. Limitaciones conocidas

1. **El método se probó solo con vista lateral.** Chen et al. lo declaran en su trabajo futuro (b). Las caídas hacia la cámara o alejándose de ella pueden no cumplir M₂ y M₃, así que la validación debe incluir caídas en varias direcciones.
2. **La oclusión parcial no está resuelta.** Chen et al. lo declaran en su trabajo futuro (a).
3. **Los datos de validación de Chen et al. son de 10 voluntarios adultos** (163–183 cm) en un laboratorio, no de adultos mayores.
4. **El movimiento inestable solo cubre pérdidas de equilibrio con descenso e inclinación.** Un balanceo leve de pie no se detecta. Se está ampliando la búsqueda de fuentes para este caso.

## Referencias

Chen, W., Jiang, Z., Guo, H., & Ni, X. (2020). Fall detection based on key points of human-skeleton using OpenPose. *Symmetry, 12*(5), 744. https://doi.org/10.3390/sym12050744

Google. (s.f.). *Pose landmark detection guide for Python*. Google AI Edge. https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker/python

Gutiérrez, J., Martin, S., & Rodriguez, V. (2023). Human stability assessment and fall detection based on dynamic descriptors. *IET Image Processing, 17*(11), 3177–3195. https://doi.org/10.1049/ipr2.12847
