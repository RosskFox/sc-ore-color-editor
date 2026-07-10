#!/usr/bin/env bash
# refresh-known-keys.sh
# Daily refresh: check whether any of the five community packs changed since
# the last run. If so, regenerate known-keys.ini/.json and commit to main.
#
#   - Reads/ writes the SHAs of the latest commit touching each pack file in
#     .pack-shas (relative to the repo dir).
#   - Idempotent: if nothing changed, exits 0 without writing or committing.
#   - Pushes to origin/main so GitHub Pages serves the updated file.
#
# Exit codes: 0 = ok (updated or no-op), 1 = error.
set -euo pipefail

REPO_DIR="/home/user/workspace/ini-color-editor"
cd "$REPO_DIR"

CHECK_ONLY=0
if [[ "${1:-}" == "--check" ]]; then
  # Programmatic trigger mode: exit 0 if any pack changed (proceed to LLM task),
  # exit 1 if nothing changed (skip the tick). No writes, no commits.
  CHECK_ONLY=1
fi

SHAS_FILE="$REPO_DIR/.pack-shas"

# pack_id|github_api_url  (path-scoped commits endpoint, per_page=1)
declare -a PACKS=(
  "stock|https://api.github.com/repos/BeltaKoda/ScCompLangPackRemix/commits?path=LIVE/stock-global.ini&sha=main&per_page=1"
  "beltakoda|https://api.github.com/repos/BeltaKoda/ScCompLangPackRemix/commits?path=LIVE/data/Localization/english/global.ini&sha=main&per_page=1"
  "exoae|https://api.github.com/repos/ExoAE/ScCompLangPack/commits?path=ScCompLangPack/data/Localization/english/global.ini&sha=main&per_page=1"
  "exoae2|https://api.github.com/repos/ExoAE/ScCompLangPack/commits?path=ScCompLangPackRemix2/data/Localization/english/global.ini&sha=main&per_page=1"
  "mrkraken|https://api.github.com/repos/MrKraken/StarStrings/commits?path=Data/Localization/english/global.ini&sha=master&per_page=1"
)

# Load previously seen SHAs: lines of "pack_id=sha"
declare -A OLD=()
if [[ -f "$SHAS_FILE" ]]; then
  while IFS='=' read -r k v; do [[ -n "$k" ]] && OLD["$k"]="$v"; done < "$SHAS_FILE"
fi

changed=0
NEWLINES=()
for entry in "${PACKS[@]}"; do
  pack="${entry%%|*}"
  url="${entry#*|}"
  sha=$(curl -fsSL -H "Accept: application/vnd.github+json" -H "User-Agent: sc-ore-color-editor" "$url" \
        | python3 -c "import sys,json; d=json.load(sys.stdin); print(d[0]['sha'] if d else '')" 2>/dev/null || echo "")
  if [[ -z "$sha" ]]; then
    echo "WARN: could not fetch SHA for $pack; skipping"
    NEWLINES+=("$pack=${OLD[$pack]:-}")
    continue
  fi
  NEWLINES+=("$pack=$sha")
  if [[ "${OLD[$pack]:-}" != "$sha" ]]; then
    echo "CHANGED: $pack  ${OLD[$pack]:-none} -> $sha"
    changed=1
  else
    echo "same:   $pack  $sha"
  fi
done

if [[ "$CHECK_ONLY" -eq 1 ]]; then
  if [[ "$changed" -eq 0 ]]; then
    echo "No pack changes detected. Skipping."
    exit 1
  fi
  echo "Pack changes detected. Proceeding to refresh."
  exit 0
fi

if [[ "$changed" -eq 0 ]]; then
  echo "No pack changes detected. Nothing to do."
  exit 0
fi

echo "Changes detected — regenerating known-keys..."
python3 "$REPO_DIR/build-known-keys.py"

# persist new SHAs (before commit so the file is part of the change)
printf '%s\n' "${NEWLINES[@]}" > "$SHAS_FILE"

git add known-keys.ini known-keys.json known-keys.meta.json .pack-shas
git commit -q -m "Auto-refresh known-keys (community pack update detected)" || {
  echo "Nothing to commit despite detected changes (build output unchanged)."
  exit 0
}
git push -q origin main
echo "Pushed updated known-keys to main."
