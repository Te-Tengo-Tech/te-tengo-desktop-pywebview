# -*- mode: python -*-
# PyInstaller spec of Te Tengo Captura: one-folder build (dist/te-tengo-captura/).
#
#   uv sync --group empaquetado && make modelo
#   uv run pyinstaller packaging/te-tengo-captura.spec --noconfirm
#
# Bundles the MediaPipe model (models/), the web UI (te_tengo_captura/ui/web) and MediaPipe's
# data files. The icon (.ico on Windows, .icns in the macOS .app) is drawn from the brand app icon
# at build time.
#
# macOS: the build is `dist/Te Tengo Captura.app`. PyInstaller signs every binary and the bundle:
# ad-hoc by default (enough to run on Apple Silicon), or with the Developer ID identity named in the
# environment variable TT_MACOS_IDENTIDAD_FIRMA (hardened runtime, secure timestamp and
# packaging/macos/entitlements.plist), which notarization requires (docs/RELEASES.md).
import os
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules

RAIZ = Path(SPECPATH).parent
sys.path.insert(0, str(RAIZ / "src"))

from te_tengo_captura import __version__  # noqa: E402
from te_tengo_captura.bandeja.iconos import icono  # noqa: E402

MODELO = RAIZ / "models" / "pose_landmarker_lite.task"
if not MODELO.is_file():
    raise SystemExit(f"Falta el modelo {MODELO}: ejecuta `make modelo`")

EN_MACOS = sys.platform == "darwin"
# Developer ID identity (e.g. "Developer ID Application: Name (TEAMID)"); empty: ad-hoc signature.
IDENTIDAD_FIRMA = os.environ.get("TT_MACOS_IDENTIDAD_FIRMA") or None
ENTITLEMENTS = str(RAIZ / "packaging" / "macos" / "entitlements.plist") if EN_MACOS else None
Path(workpath).mkdir(parents=True, exist_ok=True)
if EN_MACOS:
    ICONO = Path(workpath) / "te-tengo-captura.icns"
    icono(None, 1024).save(ICONO)
else:
    ICONO = Path(workpath) / "te-tengo-captura.ico"
    icono(None, 256).save(ICONO, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])

datas = [
    (str(MODELO), "models"),
    (str(RAIZ / "src" / "te_tengo_captura" / "ui" / "web"), "te_tengo_captura/ui/web"),
    *collect_data_files("mediapipe"),
    *collect_data_files("webview"),
]
binaries = collect_dynamic_libs("mediapipe")
hiddenimports = [
    *collect_submodules("pystray"),  # the backend is chosen at run time
    *collect_submodules("webview.platforms"),
]

a = Analysis(
    [str(RAIZ / "packaging" / "lanzador.py")],
    pathex=[str(RAIZ / "src")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["tkinter", "pytest"],  # mediapipe imports matplotlib: keep it
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="te-tengo-captura",
    console=False,  # a tray app: no console window
    icon=str(ICONO),
    upx=False,
    codesign_identity=IDENTIDAD_FIRMA,
    entitlements_file=ENTITLEMENTS,
)
coll = COLLECT(exe, a.binaries, a.datas, name="te-tengo-captura", upx=False)

if EN_MACOS:
    # A .app bundle so Finder and the Dock show the brand icon. [implementation choice] The bundle id
    # follows the mobile app's (tech.tetengo.teTengo). macOS shows NSCameraUsageDescription when it
    # asks for camera access; the prototype has no copy for it, so this minimal factual sentence is
    # pending team review (docs/BLOCKERS.md, «macOS camera permission text»).
    app = BUNDLE(
        coll,
        name="Te Tengo Captura.app",
        icon=str(ICONO),
        bundle_identifier="tech.tetengo.captura",
        version=__version__,  # the signing identity and entitlements come from the EXE
        info_plist={
            "CFBundleDisplayName": "Te Tengo Captura",
            "CFBundleVersion": __version__,
            "NSCameraUsageDescription": "Te Tengo Captura usa la webcam para detectar caídas.",
            "NSHighResolutionCapable": True,
        },
    )
