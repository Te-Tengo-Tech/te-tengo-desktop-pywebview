"""«Restablecer esta PC» and the uninstaller's ``--restablecer`` (US-31): nothing stays."""

import json
from pathlib import Path

import pytest

from te_tengo_captura import restablecer
from te_tengo_captura.backend.falso import URL_API, BackendFalso
from te_tengo_captura.vinculacion.credenciales import (
    AlmacenCredenciales,
    CredencialesPc,
    LlaveroEnMemoria,
    RevocacionPendiente,
)
from te_tengo_captura.vinculacion.oauth import ClienteOAuth


class Equipo:
    """A used PC: its credential store, data folder, configuration and logs."""

    def __init__(self, tmp_path: Path) -> None:
        self.falso = BackendFalso()
        self.llavero = LlaveroEnMemoria()
        self.almacen = AlmacenCredenciales(self.llavero)
        self.datos = tmp_path / "datos"
        self.config = tmp_path / "config" / "config.toml"
        self.logs = tmp_path / "logs"
        self.autoinicio: list[bool] = []
        for ruta in (
            self.datos / "envios.sqlite3",
            self.datos / "clips" / "e1.mp4",
            self.datos / "Datos" / "movimientos" / "c1" / "x.parquet.ttg",
            self.datos / "actividad.jsonl",
            self.datos / "instancia.lock",
            self.logs / "te-tengo-captura.log",
            self.config,
        ):
            ruta.parent.mkdir(parents=True, exist_ok=True)
            ruta.write_text("x")
        self.llavero.set_password("TeTengoCaptura", "clave-datos", "Y2xhdmU=")

    def vincular(self) -> None:
        oauth = ClienteOAuth(URL_API, self.falso.transporte())
        codigo = oauth.pedir_codigo("PC", "x", "y")
        self.falso.aprobar()
        tokens = oauth.canjear(codigo.device_code)
        self.almacen.guardar(
            CredencialesPc(tokens.access_token, 0.0, tokens.refresh_token, "pc", "hogar")
        )

    def ejecutar(self, motivo: restablecer.Motivo = "desinstalada") -> restablecer.Resultado:
        return restablecer.ejecutar(
            URL_API,
            self.almacen,
            self.datos,
            self.config,
            self.logs,
            motivo,
            transporte=self.falso.transporte(),
            quitar_autoinicio=self._quitar_autoinicio,
        )

    def _quitar_autoinicio(self) -> bool:
        self.autoinicio.append(True)
        return True

    def nada_queda(self) -> None:
        assert self.almacen.leer() is None
        assert self.almacen.leer_revocacion() is None
        assert self.llavero.get_password("TeTengoCaptura", "clave-datos") is None
        assert sorted(p.name for p in self.datos.iterdir()) == ["instancia.lock"]
        assert not self.config.exists()
        assert not self.config.parent.exists()
        assert not self.logs.exists()
        assert self.autoinicio == [True]


@pytest.fixture
def equipo(tmp_path: Path) -> Equipo:
    return Equipo(tmp_path)


def test_desinstalar_una_pc_vinculada_avisa_a_la_api_y_borra_todo(equipo: Equipo) -> None:
    equipo.vincular()
    resultado = equipo.ejecutar("desinstalada")
    assert resultado == restablecer.Resultado(vinculada=True, avisada=True)
    assert equipo.falso.desvinculaciones == [
        {"via": "revocacion", "datos": "true", "motivo": "desinstalada"}
    ]
    assert equipo.falso.pc_quitada  # the family's app removes it
    equipo.nada_queda()


def test_sin_internet_igual_borra_todo(equipo: Equipo) -> None:
    equipo.vincular()
    equipo.falso.sin_conexion = True
    assert equipo.ejecutar() == restablecer.Resultado(vinculada=True, avisada=False)
    assert equipo.falso.desvinculaciones == []  # the app shows it «Sin conexión»
    equipo.nada_queda()


def test_una_desvinculacion_pendiente_sale_con_el_motivo(equipo: Equipo) -> None:
    equipo.vincular()
    refresh = equipo.almacen.leer()
    assert refresh is not None
    equipo.almacen.borrar()
    equipo.almacen.guardar_revocacion(RevocacionPendiente(refresh.refresh_token, False))
    assert equipo.ejecutar("restablecida") == restablecer.Resultado(vinculada=True, avisada=True)
    assert equipo.falso.desvinculaciones == [
        {"via": "revocacion", "datos": None, "motivo": "restablecida"}
    ]
    equipo.nada_queda()


def test_sin_vincular_solo_borra(equipo: Equipo) -> None:
    assert equipo.ejecutar() == restablecer.Resultado(vinculada=False, avisada=False)
    assert equipo.falso.solicitudes == []
    equipo.nada_queda()


def test_la_carpeta_de_datos_movida_tambien_se_borra(equipo: Equipo, tmp_path: Path) -> None:
    movida = tmp_path / "D" / "TeTengo" / "Datos"
    (movida / "video").mkdir(parents=True)
    (movida / "video" / "v.ttg").write_text("x")
    (equipo.datos / "almacenamiento.json").write_text(json.dumps({"carpeta": str(movida)}))
    assert restablecer.carpeta_movida(equipo.datos) == movida
    equipo.ejecutar()
    assert not movida.exists()
    equipo.nada_queda()


def test_vaciar_carpeta_conserva_el_candado_y_tolera_que_no_exista(tmp_path: Path) -> None:
    restablecer.vaciar_carpeta(tmp_path / "no-existe")
    (tmp_path / "instancia.lock").write_text("")
    (tmp_path / "a" / "b").mkdir(parents=True)
    (tmp_path / "c.txt").write_text("x")
    restablecer.vaciar_carpeta(tmp_path)
    assert [p.name for p in tmp_path.iterdir()] == ["instancia.lock"]
    assert restablecer.carpeta_movida(tmp_path) is None
