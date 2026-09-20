# Death Must Die Inventory Extractor

Read-only macOS CLI for extracting a Death Must Die inventory. It does not edit saves, Steam Cloud, or the game.

1. Install Python 3.11+.
2. Close Death Must Die for a consistent snapshot.
3. Run `python3 dmd_inventory.py dump` (or pass `--save /path/to/file.sav`).
4. Read `output/inventory_raw.json`, `output/inventory.json`, and `output/unresolved.json`.

The tool detects `.sav` files in `~/Library/Application Support/Realm Archive/Death Must Die/Saves`; several files require selection or `--save`.

- `inventory_raw.json` preserves ProfileState, repository entries, containers, locations, and original item/affix fields.
- `inventory.json` is the stable LLM-oriented item list. Labels not present in the save remain `null`; numeric values and `raw` are retained.
- `unresolved.json` lists affix IDs not in the historical reference catalog and structural extraction issues.

Use `python3 dmd_inventory.py inspect --save PATH` for concise structure, and `python3 dmd_inventory.py validate output/inventory.json` to check output. `--debug-dump` adds structural metadata outside the save directory.
