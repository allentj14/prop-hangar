# Prop Hangar

A personal phone app listing every War Thunder propeller plane by nation and research tree, with play style, armament, stats, community notes and best lineups for each battle rating.

Unofficial fan tool. Not affiliated with Gaijin Entertainment. Game data comes from the community datamine (gszabi99/War-Thunder-Datamine); play-style notes are summarized from the War Thunder wiki.

## Install on iPhone

1. Open the GitHub Pages link for this repo in **Safari**.
2. Tap **Share**, then **Add to Home Screen**.
3. Open it from the new icon. It works offline with the last data it downloaded.

## How updates work

- `.github/workflows/update-data.yml` runs every 6 hours. When the game data shows a new version, it rebuilds `data/` and commits it.
- The app downloads `data/*.json` each time it opens and shows "Updated to game vX" after a patch.
- The Excel version is rebuilt too: `data/War Thunder Prop Planes.xlsx`.
- To update right away: **Actions → Update plane data → Run workflow**.

## Files

- `index.html`, `sw.js`, `manifest.webmanifest`, `icons/` – the app
- `data/` – generated plane data (don't edit by hand)
- `scripts/` – the rebuild pipeline; `scripts/community.json` holds the community notes
