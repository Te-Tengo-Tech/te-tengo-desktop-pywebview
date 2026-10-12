"""In-memory backend that implements the whole agent contract on ``httpx.MockTransport``.

It includes the PC link (US-28, US-31): the OAuth device grant with rotating refresh tokens
(reuse unlinks the PC), the PC's own endpoints, and removing the PC or an installation from the
app. ``aprobar_tras`` approves a code on its own after that many polls (``--backend-falso``).

Every test that talks to the backend uses it, and ``--backend-falso`` uses it to run the agent
without ``te-tengo-general-api``. Its state is public so tests can change it (pause, revoke
consent, expire tokens, go offline) and inspect what the agent sent.
"""

import json
import threading
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from itertools import count
from typing import Any
from urllib.parse import parse_qs

import httpx

from te_tengo_captura.backend import cliente as rutas
from te_tengo_captura.backend import pc as rutas_pc
from te_tengo_captura.backend import versiones as rutas_versiones
from te_tengo_captura.backend.modelos import MotivoCaptura, iso_utc
from te_tengo_captura.vinculacion import oauth as rutas_oauth

URL_API = "http://backend.falso"
HOST_ALMACEN = "almacen.falso"
TIPOS_EVENTO = frozenset(
    {"caida", "caida_confirmada", "movimiento_inestable", "recuperacion", "deteccion_no_confiable"}
)


@dataclass
class ClipSubido:
    contenido: bytes
    content_type: str


@dataclass
class BackendFalso:
    credencial: str = "credencial-falsa"
    camara_id: str = "camara-1"
    hogar_id: str = "hogar-1"
    reloj: Callable[[], datetime] = field(default=lambda: datetime.now(UTC))

    # Capture state (consent, pause, room name): what the mobile app would change.
    captura_permitida: bool = True
    motivo: MotivoCaptura | None = None
    pausada_hasta: datetime | None = None
    nombre_habitacion: str | None = None  # set by the first registration

    version_agente: str = "1.0.0"
    # GET /api/versiones (US-43): what the team published; nothing by default.
    versiones: dict[str, Any] = field(
        default_factory=lambda: {
            "windows": None,
            "mac": None,
            "apk": None,
            "play": None,
            "ios": None,
            "pwa": None,
            "paginaDescargas": None,
        }
    )
    sin_versiones: bool = False  # an older API without the path: 404
    # Installers served at http://almacen.falso/instaladores/<name> (GET).
    instaladores: dict[str, bytes] = field(default_factory=dict)
    umbrales: dict[str, Any] = field(default_factory=dict)

    # Failure injection.
    sin_conexion: bool = False
    fallos: list[int] = field(default_factory=list)  # statuses to answer, in order
    almacen_falla: int | None = None  # status the clip storage answers while set

    # What the agent sent.
    registros: int = 0
    eventos: dict[str, dict[str, Any]] = field(default_factory=dict)
    senales: list[dict[str, Any]] = field(default_factory=list)
    clips: dict[str, ClipSubido] = field(default_factory=dict)
    solicitudes: list[httpx.Request] = field(default_factory=list)

    # PC link (US-28, US-31): what the owner does in the app.
    pc_id: str = "pc-1"
    vinculada_por: str | None = "Carmen"
    nombre_adulto_mayor: str = "Rosa Huamán"
    consentimiento_vigente: bool = True
    aprobar_tras: int | None = None  # polls before approving on its own (demo); None: tests
    intervalo: int = 5
    expira_codigo_s: int = 600
    expira_acceso_s: int = 3600
    nombre_pc: str | None = None
    vinculaciones: list[dict[str, str]] = field(default_factory=list)  # the forms received
    senales_pc: list[dict[str, Any]] = field(default_factory=list)
    desvinculaciones: list[dict[str, Any]] = field(default_factory=list)
    pc_quitada: bool = False  # removed from the app (or unlinked): PC_DESVINCULADA
    instalacion_quitada: bool = False  # the installation's PC was removed from the app

    # The PC's webcams (US-29): camaraId → {dispositivoId, nombreDispositivo, ambiente, conectada}.
    webcams_pc: dict[str, dict[str, Any]] = field(default_factory=dict)
    ambientes: dict[str, str] = field(default_factory=dict)  # ambienteId → name
    otra_pc_ambientes: dict[str, str] = field(default_factory=dict)  # name → other PC's name
    inventarios: list[list[dict[str, Any]]] = field(default_factory=list)
    actividad: dict[str, dict[str, Any]] = field(default_factory=dict)  # US-33, by id
    # Movements (US-35, US-37): what Rosa allowed in the app; None in the cloud: not allowed.
    movimientos_en_la_pc: bool = True
    movimientos_en_la_nube_dias: int | None = 90
    _tokens_camara: dict[str, str] = field(default_factory=dict)  # token → camaraId
    _retirados: set[str] = field(default_factory=set)
    _codigos: dict[str, dict[str, Any]] = field(default_factory=dict)  # device_code → request
    _refresh: str | None = None  # the refresh token in force
    _refresh_usados: set[str] = field(default_factory=set)
    _tokens_pc: set[str] = field(default_factory=set)
    _tokens: set[str] = field(default_factory=set)
    _subidas: dict[str, str] = field(default_factory=dict)  # upload key → eventoId
    # Movement files (US-37) and clip landmarks (US-36) the agent uploaded.
    movimientos: dict[str, dict[str, Any]] = field(default_factory=dict)  # archivoId → file
    puntos_clips: dict[str, bytes] = field(default_factory=dict)  # eventoId → Parquet
    puntos_clips_ligeros: dict[str, bytes] = field(default_factory=dict)  # eventoId → TTMOV
    # An API from before the light replay files (ADR 0011): their paths answer 404.
    sin_ligeros: bool = False
    _subidas_movimientos: dict[str, str] = field(default_factory=dict)  # key → archivoId
    _subidas_puntos: dict[str, str] = field(default_factory=dict)  # key → eventoId
    _contador: Iterator[int] = field(default_factory=lambda: count(1))
    _candado: threading.Lock = field(default_factory=threading.Lock)

    # ------------------------------------------------------------------ helpers for tests

    def transporte(self) -> httpx.MockTransport:
        return httpx.MockTransport(self._manejar)

    def pausar(self, hasta: datetime) -> None:
        self.captura_permitida, self.motivo, self.pausada_hasta = (
            False,
            MotivoCaptura.EN_PAUSA,
            hasta,
        )

    def quitar_consentimiento(self) -> None:
        self.captura_permitida, self.motivo = False, MotivoCaptura.SIN_CONSENTIMIENTO
        self.pausada_hasta = None

    def permitir(self) -> None:
        self.captura_permitida, self.motivo, self.pausada_hasta = True, None, None

    def expirar_tokens(self) -> None:
        with self._candado:
            self._tokens.clear()
            self._tokens_pc.clear()

    def codigo_pendiente(self) -> str | None:
        """The ``user_code`` the PC shows, if a request is waiting."""
        with self._candado:
            for solicitud in self._codigos.values():
                if solicitud["estado"] == "pendiente":
                    return str(solicitud["user_code"])
        return None

    def aprobar(self) -> None:
        """The owner approves the code in the app (CA-28.1)."""
        self._decidir("aprobada")

    def rechazar(self) -> None:
        """«No reconozco esta PC» (CA-28.4)."""
        self._decidir("rechazada")

    def vencer_codigos(self) -> None:
        with self._candado:
            for solicitud in self._codigos.values():
                if solicitud["estado"] == "pendiente":
                    solicitud["estado"] = "vencida"

    def quitar_pc(self) -> None:
        """«Quitar esta PC» in the app (CA-31.1): every token of the PC stops working."""
        with self._candado:
            self._quitar_pc()

    def _quitar_pc(self) -> None:
        self.pc_quitada = True
        self._refresh = None
        self._tokens_pc.clear()

    def quitar_instalacion(self) -> None:
        """The owner removes the installation's «PC de la casa» from the app."""
        with self._candado:
            self.instalacion_quitada = True

    def asignar_desde_app(self, dispositivo_id: str, habitacion: str) -> str:
        """The owner chooses a room for a webcam in the app (CA-29.2); returns its camaraId."""
        with self._candado:
            camara_id = self._camara_de(dispositivo_id)
            self.webcams_pc[camara_id]["ambiente"] = self._ambiente(habitacion)
            return camara_id

    def dejar_de_usar_desde_app(self, camara_id: str) -> None:
        """«Dejar de usar» in the app: its tokens answer ``401 PC_DESVINCULADA`` at once."""
        with self._candado:
            self._retirar(camara_id)

    def _retirar(self, camara_id: str) -> None:
        self.webcams_pc[camara_id]["ambiente"] = None
        for token, cid in list(self._tokens_camara.items()):
            if cid == camara_id:
                self._retirados.add(token)
                self._tokens.discard(token)
                del self._tokens_camara[token]

    def _camara_de(self, dispositivo_id: str, nombre: str | None = None) -> str:
        for camara_id, webcam in self.webcams_pc.items():
            if webcam["dispositivoId"] == dispositivo_id:
                if nombre:
                    webcam["nombreDispositivo"] = nombre
                return camara_id
        camara_id = f"camara-pc-{next(self._contador)}"
        self.webcams_pc[camara_id] = {
            "dispositivoId": dispositivo_id,
            "nombreDispositivo": nombre or dispositivo_id,
            "ambiente": None,
            "conectada": True,
        }
        return camara_id

    def _ambiente(self, nombre: str) -> str:
        for ambiente_id, existente in self.ambientes.items():
            if existente.lower() == nombre.lower():
                return ambiente_id
        ambiente_id = f"ambiente-{next(self._contador)}"
        self.ambientes[ambiente_id] = nombre
        return ambiente_id

    def _camara_json(self, camara_id: str, con_token: bool) -> dict[str, Any]:
        webcam = self.webcams_pc[camara_id]
        ambiente = webcam["ambiente"]
        token = None
        if ambiente is not None and con_token:
            token = f"token-camara-{next(self._contador)}"
            self._tokens.add(token)
            self._tokens_camara[token] = camara_id
        return {
            "camaraId": camara_id,
            "dispositivoId": webcam["dispositivoId"],
            "nombreDispositivo": webcam["nombreDispositivo"],
            "enUso": ambiente is not None,
            "conectada": webcam["conectada"],
            "ambienteId": ambiente,
            "nombreHabitacion": self.ambientes.get(ambiente) if ambiente else None,
            "estadoConexion": "EN_LINEA" if ambiente else None,
            "pausadaHasta": None,
            "token": token,
            "expiraEn": iso_utc(self.reloj() + timedelta(hours=1)) if token else None,
        }

    def _camaras_pc(self, solicitud: httpx.Request, metodo: str, ruta: str) -> httpx.Response:
        if (metodo, ruta) == ("PUT", rutas_pc.RUTA_INVENTARIO):
            webcams = _cuerpo(solicitud).get("webcams", [])
            self.inventarios.append(webcams)
            presentes = {w["dispositivoId"] for w in webcams}
            for w in webcams:
                self._camara_de(w["dispositivoId"], w.get("nombreDispositivo"))
            for webcam in self.webcams_pc.values():
                webcam["conectada"] = webcam["dispositivoId"] in presentes
            return httpx.Response(200, json=[self._camara_json(c, True) for c in self.webcams_pc])
        if (metodo, ruta) in (("GET", rutas_pc.RUTA_CAMARAS), ("POST", rutas_pc.RUTA_TOKENS)):
            camaras = [
                c
                for c in self.webcams_pc
                if ruta == rutas_pc.RUTA_CAMARAS or self.webcams_pc[c]["ambiente"]
            ]
            return httpx.Response(200, json=[self._camara_json(c, True) for c in camaras])
        if (metodo, ruta) == ("GET", rutas_pc.RUTA_AMBIENTES):
            usados = {w["ambiente"]: c for c, w in self.webcams_pc.items() if w["ambiente"]}
            ambientes = [
                {
                    "id": a,
                    "nombre": n,
                    "camaras": [{"id": usados[a], "pcId": self.pc_id, "pcNombre": self.nombre_pc}]
                    if a in usados
                    else [],
                }
                for a, n in self.ambientes.items()
            ]
            for n, pc in self.otra_pc_ambientes.items():
                ambientes.append(
                    {
                        "id": f"otra-{n}",
                        "nombre": n,
                        "camaras": [{"id": "x", "pcId": "otra", "pcNombre": pc}],
                    }
                )
            return httpx.Response(200, json=ambientes)
        if (metodo, ruta) == ("PUT", rutas_pc.RUTA_CAMARAS):
            cuerpo = _cuerpo(solicitud)
            nombre = (cuerpo.get("nombreAmbiente") or "").strip()
            ambiente_id = cuerpo.get("ambienteId")
            if ambiente_id is None and not nombre:
                return _problema(422, "AMBIENTE_NOMBRE_VACIO", "Escribe el nombre del ambiente.")
            if nombre.lower() in ("baño", "bano", "wc", "ss.hh."):
                return _problema(422, "AMBIENTE_NO_PERMITIDO", "No se admiten cámaras en el baño")
            for otro, pc in self.otra_pc_ambientes.items():
                if otro.lower() == nombre.lower() or ambiente_id == f"otra-{otro}":
                    problema = _problema(409, "AMBIENTE_OCUPADO", "Ambiente ocupado")
                    datos = json.loads(problema.content)
                    datos.update(
                        {"ambiente": otro, "camara": {"id": "x", "pcId": "otra", "pcNombre": pc}}
                    )
                    return httpx.Response(409, json=datos)
            destino = ambiente_id or self._ambiente(nombre)
            camara_id = self._camara_de(cuerpo["dispositivoId"], cuerpo.get("nombreDispositivo"))
            for otro_id, webcam in self.webcams_pc.items():
                if otro_id != camara_id and webcam["ambiente"] == destino:
                    problema = json.loads(
                        _problema(409, "AMBIENTE_OCUPADO", "Ambiente ocupado").content
                    )
                    problema.update(
                        {
                            "ambiente": self.ambientes[destino],
                            "camara": {
                                "id": otro_id,
                                "pcId": self.pc_id,
                                "pcNombre": self.nombre_pc,
                            },
                        }
                    )
                    return httpx.Response(409, json=problema)
            self.webcams_pc[camara_id]["ambiente"] = destino
            return httpx.Response(200, json=self._camara_json(camara_id, True))
        if metodo == "DELETE" and ruta.startswith(rutas_pc.RUTA_CAMARAS + "/"):
            camara_id = ruta.removeprefix(rutas_pc.RUTA_CAMARAS + "/")
            if camara_id not in self.webcams_pc:
                return _problema(404, "CAMARA_NO_ENCONTRADA", "Cámara no encontrada")
            self._retirar(camara_id)
            return httpx.Response(204)
        return _problema(404, "RUTA_NO_ENCONTRADA", f"{metodo} {ruta}")

    def _decidir(self, estado: str) -> None:
        with self._candado:
            for solicitud in self._codigos.values():
                if solicitud["estado"] == "pendiente":
                    solicitud["estado"] = estado

    # ------------------------------------------------------------------ HTTP

    def _manejar(self, solicitud: httpx.Request) -> httpx.Response:
        with self._candado:
            self.solicitudes.append(solicitud)
            if self.sin_conexion:
                raise httpx.ConnectError("sin conexión (backend falso)", request=solicitud)
            if self.fallos:
                return _problema(self.fallos.pop(0), "FALLO_SIMULADO", "Fallo simulado")
            if solicitud.url.host == HOST_ALMACEN:
                if self.almacen_falla is not None:
                    return httpx.Response(self.almacen_falla)
                if solicitud.method == "GET" and solicitud.url.path.startswith("/instaladores/"):
                    contenido = self.instaladores.get(
                        solicitud.url.path.removeprefix("/instaladores/")
                    )
                    return httpx.Response(200 if contenido is not None else 404, content=contenido)
                return self._subir(solicitud)
            if solicitud.headers.get("Api-Version") != rutas.API_VERSION:
                return _problema(400, "VERSION_NO_SOPORTADA", "Falta Api-Version: 1")
            ruta, metodo = solicitud.url.path, solicitud.method
            if (metodo, ruta) == ("GET", rutas_versiones.RUTA_VERSIONES):
                # Public: no token is needed nor checked (contract, "Updates (US-43)").
                if self.sin_versiones:
                    return _problema(404, "RUTA_NO_ENCONTRADA", ruta)
                return httpx.Response(200, json=self.versiones)
            if metodo == "POST" and ruta in (
                rutas_oauth.RUTA_VINCULACION,
                rutas_oauth.RUTA_TOKEN,
                rutas_oauth.RUTA_REVOCACION,
            ):
                return self._oauth(ruta, _formulario(solicitud))
            if (metodo, ruta) == ("GET", rutas.RUTA_ESTADO_MOVIMIENTOS):
                return self._estado_movimientos(solicitud)
            if ruta.startswith(rutas_pc.RUTA_PC) or ruta == rutas_pc.RUTA_AMBIENTES:
                return self._pc(solicitud, metodo, ruta)
            if (metodo, ruta) == ("POST", rutas.RUTA_REGISTRO):
                if self.instalacion_quitada:
                    return _problema(401, "CREDENCIAL_INVALIDA", "La instalación se quitó")
                return self._registrar(_cuerpo(solicitud))
            if self.instalacion_quitada:
                return _problema(401, "PC_DESVINCULADA", "Esta PC se quitó de la vivienda")
            token = solicitud.headers.get("Authorization", "").removeprefix("Bearer ")
            if token in self._retirados or (self.pc_quitada and token in self._tokens_camara):
                return _problema(401, "PC_DESVINCULADA", "La cámara ya no está en uso")
            if not self._autorizado(solicitud):
                return _problema(401, "TOKEN_INVALIDO", "Token inválido o vencido")
            if (metodo, ruta) == ("GET", rutas.RUTA_ESTADO):
                return httpx.Response(200, json=self._estado())
            if (metodo, ruta) == ("POST", rutas.RUTA_SENAL):
                self.senales.append(_cuerpo(solicitud))
                return httpx.Response(200, json=self._estado())
            if (metodo, ruta) == ("POST", rutas.RUTA_EVENTOS):
                return self._evento(_cuerpo(solicitud))
            if metodo == "POST" and ruta.startswith(rutas.RUTA_EVENTOS + "/"):
                evento_id, _, resto = ruta.removeprefix(rutas.RUTA_EVENTOS + "/").partition("/")
                if resto == "clip":
                    return self._solicitar_clip(evento_id, _cuerpo(solicitud))
                if resto == "clip/puntos":
                    return self._solicitar_puntos(evento_id)
                if resto == "clip/puntos/ligero":
                    return self._solicitar_puntos(evento_id, ligero=True)
            if (metodo, ruta) == ("POST", rutas.RUTA_MOVIMIENTOS):
                return self._solicitar_movimientos(solicitud, _cuerpo(solicitud))
            if metodo == "POST" and ruta.startswith(rutas.RUTA_MOVIMIENTOS + "/"):
                archivo_id, _, resto = ruta.removeprefix(rutas.RUTA_MOVIMIENTOS + "/").partition(
                    "/"
                )
                if resto == "ligero":
                    return self._solicitar_ligero(archivo_id, _cuerpo(solicitud))
                if resto == "ligero/confirmacion":
                    return self._confirmar_ligero(archivo_id)
                return self._confirmar_movimientos(archivo_id)
            if (metodo, ruta) == ("GET", rutas.RUTA_CONFIGURACION):
                return httpx.Response(
                    200, json={"versionAgente": self.version_agente, "umbrales": self.umbrales}
                )
            return _problema(404, "RUTA_NO_ENCONTRADA", f"{metodo} {ruta}")

    # ------------------------------------------------------------------ PC link

    def _oauth(self, ruta: str, formulario: dict[str, str]) -> httpx.Response:
        if formulario.get("client_id") != rutas_oauth.CLIENT_ID:
            return _error_oauth(401, "invalid_client")
        if ruta == rutas_oauth.RUTA_VINCULACION:
            if not formulario.get("nombre_pc"):
                return _error_oauth(400, "invalid_request")
            self.vinculaciones.append(formulario)
            numero = next(self._contador)
            device_code = f"dispositivo-secreto-{numero}"
            letras = "BCDFGHJKLMNPQRSTVWXZ"
            user_code = "".join(letras[(numero * 7 + i * 3) % 20] for i in range(8))
            user_code = f"{user_code[:4]}-{user_code[4:]}"
            self._codigos[device_code] = {
                "user_code": user_code,
                "estado": "pendiente",
                "sondeos": 0,
                "nombre_pc": formulario["nombre_pc"],
            }
            return httpx.Response(
                200,
                json={
                    "device_code": device_code,
                    "user_code": user_code,
                    "verification_uri": "https://app.tetengo.reqsai.tech/vincular",
                    "verification_uri_complete": (
                        f"https://app.tetengo.reqsai.tech/vincular?codigo={user_code}"
                    ),
                    "expires_in": self.expira_codigo_s,
                    "interval": self.intervalo,
                },
            )
        if ruta == rutas_oauth.RUTA_REVOCACION:
            token = formulario.get("token", "")
            if token and token == self._refresh:
                self.desvinculaciones.append(
                    {"via": "revocacion", "datos": formulario.get("datos_locales_borrados")}
                )
                self.pc_quitada = True
                self._refresh = None
                self._tokens_pc.clear()
            return httpx.Response(200)
        tipo = formulario.get("grant_type")
        if tipo == rutas_oauth.GRANT_DISPOSITIVO:
            solicitud = self._codigos.get(formulario.get("device_code", ""))
            if solicitud is None or solicitud["estado"] == "usada":
                return _error_oauth(400, "invalid_grant")
            solicitud["sondeos"] += 1
            if (
                solicitud["estado"] == "pendiente"
                and self.aprobar_tras is not None
                and solicitud["sondeos"] >= self.aprobar_tras
            ):
                solicitud["estado"] = "aprobada"
            if solicitud["estado"] == "vencida":
                return _error_oauth(400, "expired_token")
            if solicitud["estado"] == "rechazada":
                return _error_oauth(400, "access_denied")
            if solicitud["estado"] == "pendiente":
                return _error_oauth(400, "authorization_pending")
            solicitud["estado"] = "usada"
            self.nombre_pc = solicitud["nombre_pc"]
            self.pc_quitada = False
            return self._emitir_tokens()
        if tipo == rutas_oauth.GRANT_RENOVACION:
            token = formulario.get("refresh_token", "")
            if token in self._refresh_usados:
                # RFC 9700 §4.14.2: a rotated token presented again unlinks the PC.
                self._quitar_pc()
                return _error_oauth(400, "invalid_grant")
            if self.pc_quitada or token != self._refresh:
                return _error_oauth(400, "invalid_grant")
            self._refresh_usados.add(token)
            return self._emitir_tokens()
        return _error_oauth(400, "unsupported_grant_type")

    def _emitir_tokens(self) -> httpx.Response:
        numero = next(self._contador)
        acceso, renovacion = f"acceso-pc-{numero}", f"renovacion-pc-{numero}"
        self._tokens_pc.add(acceso)
        self._refresh = renovacion
        return httpx.Response(
            200,
            json={
                "access_token": acceso,
                "token_type": "Bearer",
                "expires_in": self.expira_acceso_s,
                "refresh_token": renovacion,
                "pc_id": self.pc_id,
                "hogar_id": self.hogar_id,
            },
        )

    def _pc(self, solicitud: httpx.Request, metodo: str, ruta: str) -> httpx.Response:
        token = solicitud.headers.get("Authorization", "").removeprefix("Bearer ")
        if self.pc_quitada:
            return _problema(401, "PC_DESVINCULADA", "Esta PC se quitó de la vivienda")
        if token not in self._tokens_pc:
            return _problema(401, "SESION_EXPIRADA", "Token vencido")
        if (metodo, ruta) == ("GET", rutas_pc.RUTA_PC):
            return httpx.Response(200, json=self._pc_del_agente())
        if (metodo, ruta) == ("POST", rutas_pc.RUTA_SENAL_PC):
            self.senales_pc.append(_cuerpo(solicitud))
            return httpx.Response(200, json=self._pc_del_agente())
        if (metodo, ruta) == ("POST", rutas_pc.RUTA_ACTIVIDAD):
            cambios = _cuerpo(solicitud).get("cambios", [])
            permitidos = {
                "MODO_AVANZADO_ACTIVADO",
                "MODO_AVANZADO_DESACTIVADO",
                "GUARDADO_LOCAL_CAMBIADO",
                "DATOS_LOCALES_ELIMINADOS",
                "REPETICION_VISTA",
                "PC_ACTUALIZADA",
                "ACTUALIZACION_AUTOMATICA_ACTIVADA",
                "ACTUALIZACION_AUTOMATICA_DESACTIVADA",
            }
            if len(cambios) > 100 or any(c.get("tipo") not in permitidos for c in cambios):
                return _problema(400, "VALIDACION", "Cambio inválido")
            repetidos = sum(1 for c in cambios if c["id"] in self.actividad)
            for cambio in cambios:
                self.actividad.setdefault(cambio["id"], cambio)
            return httpx.Response(
                200, json={"registrados": len(cambios) - repetidos, "repetidos": repetidos}
            )
        if (metodo, ruta) == ("DELETE", rutas_pc.RUTA_PC):
            self.desvinculaciones.append(
                {"via": "delete", "datos": solicitud.url.params.get("datosLocalesBorrados")}
            )
            self._quitar_pc()
            return httpx.Response(204)
        return self._camaras_pc(solicitud, metodo, ruta)

    def _estado_movimientos(self, solicitud: httpx.Request) -> httpx.Response:
        token = solicitud.headers.get("Authorization", "").removeprefix("Bearer ")
        if self.pc_quitada and token in self._tokens_pc | set(self._tokens_camara):
            return _problema(401, "PC_DESVINCULADA", "Esta PC se quitó de la vivienda")
        if not (token in self._tokens_pc or self._autorizado(solicitud)):
            return _problema(401, "TOKEN_INVALIDO", "Token inválido o vencido")
        vigente = self.consentimiento_vigente and self.motivo != MotivoCaptura.SIN_CONSENTIMIENTO
        nube = vigente and self.movimientos_en_la_nube_dias is not None
        return httpx.Response(
            200,
            json={
                "consentimientoVigente": vigente,
                "guardarEnLaPc": vigente and self.movimientos_en_la_pc,
                "guardarEnLaNube": nube,
                "retencionDias": self.movimientos_en_la_nube_dias if nube else None,
                "versionTextoVigente": "v1" if vigente else None,
            },
        )

    def _pc_del_agente(self) -> dict[str, Any]:
        return {
            "pcId": self.pc_id,
            "hogarId": self.hogar_id,
            "nombre": self.nombre_pc or "PC",
            "nombreAdultoMayor": self.nombre_adulto_mayor,
            "vinculadaEn": iso_utc(self.reloj()),
            "vinculadaPor": self.vinculada_por,
            "consentimientoVigente": self.consentimiento_vigente,
        }

    # ------------------------------------------------------------------ cameras

    def _registrar(self, cuerpo: dict[str, Any]) -> httpx.Response:
        if cuerpo.get("credencialInstalacion") != self.credencial:
            return _problema(401, "CREDENCIAL_INVALIDA", "Credencial de instalación inválida")
        if not cuerpo.get("nombreHabitacion") or not cuerpo.get("versionAgente"):
            return _problema(400, "SOLICITUD_INVALIDA", "Faltan campos del registro")
        if self.nombre_habitacion is None:
            self.nombre_habitacion = cuerpo["nombreHabitacion"]
        self.registros += 1
        token = f"token-{next(self._contador)}"
        self._tokens.add(token)
        return httpx.Response(
            200,
            json={
                "camaraId": self.camara_id,
                "hogarId": self.hogar_id,
                "token": token,
                "expiraEn": iso_utc(self.reloj() + timedelta(hours=1)),
                "nombreHabitacion": self.nombre_habitacion,
            },
        )

    def _autorizado(self, solicitud: httpx.Request) -> bool:
        cabecera = solicitud.headers.get("Authorization", "")
        return cabecera.startswith("Bearer ") and cabecera.removeprefix("Bearer ") in self._tokens

    def _estado(self) -> dict[str, Any]:
        return {
            "capturaPermitida": self.captura_permitida,
            "motivo": self.motivo.value if self.motivo else None,
            "pausadaHasta": iso_utc(self.pausada_hasta) if self.pausada_hasta else None,
            "nombreHabitacion": self.nombre_habitacion or "",
        }

    def _evento(self, cuerpo: dict[str, Any]) -> httpx.Response:
        evento_id = cuerpo.get("eventoId")
        if not evento_id or cuerpo.get("tipo") not in TIPOS_EVENTO or "ocurridoEn" not in cuerpo:
            return _problema(400, "SOLICITUD_INVALIDA", "Evento inválido")
        if evento_id in self.eventos:
            return httpx.Response(200, json={"eventoId": evento_id, "alertaId": None})
        if not self.captura_permitida:
            return _problema(409, "CAPTURA_NO_PERMITIDA", "Captura no permitida")
        self.eventos[evento_id] = cuerpo
        return httpx.Response(202, json={"eventoId": evento_id, "alertaId": None})

    def _solicitar_clip(self, evento_id: str, cuerpo: dict[str, Any]) -> httpx.Response:
        if evento_id not in self.eventos:
            return _problema(404, "EVENTO_NO_ENCONTRADO", "Evento no encontrado")
        clave = f"{evento_id}-{next(self._contador)}"
        self._subidas[clave] = evento_id
        return httpx.Response(
            201,
            json={
                "urlSubida": f"https://{HOST_ALMACEN}/clips/{clave}.mp4?firma=secreta",
                "cabeceras": {"Content-Type": cuerpo.get("contentType", "video/mp4")},
                "expiraEn": iso_utc(self.reloj() + timedelta(minutes=15)),
            },
        )

    # ------------------------------------------------------------------ movements (US-36, US-37)

    def _sin_nube(self) -> httpx.Response | None:
        if not self.consentimiento_vigente or self.motivo == MotivoCaptura.SIN_CONSENTIMIENTO:
            return _problema(409, "SIN_CONSENTIMIENTO_DE_MOVIMIENTOS", "Sin consentimiento")
        if self.movimientos_en_la_nube_dias is None:
            return _problema(409, "MOVIMIENTOS_EN_LA_NUBE_DESACTIVADOS", "Nube desactivada")
        return None

    def _solicitar_movimientos(
        self, solicitud: httpx.Request, cuerpo: dict[str, Any]
    ) -> httpx.Response:
        if (rechazo := self._sin_nube()) is not None:
            return rechazo
        try:
            desde = datetime.fromisoformat(cuerpo["desde"])
            hasta = datetime.fromisoformat(cuerpo["hasta"])
            tamano, sha, filas = cuerpo["tamanoBytes"], cuerpo["sha256"], cuerpo["fotogramas"]
        except (KeyError, TypeError, ValueError):
            return _problema(400, "VALIDACION", "Cuerpo inválido")
        if not desde < hasta <= desde + timedelta(minutes=10) or len(sha) != 64:
            return _problema(400, "VALIDACION", "Rango o SHA-256 inválido")
        if desde < self.reloj() - timedelta(days=self.movimientos_en_la_nube_dias or 0):
            return _problema(422, "MOVIMIENTOS_FUERA_DEL_PLAZO", "Fuera del plazo")
        camara = self._tokens_camara.get(_token(solicitud), self.camara_id)
        for archivo_id, archivo in self.movimientos.items():
            if (archivo["camara"], archivo["desde"]) == (camara, desde):
                if archivo["estado"] == "DISPONIBLE":
                    return _problema(409, "ARCHIVO_YA_SUBIDO", "Ya subido", archivoId=archivo_id)
                break
        else:
            archivo_id = f"archivo-{next(self._contador)}"
        self.movimientos[archivo_id] = {
            "camara": camara,
            "desde": desde,
            "hasta": hasta,
            "tamanoBytes": tamano,
            "sha256": sha,
            "fotogramas": filas,
            "estado": "PENDIENTE",
            "contenido": None,
            "ligero": None,  # {tamanoBytes, sha256, contenido, disponible} once asked for
        }
        clave = f"m{next(self._contador)}"
        self._subidas_movimientos[clave] = archivo_id
        return httpx.Response(
            201,
            json={
                "archivoId": archivo_id,
                "urlSubida": f"https://{HOST_ALMACEN}/movimientos/{clave}.parquet?firma=secreta",
                "cabeceras": {"Content-Type": "application/vnd.apache.parquet"},
                "expiraEn": iso_utc(self.reloj() + timedelta(minutes=10)),
            },
        )

    def _confirmar_movimientos(self, archivo_id: str) -> httpx.Response:
        archivo = self.movimientos.get(archivo_id)
        if archivo is None:
            return _problema(404, "ARCHIVO_NO_ENCONTRADO", "No existe")
        rechazo = self._sin_nube()
        if rechazo is not None and rechazo.json()["codigo"] == "SIN_CONSENTIMIENTO_DE_MOVIMIENTOS":
            del self.movimientos[archivo_id]  # revoked meanwhile: the API deletes the object
            return rechazo
        if archivo["contenido"] is None:
            return _problema(409, "ARCHIVO_NO_SUBIDO", "El almacenamiento no lo tiene")
        archivo["estado"] = "DISPONIBLE"
        return httpx.Response(
            200,
            json={
                "archivoId": archivo_id,
                "estado": "DISPONIBLE",
                "tamanoBytes": archivo["tamanoBytes"],
            },
        )

    def _solicitar_ligero(self, archivo_id: str, cuerpo: dict[str, Any]) -> httpx.Response:
        if self.sin_ligeros:
            return httpx.Response(404, json={"status": 404, "title": "Not Found"})
        archivo = self.movimientos.get(archivo_id)
        if archivo is None:
            return _problema(404, "ARCHIVO_NO_ENCONTRADO", "No existe")
        if (rechazo := self._sin_nube()) is not None:
            return rechazo
        try:
            tamano, sha = int(cuerpo["tamanoBytes"]), str(cuerpo["sha256"])
        except (KeyError, TypeError, ValueError):
            return _problema(400, "VALIDACION", "Cuerpo inválido")
        if tamano <= 0 or len(sha) != 64:
            return _problema(400, "VALIDACION", "Tamaño o SHA-256 inválido")
        ligero = archivo["ligero"]
        if ligero is not None and ligero["disponible"]:
            return _problema(409, "ARCHIVO_YA_SUBIDO", "Ya subido", archivoId=archivo_id)
        archivo["ligero"] = {
            "tamanoBytes": tamano,
            "sha256": sha,
            "contenido": None if ligero is None else ligero["contenido"],
            "disponible": False,
        }
        clave = f"l{next(self._contador)}"
        self._subidas_movimientos[clave] = archivo_id
        return httpx.Response(
            201,
            json={
                "urlSubida": f"https://{HOST_ALMACEN}/movimientos/{clave}.ttmov?firma=secreta",
                "cabeceras": {"Content-Type": "application/gzip"},
                "expiraEn": iso_utc(self.reloj() + timedelta(minutes=10)),
            },
        )

    def _confirmar_ligero(self, archivo_id: str) -> httpx.Response:
        if self.sin_ligeros:
            return httpx.Response(404, json={"status": 404, "title": "Not Found"})
        archivo = self.movimientos.get(archivo_id)
        if archivo is None or archivo["ligero"] is None:
            return _problema(404, "ARCHIVO_NO_ENCONTRADO", "No existe")
        rechazo = self._sin_nube()
        if rechazo is not None and rechazo.json()["codigo"] == "SIN_CONSENTIMIENTO_DE_MOVIMIENTOS":
            archivo["ligero"] = None  # revoked meanwhile: the API deletes the object
            return rechazo
        if archivo["ligero"]["contenido"] is None:
            return _problema(409, "ARCHIVO_NO_SUBIDO", "El almacenamiento no lo tiene")
        archivo["ligero"]["disponible"] = True
        return httpx.Response(
            200, json={"archivoId": archivo_id, "tamanoBytes": archivo["ligero"]["tamanoBytes"]}
        )

    def _solicitar_puntos(self, evento_id: str, ligero: bool = False) -> httpx.Response:
        if ligero and self.sin_ligeros:
            return httpx.Response(404, json={"status": 404, "title": "Not Found"})
        if evento_id not in self.eventos:
            return _problema(404, "EVENTO_NO_ENCONTRADO", "Evento no encontrado")
        if not self.consentimiento_vigente or self.motivo == MotivoCaptura.SIN_CONSENTIMIENTO:
            return _problema(409, "SIN_CONSENTIMIENTO_DE_MOVIMIENTOS", "Sin consentimiento")
        clave = f"{'q' if ligero else 'p'}{next(self._contador)}"
        self._subidas_puntos[clave] = evento_id
        extension, tipo = (
            ("ttmov", "application/gzip")
            if ligero
            else ("parquet", "application/vnd.apache.parquet")
        )
        return httpx.Response(
            201,
            json={
                "urlSubida": f"https://{HOST_ALMACEN}/puntos/{clave}.{extension}?firma=secreta",
                "cabeceras": {"Content-Type": tipo},
                "expiraEn": iso_utc(self.reloj() + timedelta(minutes=15)),
            },
        )

    def _subir(self, solicitud: httpx.Request) -> httpx.Response:
        if solicitud.url.path.startswith("/movimientos/"):
            nombre = solicitud.url.path.removeprefix("/movimientos/")
            clave = nombre.removesuffix(".parquet").removesuffix(".ttmov")
            if solicitud.method != "PUT" or clave not in self._subidas_movimientos:
                return httpx.Response(403)
            archivo = self.movimientos.get(self._subidas_movimientos.pop(clave))
            if archivo is not None and nombre.endswith(".ttmov"):
                if archivo["ligero"] is not None:
                    archivo["ligero"]["contenido"] = solicitud.read()
            elif archivo is not None:
                archivo["contenido"] = solicitud.read()
            return httpx.Response(200)
        if solicitud.url.path.startswith("/puntos/"):
            nombre = solicitud.url.path.removeprefix("/puntos/")
            clave = nombre.removesuffix(".parquet").removesuffix(".ttmov")
            if solicitud.method != "PUT" or clave not in self._subidas_puntos:
                return httpx.Response(403)
            destino = self.puntos_clips_ligeros if nombre.endswith(".ttmov") else self.puntos_clips
            destino[self._subidas_puntos.pop(clave)] = solicitud.read()
            return httpx.Response(200)
        clave = solicitud.url.path.removeprefix("/clips/").removesuffix(".mp4")
        if solicitud.method != "PUT" or clave not in self._subidas:
            return httpx.Response(403)
        evento_id = self._subidas.pop(clave)
        self.clips[evento_id] = ClipSubido(
            solicitud.read(), solicitud.headers.get("Content-Type", "")
        )
        return httpx.Response(200)


def _cuerpo(solicitud: httpx.Request) -> dict[str, Any]:
    try:
        datos = json.loads(solicitud.read() or b"{}")
    except ValueError:
        return {}
    return datos if isinstance(datos, dict) else {}


def _formulario(solicitud: httpx.Request) -> dict[str, str]:
    campos = parse_qs(solicitud.read().decode("utf-8"))
    return {nombre: valores[0] for nombre, valores in campos.items()}


def _error_oauth(estado: int, codigo: str) -> httpx.Response:
    return httpx.Response(estado, json={"error": codigo}, headers={"Cache-Control": "no-store"})


def _problema(estado: int, codigo: str, detalle: str, **extra: Any) -> httpx.Response:
    return httpx.Response(
        estado,
        headers={"Content-Type": "application/problem+json"},
        json={
            "type": "about:blank",
            "title": detalle,
            "status": estado,
            "detail": detalle,
            "codigo": codigo,
            **extra,
        },
    )


def _token(solicitud: httpx.Request) -> str:
    return str(solicitud.headers.get("Authorization", "")).removeprefix("Bearer ")
