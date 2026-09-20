import json
from pathlib import Path
import zlib


def write_deflated(path: Path, value: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    compressor = zlib.compressobj(wbits=-zlib.MAX_WBITS)
    payload = ("\ufeff" + json.dumps(value)).encode("utf-8")
    path.write_bytes(compressor.compress(payload) + compressor.flush())
    return path


def make_outer(entries: list[tuple[str, str]]) -> dict:
    return {"Version": 10, "serializedSaveData": {"keys": [key for key, _ in entries], "values": [value for _, value in entries]}}


def profile_with_repo(stash_ids: list[int], loadout_ids: list[int], repo_ids: list[int] | None = None) -> dict:
    repo_ids = repo_ids if repo_ids is not None else sorted(set(stash_ids + loadout_ids))
    entries = [
        {
            "Id": {"_value": item_id},
            "Item": {"Code": f"item_{item_id}", "Type": 0, "Rarity": 0, "TierIndex": 0, "Affixes": []},
        }
        for item_id in repo_ids
    ]
    slots = lambda ids: [{"Id": {"_value": value}, "IsEmpty": False} for value in ids]
    page = {"Width": 1, "Height": 1, "Items": [], "ItemSlots": slots(stash_ids)}
    loadout = {"Items": [], "ItemSlots": slots(loadout_ids)}
    hero = {"CharacterCode": "Hero", "Json": json.dumps({"SelectedLoadout": 0, "EquipmentState": {"Items": [], "ItemSlots": []}, "LoadoutStates": [loadout]})}
    return {
        "PlayerRepoState": {"Entries": entries},
        "InventoryData": [hero],
        "Stashes": {"StashJsons": [json.dumps({"Pages": [page]})]},
        "StashJson": json.dumps({"Pages": [page]}),
        "LibraryState": {"Items": [], "ItemSlots": []},
        "BackpackState": {"Items": [], "ItemSlots": []},
        "StashState": {"Items": [], "ItemSlots": []},
    }


def profile_outer(profile: dict) -> dict:
    return make_outer([("Death.App.Profile+ProfileState, Death", json.dumps(profile))])
