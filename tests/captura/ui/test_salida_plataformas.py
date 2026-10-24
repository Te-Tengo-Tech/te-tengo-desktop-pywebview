"""The quit paths of each platform, with the GUI layers replaced (macos.py, windows.py)."""

import sys
import threading
from collections.abc import Callable
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

from te_tengo_captura.ui import macos, windows

CMD = 1 << 20  # NSEventModifierFlagCommand


class Selector:
    def __init__(
        self, funcion: Callable[..., Any], selector: bytes = b"", signature: bytes = b""
    ) -> None:
        self.callable, self.selector, self.signature = funcion, selector, signature


class Evento:
    def __init__(self, modificadores: int, caracteres: str) -> None:
        self._m, self._c = modificadores, caracteres

    def modifierFlags(self) -> int:  # noqa: N802 (AppKit name)
        return self._m

    def charactersIgnoringModifiers(self) -> str:  # noqa: N802 (AppKit name)
        return self._c


@pytest.fixture
def cocoa(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """AppKit, objc, PyObjCTools and pywebview's Cocoa classes, recording what is replaced."""
    teclas: list[object] = []
    respuestas: list[bool] = []
    en_principal: list[Callable[..., Any]] = []

    def tecla_original(_vista: object, evento: object) -> None:
        teclas.append(evento)

    class AppDelegate:
        applicationShouldTerminate_ = Selector(  # noqa: N815 (AppKit name)
            lambda _s, _a: 1, b"applicationShouldTerminate:", b"I@:@"
        )

    class WebKitHost:
        keyDown_ = Selector(  # noqa: N815 (AppKit name)
            tecla_original, b"keyDown:", b"v@:@"
        )

    reemplazos: dict[bytes, Callable[..., Any]] = {}

    def class_add_methods(_clase: type, metodos: list[Selector]) -> None:
        for metodo in metodos:
            reemplazos[metodo.selector] = metodo.callable

    app = SimpleNamespace(replyToApplicationShouldTerminate_=respuestas.append)
    appkit = ModuleType("AppKit")
    appkit.NSCommandKeyMask = CMD  # type: ignore[attr-defined]
    appkit.NSApplication = SimpleNamespace(sharedApplication=lambda: app)  # type: ignore[attr-defined]
    objc = ModuleType("objc")
    objc.classAddMethods = class_add_methods  # type: ignore[attr-defined]
    objc.selector = Selector  # type: ignore[attr-defined]
    ayuda = ModuleType("PyObjCTools.AppHelper")

    def call_after(funcion: Callable[..., Any], *argumentos: Any) -> None:
        en_principal.append(funcion)
        funcion(*argumentos)

    ayuda.callAfter = call_after  # type: ignore[attr-defined]
    herramientas = ModuleType("PyObjCTools")
    herramientas.AppHelper = ayuda  # type: ignore[attr-defined]
    plataforma = ModuleType("webview.platforms.cocoa")
    plataforma.BrowserView = SimpleNamespace(  # type: ignore[attr-defined]
        AppDelegate=AppDelegate, WebKitHost=WebKitHost
    )
    for nombre, modulo in {
        "AppKit": appkit,
        "objc": objc,
        "PyObjCTools": herramientas,
        "PyObjCTools.AppHelper": ayuda,
        "webview": ModuleType("webview"),
        "webview.platforms": ModuleType("webview.platforms"),
        "webview.platforms.cocoa": plataforma,
    }.items():
        monkeypatch.setitem(sys.modules, nombre, modulo)
    return SimpleNamespace(
        reemplazos=reemplazos, teclas=teclas, respuestas=respuestas, en_principal=en_principal
    )


def _esperar(evento: threading.Event) -> None:
    assert evento.wait(5)


def test_mac_salir_del_menu_o_del_dock_pregunta_primero(
    cocoa: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    pedida, apagada = threading.Event(), threading.Event()
    monkeypatch.setattr(macos, "razon_actual", lambda: None)  # Cmd+Q in the menu, Dock «Quit»
    macos.interceptar_salida(pedida.set, apagada.set, lambda: False)
    terminar = cocoa.reemplazos[b"applicationShouldTerminate:"]
    assert terminar(object(), object()) == macos.NS_TERMINATE_CANCEL  # the app keeps running
    _esperar(pedida)  # and the window asks «¿Salir de Te Tengo Captura?»
    assert not apagada.is_set()
    assert cocoa.respuestas == []


def test_mac_cerrar_sesion_o_apagar_sale_sin_preguntar(
    cocoa: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    pedida = threading.Event()
    apagados: list[bool] = []
    monkeypatch.setattr(macos, "razon_actual", lambda: macos._codigo("shut"))
    macos.interceptar_salida(pedida.set, lambda: apagados.append(True), lambda: False)
    terminar = cocoa.reemplazos[b"applicationShouldTerminate:"]
    assert terminar(object(), object()) == macos.NS_TERMINATE_LATER
    for _ in range(500):
        if cocoa.respuestas:
            break
        threading.Event().wait(0.01)
    assert apagados == [True]  # the agent stopped first
    assert cocoa.respuestas == [True]  # then the app terminates and the shutdown goes on
    assert not pedida.is_set()


def test_mac_cmd_q_en_la_pagina_pregunta_y_las_otras_teclas_siguen(
    cocoa: SimpleNamespace,
) -> None:
    pedida = threading.Event()
    macos.interceptar_salida(pedida.set, lambda: None, lambda: False)
    tecla = cocoa.reemplazos[b"keyDown:"]
    copiar = Evento(CMD, "c")
    tecla(object(), copiar)
    assert cocoa.teclas == [copiar]  # pywebview's own Cmd+C still copies
    tecla(object(), Evento(CMD, "Q"))
    _esperar(pedida)
    assert cocoa.teclas == [copiar]  # pywebview no longer stops the main loop without asking


def test_mac_saliendo_no_vuelve_a_preguntar(
    cocoa: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    pedidas: list[bool] = []
    monkeypatch.setattr(macos, "razon_actual", lambda: None)
    macos.interceptar_salida(lambda: pedidas.append(True), lambda: None, lambda: True)
    assert cocoa.reemplazos[b"applicationShouldTerminate:"](object(), object()) == 0
    cocoa.reemplazos[b"keyDown:"](object(), Evento(CMD, "q"))
    threading.Event().wait(0.05)
    assert pedidas == []


def test_mac_razones_de_salida() -> None:
    assert macos.decidir(None) == macos.NS_TERMINATE_CANCEL
    for razon in ("logo", "rlgo", "rrst", "rsdn", "rest", "shut"):
        assert macos.decidir(macos._codigo(razon)) == macos.NS_TERMINATE_LATER
    assert macos._codigo("why?") == macos.RAZON_DE_SALIDA == 0x7768793F
    assert macos.es_cmd_q(CMD, "q", CMD)
    assert not macos.es_cmd_q(0, "q", CMD)
    assert not macos.es_cmd_q(CMD, "w", CMD)
    assert not macos.es_cmd_q(CMD, None, CMD)


class FormularioFalso:
    def __init__(self) -> None:
        self.manejadores: list[Callable[[object, Any], None]] = []

    @property
    def FormClosing(self) -> "FormularioFalso":  # noqa: N802 (WinForms name)
        return self

    @FormClosing.setter
    def FormClosing(self, _valor: object) -> None:  # noqa: N802 (WinForms name)
        pass

    def __iadd__(self, manejador: Callable[[object, Any], None]) -> "FormularioFalso":
        self.manejadores.append(manejador)
        return self

    def cerrar(self, razon: str, cancelada_por_pywebview: bool = True) -> bool:
        """Runs the handlers as WinForms does; ``True`` if the form closes."""
        argumentos = SimpleNamespace(CloseReason=razon, Cancel=cancelada_por_pywebview)
        for manejador in self.manejadores:
            manejador(self, argumentos)
        return not argumentos.Cancel


@pytest.fixture
def winforms(monkeypatch: pytest.MonkeyPatch) -> FormularioFalso:
    formulario = FormularioFalso()
    plataforma = ModuleType("webview.platforms.winforms")
    plataforma.BrowserView = SimpleNamespace(instances={"master": formulario})  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "webview", ModuleType("webview"))
    monkeypatch.setitem(sys.modules, "webview.platforms", ModuleType("webview.platforms"))
    monkeypatch.setitem(sys.modules, "webview.platforms.winforms", plataforma)
    return formulario


def test_windows_apagar_cierra_la_ventana_y_sale(winforms: FormularioFalso) -> None:
    apagados: list[bool] = []
    assert windows.permitir_apagado(SimpleNamespace(uid="master"), lambda: apagados.append(True))
    # pywebview's handler hid the window and cancelled the close; ours lets it close.
    assert winforms.cerrar("WindowsShutDown")
    assert winforms.cerrar("TaskManagerClosing")
    assert apagados == [True, True]


def test_windows_cerrar_la_ventana_la_oculta_en_la_bandeja(winforms: FormularioFalso) -> None:
    apagados: list[bool] = []
    windows.permitir_apagado(SimpleNamespace(uid="master"), lambda: apagados.append(True))
    assert not winforms.cerrar("UserClosing")  # Alt+F4: still hidden to the tray
    assert apagados == []


def test_windows_sin_winforms_no_hace_nada(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "webview.platforms.winforms", None)
    assert not windows.permitir_apagado(SimpleNamespace(uid="master"), lambda: None)


def test_windows_sin_la_ventana_no_hace_nada(winforms: FormularioFalso) -> None:
    assert not windows.permitir_apagado(SimpleNamespace(uid="otra"), lambda: None)
