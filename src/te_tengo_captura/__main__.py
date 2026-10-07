"""Entry point: ``uv run te-tengo-captura``."""

import argparse
from collections.abc import Sequence

from te_tengo_captura import __version__


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="te-tengo-captura", description="Te Tengo Captura")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.parse_args(argv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
