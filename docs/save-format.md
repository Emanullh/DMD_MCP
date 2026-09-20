# Save format findings

The observed 0.8.x save is UTF-8 JSON (with BOM) compressed as raw DEFLATE. This extractor uses Python `zlib` and `json` only; it does not deserialize BinaryFormatter/NRBF or execute any save-provided type.

The outer object has `serializedSaveData.keys` plus `values`. The matching key containing `Death.App.Profile+ProfileState` identifies the ProfileState; its position is not assumed.

The historical editor directly modeled `StashState.Items` and `InventoryData[].Json.EquipmentState.Items`. The current save instead stores physical items in `PlayerRepoState.Entries` with numeric IDs. `ItemSlots` in stashes, backpack, library, and loadouts refer to those IDs. Current equipment is selected from `LoadoutStates[SelectedLoadout]`.

`StashJson` matched `Stashes.StashJsons[0]` in the inspected current save. The extractor retains it in raw output as a legacy alias but does not count it twice. Old direct `Items` collections remain a fallback path.

Current affixes use `Code`, `Levels`, and `Enhanced`. `data/legacy_affixes.csv` is derived from the historical `NewItemAffixes.csv` only as a reference: unknown current IDs keep `name: null` and appear in unresolved output. Item type/rarity numeric enums are preserved without claiming current names.
