import threading
from datetime import UTC, datetime
from pathlib import Path

import pytest

from te_tengo_captura.backend.cliente import ClienteBackend
from te_tengo_captura.backend.falso import URL_API, BackendFalso
from te_tengo_captura.backend.modelos import EventoAgente
from te_tengo_captura.envios.cola import (
    ESPERA_MAXIMA_S,
    MAX_INTENTOS_CLIP,
    ColaEnvios,
    EnviadorPendientes,
    Resumen,
)
from te_tengo_deteccion.clasificacion.estados import TipoEvento


class Reloj:
    def __init__(self) -> None:
        self.ahora = 1_000.0

    def __call__(self) -> float:
        return self.ahora


@pytest.fixture
def reloj() -> Reloj:
    return Reloj()


@pytest.fixture
def backend() -> BackendFalso:
    return BackendFalso()


@pytest.fixture
def cliente(backend: BackendFalso) -> ClienteBackend:
    return ClienteBackend(URL_API, backend.credencial, "Sala", "1.0.0", backend.transporte())


@pytest.fixture
def cola(tmp_path: Path, reloj: Reloj) -> ColaEnvios:
    return ColaEnvios(tmp_path, reloj=reloj, aleatorio=lambda: 1.0)


def evento(n: int, tipo: TipoEvento = TipoEvento.CAIDA) -> EventoAgente:
    return EventoAgente(
        evento_id=f"0192f6e4-0000-7000-8000-{n:012d}",
        tipo=tipo,
        ocurrido_en=datetime(2026, 10, 7, 15, 0, n, tzinfo=UTC),
        parametros={"angulo_grados": 20.0},
    )


def test_sin_conexion_y_luego_en_linea_entrega_en_orden(
    cola: ColaEnvios, cliente: ClienteBackend, backend: BackendFalso, reloj: Reloj
) -> None:
    backend.sin_conexion = True
    for n in range(1, 4):
        cola.agregar_evento(evento(n))
    resumen = cola.enviar(cliente)
    assert resumen.error is not None
    assert resumen.error.reintentable
    assert resumen.pendientes == 3
    assert backend.eventos == {}

    backend.sin_conexion = False
    reloj.ahora += cola.espera()
    resumen = cola.enviar(cliente)
    assert (resumen.eventos_enviados, resumen.pendientes, resumen.error) == (3, 0, None)
    assert list(backend.eventos) == [evento(n).evento_id for n in range(1, 4)]
    assert cola.ultimo_envio == reloj.ahora


def test_respuesta_duplicada_cuenta_como_entregada(
    cola: ColaEnvios, cliente: ClienteBackend, backend: BackendFalso
) -> None:
    cliente.publicar_evento(evento(1))  # the first attempt arrived, but its answer was lost
    cola.agregar_evento(evento(1))
    resumen = cola.enviar(cliente)
    assert (resumen.eventos_enviados, resumen.pendientes) == (1, 0)
    assert len(backend.eventos) == 1


def test_el_mismo_evento_no_se_encola_dos_veces(cola: ColaEnvios) -> None:
    cola.agregar_evento(evento(1))
    cola.agregar_evento(evento(1))
    assert cola.eventos_pendientes() == [evento(1).evento_id]


def test_sobrevive_a_un_reinicio(
    tmp_path: Path, reloj: Reloj, cliente: ClienteBackend, backend: BackendFalso
) -> None:
    primera = ColaEnvios(tmp_path, reloj=reloj)
    primera.agregar_evento(evento(1))
    primera.agregar_evento(evento(2))
    primera.agregar_clip(evento(1).evento_id, b"mp4-1")
    primera.cerrar()

    segunda = ColaEnvios(tmp_path, reloj=reloj)
    assert segunda.eventos_pendientes() == [evento(1).evento_id, evento(2).evento_id]
    assert segunda.clips_pendientes() == [evento(1).evento_id]
    resumen = segunda.enviar(cliente)
    assert (resumen.eventos_enviados, resumen.clips_subidos) == (2, 1)
    assert backend.clips[evento(1).evento_id].contenido == b"mp4-1"


def test_el_clip_se_borra_tras_subirlo(
    tmp_path: Path, cola: ColaEnvios, cliente: ClienteBackend
) -> None:
    cola.agregar_evento(evento(1))
    cola.agregar_clip(evento(1).evento_id, b"mp4")
    archivo = tmp_path / "clips" / f"{evento(1).evento_id}.mp4"
    assert archivo.read_bytes() == b"mp4"
    cola.enviar(cliente)
    assert not archivo.exists()
    assert cola.clips_pendientes() == []


def test_el_clip_espera_a_su_evento(
    cola: ColaEnvios, cliente: ClienteBackend, backend: BackendFalso, reloj: Reloj
) -> None:
    cola.agregar_evento(evento(1))
    cola.agregar_clip(evento(1).evento_id, b"mp4")
    backend.fallos = [503]
    resumen = cola.enviar(cliente)
    assert (resumen.eventos_enviados, resumen.clips_subidos, resumen.pendientes) == (0, 0, 2)
    reloj.ahora += cola.espera()
    assert cola.enviar(cliente).clips_subidos == 1


def test_la_espera_crece_con_tope_y_se_reinicia(
    cola: ColaEnvios, cliente: ClienteBackend, backend: BackendFalso, reloj: Reloj
) -> None:
    cola.agregar_evento(evento(1))
    backend.sin_conexion = True
    esperas = []
    for _ in range(10):
        cola.enviar(cliente)
        esperas.append(cola.espera())
        reloj.ahora += cola.espera()
    # aleatorio = 1.0 → the full wait of each step: 2, 4, 8 … up to the cap.
    assert esperas[:4] == [2.0, 4.0, 8.0, 16.0]
    assert esperas[-1] == ESPERA_MAXIMA_S
    backend.sin_conexion = False
    cola.enviar(cliente)
    assert cola.espera() == 0.0


def test_jitter_espera_entre_la_mitad_y_el_total(
    tmp_path: Path, reloj: Reloj, cliente: ClienteBackend, backend: BackendFalso
) -> None:
    cola = ColaEnvios(tmp_path, reloj=reloj, aleatorio=lambda: 0.0)
    cola.agregar_evento(evento(1))
    backend.sin_conexion = True
    cola.enviar(cliente)
    assert cola.espera() == 1.0  # half of 2 s


def test_no_reintenta_antes_de_tiempo_salvo_reintentar_ahora(
    cola: ColaEnvios, cliente: ClienteBackend, backend: BackendFalso
) -> None:
    cola.agregar_evento(evento(1))
    backend.sin_conexion = True
    cola.enviar(cliente)
    backend.sin_conexion = False
    intentos = len(backend.solicitudes)
    assert cola.enviar(cliente).eventos_enviados == 0
    assert len(backend.solicitudes) == intentos
    cola.reintentar_ahora()
    assert cola.enviar(cliente).eventos_enviados == 1


def test_evento_rechazado_no_bloquea_la_cola_y_su_clip_se_descarta(
    tmp_path: Path, cola: ColaEnvios, cliente: ClienteBackend, backend: BackendFalso
) -> None:
    backend.quitar_consentimiento()
    cola.agregar_evento(evento(1))
    cola.agregar_clip(evento(1).evento_id, b"mp4")
    resumen = cola.enviar(cliente)
    assert resumen.error is None
    assert cola.eventos_rechazados() == [evento(1).evento_id]
    assert cola.clips_pendientes() == []
    assert not (tmp_path / "clips" / f"{evento(1).evento_id}.mp4").exists()

    backend.permitir()
    cola.agregar_evento(evento(2))
    assert cola.enviar(cliente).eventos_enviados == 1


def test_clip_sin_evento_en_el_backend_se_descarta(
    cola: ColaEnvios, cliente: ClienteBackend
) -> None:
    cola.agregar_clip("desconocido", b"mp4")
    resumen = cola.enviar(cliente)
    assert (resumen.clips_subidos, resumen.pendientes) == (0, 0)


def test_clip_se_descarta_tras_varios_fallos(
    cola: ColaEnvios, cliente: ClienteBackend, backend: BackendFalso, reloj: Reloj
) -> None:
    cola.agregar_evento(evento(1))
    cola.enviar(cliente)
    cola.agregar_clip(evento(1).evento_id, b"mp4")
    for _ in range(MAX_INTENTOS_CLIP):
        backend.fallos = [503]
        reloj.ahora += cola.espera()
        cola.enviar(cliente)
    assert cola.clips_pendientes() == []
    assert backend.clips == {}


def test_clip_sin_archivo_se_descarta(
    tmp_path: Path, cola: ColaEnvios, cliente: ClienteBackend
) -> None:
    cola.agregar_clip("e", b"mp4")
    (tmp_path / "clips" / "e.mp4").unlink()
    cola.enviar(cliente)
    assert cola.clips_pendientes() == []


def test_borra_archivos_de_clip_huerfanos_al_iniciar(tmp_path: Path, reloj: Reloj) -> None:
    (tmp_path / "clips").mkdir()
    (tmp_path / "clips" / "huerfano.mp4").write_bytes(b"x")
    (tmp_path / "clips" / "a-medias.tmp").write_bytes(b"x")
    ColaEnvios(tmp_path, reloj=reloj)
    assert list((tmp_path / "clips").iterdir()) == []


def test_enviador_envia_al_ser_notificado(
    cola: ColaEnvios, cliente: ClienteBackend, backend: BackendFalso
) -> None:
    resumenes: list[Resumen] = []
    listo = threading.Event()

    def al_terminar(resumen: Resumen) -> None:
        resumenes.append(resumen)
        if resumen.eventos_enviados:
            listo.set()

    enviador = EnviadorPendientes(cola, cliente, al_terminar)
    enviador.iniciar()
    cola.agregar_evento(evento(1))
    enviador.notificar()
    assert listo.wait(5)
    enviador.detener()
    assert list(backend.eventos) == [evento(1).evento_id]


def test_enviador_sobrevive_a_errores_inesperados(cola: ColaEnvios) -> None:
    llamado = threading.Event()

    class Roto:
        def publicar_evento(self, evento: EventoAgente) -> object:
            llamado.set()
            raise RuntimeError("fallo")

        def solicitar_subida_clip(self, evento_id: str, tamano_bytes: int) -> object:
            raise NotImplementedError

        def subir_clip(self, subida: object, mp4: bytes) -> None:
            raise NotImplementedError

    cola.agregar_evento(evento(1))
    enviador = EnviadorPendientes(cola, Roto())  # type: ignore[arg-type]
    enviador.iniciar()
    assert llamado.wait(5)
    enviador.reintentar_ahora()
    enviador.detener()
    assert cola.eventos_pendientes() == [evento(1).evento_id]
