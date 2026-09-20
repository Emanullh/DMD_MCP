"""Tolerant extraction of ProfileState and current item references."""

from __future__ import annotations

import json
from typing import Any


class ExtractionError(RuntimeError):
    """The save lacks a structurally valid ProfileState."""


def parse_json_value(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, str):
        raise ExtractionError(f"{label} must be JSON text.")
    try:
        decoded = json.loads(value.lstrip("\ufeff"))
    except json.JSONDecodeError as error:
        raise ExtractionError(f"Invalid {label} JSON: {error}") from error
    if not isinstance(decoded, dict):
        raise ExtractionError(f"{label} must decode to an object.")
    return decoded


def maybe_json(value: Any) -> Any:
    if not isinstance(value, str) or value.lstrip("\ufeff")[:1] not in "[{":
        return value
    try:
        return json.loads(value.lstrip("\ufeff"))
    except json.JSONDecodeError:
        return value


def find_profile(outer: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    serialized = outer.get("serializedSaveData")
    if not isinstance(serialized, dict):
        raise ExtractionError("serializedSaveData must be an object.")
    keys, values = serialized.get("keys"), serialized.get("values")
    if not isinstance(keys, list) or not isinstance(values, list):
        raise ExtractionError("serializedSaveData needs keys and values lists.")
    for index, type_key in enumerate(keys):
        if isinstance(type_key, str) and "ProfileState" in type_key and index < len(values):
            return index, parse_json_value(values[index], "ProfileState")
    raise ExtractionError("ProfileState was not found in serializedSaveData.")


def repository_entries(profile: dict[str, Any]) -> list[dict[str, Any]]:
    state = profile.get("PlayerRepoState")
    return state.get("Entries", []) if isinstance(state, dict) and isinstance(state.get("Entries"), list) else []


def repository_index(entries: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    result: dict[int, dict[str, Any]] = {}
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("Id"), dict) or not isinstance(entry.get("Item"), dict):
            continue
        item_id = entry["Id"].get("_value")
        if isinstance(item_id, int):
            result[item_id] = entry["Item"]
    return result


def slot_ids(state: Any) -> list[tuple[int, int]]:
    state = maybe_json(state)
    if not isinstance(state, dict) or not isinstance(state.get("ItemSlots"), list):
        return []
    found: list[tuple[int, int]] = []
    for index, slot in enumerate(state["ItemSlots"]):
        if not isinstance(slot, dict) or slot.get("IsEmpty") is True:
            continue
        item_id = slot.get("Id", {}).get("_value") if isinstance(slot.get("Id"), dict) else None
        if isinstance(item_id, int):
            found.append((index, item_id))
    return found


def item_list(state: Any) -> list[dict[str, Any]]:
    state = maybe_json(state)
    if not isinstance(state, dict) or not isinstance(state.get("Items"), list):
        return []
    return [item for item in state["Items"] if isinstance(item, dict)]


def add_reference(
    index: dict[int, dict[str, Any]],
    items: dict[str, dict[str, Any]],
    unresolved: list[dict[str, Any]],
    container: str,
    slot: int,
    item_id: int,
    extra: dict[str, Any] | None = None,
) -> None:
    if item_id not in index:
        unresolved.append({"kind": "missing_repository_reference", "container": container, "index": slot, "id": item_id})
        return
    item = items[str(item_id)]
    item["locations"].append({"container": container, "index": slot, **(extra or {})})


def add_state(
    state: Any,
    container: str,
    index: dict[int, dict[str, Any]],
    items: dict[str, dict[str, Any]],
    unresolved: list[dict[str, Any]],
    extra: dict[str, Any] | None = None,
) -> None:
    for slot, item_id in slot_ids(state):
        add_reference(index, items, unresolved, container, slot, item_id, extra)
    for slot, raw in enumerate(item_list(state)):
        key = f"direct:{container}:{slot}"
        items[key] = {"uid": None, "raw": raw, "locations": [{"container": container, "index": slot, **(extra or {})}]}


def same_json(left: Any, right: Any) -> bool:
    return maybe_json(left) == maybe_json(right)


def extract_raw(outer: dict[str, Any], source: dict[str, str]) -> dict[str, Any]:
    """Extract all known item locations while retaining raw ProfileState data."""
    profile_index, profile = find_profile(outer)
    entries = repository_entries(profile)
    index = repository_index(entries)
    unresolved: list[dict[str, Any]] = []
    items = {str(item_id): {"uid": str(item_id), "raw": raw, "locations": []} for item_id, raw in index.items()}
    containers: dict[str, Any] = {
        "stashes": profile.get("Stashes"), "legacy_stash_json": profile.get("StashJson"),
        "stash_state": profile.get("StashState"), "library": profile.get("LibraryState"),
        "backpack": profile.get("BackpackState"), "heroes": profile.get("InventoryData"),
    }

    stashes = maybe_json(profile.get("Stashes"))
    stash_jsons = stashes.get("StashJsons", []) if isinstance(stashes, dict) and isinstance(stashes.get("StashJsons"), list) else []
    for group, stash in enumerate(stash_jsons):
        pages = maybe_json(stash)
        for page_index, page in enumerate(pages.get("Pages", []) if isinstance(pages, dict) else []):
            add_state(page, "stash", index, items, unresolved, {"stash_group": group, "page": page_index})

    legacy_alias = bool(stash_jsons) and same_json(profile.get("StashJson"), stash_jsons[0])
    if not legacy_alias:
        legacy = maybe_json(profile.get("StashJson"))
        for page_index, page in enumerate(legacy.get("Pages", []) if isinstance(legacy, dict) else []):
            add_state(page, "stash_legacy", index, items, unresolved, {"page": page_index})
    add_state(profile.get("StashState"), "stash_state", index, items, unresolved)
    add_state(profile.get("LibraryState"), "library", index, items, unresolved)
    add_state(profile.get("BackpackState"), "backpack", index, items, unresolved)

    heroes: list[dict[str, Any]] = []
    for hero_index, entry in enumerate(profile.get("InventoryData", [])):
        if not isinstance(entry, dict):
            unresolved.append({"kind": "unknown_hero_entry", "index": hero_index, "raw": entry})
            continue
        hero_state = maybe_json(entry.get("Json"))
        if not isinstance(hero_state, dict):
            unresolved.append({"kind": "invalid_hero_json", "index": hero_index, "raw": entry.get("Json")})
            continue
        selected = hero_state.get("SelectedLoadout")
        heroes.append({"id": entry.get("CharacterCode"), "selected_loadout": selected, "raw": entry})
        add_state(hero_state.get("EquipmentState"), "equipment_legacy", index, items, unresolved, {"hero_index": hero_index})
        loadouts = hero_state.get("LoadoutStates", [])
        if isinstance(selected, int) and isinstance(loadouts, list) and 0 <= selected < len(loadouts):
            add_state(loadouts[selected], "equipped", index, items, unresolved, {"hero_index": hero_index, "loadout": selected})
        elif loadouts:
            unresolved.append({"kind": "invalid_selected_loadout", "hero_index": hero_index, "value": selected})

    category_sets = {name: set() for name in ("stash", "equipped", "library", "backpack", "other")}
    for key, item in items.items():
        for location in item["locations"]:
            category = location["container"]
            category_sets[category if category in category_sets else "other"].add(key)
    counts = {f"{name}_items": len(values) for name, values in category_sets.items()}
    counts["unplaced_items"] = sum(not item["locations"] for item in items.values())
    counts["total_items"] = len(items)
    return {
        "extractor": {"version": "0.1.0", **source},
        "save": {"version": outer.get("Version"), "profile_state_index": profile_index},
        "profile_state": profile,
        "repository": {"entries": entries},
        "containers": containers,
        "heroes": heroes,
        "items": list(items.values()),
        "aliases": {"legacy_stash_json": legacy_alias},
        "counts": counts,
        "unresolved": unresolved,
    }
