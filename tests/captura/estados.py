"""Builders of window states for the tests: the prototype's example household and PC."""

from dataclasses import replace
from datetime import tzinfo
from typing import Any

from te_tengo_captura.estado import (
    CamaraEntradas,
    DatosPc,
    Entradas,
    EstadoAgente,
    Hogar,
    Webcam,
    derivar,
)

HOGAR = Hogar("Rosa Huamán", "Jr. Los Pinos 482, San Miguel, Lima")
PC = DatosPc("Sala-Rosa", "Windows 11 Home", "Te Tengo Captura 0.5.0", instalada_el="22/09/2026")
DISPOSITIVOS = {
    "Sala": "Webcam USB HD",
    "Dormitorio": "Logitech C920",
    "Pasillo": "USB2.0 PC Camera",
}


def camara(habitacion: str = "Sala", **cambios: Any) -> CamaraEntradas:
    base = CamaraEntradas(
        clave=habitacion.lower(),
        nombre_habitacion=habitacion,
        dispositivo=DISPOSITIVOS.get(habitacion, "Webcam USB HD"),
        webcam_conectada=True,
    )
    return replace(base, **cambios)


def webcam_de(c: CamaraEntradas) -> Webcam:
    return Webcam(
        clave=c.clave,
        nombre=c.dispositivo,
        dispositivo_id=None,
        nombre_habitacion=c.nombre_habitacion,
        conectada=c.webcam_conectada,
    )


def entradas(*camaras: CamaraEntradas, **cambios: Any) -> Entradas:
    camaras = camaras or (camara(),)
    base = Entradas(
        camaras=camaras,
        en_linea=True,
        consentimiento=True,
        segundos_para_reintento=8,
        webcams=tuple(webcam_de(c) for c in camaras),
    )
    return replace(base, **cambios)


def estado(
    *camaras: CamaraEntradas, zona: tzinfo | None = None, pc: DatosPc = PC, **cambios: Any
) -> EstadoAgente:
    return derivar(entradas(*camaras, **cambios), HOGAR, pc, "0.5.0", zona)
