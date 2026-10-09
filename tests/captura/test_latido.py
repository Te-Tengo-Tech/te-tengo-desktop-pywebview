import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from te_tengo_captura.backend.cliente import ClienteBackend
from te_tengo_captura.backend.falso import URL_API, BackendFalso
from te_tengo_captura.latido import HiloLatido, Latido, Salud

AHORA = datetime(2026, 10, 7, 14, 0, tzinfo=UTC)


class Relojes:
    def __init__(self) -> None:
        self.mono = 0.0
        self.utc = AHORA

    def avanzar(self, segundos: float) -> None:
        self.mono += segundos
        self.utc += timedelta(seconds=segundos)


class Escenario:
    def __init__(self, tmp_path: Path, credencial: str = "credencial-falsa") -> None:
        self.backend = BackendFalso()
        self.credencial = credencial
        self.relojes = Relojes()
        self.salud = Salud(webcam_conectada=True, deteccion_confiable=True)
        self.cambios = 0
        self.archivo = tmp_path / "estado_captura.json"
        self.latido = self.nuevo_latido()

    def nuevo_latido(self) -> Latido:
        cliente = ClienteBackend(
            URL_API, self.credencial, "Sala", "1.0.0", self.backend.transporte()
        )
        return Latido(
            cliente,
            lambda: self.salud,
            self.archivo,
            reloj=lambda: self.relojes.mono,
            reloj_utc=lambda: self.relojes.utc,
            al_cambiar=self._cambio,
        )

    def _cambio(self) -> None:
        self.cambios += 1


@pytest.fixture
def e(tmp_path: Path) -> Escenario:
    return Escenario(tmp_path)


def test_sin_estado_conocido_no_se_captura(e: Escenario) -> None:
    assert e.latido.en_linea is None
    assert not e.latido.captura_permitida()  # CA-05.2
    assert e.latido.sin_consentimiento()


def test_el_latido_envia_la_salud_y_aplica_el_estado(e: Escenario) -> None:
    e.salud = Salud(webcam_conectada=True, deteccion_confiable=False)
    e.latido.latir()
    assert e.backend.senales == [
        {"webcamConectada": True, "deteccionConfiable": False, "versionAgente": "1.0.0"}
    ]
    assert e.latido.en_linea
    assert e.latido.captura_permitida()
    assert e.latido.estado is not None
    assert e.latido.estado.nombre_habitacion == "Sala"
    assert e.latido.ultimo_contacto == AHORA
    assert e.cambios == 1


def test_late_cada_30_s(e: Escenario) -> None:
    e.latido.latir()
    e.relojes.avanzar(29)
    assert not e.latido.toca()
    e.relojes.avanzar(1)
    assert e.latido.toca()


def test_cambio_de_la_webcam_se_informa_enseguida(e: Escenario) -> None:
    e.latido.latir()
    e.relojes.avanzar(5)
    e.salud = Salud(webcam_conectada=False, deteccion_confiable=True)
    assert e.latido.toca()  # CA-07.2: no need to wait for missed heartbeats
    e.latido.latir()
    assert e.backend.senales[-1]["webcamConectada"] is False
    e.salud = Salud(webcam_conectada=True, deteccion_confiable=True)
    assert e.latido.toca()  # CA-07.3: back online at once


def test_la_respuesta_actualiza_pausa_y_nombre(e: Escenario) -> None:
    e.latido.latir()
    hasta = AHORA + timedelta(hours=1)
    e.backend.pausar(hasta)
    e.backend.nombre_habitacion = "Dormitorio"
    e.latido.latir()
    assert not e.latido.captura_permitida()
    assert e.latido.pausada_hasta() == hasta
    assert not e.latido.sin_consentimiento()
    assert e.latido.estado is not None
    assert e.latido.estado.nombre_habitacion == "Dormitorio"


def test_la_pausa_termina_sola_a_la_hora(e: Escenario) -> None:
    e.backend.pausar(AHORA + timedelta(minutes=10))
    e.latido.latir()
    assert not e.latido.captura_permitida()
    e.relojes.avanzar(600)  # CA-22.3, even before the next heartbeat answers
    assert e.latido.captura_permitida()
    assert e.latido.pausada_hasta() is None


def test_sin_consentimiento(e: Escenario) -> None:
    e.backend.quitar_consentimiento()
    e.latido.latir()
    assert not e.latido.captura_permitida()
    assert e.latido.sin_consentimiento()
    assert e.latido.pausada_hasta() is None


def test_sin_internet_reintenta_con_cuenta_regresiva(e: Escenario) -> None:
    e.latido.latir()
    e.backend.sin_conexion = True
    e.relojes.avanzar(30)
    esperas = []
    for _ in range(6):
        e.latido.latir()
        esperas.append(e.latido.segundos_para_reintento())
        e.relojes.avanzar(e.latido.espera())
    assert e.latido.en_linea is False
    assert esperas == [2, 4, 8, 16, 30, 30]
    # Capture keeps the last known state while offline.
    assert e.latido.captura_permitida()


def test_cuenta_regresiva_baja_con_el_tiempo(e: Escenario) -> None:
    e.backend.sin_conexion = True
    for _ in range(4):
        e.latido.latir()
    assert e.latido.segundos_para_reintento() == 16
    e.relojes.avanzar(7.5)
    assert e.latido.segundos_para_reintento() == 9
    assert not e.latido.toca()


def test_reintentar_ahora(e: Escenario) -> None:
    e.backend.sin_conexion = True
    e.latido.latir()
    e.backend.sin_conexion = False
    assert not e.latido.toca()
    e.latido.reintentar_ahora()
    assert e.latido.toca()
    e.latido.latir()
    assert e.latido.en_linea
    assert e.latido.segundos_para_reintento() == 0


def test_credencial_invalida_se_distingue(tmp_path: Path) -> None:
    e = Escenario(tmp_path, credencial="otra")
    e.latido.latir()
    assert e.latido.en_linea is False
    assert e.latido.credencial_invalida


def test_el_estado_sobrevive_a_un_reinicio_sin_internet(e: Escenario) -> None:
    e.backend.pausar(AHORA + timedelta(hours=2))
    e.latido.latir()
    e.backend.sin_conexion = True
    reiniciado = e.nuevo_latido()
    assert reiniciado.estado == e.latido.estado
    assert not reiniciado.captura_permitida()
    reiniciado.latir()
    assert reiniciado.en_linea is False
    assert reiniciado.pausada_hasta() == AHORA + timedelta(hours=2)


def test_estado_guardado_ilegible_se_ignora(e: Escenario) -> None:
    e.archivo.write_text("{no es json", encoding="utf-8")
    assert e.nuevo_latido().estado is None


def test_hilo_late_y_reintenta_ahora(e: Escenario) -> None:
    latio = threading.Event()
    e.latido._al_cambiar = latio.set
    hilo = HiloLatido(e.latido)
    hilo.iniciar()
    assert latio.wait(5)
    latio.clear()
    hilo.reintentar_ahora()
    assert latio.wait(5)
    hilo.detener()
    assert len(e.backend.senales) >= 2
