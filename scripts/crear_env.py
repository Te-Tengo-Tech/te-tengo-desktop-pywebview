"""Creates .env from .env.example with random tokens for local development.

It does not overwrite an existing .env. The generated tokens only work on your machine.
"""

import secrets
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PLANTILLA, DESTINO = RAIZ / ".env.example", RAIZ / ".env"
GENERAR = ("TT_INGESTA_TOKEN", "TT_BACKEND_TOKEN")


def main() -> int:
    if DESTINO.exists():
        print(f"{DESTINO.name} ya existe; no se modifica. Bórralo si quieres regenerarlo.")
        return 0
    lineas = []
    for linea in PLANTILLA.read_text(encoding="utf-8").splitlines():
        clave = linea.split("=", 1)[0]
        lineas.append(f"{clave}={secrets.token_urlsafe(32)}" if clave in GENERAR else linea)
    DESTINO.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print(f"Creado {DESTINO.name} con tokens locales para {', '.join(GENERAR)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
