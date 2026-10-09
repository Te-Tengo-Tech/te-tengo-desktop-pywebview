# Releasing the Windows agent

How a version of Te Tengo Captura becomes an installer that the project team runs on a household PC. The workflow [`release-windows.yml`](../.github/workflows/release-windows.yml) builds it; [`packaging/te-tengo-captura.iss`](../packaging/te-tengo-captura.iss) is the Inno Setup script.

## The installer
`te-tengo-captura-<version>-instalador.exe`, in Spanish, installs **per user** and needs **no administrator rights**.

| What | Where / how |
|---|---|
| Program (PyInstaller one-folder build) | `%LOCALAPPDATA%\Programs\TeTengoCaptura\` (the path in [INSTALLATION.md](INSTALLATION.md)) |
| Start menu shortcut | «Te Tengo Captura», for this user |
| Start with Windows | `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`, value `TeTengoCaptura` = `"<path>\te-tengo-captura.exe"`. This is **the same value the agent writes itself** on every start (`src/te_tengo_captura/autoinicio.py`), so the agent finds it in place and there is never a second entry |
| Configuration (optional) | `/CONFIG="C:\ruta\config.toml"` copies the household's installation file to `%APPDATA%\TeTengoCaptura\config.toml`. An existing file is never overwritten |
| Icon | The brand icon that the PyInstaller spec draws (`build\te-tengo-captura\te-tengo-captura.ico`) |

- **Upgrades.** Running a newer installer stops this user's running agent, replaces the files and starts the agent again, if a configuration exists. The agent is also restarted after a silent install (`/VERYSILENT /SUPPRESSMSGBOXES`), which is what an automatic update would use.
- **Uninstall** (*Settings → Apps*, or `unins000.exe`):
  1. It stops the agent, then removes the program, the shortcut and the autostart value.
  2. It then asks «¿Eliminar también la configuración y los datos…?» The default is **No**, so a reinstall keeps the installation credential and any pending events.
  3. A silent uninstall keeps the data.
- **Build locally** on Windows with Inno Setup 6 installed:
  ```powershell
  make empaquetar   # or: uv run pyinstaller packaging/te-tengo-captura.spec --noconfirm
  & "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" /DAppVersion=0.3.0 packaging\te-tengo-captura.iss
  ```

## The workflow
| Trigger | What happens |
|---|---|
| Pull request touching `packaging/` or the workflow | Full build and tests, installer kept as a 3-day artifact. Nothing is released |
| Push to `main` (a merged `release/*` or `hotfix/*` pull request) | Same, plus the `Draft GitHub Release` job: it **waits for an approval on the `produccion` environment**, then creates a **draft** release `v<version>` with the installer and `SHA256SUMS.txt`, targeting the released commit. A person reviews the notes and publishes it, which creates the tag |
| Manual run (*Actions → Release Windows → Run workflow*) | Same build; the installer is kept as a 30-day artifact. From `main` it also offers the draft release (with approval); from other branches it only builds, because the environment only accepts `main` |

**Steps:**
1. PyInstaller build.
2. Smoke test of the exe (`--version`, `--autoprueba`).
3. Optional signing of the exe.
4. Inno Setup compile.
5. Optional signing of the installer.
6. A **silent install and uninstall test**: it checks the program folder, the autostart value, the shortcut, `--version` from the installed copy, and that nothing remains after uninstalling.

**Releasing a version** (no tag is pushed by hand; the version in `pyproject.toml` and `__version__` must match, or the build fails):
1. Bump `version` in `pyproject.toml` and `__version__`, and update `CHANGELOG.md`.
2. Merge the release branch to `main` (git flow). Two things start on their own:
   - here, `Release Windows` builds and tests the installer, and its `Draft GitHub Release` job waits for an approval on `produccion`;
   - once `CI` passes on `main`, [`notificar-landing.yml`](../.github/workflows/notificar-landing.yml) sends `repository_dispatch` `publicar-escritorio` with `{ref: <commit SHA>, version: <pyproject version>}` to `te-tengo-landing-astro`. Its `Publicar publicar-escritorio <version>` run builds and tests the installer at that commit and waits for an approval on its own `produccion` environment before uploading `te-tengo-captura-setup.exe` to Cloudflare R2, the landing's download.
3. A required reviewer of `produccion` (jhosepmyr or elmer-riva) approves both runs: open the run, *Review deployments*, tick `produccion`, *Approve and deploy*. Nothing reaches users before that.
4. Review and publish the draft release.
5. Set `TT_AGENTE_VERSION_PUBLICADA=<version>` in the API, so `GET /api/agente/configuracion` announces it (see *Update notices*).

The dispatch needs the secret **`DISPATCH_TOKEN`**: a fine-grained personal access token with resource owner `Te-Tengo-Tech`, access to the single repository `te-tengo-landing-astro` and the repository permission *Contents: Read and write*. Without it `notificar-landing.yml` prints a notice and succeeds; after adding it, run *Actions → Notify the landing → Run workflow* on `main` to send the current release.

### Code signing (optional, inert until configured)
Without signing, the workflow adds a notice and the installer is unsigned. Configure **one** of these under *Settings → Secrets and variables → Actions*:

| Option | Secrets | Variables |
|---|---|---|
| **Azure Artifact Signing** (formerly *Trusted Signing*; about US$10 per month; the identity validation decides who can use it, so check whether an individual developer in Peru is eligible) | `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET` (an app registration with the *Artifact Signing Certificate Profile Signer* role) | `AZURE_SIGNING_ENDPOINT` (e.g. `https://eus.codesigning.azure.net/`), `AZURE_SIGNING_ACCOUNT`, `AZURE_CERTIFICATE_PROFILE` |
| **Code signing certificate** (.pfx, from a public CA) | `WINDOWS_PFX_BASE64` (`base64` of the .pfx), `WINDOWS_PFX_PASSWORD` | — |

- **What is signed:** both the agent exe and the installer, with SHA-256 and an RFC 3161 timestamp.
- **Since 2023,** CAs issue code signing keys only on hardware tokens or cloud HSMs. A .pfx export is therefore only possible with some cloud-key providers, which makes Azure Artifact Signing the practical option for CI.

## Distribution
### GitHub Releases: the common path for the pilot
- **The pilot.** The project team installs every agent itself ([INSTALLATION.md](INSTALLATION.md)), so a published GitHub Release with the installer and its checksum is enough. Releases are versioned, immutable once published, and free.
- **Public downloads.** The repository is public, so a published release's assets can be downloaded by anyone. For households, the landing page links to the stable copy that its `publicar.yml` uploads to Cloudflare R2 (`te-tengo-captura-setup.exe` with its `.sha256`), always the latest approved release.
- **Checking the download.** On the household PC: `Get-FileHash .\te-tengo-captura-<v>-instalador.exe` must match `SHA256SUMS.txt`.

### SmartScreen without signing
On first run, an unsigned installer (and the unsigned exe) triggers **Microsoft Defender SmartScreen**:
- **The message.** «Windows protegió su PC», with only «No ejecutar» visible.
- **The workaround.** The installer runs after «Más información» → «Ejecutar de todas formas» ([INSTALLATION.md](INSTALLATION.md), section 3). This is acceptable for a pilot installed by the team; the decision is recorded in `docs/BLOCKERS.md` («Windows code signing»).
- **Signing alone is not enough.** Signing removes the «editor desconocido» label, but SmartScreen also uses download **reputation**. A newly signed file can still warn until it has been downloaded enough times; EV certificates no longer skip this.

### Microsoft Store (option)
- **Free.** Since 2025, individual developers can publish to the Microsoft Store **without a registration fee** ([Windows Developer Blog, 19 May 2025](https://blogs.windows.com/windowsdeveloper/2025/05/19/microsoft-store-expands-opportunities-for-windows-app-developers/)).
- **Win32 installers.** The Store accepts **Win32 apps distributed as an .exe or .msi installer**, which fits this Inno Setup installer.
- **Requirements for an .exe/.msi submission:**
  - the installer is hosted at a **versioned HTTPS URL** that never changes content (a published GitHub Release asset in a public repository works);
  - it installs **silently** (`/VERYSILENT /SUPPRESSMSGBOXES`, already supported);
  - it is **signed** with a certificate that chains to the Microsoft Trusted Root Program: the Store does not re-sign Win32 installers, so this route still needs the signing step above.
- **What it adds:**
  - a trusted install source, without SmartScreen warnings once listed;
  - a store page for households to find the app;
  - certification and the store policies, privacy policy included (camera and health-related data, Ley 29733).
- **Updates.** They still come from the installer: the Store does not update Win32 apps itself.
- **Not needed for the pilot.** It is worth it once households install the agent without the team.

## Update notices: `versionAgente`
- **What exists today.** `GET /api/agente/configuracion` returns `versionAgente`: the API's `TT_AGENTE_VERSION_PUBLICADA`. The agent fetches it at startup and every hour (`src/te_tengo_captura/umbrales_remotos.py`). When it differs from its own `__version__`, the agent **only logs it** («Versión del agente publicada: …»).
- **How it could notify updates** (a proposal; it changes `docs/AGENT_CONTRACT.md` in both repositories, so it needs the team's agreement):
  1. **Compare as versions,** not strings (`packaging.version.Version`), and act only when the published version is **newer**. That way a downgrade or a test build never triggers anything.
  2. **Notify:** show «Hay una versión nueva de Te Tengo Captura» in the window footer and as a tray notification. The copy must be added to the desktop prototype first (AGENTS.md: no invented copy). The project team then runs the new installer, which stops and restarts the agent and keeps the configuration and the outbox.
  3. **Optional automatic update:** extend the response with `urlDescarga` and `sha256` of the installer.
     - The agent downloads it to its data directory and checks the SHA-256 and the **Authenticode signature**, so this needs signing.
     - It then runs it with `/VERYSILENT /SUPPRESSMSGBOXES`. The installer stops the agent and starts the new one.
     - It should only do this while no event is pending in the outbox and no live view is open.
