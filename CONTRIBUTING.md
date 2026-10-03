# Cómo contribuir

## Flujo de trabajo

1. Crea una rama desde `main` con el tipo y un nombre corto: `feat/ingesta-contrapresion`, `fix/angulo-vertical`, `docs/protocolo`.
2. Instala el entorno con `make instalar`. Esto también instala los hooks de pre-commit.
3. Antes de subir, `make revisar` y `make probar` deben pasar.
4. Abre un *pull request* hacia `main`. La CI repite las mismas revisiones.

## Mensajes de commit

Siguen **Conventional Commits 1.0.0**: `tipo(ámbito): descripción en imperativo`.

| Tipo | Uso |
|---|---|
| `feat` | Nueva funcionalidad |
| `fix` | Corrección de un error |
| `docs` | Solo documentación |
| `test` | Pruebas |
| `refactor` | Cambio de código sin cambiar el comportamiento |
| `build` / `ci` / `chore` | Dependencias, Docker, CI y mantenimiento |

Ejemplos:

```
feat(clasificacion): agregar regla de movimiento inestable
fix(pose): convertir landmarks a píxeles antes de calcular la razón
docs(adr): registrar decisión sobre el modo VIDEO
```

El hook `conventional-pre-commit` rechaza los mensajes que no cumplen el formato.

## Reglas del código

- Los nombres de módulos y clases siguen los componentes de la arquitectura lógica ([docs/arquitectura.md](docs/arquitectura.md)).
- `clasificacion/` no hace I/O.
- **Cada fórmula o umbral nuevo** se documenta en [docs/especificacion-clasificacion.md](docs/especificacion-clasificacion.md), con su fuente o marcado como *[Adaptación]*.
- **Las decisiones de arquitectura** se registran como ADR en [docs/adr/](docs/adr/).
- **Nunca se suben secretos:** `.env` está en `.gitignore`, y pre-commit revisa que no haya claves privadas.

## Referencias

Conventional Commits. (s.f.). *Conventional Commits 1.0.0*. https://www.conventionalcommits.org/es/v1.0.0/
