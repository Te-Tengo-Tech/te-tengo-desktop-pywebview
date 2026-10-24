"""The PC's states and the moves between them (US-28, US-31), against the fake backend."""

import json
import time
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from te_tengo_captura.agente import Agente
from te_tengo_captura.backend.cliente import ClienteBackend
from te_tengo_captura.backend.falso import URL_API, BackendFalso
from te_tengo_captura.captura.dispositivos import Dispositivo
from te_tengo_captura.captura.fuentes import FuenteFalsa
from te_tengo_captura.config import Configuracion
from te_tengo_captura.coordinador import Coordinador, Pantalla
from te_tengo_captura.vinculacion.credenciales import AlmacenCredenciales, LlaveroEnMemoria
from tests.captura.test_agente import SinPersonas

WEBCAMS = [
    Dispositivo("id-1", "Webcam USB HD", 0, 1200),
    Dispositivo("id-2", "Logitech C920", 1, 1200),
]


def esperar(prueba: Callable[[], object], limite_s: float = 45) -> None:
    fin = time.monotonic() + limite_s
    while not prueba():
        assert time.monotonic() < fin, "no ocurrió a tiempo"
        time.sleep(0.02)


class Escenario:
    def __init__(self, tmp_path: Path) -> None:
        self.falso = BackendFalso(credencial="credencial-1", intervalo=0)
        self.almacen = AlmacenCredenciales(LlaveroEnMemoria())
        self.datos = tmp_path / "datos"
        self.olvidadas = 0
        self.configuraciones_borradas = 0
        self.autoinicios_quitados = 0
        self.coordinador: Coordinador | None = None

    def crear(
        self,
        instalacion: Callable[[Callable[[str], None]], Agente] | None = None,
        plataforma: str | None = "auto",
    ) -> Coordinador:
        def olvidar() -> None:
            self.olvidadas += 1

        def borrar_configuracion() -> None:
            self.configuraciones_borradas += 1

        def quitar_autoinicio() -> bool:
            self.autoinicios_quitados += 1
            return True

        self.coordinador = Coordinador(
            "0.5.0",
            URL_API,
            self.datos,
            self.almacen,
            instalacion=instalacion,
            olvidar_instalacion=olvidar,
            olvidar_configuracion=borrar_configuracion,
            quitar_autoinicio=quitar_autoinicio,
            transporte=self.falso.transporte(),
            canal_pc=False,
            listar=lambda: list(WEBCAMS),
            plataforma=plataforma,
        )
        return self.coordinador

    def vincular(self, plataforma: str | None = "auto") -> Coordinador:
        c = self.crear(plataforma=plataforma)
        c.iniciar()
        esperar(lambda: self.falso.codigo_pendiente())
        self.falso.aprobar()
        esperar(lambda: c.estado().pantalla is Pantalla.VINCULADA)
        return c


@pytest.fixture
def e(tmp_path: Path) -> Iterator[Escenario]:
    escenario = Escenario(tmp_path)
    yield escenario
    if escenario.coordinador is not None:
        escenario.coordinador.detener()


def test_recien_instalada_muestra_el_codigo(e: Escenario) -> None:
    c = e.crear()
    c.iniciar()
    esperar(lambda: c.estado().a_json()["pair"]["code"])
    estado = c.estado()
    assert estado.pantalla is Pantalla.VINCULAR
    assert (estado.bandeja.k, estado.bandeja.etiqueta) == ("off", "sin vincular")
    datos = estado.a_json()
    assert datos["screen"] == "vincular"
    assert datos["pair"]["code"] == e.falso.codigo_pendiente()
    assert datos["pair"]["url"] == "app.tetengo.reqsai.tech/vincular"
    assert datos["pair"]["qr"]["n"] >= 21
    assert datos["pair"]["left"] == 600
    assert e.falso.vinculaciones[0]["nombre_pc"] == datos["pcname"]
    # The installation id from the credential store, so the app can say «Esta PC ya está vinculada».
    assert e.falso.vinculaciones[0]["id_instalacion"] == e.almacen.id_instalacion()
    assert "device_code" not in json.dumps(datos)
    assert "dispositivo-secreto" not in json.dumps(datos)


def test_aprobada_en_el_celular_queda_vinculada(e: Escenario) -> None:
    c = e.vincular()
    assert e.almacen.leer() is not None  # tokens in the OS credential store
    esperar(lambda: c.estado().a_json().get("linkedBy"))
    datos = c.estado().a_json()
    assert datos["screen"] == "vinculada"
    assert datos["home"]["who"] == "Rosa Huamán"
    assert datos["linkedBy"] == "Carmen"
    assert sorted(d["name"] for d in datos["devices"]) == ["Logitech C920", "Webcam USB HD"]
    assert c.estado().bandeja.etiqueta == "falta elegir las cámaras en la app"
    c.ir_a_estado()
    estado = c.estado()
    assert estado.pantalla is Pantalla.PRINCIPAL
    assert estado.a_json()["unlink"] is True
    assert estado.a_json()["dataBytes"] >= 0  # «Borrar también los datos… (3,2 GB)»
    assert estado.agente is not None
    assert estado.agente.aviso.titulo_html == "Falta elegir las cámaras en la app"
    esperar(lambda: e.falso.senales_pc)  # «En línea» in the app with no camera (CA-30.2)
    assert e.falso.senales_pc[0]["versionAgente"] == "0.5.0"


def test_al_reiniciar_sigue_vinculada_sin_pedir_el_codigo(e: Escenario) -> None:
    c = e.vincular()
    c.detener()
    otro = e.crear()
    otro.iniciar()
    assert otro.estado().pantalla is Pantalla.PRINCIPAL  # CA-28.7
    assert len(e.falso.vinculaciones) == 1


def test_el_id_de_instalacion_sobrevive_a_quitarla(e: Escenario) -> None:
    c = e.vincular()
    c.ir_a_estado()
    esperar(lambda: c.pc is not None and c.pc.latido.pc is not None)
    e.falso.quitar_pc()
    c.reintentar_ahora()
    esperar(lambda: c.estado().pantalla is Pantalla.QUITADA)
    assert e.almacen.leer() is None
    assert e.almacen.id_instalacion() == e.falso.vinculaciones[0]["id_instalacion"]


def test_quitada_desde_la_app(e: Escenario) -> None:
    c = e.vincular()
    c.ir_a_estado()
    esperar(lambda: c.pc is not None and c.pc.latido.pc is not None)  # the household is known
    e.falso.quitar_pc()
    c.reintentar_ahora()  # the next request answers 401 PC_DESVINCULADA
    esperar(lambda: c.estado().pantalla is Pantalla.QUITADA)
    estado = c.estado()
    assert estado.quitada
    assert estado.a_json()["who"] == "Rosa Huamán"
    assert (estado.bandeja.k, estado.bandeja.etiqueta) == ("off", "se quitó de la vivienda")
    assert e.almacen.leer() is None  # credentials deleted (CA-31.1)
    assert not (e.datos / "pc.json").exists()
    # A restart still says it was removed until «Vincular de nuevo».
    c.detener()
    otro = e.crear()
    otro.iniciar()
    assert otro.estado().pantalla is Pantalla.QUITADA
    otro.vincular_de_nuevo()
    esperar(lambda: otro.estado().a_json().get("pair", {}).get("code"))
    assert otro.estado().pantalla is Pantalla.VINCULAR


def test_mensaje_desvincular_del_canal(e: Escenario) -> None:
    c = e.vincular()
    assert c.pc is not None
    c.pc.sesion.desvincular("desvincular")  # what the PC channel does on the message
    esperar(lambda: c.estado().pantalla is Pantalla.QUITADA)


@pytest.mark.parametrize("borrar", [False, True])
def test_desvincular_desde_esta_pc(e: Escenario, borrar: bool) -> None:
    c = e.vincular()
    c.ir_a_estado()
    (e.datos / "clips").mkdir(parents=True, exist_ok=True)
    guardado = c.almacen.carpeta / "movimientos" / "c1" / "x.parquet.ttg"
    guardado.parent.mkdir(parents=True)
    guardado.write_bytes(b"TTG1")
    resultado = c.desvincular(borrar)
    assert resultado == {"ok": True, "avisada": True}
    assert e.falso.desvinculaciones == [{"via": "delete", "datos": "true" if borrar else None}]
    assert e.almacen.leer() is None
    assert c.estado().pantalla is Pantalla.VINCULAR  # the code again (CA-31.3)
    assert not (e.datos / "clips").exists()
    assert guardado.exists() is not borrar  # «Borrar también los datos de esta PC» (CA-31.6)


def test_desvincular_sin_internet_queda_pendiente_y_se_envia_despues(e: Escenario) -> None:
    c = e.vincular()
    c.ir_a_estado()
    e.falso.sin_conexion = True
    assert c.desvincular(True) == {"ok": True, "avisada": False}
    pendiente = e.almacen.leer_revocacion()
    assert pendiente is not None
    assert pendiente.datos_locales_borrados
    assert e.almacen.leer() is None
    e.falso.sin_conexion = False
    c.detener()
    otro = e.crear()
    otro.iniciar()
    esperar(lambda: e.almacen.leer_revocacion() is None)
    assert e.falso.desvinculaciones == [{"via": "revocacion", "datos": "true"}]


def test_restablecer_esta_pc_avisa_borra_todo_y_vuelve_al_codigo(e: Escenario) -> None:
    c = e.vincular()
    c.ir_a_estado()
    c.cambiar_modo_avanzado(True)
    for ruta in (e.datos / "clips" / "e.mp4", e.datos / "actividad.jsonl", e.datos / "x.json"):
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text("x")
    guardado = c.almacen.carpeta / "movimientos" / "c1" / "x.parquet.ttg"
    guardado.parent.mkdir(parents=True)
    guardado.write_bytes(b"TTG1")
    assert c.restablecer() == {"ok": True, "avisada": True}
    assert e.falso.desvinculaciones == [
        {"via": "delete", "datos": "true", "motivo": "restablecida"}
    ]
    assert e.almacen.leer() is None
    assert e.almacen.llavero.get_password("TeTengoCaptura", "clave-datos") is None
    assert (e.configuraciones_borradas, e.autoinicios_quitados) == (1, 1)
    assert not guardado.exists()
    assert not (e.datos / "clips").exists()
    assert not (e.datos / "actividad.jsonl").exists()
    assert not (e.datos / "x.json").exists()
    assert not c.modo_avanzado
    esperar(lambda: c.estado().a_json().get("pair", {}).get("code"))
    assert c.estado().pantalla is Pantalla.VINCULAR  # as on a new install
    assert c.restablecer() == {"ok": True, "avisada": False}  # unlinked: only deletes again


def test_restablecer_sin_internet_deja_la_desvinculacion_pendiente(
    e: Escenario, monkeypatch: pytest.MonkeyPatch
) -> None:
    import te_tengo_captura.coordinador as modulo

    monkeypatch.setattr(modulo, "REVOCACION_REINTENTO_S", 0.05)
    c = e.vincular()
    c.ir_a_estado()
    e.falso.sin_conexion = True
    assert c.restablecer("desinstalada") == {"ok": True, "avisada": False}
    pendiente = e.almacen.leer_revocacion()
    assert pendiente is not None
    assert pendiente.motivo == "desinstalada"
    assert e.almacen.leer() is None
    e.falso.sin_conexion = False
    esperar(lambda: e.almacen.leer_revocacion() is None)
    assert e.falso.desvinculaciones == [
        {"via": "revocacion", "datos": "true", "motivo": "desinstalada"}
    ]


def test_noventa_dias_sin_conexion(e: Escenario) -> None:
    c = e.vincular()
    c.ir_a_estado()
    # The first heartbeat records the last contact (then only hourly): wait for it, so it cannot
    # overwrite the 91-day-old contact written below.
    pc = c.pc
    assert pc is not None
    esperar(lambda: pc.latido.pc is not None and (e.datos / "ultimo_contacto.json").exists())
    (e.datos / "ultimo_contacto.json").write_text(json.dumps({"en": time.time() - 91 * 86400}))
    # The server unlinked it after 90 days: the refresh gives invalid_grant. It is reported before
    # the fake backend drops the PC, so no request of a worker thread can answer PC_DESVINCULADA
    # first (which shows «Esta PC se quitó» instead).
    pc.sesion.desvincular("invalid_grant")
    e.falso.quitar_pc()
    esperar(lambda: c.estado().a_json().get("pair", {}).get("re90"))
    assert c.estado().pantalla is Pantalla.VINCULAR


def test_rechazada_en_el_celular(e: Escenario) -> None:
    c = e.crear()
    c.iniciar()
    esperar(lambda: e.falso.codigo_pendiente())
    e.falso.rechazar()
    esperar(lambda: c.estado().pantalla is Pantalla.RECHAZADA)
    c.otro_codigo()
    esperar(lambda: c.estado().a_json().get("pair", {}).get("code"))


def test_una_instalacion_quitada_deja_de_capturar_y_olvida_su_credencial(
    e: Escenario, configuracion: Configuracion
) -> None:
    agentes: list[Agente] = []

    def instalar(al_desvincular: Callable[[str], None]) -> Agente:
        cliente = ClienteBackend(URL_API, "credencial-1", "Sala", "0.5.0", e.falso.transporte())
        agente = Agente(
            configuracion,
            cliente,
            FuenteFalsa(paso=1 / 8),
            SinPersonas(),
            e.datos,
            "0.5.0",
            codificar=lambda f: b"mp4",
            al_desvincular=al_desvincular,
        )
        agentes.append(agente)
        return agente

    c = e.crear(instalacion=instalar)
    c.iniciar()
    assert c.reintentar_ahora()
    assert agentes[0]._permitida()
    e.falso.quitar_instalacion()  # «Quitar esta PC» on «PC de la casa» in the app
    c.reintentar_ahora()
    assert not agentes[0]._permitida()  # capture stops at once (CA-31.1)
    esperar(lambda: c.estado().pantalla is Pantalla.QUITADA)
    assert e.olvidadas == 1  # the installation credential is deleted from config.toml
    assert c.estado().a_json()["who"] == "Rosa Huamán"
    c.vincular_de_nuevo()
    esperar(lambda: c.estado().pantalla is Pantalla.VINCULAR)


def test_modo_avanzado_apagado_por_defecto_y_anotado(e: Escenario) -> None:
    c = e.vincular()
    c.ir_a_estado()
    assert c.modo_avanzado is False  # CA-32.1
    assert c.estado().a_json()["advanced"] is False
    assert c.registro("x", 0) == []
    assert c.cambiar_modo_avanzado(True)
    assert c.diario.activo
    assert c.estado().a_json()["advanced"] is True
    lista = c.lista_actividad()
    assert lista[0]["m"] == "Desde esta PC: se activó el modo avanzado"
    assert lista[0]["who"] == "pc"
    assert c.pc is not None
    c.pc.reintentar_ahora()  # the heartbeat sends what is pending
    esperar(lambda: any(a["tipo"] == "MODO_AVANZADO_ACTIVADO" for a in e.falso.actividad.values()))
    esperar(lambda: not c.lista_actividad()[0]["pend"])
    esperar(lambda: any("vinculó la PC" in a["m"] for a in c.lista_actividad()))
    c.cambiar_modo_avanzado(False)
    assert not c.diario.activo


def test_diagnostico_desde_el_coordinador(e: Escenario, tmp_path: Path) -> None:
    c = e.vincular()
    c.ir_a_estado()
    nombre = c.nombre_diagnostico()
    assert nombre.startswith("te-tengo-diagnostico-")
    assert nombre.endswith(".zip")
    r = c.exportar_diagnostico(tmp_path / nombre)
    assert r["ok"] is True
    assert r["tamano"] > 0
    import zipfile

    with zipfile.ZipFile(tmp_path / nombre) as archivo:
        datos = json.loads(archivo.read("diagnostico.json"))
        contenido = b"".join(archivo.read(n) for n in archivo.namelist())
    assert datos["modo"] == "pc"
    assert datos["programa"] == "Te Tengo Captura 0.5.0"
    assert c.pc is not None
    for secreto in c.pc.sesion.secretos():
        assert secreto.encode() not in contenido


def test_almacenamiento_desde_la_ventana(e: Escenario) -> None:
    c = e.vincular()
    c.ir_a_estado()
    esperar(lambda: c.almacen.puede_movimientos)  # asked as soon as the PC started (CA-35.3)
    store = c.estado().a_json()["store"]
    assert store["permisoMovimientos"] is True
    assert store["nube"] == 90
    assert store["ajustes"]["video"] is False  # CA-38.2
    assert c.cambiar_almacenamiento({"limite_gb": 25, "carpeta": "/otra"}) == {"ok": True}
    assert c.almacen.ajustes.limite_gb == 25
    assert c.almacen.ajustes.carpeta is None  # only «Cambiar carpeta» moves the folder
    entrada = c.lista_actividad()[0]
    assert entrada["m"] == "Desde esta PC: el límite de espacio pasó de 50 GB a 25 GB"

    e.falso.movimientos_en_la_pc = False  # Rosa no longer allows it (CA-35.4)
    c.almacen.revisar_permiso()
    assert c.estado().a_json()["store"]["permisoMovimientos"] is False
    assert c.cambiar_almacenamiento({"movimientos": True}) == {"ok": False, "codigo": "SIN_PERMISO"}
    assert c.borrar_movimientos()["ok"] is True
    assert c.lista_actividad()[0]["m"] == "Desde esta PC: se borraron los movimientos guardados"
    assert c.pc is not None
    c.pc.reintentar_ahora()
    esperar(
        lambda: (
            {"GUARDADO_LOCAL_CAMBIADO", "DATOS_LOCALES_ELIMINADOS"}
            <= {a["tipo"] for a in e.falso.actividad.values()}
        )
    )


def test_ver_que_paso_desde_el_coordinador(e: Escenario) -> None:
    from te_tengo_captura.almacen.gestor import GrabadorCamara
    from te_tengo_captura.almacen.puntos import FilaMovimiento

    c = e.vincular()
    c.ir_a_estado()
    esperar(lambda: c.almacen.puede_movimientos)
    assert c.repeticion() == {"permitida": True, "camaras": []}  # no camera in use yet
    ahora = int(time.time() * 1000)
    grabador = GrabadorCamara(c.almacen, "c1")
    for i in range(80):
        grabador._cola.put(
            ("fila", FilaMovimiento(ahora - 60_000 + i * 125, [(0.5, 0.5, 0.0, 0.9)] * 33))
        )
    grabador.cerrar()
    ventana = c.repeticion_ventana("c1", ahora - 120_000, ahora)
    assert ventana["hayDatos"] is True
    assert len(c.repeticion_poses("c1", ahora - 60_000, ahora)["t"]) == 80
    assert c.repeticion_video("c1", ahora) is None
    assert c.cerrar_repeticion("c1", ahora - 120_000, ahora, 95) == {"ok": True}
    entrada = c.lista_actividad()[0]["m"]
    assert entrada.startswith("Desde esta PC: se vio qué pasó en «c1» (")  # CA-39.3, on this PC
    assert entrada.endswith(", 2 min)")
    # The family's log gets it too (REPETICION_VISTA): the camera, the moment and the seconds.
    assert c.pc is not None
    c.pc.reintentar_ahora()  # the heartbeat sends what is pending
    esperar(lambda: any(a["tipo"] == "REPETICION_VISTA" for a in e.falso.actividad.values()))
    [vista] = [a for a in e.falso.actividad.values() if a["tipo"] == "REPETICION_VISTA"]
    assert vista["camaraId"] == "c1"
    assert vista["duracionSegundos"] == 95
    assert vista["momentoDesde"] < vista["momentoHasta"]
    assert vista["momentoHasta"].endswith("Z")
    assert "objeto" not in vista  # no camera in use: the API names the room


def test_el_latido_de_la_pc_dice_si_se_actualiza_sola(e: Escenario) -> None:
    """US-43, CA-43.7: on by default on Windows; the switch goes to the activity log."""
    c = e.vincular(plataforma="windows")
    esperar(lambda: e.falso.senales_pc)
    assert e.falso.senales_pc[-1]["actualizacionAutomatica"] is True
    assert c.cambiar_actualizacion_automatica(False) is False
    c.pc.reintentar_ahora()  # type: ignore[union-attr]
    esperar(lambda: e.falso.senales_pc[-1].get("actualizacionAutomatica") is False)
    tipos = [a.get("tipo") for a in c.actividad.entradas()]
    assert "ACTUALIZACION_AUTOMATICA_DESACTIVADA" in tipos
    esperar(
        lambda: any(
            a["tipo"] == "ACTUALIZACION_AUTOMATICA_DESACTIVADA" for a in e.falso.actividad.values()
        )
    )
    assert c.cambiar_actualizacion_automatica(False) is False  # no change: no new entry
    assert len([t for t in (a.get("tipo") for a in c.actividad.entradas()) if t]) == 1


def test_sin_sistema_con_actualizaciones_el_latido_no_lo_dice(e: Escenario) -> None:
    e.vincular(plataforma=None)
    esperar(lambda: e.falso.senales_pc)
    assert "actualizacionAutomatica" not in e.falso.senales_pc[0]


def test_pc_actualizada_se_anota_una_vez_al_iniciar(e: Escenario) -> None:
    """CA-43.2: after a newer version starts, «Esta PC se actualizó a X» (PC_ACTUALIZADA)."""
    e.datos.mkdir(parents=True)
    (e.datos / "actualizaciones.json").write_text(json.dumps({"ultimaVersion": "0.4.3"}))
    c = e.vincular(plataforma="windows")
    entradas = [a for a in c.actividad.entradas() if a.get("tipo") == "PC_ACTUALIZADA"]
    assert len(entradas) == 1
    assert entradas[0]["texto"] == "Esta PC se actualizó a 0.5.0"
    assert (entradas[0]["objeto"], entradas[0]["valorAnterior"], entradas[0]["valorNuevo"]) == (
        "Te Tengo Captura",
        "0.4.3",
        "0.5.0",
    )
    c.ir_a_estado()
    assert c.estado().a_json()["upd"]["updated"] == "0.5.0"  # «Te Tengo Captura se actualizó a…»
    esperar(lambda: any(a["tipo"] == "PC_ACTUALIZADA" for a in e.falso.actividad.values()))
    c.detener()
    otro = e.crear(plataforma="windows")
    otro._anotar_version()  # the next start: the same version, nothing new
    tipos = [a.get("tipo") for a in otro.actividad.entradas()]
    assert tipos.count("PC_ACTUALIZADA") == 1


def test_que_se_ve_en_la_vista_previa_se_recuerda_en_esta_pc(e: Escenario) -> None:
    from te_tengo_captura.coordinador import ARCHIVO_VENTANA, modo_vista_previa

    c = e.vincular()
    c.ir_a_estado()
    assert c.estado().a_json()["pvMode"] == {"video": True, "skel": False}  # only video
    c.cambiar_modo_avanzado(True)
    assert c.cambiar_vista_previa(True, True) == {"video": True, "skel": True}
    assert c.estado().a_json()["pvMode"] == {"video": True, "skel": True}
    guardado = json.loads((e.datos / ARCHIVO_VENTANA).read_text("utf-8"))
    assert guardado == {"modoAvanzado": True, "vistaPrevia": "VIDEO_CON_POSTURA"}
    assert c.lista_actividad()[0]["m"] == "Desde esta PC: se activó el modo avanzado"  # not logged
    c.detener()
    otra = e.crear()  # the next start on this PC
    assert otra.modo_avanzado is True
    assert otra.cambiar_vista_previa(False, True) == {"video": False, "skel": True}
    assert modo_vista_previa(False, False).value == "VIDEO"  # at least one stays on


def test_que_se_ve_ilegible_vuelve_a_solo_video(e: Escenario) -> None:
    from te_tengo_captura.coordinador import ARCHIVO_VENTANA

    e.datos.mkdir(parents=True)
    (e.datos / ARCHIVO_VENTANA).write_text('{"vistaPrevia": "OTRA"}', encoding="utf-8")
    c = e.crear()
    assert c.cambiar_vista_previa(True, False) == {"video": True, "skel": False}
