# Death Must Die Inventory Extractor

Read-only Windows 11 and macOS CLI for extracting a Death Must Die inventory. It does not edit saves, Steam Cloud, or the game.

1. Install Python 3.11+.
2. Close Death Must Die for a consistent snapshot.
3. Run `py -3 dmd_inventory.py dump` on Windows, or `python3 dmd_inventory.py dump` on macOS (or pass `--save PATH`).
4. Read `output/inventory_raw.json`, `output/inventory.json`, and `output/unresolved.json`.

The tool detects `.sav` files in these locations; several files require selection or `--save`.

- Windows: `%USERPROFILE%\AppData\LocalLow\Realm Archive\Death Must Die\Saves`
- macOS: `~/Library/Application Support/Realm Archive/Death Must Die/Saves`

To clone it on Windows after publication:

```powershell
git clone https://github.com/Emanullh/DMD_MCP.git
cd DMD_MCP
py -3 dmd_inventory.py dump
```

- `inventory_raw.json` preserves ProfileState, repository entries, containers, locations, and original item/affix fields.
- `inventory.json` is the stable LLM-oriented item list. Labels not present in the save remain `null`; numeric values and `raw` are retained.
- `unresolved.json` lists affix IDs not in the historical reference catalog and structural extraction issues.

Use `py -3 dmd_inventory.py inspect --save PATH` on Windows, or `python3 dmd_inventory.py inspect --save PATH` on macOS, for concise structure. Use the same launcher with `validate output/inventory.json` to check output. `--debug-dump` adds structural metadata outside the save directory.
