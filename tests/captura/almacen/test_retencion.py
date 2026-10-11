from pathlib import Path

import pytest

from te_tengo_captura.almacen.indice import IndiceArchivos, TipoArchivo
from te_tengo_captura.almacen.retencion import (
    UN_DIA_MS,
    MotivoBorrado,
    Politica,
    ReglaTipo,
    aplicar_retencion,
    liberar_espacio,
)

T0 = 1_791_000_000_000
HORA = 60 * 60 * 1000


class Disco:
    """Fake filesystem: records deletions and fails on the paths it is told to."""

    def __init__(self) -> None:
        self.borrados: list[str] = []
        self.fallan: set[str] = set()

    def __call__(self, ruta: str) -> None:
        if ruta in self.fallan:
            raise PermissionError(ruta)
        self.borrados.append(ruta)


@pytest.fixture
def indice(tmp_path: Path) -> IndiceArchivos:
    return IndiceArchivos(tmp_path / "indice.sqlite3", reloj=lambda: T0 / 1000)


@pytest.fixture
def disco() -> Disco:
    return Disco()


def politica(
    movimientos: int | None = 30,
    video: int | None = 7,
    clip: int | None = None,
    limite_bytes: int = 10_000,
) -> Politica:
    return Politica(
        movimientos=ReglaTipo(True, movimientos),
        video=ReglaTipo(False, video),
        clip=ReglaTipo(True, clip),
        limite_bytes=limite_bytes,
    )


def guardar(
    indice: IndiceArchivos, tipo: TipoArchivo, dias_atras: float, tamano: int = 1_000
) -> str:
    hasta = T0 - round(dias_atras * UN_DIA_MS)
    ruta = f"{tipo.value}/{hasta}.ttg"
    indice.registrar(tipo, "cam-1", hasta - 5 * 60_000, hasta, ruta, tamano)
    return ruta


# ---------------------------------------------------------------------- retention


def test_retencion_por_tipo(indice: IndiceArchivos, disco: Disco) -> None:
    mov_viejo = guardar(indice, TipoArchivo.MOVIMIENTOS, 31)
    mov_justo = guardar(indice, TipoArchivo.MOVIMIENTOS, 30)  # ended exactly 30 days ago
    mov_nuevo = guardar(indice, TipoArchivo.MOVIMIENTOS, 29.9)
    vid_viejo = guardar(indice, TipoArchivo.VIDEO, 8)
    vid_nuevo = guardar(indice, TipoArchivo.VIDEO, 6)
    clip_antiguo = guardar(indice, TipoArchivo.CLIP, 900)  # «Nunca borrar»

    borrados = aplicar_retencion(indice, politica(), T0, disco)

    assert sorted(disco.borrados) == sorted([mov_viejo, mov_justo, vid_viejo])
    assert {b.motivo for b in borrados} == {MotivoBorrado.RETENCION}
    assert indice.rutas_conocidas() == {mov_nuevo, vid_nuevo, clip_antiguo}


def test_nunca_borrar_en_todos_los_tipos(indice: IndiceArchivos, disco: Disco) -> None:
    for tipo in TipoArchivo:
        guardar(indice, tipo, 5_000)
    assert aplicar_retencion(indice, politica(None, None, None), T0, disco) == []
    assert disco.borrados == []


def test_la_retencion_aplica_aunque_el_tipo_este_apagado(
    indice: IndiceArchivos, disco: Disco
) -> None:
    viejo = guardar(indice, TipoArchivo.VIDEO, 10)  # video switch is off in ``politica()``
    assert not politica().guarda(TipoArchivo.VIDEO)
    aplicar_retencion(indice, politica(), T0, disco)
    assert disco.borrados == [viejo]


def test_la_retencion_avanza_con_el_reloj_inyectado(indice: IndiceArchivos, disco: Disco) -> None:
    ruta = guardar(indice, TipoArchivo.VIDEO, 6)
    assert aplicar_retencion(indice, politica(), T0, disco) == []
    assert aplicar_retencion(indice, politica(), T0 + UN_DIA_MS - 1, disco) == []
    (borrado,) = aplicar_retencion(indice, politica(), T0 + UN_DIA_MS, disco)
    assert borrado.archivo.ruta == ruta


def test_un_archivo_que_no_se_puede_borrar_queda_en_el_indice(
    indice: IndiceArchivos, disco: Disco
) -> None:
    bloqueado = guardar(indice, TipoArchivo.VIDEO, 9)
    otro = guardar(indice, TipoArchivo.VIDEO, 8)
    disco.fallan.add(bloqueado)
    borrados = aplicar_retencion(indice, politica(), T0, disco)
    assert [b.archivo.ruta for b in borrados] == [otro]
    assert bloqueado in indice.rutas_conocidas()


def test_dias_negativos() -> None:
    with pytest.raises(ValueError, match="negativos"):
        ReglaTipo(True, -1)


# ---------------------------------------------------------------------- cap


def test_bajo_el_limite_no_borra_nada(indice: IndiceArchivos, disco: Disco) -> None:
    guardar(indice, TipoArchivo.VIDEO, 1, tamano=4_000)
    resultado = liberar_espacio(indice, politica(limite_bytes=10_000), 6_000, disco)
    assert (resultado.borrados, resultado.suficiente, resultado.faltan_bytes) == ([], True, 0)
    assert disco.borrados == []


def test_primero_el_video_mas_antiguo_luego_los_movimientos(
    indice: IndiceArchivos, disco: Disco
) -> None:
    mov_viejo = guardar(indice, TipoArchivo.MOVIMIENTOS, 20, tamano=1_000)
    mov_nuevo = guardar(indice, TipoArchivo.MOVIMIENTOS, 2, tamano=1_000)
    vid_2 = guardar(indice, TipoArchivo.VIDEO, 2, tamano=2_000)
    vid_1 = guardar(indice, TipoArchivo.VIDEO, 3, tamano=2_000)
    guardar(indice, TipoArchivo.CLIP, 50, tamano=1_000)
    # Used: 7_000 of 10_000. Writing 3_000 fits; 4_000 needs one video.
    assert liberar_espacio(indice, politica(), 3_000, disco).borrados == []
    resultado = liberar_espacio(indice, politica(), 4_000, disco)
    assert [b.archivo.ruta for b in resultado.borrados] == [vid_1]
    assert resultado.borrados[0].motivo is MotivoBorrado.ESPACIO
    assert resultado.suficiente
    # Now 5_000 used; 9_000 more needs the other video and then the oldest movements.
    resultado = liberar_espacio(indice, politica(), 9_000, disco)
    assert [b.archivo.ruta for b in resultado.borrados] == [vid_2, mov_viejo, mov_nuevo]
    assert resultado.suficiente
    assert disco.borrados == [vid_1, vid_2, mov_viejo, mov_nuevo]


def test_los_clips_nunca_se_borran_por_el_limite(indice: IndiceArchivos, disco: Disco) -> None:
    clips = {guardar(indice, TipoArchivo.CLIP, d, tamano=4_000) for d in (100, 50, 1)}
    video = guardar(indice, TipoArchivo.VIDEO, 1, tamano=1_000)
    # 13_000 used, cap 10_000: even deleting all the video the clips alone exceed it.
    resultado = liberar_espacio(indice, politica(), 500, disco)
    assert [b.archivo.ruta for b in resultado.borrados] == [video]
    assert not resultado.suficiente
    assert resultado.faltan_bytes == 12_000 + 500 - 10_000
    assert indice.rutas_conocidas() == clips


def test_parcial_cuando_no_alcanza_lo_borrable(indice: IndiceArchivos, disco: Disco) -> None:
    guardar(indice, TipoArchivo.MOVIMIENTOS, 3, tamano=3_000)
    guardar(indice, TipoArchivo.VIDEO, 2, tamano=3_000)
    resultado = liberar_espacio(indice, politica(limite_bytes=5_000), 9_000, disco)
    assert len(resultado.borrados) == 2
    assert (resultado.suficiente, resultado.faltan_bytes) == (False, 4_000)
    assert indice.uso_por_tipo() == dict.fromkeys(TipoArchivo, 0)


def test_salta_los_archivos_que_no_se_pueden_borrar(indice: IndiceArchivos, disco: Disco) -> None:
    bloqueado = guardar(indice, TipoArchivo.VIDEO, 9, tamano=2_000)
    siguiente = guardar(indice, TipoArchivo.VIDEO, 8, tamano=2_000)
    disco.fallan.add(bloqueado)
    resultado = liberar_espacio(indice, politica(limite_bytes=4_000), 1_000, disco)
    assert [b.archivo.ruta for b in resultado.borrados] == [siguiente]
    assert resultado.suficiente
    assert bloqueado in indice.rutas_conocidas()


def test_muchos_archivos_mas_que_un_lote(indice: IndiceArchivos, disco: Disco) -> None:
    for n in range(250):
        guardar(indice, TipoArchivo.VIDEO, 300 - n, tamano=10)
    resultado = liberar_espacio(indice, politica(limite_bytes=0), 2_000, disco)
    assert len(resultado.borrados) == 250
    assert disco.borrados == sorted(disco.borrados, key=lambda r: int(r.split("/")[1][:-4]))
    assert resultado.faltan_bytes == 2_000


def test_es_determinista(tmp_path: Path) -> None:
    def correr(nombre: str) -> list[str]:
        indice = IndiceArchivos(tmp_path / nombre, reloj=lambda: T0 / 1000)
        disco = Disco()
        for d in (5, 1, 3, 2, 4):
            guardar(indice, TipoArchivo.VIDEO, d, tamano=1_000)
            guardar(indice, TipoArchivo.MOVIMIENTOS, d, tamano=500)
        aplicar_retencion(indice, politica(video=3), T0, disco)
        liberar_espacio(indice, politica(limite_bytes=4_000), 1_000, disco)
        return disco.borrados

    assert correr("a.sqlite3") == correr("b.sqlite3")
