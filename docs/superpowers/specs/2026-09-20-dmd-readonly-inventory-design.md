# Death Must Die Read-Only Inventory Extractor Design

## Goal

Create a macOS CLI that reads a Death Must Die `.sav` snapshot and writes a
faithful inventory dump plus a stable, LLM-oriented inventory JSON. It never
edits, moves, renames, backs up, or otherwise writes in the game's save
directory.

## Non-goals

No save editor, mod, MCP server, UI, optimizer, recommendations, item selling,
or inventory sorting.

## Verified format

The current local save (format `Version: 10`) is UTF-8 JSON with a BOM,
compressed as raw DEFLATE. It is not BinaryFormatter/NRBF, so decoding uses
only Python's non-executing `zlib` and `json` modules.

The outer document contains `serializedSaveData.keys` and
`serializedSaveData.values`. The ProfileState is found by matching its type-key
for `ProfileState`, never by assuming it is at index zero.

The former editor's model is useful only as historical evidence: it directly
stored items in `StashState` and `EquipmentState`. The current save instead
uses `PlayerRepoState.Entries`: each entry is `{Id: {_value: int}, Item: {...}}`.
Containers hold `{Id: {_value: int}, IsEmpty: bool}` references. The current
equipment lives in each hero's `LoadoutStates[SelectedLoadout]` rather than
`EquipmentState.Items`. `StashJson` is a byte-for-byte structural duplicate of
`Stashes.StashJsons[0]` in the observed save and must be recorded but not
counted twice.

Current item fields observed: `Code`, `Type`, `Rarity`, `TierIndex`,
`IsUnique`, `SubtypeCode`, `IconVariant`, `DropVariant`, `Affixes`, and
`WasOwnedByPlayer`. Affixes contain `Code`, `Levels`, and `Enhanced`.
All fields, including future fields, are retained as raw data.

## Safety contract

- Save discovery reads only `*.sav` from the SteamDB-confirmed macOS path.
- Each command that opens a save first copies it to a temporary file outside
  the save directory, applies permission `0400`, and parses only that copy.
- Outputs are written only beneath the project `output/` directory (or a
  future explicit external output path), never in the save directory.
- The code contains no encoder, compressor-for-save, serializer-to-save, or
  Steam interaction.
- A process-name check emits a warning if Death Must Die appears to be running;
  it never changes that process.
- The output source identifies only the filename, never an absolute path or
  macOS username.

## CLI

`dump [--save PATH] [--verbose] [--debug-dump]` discovers a save or uses the
explicit path, snapshots it, creates all three output JSON files, and prints
counts. When several saves exist, it prints indexed filenames and accepts an
interactive selection on a terminal; non-interactive use receives a precise
`--save` instruction.

`inspect --save PATH [--verbose]` snapshots and reports compression, root keys,
ProfileState discovery, candidate collections, counts, and unknown structures
without writing normal outputs.

`validate output/inventory.json` is offline and verifies schema basics,
unique UIDs, item locations, and declared count arithmetic.

## Data flow

1. Discover or validate a `.sav` path, rejecting directories and a target
   inside `output/` only when invalid.
2. Snapshot the source with `shutil.copyfile` into a restrictive temporary
   file. Record source filename and a SHA-256 of the snapshot, not its path.
3. Decompress raw DEFLATE, decode UTF-8 with BOM support, and parse JSON.
4. Find ProfileState by type-key; preserve the entire outer root and parsed
   nested JSON values as raw data.
5. Build an ID-to-item index from repository entries, then follow every known
   item-slot reference. Treat old direct `Items` collections as a fallback.
6. Deduplicate aliases such as legacy `StashJson` only for item totals. Keep
   every original container in the raw dump and record the alias decision.
7. Normalize physical items using the stable repository ID as `uid`; if an
   entry lacks an ID, derive a deterministic SHA-256 UID from canonical raw
   JSON plus location and index.
8. Load the historical affix CSV only as a reference catalog. A missing code
   has `name: null`, `unresolved: true`, and a matching entry in
   `unresolved.json`; the original affix remains in `raw`.

## Outputs

`output/inventory_raw.json` contains extractor metadata, save metadata,
ProfileState, parsed nested JSON, repository entries, all containers and
locations, alias metadata, unresolved structures, and full original item and
affix data.

`output/inventory.json` has `schema_version: 1`, redacted source metadata,
heroes with selected-loadout item IDs, a flat item array, and `unresolved`.
It exposes only demonstrated semantics. Numeric item type, rarity, and slot
index are preserved; a human label is `null` unless it exists directly in the
save or in a separately verified current-game catalog. `raw` retains the
complete source item, affixes, repository ID, and location references.

`output/unresolved.json` contains unknown affix IDs, unknown container shapes,
unresolved reference IDs, unknown item type numbers, and parsing failures with
their raw fragments. `--debug-dump` additionally writes
`output/debug_structure.json` with structural paths and field sets, not source
paths.

## Validation and errors

The extractor validates each non-empty reference resolves to exactly one repo
item, UIDs are unique, and no indexed item silently disappears. It reports
separate counts for selected-loadout equipment, stash groups, backpack,
library, fallback/direct collections, unplaced repository entries, affixes,
and unresolved codes. It checks the total equality only across the canonical,
non-alias containers. Truncated, invalid-DEFLATE, invalid-UTF-8, invalid-JSON,
or missing-ProfileState saves raise clear errors without creating partial
inventory files.

## Implementation shape

Keep the project dependency-free and small:

- `dmd_inventory.py`: argparse entry point and command dispatch.
- `dmd/save_reader.py`: discovery, snapshot, process warning, and safe decode.
- `dmd/extractor.py`: ProfileState lookup, nested JSON expansion, repository
  resolution, container traversal, and raw output construction.
- `dmd/normalizer.py`: deterministic UIDs, affix catalog lookup, and LLM JSON.
- `dmd/validator.py`: reusable output and count checks.
- `tests/`: synthetic raw-DEFLATE fixtures created in tests; no personal save.
- `docs/save-format.md`: reference findings and observed old-versus-current
  differences.

## Sources consulted

- `DenislavLitsov/DeathMustDieSaveEditor`: `FileManager` uses raw DEFLATE;
  `SaveData` models the outer key/value table; `decodedSave.json` identifies
  `Death.App.Profile+ProfileState`; `NewItemAffixes.csv` is a historical affix
  catalog; `Notes.txt` points to `Items_AffixesBoons` in Unity assets.
- SteamDB App 2334730 UFS: macOS override is
  `~/Library/Application Support/Realm Archive/Death Must Die/Saves`, with
  `*.sav` cloud-save pattern.

## Test coverage

Tests cover discovery (zero, one, and multiple saves), snapshot permissions and
source immutability, BOM/raw-DEFLATE decoding, corrupt saves, ProfileState
lookup independent of key order, direct and repository-backed item extraction,
selected loadouts, stash alias de-duplication, raw unknown fields, deterministic
UIDs, known and unknown affixes, and output validation/count failures.
