from te_tengo_captura import rutas


def test_directorios_de_la_plataforma_usan_el_nombre_de_la_app() -> None:
    assert "TeTengoCaptura" in rutas.datos().parts
    assert "TeTengoCaptura" in rutas.logs().parts
