import sys
from datetime import UTC, datetime

import pytest
from PIL import Image

from te_tengo_captura.bandeja.avisos import Avisos
from te_tengo_captura.bandeja.iconos import MORADO, PUNTOS, icono
from te_tengo_captura.config import Configuracion
from te_tengo_captura.estado import Entradas, EstadoAgente, Notificacion, derivar
from tests.captura.ui.pystray_falso import PystrayFalso


def estado(configuracion: Configuracion, **cambios: object) -> EstadoAgente:
    base: dict[str, object] = {
        "webcam_conectada": True,
        "en_linea": True,
        "consentimiento": True,
        "pausada_hasta": None,
        "segundos_desde_envio": 2,
        "segundos_para_reintento": 8,
        "nombre_habitacion": "Sala",
    }
    return derivar(Entradas(**{**base, **cambios}), configuracion, "1.0.0")  # type: ignore[arg-type]


def _rgb(hexadecimal: str) -> tuple[int, int, int]:
    return tuple(int(hexadecimal[i : i + 2], 16) for i in (1, 3, 5))  # type: ignore[return-value]


def pixel(imagen: Image.Image, xy: tuple[int, int]) -> tuple[int, ...]:
    valor = imagen.getpixel(xy)
    assert isinstance(valor, tuple)
    return valor


def _cerca(a: tuple[int, ...], b: tuple[int, ...], tolerancia: int = 12) -> bool:
    return all(abs(x - y) <= tolerancia for x, y in zip(a, b, strict=False))


@pytest.mark.parametrize("punto", ["ok", "idle", "warn"])
def test_icono_con_el_punto_de_estado(punto: str) -> None:
    imagen = icono(punto, 64)
    assert imagen.size == (64, 64)
    assert imagen.mode == "RGBA"
    assert pixel(imagen, (0, 0))[3] == 0  # rounded corner: transparent
    assert _cerca(pixel(imagen, (10, 32))[:3], _rgb(MORADO))
    assert _cerca(pixel(imagen, (32, 21))[:3], _rgb("#FFB59C"))  # the dot of the symbol
    assert _cerca(pixel(imagen, (32, 44))[:3], (255, 255, 255))  # the stem
    assert _cerca(pixel(imagen, (54, 54))[:3], _rgb(PUNTOS[punto]))


def test_icono_sin_punto() -> None:
    assert _cerca(pixel(icono(None, 64), (54, 54))[:3], _rgb(MORADO))


def test_aviso_al_cerrar_solo_la_primera_vez(configuracion: Configuracion) -> None:
    avisos: list[Notificacion] = []
    a = Avisos(configuracion, avisos.append)
    a.ventana_oculta(estado(configuracion))
    a.ventana_mostrada()
    a.ventana_oculta(estado(configuracion))
    assert avisos == [
        Notificacion(
            "Te Tengo Captura sigue funcionando en segundo plano",
            "Sigue enviando el video de la cámara. Ábrelo desde su ícono, junto al reloj.",
        )
    ]


def test_aviso_de_webcam_desconectada_con_la_ventana_cerrada(configuracion: Configuracion) -> None:
    avisos: list[Notificacion] = []
    a = Avisos(configuracion, avisos.append)
    a.ventana_oculta(estado(configuracion))
    avisos.clear()
    a.estado(estado(configuracion, webcam_conectada=False))
    a.estado(estado(configuracion, webcam_conectada=False))  # not repeated every second
    assert [n.titulo for n in avisos] == ["La webcam se desconectó"]
    a.estado(estado(configuracion))
    a.estado(estado(configuracion, webcam_conectada=False))  # a new disconnection
    assert len(avisos) == 2


def test_sin_aviso_de_webcam_con_la_ventana_abierta(configuracion: Configuracion) -> None:
    avisos: list[Notificacion] = []
    a = Avisos(configuracion, avisos.append)
    a.estado(estado(configuracion, webcam_conectada=False))
    assert avisos == []


@pytest.fixture
def pystray(monkeypatch: pytest.MonkeyPatch) -> PystrayFalso:
    falso = PystrayFalso()
    monkeypatch.setitem(sys.modules, "pystray", falso)
    return falso


def test_icono_de_bandeja(pystray: PystrayFalso, configuracion: Configuracion) -> None:
    from te_tengo_captura.bandeja.icono import IconoBandeja

    llamadas: list[str] = []
    bandeja = IconoBandeja(lambda: llamadas.append("abrir"), lambda: llamadas.append("salir"))
    icono_ = pystray.iconos[0]
    assert icono_.menu is not None
    abrir, salir = icono_.menu.items
    assert (abrir.text, abrir.default) == ("Abrir Te Tengo Captura", True)
    assert salir.text == "Salir"
    abrir.accion()
    salir.accion()
    assert llamadas == ["abrir", "salir"]

    bandeja.iniciar()
    assert icono_.corriendo
    bandeja.actualizar(estado(configuracion))
    assert icono_.title == "Te Tengo Captura · enviando video de la cámara de la sala"
    imagen = icono_.icon
    bandeja.actualizar(estado(configuracion))
    assert icono_.icon is imagen  # not redrawn every second
    pausa = datetime(2026, 10, 7, 20, 0, tzinfo=UTC)
    bandeja.actualizar(estado(configuracion, pausada_hasta=pausa))
    assert icono_.icon is not imagen
    assert icono_.title.startswith("Te Tengo Captura · en pausa hasta las ")

    bandeja.notificar(Notificacion("La webcam se desconectó", "Revisa…"))
    assert icono_.notificaciones == [("La webcam se desconectó", "Revisa…")]
    bandeja.detener()
    assert not icono_.corriendo


def test_notificacion_fallida_no_rompe_nada(pystray: PystrayFalso) -> None:
    from te_tengo_captura.bandeja.icono import IconoBandeja

    bandeja = IconoBandeja(lambda: None, lambda: None)

    def fallar(mensaje: str, titulo: str | None = None) -> None:
        raise NotImplementedError

    pystray.iconos[0].notify = fallar  # type: ignore[method-assign]
    bandeja.notificar(Notificacion("t", "x"))
