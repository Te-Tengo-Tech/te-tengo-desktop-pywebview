"""What the PC is right now, and the moves between those states (US-28, US-31).

* **Installation** (``config.toml`` with ``credencial_instalacion``): the project team's camera
  (``agente.Agente``), unchanged.
* **Linking** («Vincular esta PC», D-28.1): no credentials yet; ``vinculacion.Vinculador`` shows
  the QR and the code until the owner approves it in the app.
* **Linked PC** (``agente_pc.AgentePc``): its tokens are in the OS credential store.

Moves:

* approved in the app → the tokens are stored, the PC starts and the window says «Esta PC quedó
  vinculada a la casa de …» (D-28.4) until «Ir a Estado»;
* removed from the app (``{"desvincular":true}``, ``401 PC_DESVINCULADA``, or ``invalid_grant``
  when renewing) → capture stops at once, the credentials are deleted (the tokens, or the
  installation credential from ``config.toml``), and the window says «Esta PC se quitó de la casa
  de …» (D-31.2) with «Vincular de nuevo» (CA-31.1, CA-31.2). After 90 days or more without
  connecting it goes straight to the code with «Esta PC estuvo más de 90 días sin conexión»
  (CA-28.7);
* «Desvincular esta PC» from the PC (CA-31.3, CA-31.6) → the API is told (or the revocation is
  left pending until there is internet), the credentials and, if asked, the data saved on the PC
  are deleted, and the code is shown again.

The coordinator also runs the state notifier: every second the window, the tray icon and the
system notices get an ``EstadoVentana`` (``suscribir``). Moves triggered by a worker thread run
in their own thread, so no thread ever waits for itself to stop.
"""

import json
import logging
import os
import shutil
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta, tzinfo
from enum import StrEnum
from pathlib import Path
from typing import Any

import httpx

from te_tengo_captura.actividad import RegistroActividad, para_la_ventana
from te_tengo_captura.agente import Agente
from te_tengo_captura.agente_pc import (
    AgentePc,
    FabricaCamaras,
    enviar_revocacion_pendiente,
    leer_pc,
)
from te_tengo_captura.almacen.gestor import AjustesAlmacen, AlmacenLocal
from te_tengo_captura.almacen.indice import TipoArchivo
from te_tengo_captura.almacen.repeticion import Repeticion
from te_tengo_captura.backend.errores import ErrorBackendError
from te_tengo_captura.backend.modelos import EstadoMovimientos
from te_tengo_captura.backend.pc import ClientePc
from te_tengo_captura.captura.dispositivos import Dispositivo, listar_dispositivos
from te_tengo_captura.diagnostico import exportar, nombre_archivo
from te_tengo_captura.diario import Diario
from te_tengo_captura.estado import EstadoAgente, EstadoBandeja, Hogar, habitacion_arte, hora_local
from te_tengo_captura.sistema import nombre_pc, sistema_operativo
from te_tengo_captura.vinculacion.credenciales import (
    AlmacenCredenciales,
    AlmacenNoDisponibleError,
    CredencialesPc,
    Llavero,
)
from te_tengo_captura.vinculacion.maquina import Fase, HiloVinculacion, Vinculador
from te_tengo_captura.vinculacion.oauth import ClienteOAuth, TokensPc
from te_tengo_captura.vinculacion.qr import codigo_qr
from te_tengo_captura.vinculacion.sesion import SesionPc, credenciales_de

logger = logging.getLogger(__name__)

INTERVALO_ESTADO_S = 1.0  # the window's countdowns move every second
DIAS_SIN_CONEXION = 90  # CA-28.7
ARCHIVO_CONTACTO = "ultimo_contacto.json"
ARCHIVO_QUITADA = "quitada.json"
REVOCACION_REINTENTO_S = 30.0
# What a removed PC deletes from its data folder: the outbox and the capture state belong to the
# identity that left (the cameras' folders arrive with US-29).
ESTADO_DE_LA_IDENTIDAD = (
    "envios.sqlite3",
    "clips",
    "estado_captura.json",
    "pc.json",
    "camaras",
    "actividad.jsonl",
    "actividad-enviada.txt",
)
ARCHIVO_VENTANA = "ventana.json"  # the advanced mode's switch (off by default, CA-32.1)


class Pantalla(StrEnum):
    VINCULAR = "vincular"
    VINCULADA = "vinculada"
    RECHAZADA = "rechazada"
    QUITADA = "quitada"
    PRINCIPAL = "main"


@dataclass(frozen=True, slots=True)
class EstadoVentana:
    """What the window, the tray icon and the system notices get every second."""

    pantalla: Pantalla
    bandeja: EstadoBandeja
    agente: EstadoAgente | None
    datos: dict[str, Any] = field(default_factory=dict)
    quitada: bool = False  # removed from the app (D-31.2): a system notice when hidden

    def a_json(self) -> dict[str, Any]:
        return self.datos


class Coordinador:
    def __init__(
        self,
        version: str,
        api_url: str,
        directorio_datos: Path,
        almacen: AlmacenCredenciales,
        instalacion: Callable[[Callable[[str], None]], Agente] | None = None,
        olvidar_instalacion: Callable[[], None] = lambda: None,
        transporte: httpx.BaseTransport | None = None,
        canal_pc: bool = True,
        listar: Callable[[], list[Dispositivo]] = listar_dispositivos,
        reloj: Callable[[], float] = time.time,
        zona: tzinfo | None = None,
        fabrica: FabricaCamaras | None = None,
        diario: Diario | None = None,
        registros: Path | None = None,
        llavero: Llavero | None = None,
        carpeta_datos: Path | None = None,
    ) -> None:
        """``fabrica`` builds the agents of a linked PC's cameras (US-29); ``diario`` keeps the
        advanced mode's live log (US-32); ``registros`` is the log folder (diagnostic, US-34)."""
        self.version = version
        self.diario = diario or Diario()
        self._registros = registros
        self.actividad = RegistroActividad(directorio_datos)
        # Local storage (US-38): its folder may be anywhere; its settings stay with the agent.
        self._llavero = llavero if llavero is not None else almacen.llavero
        self._directorio = directorio_datos
        self._carpeta_datos = carpeta_datos or directorio_datos / "Datos"
        self.almacen = self._nuevo_almacen()
        self._cpu = MedidorProceso()
        self._fabrica = fabrica
        self._api_url = api_url
        self._almacen = almacen
        self._instalacion = instalacion
        self._olvidar_instalacion = olvidar_instalacion
        self._transporte = transporte
        self._canal_pc = canal_pc
        self._listar = listar
        self._reloj = reloj
        self._zona = zona
        self._oauth = ClienteOAuth(api_url, transporte)
        self._candado = threading.RLock()
        self._candado_bandera = threading.Lock()  # never held while threads are joined
        self.agente: Agente | None = None
        self.pc: AgentePc | None = None
        self._vinculador: Vinculador | None = None
        self._hilo_vinculacion: HiloVinculacion | None = None
        self._pantalla: Pantalla | None = None  # VINCULADA or QUITADA over the current mode
        self._quitada: dict[str, str] = {}
        self._re90 = False
        self._repetidor: Repeticion | None = None
        self._repetidor_de: AlmacenLocal | None = None
        self._desvinculando = False
        self._tamano: tuple[float, int] | None = None
        self._avanzado = bool((self._leer_json(ARCHIVO_VENTANA) or {}).get("modoAvanzado", False))
        self._oyentes: list[Callable[[EstadoVentana], None]] = []
        self._detenido = threading.Event()
        self._hilo_estado = threading.Thread(target=self._notificar, name="estado", daemon=True)
        self._hilo_revocacion = threading.Thread(
            target=self._revocar_pendiente, name="revocacion", daemon=True
        )

    # ------------------------------------------------------------------ lifecycle

    def iniciar(self) -> None:
        self._directorio.mkdir(parents=True, exist_ok=True)
        self.diario.activo = self.modo_avanzado
        self.almacen.iniciar(self._consultar_movimientos)
        if self._instalacion is not None:
            self.agente = self._instalacion(self._al_desvincular)
            self.agente.conectar_almacen(self.almacen)
            self.agente.iniciar()
            self.almacen.pedir_permiso()
        else:
            credenciales = self._leer_credenciales()
            if credenciales is not None:
                self._iniciar_pc(credenciales)
            else:
                self._iniciar_vinculacion()
        self._hilo_revocacion.start()
        self._hilo_estado.start()

    def detener(self) -> None:
        self._detenido.set()
        with self._candado:
            self._detener_modo()
        self.almacen.detener()
        self._oauth.cerrar()

    def secretos(self) -> list[str]:
        secretos: list[str] = []
        if self.agente is not None:
            secretos += self.agente.secretos()
        if self.pc is not None:
            secretos += self.pc.secretos()
        return secretos

    # ------------------------------------------------------------------ state

    def suscribir(self, oyente: Callable[[EstadoVentana], None]) -> None:
        """``oyente`` gets the state every second (window, tray); it runs in a worker thread."""
        self._oyentes.append(oyente)

    def publicar_estado(self) -> None:
        estado = self.estado()
        for oyente in list(self._oyentes):
            try:
                oyente(estado)
            except Exception:
                logger.exception("Error al mostrar el estado")

    def estado(self) -> EstadoVentana:
        with self._candado:
            pantalla, agente, pc, vinculador = (
                self._pantalla,
                self.agente,
                self.pc,
                self._vinculador,
            )
        if pantalla is Pantalla.QUITADA:
            datos = {"screen": "quitada", **self._quitada}
            return EstadoVentana(
                Pantalla.QUITADA,
                EstadoBandeja("off", "se quitó de la vivienda"),
                None,
                datos,
                quitada=True,
            )
        if agente is not None:
            e = agente.estado()
            return EstadoVentana(
                Pantalla.PRINCIPAL,
                e.bandeja,
                e,
                {**e.a_json(), "advanced": self._avanzado, "store": self.almacen.estado()},
            )
        if pc is not None:
            e = pc.estado()
            if pantalla is Pantalla.VINCULADA:
                return EstadoVentana(
                    Pantalla.VINCULADA,
                    EstadoBandeja("warn", "falta elegir las cámaras en la app"),
                    e,
                    self._datos_vinculada(pc, e),
                )
            return EstadoVentana(
                Pantalla.PRINCIPAL,
                e.bandeja,
                e,
                {
                    **e.a_json(),
                    "unlink": True,
                    "dataBytes": self._tamano_datos(),
                    "advanced": self._avanzado,
                    "store": self.almacen.estado(),
                },
            )
        if vinculador is not None and vinculador.fase is Fase.RECHAZADA:
            return EstadoVentana(
                Pantalla.RECHAZADA,
                EstadoBandeja("off", "sin vincular"),
                None,
                {"screen": "rechazada"},
            )
        return EstadoVentana(
            Pantalla.VINCULAR,
            EstadoBandeja("off", "sin vincular"),
            None,
            self._datos_vincular(vinculador),
        )

    def _datos_vincular(self, vinculador: Vinculador | None) -> dict[str, Any]:
        v = vinculador.estado() if vinculador is not None else None
        qr = codigo_qr(v.url_completa) if v is not None and v.url_completa else None
        return {
            "screen": "vincular",
            "pcname": nombre_pc(),
            "pair": {
                "fase": v.fase.value if v else Fase.PIDIENDO.value,
                "code": v.codigo if v else None,
                "url": v.url if v else None,
                "qr": {"n": qr.modulos, "d": qr.ruta} if qr else None,
                "left": v.segundos if v else 0,
                "renewed": v.renovado if v else False,
                "retry": v.reintento if v else 0,
                "re90": self._re90,
            },
        }

    def _datos_vinculada(self, pc: AgentePc, e: EstadoAgente) -> dict[str, Any]:
        datos = pc.latido.pc
        a_las = hora_local(datos.vinculada_en, self._zona) if datos is not None else ""
        return {
            **e.a_json(),
            "screen": "vinculada",
            "linkedBy": datos.vinculada_por if datos is not None else None,
            "linkedAt": a_las,
        }

    # ------------------------------------------------------------------ readiness (splash)

    def webcam_resuelta(self) -> bool:
        agente = self.agente
        if agente is not None:
            latido = agente.latido
            no_permitida = latido.en_linea is not None and not latido.captura_permitida()
            return agente.captador.conectada is not None or no_permitida
        pc = self.pc
        return pc is None or pc.webcams_listadas

    def conexion_resuelta(self) -> bool:
        if self.agente is not None:
            return self.agente.latido.en_linea is not None
        if self.pc is not None:
            return self.pc.latido.en_linea is not None
        vinculador = self._vinculador
        return vinculador is None or vinculador.fase is not Fase.PIDIENDO

    # ------------------------------------------------------------------ bridge actions

    def buscar_webcam(self) -> bool:
        if self.agente is not None:
            return self.agente.buscar_webcam()
        if self.pc is not None:
            return self.pc.buscar_webcams()
        return False

    def reintentar_ahora(self) -> bool:
        if self.agente is not None:
            return self.agente.reintentar_ahora()
        if self.pc is not None:
            return self.pc.reintentar_ahora()
        vinculador, hilo = self._vinculador, self._hilo_vinculacion
        if vinculador is not None and hilo is not None:
            vinculador.reintentar_ahora()
            hilo.despertar()
        return False

    def vista_previa_jpeg(self, clave: str) -> bytes | None:
        if self.agente is not None:
            return self.agente.vista_previa_jpeg(clave)
        if self.pc is not None:
            return self.pc.vista_previa_jpeg(clave)
        return None

    def ambientes(self) -> list[dict[str, Any]]:
        """The household's rooms for «Elegir aquí» (CA-29.8), with the camera in each."""
        pc = self.pc
        if pc is None:
            return []
        try:
            ambientes = pc.ambientes()
        except ErrorBackendError:
            return []
        propia = pc.sesion.pc_id
        return [
            {
                "id": a.id,
                "nombre": a.nombre,
                "camaras": [
                    {"id": c.id, "pc": c.pc_nombre, "estaPc": c.pc_id == propia} for c in a.camaras
                ],
            }
            for a in ambientes
        ]

    def usar_aqui(
        self, dispositivo_id: str, ambiente_id: str | None, nombre: str | None
    ) -> dict[str, Any]:
        """«Usar esta cámara» / «Guardar cambio» from the PC (CA-29.8)."""
        pc = self.pc
        if pc is None:
            return {"ok": False, "codigo": "SIN_PC"}
        try:
            r = pc.usar_aqui(dispositivo_id, ambiente_id, nombre)
        except ErrorBackendError:
            return {"ok": False, "codigo": "PC_DESVINCULADA"}
        return {"ok": r.ok, "codigo": r.codigo, "ambiente": r.ambiente, "pc": r.pc}

    def dejar_de_usar(self, camara_id: str) -> dict[str, Any]:
        pc = self.pc
        if pc is None:
            return {"ok": False}
        try:
            r = pc.dejar_de_usar(camara_id)
        except ErrorBackendError:
            return {"ok": False, "codigo": "PC_DESVINCULADA"}
        return {"ok": r.ok, "codigo": r.codigo}

    # ------------------------------------------------------------------ advanced (US-32 to US-34)

    @property
    def modo_avanzado(self) -> bool:
        return self._avanzado

    def cambiar_modo_avanzado(self, activar: bool) -> bool:
        """The switch of «Avanzado»; the change goes to the activity log (CA-32.1)."""
        if activar == self.modo_avanzado:
            return activar
        self._guardar_json(ARCHIVO_VENTANA, {"modoAvanzado": activar})
        self._avanzado = activar
        self.diario.activo = activar
        if not activar:
            self.diario.vaciar()
        self.actividad.anotar(
            "Desde esta PC: se activó el modo avanzado"
            if activar
            else "Desde esta PC: se desactivó el modo avanzado",
            tipo="MODO_AVANZADO_ACTIVADO" if activar else "MODO_AVANZADO_DESACTIVADO",
        )
        return activar

    def _agentes(self) -> dict[str, Agente]:
        if self.agente is not None:
            return {self.agente.clave_camara: self.agente}
        if self.pc is not None:
            with self.pc.camaras._candado:
                return dict(self.pc.camaras.agentes)
        return {}

    def registro(self, camara: str, ultimo: int) -> list[dict[str, Any]]:
        """New lines of a camera's live log since ``ultimo`` (CA-32.2)."""
        if not self.diario.activo:
            return []
        return [linea.a_json() for linea in self.diario.desde(camara, ultimo)]

    def medidores(self, camara: str) -> dict[str, Any] | None:
        """A camera's meters (CA-32.3, CA-32.4), with this program's CPU use."""
        agente = self._agentes().get(camara)
        if agente is None or not self.diario.activo:
            return None
        return {**agente.medidores(), "cpu": round(self._cpu.medir())}

    def lista_actividad(self) -> list[dict[str, Any]]:
        return para_la_ventana(self.actividad.entradas(), self._zona)

    def nombre_diagnostico(self) -> str:
        nombre = self.pc.datos_pc().nombre if self.pc is not None else nombre_pc()
        return nombre_archivo(
            nombre, datetime.fromtimestamp(self._reloj(), UTC).astimezone(self._zona).date()
        )

    def datos_diagnostico(self) -> dict[str, Any]:
        """What the support team gets (CA-34.1): no credential, image or landmark."""
        e = self.estado().agente
        camaras = []
        for clave, agente in self._agentes().items():
            fila = agente.camara()
            camaras.append(
                {
                    "habitacion": fila.nombre_habitacion,
                    "dispositivo": fila.dispositivo,
                    "conectada": fila.webcam_conectada,
                    "fps": round(agente.bucle.fps, 1),
                    "umbrales": agente.bucle.umbrales.model_dump(),
                    "camaraId": clave,
                }
            )
        return {
            "programa": f"Te Tengo Captura {self.version}",
            "sistema": sistema_operativo(),
            "pc": self.pc.datos_pc().nombre if self.pc is not None else nombre_pc(),
            "modo": "instalacion"
            if self.agente is not None
            else "pc"
            if self.pc is not None
            else "sin_vincular",
            "enLinea": e.entradas.en_linea if e is not None else None,
            "situacion": e.situacion.value if e is not None else None,
            "webcamsDetectadas": [w.nombre for w in e.entradas.webcams] if e is not None else [],
            "camaras": camaras,
            "generado": datetime.fromtimestamp(self._reloj(), UTC).isoformat(),
        }

    def exportar_diagnostico(self, destino: Path) -> dict[str, Any]:
        """«Elegir dónde guardar»: the zip at ``destino`` (CA-34.1 to CA-34.3)."""
        try:
            tamano = exportar(
                destino,
                self._registros or self._directorio,
                self.datos_diagnostico(),
                self.secretos(),
            )
        except OSError as error:
            logger.warning("No se pudo guardar el diagnóstico: %s", error)
            return {"ok": False}
        logger.info("Diagnóstico guardado (%d bytes)", tamano)
        return {"ok": True, "ruta": str(destino), "nombre": destino.name, "tamano": tamano}

    def otro_codigo(self) -> None:
        """«Mostrar otro código» (D-28.5)."""
        vinculador, hilo = self._vinculador, self._hilo_vinculacion
        if vinculador is not None and hilo is not None:
            vinculador.otro_codigo()
            hilo.despertar()

    def vincular_de_nuevo(self) -> None:
        """«Vincular de nuevo» (D-31.2)."""
        with self._candado:
            if self._pantalla is Pantalla.QUITADA:
                self._pantalla = None
                self._borrar_archivo(ARCHIVO_QUITADA)
                self._iniciar_vinculacion()

    def ir_a_estado(self) -> None:
        with self._candado:
            if self._pantalla is Pantalla.VINCULADA:
                self._pantalla = None

    def desvincular(self, borrar_datos: bool) -> dict[str, bool]:
        """«Desvincular esta PC» (CA-31.3, CA-31.6): ``avisada`` if the API heard it now."""
        with self._candado_bandera:
            pc = self.pc
            if pc is None or self._desvinculando:
                return {"ok": False, "avisada": False}
            self._desvinculando = True
        avisada = pc.desvincular(borrar_datos)
        with self._candado:
            self._detener_modo()
            self._borrar_credenciales()
            self._borrar_identidad()
            if borrar_datos:
                self.borrar_datos_locales()
            self._pantalla = None
            self._iniciar_vinculacion()
            self._desvinculando = False
        return {"ok": True, "avisada": avisada}

    def borrar_datos_locales(self) -> None:
        """«Borrar también los datos guardados en esta PC» (CA-31.6): movements, video and clips
        of the data folder, and the key that encrypted them."""
        shutil.rmtree(self._directorio / "clips", ignore_errors=True)
        self.almacen.borrar_todo()
        self.almacen = self._nuevo_almacen()
        self.almacen.iniciar(self._consultar_movimientos)

    def _nuevo_almacen(self) -> AlmacenLocal:
        return AlmacenLocal(self._directorio, self._carpeta_datos, self._llavero)

    def _consultar_movimientos(self) -> EstadoMovimientos:
        """``GET /api/agente/movimientos/estado`` with the PC's or the camera's token."""
        if self.pc is not None:
            return self.pc.estado_movimientos()
        if self.agente is not None:
            return self.agente.estado_movimientos()
        raise ErrorBackendError("Sin vincular")

    # ------------------------------------------------------------------ storage (US-38, US-35)

    def cambiar_almacenamiento(self, cambios: dict[str, Any]) -> dict[str, Any]:
        """A setting of «Almacenamiento»: one activity entry per setting (contract)."""
        permitidos = set(AjustesAlmacen.__dataclass_fields__) - {"carpeta"}
        validos = {k: v for k, v in cambios.items() if k in permitidos}
        if (
            "movimientos" in validos
            and validos["movimientos"]
            and not self.almacen.puede_movimientos
        ):
            return {"ok": False, "codigo": "SIN_PERMISO"}  # CA-35.3: disabled with its reason
        for cambio in self.almacen.cambiar(**validos):
            self.actividad.anotar(
                cambio.texto,
                tipo="GUARDADO_LOCAL_CAMBIADO",
                objeto=cambio.objeto,
                anterior=cambio.anterior,
                nuevo=cambio.nuevo,
            )
        return {"ok": True}

    def cambiar_carpeta(self, nueva: Path) -> dict[str, Any]:
        """«Cambiar carpeta»: moves the files while detection goes on (CA-38.1)."""

        def terminado(ok: bool) -> None:
            if ok:
                self.actividad.anotar(
                    "Desde esta PC: se cambió la carpeta de los datos",
                    tipo="GUARDADO_LOCAL_CAMBIADO",
                    objeto="Carpeta",
                )

        self.almacen.mover_carpeta(nueva, terminado)
        return {"ok": True}

    def borrar_movimientos(self) -> dict[str, Any]:
        """«Borrar» after the movement consent was revoked (CA-35.4)."""
        bytes_borrados = self.almacen.borrar_tipo(TipoArchivo.MOVIMIENTOS)
        self.actividad.anotar(
            "Desde esta PC: se borraron los movimientos guardados",
            tipo="DATOS_LOCALES_ELIMINADOS",
            objeto="Movimientos",
        )
        return {"ok": True, "bytes": bytes_borrados}

    def conservar_movimientos(self) -> dict[str, Any]:
        self.almacen.conservar()
        return {"ok": True}

    # ------------------------------------------------------------------ «Ver qué pasó» (US-39)

    def _repeticion(self) -> Repeticion:
        with self._candado_bandera:
            if self._repetidor is None or self._repetidor_de is not self.almacen:
                self._repetidor = Repeticion(self.almacen, self._zona)
                self._repetidor_de = self.almacen
            return self._repetidor

    def repeticion(self) -> dict[str, Any]:
        """What can be replayed: the cameras with their days with data (CA-39.2, CA-39.4)."""
        r = self._repeticion()
        hoy = datetime.now(self._zona).date()
        camaras = []
        for clave, agente in self._agentes().items():
            dias = r.dias(clave)
            desde = r.datos_desde(clave)
            camaras.append(
                {
                    "id": clave,
                    "room": agente.nombre_habitacion,
                    "dias": [_dia(d, hoy) for d in dias],
                    "desde": (
                        datetime.fromtimestamp(desde / 1000, UTC)
                        .astimezone(self._zona)
                        .strftime("%d/%m/%Y")
                        if desde is not None
                        else None
                    ),
                    "desdeMs": desde,
                    "hastaMs": r.datos_hasta(clave),
                }
            )
        return {"permitida": r.permitida, "camaras": camaras}

    def repeticion_ventana(self, camara: str, desde_ms: int, hasta_ms: int) -> dict[str, Any]:
        return self._repeticion().abrir(camara, int(desde_ms), int(hasta_ms))

    def repeticion_poses(self, camara: str, desde_ms: int, hasta_ms: int) -> dict[str, Any]:
        return self._repeticion().poses(camara, int(desde_ms), int(hasta_ms))

    def repeticion_video(self, camara: str, t_ms: int) -> bytes | None:
        return self._repeticion().fotograma_video(camara, int(t_ms))

    def cerrar_repeticion(
        self, camara: str, desde_ms: int, hasta_ms: int, segundos: float
    ) -> dict[str, Any]:
        """«Volver»: the replay is written in the activity log (CA-39.3) and memory is freed."""
        self._repeticion().cerrar()
        agente = self._agentes().get(camara)
        habitacion = agente.nombre_habitacion if agente is not None else camara
        inicio = datetime.fromtimestamp(int(desde_ms) / 1000, UTC).astimezone(self._zona)
        fin = datetime.fromtimestamp(int(hasta_ms) / 1000, UTC).astimezone(self._zona)
        minutos = max(1, round(float(segundos) / 60))
        self.actividad.anotar(
            f"Desde esta PC: se vio qué pasó en {habitacion_arte(habitacion)} "
            f"({inicio:%d/%m %H:%M}–{fin:%H:%M}, {minutos} min)"
        )
        return {"ok": True}

    # ------------------------------------------------------------------ moves

    def _al_desvincular(self, motivo: str) -> None:
        """The PC left the household (any worker thread): handled in a thread of its own."""
        with self._candado_bandera:
            if self._desvinculando:
                return
            self._desvinculando = True
        pc = self.pc
        if pc is not None:
            pc.bloquear()  # capture stops now, before the threads are stopped (CA-31.1)
        threading.Thread(
            target=self._quitar, args=(motivo,), name="desvincular", daemon=True
        ).start()

    def _quitar(self, motivo: str) -> None:
        with self._candado:
            hogar = self._hogar_actual()
            sin_contacto = self._dias_sin_contacto()
            self._detener_modo()
            self._borrar_credenciales()
            self._borrar_identidad()
            if motivo == "invalid_grant" and sin_contacto >= DIAS_SIN_CONEXION:
                logger.warning(
                    "Esta PC estuvo %d días sin conexión: hay que vincularla", sin_contacto
                )
                self._re90 = True
                self._pantalla = None
                self._iniciar_vinculacion()
            else:
                self._quitada = {
                    "who": hogar.nombre_adulto_mayor,
                    "at": hora_local(datetime.fromtimestamp(self._reloj(), UTC), self._zona),
                }
                self._guardar_json(ARCHIVO_QUITADA, self._quitada)
                self._pantalla = Pantalla.QUITADA
            self._desvinculando = False
        self.publicar_estado()

    def _vinculada(self, tokens: TokensPc) -> None:
        """The owner approved the link in the app (the pairing thread)."""
        credenciales = credenciales_de(tokens, self._reloj())
        try:
            self._almacen.guardar(credenciales)
        except AlmacenNoDisponibleError as error:
            logger.error("No se pudieron guardar los tokens de la PC (%s)", error)
        with self._candado:
            self._vinculador, self._hilo_vinculacion = None, None
            self._re90 = False
            self._iniciar_pc(credenciales)
            self._pantalla = Pantalla.VINCULADA
        threading.Thread(target=self._anotar_vinculacion, name="actividad", daemon=True).start()
        self.publicar_estado()

    def _anotar_vinculacion(self) -> None:
        """«Carmen vinculó la PC Sala-Rosa» once the PC knows who approved it."""
        for _ in range(50):
            pc = self.pc
            if pc is None or self._detenido.is_set():
                return
            datos = pc.latido.pc
            if datos is not None:
                quien = datos.vinculada_por or "La familia"
                self.actividad.anotar(
                    f"{quien} vinculó la PC {datos.nombre}", quien=_iniciales(quien)
                )
                return
            self._detenido.wait(0.2)

    def _iniciar_pc(self, credenciales: CredencialesPc) -> None:
        sesion = SesionPc(self._oauth, self._almacen, credenciales, self._al_desvincular)
        cliente = ClientePc(self._api_url, sesion, self._transporte)
        self.pc = AgentePc(
            self._api_url,
            sesion,
            cliente,
            self._oauth,
            self._almacen,
            self._directorio,
            self.version,
            listar=self._listar,
            canal=self._canal_pc,
            zona=self._zona,
            al_contactar=self._contacto,
            fabrica=self._fabrica,
            actividad=self.actividad,
            almacen_local=self.almacen,
        )
        self.pc.iniciar()
        self.almacen.pedir_permiso()

    def _iniciar_vinculacion(self) -> None:
        quitada = self._leer_json(ARCHIVO_QUITADA)
        if quitada and self._pantalla is None and not self._re90:
            self._quitada = {str(k): str(v) for k, v in quitada.items()}
            self._pantalla = Pantalla.QUITADA
            return
        self._vinculador = Vinculador(
            self._oauth, nombre_pc(), sistema_operativo(), self.version, self._vinculada
        )
        self._hilo_vinculacion = HiloVinculacion(self._vinculador)
        self._hilo_vinculacion.iniciar()

    def _detener_modo(self) -> None:
        agente, pc, hilo = self.agente, self.pc, self._hilo_vinculacion
        self.agente, self.pc, self._vinculador, self._hilo_vinculacion = None, None, None, None
        if agente is not None:
            agente.detener()
        if pc is not None:
            pc.detener()
        if hilo is not None:
            hilo.detener()

    # ------------------------------------------------------------------ storage

    def _leer_credenciales(self) -> CredencialesPc | None:
        try:
            return self._almacen.leer()
        except AlmacenNoDisponibleError as error:
            logger.error("El almacén de credenciales del sistema no está disponible (%s)", error)
            return None

    def _borrar_credenciales(self) -> None:
        try:
            self._almacen.borrar()
        except AlmacenNoDisponibleError as error:
            logger.error("No se pudieron borrar las credenciales de la PC (%s)", error)
        if self._instalacion is not None:
            self._instalacion = None
            try:
                self._olvidar_instalacion()
            except OSError as error:
                logger.error("No se pudo borrar la credencial de instalación (%s)", error)

    def _borrar_identidad(self) -> None:
        for nombre in ESTADO_DE_LA_IDENTIDAD:
            ruta = self._directorio / nombre
            if ruta.is_dir():
                shutil.rmtree(ruta, ignore_errors=True)
            else:
                ruta.unlink(missing_ok=True)

    def _tamano_datos(self) -> int:
        """Bytes in the data folder (for «Borrar también los datos… (3,2 GB)»), every 30 s."""
        ahora = self._reloj()
        if self._tamano is None or ahora - self._tamano[0] > 30:
            total = 0
            for ruta in self._directorio.rglob("*"):
                try:
                    if ruta.is_file():
                        total += ruta.stat().st_size
                except OSError:
                    continue
            self._tamano = (ahora, total)
        return self._tamano[1]

    def _hogar_actual(self) -> Hogar:
        if self.agente is not None:
            return self.agente.estado().hogar
        if self.pc is not None:
            return self.pc.hogar()
        pc = leer_pc(self._directorio / "pc.json")
        return Hogar(pc.nombre_adulto_mayor if pc is not None else "", "")

    def _contacto(self) -> None:
        self._guardar_json(ARCHIVO_CONTACTO, {"en": self._reloj()})

    def _dias_sin_contacto(self) -> int:
        datos = self._leer_json(ARCHIVO_CONTACTO)
        if not datos:
            return 0
        try:
            return int((self._reloj() - float(datos["en"])) // 86400)
        except (KeyError, TypeError, ValueError):
            return 0

    def _leer_json(self, nombre: str) -> dict[str, Any] | None:
        try:
            datos = json.loads((self._directorio / nombre).read_text("utf-8"))
        except (OSError, ValueError):
            return None
        return datos if isinstance(datos, dict) else None

    def _guardar_json(self, nombre: str, datos: dict[str, Any]) -> None:
        try:
            self._directorio.mkdir(parents=True, exist_ok=True)
            (self._directorio / nombre).write_text(json.dumps(datos), encoding="utf-8")
        except OSError as error:
            logger.warning("No se pudo guardar %s: %s", nombre, error)

    def _borrar_archivo(self, nombre: str) -> None:
        (self._directorio / nombre).unlink(missing_ok=True)

    # ------------------------------------------------------------------ threads

    def _notificar(self) -> None:
        while not self._detenido.wait(INTERVALO_ESTADO_S):
            self.publicar_estado()

    def _revocar_pendiente(self) -> None:
        while not self._detenido.is_set():
            try:
                if enviar_revocacion_pendiente(self._almacen, self._oauth):
                    return
            except AlmacenNoDisponibleError:
                return
            except Exception:
                logger.exception("Error al enviar la desvinculación pendiente")
            self._detenido.wait(REVOCACION_REINTENTO_S)


def _iniciales(nombre: str) -> str:
    """«CH» for «Carmen Huamán»: the avatar of a family member in «Actividad»."""
    partes = [p for p in nombre.split() if p]
    return "".join(p[0] for p in partes[:2]).upper() or "TT"


class MedidorProceso:
    """«Uso del procesador»: this program's share of the PC's CPU since the last reading."""

    def __init__(self) -> None:
        self._anterior = (time.monotonic(), time.process_time())
        self.uso = 0.0

    def medir(self) -> float:
        ahora, cpu = time.monotonic(), time.process_time()
        pared, usado = ahora - self._anterior[0], cpu - self._anterior[1]
        if pared >= 0.5:
            nucleos = os.cpu_count() or 1
            self.uso = max(0.0, min(100.0, usado / pared / nucleos * 100))
            self._anterior = (ahora, cpu)
        return self.uso


DIAS_SEMANA = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")


def _dia(dia: date, hoy: date) -> dict[str, str]:
    """A day of «Fecha» in «Ver qué pasó»: «Hoy, 23/09/2026», «Ayer, …», «Lunes 21/09/2026»."""
    nombre = DIAS_SEMANA[dia.weekday()]
    if dia == hoy:
        texto = f"Hoy, {dia:%d/%m/%Y}"
    elif dia == hoy - timedelta(days=1):
        texto = f"Ayer, {dia:%d/%m/%Y}"
    else:
        texto = f"{nombre.capitalize()} {dia:%d/%m/%Y}"
    return {"valor": dia.isoformat(), "texto": texto, "corto": f"{nombre} {dia:%d/%m}"}
