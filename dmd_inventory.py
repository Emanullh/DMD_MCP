#!/usr/bin/env python3
"""Read-only Death Must Die inventory extractor."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import zipfile

from dmd.extractor import ExtractionError, extract_raw
from dmd.normalizer import normalize
from dmd.save_reader import DEFAULT_SAVE_DIRECTORY, SaveReadError, choose_save, decode_save, redacted_source, snapshot_save
from dmd.validator import validate_inventory


ROOT = Path(__file__).resolve().parent


def write_json(output_dir: Path, filename: str, value: dict) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / filename
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(target)
    return target


def write_inventory_archive(output_dir: Path) -> Path:
    """Replace the previous bundle with the two LLM-facing JSON files."""
    target = output_dir / "inventory_bundle.zip"
    temporary = target.with_suffix(".zip.tmp")
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for filename in ("inventory.json", "unresolved.json"):
            bundle.write(output_dir / filename, arcname=filename)
    temporary.replace(target)
    return target


def game_running() -> bool:
    if sys.platform == "win32":
        return False
    try:
        return subprocess.run(["pgrep", "-f", "Death Must Die"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
    except OSError:
        return False


def load(args):
    source = choose_save(args.save, DEFAULT_SAVE_DIRECTORY, sys.stdin.isatty())
    snapshot = snapshot_save(source)
    try:
        outer = decode_save(snapshot)
        raw = extract_raw(outer, redacted_source(source))
    finally:
        snapshot.chmod(0o600)
        snapshot.unlink(missing_ok=True)
    return source, outer, raw


def run_dump(args) -> int:
    source, outer, raw = load(args)
    output = Path(args.output).expanduser()
    if output.resolve().is_relative_to(source.parent.resolve()):
        raise SaveReadError("Output directory must be outside the game save directory.")
    inventory, unresolved = normalize(raw, ROOT / "data/legacy_affixes.csv")
    errors = validate_inventory(inventory)
    if errors:
        raise SaveReadError("Validation failed: " + "; ".join(errors))
    write_json(output, "inventory_raw.json", raw)
    write_json(output, "inventory.json", inventory)
    write_json(output, "unresolved.json", unresolved)
    archive = write_inventory_archive(output)
    if args.debug_dump:
        write_json(output, "debug_structure.json", {"root_keys": sorted(outer), "profile_keys": sorted(raw["profile_state"]), "container_keys": sorted(raw["containers"]), "aliases": raw["aliases"]})
    counts = raw["counts"]
    print(f"Save: {source.name}")
    print(f"Heroes found: {len(raw['heroes'])}")
    print(f"Equipped items: {counts['equipped_items']}")
    print(f"Stash items: {counts['stash_items']}")
    print(f"Total items: {counts['total_items']}")
    print(f"Affixes parsed: {sum(len(item['raw'].get('Affixes', [])) for item in raw['items'])}")
    print(f"Unknown affix IDs: {len(unresolved['unknown_affix_ids'])}")
    print(f"Output: {output / 'inventory_raw.json'}")
    print(f"Archive: {archive}")
    return 0


def run_inspect(args) -> int:
    _, outer, raw = load(args)
    print(f"Save format: raw DEFLATE JSON; version {outer.get('Version')}")
    print(f"Root objects: {', '.join(sorted(outer))}")
    print("ProfileState detected: yes")
    print(f"Repository items: {len(raw['repository']['entries'])}")
    print(f"Candidate item collections: {', '.join(sorted(raw['containers']))}")
    print(f"Counts: {json.dumps(raw['counts'], sort_keys=True)}")
    print(f"Unknown structures: {len(raw['unresolved'])}")
    return 0


def run_validate(args) -> int:
    with Path(args.inventory).open(encoding="utf-8") as handle:
        errors = validate_inventory(json.load(handle))
    if errors:
        print("Validation failed:\n" + "\n".join(errors), file=sys.stderr)
        return 1
    print("Validation passed.")
    return 0


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="command", required=True)
    for name in ("dump", "inspect"):
        command = commands.add_parser(name)
        command.add_argument("--save")
        command.add_argument("--verbose", action="store_true")
    dump = commands.choices["dump"]
    dump.add_argument("--debug-dump", action="store_true")
    dump.add_argument("--output", default=str(ROOT / "output"))
    validate = commands.add_parser("validate")
    validate.add_argument("inventory")
    return result


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "dump":
            if game_running():
                print("Warning: Death Must Die appears to be running; close it for a consistent snapshot.", file=sys.stderr)
            return run_dump(args)
        if args.command == "inspect":
            return run_inspect(args)
        return run_validate(args)
    except (ExtractionError, SaveReadError, OSError, json.JSONDecodeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
