#!/usr/bin/env bash
# Uploads one release binary and its .sha256 file to the public R2 bucket of the downloads, then
# checks the public copy: it downloads it from DESCARGAS_BASE_URL and compares the SHA-256 with the
# local file (the smoke check of the staging and produccion stages of release.yml).
#
#   publicar_r2.sh <local file> <key> <content type>
#   e.g. publicar_r2.sh salida/te-tengo-captura.dmg staging/te-tengo-captura.dmg application/x-apple-diskimage
#
# Environment: CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID (read by Wrangler), R2_BUCKET,
# DESCARGAS_BASE_URL and WRANGLER_VERSION. The <local file>.sha256 next to the file is uploaded as
# <key>.sha256 when present.
set -euo pipefail

archivo="$1"
clave="$2"
tipo="$3"
: "${R2_BUCKET:?R2_BUCKET is not set}"
: "${DESCARGAS_BASE_URL:?DESCARGAS_BASE_URL is not set}"
: "${WRANGLER_VERSION:?WRANGLER_VERSION is not set}"

if [[ ! -f "$archivo" ]]; then
  echo "::error title=Missing binary::$archivo is not in the build artifact."
  exit 1
fi
nombre=$(basename "$clave")

npx --yes "wrangler@$WRANGLER_VERSION" r2 object put "$R2_BUCKET/$clave" --remote \
  --file "$archivo" --content-type "$tipo" \
  --cache-control "no-cache" --content-disposition "attachment; filename=\"$nombre\""
if [[ -f "$archivo.sha256" ]]; then
  npx --yes "wrangler@$WRANGLER_VERSION" r2 object put "$R2_BUCKET/$clave.sha256" --remote \
    --file "$archivo.sha256" --content-type "text/plain; charset=utf-8" --cache-control "no-cache"
fi

# Smoke check: the public URL serves exactly the uploaded bytes.
url="${DESCARGAS_BASE_URL%/}/$clave"
descarga=$(mktemp)
trap 'rm -f "$descarga"' EXIT
curl --fail --silent --show-error --location --retry 5 --retry-delay 5 --retry-all-errors \
  --header "Cache-Control: no-cache" --output "$descarga" "$url"
esperado=$(sha256sum "$archivo" | cut -d' ' -f1)
publicado=$(sha256sum "$descarga" | cut -d' ' -f1)
if [[ "$esperado" != "$publicado" ]]; then
  echo "::error title=Smoke check failed::$url has SHA-256 $publicado, expected $esperado."
  exit 1
fi
echo "Published and checked: $url (SHA-256 $esperado)"
echo "- \`$clave\`: $url (SHA-256 \`$esperado\`)" >> "${GITHUB_STEP_SUMMARY:-/dev/null}"
