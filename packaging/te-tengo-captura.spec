# -*- mode: python -*-
# PyInstaller spec of Te Tengo Captura: one-folder build (dist/te-tengo-captura/).
#
#   uv sync --group empaquetado && make modelo
#   uv run pyinstaller packaging/te-tengo-captura.spec --noconfirm
#
# Bundles the MediaPipe model (models/), the web UI (te_tengo_captura/ui/web) and MediaPipe's
# data files. The Windows icon is drawn from the brand app icon at build time.
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules

RAIZ = Path(SPECPATH).parent
sys.path.insert(0, str(RAIZ / "src"))

from te_tengo_captura.bandeja.iconos import icono  # noqa: E402

MODELO = RAIZ / "models" / "pose_landmarker_lite.task"
if not MODELO.is_file():
    raise SystemExit(f"Falta el modelo {MODELO}: ejecuta `make modelo`")

ICONO = Path(workpath) / "te-tengo-captura.ico"
ICONO.parent.mkdir(parents=True, exist_ok=True)
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
)
coll = COLLECT(exe, a.binaries, a.datas, name="te-tengo-captura", upx=False)
