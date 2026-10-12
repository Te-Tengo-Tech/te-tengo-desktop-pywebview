import sys
from pathlib import Path

import pytest

from te_tengo_captura.config import Configuracion
from te_tengo_captura.ui.puente import Puente
from te_tengo_captura.ui.ventana import ALTO, ANCHO, WEB, VentanaEstado
from tests.captura.estados import estado as estado_de_ejemplo
from tests.captura.estados import ventana
from tests.captura.ui.pystray_falso import PystrayFalso
from tests.captura.ui.webview_falso import WebviewFalso


@pytest.fixture
def webview(monkeypatch: pytest.MonkeyPatch) -> WebviewFalso:
    falso = WebviewFalso()
    monkeypatch.setitem(sys.modules, "webview", falso)
    return falso


def puente() -> Puente:
    return Puente(lambda: {}, lambda: None, lambda: True, lambda: True)


def test_ventana_de_960_x_640_sin_marco_ni_cambio_de_tamano(webview: WebviewFalso) -> None:
    VentanaEstado(puente())
    ventana = webview.ventanas[0]
    assert ventana.titulo == "Te Tengo Captura"
    assert Path(ventana.url or "") == WEB / "index.html"
    assert (ventana.opciones["width"], ventana.opciones["height"]) == (ANCHO, ALTO) == (960, 640)
    assert ventana.opciones["resizable"] is False
    assert ventana.opciones["frameless"] is True
    assert ventana.opciones["easy_drag"] is False
    assert ventana.opciones["hidden"] is True


def test_cerrar_oculta_en_la_bandeja_sin_salir(webview: WebviewFalso) -> None:
    ocultada = []
    estado = VentanaEstado(puente(), al_ocultar=lambda: ocultada.append(True), oculta=False)
    ventana = webview.ventanas[0]
    assert ventana.events.closing.disparar() == [False]  # the close is cancelled
    assert not ventana.visible
    assert ocultada == [True]
    estado.mostrar()
    assert ventana.visible
    estado.destruir()
    assert ventana.events.closing.disparar() == [True]  # «Salir» really closes
    assert ventana.destruida


def test_actualiza_la_pagina_solo_cuando_cargo(
    webview: WebviewFalso, configuracion: Configuracion
) -> None:
    estado = VentanaEstado(puente())
    ventana = webview.ventanas[0]
    agente = estado_de_ejemplo()
    estado.actualizar(agente)
    assert ventana.scripts == []
    ventana.events.loaded.disparar()
    estado.actualizar(agente)
    assert ventana.scripts[0].startswith("window.ttg && window.ttg.actualizar(")


def test_ejecutar_abre_la_ventana_inicia_y_detiene_el_agente(
    webview: WebviewFalso,
    configuracion: Configuracion,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    pystray = PystrayFalso()
    monkeypatch.setitem(sys.modules, "pystray", pystray)
    from te_tengo_captura.actualizaciones.actualizador import Actualizador
    from te_tengo_captura.ui import arranque
    from te_tengo_captura.ui.aplicacion import ejecutar

    class AgenteFalso:
        version = "1.0.0"
        actualizador = Actualizador("1.0.0", tmp_path, lambda: None)

        def cambiar_actualizacion_automatica(self, activar: bool) -> bool:
            return activar

        def __init__(self) -> None:
            self.eventos: list[str] = []
            self.oyentes: list[object] = []

        config = configuracion

        def estado(self) -> object:
            return ventana(estado_de_ejemplo())

        def publicar_estado(self) -> None:
            self.eventos.append("publicar")

        def suscribir(self, oyente: object) -> None:
            self.oyentes.append(oyente)

        def iniciar(self) -> None:
            self.eventos.append("iniciar")

        def detener(self) -> None:
            self.eventos.append("detener")

        def buscar_webcam(self) -> bool:
            return True

        def reintentar_ahora(self) -> bool:
            return True

        def vista_previa_jpeg(self, clave: str) -> bytes | None:
            return None

        def otro_codigo(self) -> None: ...

        def vincular_de_nuevo(self) -> None: ...

        def ir_a_estado(self) -> None: ...

        def desvincular(self, borrar: bool) -> dict[str, bool]:
            return {"ok": False}

        def ambientes(self) -> list[dict[str, object]]:
            return []

        def usar_aqui(self, d: str, a: str | None, n: str | None) -> dict[str, object]:
            return {"ok": False}

        def dejar_de_usar(self, c: str) -> dict[str, object]:
            return {"ok": False}

        def cambiar_modo_avanzado(self, activar: bool) -> bool:
            return activar

        def registro(self, c: str, u: int) -> list[dict[str, object]]:
            return []

        def medidores(self, c: str) -> None:
            return None

        def lista_actividad(self) -> list[dict[str, object]]:
            return []

        def nombre_diagnostico(self) -> str:
            return "x.zip"

        def exportar_diagnostico(self, destino: Path) -> dict[str, object]:
            return {"ok": False}

        def cambiar_almacenamiento(self, cambios: dict[str, object]) -> dict[str, object]:
            return {"ok": True}

        def cambiar_carpeta(self, nueva: Path) -> dict[str, object]:
            return {"ok": True}

        def borrar_movimientos(self) -> dict[str, object]:
            return {"ok": True}

        def conservar_movimientos(self) -> dict[str, object]:
            return {"ok": True}

        def repeticion(self) -> dict[str, object]:
            return {"permitida": False, "camaras": []}

        def repeticion_ventana(self, c: str, d: int, h: int) -> dict[str, object]:
            return {}

        def repeticion_poses(self, c: str, d: int, h: int) -> dict[str, object]:
            return {}

        def repeticion_video(self, c: str, t: int) -> bytes | None:
            return None

        def cerrar_repeticion(self, c: str, d: int, h: int, s: float) -> dict[str, object]:
            return {"ok": True}

        def restablecer(self, motivo: str = "restablecida") -> dict[str, bool]:
            self.eventos.append(f"restablecer:{motivo}")
            return {"ok": True, "avisada": True}

    agente = AgenteFalso()
    pasos = [arranque.Paso(22, 0, lambda: True), arranque.Paso(100, 2, lambda: True)]
    monkeypatch.setattr(arranque, "pasos", lambda _: pasos)
    monkeypatch.setattr(arranque, "DURACION_MINIMA_S", 0.0)
    monkeypatch.setattr(arranque, "SALIDA_S", 0.0)
    ejecutar(agente)  # type: ignore[arg-type]
    assert webview.iniciado
    assert Path(webview.opciones["icon"]).is_file()  # window icon on Linux
    assert agente.eventos == ["iniciar", "publicar", "detener"]
    assert len(agente.oyentes) == 4  # window, tray icon, notifications and new versions
    inicio, estado = webview.ventanas
    assert inicio.destruida  # the splash gives way to the status window
    assert inicio.scripts[-1] == "window.ttg && window.ttg.arranqueFin()"
    assert estado.visible
    puente = estado.opciones["js_api"]
    assert puente.estado()["situacion"] == "cuidando"
    bandeja = pystray.iconos[0]
    assert not bandeja.corriendo  # stopped when the app ended
    puente.cerrar()
    assert not estado.visible
    assert bandeja.notificaciones == [
        (
            "Sigue funcionando en segundo plano",
            "Cuida la sala. Ábrelo junto al reloj.",
        )
    ]
    assert bandeja.menu is not None
    abrir, _descargar, _buscar, salir = bandeja.menu.items
    abrir.accion()
    assert estado.visible
    salir.accion()  # «Salir» stops fall detection: the window asks first
    assert not estado.destruida
    assert estado.scripts[-1] == 'window.ttg && window.ttg.accion("salir")'
    # «Desinstalar» from source: the reset happens, the app is not moved to the Trash.
    assert puente.desinstalar() == {"ok": True, "avisada": True, "papelera": False}
    assert agente.eventos[-1] == "restablecer:desinstalada"
    puente.salir()  # confirmed in the window
    assert estado.destruida


def test_la_app_de_mac_se_encuentra_desde_su_ejecutable(tmp_path: Path) -> None:
    from te_tengo_captura.ui.aplicacion import mover_a_la_papelera, paquete_de_la_app

    exe = "/Applications/Te Tengo Captura.app/Contents/MacOS/te-tengo-captura"
    assert paquete_de_la_app(exe) == Path("/Applications/Te Tengo Captura.app")
    assert paquete_de_la_app(str(tmp_path / "te-tengo-captura.exe")) is None
    assert paquete_de_la_app() is None  # from source
    assert mover_a_la_papelera(None) is False


def test_quita_los_plugins_qt_de_opencv() -> None:
    import os

    from te_tengo_captura.ui.aplicacion import quitar_qt_de_opencv

    cv2 = os.path.join("", "venv", "site-packages", "cv2", "qt", "plugins")
    entorno = {"QT_QPA_PLATFORM_PLUGIN_PATH": cv2, "QT_QPA_FONTDIR": cv2, "OTRA": "x"}
    quitar_qt_de_opencv(entorno)
    assert entorno == {"OTRA": "x"}
    propio = {"QT_QPA_PLATFORM_PLUGIN_PATH": os.path.join("", "opt", "qt", "plugins")}
    quitar_qt_de_opencv(propio)
    assert "QT_QPA_PLATFORM_PLUGIN_PATH" in propio


def test_el_icono_de_la_aplicacion_es_el_de_la_marca(tmp_path: Path) -> None:
    from PIL import Image

    from te_tengo_captura.bandeja.iconos import MORADO
    from te_tengo_captura.ui.aplicacion import guardar_icono

    with Image.open(guardar_icono(tmp_path)) as imagen:
        assert imagen.size == (512, 512)
        fondo = imagen.convert("RGB").getpixel((256, 480))  # below the stem: the purple square
    assert fondo == tuple(int(MORADO[i : i + 2], 16) for i in (1, 3, 5))
