from detection_worker.ingesta import protocolo
from detection_worker.ingesta.service import ProcesadorCamara
from te_tengo_deteccion.clasificacion.estados import ClasificadorCinematico, TipoEvento
from te_tengo_deteccion.clasificacion.umbrales import Umbrales
from te_tengo_deteccion.pose.schemas import Pose
from tests import fabricas
from tests.conftest import AlmacenFalso, EstimadorFalso, PublicadorFalso

JPEG = b"\xff\xd8\xff\xe0contenido"


async def test_caida_se_publica_y_su_clip_se_guarda(umbrales: Umbrales) -> None:
    instantes = (
        [round(i * 0.1, 1) for i in range(11)]
        + [1.1]
        + [round(1.2 + i * 0.5, 1) for i in range(14)]
    )
    poses: list[Pose | None] = [fabricas.DE_PIE] * 11
    poses += [fabricas.CAYENDO] + [fabricas.TENDIDA] * 14
    publicador, almacen = PublicadorFalso(), AlmacenFalso()
    procesador = ProcesadorCamara(
        "camara-1",
        EstimadorFalso(poses),
        ClasificadorCinematico(umbrales),
        publicador,
        almacen,
    )

    for t in instantes:
        await procesador.procesar(protocolo.codificar(int(t * 1000), JPEG))
    await procesador.cerrar()

    assert [e.tipo for e in publicador.eventos] == [TipoEvento.CAIDA]
    caida = publicador.eventos[0]
    assert caida.camara_id == "camara-1"
    assert len(almacen.guardados) == 1
    assert publicador.clips == {caida.evento_id: f"clips/camara-1/{caida.evento_id}.mp4"}
