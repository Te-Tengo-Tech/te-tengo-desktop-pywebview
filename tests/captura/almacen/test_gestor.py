"""«Almacenamiento» (US-38) with the movement consent (US-35): what the PC keeps, and how."""

import io
import threading
import time
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pytest

from te_tengo_captura.almacen import gestor
from te_tengo_captura.almacen.cifrado import MAGIA, SERVICIO, USUARIO, descifrar_bytes
from te_tengo_captura.almacen.gestor import AjustesAlmacen, AlmacenLocal
from te_tengo_captura.almacen.indice import TipoArchivo
from te_tengo_captura.almacen.ligero import leer_ligero
from te_tengo_captura.almacen.puntos import (
    FilaMovimiento,
    TramoCerrado,
    TramoMovimientos,
    a_ms,
    leer_parquet,
)
from te_tengo_captura.backend.errores import ErrorBackendError
from te_tengo_captura.backend.modelos import EstadoMovimientos
from te_tengo_captura.captura.bucle import Analisis
from te_tengo_captura.captura.fuentes import Fotograma
from te_tengo_captura.vinculacion.credenciales import LlaveroEnMemoria
from te_tengo_deteccion.clasificacion.estados import ClasificadorCinematico
from te_tengo_deteccion.clasificacion.umbrales import Umbrales
from te_tengo_deteccion.pose.schemas import Pose
from tests.fabricas import DE_PIE

T0 = datetime(2026, 9, 23, 15, 40, tzinfo=UTC)
PERMITIDO = EstadoMovimientos(
    consentimiento_vigente=True, guardar_en_la_pc=True, guardar_en_la_nube=True, retencion_dias=30
)
REVOCADO = EstadoMovimientos(
    consentimiento_vigente=False, guardar_en_la_pc=False, guardar_en_la_nube=False
)


def esperar(condicion: Callable[[], object], segundos: float = 5.0) -> None:
    limite = time.monotonic() + segundos
    while not condicion():
        if time.monotonic() > limite:
            raise AssertionError("no se cumplió a tiempo")
        time.sleep(0.02)


class Permiso:
    """What ``GET /api/agente/movimientos/estado`` answers."""

    def __init__(self, estado: EstadoMovimientos = PERMITIDO) -> None:
        self.estado = estado

    def __call__(self) -> EstadoMovimientos:
        return self.estado


@pytest.fixture
def llavero() -> LlaveroEnMemoria:
    return LlaveroEnMemoria()


@pytest.fixture
def almacen(tmp_path: Path, llavero: LlaveroEnMemoria) -> Iterator[AlmacenLocal]:
    a = AlmacenLocal(tmp_path / "ajustes", tmp_path / "Datos", llavero, reloj_utc=lambda: T0)
    yield a
    a.detener()


def analisis(
    n: int, pose: Pose | None = DE_PIE, imagen: np.ndarray | None = None
) -> list[Analisis]:
    clasificador = ClasificadorCinematico(Umbrales(velocidad_descenso_min=0.5))
    if imagen is None:
        imagen = np.zeros((480, 640, 3), dtype=np.uint8)
    resultado = []
    for i in range(n):
        instante = i / 8
        eventos = clasificador.actualizar(instante, pose)
        resultado.append(
            Analisis(
                fotograma=Fotograma(instante, b"", imagen),
                pose=pose,
                clasificador=clasificador,
                eventos=eventos,
                detectados=[],
                ocurrido_en=T0 + timedelta(seconds=instante),
            )
        )
    return resultado


def archivos(almacen: AlmacenLocal, tipo: TipoArchivo) -> list[Path]:
    assert almacen.indice is not None
    return [almacen.carpeta / a.ruta for a in almacen.indice.anteriores_a(tipo, 2**62)]


def test_guarda_los_movimientos_cifrados_y_se_pueden_leer(almacen: AlmacenLocal) -> None:
    avisados: list[tuple[str, int]] = []
    almacen.al_movimientos.append(lambda camara, archivo: avisados.append((camara, archivo)))
    almacen.iniciar(Permiso())
    almacen.revisar_permiso()
    grabador = almacen.para_camara("c1")
    for a in analisis(40):
        grabador.analizado(a)
    almacen.soltar_camara("c1")  # closes the 5-minute file

    [ruta] = archivos(almacen, TipoArchivo.MOVIMIENTOS)
    assert ruta.relative_to(almacen.carpeta).as_posix() == (
        "movimientos/c1/2026/09/23/154000.parquet.ttg"
    )
    cifrado = ruta.read_bytes()
    assert cifrado.startswith(MAGIA)
    assert b"PAR1" not in cifrado  # no plaintext Parquet on the disk (CA-38.4)
    clave = almacen.clave()
    assert clave is not None
    metadatos, filas = leer_parquet(descifrar_bytes(clave, cifrado))
    assert metadatos["camara_id"] == "c1"
    assert len(filas) == 40
    assert filas[0].t_ms == a_ms(T0)
    assert filas[0].landmarks is not None
    x, y, _, _ = filas[0].landmarks[0]
    assert x == pytest.approx(DE_PIE.landmarks[0].x, abs=1e-4)
    assert y == pytest.approx(DE_PIE.landmarks[0].y, abs=1e-4)
    assert avisados
    assert avisados[0][0] == "c1"  # the cloud upload hears of it (US-37)

    ligera = ruta.with_name("154000.ttmov.ttg")  # the light file the app draws (US-39)
    cifrada = ligera.read_bytes()
    assert cifrada.startswith(MAGIA)  # encrypted too (CA-38.4)
    assert b"TTMV" not in cifrada
    [archivo] = almacen.indice.anteriores_a(TipoArchivo.MOVIMIENTOS, 2**62)  # type: ignore[union-attr]
    assert archivo.tamano_bytes == len(cifrado) + len(cifrada)  # both count for the limit
    ligero = almacen.leer_ligero(archivo)
    assert ligero is not None
    assert ligero == descifrar_bytes(clave, cifrada)
    assert [f.t_ms for f in leer_ligero(ligero).fotogramas] == [f.t_ms for f in filas]


def test_sin_permiso_no_guarda_movimientos(almacen: AlmacenLocal) -> None:
    almacen.iniciar(Permiso(REVOCADO))
    almacen.revisar_permiso()
    grabador = almacen.para_camara("c1")
    for a in analisis(16):
        grabador.analizado(a)
    almacen.soltar_camara("c1")
    assert archivos(almacen, TipoArchivo.MOVIMIENTOS) == []
    estado = almacen.estado()
    assert estado["permisoMovimientos"] is False
    assert estado["nube"] is None


def test_sin_respuesta_de_la_api_no_guarda_movimientos(almacen: AlmacenLocal) -> None:
    def sin_conexion() -> EstadoMovimientos:
        raise ErrorBackendError("sin conexión")

    almacen.iniciar(sin_conexion)
    almacen.revisar_permiso()
    assert almacen.puede_movimientos is False  # only with a known consent (CA-35.3)


def test_al_revocar_pregunta_si_borra_lo_guardado(almacen: AlmacenLocal) -> None:
    permiso = Permiso()
    almacen.iniciar(permiso)
    almacen.revisar_permiso()
    grabador = almacen.para_camara("c1")
    for a in analisis(16):
        grabador.analizado(a)
    almacen.soltar_camara("c1")
    assert len(archivos(almacen, TipoArchivo.MOVIMIENTOS)) == 1

    permiso.estado = REVOCADO
    almacen.revisar_permiso()
    assert almacen.estado()["revocado"] is True  # «¿Borrar los movimientos de esta PC?»
    almacen.conservar()
    assert almacen.estado()["revocado"] is False
    assert len(archivos(almacen, TipoArchivo.MOVIMIENTOS)) == 1  # «Conservar»

    permiso.estado = PERMITIDO
    almacen.revisar_permiso()
    permiso.estado = REVOCADO
    almacen.revisar_permiso()
    [ruta] = archivos(almacen, TipoArchivo.MOVIMIENTOS)
    ligera = ruta.with_name(ruta.name.replace(".parquet", ".ttmov"))
    assert ligera.exists()
    assert almacen.borrar_tipo(TipoArchivo.MOVIMIENTOS) > 0  # «Borrar»
    assert not ruta.exists()
    assert not ligera.exists()  # with its light file
    assert archivos(almacen, TipoArchivo.MOVIMIENTOS) == []
    assert almacen.estado()["revocado"] is False


def _escribir(tamano: int) -> Callable[[Path, bytes], int]:
    def escribir(destino: Path, clave: bytes) -> int:
        destino.write_bytes(b"x" * tamano)
        return tamano

    return escribir


def test_al_llegar_al_limite_borra_primero_el_video(almacen: AlmacenLocal) -> None:
    almacen.iniciar(None)
    almacen.cambiar(limite_gb=2000 / gestor.GB)  # 2000 bytes
    hora = a_ms(T0)
    video = almacen.guardar(TipoArchivo.VIDEO, "c1", hora, hora + 1, "video/a", _escribir(900), 900)
    mov1 = almacen.guardar(
        TipoArchivo.MOVIMIENTOS, "c1", hora + 1, hora + 2, "movimientos/a", _escribir(500), 500
    )
    assert video is not None
    assert mov1 is not None
    assert almacen.estado()["estado"] is None

    mov2 = almacen.guardar(
        TipoArchivo.MOVIMIENTOS, "c1", hora + 2, hora + 3, "movimientos/b", _escribir(800), 800
    )
    assert mov2 is not None
    assert not (almacen.carpeta / "video/a").exists()  # the oldest video goes first (CA-38.3)
    assert (almacen.carpeta / "movimientos/a").exists()
    estado = almacen.estado()
    assert estado["estado"] == "limite"
    assert estado["liberado"] == f"{T0.astimezone():%d/%m}"

    almacen.guardar(
        TipoArchivo.MOVIMIENTOS, "c1", hora + 3, hora + 4, "movimientos/c", _escribir(900), 900
    )
    assert not (almacen.carpeta / "movimientos/a").exists()  # then the oldest movements
    assert (almacen.carpeta / "movimientos/c").exists()


def test_un_archivo_que_no_cabe_se_salta_sin_detener_nada(almacen: AlmacenLocal) -> None:
    almacen.iniciar(None)
    almacen.cambiar(limite_gb=100 / gestor.GB)
    hora = a_ms(T0)
    assert (
        almacen.guardar(TipoArchivo.CLIP, "c1", hora, hora + 1, "clips/a", _escribir(500), 500)
        is None
    )
    assert not (almacen.carpeta / "clips/a").exists()


def test_la_retencion_borra_lo_vencido(almacen: AlmacenLocal) -> None:
    almacen.iniciar(None)
    viejo = a_ms(T0 - timedelta(days=10))
    almacen.guardar(TipoArchivo.MOVIMIENTOS, "c1", viejo, viejo + 1, "m/viejo", _escribir(10), 10)
    almacen.guardar(
        TipoArchivo.MOVIMIENTOS, "c1", a_ms(T0), a_ms(T0) + 1, "m/hoy", _escribir(10), 10
    )
    almacen.guardar(
        TipoArchivo.MOVIMIENTOS, "c1", viejo, viejo + 2, "m/v.parquet.ttg", _escribir(10), 10
    )
    (almacen.carpeta / "m/v.ttmov.ttg").write_bytes(b"x")  # its light file
    almacen.cambiar(dias_movimientos=7)  # applies at once
    esperar(lambda: not (almacen.carpeta / "m/viejo").exists())
    assert (almacen.carpeta / "m/hoy").exists()
    esperar(lambda: not (almacen.carpeta / "m/v.ttmov.ttg").exists())
    assert not (almacen.carpeta / "m/v.parquet.ttg").exists()


def test_cambios_para_la_actividad_y_ajustes_guardados(
    tmp_path: Path, llavero: LlaveroEnMemoria
) -> None:
    almacen = AlmacenLocal(tmp_path / "ajustes", tmp_path / "Datos", llavero)
    assert almacen.ajustes == AjustesAlmacen()  # video off by default (CA-38.2)
    textos = [c.texto for c in almacen.cambiar(video=True, dias_movimientos=30, limite_gb=25)]
    assert textos == [
        "Desde esta PC: los movimientos pasaron de 90 días a 30 días",
        "Desde esta PC: se activó el video continuo",
        "Desde esta PC: el límite de espacio pasó de 50 GB a 25 GB",
    ]
    assert almacen.cambiar(video=True) == []
    [nunca] = almacen.cambiar(dias_clips=365)
    assert (nunca.anterior, nunca.nuevo) == ("Nunca borrar", "1 año")
    otra = AlmacenLocal(tmp_path / "ajustes", tmp_path / "Datos", llavero)
    assert otra.ajustes.video is True
    assert otra.ajustes.limite_gb == 25


def test_video_continuo_cifrado_en_partes(almacen: AlmacenLocal) -> None:
    av = pytest.importorskip("av")
    almacen.iniciar(Permiso())
    almacen.cambiar(video=True)
    ruido = np.random.default_rng(1).integers(0, 255, (480, 640, 3), dtype=np.uint8)
    grabador = almacen.para_camara("c1")
    for a in analisis(24, imagen=ruido):
        grabador.analizado(a)
    almacen.soltar_camara("c1")

    [ruta] = archivos(almacen, TipoArchivo.VIDEO)
    assert ruta.name == "154000.mp4.ttg"
    clave = almacen.clave()
    assert clave is not None
    mp4 = descifrar_bytes(clave, ruta.read_bytes())
    with av.open(io.BytesIO(mp4)) as contenedor:
        flujo = contenedor.streams.video[0]
        assert (flujo.codec_context.name, flujo.width, flujo.height) == ("h264", 640, 480)
        assert sum(1 for _ in contenedor.decode(flujo)) == 24


def test_el_capturador_nunca_espera_al_disco(
    almacen: AlmacenLocal, monkeypatch: pytest.MonkeyPatch
) -> None:
    almacen.iniciar(Permiso())
    almacen.revisar_permiso()
    soltar = threading.Event()
    original = TramoMovimientos.agregar

    def lento(self: TramoMovimientos, fila: FilaMovimiento) -> list[TramoCerrado]:
        soltar.wait(5)
        return original(self, fila)

    monkeypatch.setattr(TramoMovimientos, "agregar", lento)
    grabador = almacen.para_camara("c1")
    lista = analisis(400)
    inicio = time.monotonic()
    for a in lista:
        grabador.analizado(a)
    assert time.monotonic() - inicio < 1.0
    assert grabador.descartados > 0  # dropped, never waited for
    soltar.set()


def test_borrar_todo_borra_la_carpeta_y_la_clave(
    almacen: AlmacenLocal, llavero: LlaveroEnMemoria
) -> None:
    almacen.iniciar(Permiso())
    almacen.revisar_permiso()
    grabador = almacen.para_camara("c1")
    for a in analisis(16):
        grabador.analizado(a)
    almacen.soltar_camara("c1")
    assert llavero.get_password(SERVICIO, USUARIO) is not None
    almacen.borrar_todo()  # «Borrar también los datos de esta PC» (CA-31.6)
    assert not almacen.carpeta.exists()
    assert llavero.get_password(SERVICIO, USUARIO) is None


def test_cambiar_carpeta_mueve_todo(almacen: AlmacenLocal, tmp_path: Path) -> None:
    almacen.iniciar(None)
    hora = a_ms(T0)
    almacen.guardar(TipoArchivo.CLIP, "c1", hora, hora + 1, "clips/c1/a.mp4.ttg", _escribir(64), 64)
    terminado: list[bool] = []
    nueva = tmp_path / "Otra" / "TeTengo" / "Datos"
    almacen.mover_carpeta(nueva, terminado.append)
    esperar(lambda: terminado)
    assert terminado == [True]
    assert almacen.carpeta == nueva
    assert (nueva / "clips/c1/a.mp4.ttg").read_bytes() == b"x" * 64
    assert not (tmp_path / "Datos").exists()
    assert almacen.uso()[TipoArchivo.CLIP] == 64
    assert almacen.estado()["estado"] is None


class LlaveroRoto(LlaveroEnMemoria):
    def get_password(self, service_name: str, username: str) -> str | None:
        raise RuntimeError("sin almacén de credenciales")


def test_sin_almacen_de_claves_no_guarda_nada_y_lo_dice(tmp_path: Path) -> None:
    almacen = AlmacenLocal(tmp_path / "ajustes", tmp_path / "Datos", LlaveroRoto())
    almacen.iniciar(None)
    try:
        hora = a_ms(T0)
        assert (
            almacen.guardar(TipoArchivo.CLIP, "c1", hora, hora + 1, "clips/a", _escribir(1), 1)
            is None
        )
        assert almacen.problema == "sin_clave"
        assert almacen.estado()["estado"] == "lleno"  # «No podemos guardar en la carpeta»
    finally:
        almacen.detener()
