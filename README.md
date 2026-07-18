# Star Citizen INI Color Editor

A browser-based editor for applying in-game color to Star Citizen's `global.ini` localization file. Assign verified emphasis (EM) tags to mineable commodities and vehicle components, then export a modified `Global.ini` to drop back into the game.

Live site: **https://rosskfox.github.io/sc-ore-color-editor/**

---

## What it does

- **Three-pane workspace**
  - **Left** — load a source `global.ini` (drag-and-drop a local file, or pick one of five community language packs)
  - **Center** — search, filter, and assign EM color tags to each key
  - **Right** — the modified output, with a toggle between **Full output** (entire file) and **Changes only** (just the keys you tagged)

- **Verified in-game color** — Star Citizen colors localization text by wrapping a value in emphasis tags (`key=<EM4>Value</EM4>`), not with hex codes. Only two tags render a distinct color:

  | Tag | In-game color |
  |-----|---------------|
  | EM2 | Green |
  | EM4 | Red |

  EM0, EM1, EM3, EM5, and EM6 all fall back to the default UI cyan and have no visible effect, so only EM2 and EM4 are offered.

- **Custom string editing** — beyond assigning a color, you can edit the displayed text of any key directly in the center pane. Edited values appear in the accent color and flow into the output (wrapped in the EM tag when one is assigned, plain `key=value` otherwise). Use the reset (x) button on a row to restore the original text and clear its tag.

- **Curated editable scope** — the center pane is limited to **357 real keys** derived from the [star-citizen.wiki API](https://api.star-citizen.wiki):
  - Mineable commodities (`is_mineable=true`) → `items_commodities_*` keys, including variants (e.g. `items_commodities_carinite`, `_pure`, `_raw`)
  - Vehicle components (`category=vehicle-components`) → `item_Name<class_name>` keys

  The full loaded file is still parsed and written back unchanged; only the editing surface is scoped.

- **Virtual keys** — if a key exists in the known-keys reference but not in your loaded file, it still appears in the center pane (tagged "virtual"). Tagging it appends it to your output.

- **Auto-import** — loading a file that already contains `<EMn>...</EMn>` wrappers detects and strips them, pre-selecting the tag for clean editing.

- **Reference dictionary** — on startup the app loads a merged union of 90,171 real localization keys from five sources (stock + four community packs), so even keys absent from your chosen pack are available to edit.

- **Light / dark mode** toggle.

- **Correct file format on export** — UTF-8 BOM + CRLF line endings, matching what the game expects. **Download always exports the full modified `Global.ini`**, regardless of whether the right pane is set to Full output or Changes only. (The Copy button copies whatever is currently visible in the pane.)

---

## Community packs

Loadable directly from within the app:

| Pack | Last updated |
|------|-------------|
| Stock global.ini | May 20, 2026 |
| BeltaKoda Remix | May 20, 2026 |
| ExoAE ScCompLangPack | Jul 16, 2026 |
| ExoAE Remix2 | Jul 16, 2026 |
| MrKraken StarStrings | Jul 17, 2026 |

_Pack update dates are fetched server-side by the daily refresh script and shown live in the app._

---

## How to use

1. Open the [live site](https://rosskfox.github.io/sc-ore-color-editor/).
2. Load a source file — drag in your own `global.ini`, or pick a community pack from the dropdown.
3. Search or browse the center pane (try `carinite`, `AbsoluteZero`, etc.).
4. For each key: edit the displayed text inline (optional), then pick **EM2 — green** or **EM4 — red** from the dropdown (or use Auto-tag / Randomize for bulk color assignment).
5. Click **Download** to export your modified `Global.ini` (always the full file, including every key you tagged or edited).
6. Drop the file into your Star Citizen `Data/Localization/english/` folder.

---

## Project structure

```
index.html          # the entire app (HTML + CSS + JS, single file)
known-keys.ini      # merged union of 90,171 localization keys (reference dictionary)
known-keys.json     # compact key-only list
known-keys.meta.json # refresh timestamp + per-pack key counts & last-updated dates
categories.json     # StarMeld category schema (groups + regex patterns)
curated-keys.json   # the 357 curated editable keys (commodities + components)
curated-keys.txt    # plain-text list of the curated keys
build-known-keys.py # rebuilds the known-keys files from the five community packs
refresh-known-keys.sh # daily SHA-gated refresh (regenerates + commits when a pack changes)
```

The app is a single static `index.html` with no build step. GitHub Pages serves it from the `main` branch.

---

## Credits & sources

- Community language packs: [BeltaKoda/ScCompLangPackRemix](https://github.com/BeltaKoda/ScCompLangPackRemix), [ExoAE/ScCompLangPack](https://github.com/ExoAE/ScCompLangPack), [MrKraken/StarStrings](https://github.com/MrKraken/StarStrings)
- Category schema: [BeltaKoda/StarMeld](https://github.com/BeltaKoda/StarMeld)
- Commodity & component data: [star-citizen.wiki API](https://api.star-citizen.wiki)
- Key list reference: [BeltaKoda/ScCompLangPackRemix](https://beltakoda.github.io/ScCompLangPackRemix/)
