# Death Must Die Inventory Extractor

([Spanish version](README.es.md))

A read-only command-line tool for exporting a Death Must Die inventory from a local save file. It supports Windows 11 and macOS, and never modifies the save, Steam Cloud, or the game.

## Quick start

Requirements: Python 3.11 or newer. Git is needed only to clone the repository.

```powershell
git clone https://github.com/Emanullh/DMD_MCP.git
cd DMD_MCP
python dmd_inventory.py dump
```

If your Windows installation provides the Python Launcher, `py -3 dmd_inventory.py dump` also works. On macOS, run `python3 dmd_inventory.py dump`.

Close the game before running the command so the exported snapshot is consistent.

## Save locations

The tool detects `.sav` files automatically in the following folders. If more than one file is found, choose one interactively or pass its path with `--save`.

| Platform | Default save folder |
| --- | --- |
| Windows 11 | `%USERPROFILE%\AppData\LocalLow\Realm Archive\Death Must Die\Saves` |
| macOS | `~/Library/Application Support/Realm Archive/Death Must Die/Saves` |

## Commands

| Command | Description |
| --- | --- |
| `dump` | Exports the inventory to JSON files. |
| `dump --save PATH` | Exports a specific `.sav` file. |
| `dump --output DIRECTORY` | Writes files to another output directory. |
| `dump --debug-dump` | Adds structural metadata for troubleshooting. |
| `inspect --save PATH` | Prints a save summary without creating output files. |
| `validate output/inventory.json` | Checks that an exported inventory is internally consistent. |

Use `python dmd_inventory.py <command>` on Windows and `python3 dmd_inventory.py <command>` on macOS. Windows installations with the Python Launcher may use `py -3` instead of `python`.

## Output

By default, `dump` creates an `output` folder outside the save directory.

| File | Contents |
| --- | --- |
| `inventory_raw.json` | Raw ProfileState, repository entries, containers, locations, and original item fields. |
| `inventory.json` | Stable item list for analysis or LLM use; unknown labels remain `null`. |
| `unresolved.json` | Unknown affix IDs and structural issues found during extraction. |
| `inventory_bundle.zip` | Archive containing `inventory.json` and `unresolved.json`. |
| `debug_structure.json` | Optional structural metadata, created only with `--debug-dump`. |

## Safety and troubleshooting

- The tool only reads the selected save and works from a temporary snapshot.
- Output inside the game's save directory is rejected to protect the original files.
- If no save is detected, pass its full path: `dump --save "PATH\TO\Save_0.sav"`.
- If validation fails, keep `inventory_raw.json` and `unresolved.json`; they contain the data needed to inspect the problem.
