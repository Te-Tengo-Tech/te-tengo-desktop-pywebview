"""US-29, CA-29.4 «La cámara no se confunde»: stable device IDs mapped to OpenCV indexes."""

import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from te_tengo_captura.captura.dispositivos import (
    CAP_AVFOUNDATION,
    CAP_DSHOW,
    CAP_V4L2,
    LARGO_MAX_ID,
    LARGO_MAX_NOMBRE,
    Dispositivo,
    EntradaDirectShow,
    FuenteWebcamPorId,
    abrir_por_id,
    comparar_utf16,
    listar_avfoundation,
    listar_directshow,
    listar_dispositivos,
    listar_v4l2,
    ordenar_avfoundation,
    ordenar_directshow,
)

MAC_INTEGRADA = ("6C707041-05AC-0011-0009-000000000001", "MacBook Pro Camera")
MAC_OBS = ("7626645E-4425-469E-9D8B-97E0FA59AC75", "OBS Virtual Camera")
MAC_USB = ("0x1420000046d0825", "HD Webcam C270")

LOGITECH = r"\\?\usb#vid_046d&pid_0825&mi_00#7&1a2b3c4d&0&0000#{65e8773d-8f56-11d0-a3b9-00a0c9223196}\global"
MICROSOFT = r"\\?\usb#vid_045e&pid_0779&mi_00#6&2f3e4d5c&0&0000#{65e8773d-8f56-11d0-a3b9-00a0c9223196}\global"


def test_constantes_de_backend_iguales_a_opencv() -> None:
    import cv2

    assert (CAP_AVFOUNDATION, CAP_DSHOW, CAP_V4L2) == (
        cv2.CAP_AVFOUNDATION,
        cv2.CAP_DSHOW,
        cv2.CAP_V4L2,
    )


# ------------------------------------------------------------------ macOS


def test_avfoundation_ordena_por_unique_id_como_opencv() -> None:
    # devicesWithMediaType(Video) + devicesWithMediaType(Muxed), then sorted by uniqueID.
    dispositivos = ordenar_avfoundation([MAC_OBS, MAC_INTEGRADA, MAC_USB])
    assert [(d.dispositivo_id, d.indice) for d in dispositivos] == [
        (MAC_USB[0], 0),  # "0" < "6" < "7"
        (MAC_INTEGRADA[0], 1),
        (MAC_OBS[0], 2),
    ]
    assert {d.backend for d in dispositivos} == {CAP_AVFOUNDATION}
    assert dispositivos[1].nombre == "MacBook Pro Camera"


def test_avfoundation_compara_como_nsstring_y_no_por_mayusculas() -> None:
    # compare: without options is case sensitive: "B" (0x42) sorts before "a" (0x61).
    dispositivos = ordenar_avfoundation([("a-1", "uno"), ("B-2", "dos")])
    assert [d.dispositivo_id for d in dispositivos] == ["B-2", "a-1"]
    # UTF-16 code units, not code points: U+FF5E sorts after U+1F600's high surrogate D83D.
    assert comparar_utf16("\uff5e", "\U0001f600") == 1
    assert comparar_utf16("x", "x") == 0


def test_avfoundation_repetido_en_video_y_muxed_conserva_el_primer_indice() -> None:
    dispositivos = ordenar_avfoundation([MAC_INTEGRADA, MAC_OBS, MAC_INTEGRADA])
    assert [(d.dispositivo_id, d.indice) for d in dispositivos] == [
        (MAC_INTEGRADA[0], 0),
        (MAC_OBS[0], 2),
    ]


def test_avfoundation_usa_las_camaras_y_el_comparador_inyectados() -> None:
    llamadas: list[tuple[str, str]] = []

    def comparar(a: str, b: str) -> int:
        llamadas.append((a, b))
        return comparar_utf16(a, b)

    dispositivos = listar_avfoundation(lambda: [MAC_OBS, MAC_INTEGRADA], comparar)
    assert [d.dispositivo_id for d in dispositivos] == [MAC_INTEGRADA[0], MAC_OBS[0]]
    assert llamadas


# ------------------------------------------------------------------ Windows


def test_directshow_en_orden_de_enumeracion_con_device_path() -> None:
    dispositivos = ordenar_directshow(
        [
            EntradaDirectShow(True, "HD Webcam C270", LOGITECH),
            EntradaDirectShow(True, "OBS Virtual Camera", None),
            EntradaDirectShow(True, "Microsoft LifeCam", MICROSOFT),
        ]
    )
    assert dispositivos == [
        Dispositivo(LOGITECH, "HD Webcam C270", 0, CAP_DSHOW),
        # No DevicePath (virtual camera): the name plus its occurrence.
        Dispositivo("OBS Virtual Camera#1", "OBS Virtual Camera", 1, CAP_DSHOW),
        Dispositivo(MICROSOFT, "Microsoft LifeCam", 2, CAP_DSHOW),
    ]


def test_directshow_sin_device_path_repetidos_se_numeran() -> None:
    dispositivos = ordenar_directshow(
        [EntradaDirectShow(True, "Virtual", None), EntradaDirectShow(True, "Virtual", "")]
    )
    assert [d.dispositivo_id for d in dispositivos] == ["Virtual#1", "Virtual#2"]


def test_directshow_cuenta_monikers_sin_nombre_pero_no_los_lista() -> None:
    # getDevice counts every moniker: the camera after a nameless one keeps index 1.
    dispositivos = ordenar_directshow(
        [EntradaDirectShow(True, None, "x"), EntradaDirectShow(True, "Cam", LOGITECH)]
    )
    assert [(d.dispositivo_id, d.indice) for d in dispositivos] == [(LOGITECH, 1)]


def test_directshow_moniker_que_no_enlaza_corre_el_limite_de_opencv() -> None:
    # listDevices counts 2 bindable monikers, so OpenCV rejects index 2 although getDevice
    # would reach it: that camera is not openable and is not listed.
    dispositivos = ordenar_directshow(
        [
            EntradaDirectShow(True, "A", LOGITECH),
            EntradaDirectShow(False, None, None),
            EntradaDirectShow(True, "B", MICROSOFT),
        ]
    )
    assert [(d.dispositivo_id, d.indice) for d in dispositivos] == [(LOGITECH, 0)]


def test_directshow_usa_las_entradas_inyectadas() -> None:
    dispositivos = listar_directshow(lambda: [EntradaDirectShow(True, " Cam ", LOGITECH)])
    assert dispositivos == [Dispositivo(LOGITECH, "Cam", 0, CAP_DSHOW)]


# ------------------------------------------------------------------ Linux


def _arbol_v4l(raiz: Path, camaras: dict[str, tuple[int, str | None]]) -> tuple[Path, Path]:
    """Fake /dev and /sys trees: ``{by-id name: (N of /dev/videoN, sysfs name)}``."""
    dev, sysfs = raiz / "dev", raiz / "sys" / "class" / "video4linux"
    por_id = dev / "v4l" / "by-id"
    por_id.mkdir(parents=True)
    sysfs.mkdir(parents=True)
    for nombre_enlace, (n, nombre) in camaras.items():
        nodo = dev / f"video{n}"
        nodo.touch()
        os.symlink(f"../../video{n}", por_id / nombre_enlace)
        if nombre is not None:
            (sysfs / f"video{n}").mkdir()
            (sysfs / f"video{n}" / "name").write_text(f"{nombre}\n", encoding="utf-8")
    return por_id, sysfs


def test_v4l2_lista_video_index0_ordenado_por_indice(tmp_path: Path) -> None:
    por_id, sysfs = _arbol_v4l(
        tmp_path,
        {
            "usb-Microsoft_LifeCam-video-index0": (2, "Microsoft® LifeCam"),
            "usb-Microsoft_LifeCam-video-index1": (3, "Microsoft® LifeCam"),  # metadata
            "usb-046d_0825_A1B2C3-video-index0": (0, "UVC Camera (046d:0825)"),
            "usb-046d_0825_A1B2C3-video-index1": (1, "UVC Camera (046d:0825)"),  # metadata
            "usb-Sin_Nombre-video-index0": (4, None),
        },
    )
    os.symlink("../../video9", por_id / "usb-Desenchufada-video-index0")  # dangling
    os.symlink("../../media0", por_id / "usb-Otra-media-index0")
    assert listar_v4l2(por_id, sysfs) == [
        Dispositivo("usb-046d_0825_A1B2C3-video-index0", "UVC Camera (046d:0825)", 0, CAP_V4L2),
        Dispositivo("usb-Microsoft_LifeCam-video-index0", "Microsoft® LifeCam", 2, CAP_V4L2),
        Dispositivo("usb-Sin_Nombre-video-index0", "usb-Sin_Nombre-video-index0", 4, CAP_V4L2),
    ]


def test_v4l2_sin_directorio_by_id_no_hay_camaras(tmp_path: Path) -> None:
    assert listar_v4l2(tmp_path / "no-existe", tmp_path) == []


# ------------------------------------------------------------------ ID stability


def test_el_id_sigue_a_la_camara_cuando_otra_se_enchufa_antes(tmp_path: Path) -> None:
    antes = tmp_path / "antes"
    por_id, sysfs = _arbol_v4l(antes, {"usb-Sala-video-index0": (0, "Sala")})
    sala = abrir_por_id("usb-Sala-video-index0", lambda: listar_v4l2(por_id, sysfs))
    assert sala is not None
    assert sala.indice == 0

    # After a reboot a new webcam takes /dev/video0 and the living-room one moves to video2.
    despues = tmp_path / "despues"
    por_id, sysfs = _arbol_v4l(
        despues,
        {"usb-Cocina-video-index0": (0, "Cocina"), "usb-Sala-video-index0": (2, "Sala")},
    )
    sala = abrir_por_id("usb-Sala-video-index0", lambda: listar_v4l2(por_id, sysfs))
    assert sala is not None
    assert (sala.indice, sala.nombre) == (2, "Sala")


def test_el_id_sigue_a_la_camara_en_macos_y_windows() -> None:
    nueva = ("0x0100000046d0826", "Otra webcam")
    assert ordenar_avfoundation([MAC_INTEGRADA])[0].indice == 0
    dispositivos = ordenar_avfoundation([MAC_INTEGRADA, nueva])
    resuelto = abrir_por_id(MAC_INTEGRADA[0], lambda: dispositivos)
    assert resuelto is not None
    assert resuelto.indice == 1

    entradas = [EntradaDirectShow(True, "Cam", LOGITECH)]
    assert ordenar_directshow(entradas)[0].indice == 0
    entradas.insert(0, EntradaDirectShow(True, "Nueva", MICROSOFT))
    resuelto = abrir_por_id(LOGITECH, lambda: ordenar_directshow(entradas))
    assert resuelto is not None
    assert resuelto.indice == 1


def test_abrir_por_id_desconocido_es_none() -> None:
    assert abrir_por_id("no-existe", lambda: ordenar_avfoundation([MAC_INTEGRADA])) is None


# ------------------------------------------------------------------ contract limits


def test_id_y_nombre_se_recortan_a_los_limites_del_contrato() -> None:
    largo_id, largo_nombre = "i" * 400, "n" * 150
    (dispositivo,) = ordenar_directshow([EntradaDirectShow(True, largo_nombre, largo_id)])
    assert len(dispositivo.dispositivo_id) == LARGO_MAX_ID == 300
    assert len(dispositivo.nombre) == LARGO_MAX_NOMBRE == 100
    # The stored (truncated) ID and the full one both resolve to the same device.
    assert abrir_por_id(dispositivo.dispositivo_id, lambda: [dispositivo]) == dispositivo
    assert abrir_por_id(largo_id, lambda: [dispositivo]) == dispositivo
    (mac,) = ordenar_avfoundation([(largo_id, largo_nombre)])
    assert (len(mac.dispositivo_id), len(mac.nombre)) == (300, 100)


# ------------------------------------------------------------------ dispatch


def test_listar_dispositivos_en_una_plataforma_desconocida_esta_vacio() -> None:
    assert listar_dispositivos("sunos5") == []


def test_listar_dispositivos_elige_el_backend_de_la_plataforma(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    modulo = "te_tengo_captura.captura.dispositivos"
    mac, win, linux = (Dispositivo(n, n, 0, 0) for n in ("mac", "win", "linux"))
    monkeypatch.setattr(f"{modulo}.listar_avfoundation", lambda: [mac])
    monkeypatch.setattr(f"{modulo}.listar_directshow", lambda: [win])
    monkeypatch.setattr(f"{modulo}.listar_v4l2", lambda: [linux])
    assert listar_dispositivos("darwin") == [mac]
    assert listar_dispositivos("win32") == [win]
    assert listar_dispositivos("linux") == [linux]


def test_importar_el_modulo_no_importa_librerias_del_sistema() -> None:
    import subprocess

    codigo = (
        "import sys, te_tengo_captura.captura.dispositivos as d; "
        "print([m for m in ('cv2', 'objc', 'AVFoundation', 'comtypes') if m in sys.modules])"
    )
    salida = subprocess.run(
        [sys.executable, "-c", codigo], capture_output=True, text=True, check=True
    )
    assert salida.stdout.strip() == "[]"


@pytest.mark.skipif(sys.platform != "darwin", reason="AVFoundation solo existe en macOS")
def test_listar_dispositivos_reales_en_macos() -> None:
    dispositivos = listar_dispositivos()
    assert isinstance(dispositivos, list)
    assert [d.indice for d in dispositivos] == sorted(d.indice for d in dispositivos)
    assert all(d.backend == CAP_AVFOUNDATION for d in dispositivos)


# ------------------------------------------------------------------ FuenteWebcamPorId


class CapturaFalsa:
    def __init__(self, abierta: bool = True) -> None:
        self.abierta = abierta
        self.liberada = False

    def isOpened(self) -> bool:  # noqa: N802
        return self.abierta

    def read(self) -> tuple[bool, Any]:
        if self.liberada:
            return False, None
        return True, np.zeros((2, 2, 3), dtype=np.uint8)

    def release(self) -> None:
        self.liberada = True


class Pc:
    """Fake PC: the plugged webcams and the captures OpenCV opened."""

    def __init__(self, enchufadas: Sequence[tuple[str, str]]) -> None:
        self.enchufadas = list(enchufadas)
        self.aperturas: list[tuple[int, int]] = []
        self.capturas: list[CapturaFalsa] = []
        self.abre = True

    def listar(self) -> list[Dispositivo]:
        return ordenar_avfoundation(self.enchufadas)

    def abrir_captura(self, indice: int, backend: int) -> CapturaFalsa:
        self.aperturas.append((indice, backend))
        self.capturas.append(CapturaFalsa(self.abre))
        return self.capturas[-1]


def test_fuente_abre_el_indice_actual_y_lee() -> None:
    pc = Pc([MAC_OBS, MAC_INTEGRADA])
    fuente = FuenteWebcamPorId(MAC_OBS[0], pc.listar, pc.abrir_captura, reloj=lambda: 4.5)
    assert fuente.leer() is None
    assert fuente.abrir()
    assert pc.aperturas == [(1, CAP_AVFOUNDATION)]
    assert fuente.dispositivo is not None
    assert fuente.dispositivo.nombre == "OBS Virtual Camera"
    lectura = fuente.leer()
    assert lectura is not None
    assert lectura[0] == 4.5
    fuente.cerrar()
    assert pc.capturas[0].liberada
    assert fuente.leer() is None


def test_fuente_desenchufada_no_abre_y_al_volver_abre_en_su_nuevo_indice() -> None:
    pc = Pc([MAC_INTEGRADA, MAC_OBS])
    fuente = FuenteWebcamPorId(MAC_OBS[0], pc.listar, pc.abrir_captura)
    assert fuente.abrir()
    assert pc.aperturas[-1] == (1, CAP_AVFOUNDATION)

    pc.enchufadas = [MAC_INTEGRADA]  # unplugged
    assert not fuente.abrir()
    assert pc.capturas[0].liberada  # abrir closes the previous capture first
    assert len(pc.aperturas) == 1  # never opened another camera's index

    pc.enchufadas = [MAC_OBS, MAC_INTEGRADA, MAC_USB]  # replugged, with a new one before it
    assert fuente.abrir()
    assert pc.aperturas[-1] == (2, CAP_AVFOUNDATION)
    assert fuente.leer() is not None


def test_fuente_no_abre_si_opencv_no_abre() -> None:
    pc = Pc([MAC_INTEGRADA])
    pc.abre = False
    fuente = FuenteWebcamPorId(MAC_INTEGRADA[0], pc.listar, pc.abrir_captura)
    assert not fuente.abrir()
    assert pc.capturas[0].liberada
    assert fuente.leer() is None


def test_fuente_no_abre_si_listar_falla(caplog: pytest.LogCaptureFixture) -> None:
    def listar() -> list[Dispositivo]:
        raise OSError("COM no disponible")

    fuente = FuenteWebcamPorId("x", listar, Pc([]).abrir_captura)
    assert not fuente.abrir()
    assert "No se pudo listar" in caplog.text


def test_fuente_lectura_fallida_es_none() -> None:
    pc = Pc([MAC_INTEGRADA])
    fuente = FuenteWebcamPorId(MAC_INTEGRADA[0], pc.listar, pc.abrir_captura)
    assert fuente.abrir()
    pc.capturas[0].liberada = True  # the camera stops delivering frames
    assert fuente.leer() is None
