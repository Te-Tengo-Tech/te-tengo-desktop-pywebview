#!/usr/bin/env bash
# Downloads the binaries of a GitHub Release (a candidate vX.Y.Z-rc.N or a final vX.Y.Z) and proves
# they are the stored bytes before anything is published (docs/RELEASES.md):
#   1. every asset listed in SHA256SUMS.txt is present and has that SHA-256;
#   2. SHA256SUMS.txt matches, line for line, the SHA-256 block written in the release notes when
#      the candidate was created.
# It then prepares the copies under the R2 names in <directory>/r2/, each with its .sha256 file:
# te-tengo-captura-setup.exe and te-tengo-captura.dmg (only the binaries the release has).
#
#   descargar_candidata.sh <tag> <directory>
#   e.g. descargar_candidata.sh v0.3.0-rc.2 candidata
#
# Environment: GH_TOKEN and GITHUB_REPOSITORY (set by GitHub Actions).
set -euo pipefail

tag="$1"
destino="$2"
: "${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is not set}"

mkdir -p "$destino"
gh release download "$tag" --repo "$GITHUB_REPOSITORY" --dir "$destino" --clobber
if [[ ! -f "$destino/SHA256SUMS.txt" ]]; then
  echo "::error title=No SHA256SUMS.txt::Release $tag has no SHA256SUMS.txt, so its binaries cannot be verified."
  exit 1
fi

# 1) The files are the ones the checksum file lists.
(cd "$destino" && sha256sum --check --strict SHA256SUMS.txt)

# 2) The checksum file is the one recorded in the notes when the release was created.
gh release view "$tag" --repo "$GITHUB_REPOSITORY" --json body --jq .body \
  | tr -d '\r' | grep -E '^[0-9a-f]{64}  [^ ]+$' | sort > "$destino/notas.sha256" || true
if [[ ! -s "$destino/notas.sha256" ]]; then
  echo "::error title=No SHA-256 in the notes::The notes of $tag do not list the SHA-256 of its binaries."
  exit 1
fi
if ! sort "$destino/SHA256SUMS.txt" | cmp -s - "$destino/notas.sha256"; then
  echo "::error title=Checksums differ::SHA256SUMS.txt of $tag differs from the SHA-256 recorded in its notes; an asset was replaced after the release was created."
  diff <(sort "$destino/SHA256SUMS.txt") "$destino/notas.sha256" || true
  exit 1
fi
rm -f "$destino/notas.sha256"

# 3) Copies under the R2 names (the landing links to these keys).
mkdir -p "$destino/r2"
copiar() {
  local origen="$1" nombre="$2"
  cp "$origen" "$destino/r2/$nombre"
  (cd "$destino/r2" && sha256sum "$nombre" > "$nombre.sha256")
}
shopt -s nullglob
for archivo in "$destino"/te-tengo-captura-*-windows-setup.exe; do copiar "$archivo" te-tengo-captura-setup.exe; done
for archivo in "$destino"/te-tengo-captura-*-macos.dmg; do copiar "$archivo" te-tengo-captura.dmg; done

echo "Verified $tag:"
cat "$destino/SHA256SUMS.txt"
{
  echo "Verified the binaries of \`$tag\` (SHA256SUMS.txt and the notes):"
  echo '```'
  cat "$destino/SHA256SUMS.txt"
  echo '```'
} >> "${GITHUB_STEP_SUMMARY:-/dev/null}"
