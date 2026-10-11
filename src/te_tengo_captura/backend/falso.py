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

    _codigos: dict[str, dict[str, Any]] = field(default_factory=dict)  # device_code → request
    _refresh: str | None = None  # the refresh token in force
    _refresh_usados: set[str] = field(default_factory=set)
    _tokens_pc: set[str] = field(default_factory=set)
    _tokens: set[str] = field(default_factory=set)
    _subidas: dict[str, str] = field(default_factory=dict)  # upload key → eventoId
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
                return self._subir(solicitud)
            if solicitud.headers.get("Api-Version") != rutas.API_VERSION:
                return _problema(400, "VERSION_NO_SOPORTADA", "Falta Api-Version: 1")
            ruta, metodo = solicitud.url.path, solicitud.method
            if metodo == "POST" and ruta in (
                rutas_oauth.RUTA_VINCULACION,
                rutas_oauth.RUTA_TOKEN,
                rutas_oauth.RUTA_REVOCACION,
            ):
                return self._oauth(ruta, _formulario(solicitud))
            if ruta.startswith(rutas_pc.RUTA_PC):
                return self._pc(solicitud, metodo, ruta)
            if (metodo, ruta) == ("POST", rutas.RUTA_REGISTRO):
                if self.instalacion_quitada:
                    return _problema(401, "CREDENCIAL_INVALIDA", "La instalación se quitó")
                return self._registrar(_cuerpo(solicitud))
            if self.instalacion_quitada:
                return _problema(401, "PC_DESVINCULADA", "Esta PC se quitó de la vivienda")
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
        if (metodo, ruta) == ("DELETE", rutas_pc.RUTA_PC):
            self.desvinculaciones.append(
                {"via": "delete", "datos": solicitud.url.params.get("datosLocalesBorrados")}
            )
            self._quitar_pc()
            return httpx.Response(204)
        return _problema(404, "RUTA_NO_ENCONTRADA", f"{metodo} {ruta}")

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

    def _subir(self, solicitud: httpx.Request) -> httpx.Response:
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


def _problema(estado: int, codigo: str, detalle: str) -> httpx.Response:
    return httpx.Response(
        estado,
        headers={"Content-Type": "application/problem+json"},
        json={
            "type": "about:blank",
            "title": detalle,
            "status": estado,
            "detail": detalle,
            "codigo": codigo,
        },
    )
