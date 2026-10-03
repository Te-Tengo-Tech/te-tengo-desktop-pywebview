# 0006. MediaPipe en modo VIDEO, un seguimiento por cámara

**Estado:** aceptada (2026-10-03). Reemplaza la decisión de modo `IMAGE` del ADR 0003; el resto de ese ADR sigue vigente.

## Contexto
En la validación con URFD y CAUCAFall ([validacion.md](../validacion.md)), el modo `IMAGE` perdía a la persona en el **43 %** de los fotogramas de las caídas de CAUCAFall, justo durante el descenso. El modo `VIDEO` sigue a la persona entre fotogramas y exige marcas de tiempo crecientes.

| Variante (8 fps) | Cobertura en caídas de CAUCAFall | Cobertura en caídas de URFD |
|---|---|---|
| lite · IMAGE | 57 % | 86 % |
| **lite · VIDEO** | **82 %** | **88 %** |
| full · IMAGE | 57 % | 83 % |
| full · VIDEO | 82 % | 89 % |

## Decisión
- Usar el modo `VIDEO` con el modelo *lite*. El *full* no mejora la cobertura y consume más CPU.
- El proceso de inferencia mantiene **un landmarker por cámara** con su última marca de tiempo. Si llega una marca anterior (el agente se reconectó), se crea uno nuevo.
- Cuando la cámara se desconecta, se libera su landmarker.

## Consecuencias
- El worker recibe el `camara_id` y la marca de tiempo del agente en cada inferencia.
- La validación (`scripts/evaluar.py`) y el worker usan el mismo modo, así que sus resultados coinciden: 24 de 24 videos reproducidos en vivo.
