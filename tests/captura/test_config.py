from datetime import date
from pathlib import Path

import pytest

from te_tengo_captura import config
from te_tengo_captura.config import ConfiguracionInvalidaError, cargar

EJEMPLO = Path(__file__).resolve().parents[2] / "config.ejemplo.toml"

MINIMO = """
api_url = "https://api.tetengo.test/"
credencial_instalacion = "secreto-123"
instalada_el = 2026-09-22

[webcam]
indice = 1
nombre = "Webcam USB HD (1080p)"
especificacion = "USB · 1920 × 1080"

[vivienda]
nombre_adulto_mayor = "Rosa Huamán"
direccion = "Jr. Los Pinos 482, San Miguel, Lima"

[camara]
nombre_habitacion = "Sala"
"""


def escribir(tmp_path: Path, texto: str) -> Path:
    ruta = tmp_path / "config.toml"
    ruta.write_text(texto, encoding="utf-8")
    return ruta


def test_lee_todos_los_campos(tmp_path: Path) -> None:
    c = cargar(escribir(tmp_path, MINIMO))
    assert c.api_url == "https://api.tetengo.test"
    assert c.credencial_instalacion.get_secret_value() == "secreto-123"
    assert c.instalada_el == date(2026, 9, 22)
    assert (c.webcam.indice, c.webcam.nombre) == (1, "Webcam USB HD (1080p)")
    assert c.webcam.especificacion == "USB · 1920 × 1080"
    assert c.vivienda.nombre_adulto_mayor == "Rosa Huamán"
    assert c.vivienda.direccion == "Jr. Los Pinos 482, San Miguel, Lima"
    assert c.camara.nombre_habitacion == "Sala"


def test_sin_clasificacion_usa_los_valores_calibrados(tmp_path: Path) -> None:
    umbrales = cargar(escribir(tmp_path, MINIMO)).clasificacion
    assert umbrales.velocidad_descenso_min == 0.01  # docs/validation.md
    assert umbrales.calibrado
    assert umbrales.angulo_linea_central_max_grados == 45.0
    assert umbrales.confirmacion_suelo_s == 30.0


def test_clasificacion_sobrescribe_solo_lo_indicado(tmp_path: Path) -> None:
    texto = MINIMO + "\n[clasificacion]\nconfirmacion_suelo_s = 20\n"
    umbrales = cargar(escribir(tmp_path, texto)).clasificacion
    assert umbrales.confirmacion_suelo_s == 20.0
    assert umbrales.velocidad_descenso_min == 0.01


def test_el_ejemplo_del_repositorio_es_valido() -> None:
    c = cargar(EJEMPLO)
    assert c.camara.nombre_habitacion == "Sala"
    assert c.clasificacion.calibrado


@pytest.mark.parametrize(
    ("quitar", "campo"),
    [
        ('api_url = "https://api.tetengo.test/"\n', "api_url"),
        ('credencial_instalacion = "secreto-123"\n', "credencial_instalacion"),
        ("indice = 1\n", "webcam.indice"),
        ('nombre_habitacion = "Sala"\n', "camara.nombre_habitacion"),
        ('direccion = "Jr. Los Pinos 482, San Miguel, Lima"\n', "vivienda.direccion"),
        ("instalada_el = 2026-09-22\n", "instalada_el"),
    ],
)
def test_campo_faltante_se_nombra_en_espanol(tmp_path: Path, quitar: str, campo: str) -> None:
    with pytest.raises(ConfiguracionInvalidaError, match=f"Falta el campo «{campo}»"):
        cargar(escribir(tmp_path, MINIMO.replace(quitar, "")))


def test_valor_invalido_no_muestra_la_credencial(tmp_path: Path) -> None:
    texto = MINIMO.replace('"https://api.tetengo.test/"', '"ftp://x"').replace(
        "indice = 1", 'indice = "secreto-123"'
    )
    with pytest.raises(ConfiguracionInvalidaError) as error:
        cargar(escribir(tmp_path, texto))
    mensaje = str(error.value)
    assert "«api_url» no es válido" in mensaje
    assert "«webcam.indice» no es válido" in mensaje
    assert "secreto-123" not in mensaje


def test_credencial_vacia_no_es_valida(tmp_path: Path) -> None:
    texto = MINIMO.replace('"secreto-123"', '"  "')
    with pytest.raises(ConfiguracionInvalidaError, match="credencial_instalacion"):
        cargar(escribir(tmp_path, texto))


def test_campo_desconocido(tmp_path: Path) -> None:
    with pytest.raises(ConfiguracionInvalidaError, match="«otro» no existe"):
        cargar(escribir(tmp_path, "otro = 1\n" + MINIMO))


def test_archivo_inexistente(tmp_path: Path) -> None:
    with pytest.raises(ConfiguracionInvalidaError, match="No se encontró"):
        cargar(tmp_path / "no-existe.toml")


def test_toml_mal_formado(tmp_path: Path) -> None:
    with pytest.raises(ConfiguracionInvalidaError, match="No se pudo leer"):
        cargar(escribir(tmp_path, "api_url = "))


def test_ruta_predeterminada_en_el_directorio_de_la_plataforma() -> None:
    ruta = config.ruta_predeterminada()
    assert ruta.name == "config.toml"
    assert ruta.parent.name == "TeTengoCaptura"


def test_la_credencial_no_aparece_en_repr(tmp_path: Path) -> None:
    assert "secreto-123" not in repr(cargar(escribir(tmp_path, MINIMO)))
