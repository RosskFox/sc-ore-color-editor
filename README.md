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

- **Curated editable scope** — the center pane is limited to **355 real keys** derived from the [star-citizen.wiki API](https://api.star-citizen.wiki):
  - Mineable commodities (`is_mineable=true`) → `items_commodities_*` keys, including variants (e.g. `items_commodities_carinite`, `_pure`, `_raw`)
  - Vehicle components (`category=vehicle-components`) → `item_Name<class_name>` keys

  The full loaded file is still parsed and written back unchanged; only the editing surface is scoped.

- **Virtual keys** — if a key exists in the known-keys reference but not in your loaded file, it still appears in the center pane (tagged "virtual"). Tagging it appends it to your output.

- **Auto-import** — loading a file that already contains `<EMn>...</EMn>` wrappers detects and strips them, pre-selecting the tag for clean editing.

- **Reference dictionary** — on startup the app loads a merged union of 89,059 real localization keys from five sources (stock + four community packs), so even keys absent from your chosen pack are available to edit.

- **Light / dark mode** toggle.

- **Correct file format on export** — UTF-8 BOM + CRLF line endings, matching what the game expects. Downloads default to `Global.ini` (or `Global-changes.ini` for the changes-only view).

---

## Community packs

Loadable directly from within the app:

| Pack | Last updated |
|------|-------------|
| Stock global.ini | May 20, 2026 |
| BeltaKoda Remix | May 20, 2026 |
| ExoAE ScCompLangPack | Jul 1, 2026 |
| ExoAE Remix2 | Jul 1, 2026 |
| MrKraken StarStrings | Jul 1, 2026 |

---

## How to use

1. Open the [live site](https://rosskfox.github.io/sc-ore-color-editor/).
2. Load a source file — drag in your own `global.ini`, or pick a community pack from the dropdown.
3. Search or browse the center pane (try `carinite`, `AbsoluteZero`, etc.).
4. For each key, pick **EM2 — green** or **EM4 — red** from the dropdown (or use Auto-tag / Randomize for bulk assignment).
5. Switch the right pane to **Full output** and click **Download** to get your modified `Global.ini`.
6. Drop the file into your Star Citizen `Data/Localization/english/` folder.

---

## Project structure

```
index.html          # the entire app (HTML + CSS + JS, single file)
known-keys.ini      # merged union of 89,059 localization keys (reference dictionary)
known-keys.json     # compact key-only list
categories.json     # StarMeld category schema (groups + regex patterns)
curated-keys.json   # the 355 curated editable keys (commodities + components)
curated-keys.txt    # plain-text list of the curated keys
```

The app is a single static `index.html` with no build step. GitHub Pages serves it from the `main` branch.

---

## Credits & sources

- Community language packs: [BeltaKoda/ScCompLangPackRemix](https://github.com/BeltaKoda/ScCompLangPackRemix), [ExoAE/ScCompLangPack](https://github.com/ExoAE/ScCompLangPack), [MrKraken/StarStrings](https://github.com/MrKraken/StarStrings)
- Category schema: [BeltaKoda/StarMeld](https://github.com/BeltaKoda/StarMeld)
- Commodity & component data: [star-citizen.wiki API](https://api.star-citizen.wiki)
- Key list reference: [BeltaKoda/ScCompLangPackRemix](https://beltakoda.github.io/ScCompLangPackRemix/)
