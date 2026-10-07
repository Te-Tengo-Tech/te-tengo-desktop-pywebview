# Blockers

Things the agent cannot decide or get by itself. Work continues with fakes; the team resolves each item.

| Item | What is needed | Owner | Status |
|---|---|---|---|
| UI copy after edge processing | The prototype (screens 01, 06) says «Enviando video» and «Video cifrado». With ADR 0007 the agent sends events and clips, not video. Until the team updates the prototype, the copy is used verbatim from `core.js` and kept in one module so it is easy to change. | Team | Open |
| Live view transport | Team confirmation of the WebSocket JPEG relay proposed in `docs/API_CONTRACT.md` of `te-tengo-general-api` (section 4). Blocks T18. | Team | Open |
| Tray menu texts | The prototype shows the tray icon and its notifications but not the right-click menu. «Abrir Te Tengo Captura» and «Salir» are placeholders until the team confirms them. | Team | Open |
| Hardware checks | Webcam, display, tray and Windows packaging cannot be tested in the cloud. See the local test checklist in `docs/WORK_PLAN.md`. | Team (local) | Open |
| Dataset validation | `make validar` downloads URFD and CAUCAFall from hosts outside the cloud allow-list. Any change to the detection logic must be validated locally. | Team (local) | Open |
| Windows code signing | Without a certificate, Windows SmartScreen warns on first run. Acceptable for the pilot; record the decision. | Team | Open |
| Rejected installation credential | The prototype has no screen or copy for `401 CREDENCIAL_INVALIDA`. The agent logs it, keeps retrying and shows the «Sin internet» state (04), which tells the family to wait and the window note tells them to call the team. A specific copy is needed if the team wants one. | Team | Open |
| Video codec license | PyAV's wheels bundle `libx264` (GPL-2.0-or-later), used to encode the clips (ADR 0008). Fine for the pilot; review before wider distribution or switch to an LGPL build with OpenH264. | Team | Open |
