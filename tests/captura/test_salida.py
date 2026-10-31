"""The bounded exit: no thread pywebview leaves behind keeps the process alive (salida.py)."""

import logging
import threading
from collections.abc import Callable

import pytest

from te_tengo_captura.salida import Salida, describir_hilos, hilos_pendientes


def _solo(*hilos: threading.Thread) -> Callable[[], list[threading.Thread]]:
    """Only this test's threads (another test may have left one behind)."""
    return lambda: [h for h in hilos_pendientes() if h in hilos]


def _hilo_atascado(liberar: threading.Event, nombre: str = "atascado") -> threading.Thread:
    # What pywebview's bridge thread does once the window is gone: wait for an answer forever.
    hilo = threading.Thread(target=liberar.wait, name=nombre, daemon=False)
    hilo.start()
    return hilo


def test_los_hilos_pendientes_son_los_que_no_son_daemon() -> None:
    liberar = threading.Event()
    atascado = _hilo_atascado(liberar)
    daemon = threading.Thread(target=liberar.wait, name="daemon", daemon=True)
    daemon.start()
    try:
        pendientes = hilos_pendientes()
        assert atascado in pendientes
        assert daemon not in pendientes
        assert threading.main_thread() not in pendientes
        assert threading.current_thread() not in pendientes
        assert "atascado" in describir_hilos([atascado])
    finally:
        liberar.set()
        atascado.join()


def test_terminar_no_fuerza_nada_si_ningun_hilo_queda() -> None:
    forzadas: list[int] = []
    Salida(gracia_s=0.0, forzar=forzadas.append, pendientes=_solo()).terminar(0)
    assert forzadas == []


def test_terminar_espera_un_hilo_que_termina_a_tiempo() -> None:
    forzadas: list[int] = []
    liberar = threading.Event()
    hilo = _hilo_atascado(liberar)
    threading.Timer(0.05, liberar.set).start()
    Salida(gracia_s=5.0, forzar=forzadas.append, pendientes=_solo(hilo)).terminar(0)
    assert not hilo.is_alive()
    assert forzadas == []


def test_terminar_no_espera_para_siempre_a_un_hilo_atascado(
    caplog: pytest.LogCaptureFixture,
) -> None:
    forzadas: list[int] = []
    liberar = threading.Event()
    hilo = _hilo_atascado(liberar, "Thread-21 (_call)")
    salida = Salida(gracia_s=0.05, forzar=forzadas.append, pendientes=_solo(hilo))
    salida.vigilar()
    salida.detener_vigilancia()
    try:
        with caplog.at_level(logging.INFO, logger="te_tengo_captura.salida"):
            salida.terminar(0)
        assert forzadas == [0]  # the process ends at once (os._exit) instead of hanging
        assert "Thread-21 (_call)" in caplog.text
        assert "Salida completa en" in caplog.text
    finally:
        liberar.set()
        hilo.join()


def test_la_vigilancia_cierra_el_programa_si_la_salida_se_atasca(
    caplog: pytest.LogCaptureFixture,
) -> None:
    forzado = threading.Event()
    codigos: list[int] = []

    def forzar(codigo: int) -> None:
        codigos.append(codigo)
        forzado.set()

    salida = Salida(limite_s=0.05, forzar=forzar)
    with caplog.at_level(logging.ERROR, logger="te_tengo_captura.salida"):
        salida.vigilar()
        salida.vigilar()  # idempotent: one watchdog
        assert forzado.wait(5)
    assert codigos == [1]
    assert "La salida tardó más de" in caplog.text
    assert "MainThread" in caplog.text  # every thread's stack, to find what got stuck


def test_la_vigilancia_no_hace_nada_si_el_programa_ya_termino() -> None:
    forzadas: list[int] = []
    salida = Salida(limite_s=0.05, forzar=forzadas.append)
    assert not salida.iniciada
    salida.vigilar()
    assert salida.iniciada
    salida.detener_vigilancia()
    threading.Event().wait(0.15)
    assert forzadas == []
