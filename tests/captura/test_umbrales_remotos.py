import logging
import threading

import pytest

from te_tengo_captura.backend.cliente import ClienteBackend
from te_tengo_captura.backend.falso import URL_API, BackendFalso
from te_tengo_captura.umbrales_remotos import ActualizadorUmbrales, combinar
from te_tengo_deteccion.clasificacion.umbrales import Umbrales

LOCALES = Umbrales(velocidad_descenso_min=0.01)


def test_aplica_los_campos_validos() -> None:
    resultado = combinar(LOCALES, {"confirmacion_suelo_s": 20, "velocidad_descenso_min": 0.02})
    assert resultado.confirmacion_suelo_s == 20.0
    assert resultado.velocidad_descenso_min == 0.02
    assert resultado.angulo_linea_central_max_grados == 45.0  # missing: keeps the local value


def test_ignora_campos_desconocidos_y_valores_invalidos(caplog: pytest.LogCaptureFixture) -> None:
    resultado = combinar(
        LOCALES,
        {
            "campo_nuevo": 3,
            "angulo_linea_central_max_grados": 120,  # must be below 90
            "visibilidad_min": "alta",
            "confirmacion_suelo_s": 25,
        },
    )
    assert resultado == LOCALES.model_copy(update={"confirmacion_suelo_s": 25.0})
    assert "Umbral remoto desconocido ignorado: campo_nuevo" in caplog.text
    assert "angulo_linea_central_max_grados=120" in caplog.text
    assert "visibilidad_min='alta'" in caplog.text


def test_nunca_quita_el_umbral_de_velocidad(caplog: pytest.LogCaptureFixture) -> None:
    assert combinar(LOCALES, {"velocidad_descenso_min": None}) == LOCALES
    assert "no puede quedar sin valor" in caplog.text


@pytest.fixture
def backend() -> BackendFalso:
    return BackendFalso()


def actualizador(backend: BackendFalso, aplicados: list[Umbrales]) -> ActualizadorUmbrales:
    cliente = ClienteBackend(URL_API, backend.credencial, "Sala", "1.0.0", backend.transporte())
    return ActualizadorUmbrales(cliente, LOCALES, aplicados.append, "1.0.0")


def test_aplica_al_iniciar_y_solo_si_cambian(
    backend: BackendFalso, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO)
    aplicados: list[Umbrales] = []
    a = actualizador(backend, aplicados)
    assert a.actualizar()
    assert aplicados == []  # the backend has nothing different
    backend.umbrales = {"confirmacion_suelo_s": 20}
    backend.version_agente = "1.1.0"
    assert a.actualizar()
    assert a.actualizar()
    assert [u.confirmacion_suelo_s for u in aplicados] == [20.0]
    assert "Versión del agente publicada: 1.1.0" in caplog.text


def test_si_el_backend_deja_de_enviar_un_campo_vuelve_el_valor_local(backend: BackendFalso) -> None:
    aplicados: list[Umbrales] = []
    a = actualizador(backend, aplicados)
    backend.umbrales = {"confirmacion_suelo_s": 20}
    a.actualizar()
    backend.umbrales = {}
    a.actualizar()
    assert aplicados[-1] == LOCALES


def test_sin_conexion_conserva_los_vigentes(backend: BackendFalso) -> None:
    aplicados: list[Umbrales] = []
    a = actualizador(backend, aplicados)
    backend.sin_conexion = True
    assert not a.actualizar()
    assert a.vigentes == LOCALES


def test_hilo_aplica_al_iniciar(backend: BackendFalso) -> None:
    listo = threading.Event()
    aplicados: list[Umbrales] = []

    def aplicar(u: Umbrales) -> None:
        aplicados.append(u)
        listo.set()

    backend.umbrales = {"confirmacion_suelo_s": 20}
    cliente = ClienteBackend(URL_API, backend.credencial, "Sala", "1.0.0", backend.transporte())
    a = ActualizadorUmbrales(cliente, LOCALES, aplicar, "1.0.0")
    a.iniciar()
    assert listo.wait(5)
    a.detener()
