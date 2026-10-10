#!/usr/bin/env bash
# Finds the approved release candidate of Te Tengo Captura for a git tree (docs/RELEASES.md): the newest
# published pre-release vX.Y.Z-rc.N whose notes (written by release.yml) record `- Tree: <tree>` and
# `- Staging: passed` or `- Staging: off` (staging switched off when it was built), and whose tag points
# at a commit with that same tree. Used by produccion.yml (the tree of main) and release-gate.yml (the
# tree of the pull request's test merge), so both accept exactly the same candidates.
#
#   buscar_candidata.sh <version x.y.z> <git tree sha>
#
# Exit 0 when found, with tag=<vX.Y.Z-rc.N> and staging=<passed|off> written to $GITHUB_OUTPUT; exit 1
# with a ::error and the list of candidates (in the run summary) otherwise.
# Environment: GH_TOKEN, GITHUB_REPOSITORY, GITHUB_OUTPUT, GITHUB_STEP_SUMMARY.
set -euo pipefail

version=${1:?usage: buscar_candidata.sh <version> <tree>}
arbol=${2:?usage: buscar_candidata.sh <version> <tree>}
: "${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is not set}"
repo=$GITHUB_REPOSITORY
salida=${GITHUB_OUTPUT:-/dev/null}
resumen=${GITHUB_STEP_SUMMARY:-/dev/null}
if [[ ! "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "::error title=Unexpected version::'$version' is not <major>.<minor>.<patch>."
  exit 1
fi

# The published (not draft) pre-releases of this version, newest rc first. The list is read first, so
# a failing API call stops the script instead of looking like "no candidate".
prereleases=$(gh api --paginate "repos/$repo/releases?per_page=100" \
  --jq '.[] | select(.prerelease and (.draft | not)) | .tag_name')
mapfile -t candidatas < <(
  { grep -E "^v${version//./\\.}-rc\.[0-9]+$" <<< "$prereleases" || true; } | sort -t. -k4,4nr
)
revisadas=()
sin_staging=()
for tag in "${candidatas[@]}"; do
  cuerpo=$(gh api "repos/$repo/releases/tags/$tag" --jq .body | tr -d '\r')
  arbol_notas=$(sed -n 's/^- Tree: \([0-9a-f]\{40,\}\)$/\1/p' <<< "$cuerpo" | head -n1)
  staging=$(sed -n 's/^- Staging: \([a-z]*\).*/\1/p' <<< "$cuerpo" | head -n1)
  revisadas+=("\`$tag\`: tree \`${arbol_notas:0:12}\`, staging ${staging:-not recorded}")
  [ "$arbol_notas" = "$arbol" ] || continue
  # The record is in the notes; the tag itself must point at a commit with that same tree.
  arbol_tag=$(gh api "repos/$repo/commits/$tag" --jq .commit.tree.sha)
  if [ "$arbol_tag" != "$arbol" ]; then
    echo "::warning title=Candidate record mismatch::$tag records the tree ${arbol:0:12}, but its tag points at a commit with the tree ${arbol_tag:0:12}; ignored."
    continue
  fi
  if [ "$staging" != passed ] && [ "$staging" != off ]; then
    sin_staging+=("$tag (Staging: ${staging:-not recorded})")
    continue # built from this tree but not through staging (pending, or its staging failed)
  fi
  {
    echo "tag=$tag"
    echo "staging=$staging"
  } >> "$salida"
  echo "- Candidate [\`$tag\`](${GITHUB_SERVER_URL:-https://github.com}/$repo/releases/tag/$tag) (staging $staging) has the tree \`${arbol:0:12}\`" >> "$resumen"
  echo "$tag (staging $staging) has the tree $arbol"
  exit 0
done

if [ "${#sin_staging[@]}" -gt 0 ]; then
  echo "::error title=Candidate not approved in staging::${sin_staging[*]} has the tree ${arbol:0:12} but did not pass staging. Approve its staging job in the Release run (or let a newer candidate pass it), then run this again."
else
  echo "::error title=No tested candidate for this tree::No pre-release v$version-rc.N has the tree ${arbol:0:12}. Push the change to the release branch to build a new candidate, let it pass staging and try again."
fi
{
  echo "### No approved candidate of $version has the tree \`${arbol:0:12}\`"
  if [ "${#revisadas[@]}" -eq 0 ]; then
    echo "- no candidate of $version yet"
  else
    printf -- '- %s\n' "${revisadas[@]}"
  fi
} >> "$resumen"
exit 1
