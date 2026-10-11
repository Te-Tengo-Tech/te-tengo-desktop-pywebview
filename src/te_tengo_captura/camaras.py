"""The cameras of a linked PC (US-29, US-30): the PC reports its webcams, the owner assigns them
to rooms from the phone, and the PC follows (``docs/AGENT_CONTRACT.md``, "Cameras of a linked
PC").

* **Inventory:** at start and whenever a webcam is plugged in or out (the list is checked every
  ``REVISION_S`` seconds [implementation choice]) the PC sends ``PUT …/camaras/inventario`` with
  every webcam it detects, by the operating system's unique id (``captura/dispositivos.py``,
  CA-29.4). The answer is every webcam of the PC with its room and, when in use, its token.
* **Following the owner:** ``{"camara":…}`` on the PC's channel starts or stops a camera,
  ``{"buscarCamaras":true}`` reports the inventory again (CA-29.6), and after every (re)connection
  ``GET …/camaras`` reconciles what was missed offline. Only cameras in use capture.
* **One agent per camera in use** (``agente.Agente``): its own capture loop with its own MediaPipe
  landmarker and monotonic timestamps, heartbeat, outbox, clips, live view on its own MediaMTX path
  and control channel, with the camera's token. The user decides how many cameras a PC runs; the
  real frame rate of each is measured (no artificial limit).
* **Tokens:** camera tokens last as long as the PC's access token; they are renewed with
  ``POST …/camaras/tokens`` right after the PC's tokens, or after a camera's ``401``.
* **A camera retired in the app** answers ``401 PC_DESVINCULADA`` with its own token: the
  supervisor then asks the PC's state with the PC's token, which tells whether only that camera
  or the whole PC left (``vinculacion/sesion.py``).
* **Previews** (CA-29.7): a webcam «sin usar» has no channel of its own; the PC's channel carries
  its live view messages with ``camaraId``/``dispositivoId``, published like a live view for at
  most ``PREVIA_MAXIMA_S`` (nothing leaves the PC before ``transmitir``). The «Cámaras» tab's
  local preview (CA-29.8) opens a webcam that is not in use only while the window asks for it.
* **«Elegir aquí»** (CA-29.8): ``PUT …/camaras`` / ``DELETE …/camaras/{id}`` with the same rules
  as the app; when the app and the PC both change a camera the last change wins and the PC
  follows what the API answers (CA-29.10).
"""

import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from pydantic import ValidationError

from te_tengo_captura.agente import Agente
from te_tengo_captura.backend.errores import ErrorBackendError, PcDesvinculadaError
from te_tengo_captura.backend.modelos import (
    Ambiente,
    AsignacionCamara,
    CamaraDeLaPc,
    ModoVista,
    WebcamInventario,
)
from te_tengo_captura.captura.dispositivos import Dispositivo
from te_tengo_captura.captura.en_vivo import TransmisionEnVivo
from te_tengo_captura.captura.fuentes import FuenteVideo, Imagen
from te_tengo_captura.captura.publicador import Publicador
from te_tengo_captura.captura.vista_previa import VistaPreviaLocal

logger = logging.getLogger(__name__)

REVISION_S = 5.0  # how often the webcams are listed again (plugged in or out)
PREVIA_MAXIMA_S = 120.0  # contract: previews last 2 minutes at most
LECTURA_S = 1 / 15  # the readers of webcams not in use run at the live view's rate
MAXIMO_WEBCAMS = 32  # contract limit of the inventory


class ClienteCamaras(Protocol):
    """The part of ``backend.pc.ClientePc`` the supervisor uses."""

    def inventario(self, webcams: list[WebcamInventario]) -> list[CamaraDeLaPc]: ...

    def camaras(self) -> list[CamaraDeLaPc]: ...

    def tokens_de_camaras(self) -> list[CamaraDeLaPc]: ...

    def ambientes(self) -> list[Ambiente]: ...

    def asignar(self, asignacion: AsignacionCamara) -> CamaraDeLaPc: ...

    def dejar_de_usar(self, camara_id: str) -> None: ...


class TokenDeCamara:
    """A camera's token as its ``ClienteBackend`` sees it (``FuenteDeToken``)."""

    def __init__(self, camara_id: str, token: str, renovar_todos: Callable[[], None]) -> None:
        self._camara_id = camara_id
        self._token = token
        self._renovar_todos = renovar_todos
        self._candado = threading.Lock()

    @property
    def camara_id(self) -> str:
        return self._camara_id

    def token(self) -> str | None:
        return self._token

    def actualizar(self, token: str) -> None:
        self._token = token

    def renovar(self, rechazado: str | None) -> str:
        """After a ``401``: new tokens for every camera, unless another thread already did."""
        with self._candado:
            if rechazado is not None and self._token != rechazado:
                return self._token
            self._renovar_todos()
            return self._token


@dataclass(frozen=True, slots=True)
class ResultadoAsignacion:
    ok: bool
    codigo: str | None = None
    ambiente: str | None = None  # 409 AMBIENTE_OCUPADO: the room
    pc: str | None = None  # 409 AMBIENTE_OCUPADO: the PC that has a camera there


class LectorWebcam:
    """Reads a webcam that is not in use, while ``activo`` says so, for its consumers."""

    def __init__(
        self,
        fuente: FuenteVideo,
        consumidores: list[Callable[[float, Imagen], None]],
        activo: Callable[[], bool],
        nombre: str,
    ) -> None:
        self._fuente = fuente
        self._consumidores = consumidores
        self._activo = activo
        self._detenido = threading.Event()
        self._hilo = threading.Thread(target=self._correr, name=f"lector-{nombre}", daemon=True)

    @property
    def vivo(self) -> bool:
        return self._hilo.is_alive()

    def iniciar(self) -> None:
        self._hilo.start()

    def detener(self) -> None:
        self._detenido.set()
        if self._hilo.is_alive() and self._hilo is not threading.current_thread():
            self._hilo.join(3.0)

    def _correr(self) -> None:
        try:
            if not self._fuente.abrir():
                logger.info("No se pudo abrir la webcam para la vista previa")
                return
            while not self._detenido.is_set() and self._activo():
                lectura = self._fuente.leer()
                if lectura is None:
                    self._detenido.wait(LECTURA_S)
                    continue
                for consumidor in self._consumidores:
                    try:
                        consumidor(*lectura)
                    except Exception:
                        logger.exception("Error al entregar un fotograma de la vista previa")
        finally:
            self._fuente.cerrar()


class _PreviaRemota:
    """A preview requested from the app for a webcam «sin usar» (CA-29.7)."""

    def __init__(
        self,
        dispositivo_id: str,
        abrir: Callable[[str], FuenteVideo],
        fps: float,
        reloj: Callable[[], float],
        abrir_publicador: Callable[[str, float], Publicador] | None = None,
    ) -> None:
        self.dispositivo_id = dispositivo_id
        self._reloj = reloj
        self.hasta = reloj() + PREVIA_MAXIMA_S
        self.en_vivo = (
            TransmisionEnVivo(permitida=self.vigente, fps=fps, abrir_publicador=abrir_publicador)
            if abrir_publicador is not None
            else TransmisionEnVivo(permitida=self.vigente, fps=fps)
        )
        self._lector = LectorWebcam(
            abrir(dispositivo_id), [self.en_vivo.ofrecer], self.vigente, "previa"
        )

    def vigente(self) -> bool:
        return self._reloj() < self.hasta

    def iniciar(self, url: str, usuario: str | None, clave: str | None, modo: ModoVista) -> None:
        self.en_vivo.iniciar()
        self.en_vivo.transmitir(url, usuario, clave, modo)
        self._lector.iniciar()

    def detener(self) -> None:
        self.hasta = 0.0
        self.en_vivo.cerrar()
        self._lector.detener()


class SupervisorCamaras:
    def __init__(
        self,
        cliente: ClienteCamaras,
        crear_agente: Callable[[CamaraDeLaPc, TokenDeCamara], Agente],
        listar: Callable[[], list[Dispositivo]],
        abrir: Callable[[str], FuenteVideo],
        consentimiento: Callable[[], bool] = lambda: True,
        fps_vivo: float = 15.0,
        reloj: Callable[[], float] = time.monotonic,
        abrir_publicador: Callable[[str, float], Publicador] | None = None,
    ) -> None:
        self._abrir_publicador = abrir_publicador
        self._cliente = cliente
        self._crear_agente = crear_agente
        self._listar = listar
        self._abrir = abrir
        self._consentimiento = consentimiento
        self._fps_vivo = fps_vivo
        self._reloj = reloj
        self._candado = threading.RLock()
        self.camaras: dict[str, CamaraDeLaPc] = {}  # every webcam of the PC, by camaraId
        self.agentes: dict[str, Agente] = {}  # cameras in use, by camaraId
        self._tokens: dict[str, TokenDeCamara] = {}
        self.dispositivos: list[Dispositivo] | None = None  # detected now
        self._conocidos: set[str] | None = None  # device ids seen at the first listing
        self.nuevos: set[str] = set()  # plugged in after the agent started («Nueva»)
        self.elegidas_aqui: set[str] = set()  # camaraIds assigned from this PC (CA-29.8)
        self._previas: dict[str, _PreviaRemota] = {}
        self._locales: dict[str, tuple[VistaPreviaLocal, LectorWebcam]] = {}
        self.inventario_enviado = False
        # The activity log (US-33): what the app changed (heard here) and «Elegir aquí».
        self.al_actividad: Callable[[str, str], None] = lambda _texto, _quien: None
        self._detenido = threading.Event()
        self._despertar = threading.Event()
        self._pendiente_sincronizar = threading.Event()
        self._hilo = threading.Thread(target=self._correr, name="camaras", daemon=True)

    # ------------------------------------------------------------------ lifecycle

    def iniciar(self) -> None:
        self._hilo.start()

    def detener(self) -> None:
        self._detenido.set()
        self._despertar.set()
        if self._hilo.is_alive() and self._hilo is not threading.current_thread():
            self._hilo.join(5.0)
        with self._candado:
            agentes, self.agentes = list(self.agentes.values()), {}
            previas, self._previas = list(self._previas.values()), {}
            locales, self._locales = list(self._locales.values()), {}
        for agente in agentes:
            agente.detener()
        for previa in previas:
            previa.detener()
        for _vista, lector in locales:
            lector.detener()

    def bloquear(self) -> None:
        """The PC left the household: every camera stops capturing at once (CA-31.1)."""
        with self._candado:
            for agente in self.agentes.values():
                agente.bloquear()

    def secretos(self) -> list[str]:
        with self._candado:
            agentes = list(self.agentes.values())
        return [s for a in agentes for s in a.secretos()]

    # ------------------------------------------------------------------ webcams and inventory

    def listar(self) -> bool:
        """Lists the webcams; ``True`` if the set changed (then the inventory is due)."""
        try:
            dispositivos = self._listar()[:MAXIMO_WEBCAMS]
        except Exception:
            logger.exception("No se pudieron listar las webcams")
            dispositivos = []
        ids = {d.dispositivo_id for d in dispositivos}
        with self._candado:
            anteriores = (
                None if self.dispositivos is None else {d.dispositivo_id for d in self.dispositivos}
            )
            if self._conocidos is None:
                self._conocidos = set(ids)
            else:
                self.nuevos |= ids - self._conocidos
            self.dispositivos = dispositivos
        if anteriores != ids:
            logger.info("Webcams detectadas: %d", len(dispositivos))
        return anteriores != ids

    def reportar_inventario(self) -> bool:
        """``PUT …/camaras/inventario`` with what the PC detects now; ``True`` if it answered."""
        with self._candado:
            dispositivos = list(self.dispositivos or [])
        webcams = [
            WebcamInventario(dispositivo_id=d.dispositivo_id, nombre_dispositivo=d.nombre)
            for d in dispositivos
        ]
        try:
            camaras = self._cliente.inventario(webcams)
        except PcDesvinculadaError:
            raise
        except ErrorBackendError as error:
            logger.warning("No se pudo informar las webcams: %s", error)
            return False
        self.inventario_enviado = True
        self.reconciliar(camaras)
        return True

    def buscar_de_nuevo(self) -> bool:
        """«Buscar de nuevo» (CA-29.6), from the window or ``{"buscarCamaras":true}``."""
        self.listar()
        self.reportar_inventario()
        with self._candado:
            return bool(self.dispositivos)

    def sincronizar(self) -> None:
        """``GET …/camaras`` after (re)connecting: what the owner changed meanwhile."""
        try:
            camaras = self._cliente.camaras()
        except PcDesvinculadaError:
            raise
        except ErrorBackendError as error:
            logger.info("No se pudieron leer las cámaras de la PC: %s", error)
            return
        self.reconciliar(camaras)

    def renovar_tokens(self) -> None:
        """New per-camera tokens (after the PC's renewal or a camera's ``401``)."""
        try:
            camaras = self._cliente.tokens_de_camaras()
        except PcDesvinculadaError:
            raise
        except ErrorBackendError as error:
            logger.warning("No se pudieron renovar los tokens de las cámaras: %s", error)
            raise
        self.reconciliar(camaras, completo=False)

    # ------------------------------------------------------------------ the owner's changes

    def al_mensaje(self, mensaje: dict[str, Any]) -> None:
        """``{"camara":…}`` or ``{"buscarCamaras":true}`` on the PC's channel."""
        if mensaje.get("buscarCamaras") is True:
            self._despertar_con(self.buscar_de_nuevo)
            return
        datos = mensaje.get("camara")
        if not isinstance(datos, dict):
            return
        try:
            camara = CamaraDeLaPc.model_validate({"conectada": True, **datos})
        except ValidationError:
            logger.warning("Canal de la PC: cámara inválida ignorada")
            return
        with self._candado:
            anterior = self.camaras.get(camara.camara_id)
            self.camaras[camara.camara_id] = camara
            if not camara.en_uso:
                self.elegidas_aqui.discard(camara.camara_id)
        if camara.en_uso and (
            anterior is None
            or not anterior.en_uso
            or anterior.nombre_habitacion != camara.nombre_habitacion
        ):
            self.al_actividad(
                f"La familia eligió desde la app la {camara.nombre_dispositivo} para "
                f"{_arte(camara.nombre_habitacion or '')}",
                "app",
            )
        elif not camara.en_uso and anterior is not None and anterior.en_uso:
            self.al_actividad(
                f"La familia dejó de usar desde la app la {camara.nombre_dispositivo} "
                f"{_del(anterior.nombre_habitacion or '')}",
                "app",
            )
        if camara.en_uso:
            logger.info(
                "La familia eligió la cámara %s para %s",
                camara.nombre_dispositivo,
                camara.nombre_habitacion,
            )
            if anterior is not None and anterior.en_uso and camara.camara_id in self.agentes:
                self._renombrar(camara)
            else:
                self._despertar_con(self.renovar_tokens)  # its token comes with the tokens call
        else:
            logger.info("La familia dejó de usar la cámara %s", camara.nombre_dispositivo)
            self._detener(camara.camara_id)

    def camara_retirada(self, camara_id: str, motivo: str) -> None:
        """A camera's ``401 PC_DESVINCULADA`` or ``desvincular``: is it the camera or the PC?"""
        logger.info("La cámara %s ya no está en uso (%s); se revisa la PC", camara_id, motivo)
        self._pendiente_sincronizar.set()
        self._despertar.set()

    def reconciliar(self, camaras: list[CamaraDeLaPc], completo: bool = True) -> None:
        """Starts the cameras in use with a token and stops the others."""
        with self._candado:
            if completo:
                self.camaras = {c.camara_id: c for c in camaras}
            else:
                self.camaras.update({c.camara_id: c for c in camaras})
            en_uso = {c.camara_id: c for c in self.camaras.values() if c.en_uso}
            sobran = [cid for cid in self.agentes if cid not in en_uso]
        for camara_id in sobran:
            self._detener(camara_id)
        for camara in camaras:
            if not camara.en_uso:
                continue
            with self._candado:
                existente = self.agentes.get(camara.camara_id)
                token = self._tokens.get(camara.camara_id)
            if camara.token and token is not None:
                token.actualizar(camara.token)
            if existente is not None:
                if existente.ajustes.dispositivo_id != camara.dispositivo_id:
                    self._detener(camara.camara_id)  # moved to another webcam: start over
                else:
                    self._renombrar(camara)
                    continue
            if camara.token:
                self._iniciar(camara)

    # ------------------------------------------------------------------ «Elegir aquí» (CA-29.8)

    def ambientes(self) -> list[Ambiente]:
        return self._cliente.ambientes()

    def usar_aqui(
        self,
        dispositivo_id: str,
        ambiente_id: str | None,
        nombre_ambiente: str | None,
    ) -> ResultadoAsignacion:
        with self._candado:
            dispositivo = next(
                (d for d in self.dispositivos or [] if d.dispositivo_id == dispositivo_id), None
            )
            conocida = next(
                (c for c in self.camaras.values() if c.dispositivo_id == dispositivo_id), None
            )
        nombre = (
            dispositivo.nombre
            if dispositivo is not None
            else conocida.nombre_dispositivo
            if conocida is not None
            else dispositivo_id
        )
        try:
            camara = self._cliente.asignar(
                AsignacionCamara(
                    dispositivo_id=dispositivo_id,
                    nombre_dispositivo=nombre,
                    ambiente_id=ambiente_id,
                    nombre_ambiente=nombre_ambiente,
                )
            )
        except PcDesvinculadaError:
            raise
        except ErrorBackendError as error:
            otra = error.cuerpo.get("camara") if isinstance(error.cuerpo, dict) else None
            return ResultadoAsignacion(
                False,
                error.codigo or ("SIN_CONEXION" if error.estado is None else "ERROR"),
                ambiente=error.cuerpo.get("ambiente"),
                pc=otra.get("pcNombre") if isinstance(otra, dict) else None,
            )
        with self._candado:
            self.elegidas_aqui.add(camara.camara_id)
        antes = conocida.nombre_habitacion if conocida is not None and conocida.en_uso else None
        self.al_actividad(
            f"Desde esta PC: la cámara {camara.nombre_dispositivo} pasó "
            + (
                f"de {antes} a {camara.nombre_habitacion}"
                if antes
                else f"a {camara.nombre_habitacion}"
            ),
            "pc",
        )
        logger.info(
            "Desde esta PC: la cámara %s cuida ahora %s",
            camara.nombre_dispositivo,
            camara.nombre_habitacion,
        )
        self.reconciliar([camara], completo=False)
        return ResultadoAsignacion(True)

    def dejar_de_usar(self, camara_id: str) -> ResultadoAsignacion:
        try:
            self._cliente.dejar_de_usar(camara_id)
        except PcDesvinculadaError:
            raise
        except ErrorBackendError as error:
            return ResultadoAsignacion(False, error.codigo or "ERROR")
        with self._candado:
            camara = self.camaras.get(camara_id)
            if camara is not None:
                self.al_actividad(
                    f"Desde esta PC: la cámara {camara.nombre_dispositivo} ya no cuida "
                    f"{_arte(camara.nombre_habitacion or '')}",
                    "pc",
                )
                self.camaras[camara_id] = camara.model_copy(
                    update={"en_uso": False, "nombre_habitacion": None, "token": None}
                )
            self.elegidas_aqui.discard(camara_id)
        self._detener(camara_id)
        return ResultadoAsignacion(True)

    # ------------------------------------------------------------------ previews

    def previa_remota(
        self,
        dispositivo_id: str,
        transmitir: bool,
        url: str | None = None,
        usuario: str | None = None,
        clave: str | None = None,
        modo: ModoVista = ModoVista.VIDEO,
    ) -> None:
        """The preview of a webcam «sin usar» requested from the app (CA-29.7)."""
        with self._candado:
            anterior = self._previas.pop(dispositivo_id, None)
        if anterior is not None:
            anterior.detener()
        if not transmitir or not url:
            return
        local = self._locales.get(dispositivo_id)
        if local is not None:  # the PC's window was showing it: one reader per webcam
            local[1].detener()
            self._locales.pop(dispositivo_id, None)
        previa = _PreviaRemota(
            dispositivo_id, self._abrir, self._fps_vivo, self._reloj, self._abrir_publicador
        )
        with self._candado:
            self._previas[dispositivo_id] = previa
        logger.info("Vista previa de una webcam sin usar pedida desde la app")
        previa.iniciar(url, usuario, clave, modo)

    def cambiar_modo_previa(self, dispositivo_id: str, modo: ModoVista) -> None:
        previa = self._previas.get(dispositivo_id)
        if previa is not None:
            previa.en_vivo.cambiar_modo(modo)

    @property
    def mirando(self) -> set[str]:
        """Webcams a family member is previewing from the app right now (the violet light)."""
        with self._candado:
            return {d for d, p in self._previas.items() if p.vigente()}

    def vista_previa_jpeg(self, clave: str) -> bytes | None:
        """The «Cámaras» tab's local preview: a camera in use or a webcam «sin usar»."""
        with self._candado:
            agente = self.agentes.get(clave)
        if agente is not None:
            return agente.vista_previa.jpeg()
        if not self._consentimiento():
            return None  # no webcam is opened without the monitoring consent
        with self._candado:
            if clave in self._previas:
                return None
            if not any(d.dispositivo_id == clave for d in self.dispositivos or []):
                return None
            local = self._locales.get(clave)
            if local is None or not local[1].vivo:
                vista = VistaPreviaLocal(self._reloj)
                lector = LectorWebcam(
                    self._abrir(clave), [vista.ofrecer], lambda: vista.pedida, "local"
                )
                self._locales[clave] = (vista, lector)
                vista.jpeg()  # marks it as asked for before the reader starts
                lector.iniciar()
                return None
        return local[0].jpeg()

    # ------------------------------------------------------------------ state

    def fps(self) -> dict[str, float]:
        with self._candado:
            return {cid: a.bucle.fps for cid, a in self.agentes.items()}

    # ------------------------------------------------------------------ internals

    def _iniciar(self, camara: CamaraDeLaPc) -> None:
        with self._candado:
            if camara.camara_id in self.agentes or not camara.token:
                return
            token = TokenDeCamara(camara.camara_id, camara.token, self.renovar_tokens)
            self._tokens[camara.camara_id] = token
            local = self._locales.pop(camara.dispositivo_id, None)
        if local is not None:
            local[1].detener()  # the camera's own agent opens the webcam now
        agente = self._crear_agente(camara, token)
        with self._candado:
            self.agentes[camara.camara_id] = agente
        logger.info(
            "Cámara %s en uso: %s (%s)",
            camara.camara_id,
            camara.nombre_habitacion,
            camara.nombre_dispositivo,
        )
        agente.iniciar()

    def _renombrar(self, camara: CamaraDeLaPc) -> None:
        agente = self.agentes.get(camara.camara_id)
        if agente is not None and camara.nombre_habitacion:
            agente.renombrar(camara.nombre_habitacion)

    def _detener(self, camara_id: str) -> None:
        with self._candado:
            agente = self.agentes.pop(camara_id, None)
            self._tokens.pop(camara_id, None)
        if agente is not None:
            agente.bloquear()
            logger.info("Cámara %s detenida", camara_id)
            threading.Thread(target=agente.detener, name="detener-camara", daemon=True).start()

    def _despertar_con(self, accion: Callable[[], object]) -> None:
        def correr() -> None:
            try:
                accion()
            except PcDesvinculadaError:
                pass  # the session already told the coordinator
            except ErrorBackendError as error:
                logger.warning("Cámaras: %s", error)

        threading.Thread(target=correr, name="camaras-accion", daemon=True).start()

    def _correr(self) -> None:
        primera = True
        while not self._detenido.is_set():
            try:
                cambio = self.listar()
                if primera or cambio or not self.inventario_enviado:
                    self.reportar_inventario()
                if self._pendiente_sincronizar.is_set():
                    self._pendiente_sincronizar.clear()
                    self.sincronizar()
                primera = False
            except PcDesvinculadaError:
                return
            except Exception:
                logger.exception("Error inesperado al revisar las cámaras")
            self._despertar.wait(REVISION_S)
            self._despertar.clear()
            self._cerrar_locales_sin_uso()

    def _cerrar_locales_sin_uso(self) -> None:
        with self._candado:
            terminados = [d for d, (v, lector) in self._locales.items() if not lector.vivo]
            for dispositivo_id in terminados:
                self._locales.pop(dispositivo_id, None)
            vencidas = [d for d, p in self._previas.items() if not p.vigente()]
        for dispositivo_id in vencidas:
            self.previa_remota(dispositivo_id, False)


_ARTE = {
    "sala": "la Sala",
    "dormitorio": "el Dormitorio",
    "cocina": "la Cocina",
    "comedor": "el Comedor",
    "pasillo": "el Pasillo",
}


def _arte(habitacion: str) -> str:
    """proto.js ``ROOM_ART``: «la Sala», «el Dormitorio», «Sala comedor» in quotes."""
    return _ARTE.get(habitacion.strip().lower(), f"«{habitacion}»")


def _del(habitacion: str) -> str:
    texto = _arte(habitacion)
    return "del " + texto[3:] if texto.startswith("el ") else "de " + texto
