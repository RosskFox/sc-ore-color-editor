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
import sys
import urllib.request
from datetime import datetime, timezone

# Same packs / URLs the app uses (index.html PACK_URLS), in priority order.
# Stock is first so its values are preferred for any shared key.
PACKS = [
    ("stock",     "https://raw.githubusercontent.com/BeltaKoda/ScCompLangPackRemix/main/LIVE/stock-global.ini"),
    ("beltakoda", "https://raw.githubusercontent.com/BeltaKoda/ScCompLangPackRemix/main/LIVE/data/Localization/english/global.ini"),
    ("exoae",     "https://raw.githubusercontent.com/ExoAE/ScCompLangPack/main/ScCompLangPack/data/Localization/english/global.ini"),
    ("exoae2",    "https://raw.githubusercontent.com/ExoAE/ScCompLangPack/main/ScCompLangPackRemix2/data/Localization/english/global.ini"),
    ("mrkraken",  "https://raw.githubusercontent.com/MrKraken/StarStrings/master/Data/Localization/english/global.ini"),
]

INI_OUT  = "known-keys.ini"
JSON_OUT = "known-keys.json"


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "sc-ore-color-editor/build-known-keys"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8-sig", errors="replace")


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
    per_pack = {}        # pack -> key count
    for pack_id, url in PACKS:
        try:
            text = fetch(url)
        except Exception as e:
            print(f"  ✗ {pack_id}: fetch failed ({e})", file=sys.stderr)
            sys.exit(1)
        keys = parse_keys(text)
        per_pack[pack_id] = len(keys)
        added = 0
        for k, v in keys.items():
            if k not in merged:
                merged[k] = v
                added += 1
        print(f"  ✓ {pack_id}: {len(keys):,} keys ({added:,} new)")

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
    print("\nDone. Commit and push to update the live site.")


if __name__ == "__main__":
    main()
