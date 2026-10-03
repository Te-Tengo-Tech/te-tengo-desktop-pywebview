# 0004. Clasificación por umbrales de Chen et al. (2020)

**Estado:** aceptada (2026-10-03)

## Contexto
El proyecto prohíbe entrenar modelos. El benchmarking IB3 eligió el método de umbrales geométricos de Chen et al. (2020), con un puntaje de 4,33.

## Decisión
Implementar sus tres condiciones (velocidad de descenso del centro de la cadera, ángulo de la línea central < 45° y razón ancho/alto ≥ 1) y su regla para detectar que la persona se levanta, adaptadas a MediaPipe. El detalle está en [especificacion-clasificacion.md](../especificacion-clasificacion.md).

## Consecuencias
- El umbral de velocidad debe calibrarse (el artículo tiene valores contradictorios).
- La vista lateral y la oclusión son limitaciones conocidas que deben evaluarse en la validación.
- La regla de movimiento inestable es una propuesta propia pendiente de validación.

Chen, W., Jiang, Z., Guo, H., & Ni, X. (2020). Fall detection based on key points of human-skeleton using OpenPose. *Symmetry, 12*(5), 744. https://doi.org/10.3390/sym12050744
