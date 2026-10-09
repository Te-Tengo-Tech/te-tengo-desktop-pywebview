#!/usr/bin/env bash
# Prints the version of Te Tengo Captura after checking that `version` in pyproject.toml and
# `__version__` in src/te_tengo_captura/__init__.py match and are <major>.<minor>.<patch>
# (docs/RELEASES.md). Used by release.yml and produccion.yml from the repository root.
set -euo pipefail

version=$(sed -n 's/^__version__ = "\(.*\)"/\1/p' src/te_tengo_captura/__init__.py)
proyecto=$(sed -n 's/^version = "\(.*\)"/\1/p' pyproject.toml | head -n1)
if [[ "$version" != "$proyecto" ]]; then
  echo "::error title=Version mismatch::__version__ $version (src/te_tengo_captura/__init__.py) does not match pyproject.toml version $proyecto" >&2
  exit 1
fi
if [[ ! "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "::error title=Unexpected version::'$version' is not <major>.<minor>.<patch>." >&2
  exit 1
fi
echo "$version"
