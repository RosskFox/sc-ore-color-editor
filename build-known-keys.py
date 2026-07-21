#!/usr/bin/env python3
"""
Regenerate known-keys.ini and known-keys.json from all five community language packs.

The known-keys file is a merged union of every localization key across the packs.
It ships as a static snapshot alongside index.html and is loaded once at app
startup to power the "virtual" key list and default-value lookup.

Usage:
    python3 build-known-keys.py            # fetch all packs, overwrite the files
    python3 build-known-keys.py --check    # fetch, report changes, don't write

The output format matches what the app's buildKnownValues() expects:
  - plain `key=value` lines
  - LF line endings (no BOM)
  - deduplicated: each key appears once (first-seen value wins, packs iterated
    in a stable priority order so the stock baseline is preferred)
  - sorted by key for a stable, diff-friendly file
"""

import json
import re
import sys
import urllib.request
import urllib.parse
from datetime import datetime, timezone

# Same packs / URLs the app uses (index.html PACK_URLS), in priority order.
# Stock is first so its values are preferred for any shared key.
PACKS = [
    ("stock",     "https://raw.githubusercontent.com/BeltaKoda/ScCompLangPackRemix/main/LIVE/stock-global.ini"),
    ("beltakoda", "https://raw.githubusercontent.com/BeltaKoda/ScCompLangPackRemix/main/LIVE/data/Localization/english/global.ini"),
    ("exoae",     "https://raw.githubusercontent.com/ExoAE/ScCompLangPack/main/ScCompLangPack/data/Localization/english/global.ini"),
    ("exoae2",    "https://raw.githubusercontent.com/ExoAE/ScCompLangPack/main/ScCompLangPackRemix2/data/Localization/english/global.ini"),
    ("mrkraken",  "https://raw.githubusercontent.com/MrKraken/StarStrings/master/src/For_Players/Data/Localization/english/global.ini"),
]

INI_OUT  = "known-keys.ini"
JSON_OUT = "known-keys.json"
META_OUT = "known-keys.meta.json"

README_OUT = "README.md"
# pack_id -> display name as written in the README community-packs table
README_PACK_NAMES = {
    "stock":     "Stock global.ini",
    "beltakoda": "BeltaKoda Remix",
    "exoae":     "ExoAE ScCompLangPack",
    "exoae2":    "ExoAE Remix2",
    "mrkraken":  "MrKraken StarStrings",
}


def fmt_date(iso):
    """ISO commit date -> 'Jul 17, 2026' (matches the app's en-US format)."""
    if not iso:
        return "unknown"
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%b %-d, %Y")
    except Exception:
        return iso


def load_old_dates():
    """Read previously stored per-pack 'updated' dates from the existing meta file,
    so that when the GitHub API is rate-limited (HTTP 403) we preserve the last-known
    date instead of blanking it out. Dates never regress to null."""
    try:
        with open(META_OUT, "r", encoding="utf-8") as f:
            m = json.load(f)
        out = {}
        for k, v in (m.get("packs") or {}).items():
            if isinstance(v, dict) and v.get("updated"):
                out[k] = v["updated"]
        return out
    except Exception:
        return {}


def update_readme_dates(per_pack):
    """Rewrite the README community-packs table rows with fresh last-updated dates.
    Keeps the README in sync with the packs automatically (never goes stale)."""
    try:
        with open(README_OUT, "r", encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        print(f"  · {README_OUT} not found; skipping date sync", file=sys.stderr)
        return False
    changed = False
    for pid, name in README_PACK_NAMES.items():
        info = per_pack.get(pid, {})
        iso = info.get("updated") if isinstance(info, dict) else None
        date_str = fmt_date(iso)
        # match: | <Pack name> | <old date> |
        pattern = re.compile(r"(\| " + re.escape(name) + r" \| )[^|]+?( \|)")
        new_text, n = pattern.subn(lambda m, d=date_str: m.group(1) + d + m.group(2), text)
        if n:
            text = new_text
            changed = True
    if changed:
        with open(README_OUT, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        print(f"  updated {README_OUT} pack dates")
    return changed


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "sc-ore-color-editor/build-known-keys"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8-sig", errors="replace")


def commit_api_url(raw_url):
    """Derive the GitHub commits API URL (latest commit for a file) from a
    raw.githubusercontent.com file URL: .../{owner}/{repo}/{branch}/{path...}"""
    p = urllib.parse.urlparse(raw_url)
    parts = [s for s in p.path.split("/") if s]  # [owner, repo, branch, ...path]
    if len(parts) < 4:
        return None
    owner, repo, branch = parts[0], parts[1], parts[2]
    path = "/".join(parts[3:])
    q = urllib.parse.urlencode({"path": path, "sha": branch, "per_page": "1"})
    return f"https://api.github.com/repos/{owner}/{repo}/commits?{q}"


def fetch_commit_date(raw_url):
    """Return the ISO date of the latest commit touching raw_url's file, or None."""
    api = commit_api_url(raw_url)
    if not api:
        return None
    req = urllib.request.Request(api, headers={
        "User-Agent": "sc-ore-color-editor/build-known-keys",
        "Accept": "application/vnd.github+json",
    })
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.loads(r.read().decode("utf-8", errors="replace"))
    if isinstance(data, list) and data:
        c = data[0].get("commit", {}).get("committer", {}).get("date")
        return c
    return None


def parse_keys(text):
    """Return an ordered dict {key: value} from raw ini text. First occurrence wins."""
    out = {}
    for line in text.splitlines():
        line = line.rstrip("\r")
        if not line or line.lstrip().startswith(";") or line.lstrip().startswith("#"):
            continue
        eq = line.find("=")
        if eq == -1:
            continue
        key = line[:eq]
        val = line[eq + 1:]
        if key and key not in out:
            out[key] = val
    return out


def main():
    check_only = "--check" in sys.argv

    merged = {}          # key -> value (first pack to define it wins)
    per_pack = {}        # pack -> {keys: count, updated: ISO date}
    old_dates = load_old_dates()  # last-known dates, used if the API is rate-limited
    for pack_id, url in PACKS:
        try:
            text = fetch(url)
        except Exception as e:
            print(f"  ✗ {pack_id}: fetch failed ({e})", file=sys.stderr)
            sys.exit(1)
        keys = parse_keys(text)
        # latest commit date for this pack's file (best-effort; non-fatal).
        # If the GitHub API is rate-limited (403), preserve the previous date.
        updated = None
        try:
            updated = fetch_commit_date(url)
        except Exception as e:
            print(f"  · {pack_id}: commit date unavailable ({e})", file=sys.stderr)
        if not updated and old_dates.get(pack_id):
            updated = old_dates[pack_id]
            print(f"  · {pack_id}: preserving previous date ({updated[:10]})", file=sys.stderr)
        per_pack[pack_id] = {"keys": len(keys), "updated": updated}
        added = 0
        for k, v in keys.items():
            if k not in merged:
                merged[k] = v
                added += 1
        print(f"  ✓ {pack_id}: {len(keys):,} keys ({added:,} new)" + (f"  updated {updated[:10]}" if updated else ""))

    # Stable, diff-friendly ordering: sort by key.
    sorted_keys = sorted(merged.items(), key=lambda kv: kv[0])

    print(f"\n  merged union: {len(sorted_keys):,} unique keys")

    if check_only:
        # compare against existing known-keys.ini without writing
        try:
            with open(INI_OUT, "r", encoding="utf-8-sig") as f:
                existing = [l.rstrip("\r") for l in f if "=" in l]
            existing_set = {l.split("=", 1)[0] for l in existing}
        except FileNotFoundError:
            existing_set = set()
        new = set(merged) - existing_set
        gone = existing_set - set(merged)
        print(f"  existing: {len(existing_set):,} keys")
        print(f"  added vs current: {len(new):,}")
        print(f"  removed vs current: {len(gone):,}")
        if new:
            print("  sample new:", ", ".join(sorted(new)[:8]))
        if gone:
            print("  sample removed:", ", ".join(sorted(gone)[:8]))
        print("\n  (check mode — no files written)")
        return

    # Write known-keys.ini: LF endings, no BOM, key=value
    with open(INI_OUT, "w", encoding="utf-8", newline="\n") as f:
        for k, v in sorted_keys:
            f.write(f"{k}={v}\n")

    # Write known-keys.json: compact array of key strings (used by tooling)
    with open(JSON_OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump([k for k, _ in sorted_keys], f, ensure_ascii=False, separators=(",", ":"))

    # Write metadata: timestamp + counts, so the app can show last-refreshed
    meta = {
        "refreshed": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "keys": len(sorted_keys),
        "packs": per_pack,
    }
    with open("known-keys.meta.json", "w", encoding="utf-8", newline="\n") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"  wrote {INI_OUT} ({len(sorted_keys):,} keys)")
    print(f"  wrote {JSON_OUT}")
    print(f"  wrote known-keys.meta.json")
    # keep the README community-packs table in sync with the fresh pack dates
    update_readme_dates(per_pack)
    print("\nDone. Commit and push to update the live site.")


if __name__ == "__main__":
    main()
