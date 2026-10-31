# Novedades

«Qué cambió» of each version of Te Tengo Captura, as the family reads it when the app says «Hay una versión nueva» (US-43). When a version reaches production, `produccion.yml` publishes the lines of its section with the version for the apps (`versiones/windows.json` and `versiones/mac.json`, read by `GET /api/versiones`; docs/RELEASES.md).

- One section per version, `## [x.y.z]`, written on the release branch before merging it (rename `[Unreleased]`).
- Each line starts with `- `: one short sentence in Spanish for a family member, at most 10 lines of 200 characters; what changed for them, not how (the CHANGELOG is the technical record).
- The lines are copy: they need the same approval as any other label (docs/BLOCKERS.md). A version without a section is published without notes, and the apps hide «Qué cambió».

## [Unreleased]

## [0.7.0]

- Ahora detecta también las caídas lentas, como resbalar de una silla o de la cama hasta el suelo.
- Nuevo en «Cámaras»: puedes ver u ocultar el video y el esqueleto en la vista previa de la cámara.
- Al salir de la aplicación, se cierra en pocos segundos y ya no se queda congelada.
- Corregimos el guardado de video para que «Ver qué pasó» muestre el video.
- Preparada para guardar tus grabaciones en el nuevo almacenamiento de Te Tengo.

## [0.6.0]

- Nuevo «Restablecer esta PC» en «Acerca de»: la desvincula y borra todo lo que guardó.
- Al desinstalar, la PC también se quita de la casa y se borran sus datos.
- «Salir» ahora pide confirmación, porque deja de detectar caídas.
