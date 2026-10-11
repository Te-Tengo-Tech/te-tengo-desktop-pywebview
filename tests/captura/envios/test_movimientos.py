"""Movements to the cloud (US-37) and the landmarks of a clip (US-36), through the outbox."""

import hashlib
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest

from te_tengo_captura.almacen.gestor import AlmacenLocal, GrabadorCamara
from te_tengo_captura.almacen.indice import TipoArchivo
from te_tengo_captura.almacen.ligero import leer_ligero, ruta_ligera
from te_tengo_captura.almacen.puntos import FilaMovimiento, a_ms, leer_parquet
from te_tengo_captura.backend.cliente import ClienteBackend
from te_tengo_captura.backend.errores import SinConexionError
from te_tengo_captura.backend.falso import URL_API, BackendFalso
from te_tengo_captura.backend.modelos import EventoAgente
from te_tengo_captura.envios.cola import ColaEnvios
from te_tengo_captura.envios.movimientos import CarrilMovimientos
from te_tengo_captura.vinculacion.credenciales import LlaveroEnMemoria
from te_tengo_deteccion.clasificacion.estados import TipoEvento

AHORA = datetime.now(UTC).replace(microsecond=0) - timedelta(minutes=30)
PUNTO = (0.5, 0.25, 0.0, 0.9)


class Reloj:
    def __init__(self) -> None:
        self.ahora = 1_000.0

    def __call__(self) -> float:
        return self.ahora


@pytest.fixture
def backend() -> BackendFalso:
    return BackendFalso()


@pytest.fixture
def cliente(backend: BackendFalso) -> ClienteBackend:
    c = ClienteBackend(URL_API, backend.credencial, "Sala", "1.0.0", backend.transporte())
    c.registrar()
    return c


@pytest.fixture
def almacen(tmp_path: Path, cliente: ClienteBackend) -> Iterator[AlmacenLocal]:
    a = AlmacenLocal(tmp_path / "ajustes", tmp_path / "Datos", LlaveroEnMemoria())
    a.iniciar(cliente.estado_movimientos)
    a.revisar_permiso()
    yield a
    a.detener()


@pytest.fixture
def reloj() -> Reloj:
    return Reloj()


@pytest.fixture
def cola(tmp_path: Path, almacen: AlmacenLocal, reloj: Reloj) -> ColaEnvios:
    c = ColaEnvios(tmp_path / "envios", reloj=reloj, aleatorio=lambda: 1.0)
    c.carril_movimientos = CarrilMovimientos(almacen, lambda: "camara-1")
    return c


def guardar_movimientos(almacen: AlmacenLocal, inicio: datetime, filas: int = 40) -> None:
    grabador = GrabadorCamara(almacen, "camara-1")
    for i in range(filas):
        grabador._poner(("fila", FilaMovimiento(a_ms(inicio) + i * 125, [PUNTO] * 33)))
    grabador.cerrar()


def archivos(almacen: AlmacenLocal) -> list[Path]:
    assert almacen.indice is not None
    return [
        almacen.carpeta / a.ruta
        for a in almacen.indice.anteriores_a(TipoArchivo.MOVIMIENTOS, 2**62)
    ]


def test_sube_el_archivo_y_lo_conserva_en_la_pc(
    cola: ColaEnvios, cliente: ClienteBackend, backend: BackendFalso, almacen: AlmacenLocal
) -> None:
    guardar_movimientos(almacen, AHORA)
    assert cola.movimientos_pendientes() == 1
    resumen = cola.enviar(cliente)
    assert resumen.movimientos_subidos == 1
    assert resumen.movimientos_pendientes == 0
    [subido] = backend.movimientos.values()
    assert subido["estado"] == "DISPONIBLE"
    contenido = subido["contenido"]
    assert contenido.startswith(b"PAR1")  # the plaintext Parquet, decrypted for the upload
    assert subido["sha256"] == hashlib.sha256(contenido).hexdigest()
    assert subido["fotogramas"] == 40
    assert subido["desde"] == AHORA
    _, filas = leer_parquet(contenido)
    assert len(filas) == 40
    ligero = subido["ligero"]  # the light file, right after (US-39)
    assert ligero["disponible"]
    assert ligero["sha256"] == hashlib.sha256(ligero["contenido"]).hexdigest()
    assert ligero["tamanoBytes"] == len(ligero["contenido"])
    assert [f.t_ms for f in leer_ligero(ligero["contenido"]).fotogramas] == [f.t_ms for f in filas]
    [ruta] = archivos(almacen)
    assert ruta.exists()  # kept for its local period, with its light file
    assert (ruta.parent / Path(ruta_ligera(ruta.name) or "")).exists()
    assert cola.enviar(cliente).movimientos_subidos == 0  # once


def test_un_archivo_solo_para_la_nube_se_borra_al_subirlo(
    cola: ColaEnvios, cliente: ClienteBackend, backend: BackendFalso, almacen: AlmacenLocal
) -> None:
    """Decided on 2026-10-11: with «Movimientos» off on the PC, a cloud retention chosen with the
    consent in force still uploads every file, so the family can replay it on the phone; the
    file is written only for the upload and deleted once the cloud has it."""
    almacen.cambiar(movimientos=False)
    assert not almacen.guarda(TipoArchivo.MOVIMIENTOS)  # nothing is kept on the PC
    assert almacen.sube_movimientos
    assert almacen.escribe_tramos  # still written: the cloud is on
    guardar_movimientos(almacen, AHORA)
    [ruta] = archivos(almacen)
    ligera = ruta.parent / (ruta_ligera(ruta.name) or "")
    assert ligera.exists()
    resumen = cola.enviar(cliente)
    assert resumen.movimientos_subidos == 1
    [subido] = backend.movimientos.values()
    assert subido["estado"] == "DISPONIBLE"
    assert len(leer_parquet(subido["contenido"])[1]) == 40
    assert not ruta.exists()
    assert not ligera.exists()
    assert archivos(almacen) == []

    # Without the cloud either, nothing is written at all.
    backend.movimientos_en_la_nube_dias = None
    almacen.revisar_permiso()
    assert not almacen.escribe_tramos


def test_una_api_sin_archivos_ligeros_recibe_solo_el_parquet(
    cola: ColaEnvios, cliente: ClienteBackend, backend: BackendFalso, almacen: AlmacenLocal
) -> None:
    backend.sin_ligeros = True  # 404 without codigo
    guardar_movimientos(almacen, AHORA)
    resumen = cola.enviar(cliente)
    assert resumen.error is None
    [subido] = backend.movimientos.values()
    assert subido["estado"] == "DISPONIBLE"
    assert subido["ligero"] is None
    assert cola.movimientos_pendientes() == 0


def test_un_ligero_que_fallo_se_sube_en_la_siguiente_pasada(
    cola: ColaEnvios,
    cliente: ClienteBackend,
    backend: BackendFalso,
    almacen: AlmacenLocal,
    reloj: Reloj,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    guardar_movimientos(almacen, AHORA)
    original = cliente.solicitar_subida_ligero

    def sin_red(*_: object) -> None:
        raise SinConexionError("sin red")

    monkeypatch.setattr(cliente, "solicitar_subida_ligero", sin_red)
    assert cola.enviar(cliente).error is not None
    [(archivo_id, subido)] = backend.movimientos.items()
    assert subido["estado"] == "DISPONIBLE"
    assert subido["ligero"] is None
    assert cola.movimientos_pendientes() == 1  # both stay on disk

    monkeypatch.setattr(cliente, "solicitar_subida_ligero", original)
    reloj.ahora += 10
    cola.enviar(cliente)  # 409 ARCHIVO_YA_SUBIDO {archivoId} → the light file
    assert list(backend.movimientos) == [archivo_id]
    assert backend.movimientos[archivo_id]["ligero"]["disponible"]
    assert cola.movimientos_pendientes() == 0


def test_va_despues_de_los_eventos(
    cola: ColaEnvios, cliente: ClienteBackend, backend: BackendFalso, almacen: AlmacenLocal
) -> None:
    guardar_movimientos(almacen, AHORA)
    cola.agregar_evento(
        EventoAgente(
            evento_id="0192f6e4-0000-7000-8000-000000000001",
            tipo=TipoEvento.CAIDA,
            ocurrido_en=AHORA,
        )
    )
    backend.fallos.append(503)
    resumen = cola.enviar(cliente)
    assert resumen.error is not None
    assert backend.movimientos == {}  # an alert waiting: no movement upload (CA-37.2)
    cola.reintentar_ahora()
    cola.enviar(cliente)  # the event goes out; then the movements
    assert len(backend.movimientos) == 1


def test_sin_nube_espera_y_sube_cuando_se_activa(
    cola: ColaEnvios, cliente: ClienteBackend, backend: BackendFalso, almacen: AlmacenLocal
) -> None:
    backend.movimientos_en_la_nube_dias = None
    almacen.revisar_permiso()
    guardar_movimientos(almacen, AHORA)
    assert cola.movimientos_pendientes() == 0
    cola.enviar(cliente)
    assert backend.movimientos == {}
    avisos: list[int] = []
    almacen.al_cambiar_permiso.append(lambda: avisos.append(1))
    backend.movimientos_en_la_nube_dias = 30
    almacen.revisar_permiso()
    assert avisos == [1]  # the outbox is woken up
    cola.enviar(cliente)
    assert len(backend.movimientos) == 1


def test_sin_internet_espera_en_disco(
    cola: ColaEnvios,
    cliente: ClienteBackend,
    backend: BackendFalso,
    almacen: AlmacenLocal,
    reloj: Reloj,
) -> None:
    guardar_movimientos(almacen, AHORA)
    backend.sin_conexion = True
    resumen = cola.enviar(cliente)
    assert resumen.error is not None
    assert resumen.movimientos_pendientes == 1
    assert cola.espera() > 0  # its own backoff
    backend.sin_conexion = False
    reloj.ahora += 10
    cola.enviar(cliente)
    assert len(backend.movimientos) == 1  # CA-37.3


def test_fuera_del_plazo_o_ya_subido_salen_de_la_cola(
    cola: ColaEnvios, cliente: ClienteBackend, backend: BackendFalso, almacen: AlmacenLocal
) -> None:
    backend.movimientos_en_la_nube_dias = 7
    almacen.revisar_permiso()
    guardar_movimientos(almacen, AHORA - timedelta(days=10))
    cola.enviar(cliente)
    assert backend.movimientos == {}  # 422 MOVIMIENTOS_FUERA_DEL_PLAZO
    assert cola.movimientos_pendientes() == 0
    assert len(archivos(almacen)) == 1  # the local period still applies

    guardar_movimientos(almacen, AHORA)
    cola.enviar(cliente)
    [archivo_id] = backend.movimientos
    assert almacen.indice is not None
    [nuevo] = [a for a in almacen.indice.anteriores_a(TipoArchivo.MOVIMIENTOS, 2**62) if a.subido][
        -1:
    ]
    almacen.indice._db.execute("UPDATE archivos SET subido = 0 WHERE id = ?", (nuevo.id,))
    cola.enviar(cliente)  # 409 ARCHIVO_YA_SUBIDO: dropped, not uploaded twice
    assert list(backend.movimientos) == [archivo_id]
    assert cola.movimientos_pendientes() == 0


def test_revocado_en_la_nube_detiene_y_consulta(
    cola: ColaEnvios, cliente: ClienteBackend, backend: BackendFalso, almacen: AlmacenLocal
) -> None:
    guardar_movimientos(almacen, AHORA)
    backend.movimientos_en_la_nube_dias = None  # the PC has not heard yet
    resumen = cola.enviar(cliente)
    assert resumen.error is not None
    assert resumen.error.codigo == "MOVIMIENTOS_EN_LA_NUBE_DESACTIVADOS"
    almacen.revisar_permiso()  # what pedir_permiso triggers in the storage thread
    assert not almacen.sube_movimientos
    assert cola.movimientos_pendientes() == 0


def test_si_el_almacenamiento_no_lo_tiene_se_vuelve_a_subir(
    cola: ColaEnvios,
    cliente: ClienteBackend,
    backend: BackendFalso,
    almacen: AlmacenLocal,
    reloj: Reloj,
) -> None:
    guardar_movimientos(almacen, AHORA)
    backend.almacen_falla = 500
    assert cola.enviar(cliente).error is not None
    backend.almacen_falla = None
    reloj.ahora += 10
    cola.enviar(cliente)
    assert [a["estado"] for a in backend.movimientos.values()] == ["DISPONIBLE"]


def test_los_puntos_del_clip_van_despues_del_clip(
    cola: ColaEnvios, cliente: ClienteBackend, backend: BackendFalso, tmp_path: Path
) -> None:
    evento_id = "0192f6e4-0000-7000-8000-000000000002"
    cola.agregar_evento(EventoAgente(evento_id=evento_id, tipo=TipoEvento.CAIDA, ocurrido_en=AHORA))
    cola.agregar_clip(evento_id, b"\x00\x00\x00\x18ftypmp42")
    cola.agregar_puntos_clip(evento_id, b"PAR1 puntos", b"\x1f\x8b ligero")
    assert cola.puntos_pendientes() == [evento_id]
    assert (tmp_path / "envios" / "clips" / f"{evento_id}.puntos.ttmov").exists()
    cola.enviar(cliente)
    assert evento_id in backend.clips
    assert backend.puntos_clips[evento_id] == b"PAR1 puntos"
    assert backend.puntos_clips_ligeros[evento_id] == b"\x1f\x8b ligero"
    assert cola.puntos_pendientes() == []
    assert not (tmp_path / "envios" / "clips" / f"{evento_id}.puntos.parquet").exists()
    assert not (tmp_path / "envios" / "clips" / f"{evento_id}.puntos.ttmov").exists()


def test_los_puntos_ligeros_del_clip_con_una_api_anterior(
    cola: ColaEnvios, cliente: ClienteBackend, backend: BackendFalso, tmp_path: Path
) -> None:
    backend.sin_ligeros = True
    evento_id = "0192f6e4-0000-7000-8000-000000000004"
    cola.agregar_evento(EventoAgente(evento_id=evento_id, tipo=TipoEvento.CAIDA, ocurrido_en=AHORA))
    cola.agregar_puntos_clip(evento_id, b"PAR1 puntos", b"\x1f\x8b ligero")
    resumen = cola.enviar(cliente)
    assert resumen.error is None
    assert backend.puntos_clips[evento_id] == b"PAR1 puntos"
    assert backend.puntos_clips_ligeros == {}
    assert cola.puntos_pendientes() == []
    assert list((tmp_path / "envios" / "clips").iterdir()) == []


def test_los_puntos_ligeros_sobreviven_al_reinicio(tmp_path: Path) -> None:
    cola = ColaEnvios(tmp_path / "envios")
    cola.agregar_puntos_clip("e1", b"PAR1", b"ligero")
    (tmp_path / "envios" / "clips" / "huerfano.puntos.ttmov").write_bytes(b"x")
    cola.cerrar()
    ColaEnvios(tmp_path / "envios").cerrar()  # startup deletes what the database does not know
    assert sorted(p.name for p in (tmp_path / "envios" / "clips").iterdir()) == [
        "e1.puntos.parquet",
        "e1.puntos.ttmov",
    ]


def test_sin_consentimiento_los_puntos_del_clip_se_descartan(
    cola: ColaEnvios, cliente: ClienteBackend, backend: BackendFalso
) -> None:
    evento_id = "0192f6e4-0000-7000-8000-000000000003"
    cola.agregar_evento(EventoAgente(evento_id=evento_id, tipo=TipoEvento.CAIDA, ocurrido_en=AHORA))
    cola.agregar_puntos_clip(evento_id, b"PAR1 puntos")
    backend.consentimiento_vigente = False
    cola.enviar(cliente)
    assert backend.puntos_clips == {}
    assert cola.puntos_pendientes() == []  # 409 SIN_CONSENTIMIENTO_DE_MOVIMIENTOS (CA-36.2)


def test_el_grabador_entrega_los_12_segundos_del_clip(almacen: AlmacenLocal) -> None:
    grabador = GrabadorCamara(almacen, "camara-1")
    recibidos: list[tuple[str, bytes, bytes]] = []
    grabador.al_puntos_clip = lambda evento, datos, ligero: recibidos.append(
        (evento, datos, ligero)
    )
    for i in range(20 * 8):
        grabador._poner(("fila", FilaMovimiento(a_ms(AHORA) + i * 125, [PUNTO] * 33)))
    grabador.clip("evento-1", AHORA + timedelta(seconds=10), b"mp4")
    grabador.cerrar()
    [(evento, datos, ligero)] = recibidos
    assert evento == "evento-1"
    metadatos, filas = leer_parquet(datos)
    assert metadatos["camara_id"] == "camara-1"
    assert filas[0].t_ms == a_ms(AHORA) + 4000
    assert filas[-1].t_ms == a_ms(AHORA) + 16000
    assert len(filas) == 12 * 8 + 1
    archivo = leer_ligero(ligero)  # the same rows for the app (US-36)
    assert archivo.t0_ms == a_ms(AHORA) + 4000
    assert archivo.duracion_ms == 12_000
    assert [f.t_ms for f in archivo.fotogramas] == [f.t_ms for f in filas]


def test_confirmacion_sin_archivo_lo_sube_otra_vez(
    cola: ColaEnvios,
    cliente: ClienteBackend,
    backend: BackendFalso,
    almacen: AlmacenLocal,
    reloj: Reloj,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    guardar_movimientos(almacen, AHORA)
    original = backend._subir
    monkeypatch.setattr(backend, "_subir", lambda solicitud: httpx.Response(200))  # lost
    resumen = cola.enviar(cliente)
    assert resumen.error is not None  # 409 ARCHIVO_NO_SUBIDO at the confirmation
    assert cola.movimientos_pendientes() == 1
    monkeypatch.setattr(backend, "_subir", original)
    reloj.ahora += 10
    cola.enviar(cliente)
    assert [a["estado"] for a in backend.movimientos.values()] == ["DISPONIBLE"]
