"""In-memory backend that implements the whole agent contract on ``httpx.MockTransport``.

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

import httpx

from te_tengo_captura.backend import cliente as rutas
from te_tengo_captura.backend.modelos import MotivoCaptura, iso_utc

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
            if (metodo, ruta) == ("POST", rutas.RUTA_REGISTRO):
                return self._registrar(_cuerpo(solicitud))
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
