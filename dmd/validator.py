"""Small validation checks for normalized inventory output."""

from typing import Any


def validate_inventory(inventory: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    for item in inventory.get("items", []):
        uid = item.get("uid")
        if uid in seen:
            errors.append(f"duplicate uid: {uid}")
        seen.add(uid)
        if item.get("location") is None:
            errors.append(f"item {uid} has no location")
    if inventory.get("counts", {}).get("total_items") != len(inventory.get("items", [])):
        errors.append("total_items does not equal item list length")
    return errors
