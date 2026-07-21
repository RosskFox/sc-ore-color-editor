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

# pack_id|raw_file_url  (raw.githubusercontent.com serves an `etag` header = sha256 of
# the file content, via Fastly CDN with generous rate limits — no GitHub API needed,
# so change detection never 403s under the shared-IP unauthenticated API quota.)
declare -a PACKS=(
  "stock|https://raw.githubusercontent.com/BeltaKoda/ScCompLangPackRemix/main/LIVE/stock-global.ini"
  "beltakoda|https://raw.githubusercontent.com/BeltaKoda/ScCompLangPackRemix/main/LIVE/data/Localization/english/global.ini"
  "exoae|https://raw.githubusercontent.com/ExoAE/ScCompLangPack/main/ScCompLangPack/data/Localization/english/global.ini"
  "exoae2|https://raw.githubusercontent.com/ExoAE/ScCompLangPack/main/ScCompLangPackRemix2/data/Localization/english/global.ini"
  "mrkraken|https://raw.githubusercontent.com/MrKraken/StarStrings/master/src/For_Players/Data/Localization/english/global.ini"
)

# Load previously seen content tags: lines of "pack_id=etag"
declare -A OLD=()
if [[ -f "$SHAS_FILE" ]]; then
  while IFS='=' read -r k v; do [[ -n "$k" ]] && OLD["$k"]="$v"; done < "$SHAS_FILE"
fi

changed=0
NEWLINES=()
for entry in "${PACKS[@]}"; do
  pack="${entry%%|*}"
  url="${entry#*|}"
  # HEAD request only — the etag header is the file's content sha256.
  hdr=$(curl -fsSI -H "User-Agent: sc-ore-color-editor" "$url" 2>/dev/null || true)
  tag=$(printf '%s\n' "$hdr" | awk 'tolower($1)=="etag:"{gsub(/"/,"",$2); gsub(/\r/,"",$2); print $2; exit}')
  if [[ -z "$tag" ]]; then
    echo "WARN: could not fetch content tag for $pack; skipping"
    NEWLINES+=("$pack=${OLD[$pack]:-}")
    continue
  fi
  NEWLINES+=("$pack=$tag")
  if [[ "${OLD[$pack]:-}" != "$tag" ]]; then
    echo "CHANGED: $pack  ${OLD[$pack]:-none} -> $tag"
    changed=1
  else
    echo "same:   $pack  $tag"
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

git add known-keys.ini known-keys.json known-keys.meta.json README.md .pack-shas
git commit -q -m "Auto-refresh known-keys (community pack update detected)" || {
  echo "Nothing to commit despite detected changes (build output unchanged)."
  exit 0
}
git push -q origin main
echo "Pushed updated known-keys to main."
