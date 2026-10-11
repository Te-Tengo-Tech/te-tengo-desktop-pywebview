# References

Source material copied from the thesis documentation repository (Spanish, kept verbatim). Do not edit these files; they are the ground truth for copy, design and acceptance criteria. The full gallery of the desktop prototype (63 screens) lives in the docs repository, `05-prototipos/app-escritorio/pantallas.html`; only the screens the agent implements are copied here.

| Path | What it is |
|---|---|
| `PRODUCT_BACKLOG.md` | User stories and acceptance criteria (Given/When/Then), US-01 to US-40 |
| `BRIEF-pcs-camaras-y-movimientos.md` | Design brief of the change request «PCs, cámaras y datos de movimiento» (US-28 to US-40): screens D-28 to D-38 of the desktop |
| `desktop-prototype/screens/` | The prototype screens the agent implements, named as in the gallery (00 splash, 01–05 states of «Estado», 06–09 tray notifications and the live view, 20 and 23 «Cámaras»; later screens are added with their features) |
| `desktop-prototype/src/core.js` | Prototype source: exact Spanish copy, state priority (`health`, `camStatus`, `trayState`), icons, the brand kit's symbol and the room illustrations |
| `desktop-prototype/src/app.css` | Design tokens and component styles (copied whole into `ui/web/app.css`) |
| `desktop-prototype/src/proto.*` | The navigable prototype (its demo panel simulates the phone; not part of the app) |
| `desktop-prototype/DESIGN.md`, `PRODUCT.md` | Design and product notes, including the draft copy that still needs approval |
| `desktop-prototype/*.svg` | Brand kit: app icon, symbol and the «Captura» logotype (two figures hugging) |
| `diagrams/integracion.puml` | Sequence diagrams per flow of the integration architecture |

The prototype loads Poppins from Google Fonts; the agent bundles it in `src/te_tengo_captura/ui/web/fonts/` (SIL Open Font License, `OFL.txt`) because it must work offline.
