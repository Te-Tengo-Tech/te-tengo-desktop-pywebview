"""The cameras of a linked PC (US-29, US-30) against the fake backend."""

import threading
import time
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import ClassVar

import numpy as np
import pytest

from te_tengo_captura.agente_pc import FabricaCamaras
from te_tengo_captura.backend.falso import URL_API, BackendFalso
from te_tengo_captura.backend.modelos import ModoVista
from te_tengo_captura.captura.dispositivos import Dispositivo
from te_tengo_captura.captura.fuentes import FuenteFalsa, Imagen
from te_tengo_captura.config import AjustesPc
from te_tengo_captura.coordinador import Coordinador, Pantalla
from te_tengo_captura.estado import Situacion
from te_tengo_captura.vinculacion.credenciales import AlmacenCredenciales, LlaveroEnMemoria
from te_tengo_deteccion.pose.schemas import Pose


def esperar(prueba: Callable[[], object], limite_s: float = 15) -> None:
    fin = time.monotonic() + limite_s
    while not prueba():
        assert time.monotonic() < fin, "no ocurrió a tiempo"
        time.sleep(0.02)


class Grabadora:
    """An estimator per camera that records its timestamps (VIDEO mode: increasing per stream)."""

    creadas: ClassVar[list["Grabadora"]] = []

    def __init__(self) -> None:
        self.instantes: list[int] = []
        self.hilos: set[str] = set()
        Grabadora.creadas.append(self)

    def estimar(self, imagen: Imagen, instante_ms: int) -> Pose | None:
        self.instantes.append(instante_ms)
        self.hilos.add(threading.current_thread().name)
        return None

    def reiniciar(self) -> None:
        pass

    def cerrar(self) -> None:
        pass


class Webcams:
    """The PC's USB webcams: which are plugged in, by OS id."""

    def __init__(self) -> None:
        self.enchufadas: list[Dispositivo] = [
            Dispositivo("usb-0c45-6366", "Webcam USB HD", 0, 1200),
            Dispositivo("usb-046d-082d", "Logitech C920", 1, 1200),
        ]
        self.abiertas: list[str] = []

    def listar(self) -> list[Dispositivo]:
        return list(self.enchufadas)

    def abrir(self, dispositivo_id: str) -> FuenteFalsa:
        webcams = self

        class PorId(FuenteFalsa):
            def abrir(self) -> bool:
                webcams.abiertas.append(dispositivo_id)
                self.conectada = any(d.dispositivo_id == dispositivo_id for d in webcams.enchufadas)
                return super().abrir()

        return PorId(ancho=64, alto=48, paso=1 / 30)


class Publicados:
    def __init__(self) -> None:
        self.urls: list[str] = []

    def abrir(self, url: str, fps: float) -> "Publicados":
        self.urls.append(url)
        return self

    def publicar(self, imagen: Imagen, instante: float) -> None:
        pass

    def cerrar(self) -> None:
        pass


class Escenario:
    def __init__(self, tmp_path: Path) -> None:
        Grabadora.creadas = []
        self.falso = BackendFalso(intervalo=0)
        self.falso.nombre_pc = "Sala-Rosa"
        self.webcams = Webcams()
        self.coordinador = Coordinador(
            "0.5.0",
            URL_API,
            tmp_path / "datos",
            AlmacenCredenciales(LlaveroEnMemoria()),
            transporte=self.falso.transporte(),
            canal_pc=False,
            listar=self.webcams.listar,
            fabrica=FabricaCamaras(
                ajustes=AjustesPc(),
                crear_estimador=Grabadora,
                abrir_fuente=self.webcams.abrir,
                transporte=self.falso.transporte(),
                canal=False,
            ),
        )
        self.coordinador.iniciar()
        esperar(self.falso.codigo_pendiente)
        self.falso.aprobar()
        esperar(lambda: self.coordinador.pc is not None)
        self.coordinador.ir_a_estado()
        esperar(lambda: self.falso.inventarios)

    @property
    def supervisor(self):  # type: ignore[no-untyped-def]
        assert self.coordinador.pc is not None
        return self.coordinador.pc.camaras

    def mensaje_de_la_app(self, camara_id: str) -> None:
        """What the API sends on the PC's channel after a change in the app."""
        w = self.falso.webcams_pc[camara_id]
        self.supervisor.al_mensaje(
            {
                "camara": {
                    "camaraId": camara_id,
                    "dispositivoId": w["dispositivoId"],
                    "nombreDispositivo": w["nombreDispositivo"],
                    "enUso": w["ambiente"] is not None,
                    "ambienteId": w["ambiente"],
                    "nombreHabitacion": self.falso.ambientes.get(w["ambiente"]),
                }
            }
        )


@pytest.fixture
def e(tmp_path: Path) -> Iterator[Escenario]:
    escenario = Escenario(tmp_path)
    yield escenario
    escenario.coordinador.detener()


def test_informa_las_webcams_por_su_identificador_unico(e: Escenario) -> None:
    assert e.falso.inventarios[0] == [
        {"dispositivoId": "usb-0c45-6366", "nombreDispositivo": "Webcam USB HD", "conectada": True},
        {"dispositivoId": "usb-046d-082d", "nombreDispositivo": "Logitech C920", "conectada": True},
    ]
    estado = e.coordinador.estado()
    assert estado.agente is not None
    assert estado.agente.situacion is Situacion.FALTA_ELEGIR  # «Falta elegir las cámaras en la app»
    dispositivos = estado.a_json()["devices"]
    assert [(d["name"], d["room"], d["uid"]) for d in dispositivos] == [
        ("Logitech C920", None, "usb-046d-082d"),
        ("Webcam USB HD", None, "usb-0c45-6366"),
    ]
    assert e.supervisor.agentes == {}  # only cameras in use capture


def test_sigue_las_asignaciones_del_celular(e: Escenario) -> None:
    sala = e.falso.asignar_desde_app("usb-0c45-6366", "Sala")
    e.mensaje_de_la_app(sala)
    esperar(lambda: sala in e.supervisor.agentes)
    dormitorio = e.falso.asignar_desde_app("usb-046d-082d", "Dormitorio")
    e.mensaje_de_la_app(dormitorio)
    esperar(lambda: dormitorio in e.supervisor.agentes)
    # One pipeline per camera: its own landmarker fed increasing timestamps, in its own thread.
    esperar(lambda: all(len(g.instantes) > 10 for g in Grabadora.creadas))
    assert len(Grabadora.creadas) == 2
    for grabadora in Grabadora.creadas:
        assert grabadora.instantes == sorted(set(grabadora.instantes))
        assert len(grabadora.hilos) == 1
    assert Grabadora.creadas[0].hilos == Grabadora.creadas[1].hilos  # both named «captura»…
    esperar(lambda: all(f > 0 for f in e.supervisor.fps().values()))
    estado = e.coordinador.estado()
    assert estado.agente is not None
    assert [c.nombre_habitacion for c in estado.agente.entradas.camaras] == ["Sala", "Dormitorio"]

    def cuidando() -> bool:
        agente = e.coordinador.estado().agente
        return agente is not None and agente.situacion is Situacion.CUIDANDO

    esperar(cuidando)
    final = e.coordinador.estado().agente
    assert final is not None
    assert final.aviso.titulo_html == "Te Tengo está cuidando 2 habitaciones"
    # «Dejar de usar» in the app: it stops at once and its room is free.
    e.falso.dejar_de_usar_desde_app(sala)
    e.mensaje_de_la_app(sala)
    assert sala not in e.supervisor.agentes
    assert dormitorio in e.supervisor.agentes


def test_la_camara_no_se_confunde_al_conectar_otra(e: Escenario) -> None:
    sala = e.falso.asignar_desde_app("usb-046d-082d", "Sala")
    e.mensaje_de_la_app(sala)
    esperar(lambda: sala in e.supervisor.agentes)
    esperar(lambda: e.webcams.abiertas)
    # Another webcam is plugged in first: indexes change, the OS id of the room does not.
    e.webcams.enchufadas.insert(0, Dispositivo("usb-1908-2311", "USB2.0 PC Camera", 0, 1200))
    e.webcams.enchufadas[1] = Dispositivo("usb-0c45-6366", "Webcam USB HD", 1, 1200)
    e.webcams.enchufadas[2] = Dispositivo("usb-046d-082d", "Logitech C920", 2, 1200)
    assert e.supervisor.buscar_de_nuevo()
    assert set(e.webcams.abiertas) == {"usb-046d-082d"}
    assert e.supervisor.agentes[sala].ajustes.dispositivo_id == "usb-046d-082d"
    nueva = next(
        d for d in e.coordinador.estado().a_json()["devices"] if d["uid"] == "usb-1908-2311"
    )
    assert (nueva["new"], nueva["room"]) == (True, None)  # «Nueva · Sin usar» (CA-29.4)


def test_tras_reconectar_reconcilia_lo_que_cambio(e: Escenario) -> None:
    sala = e.falso.asignar_desde_app("usb-0c45-6366", "Sala")
    e.supervisor.sincronizar()  # missed while offline: GET …/camaras
    assert sala in e.supervisor.agentes
    e.falso.dejar_de_usar_desde_app(sala)
    e.supervisor.sincronizar()
    assert sala not in e.supervisor.agentes


def test_una_camara_retirada_responde_401_y_se_detiene(e: Escenario) -> None:
    sala = e.falso.asignar_desde_app("usb-0c45-6366", "Sala")
    e.supervisor.sincronizar()
    agente = e.supervisor.agentes[sala]
    e.falso.dejar_de_usar_desde_app(sala)  # its token answers 401 PC_DESVINCULADA now
    agente.reintentar_ahora()  # its heartbeat hears it: only the camera left, not the PC
    esperar(lambda: sala not in e.supervisor.agentes)
    assert e.coordinador.estado().pantalla is Pantalla.PRINCIPAL


def test_los_tokens_de_las_camaras_se_renuevan_tras_los_de_la_pc(e: Escenario) -> None:
    sala = e.falso.asignar_desde_app("usb-0c45-6366", "Sala")
    e.supervisor.sincronizar()
    token = e.supervisor._tokens[sala].token()
    pc = e.coordinador.pc
    assert pc is not None
    pc.sesion.renovar_token(pc.sesion.token_vigente())
    esperar(lambda: e.supervisor._tokens[sala].token() != token)


def test_elegir_aqui_con_las_reglas_de_la_app(e: Escenario) -> None:
    e.falso.otra_pc_ambientes["Cocina"] = "Cocina-Rosa"
    ambientes = e.coordinador.ambientes()
    assert {
        "id": "otra-Cocina",
        "nombre": "Cocina",
        "camaras": [{"id": "x", "pc": "Cocina-Rosa", "estaPc": False}],
    } in ambientes
    ok = e.coordinador.usar_aqui("usb-0c45-6366", None, "Sala")
    assert ok == {"ok": True, "codigo": None, "ambiente": None, "pc": None}
    esperar(lambda: e.supervisor.agentes)
    camara_id = next(iter(e.supervisor.agentes))
    assert e.supervisor.agentes[camara_id].ajustes.elegida_desde == "pc"
    sala = next(d for d in e.coordinador.estado().a_json()["devices"] if d["room"] == "Sala")
    assert sala["by"] == "pc"  # «Elegida desde esta PC»
    ocupada = e.coordinador.usar_aqui("usb-046d-082d", None, "Sala")
    assert ocupada == {
        "ok": False,
        "codigo": "AMBIENTE_OCUPADO",
        "ambiente": "Sala",
        "pc": e.falso.nombre_pc,
    }
    otra_pc = e.coordinador.usar_aqui("usb-046d-082d", None, "cocina")
    assert (otra_pc["codigo"], otra_pc["pc"]) == ("AMBIENTE_OCUPADO", "Cocina-Rosa")
    assert (
        e.coordinador.usar_aqui("usb-046d-082d", None, "Baño")["codigo"] == "AMBIENTE_NO_PERMITIDO"
    )
    assert e.coordinador.usar_aqui("usb-046d-082d", None, " ")["codigo"] == "AMBIENTE_NOMBRE_VACIO"
    assert e.coordinador.dejar_de_usar(camara_id) == {"ok": True, "codigo": None}
    assert e.supervisor.agentes == {}


def test_vista_previa_de_una_webcam_sin_usar_pedida_desde_la_app(e: Escenario) -> None:
    publicados = Publicados()
    e.supervisor._abrir_publicador = publicados.abrir
    e.supervisor.previa_remota(
        "usb-046d-082d", True, "rtsp://m/camaras/c-2", "agente", "clave", ModoVista.VIDEO
    )
    assert e.supervisor.mirando == {"usb-046d-082d"}
    dispositivo = next(
        d for d in e.coordinador.estado().a_json()["devices"] if d["uid"] == "usb-046d-082d"
    )
    assert dispositivo["peek"] is True  # «Un familiar está viendo esta cámara para elegirla»
    esperar(lambda: publicados.urls)
    assert publicados.urls[0].startswith("rtsp://agente:clave@m/")
    e.supervisor.previa_remota("usb-046d-082d", False)
    assert e.supervisor.mirando == set()


def test_vista_previa_local_solo_con_consentimiento(e: Escenario) -> None:
    esperar(lambda: e.coordinador.pc is not None and e.coordinador.pc.latido.pc is not None)
    assert e.coordinador.vista_previa_jpeg("usb-046d-082d") is None  # starts the reader
    esperar(lambda: e.coordinador.vista_previa_jpeg("usb-046d-082d") is not None)
    e.falso.consentimiento_vigente = False
    assert e.coordinador.pc is not None
    e.coordinador.pc.reintentar_ahora()
    assert e.coordinador.vista_previa_jpeg("usb-0c45-6366") is None
    assert e.coordinador.vista_previa_jpeg("desconocida") is None


def test_quitada_desde_la_app_detiene_todas_las_camaras(e: Escenario) -> None:
    sala = e.falso.asignar_desde_app("usb-0c45-6366", "Sala")
    e.supervisor.sincronizar()
    agente = e.supervisor.agentes[sala]
    e.falso.quitar_pc()
    assert e.coordinador.pc is not None
    e.coordinador.pc.sesion.desvincular("desvincular")
    assert not agente._permitida()  # at once (CA-31.1)
    esperar(lambda: e.coordinador.estado().pantalla is Pantalla.QUITADA)


def test_imagenes_reales_no_se_guardan(e: Escenario) -> None:
    np.zeros(1)  # numpy imported for FuenteFalsa frames
    sala = e.falso.asignar_desde_app("usb-0c45-6366", "Sala")
    e.supervisor.sincronizar()
    esperar(lambda: len(Grabadora.creadas[0].instantes) > 5)
    datos = Path(e.coordinador._directorio) / "camaras" / sala
    assert not any(p.suffix in (".jpg", ".png", ".mp4") for p in datos.rglob("*"))
