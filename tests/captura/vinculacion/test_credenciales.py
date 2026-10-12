import json
import uuid

import pytest

from te_tengo_captura.vinculacion.credenciales import (
    SERVICIO,
    AlmacenCredenciales,
    AlmacenNoDisponibleError,
    CredencialesPc,
    LlaveroEnMemoria,
    RevocacionPendiente,
)

CREDENCIALES = CredencialesPc("acceso-1", 1_800_000_000.0, "renovacion-1", "pc-1", "hogar-1")


def test_guarda_lee_y_borra_en_el_almacen_del_sistema() -> None:
    llavero = LlaveroEnMemoria()
    almacen = AlmacenCredenciales(llavero)
    assert almacen.leer() is None
    almacen.guardar(CREDENCIALES)
    assert almacen.leer() == CREDENCIALES
    # Two small entries under the app's service: never one big blob (Windows: 2560 bytes).
    renovacion = json.loads(llavero.get_password(SERVICIO, "pc-renovacion") or "")
    acceso = json.loads(llavero.get_password(SERVICIO, "pc-acceso") or "")
    assert renovacion == {"refresh_token": "renovacion-1", "pc_id": "pc-1", "hogar_id": "hogar-1"}
    assert acceso == {"access_token": "acceso-1", "expira_en": 1_800_000_000.0}
    almacen.borrar()
    assert almacen.leer() is None
    almacen.borrar()  # nothing to delete: no error


def test_sin_token_de_acceso_aun_se_puede_renovar() -> None:
    llavero = LlaveroEnMemoria()
    almacen = AlmacenCredenciales(llavero)
    almacen.guardar(CREDENCIALES)
    llavero.delete_password(SERVICIO, "pc-acceso")
    leidas = almacen.leer()
    assert leidas is not None
    assert (leidas.access_token, leidas.expira_en, leidas.refresh_token) == (
        "",
        0.0,
        "renovacion-1",
    )


def test_valores_ilegibles_se_ignoran() -> None:
    llavero = LlaveroEnMemoria()
    llavero.set_password(SERVICIO, "pc-renovacion", "{no es json")
    assert AlmacenCredenciales(llavero).leer() is None
    llavero.set_password(SERVICIO, "pc-renovacion", json.dumps({"pc_id": "x"}))
    assert AlmacenCredenciales(llavero).leer() is None


def test_revocacion_pendiente() -> None:
    almacen = AlmacenCredenciales(LlaveroEnMemoria())
    assert almacen.leer_revocacion() is None
    almacen.guardar_revocacion(RevocacionPendiente("renovacion-1", True))
    pendiente = almacen.leer_revocacion()
    assert pendiente == RevocacionPendiente("renovacion-1", True)
    assert "renovacion-1" not in repr(pendiente)
    almacen.borrar_revocacion()
    assert almacen.leer_revocacion() is None


class LlaveroRoto:
    def get_password(self, service_name: str, username: str) -> str | None:
        raise RuntimeError("No recommended backend was available")

    def set_password(self, service_name: str, username: str, password: str) -> None:
        raise RuntimeError("No recommended backend was available")

    def delete_password(self, service_name: str, username: str) -> None:
        raise RuntimeError("No recommended backend was available")


def test_almacen_no_disponible() -> None:
    almacen = AlmacenCredenciales(LlaveroRoto())
    with pytest.raises(AlmacenNoDisponibleError):
        almacen.leer()
    with pytest.raises(AlmacenNoDisponibleError):
        almacen.guardar(CREDENCIALES)
    almacen.borrar()  # best effort


def test_id_de_instalacion_se_genera_una_vez_y_sobrevive_a_la_desvinculacion() -> None:
    llavero = LlaveroEnMemoria()
    almacen = AlmacenCredenciales(llavero)
    primero = almacen.id_instalacion()
    assert str(uuid.UUID(primero)) == primero
    almacen.guardar(CREDENCIALES)
    almacen.borrar()  # unlinking deletes the tokens, never the installation id
    assert AlmacenCredenciales(llavero).id_instalacion() == primero


def test_id_de_instalacion_ilegible_se_reemplaza() -> None:
    llavero = LlaveroEnMemoria()
    llavero.set_password(SERVICIO, "pc-instalacion", json.dumps({"id": "no-es-uuid"}))
    nuevo = AlmacenCredenciales(llavero).id_instalacion()
    assert nuevo != "no-es-uuid"
    assert AlmacenCredenciales(llavero).id_instalacion() == nuevo
