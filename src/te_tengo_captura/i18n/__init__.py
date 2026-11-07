"""The language of the window, the tray and the system notices: Spanish (default) or English.

A small, dependency-free catalog: ``es.py`` and ``en.py`` map the same ids to texts with
``{name}`` placeholders, and ``t(id, **valores)`` formats one in the current language. The web
page has its own catalog (``ui/web/textos.js``) and gets the language in the state (``idioma``).

The language is chosen once at start (``elegir``): the window's own choice (``ventana.json``,
«Idioma» in «Avanzado»), else ``[interfaz] idioma`` of the configuration file, else the system's
language (English when it starts with ``en``, Spanish otherwise). Only what people read changes:
logs, the activity sent to the API and every other payload stay as they were.
"""

import locale
import logging
import os
import sys
from collections.abc import Callable, Mapping
from datetime import date

from te_tengo_captura.i18n import en, es

logger = logging.getLogger(__name__)

ES, EN = "es", "en"
IDIOMAS = (ES, EN)
PREDETERMINADO = ES
CATALOGOS: dict[str, Mapping[str, str]] = {ES: es.TEXTOS, EN: en.TEXTOS}

# A text to show: already written, or written on demand in a language (``frase``).
Texto = str | Callable[[str], str]

_actual = PREDETERMINADO


def idioma() -> str:
    """The current language: ``"es"`` or ``"en"``."""
    return _actual


def establecer(valor: str | None) -> str:
    """Sets the current language (anything not supported is Spanish); returns it."""
    global _actual
    _actual = normalizar(valor) or PREDETERMINADO
    return _actual


def normalizar(valor: str | None) -> str | None:
    """``"en_US.UTF-8"``, ``"en-GB"`` or ``"EN"`` → ``"en"``; ``"es"``, ``"es-PE"`` → ``"es"``;
    another language → ``None``."""
    if not valor:
        return None
    codigo = valor.strip().lower().replace("-", "_").split("_")[0].split(".")[0]
    return codigo if codigo in IDIOMAS else None


def traducir(idioma_: str, clave: str, **valores: object) -> str:
    """The text ``clave`` in ``idioma_`` (Spanish if missing there; the id if missing in both)."""
    texto = CATALOGOS.get(idioma_, CATALOGOS[ES]).get(clave)
    if texto is None:
        texto = CATALOGOS[ES].get(clave, clave)
    return texto.format(**valores) if valores else texto


def t(clave: str, **valores: object) -> str:
    """The text ``clave`` in the current language."""
    return traducir(_actual, clave, **valores)


def frase(clave: str, **valores: object) -> Callable[[str], str]:
    """``clave`` written later in any language, e.g. Spanish for the log file and the current
    language for the window."""
    return lambda idioma_: traducir(idioma_, clave, **valores)


def escribir(texto: Texto, idioma_: str) -> str:
    return texto if isinstance(texto, str) else texto(idioma_)


# ------------------------------------------------------------------ dates and numbers


def fecha(dia: date, idioma_: str | None = None) -> str:
    """«23/09/2026» in Spanish, «Sep 23, 2026» in English."""
    if (idioma_ or _actual) == EN:
        return f"{_mes(dia.month)} {dia.day}, {dia.year}"
    return f"{dia:%d/%m/%Y}"


def fecha_corta(dia: date, idioma_: str | None = None) -> str:
    """«23/09» in Spanish, «Sep 23» in English."""
    if (idioma_ or _actual) == EN:
        return f"{_mes(dia.month)} {dia.day}"
    return f"{dia:%d/%m}"


def decimal(valor: float, decimales: int, idioma_: str | None = None) -> str:
    """«1,5» in Spanish, «1.5» in English."""
    texto = f"{valor:.{decimales}f}"
    return texto if (idioma_ or _actual) == EN else texto.replace(".", ",")


def _mes(numero: int) -> str:
    return traducir(EN, f"mes.{numero}")


# ------------------------------------------------------------------ choosing the language


def elegir(
    eleccion: str | None = None,
    configurado: str | None = None,
    sistema: Callable[[], str | None] | None = None,
) -> str:
    """The window's choice, else the configuration file's, else the system's language."""
    for valor in (eleccion, configurado):
        if elegido := normalizar(valor):
            return elegido
    return de_la_configuracion_regional((sistema or idioma_del_sistema)())


def de_la_configuracion_regional(codigo: str | None) -> str:
    """English when the system's locale starts with ``en``; Spanish otherwise."""
    return EN if codigo and codigo.strip().lower().startswith("en") else ES


def idioma_del_sistema(
    entorno: Mapping[str, str] | None = None, plataforma: str = sys.platform
) -> str | None:
    """The user's interface language as a locale code (``en_US``, ``es-PE``), or ``None``."""
    try:
        if plataforma == "win32" and (codigo := _idioma_windows()):
            return codigo
        if plataforma == "darwin" and (codigo := _idioma_mac()):
            return codigo
    except Exception:  # the language is a nicety: never fail the start for it
        logger.debug("No se pudo leer el idioma del sistema", exc_info=True)
    entorno = os.environ if entorno is None else entorno
    for variable in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
        valor = entorno.get(variable, "").split(":")[0]
        if valor and valor not in ("C", "POSIX", "C.UTF-8"):
            return valor
    try:
        return locale.getlocale()[0]
    except ValueError:
        return None


def _idioma_windows() -> str | None:  # pragma: no cover - Windows only
    import ctypes

    lcid = ctypes.windll.kernel32.GetUserDefaultUILanguage()  # type: ignore[attr-defined]
    return locale.windows_locale.get(int(lcid))


def _idioma_mac() -> str | None:  # pragma: no cover - macOS only
    from Foundation import NSLocale  # type: ignore[import-not-found,unused-ignore]

    preferidos = NSLocale.preferredLanguages()
    return str(preferidos[0]) if preferidos else None
