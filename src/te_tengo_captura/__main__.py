"""Entry point: ``uv run te-tengo-captura``."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from te_tengo_captura import __version__, config


def _argumentos(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="te-tengo-captura", description="Te Tengo Captura")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--config",
        type=Path,
        help=f"installation file (default: {config.ruta_predeterminada()})",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _argumentos(argv)
    try:
        config.cargar(args.config)
    except config.ConfiguracionInvalidaError as error:
        print(error, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
