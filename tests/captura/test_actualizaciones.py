"""Updates of Te Tengo Captura (US-43): checks, download, verification, install and waits."""

import hashlib
import subprocess
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpx
import pytest

from te_tengo_captura.actualizaciones import descarga, instalador
from te_tengo_captura.actualizaciones.actualizador import (
    Actualizador,
    Estado,
    Plataforma,
    en_madrugada,
    proxima_madrugada,
)
from te_tengo_captura.actualizaciones.alerta import DURACION_S, SeguimientoAlerta
from te_tengo_captura.actualizaciones.comparar import es_mas_nueva, numeros
from te_tengo_captura.backend.errores import SinConexionError
from te_tengo_captura.backend.falso import HOST_ALMACEN, URL_API, BackendFalso
from te_tengo_captura.backend.modelos import VersionesPublicadas
from te_tengo_captura.backend.versiones import ClienteVersiones
from te_tengo_captura.bandeja.avisos import Avisos
from te_tengo_captura.estado import Notificacion
from te_tengo_captura.instancia import MUTEX, crear_mutex
from te_tengo_deteccion.clasificacion.estados import TipoEvento

INSTALADOR = b"MZ instalador de la 0.5.0"
SHA = hashlib.sha256(INSTALADOR).hexdigest()
URL_INSTALADOR = f"http://{HOST_ALMACEN}/instaladores/te-tengo-captura-setup.exe"


def publicadas(
    version: str = "0.5.0",
    minima: str | None = None,
    url: str | None = URL_INSTALADOR,
    sha256: str | None = SHA,
    tamano: int | None = 90177536,
) -> dict[str, Any]:
    canal = {
        "version": version,
        "versionMinima": minima,
        "url": url,
        "sha256": sha256,
        "tamanoBytes": tamano,
        "publicadaEn": "2026-09-22T08:00:00Z",
        "notas": ["Detecta mejor las caídas con poca luz.", "Usa menos el procesador."],
    }
    mac = {**canal, "url": "https://descargas.ejemplo/te-tengo-captura.dmg", "sha256": None}
    return {
        "windows": canal,
        "mac": mac,
        "apk": None,
        "play": None,
        "ios": None,
        "pwa": None,
        "paginaDescargas": "https://tetengo.reqsai.tech/descargas",
    }


class Reloj:
    def __init__(self, ahora: datetime) -> None:
        self.ahora = ahora

    def __call__(self) -> datetime:
        return self.ahora

    def avanzar(self, **delta: float) -> None:
        self.ahora += timedelta(**delta)


class Escenario:
    """An updater against the fake backend, with the clock, the block and the installer faked."""

    def __init__(self, tmp_path: Path, plataforma: Plataforma | None = Plataforma.WINDOWS) -> None:
        self.falso = BackendFalso()
        self.falso.versiones = publicadas()
        self.falso.instaladores["te-tengo-captura-setup.exe"] = INSTALADOR
        self.reloj = Reloj(datetime(2026, 9, 23, 10, 30))
        self.bloqueo: str | None = None
        self.lanzados: list[Path] = []
        self.salidas = 0
        self.navegador: list[str] = []
        self.libre = 10 * 2**30
        self.directorio = tmp_path
        self.plataforma = plataforma
        self.cliente = ClienteVersiones(URL_API, self.falso.transporte())
        self.consultas = 0
        self.actualizador = self.crear()

    def crear(self, **opciones: Any) -> Actualizador:
        def versiones() -> VersionesPublicadas | None:
            self.consultas += 1
            return self.cliente.versiones()

        argumentos: dict[str, Any] = {
            "reloj": self.reloj,
            "zona": UTC,
            "bloqueo": lambda: self.bloqueo,
            "lanzar": self.lanzados.append,
            "abrir_navegador": self.navegador.append,
            "transporte": self.falso.transporte(),
            "uso": lambda _d: SimpleNamespace(free=self.libre),
            "en_hilo": lambda accion: accion(),  # synchronous: no thread in tests
            "esperar": lambda _s: None,
        }
        actualizador = Actualizador(
            "0.4.3", self.directorio, versiones, self.plataforma, **{**argumentos, **opciones}
        )
        actualizador.al_salir = self.salir
        return actualizador

    def salir(self) -> None:
        self.salidas += 1


@pytest.fixture
def e(tmp_path: Path) -> Escenario:
    return Escenario(tmp_path)


# ------------------------------------------------------------------ versions


def test_versiones_numericas_sin_sufijos() -> None:
    assert numeros("0.5.0-rc.1") == (0, 5, 0)
    assert numeros("v1.2") == (1, 2, 0)
    assert es_mas_nueva("0.10.0", "0.9.9")  # numerically, not as text
    assert not es_mas_nueva("0.5.0-rc.2", "0.5.0")  # suffixes are ignored
    assert not es_mas_nueva("nada", "0.4.3")
    with pytest.raises(ValueError, match="no válida"):
        numeros("x.y")


def test_get_versiones_es_publico_y_tolera_un_backend_antiguo(e: Escenario) -> None:
    v = e.cliente.versiones()
    assert v is not None
    assert v.windows is not None
    assert v.windows.tamano_bytes == 90177536
    assert v.pagina_descargas == "https://tetengo.reqsai.tech/descargas"
    solicitud = e.falso.solicitudes[-1]
    assert solicitud.url.path == "/api/versiones"
    assert "Authorization" not in solicitud.headers  # public: an expired token must not matter
    e.falso.sin_versiones = True
    assert e.cliente.versiones() is None  # 404: no information
    e.falso.sin_conexion = True
    with pytest.raises(SinConexionError):
        e.cliente.versiones()


# ------------------------------------------------------------------ checks (CA-43.1)


def test_busca_al_abrir_y_una_vez_al_dia(e: Escenario) -> None:
    a = e.actualizador
    a.paso()
    assert e.consultas == 1
    assert a.nueva is not None
    assert a.nueva.version == "0.5.0"
    datos = a.a_json()
    assert (datos["latest"], datos["last"], datos["mb"], datos["date"]) == (
        "0.5.0",
        "hoy 10:30",
        86,
        "22/09/2026",
    )
    assert datos["notes"][0] == "Detecta mejor las caídas con poca luz."
    assert datos["page"] == "tetengo.reqsai.tech/descargas"
    e.reloj.avanzar(hours=23, minutes=59)
    a.paso()
    assert e.consultas == 1
    e.reloj.avanzar(minutes=1)
    a.paso()
    assert e.consultas == 2
    assert a.a_json()["last"] == "hoy 10:30"


def test_sin_internet_se_reintenta_en_la_proxima_busqueda(e: Escenario) -> None:
    e.falso.sin_conexion = True
    a = e.actualizador
    a.paso()
    assert a.buscar() == {"ok": False, "nueva": False, "version": "0.4.3"}  # «Sin internet…»
    assert a.estado is None
    assert a.ultima_busqueda is None
    e.falso.sin_conexion = False
    e.reloj.avanzar(minutes=59)
    consultas = e.consultas
    a.paso()
    assert e.consultas == consultas  # not before the next check
    e.reloj.avanzar(minutes=2)
    a.paso()
    assert a.nueva is not None


def test_buscar_sin_version_nueva_y_con_un_backend_antiguo(e: Escenario) -> None:
    e.falso.versiones = publicadas(version="0.4.3")
    assert e.actualizador.buscar() == {"ok": True, "nueva": False, "version": "0.4.3"}
    e.falso.sin_versiones = True
    assert e.actualizador.buscar()["ok"] is True  # 404: no error for the person


def test_version_minima(e: Escenario) -> None:
    """CA-43.8: below ``versionMinima`` the band asks to update; detection goes on."""
    e.falso.versiones = publicadas(minima="0.4.0")
    e.actualizador.buscar()
    assert not e.actualizador.debajo_de_la_minima
    e.falso.versiones = publicadas(minima="0.5.0")
    e.actualizador.buscar()
    assert e.actualizador.debajo_de_la_minima
    assert e.actualizador.a_json()["minima"] is True


# ------------------------------------------------------------------ download and install (CA-43.2)


def test_descarga_verifica_e_instala_en_silencio(e: Escenario) -> None:
    a = e.actualizador
    a.buscar()
    assert a.descargar() == {"ok": True}
    assert len(e.lanzados) == 1
    instalado = e.lanzados[0]
    assert instalado.name == "te-tengo-captura-0.5.0-setup.exe"
    assert instalado.read_bytes() == INSTALADOR
    assert a.estado is Estado.REINICIANDO
    assert e.salidas == 1  # the window closes; the installer opens the new version
    assert instalador.leer_marca(e.directorio) == {
        "desde": "0.4.3",
        "hacia": "0.5.0",
        "instalador": str(instalado),
    }
    # The next start: «Terminando la actualización…», then the installer is deleted.
    siguiente = e.crear()
    assert siguiente.terminando
    siguiente._terminar_actualizacion()
    assert not instalado.exists()
    assert instalador.leer_marca(e.directorio) is None


def test_suma_que_no_coincide_borra_el_archivo_y_conserva_la_version(e: Escenario) -> None:
    e.falso.versiones = publicadas(sha256="0" * 64)
    a = e.actualizador
    a.buscar()
    a.descargar()
    assert a.estado is Estado.ALTERADA  # «No se pudo verificar la descarga. No se instaló.»
    assert e.lanzados == []
    assert e.salidas == 0
    assert list((e.directorio / "actualizaciones").iterdir()) == []
    assert a.version == "0.4.3"


@pytest.mark.parametrize(
    ("preparar", "estado"),
    [
        (lambda f: setattr(f, "almacen_falla", 500), Estado.FALLO),
        (lambda f: f.instaladores.clear(), Estado.FALLO),  # 404
        (lambda f: setattr(f, "sin_conexion", True), Estado.SIN_INTERNET),
    ],
)
def test_descarga_fallida_no_instala_nada(
    e: Escenario, preparar: Callable[[BackendFalso], None], estado: Estado
) -> None:
    a = e.actualizador
    a.buscar()
    preparar(e.falso)
    a.descargar()
    assert a.estado is estado
    assert e.lanzados == []
    assert not any((e.directorio / "actualizaciones").glob("*"))
    e.falso.almacen_falla, e.falso.sin_conexion = None, False
    e.falso.instaladores["te-tengo-captura-setup.exe"] = INSTALADOR
    a.descargar()  # «Reintentar»
    assert len(e.lanzados) == 1


def test_sin_espacio_no_descarga(e: Escenario) -> None:
    e.libre = 50 * 2**20
    a = e.actualizador
    a.buscar()
    a.descargar()
    assert a.estado is Estado.SIN_ESPACIO
    # 86 MB + the 100 MB reserve − 50 MB free: «Libera 136 MB en el disco C:.»
    assert a.a_json()["free"] == 136
    assert a.a_json()["drive"]
    assert len(e.falso.solicitudes) == 1  # only GET /api/versiones: nothing downloaded


def test_cancelar_la_descarga(tmp_path: Path) -> None:
    datos = INSTALADOR * 1000
    cancelada = __import__("threading").Event()

    def responder(_s: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=datos)

    def progreso(_pct: int) -> None:
        cancelada.set()  # «Cancelar» after the first block

    r = descarga.descargar(
        "http://x/i.exe",
        hashlib.sha256(datos).hexdigest(),
        tmp_path / "i.exe",
        al_progreso=progreso,
        cancelada=cancelada,
        transporte=httpx.MockTransport(responder),
    )
    assert r.resultado is descarga.Resultado.CANCELADA
    assert list(tmp_path.iterdir()) == []


def test_disco_lleno_al_escribir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import errno

    def lleno(*_a: object, **_k: object) -> descarga.Resultado:
        raise OSError(errno.ENOSPC, "No space left on device")

    monkeypatch.setattr(descarga, "_bajar", lleno)
    r = descarga.descargar("http://x/i.exe", SHA, tmp_path / "i.exe", tamano=10)
    assert r.resultado is descarga.Resultado.SIN_ESPACIO
    assert r.faltan_bytes > 0


def test_comando_del_instalador_silencioso(tmp_path: Path) -> None:
    llamadas: list[tuple[list[str], dict[str, Any]]] = []

    def popen(argv: list[str], **opciones: Any) -> None:
        llamadas.append((argv, opciones))

    archivo = tmp_path / "te-tengo-captura-0.5.0-setup.exe"
    instalador.lanzar(archivo, popen=popen)
    argv, opciones = llamadas[0]
    assert argv == [
        str(archivo),
        "/VERYSILENT",
        "/SUPPRESSMSGBOXES",
        "/NORESTART",
        "/RELANZAR",
        f"/LOG={tmp_path / 'instalacion.log'}",
    ]
    # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP: it outlives this process.
    assert opciones["creationflags"] == 0x00000008 | 0x00000200
    assert opciones["close_fds"] is True
    assert opciones["stdin"] is subprocess.DEVNULL


def test_el_mutex_que_espera_el_instalador() -> None:
    class Kernel32:
        def __init__(self) -> None:
            self.nombres: list[str] = []

        def CreateMutexW(self, _a: object, _b: bool, nombre: str) -> int:  # noqa: N802
            self.nombres.append(nombre)
            return 42

    k = Kernel32()
    assert crear_mutex(kernel32=k) == 42
    assert k.nombres == [MUTEX]
    iss = (Path(__file__).parents[2] / "packaging" / "te-tengo-captura.iss").read_text("utf-8")
    assert f'"{MUTEX}"' in iss  # the installer waits on the same name
    assert "/RELANZAR" in iss


def test_un_fallo_al_lanzar_el_instalador_conserva_la_version(e: Escenario) -> None:
    def falla(_archivo: Path) -> None:
        raise OSError("bloqueado por el antivirus")

    a = e.crear(lanzar=falla)
    a.buscar()
    a.descargar()
    assert a.estado is Estado.FALLO
    assert e.salidas == 0
    assert instalador.leer_marca(e.directorio) is None


# ------------------------------------------------------------------ never during an alert (CA-43.9)


@pytest.mark.parametrize(("motivo", "texto"), [("alerta", "alerta"), ("vivo", "vivo")])
def test_espera_a_que_termine_la_alerta_o_la_vista(e: Escenario, motivo: str, texto: str) -> None:
    a = e.actualizador
    a.buscar()
    e.bloqueo = motivo
    a.descargar()  # download and verification go on
    assert a.estado is Estado.ESPERANDO
    assert a.a_json()["why"] == texto
    assert a.a_json()["ready"] is True
    assert e.lanzados == []
    a.paso()
    assert e.lanzados == []  # still waiting
    assert a.aviso_pendiente() is None  # no notice either
    e.bloqueo = None
    a.paso()  # it goes on by itself
    assert len(e.lanzados) == 1
    assert e.salidas == 1


def test_alerta_en_curso_hasta_que_se_levanta_o_pasa_el_tiempo() -> None:
    reloj = Reloj(datetime(2026, 1, 1))
    seg = SeguimientoAlerta(reloj=lambda: reloj.ahora.timestamp())
    assert not seg.en_curso
    seg.observar([TipoEvento.MOVIMIENTO_INESTABLE])
    assert not seg.en_curso
    seg.observar([TipoEvento.CAIDA])
    assert seg.en_curso
    seg.observar([TipoEvento.RECUPERACION])
    assert not seg.en_curso
    seg.observar([TipoEvento.CAIDA_CONFIRMADA])
    reloj.avanzar(seconds=DURACION_S - 1)
    assert seg.en_curso
    reloj.avanzar(seconds=1)
    assert not seg.en_curso


# ------------------------------------------------------------------ automatically (CA-43.7)


def test_proxima_madrugada() -> None:
    assert proxima_madrugada(datetime(2026, 9, 23, 2, 59)) == datetime(2026, 9, 23, 3, 0)
    assert proxima_madrugada(datetime(2026, 9, 23, 3, 0)) == datetime(2026, 9, 24, 3, 0)
    assert proxima_madrugada(datetime(2026, 12, 31, 22, 0)) == datetime(2027, 1, 1, 3, 0)
    assert en_madrugada(datetime(2026, 9, 23, 3, 0)) == datetime(2026, 9, 23).date()
    assert en_madrugada(datetime(2026, 9, 23, 5, 59)) is not None
    assert en_madrugada(datetime(2026, 9, 23, 6, 0)) is None
    assert en_madrugada(datetime(2026, 9, 23, 2, 59)) is None


def test_se_actualiza_sola_de_madrugada(e: Escenario) -> None:
    a = e.actualizador
    assert a.automatica  # on by default on Windows
    a.paso()  # 10:30: a new version, but not at night
    assert e.lanzados == []
    e.reloj.ahora = datetime(2026, 9, 24, 3, 0)
    e.bloqueo = "vivo"
    a.paso()
    assert e.lanzados == []  # never with a live view open
    e.reloj.avanzar(minutes=20)
    e.bloqueo = None
    a.paso()
    assert len(e.lanzados) == 1
    assert e.salidas == 1


def test_no_se_actualiza_sola_si_se_desactivo(e: Escenario) -> None:
    a = e.actualizador
    assert a.cambiar_automatica(False) is False
    assert a.actualizacion_automatica() is False
    assert e.crear().automatica is False  # remembered
    e.reloj.ahora = datetime(2026, 9, 24, 3, 0)
    a.paso()
    assert a.nueva is not None
    assert e.lanzados == []


def test_una_vez_por_noche_aunque_falle(e: Escenario) -> None:
    e.falso.versiones = publicadas(sha256="0" * 64)
    e.reloj.ahora = datetime(2026, 9, 24, 3, 0)
    a = e.actualizador
    a.paso()
    assert a.estado is Estado.ALTERADA
    descargas = len(e.falso.solicitudes)
    e.reloj.avanzar(minutes=30)
    a.paso()
    assert len(e.falso.solicitudes) == descargas  # not again tonight


def test_en_mac_nunca_descarga_ni_se_actualiza_sola(tmp_path: Path) -> None:
    e = Escenario(tmp_path, plataforma=Plataforma.MAC)
    a = e.actualizador
    assert not a.automatica
    assert a.actualizacion_automatica() is False
    a.buscar()
    assert a.nueva is not None
    assert not a.se_descarga
    assert a.descargar() == {"ok": True, "pagina": "tetengo.reqsai.tech/descargas"}
    assert e.navegador == ["https://tetengo.reqsai.tech/descargas"]
    e.reloj.ahora = datetime(2026, 9, 24, 3, 0)
    a.paso()
    assert e.lanzados == []
    assert not any(s.url.host == HOST_ALMACEN for s in e.falso.solicitudes)
    datos = a.a_json()
    assert (datos["os"], datos["download"], datos["auto"], datos["dmg"]) == (
        "mac",
        False,
        False,
        "te-tengo-captura.dmg",
    )


def test_windows_sin_instalador_va_a_la_descarga(e: Escenario) -> None:
    e.falso.versiones = publicadas(url=None, sha256=None)
    a = e.actualizador
    a.buscar()
    assert not a.se_descarga
    assert a.descargar()["pagina"] == "tetengo.reqsai.tech/descargas"
    assert e.lanzados == []


def test_sin_canal_no_se_busca(tmp_path: Path) -> None:
    e = Escenario(tmp_path, plataforma=None)
    assert e.actualizador.buscar()["nueva"] is False
    assert e.consultas == 0
    assert e.actualizador.actualizacion_automatica() is None


# ------------------------------------------------------------------ one notice per version


def test_un_solo_aviso_del_sistema_por_version(e: Escenario) -> None:
    a = e.actualizador
    a.buscar()
    avisos: list[Notificacion] = []
    sistema = Avisos(avisos.append)
    sistema.ventana_oculta(SimpleNamespace(agente=None, quitada=False, a_json=dict))
    avisos.clear()
    sistema.version_nueva(a.aviso_pendiente(), False, a.marcar_notificada)
    assert avisos == [
        Notificacion("Hay una versión nueva: 0.5.0", "Ábrelo para descargarla. La detección sigue.")
    ]
    sistema.version_nueva(a.aviso_pendiente(), False, a.marcar_notificada)
    otro = e.crear()  # after a restart, or the same version published again
    otro.buscar()
    sistema.version_nueva(otro.aviso_pendiente(), False, otro.marcar_notificada)
    assert len(avisos) == 1
    e.falso.versiones = publicadas(version="0.5.1")
    otro.buscar()
    sistema.version_nueva(otro.aviso_pendiente(), True, otro.marcar_notificada)
    assert avisos[-1] == Notificacion(
        "Hay una versión nueva: 0.5.1", "Ábrelo para ir a la descarga."
    )


def test_con_la_ventana_abierta_no_hay_aviso_del_sistema(e: Escenario) -> None:
    a = e.actualizador
    a.buscar()
    avisos: list[Notificacion] = []
    Avisos(avisos.append).version_nueva(a.aviso_pendiente(), False, a.marcar_notificada)
    assert avisos == []
    assert not a.marcar_notificada("0.5.0")  # the band said it: counted as announced


def test_registrar_version_una_vez(e: Escenario) -> None:
    assert e.actualizador.registrar_version() is None  # first run: nothing to say
    nueva = Actualizador("0.5.0", e.directorio, lambda: None)
    assert nueva.registrar_version() == ("0.4.3", "0.5.0")
    assert Actualizador("0.5.0", e.directorio, lambda: None).registrar_version() is None
