"""USB webcams of the PC, identified by a stable device ID from the operating system (CA-29.4).

OpenCV opens a webcam by index (``cv2.VideoCapture(indice, backend)``), and an index changes
when another webcam is plugged in or the PC restarts. The agent therefore stores the operating
system's device ID and resolves the current index **each time it opens the webcam**, so a room
is always watched by the same camera.

* macOS: AVFoundation (``AVCaptureDevice.uniqueID``), in the order of OpenCV's backend.
* Windows: DirectShow (the moniker's ``DevicePath``), in the order of OpenCV's videoInput.
* Linux: V4L2 (the ``/dev/v4l/by-id`` link name), with the index of its ``/dev/videoN``.

Each list reproduces exactly how OpenCV 5.0.0 numbers the devices for that backend
(``modules/videoio/src/cap_avfoundation_mac.mm``, ``cap_dshow.cpp`` and ``cap_v4l.cpp``), so
the index is valid for ``cv2.VideoCapture(indice, backend)``. The OS calls are injectable and
imported inside functions: importing this module never imports cv2, PyObjC or comtypes.
"""

import functools
import logging
import os
import re
import sys
import time
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from te_tengo_captura.captura.fuentes import Imagen

logger = logging.getLogger(__name__)

# Contract limits of the stored device ID and name.
LARGO_MAX_ID = 300
LARGO_MAX_NOMBRE = 100

# cv2.CAP_* values (a test checks them against cv2), so listing needs no OpenCV import.
CAP_V4L2 = 200
CAP_DSHOW = 700
CAP_AVFOUNDATION = 1200


@dataclass(frozen=True, slots=True)
class Dispositivo:
    dispositivo_id: str  # stable OS ID, at most LARGO_MAX_ID characters
    nombre: str  # human name, at most LARGO_MAX_NOMBRE characters
    indice: int  # OpenCV index, valid for ``backend`` only
    backend: int  # cv2.CAP_* constant


def _dispositivo(dispositivo_id: str, nombre: str, indice: int, backend: int) -> Dispositivo:
    return Dispositivo(
        dispositivo_id[:LARGO_MAX_ID], nombre.strip()[:LARGO_MAX_NOMBRE], indice, backend
    )


def _sin_repetidos(dispositivos: Iterable[Dispositivo]) -> list[Dispositivo]:
    """Keeps the first device of each ID (the one OpenCV reaches first)."""
    vistos: set[str] = set()
    unicos = []
    for dispositivo in dispositivos:
        if dispositivo.dispositivo_id not in vistos:
            vistos.add(dispositivo.dispositivo_id)
            unicos.append(dispositivo)
    return unicos


# ------------------------------------------------------------------ macOS (AVFoundation)


def comparar_utf16(a: str, b: str) -> int:
    """``-1``, ``0`` or ``1`` comparing UTF-16 code units, like ``-[NSString compare:]``."""
    ca, cb = a.encode("utf-16-be"), b.encode("utf-16-be")
    return (ca > cb) - (ca < cb)


def ordenar_avfoundation(
    camaras: Sequence[tuple[str, str]], comparar: Callable[[str, str], int] = comparar_utf16
) -> list[Dispositivo]:
    """Numbers ``(uniqueID, localizedName)`` pairs as OpenCV's AVFoundation backend does.

    ``camaras`` comes in the order of ``devicesWithMediaType:AVMediaTypeVideo`` followed by
    ``devicesWithMediaType:AVMediaTypeMuxed``. OpenCV sorts that array by ``uniqueID`` with
    ``compare:`` and opens ``devices[cameraNum]`` (``CvCaptureCAM::startCaptureDevice``).
    """

    def por_id(x: tuple[str, str], y: tuple[str, str]) -> int:
        return comparar(x[0], y[0])

    ordenadas = sorted(camaras, key=functools.cmp_to_key(por_id))
    return _sin_repetidos(
        _dispositivo(unico, nombre, indice, CAP_AVFOUNDATION)
        for indice, (unico, nombre) in enumerate(ordenadas)
    )


def _camaras_avfoundation() -> list[tuple[str, str]]:
    """The same AVFoundation query as OpenCV, in the same process (same permissions)."""
    import AVFoundation

    dispositivo = AVFoundation.AVCaptureDevice
    camaras = list(dispositivo.devicesWithMediaType_(AVFoundation.AVMediaTypeVideo))
    camaras += list(dispositivo.devicesWithMediaType_(AVFoundation.AVMediaTypeMuxed))
    return [(str(c.uniqueID()), str(c.localizedName())) for c in camaras]


def _comparar_nsstring(a: str, b: str) -> int:
    from Foundation import NSString

    return int(NSString.stringWithString_(a).compare_(b))


def listar_avfoundation(
    camaras: Callable[[], Sequence[tuple[str, str]]] = _camaras_avfoundation,
    comparar: Callable[[str, str], int] = _comparar_nsstring,
) -> list[Dispositivo]:
    return ordenar_avfoundation(camaras(), comparar)


# ------------------------------------------------------------------ Windows (DirectShow)


@dataclass(frozen=True, slots=True)
class EntradaDirectShow:
    """One moniker of ``CLSID_VideoInputDeviceCategory``, in enumeration order."""

    enlazable: bool  # BindToStorage(IPropertyBag) succeeded
    nombre: str | None  # "FriendlyName"
    ruta: str | None  # "DevicePath"


def ordenar_directshow(entradas: Sequence[EntradaDirectShow]) -> list[Dispositivo]:
    """Numbers the monikers as OpenCV's DirectShow backend (videoInput) does.

    ``videoInput::getDevice`` opens the moniker at position ``deviceId`` counting **every**
    moniker, and needs its "FriendlyName"; ``VideoCapture_DShow::open`` first rejects indexes at
    or above ``listDevices``, which counts only the monikers that bind to a property bag. So a
    device is openable when it binds, has a name and its position is below that count.
    """
    enlazables = sum(entrada.enlazable for entrada in entradas)
    sin_ruta: dict[str, int] = {}
    dispositivos = []
    for posicion, entrada in enumerate(entradas):
        if not entrada.enlazable or not entrada.nombre or posicion >= enlazables:
            continue
        if entrada.ruta:
            dispositivo_id = entrada.ruta
        else:
            # Virtual cameras (OBS, some drivers) have no "DevicePath": their ID is the name
            # plus its occurrence, which stays stable while no other camera of that name appears.
            sin_ruta[entrada.nombre] = sin_ruta.get(entrada.nombre, 0) + 1
            dispositivo_id = f"{entrada.nombre}#{sin_ruta[entrada.nombre]}"
        dispositivos.append(_dispositivo(dispositivo_id, entrada.nombre, posicion, CAP_DSHOW))
    return _sin_repetidos(dispositivos)


@functools.cache
def _interfaces_directshow() -> tuple[Any, Any]:
    """``ICreateDevEnum`` and ``IPropertyBag``, declared once (vtable order of the SDK headers).

    Declared by hand, so comtypes never generates a typelib wrapper at run time and the
    PyInstaller bundle needs none. Only the methods used are typed; the others keep their slot.
    """
    from ctypes import POINTER, c_ulong, c_void_p

    from comtypes import COMMETHOD, GUID, HRESULT, IPersist, IUnknown
    from comtypes.persist import IPropertyBag

    class IPersistStream(IPersist):  # type: ignore[misc]
        _iid_ = GUID("{00000109-0000-0000-C000-000000000046}")
        _methods_ = [  # noqa: RUF012
            COMMETHOD([], HRESULT, "IsDirty"),
            COMMETHOD([], HRESULT, "Load", (["in"], c_void_p, "pStm")),
            COMMETHOD([], HRESULT, "Save", (["in"], c_void_p, "pStm"), (["in"], c_ulong, "f")),
            COMMETHOD([], HRESULT, "GetSizeMax", (["in"], c_void_p, "pcbSize")),
        ]

    class IMoniker(IPersistStream):
        # Only the first two IMoniker methods are used; later vtable slots need no declaration.
        _iid_ = GUID("{0000000F-0000-0000-C000-000000000046}")
        _methods_ = [  # noqa: RUF012
            COMMETHOD(
                [],
                HRESULT,
                "BindToObject",
                (["in"], c_void_p, "pbc"),
                (["in"], c_void_p, "pmkToLeft"),
                (["in"], POINTER(GUID), "riidResult"),
                (["in"], c_void_p, "ppvResult"),
            ),
            COMMETHOD(
                [],
                HRESULT,
                "BindToStorage",
                (["in"], c_void_p, "pbc"),
                (["in"], c_void_p, "pmkToLeft"),
                (["in"], POINTER(GUID), "riid"),
                (["out"], POINTER(POINTER(IPropertyBag)), "ppvObj"),
            ),
        ]

    class IEnumMoniker(IUnknown):  # type: ignore[misc]
        _iid_ = GUID("{00000102-0000-0000-C000-000000000046}")
        _methods_ = [  # noqa: RUF012
            COMMETHOD(
                [],
                HRESULT,
                "Next",
                (["in"], c_ulong, "celt"),
                (["out"], POINTER(POINTER(IMoniker)), "rgelt"),
                (["out"], POINTER(c_ulong), "pceltFetched"),
            ),
        ]

    class ICreateDevEnum(IUnknown):  # type: ignore[misc]
        _iid_ = GUID("{29840822-5B84-11D0-BD3B-00A0C911CE86}")
        _methods_ = [  # noqa: RUF012
            COMMETHOD(
                [],
                HRESULT,
                "CreateClassEnumerator",
                (["in"], POINTER(GUID), "clsidDeviceClass"),
                (["out"], POINTER(POINTER(IEnumMoniker)), "ppEnumMoniker"),
                (["in"], c_ulong, "dwFlags"),
            ),
        ]

    return ICreateDevEnum, IPropertyBag


def _entradas_directshow() -> list[EntradaDirectShow]:
    """Enumerates the video input monikers with ICreateDevEnum, like OpenCV's videoInput."""
    import comtypes
    from comtypes import GUID
    from comtypes.automation import VARIANT

    ICreateDevEnum, IPropertyBag = _interfaces_directshow()  # noqa: N806
    clsid_enumerador = GUID("{62BE5D10-60EB-11D0-BD3B-00A0C911CE86}")  # CLSID_SystemDeviceEnum
    categoria_video = GUID("{860BB310-5D01-11D0-BD3B-00A0C911CE86}")  # VideoInputDeviceCategory

    def leer(bolsa: Any, propiedad: str) -> str | None:
        try:
            valor = bolsa.Read(propiedad, VARIANT(), None)
        except (comtypes.COMError, OSError):
            return None
        return valor if isinstance(valor, str) and valor else None

    def enumerar() -> list[EntradaDirectShow]:
        enumerador = comtypes.CoCreateInstance(
            clsid_enumerador, interface=ICreateDevEnum, clsctx=comtypes.CLSCTX_INPROC_SERVER
        )
        # S_FALSE with a NULL enumerator when the category is empty (no cameras).
        monikers = enumerador.CreateClassEnumerator(categoria_video, 0)
        entradas: list[EntradaDirectShow] = []
        if not monikers:
            return entradas
        while True:
            moniker, obtenidos = monikers.Next(1)
            if obtenidos != 1 or not moniker:
                return entradas
            try:
                bolsa = moniker.BindToStorage(None, None, IPropertyBag._iid_)
            except (comtypes.COMError, OSError):
                entradas.append(EntradaDirectShow(False, None, None))
                continue
            entradas.append(
                EntradaDirectShow(True, leer(bolsa, "FriendlyName"), leer(bolsa, "DevicePath"))
            )

    # OpenCV initializes COM as single-threaded (CoInitialize) in its DirectShow capture; do
    # the same in this thread. Another apartment model already set here is fine to reuse.
    try:
        comtypes.CoInitialize()
        inicializado = True
    except OSError:
        inicializado = False
    try:
        # enumerar() returns before CoUninitialize, so every COM pointer is released first.
        return enumerar()
    finally:
        if inicializado:
            comtypes.CoUninitialize()


def listar_directshow(
    entradas: Callable[[], Sequence[EntradaDirectShow]] = _entradas_directshow,
) -> list[Dispositivo]:
    return ordenar_directshow(entradas())


# ------------------------------------------------------------------ Linux (V4L2)

_NODO_VIDEO = re.compile(r"video(\d+)")


def listar_v4l2(
    por_id: Path = Path("/dev/v4l/by-id"), sysfs: Path = Path("/sys/class/video4linux")
) -> list[Dispositivo]:
    """USB webcams from their ``/dev/v4l/by-id/*-video-index0`` links, sorted by index.

    The link name (bus, vendor, model and serial) is the stable ID; it points to
    ``/dev/videoN``, which OpenCV opens as ``cv2.VideoCapture(N, cv2.CAP_V4L2)``. The
    ``-video-index1`` nodes are metadata, not video, and are skipped.
    """
    if not por_id.is_dir():
        return []
    dispositivos = []
    for enlace in sorted(por_id.glob("*-video-index0")):
        destino = Path(os.path.realpath(enlace))
        coincidencia = _NODO_VIDEO.fullmatch(destino.name)
        if coincidencia is None or not destino.exists():
            continue  # dangling link (camera just unplugged) or not a video node
        try:
            nombre = (sysfs / destino.name / "name").read_text(encoding="utf-8").strip()
        except OSError:
            nombre = ""
        indice = int(coincidencia.group(1))
        dispositivos.append(_dispositivo(enlace.name, nombre or enlace.name, indice, CAP_V4L2))
    return _sin_repetidos(sorted(dispositivos, key=lambda d: d.indice))


# ------------------------------------------------------------------ all platforms


def listar_dispositivos(plataforma: str | None = None) -> list[Dispositivo]:
    """The webcams of this PC, in OpenCV's index order for the platform's backend."""
    plataforma = sys.platform if plataforma is None else plataforma
    if plataforma == "darwin":
        return listar_avfoundation()
    if plataforma == "win32":
        return listar_directshow()
    if plataforma.startswith("linux"):
        return listar_v4l2()
    return []


def abrir_por_id(
    dispositivo_id: str, listar: Callable[[], Sequence[Dispositivo]] = listar_dispositivos
) -> Dispositivo | None:
    """The device with that ID and its **current** index, or ``None`` if it is not plugged in."""
    buscado = dispositivo_id[:LARGO_MAX_ID]
    return next((d for d in listar() if d.dispositivo_id == buscado), None)


class Captura(Protocol):
    """The part of ``cv2.VideoCapture`` the source uses."""

    def isOpened(self) -> bool: ...  # noqa: N802
    def read(self) -> tuple[bool, Any]: ...
    def release(self) -> None: ...


def _abrir_captura_opencv(indice: int, backend: int) -> Captura:
    import cv2

    captura: Captura = cv2.VideoCapture(indice, backend)
    return captura


class FuenteWebcamPorId:
    """The webcam with a given OS device ID, wherever its index is at the moment it opens.

    Same protocol as ``FuenteWebcam``. Each ``abrir`` lists the devices again, so a replugged
    webcam or a new one plugged before it keeps this room on the right camera.
    """

    def __init__(
        self,
        dispositivo_id: str,
        listar: Callable[[], Sequence[Dispositivo]] = listar_dispositivos,
        abrir_captura: Callable[[int, int], Captura] = _abrir_captura_opencv,
        reloj: Callable[[], float] = time.monotonic,
    ) -> None:
        self._id = dispositivo_id
        self._listar = listar
        self._abrir_captura = abrir_captura
        self._reloj = reloj
        self._captura: Captura | None = None
        self.dispositivo: Dispositivo | None = None  # last resolved device, for logging

    def abrir(self) -> bool:
        self.cerrar()
        try:
            dispositivo = abrir_por_id(self._id, self._listar)
        except Exception:
            logger.exception("No se pudo listar las webcams")
            return False
        if dispositivo is None:
            return False
        self.dispositivo = dispositivo
        captura = self._abrir_captura(dispositivo.indice, dispositivo.backend)
        if not captura.isOpened():
            captura.release()
            return False
        logger.info("Webcam «%s» abierta en el índice %d", dispositivo.nombre, dispositivo.indice)
        self._captura = captura
        return True

    def leer(self) -> tuple[float, Imagen] | None:
        if self._captura is None:
            return None
        ok, imagen = self._captura.read()
        if not ok or imagen is None:
            return None
        return self._reloj(), imagen

    def cerrar(self) -> None:
        if self._captura is not None:
            self._captura.release()
            self._captura = None
