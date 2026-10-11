import sys
from datetime import UTC, datetime
from typing import Any

import pytest
from PIL import Image

from te_tengo_captura.bandeja.avisos import Avisos
from te_tengo_captura.bandeja.iconos import CORAL, MORADO, PUNTOS, icono, poligono
from te_tengo_captura.coordinador import EstadoVentana, Pantalla
from te_tengo_captura.estado import EstadoBandeja, Notificacion
from tests.captura.estados import camara, ventana
from tests.captura.estados import estado as estado_de
from tests.captura.ui.pystray_falso import PystrayFalso

PAUSA = datetime(2026, 10, 7, 20, 0, tzinfo=UTC)
VIVO = datetime(2026, 10, 7, 19, 0, tzinfo=UTC)


def estado(**cambios: Any) -> EstadoVentana:
    return ventana(estado_de(camara(**cambios)))


def _rgb(hexadecimal: str) -> tuple[int, int, int]:
    return tuple(int(hexadecimal[i : i + 2], 16) for i in (1, 3, 5))  # type: ignore[return-value]


def pixel(imagen: Image.Image, xy: tuple[int, int]) -> tuple[int, ...]:
    valor = imagen.getpixel(xy)
    assert isinstance(valor, tuple)
    return valor


def _cerca(a: tuple[int, ...], b: tuple[int, ...], tolerancia: int = 12) -> bool:
    return all(abs(x - y) <= tolerancia for x, y in zip(a, b, strict=False))


@pytest.mark.parametrize("punto", ["ok", "idle", "warn", "live"])
def test_icono_con_el_punto_de_estado(punto: str) -> None:
    imagen = icono(punto, 64)
    assert imagen.size == (64, 64)
    assert imagen.mode == "RGBA"
    assert pixel(imagen, (0, 0))[3] == 0  # rounded corner: transparent
    assert _cerca(pixel(imagen, (6, 32))[:3], _rgb(MORADO))
    assert _cerca(pixel(imagen, (27, 18))[:3], (255, 255, 255))  # the hugging figure's head
    assert _cerca(pixel(imagen, (39, 24))[:3], _rgb(CORAL))  # the hugged figure's head
    assert _cerca(pixel(imagen, (54, 54))[:3], _rgb(PUNTOS[punto]))


def test_icono_sin_vincular_lleva_un_anillo_vacio() -> None:
    imagen = icono("off", 64)
    assert _cerca(pixel(imagen, (54, 54))[:3], (255, 255, 255))
    assert _cerca(pixel(imagen, (54, 43))[:3], _rgb("#8E879C"), tolerancia=20)


def test_icono_sin_punto() -> None:
    assert _cerca(pixel(icono(None, 64), (54, 54))[:3], _rgb(MORADO))


def test_las_curvas_del_simbolo_se_aplanan() -> None:
    puntos = poligono("M0 0 C0 10 10 10 10 0Z", pasos=4)
    assert puntos[0] == (0.0, 0.0)
    assert puntos[-1] == (10.0, 0.0)
    assert len(puntos) == 5
    assert puntos[2] == (5.0, 7.5)  # the middle of the cubic


def test_aviso_al_cerrar_solo_la_primera_vez() -> None:
    avisos: list[Notificacion] = []
    a = Avisos(avisos.append)
    a.ventana_oculta(estado())
    a.ventana_mostrada()
    a.ventana_oculta(estado())
    assert avisos == [
        Notificacion(
            "Sigue funcionando en segundo plano",
            "Cuida la sala. Ábrelo junto al reloj.",
        )
    ]


def test_aviso_de_camara_desconectada_con_la_ventana_cerrada() -> None:
    avisos: list[Notificacion] = []
    a = Avisos(avisos.append)
    a.ventana_oculta(estado())
    avisos.clear()
    a.estado(estado(webcam_conectada=False))
    a.estado(estado(webcam_conectada=False))  # not repeated every second
    assert [n.titulo for n in avisos] == ["La cámara de la sala no responde"]
    a.estado(estado())
    a.estado(estado(webcam_conectada=False))  # a new disconnection
    assert len(avisos) == 2


def test_aviso_de_vista_en_vivo_con_la_ventana_cerrada() -> None:
    avisos: list[Notificacion] = []
    a = Avisos(avisos.append)
    a.ventana_oculta(estado())
    avisos.clear()
    a.estado(estado(en_vivo_desde=VIVO))
    a.estado(estado(en_vivo_desde=VIVO))
    assert avisos == [
        Notificacion(
            "Un familiar está viendo la sala en vivo",
            "No se graba · queda registrado.",
        )
    ]


def test_sin_avisos_con_la_ventana_abierta() -> None:
    avisos: list[Notificacion] = []
    a = Avisos(avisos.append)
    a.estado(estado(webcam_conectada=False))
    a.estado(estado(en_vivo_desde=VIVO))
    assert avisos == []


@pytest.fixture
def pystray(monkeypatch: pytest.MonkeyPatch) -> PystrayFalso:
    falso = PystrayFalso()
    monkeypatch.setitem(sys.modules, "pystray", falso)
    return falso


def test_icono_de_bandeja(pystray: PystrayFalso) -> None:
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
    bandeja.actualizar(estado())
    assert icono_.title == "Te Tengo Captura · cuidando la sala"
    imagen = icono_.icon
    bandeja.actualizar(estado())
    assert icono_.icon is imagen  # not redrawn every second
    bandeja.actualizar(estado(pausada_hasta=PAUSA))
    assert icono_.icon is not imagen
    assert icono_.title.startswith("Te Tengo Captura · la sala en pausa hasta las ")

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


def test_en_macos_la_bandeja_se_actualiza_en_el_hilo_principal(
    pystray: PystrayFalso, monkeypatch: pytest.MonkeyPatch
) -> None:
    from types import ModuleType

    from te_tengo_captura.bandeja.icono import IconoBandeja

    pendientes: list[object] = []
    apphelper = ModuleType("PyObjCTools.AppHelper")
    apphelper.callAfter = pendientes.append  # type: ignore[attr-defined]
    paquete = ModuleType("PyObjCTools")
    paquete.AppHelper = apphelper  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "PyObjCTools", paquete)
    monkeypatch.setitem(sys.modules, "PyObjCTools.AppHelper", apphelper)
    monkeypatch.setattr("te_tengo_captura.bandeja.icono.EN_MACOS", True)

    bandeja = IconoBandeja(lambda: None, lambda: None)
    bandeja.actualizar(estado())
    bandeja.notificar(Notificacion("t", "x"))

    icono_ = pystray.iconos[0]
    assert icono_.title == "Te Tengo Captura"  # nothing touched outside the main thread
    assert len(pendientes) == 2
    for accion in pendientes:
        accion()  # type: ignore[operator]
    assert icono_.title.startswith("Te Tengo Captura · cuidando")
    assert icono_.notificaciones == [("t", "x")]


def test_avisos_antes_de_vincular_y_al_quitar_la_pc() -> None:
    avisos: list[Notificacion] = []
    a = Avisos(avisos.append)
    sin_vincular = EstadoVentana(
        Pantalla.VINCULAR, EstadoBandeja("off", "sin vincular"), None, {"screen": "vincular"}
    )
    a.ventana_oculta(sin_vincular)
    assert avisos[-1].texto == "Ábrelo junto al reloj para vincular esta PC."
    quitada = EstadoVentana(
        Pantalla.QUITADA,
        EstadoBandeja("off", "se quitó de la vivienda"),
        None,
        {"screen": "quitada", "who": "Rosa Huamán", "at": "11:20"},
        quitada=True,
    )
    a.estado(estado())
    a.estado(quitada)
    a.estado(quitada)  # once
    assert avisos[-1] == Notificacion(
        "Esta PC se quitó de la vivienda",
        "La familia la quitó a las 11:20. Ábrela para vincularla de nuevo.",
    )
    assert len(avisos) == 2
