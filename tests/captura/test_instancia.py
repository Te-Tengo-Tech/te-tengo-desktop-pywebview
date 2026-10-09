import json
import threading
from pathlib import Path

from te_tengo_captura.instancia import Instancia


def test_la_segunda_instancia_muestra_la_ventana_de_la_primera(tmp_path: Path) -> None:
    mostrada = threading.Event()
    primera = Instancia(tmp_path)
    assert primera.adquirir(mostrada.set)
    segunda = Instancia(tmp_path)
    assert not segunda.adquirir(lambda: None)
    assert segunda.avisar()
    assert mostrada.wait(5)
    primera.liberar()


def test_tras_salir_otra_instancia_puede_iniciar(tmp_path: Path) -> None:
    primera = Instancia(tmp_path)
    assert primera.adquirir(lambda: None)
    primera.liberar()
    nueva = Instancia(tmp_path)
    assert nueva.adquirir(lambda: None)
    nueva.liberar()


def test_un_token_equivocado_no_muestra_nada(tmp_path: Path) -> None:
    mostrada = threading.Event()
    primera = Instancia(tmp_path)
    assert primera.adquirir(mostrada.set)
    archivo = tmp_path / "instancia.json"
    datos = json.loads(archivo.read_text(encoding="utf-8"))
    archivo.write_text(json.dumps({**datos, "token": "otro"}), encoding="utf-8")
    assert not Instancia(tmp_path).avisar(espera_s=1)
    assert not mostrada.is_set()
    primera.liberar()


def test_avisar_sin_instancia_en_ejecucion(tmp_path: Path) -> None:
    assert not Instancia(tmp_path).avisar()
