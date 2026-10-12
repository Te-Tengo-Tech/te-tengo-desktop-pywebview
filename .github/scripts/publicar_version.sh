#!/usr/bin/env bash
# Publishes the version of one channel for GET /api/versiones (US-43; ADR 0012 of te-tengo-general-api):
# writes versiones/<canal>.json to the public R2 bucket of the downloads, next to the binaries, and
# checks the public copy. The API reads it within 5 minutes; nobody sets versions by hand.
#
#   publicar_version.sh <canal> <version> <url> [<local file>]
#   e.g. publicar_version.sh windows 0.5.0 "$DESCARGAS_BASE_URL/te-tengo-captura-setup.exe" \
#          candidata/r2/te-tengo-captura-setup.exe
#
# <canal>: windows, mac, apk, play, ios or pwa. With <local file> (the verified binary that was just
# uploaded to <url>), the manifest carries its SHA-256 and size, which clients check before
# installing (CA-43.2). The «Qué cambió» notes are the "- " lines of the "## [<version>]" section of
# NOVEDADES.md (short lines in Spanish for the family); none if there is no section.
#
# An empty <url> (a store address that is not configured) or an unset DESCARGAS_BASE_URL skips the
# channel with a notice: the binary is already live, only the notice to the apps is missing.
#
# Environment: CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID (read by Wrangler), R2_BUCKET,
# DESCARGAS_BASE_URL and WRANGLER_VERSION. Set DRY_RUN=1 to only print the manifest (tests).
set -euo pipefail

canal="$1"
version="$2"
url="$3"
archivo="${4:-}"

if [[ -z "$url" ]]; then
  echo "::notice title=No $canal address::The $canal channel has no address (e.g. the variable IOS_TIENDA_URL is not set), so the apps are not told about $version."
  exit 0
fi
if [[ -z "${DESCARGAS_BASE_URL:-}" && "${DRY_RUN:-}" != 1 ]]; then
  echo "::warning title=DESCARGAS_BASE_URL missing::Without the variable DESCARGAS_BASE_URL the $canal version $version is not published for the apps (GET /api/versiones)."
  exit 0
fi

case "$canal" in
  windows | mac | apk | play | ios | pwa) ;;
  *)
    echo "::error title=Unknown channel::'$canal' is not windows, mac, apk, play, ios or pwa."
    exit 1
    ;;
esac
if [[ ! "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "::error title=Unexpected version::'$version' is not <major>.<minor>.<patch>."
  exit 1
fi
if [[ ! "$url" =~ ^https:// ]]; then
  echo "::error title=Not an HTTPS address::The $canal download '$url' must be an https:// address."
  exit 1
fi

sha256=""
tamano=""
if [[ -n "$archivo" ]]; then
  if [[ ! -f "$archivo" ]]; then
    echo "::error title=Missing binary::$archivo does not exist; the $canal manifest is not published."
    exit 1
  fi
  sha256=$(sha256sum "$archivo" | cut -d' ' -f1)
  tamano=$(wc -c < "$archivo" | tr -d ' ')
fi

notas="[]"
if [[ -f NOVEDADES.md ]]; then
  notas=$(awk -v v="$version" '
    index($0, "## [" v "]") == 1 { dentro = 1; next }
    dentro && /^## / { exit }
    dentro && /^- / { sub(/^- /, ""); print }
  ' NOVEDADES.md | jq -R . | jq -s 'map(select(length > 0)) | .[0:10]')
fi

manifiesto=$(mktemp)
descarga=$(mktemp)
trap 'rm -f "$manifiesto" "$descarga"' EXIT
jq -n --arg version "$version" --arg url "$url" --arg sha256 "$sha256" --arg tamano "$tamano" \
  --arg publicadaEn "$(date -u +%Y-%m-%dT%H:%M:%SZ)" --argjson notas "$notas" '
  {version: $version, url: $url}
  + (if $sha256 != "" then {sha256: $sha256, tamanoBytes: ($tamano | tonumber)} else {} end)
  + {publicadaEn: $publicadaEn, notas: $notas}' > "$manifiesto"

if [[ "${DRY_RUN:-}" == 1 ]]; then
  cat "$manifiesto"
  exit 0
fi

: "${R2_BUCKET:?R2_BUCKET is not set}"
: "${DESCARGAS_BASE_URL:?DESCARGAS_BASE_URL is not set}"
: "${WRANGLER_VERSION:?WRANGLER_VERSION is not set}"
clave="versiones/$canal.json"
npx --yes "wrangler@$WRANGLER_VERSION" r2 object put "$R2_BUCKET/$clave" --remote \
  --file "$manifiesto" --content-type "application/json; charset=utf-8" --cache-control "no-cache"

# Smoke check: the public URL serves exactly this manifest.
publica="${DESCARGAS_BASE_URL%/}/$clave"
curl --fail --silent --show-error --location --retry 5 --retry-delay 5 --retry-all-errors \
  --header "Cache-Control: no-cache" --output "$descarga" "$publica"
if ! cmp -s "$manifiesto" "$descarga"; then
  echo "::error title=Smoke check failed::$publica does not serve the manifest just uploaded."
  exit 1
fi
echo "Published the $canal version: $publica"
cat "$manifiesto"
{
  echo "- Version for the apps (\`GET /api/versiones\`, within 5 min): \`$clave\` → $canal $version"
} >> "${GITHUB_STEP_SUMMARY:-/dev/null}"
