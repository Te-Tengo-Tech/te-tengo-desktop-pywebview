"""Endpoint WebSocket por el que el Agente de captura envía el video.

Formato de los mensajes: docs/ingestion-protocol.md.
"""

import logging
import secrets

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from detection_worker.clasificacion.estados import ClasificadorCinematico
from detection_worker.ingesta.protocolo import MensajeInvalidoError
from detection_worker.ingesta.service import ProcesadorCamara

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/ingesta", tags=["ingesta"])


@router.websocket("/{camara_id}")
async def recibir_video(websocket: WebSocket, camara_id: str) -> None:
    settings = websocket.app.state.settings
    componentes = websocket.app.state.componentes

    esperado = f"Bearer {settings.ingesta_token.get_secret_value()}"
    recibido = websocket.headers.get("authorization", "")
    if not secrets.compare_digest(recibido.encode(), esperado.encode()):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    if not settings.clasificacion.calibrado:
        logger.error("Video rechazado de %s: el umbral de velocidad no está calibrado", camara_id)
        await websocket.close(
            code=status.WS_1011_INTERNAL_ERROR, reason="Umbral de velocidad sin calibrar"
        )
        return
    logger.info("Cámara conectada: %s", camara_id)
    procesador = ProcesadorCamara(
        camara_id=camara_id,
        estimador=componentes.estimador,
        clasificador=ClasificadorCinematico(settings.clasificacion),
        publicador=componentes.publicador,
        almacen=componentes.almacen,
    )
    try:
        while True:
            mensaje = await websocket.receive_bytes()
            try:
                await procesador.procesar(mensaje)
            except MensajeInvalidoError as error:
                logger.warning("Mensaje descartado de %s: %s", camara_id, error)
    except WebSocketDisconnect:
        logger.info("Cámara desconectada: %s", camara_id)
    finally:
        await procesador.cerrar()
