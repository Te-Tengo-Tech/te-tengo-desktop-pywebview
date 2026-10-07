# Validación del clasificador con datasets públicos

Este documento reporta cómo se validó el Servicio de clasificación cinemática con los dos datasets públicos que nombra el project charter (URFD y CAUCAFall), qué se cambió a partir de los resultados y qué límites quedan. Es la base técnica del indicador OE4-I1 («exactitud, sensibilidad y especificidad en conjuntos de datos públicos»).

Se reproduce con:

```bash
make datasets   # descarga URFD y CAUCAFall en datos/ (unos 220 MB)
make validar    # extrae poses y genera resultados/reporte.md
```

## 1. Datos

| Dataset | Videos | Cámara | Uso |
|---|---|---|---|
| **URFD** (Kwolek y Kepski, 2014) | 30 caídas y 40 actividades diarias, de las cuales **16 terminan con la persona acostada en el piso a propósito**, según las etiquetas por fotograma del dataset | Kinect paralela al piso, a la altura del cuerpo; se usa la mitad RGB del MP4 (320 × 240) | CC BY-NC-SA 4.0 |
| **CAUCAFall** (Eraso Guerrero et al., 2022) | 10 personas × (5 caídas: adelante, atrás, izquierda, derecha y desde sentado + 5 actividades: caminar, saltar, recoger un objeto, sentarse y arrodillarse) = 100 videos | Cámara de vigilancia **elevada en una esquina** de una vivienda (720 × 480), con oclusiones y cambios de luz | CC BY 4.0 |

Ninguno incluye adultos mayores ni caídas reales; esta limitación está declarada en el charter (riesgo 9).

## 2. Protocolo

1. **Mismo procesamiento que en producción.** Cada video se baja a 480p y a 8 fps (también se probó con 6 y 10 fps). Se comprime en JPEG de calidad 80, como hace el agente, y se pasa por MediaPipe Pose Landmarker *lite* en modo VIDEO. Las poses se guardan una vez y luego se reproducen en **el mismo `ClasificadorCinematico` del worker**.
2. **Criterio por video.** Un video de caída es un verdadero positivo si el clasificador emite al menos un evento `caida`. Un video de actividad diaria es un falso positivo si emite alguno.
3. **Métricas.** Sensibilidad = VP/(VP+FN), especificidad = VN/(VN+FP) y exactitud = (VP+VN)/total, las mismas definiciones de Chen et al. (2020, ec. 6–8) y del charter.
4. **Calibración.** El único umbral calibrado es la velocidad mínima de bajada (R1). Se prueban 100 valores (0,01–1,0) y se elige el de mayor **índice de Youden** (J = sensibilidad + especificidad − 1; Youden, 1950). El ángulo (45°) y la razón (1) se dejan en los valores publicados: ajustarlos no mejoró la validación entre datasets.
5. **Estimación honesta del desempeño:**
   - **Dejando un grupo fuera.** Hay 11 grupos: cada sujeto de CAUCAFall y URFD completo, porque URFD no publica el sujeto de cada video. Cada grupo se evalúa con el umbral calibrado **sin** sus videos.
   - **Entre datasets.** Se calibra con uno y se mide en el otro.

## 3. Resultados

### 3.1. Desempeño principal: 8 fps, JPEG, dejando un grupo fuera

| Grupo | Caídas | No caídas | VP | FN | VN | FP | Sensibilidad | Especificidad | Exactitud |
|---|---|---|---|---|---|---|---|---|---|
| **Total** | 80 | 90 | 65 | 15 | 73 | 17 | **81,2 %** | **81,1 %** | **81,2 %** |
| URFD | 30 | 40 | 23 | 7 | 31 | 9 | 76,7 % | 77,5 % | 77,1 % |
| CAUCAFall | 50 | 50 | 42 | 8 | 42 | 8 | 84,0 % | 84,0 % | 84,0 % |

**Por actividad** (las cifras de la tabla anterior agregadas por tipo):

| Actividad | Resultado |
|---|---|
| CAUCAFall · caída hacia atrás | 10/10 detectadas |
| CAUCAFall · caída a la izquierda | 9/10 |
| CAUCAFall · caída hacia adelante | 8/10 |
| CAUCAFall · caída a la derecha | 8/10 |
| CAUCAFall · caída desde sentado | 7/10 |
| CAUCAFall · saltar | 0/10 falsas alarmas |
| CAUCAFall · caminar · sentarse | 1/10 falsa alarma cada una |
| CAUCAFall · arrodillarse · recoger un objeto | 3/10 falsas alarmas cada una |
| URFD · caídas | 23/30 detectadas |
| URFD · actividades diarias | 9/40 falsas alarmas; **6 de ellas al acostarse a propósito en el piso** |

**Otros eventos:**
- **0 recuperaciones falsas** en las 30 caídas de URFD, en las que nadie se levanta.
- **2 de 90** actividades diarias generaron un `movimiento_inestable`.

### 3.2. Robustez a la tasa de fotogramas (dejando un grupo fuera)

El agente envía entre 5 y 10 fps, según la arquitectura.

| fps | Sensibilidad | Especificidad | Exactitud | Recuperaciones falsas |
|---|---|---|---|---|
| 6 | 76,2 % | 83,3 % | 80,0 % | 0/30 |
| **8** | **81,2 %** | **81,1 %** | **81,2 %** | 0/30 |
| 10 | 81,2 % | 84,4 % | 82,9 % | 0/30 |

### 3.3. Validación entre datasets (8 fps)

| Calibración → prueba | Umbral | Sensibilidad | Especificidad | Exactitud |
|---|---|---|---|---|
| URFD → CAUCAFall | 0,45 | 28,0 % | 94,0 % | 61,0 % |
| CAUCAFall → URFD | 0,01 | 76,7 % | 77,5 % | 77,1 % |

**Un umbral calibrado con una cámara a la altura del cuerpo (URFD) no sirve para una cámara elevada (CAUCAFall).** Desde arriba, la bajada de la cadera se ve más corta en la imagen. El umbral debe calibrarse con una cámara ubicada como en la vivienda: por eso se usa el de CAUCAFall y el conjunto completo (0,01).

### 3.4. Comprobación del servicio en vivo
Se enviaron 24 videos (12 de URFD y 12 de CAUCAFall) al worker levantado, usando el agente simulado por WebSocket. Los eventos de caída coincidieron con la evaluación sin conexión en **24 de 24**.

## 4. Cambios hechos a partir de la validación

Las cifras de esta sección están **calibradas con todos los videos**, así que son optimistas y solo sirven para comparar las etapas entre sí.

| Etapa | Sensibilidad | Especificidad | Qué se cambió y por qué |
|---|---|---|---|
| Método de referencia adaptado (modo IMAGE) | 80,0 % | 65,6 % | Punto de partida. MediaPipe perdía a la persona en el 43 % de los fotogramas de caídas de CAUCAFall. |
| + MediaPipe en modo VIDEO | 80,0 % | 68,9 % | El seguimiento entre fotogramas subió la cobertura de CAUCAFall-caídas del 57 % al 82 %. El modelo *full* no mejoró frente al *lite* (ADR 0006). |
| + velocidad con signo, ventana de 1 s y solo con puntos visibles (A3, A6); cabeza bajo los pies (A7); 0,5 s erguido para la recuperación (A8) | 83,8 % | 82,2 % | **Velocidad:** con poses dudosas, en URFD, «acostarse a propósito» daba velocidades **mayores** que las caídas (mediana 1,78 frente a 1,01 cuerpos/s), lo que es físicamente imposible; con puntos visibles se separan (mediana 0 frente a 0,88). La ventana de 1 s cubre la duración del descenso de una caída real de un adulto mayor (583 ± 255 ms hasta el impacto de la pelvis; Choi et al., 2015, como se citó en Traverso et al., 2024). **Cabeza bajo los pies:** en las caídas hacia adelante con cámara elevada, el ángulo y la razón no cambian (solo 3/10 cumplían M2 y M3), pero la cabeza queda por debajo de los pies en la imagen; con esta señal se detectaron 7/10. **Recuperación:** 0,5 s erguido redujo las recuperaciones falsas de 2 a 0 de 30. |
| + JPEG como en producción y 1 s erguido (configuración final) | 81,2 % | 81,1 % | Con JPEG cambia qué fotogramas detecta MediaPipe, así que la validación debe reproducirlo; el desempeño baja un poco, pero es el realista. Con JPEG, 0,5 s erguido dejaba 1 recuperación falsa de 30; con 1 s, ninguna. |

**Probado y descartado:** exigir que la postura horizontal se mantenga entre 0,25 y 1 s antes de declarar la caída. Bajó la sensibilidad al 61–70 %, porque MediaPipe pierde a la persona tendida.

**Sobre el umbral de velocidad:** el valor calibrado (0,01 cuerpos/s) es casi «la cadera bajó algo». En estos datasets, a 8 fps y en 2D, la velocidad aporta poco por sí sola: las caídas son tan rápidas que MediaPipe pierde parte de los fotogramas del descenso, justo los que tendrían la velocidad más alta. El trabajo de distinguir lo hacen sobre todo el ángulo, la razón y la cabeza bajo los pies.

## 5. Límites conocidos

1. **Acostarse a propósito en el piso** se confunde con una caída en 6 de 16 casos de URFD. En una vivienda, eso equivale a una falsa alarma cuando el adulto mayor se tiende en el suelo por voluntad propia.
2. **Recoger un objeto y arrodillarse** generan falsas alarmas en 3 de cada 10 casos con cámara elevada.
3. **La calibración depende de la ubicación de la cámara** (sección 3.3). Debe repetirse con las grabaciones del piloto, tal como indica el charter (riesgos 2, 3 y 6).
4. **No hay adultos mayores ni caídas reales** en los datos (riesgo 9 del charter). La tasa de falsas alarmas real se medirá en la vivienda (OE4-I2).
5. **La validación es por video,** no por instante. No mide la latencia de la alerta, cuyo requisito es menos de 10 s; el clasificador emite la caída en cuanto se cumple M3.

## Referencias

Chen, W., Jiang, Z., Guo, H., & Ni, X. (2020). Fall detection based on key points of human-skeleton using OpenPose. *Symmetry, 12*(5), 744. https://doi.org/10.3390/sym12050744

Eraso Guerrero, J. C., Muñoz España, E., Muñoz Añasco, M., & Pinto Lopera, J. E. (2022). Dataset for human fall recognition in an uncontrolled environment. *Data in Brief, 45*, 108610. https://doi.org/10.1016/j.dib.2022.108610 · Datos: https://doi.org/10.17632/7w7fccy7ky.4

Kwolek, B., & Kepski, M. (2014). Human fall detection on embedded platform using depth maps and wireless accelerometer. *Computer Methods and Programs in Biomedicine, 117*(3), 489–501. https://doi.org/10.1016/j.cmpb.2014.09.005 · Datos: https://fenix.ur.edu.pl/~mkepski/ds/uf.html

Traverso, A., Bayram, A., Rossettini, G., Chiappinotto, S., Galazzi, A., & Palese, A. (2024). Investigating the biomechanics of falls in older adults in long-term care using a video camera: A scoping review. *BMC Geriatrics, 24*, 810. https://doi.org/10.1186/s12877-024-05395-2

Youden, W. J. (1950). Index for rating diagnostic tests. *Cancer, 3*(1), 32–35. https://doi.org/10.1002/1097-0142(1950)3:1<32::AID-CNCR2820030106>3.0.CO;2-3
