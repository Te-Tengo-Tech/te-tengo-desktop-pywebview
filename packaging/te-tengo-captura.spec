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

from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_dynamic_libs,
    collect_submodules,
    copy_metadata,
)

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
    *copy_metadata("keyring"),  # its backends are found through entry points
]
binaries = collect_dynamic_libs("mediapipe")
hiddenimports = [
    *collect_submodules("pystray"),  # the backend is chosen at run time
    *collect_submodules("webview.platforms"),
    # keyring picks the OS credential store at run time (Windows Credential Manager, the macOS
    # Keychain): its backends are entry points PyInstaller cannot follow.
    *collect_submodules("keyring.backends"),
]
if EN_MACOS:
    hiddenimports += ["AVFoundation", "Foundation"]  # webcam ids (captura/dispositivos.py)
elif sys.platform == "win32":
    hiddenimports += ["comtypes", "comtypes.persist", "comtypes.automation"]

PYARROW_SOBRANTE = [
    f"pyarrow.{m}"
    for m in (
        "flight", "_flight", "dataset", "_dataset", "_dataset_orc", "_dataset_parquet",
        "_dataset_parquet_encryption", "_parquet_encryption", "acero", "_acero", "substrait",
        "_substrait", "_s3fs", "_gcsfs", "_azurefs", "_hdfs", "orc", "_orc", "cuda", "_cuda",
        "gandiva", "interchange", "tests",
    )
]
# The core links libarrow_dataset, _acero and _substrait, so those libraries stay.
LIBS_ARROW_SOBRANTES = ("arrow_flight", "arrow_s3", "gandiva", "python_flight", "python_parquet_encryption")
SOBRANTES_ARROW = (".pyx", ".pxd", ".pxi", ".h", ".hpp", ".cc")

a = Analysis(
    [str(RAIZ / "packaging" / "lanzador.py")],
    pathex=[str(RAIZ / "src")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["tkinter", "pytest", *PYARROW_SOBRANTE],  # mediapipe imports matplotlib: keep it
    noarchive=False,
)
# pyarrow's hook takes every Arrow library (~120 MB). The movements (almacen/puntos.py) only read
# and write Parquet in memory: Flight, Gandiva and the cloud file systems stay out, and so do the
# C++ headers and Cython sources.
a.binaries = [b for b in a.binaries if not any(f in Path(b[0]).name for f in LIBS_ARROW_SOBRANTES)]
a.datas = [
    d for d in a.datas if not (d[0].startswith("pyarrow") and (d[0].endswith(SOBRANTES_ARROW) or "/include/" in d[0].replace("\\", "/")))
]
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
