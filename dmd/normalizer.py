"""Stable, conservative inventory JSON normalization."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any


def load_affix_catalog(path: Path) -> dict[str, str]:
    catalog: dict[str, str] = {}
    if not path.is_file():
        return catalog
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.reader(handle, delimiter=";"):
            if not row:
                continue
            if row[0].strip().lower() == "code":
                continue
            offset = 1 if not row[0].strip() else 0
            if len(row) > offset + 1 and row[offset].strip() and row[offset + 1].strip():
                catalog[row[offset].strip()] = row[offset + 1].strip()
    return catalog


def fallback_uid(raw: dict[str, Any], locations: list[dict[str, Any]]) -> str:
    payload = json.dumps({"locations": locations, "raw": raw}, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def normalize_affix(value: Any, catalog: dict[str, str]) -> tuple[dict[str, Any], str | None]:
    if not isinstance(value, dict):
        return {"id": None, "name": None, "value": None, "enhanced": None, "implicit": None, "unresolved": True, "raw": value}, None
    code = value.get("Code")
    unresolved = not isinstance(code, str) or code not in catalog
    return {
        "id": code, "name": catalog.get(code) if isinstance(code, str) else None,
        "value": value.get("Levels"), "enhanced": value.get("Enhanced"),
        "implicit": None, "unresolved": unresolved, "raw": value,
    }, code if unresolved and isinstance(code, str) else None


def normalize(raw: dict[str, Any], catalog_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    catalog = load_affix_catalog(catalog_path)
    unknown_codes: set[str] = set()
    normalized_items: list[dict[str, Any]] = []
    for extracted in raw.get("items", []):
        source = extracted.get("raw", {}) if isinstance(extracted, dict) else {}
        locations = extracted.get("locations", []) if isinstance(extracted, dict) and isinstance(extracted.get("locations"), list) else []
        uid = extracted.get("uid") if isinstance(extracted, dict) else None
        uid = uid or fallback_uid(source, locations)
        affixes = []
        for affix in source.get("Affixes", []) if isinstance(source, dict) and isinstance(source.get("Affixes"), list) else []:
            normalized, unknown = normalize_affix(affix, catalog)
            affixes.append(normalized)
            if unknown:
                unknown_codes.add(unknown)
        normalized_items.append({
            "uid": uid, "location": locations[0] if locations else None, "locations": locations,
            "name": source.get("Name") if isinstance(source, dict) else None,
            "base_id": source.get("Code") if isinstance(source, dict) else None,
            "slot": None, "slot_index": locations[0].get("index") if locations else None,
            "type": source.get("Type") if isinstance(source, dict) else None, "type_name": None,
            "tier": source.get("TierIndex") if isinstance(source, dict) else None,
            "rarity": source.get("Rarity") if isinstance(source, dict) else None,
            "hero_restriction": source.get("BoundToCharacterCode") if isinstance(source, dict) else None,
            "affixes": affixes, "implicit_affixes": [], "flags": {}, "raw": source,
        })
    heroes = []
    for index, hero in enumerate(raw.get("heroes", [])):
        equipped = [item["uid"] for item in normalized_items if any(location.get("container") == "equipped" and location.get("hero_index") == index for location in item["locations"])]
        heroes.append({"id": hero.get("id"), "name": hero.get("name"), "level": None, "selected_loadout": hero.get("selected_loadout"), "equipped": equipped, "raw": hero.get("raw")})
    unresolved = {"unknown_affix_ids": sorted(unknown_codes), "extractor": raw.get("unresolved", [])}
    inventory = {
        "schema_version": 1, "source": {"save_file": raw.get("extractor", {}).get("save_file"), "save_version": raw.get("save", {}).get("version")},
        "heroes": heroes, "items": normalized_items, "counts": raw.get("counts", {}), "unresolved": unresolved,
    }
    return inventory, unresolved
