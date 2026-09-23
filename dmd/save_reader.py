"""Safe save discovery, snapshotting, and raw-DEFLATE JSON decoding."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Callable
import zlib


def default_save_directory(platform: str = sys.platform) -> Path:
    directory = "AppData/LocalLow/Realm Archive/Death Must Die/Saves" if platform == "win32" else "Library/Application Support/Realm Archive/Death Must Die/Saves"
    return Path.home() / directory


DEFAULT_SAVE_DIRECTORY = default_save_directory()


class SaveReadError(RuntimeError):
    """A save cannot be safely selected, copied, or decoded."""


def discover_saves(directory: Path) -> list[Path]:
    """Return only regular .sav files in deterministic order."""
    if not directory.is_dir():
        return []
    return sorted(path for path in directory.glob("*.sav") if path.is_file())


def choose_save(
    save: str | None,
    directory: Path = DEFAULT_SAVE_DIRECTORY,
    stdin_isatty: bool = False,
    input_fn: Callable[[str], str] = input,
) -> Path:
    """Select one save without guessing when more than one exists."""
    if save:
        path = Path(save).expanduser()
        if path.is_file() and path.suffix.lower() == ".sav":
            return path
        raise SaveReadError(f"Save not found or not a .sav file: {path}")

    saves = discover_saves(directory)
    if len(saves) == 1:
        return saves[0]
    if not saves:
        raise SaveReadError(f"No .sav files found. Pass --save PATH.")
    if not stdin_isatty:
        raise SaveReadError("Multiple saves found; pass --save PATH.")

    choices = "\n".join(f"{index}: {path.name}" for index, path in enumerate(saves, 1))
    try:
        selection = int(input_fn(f"Multiple saves found:\n{choices}\nSelect a save number: "))
        return saves[selection - 1]
    except (IndexError, ValueError) as error:
        raise SaveReadError("Invalid save selection; pass --save PATH.") from error


def snapshot_save(source: Path) -> Path:
    """Copy a save outside its directory and restrict the copy to read-only."""
    if not source.is_file():
        raise SaveReadError(f"Save not found: {source}")
    handle = tempfile.NamedTemporaryFile(prefix="dmd-inventory-", suffix=".sav", delete=False)
    handle.close()
    snapshot = Path(handle.name)
    try:
        shutil.copyfile(source, snapshot)
        snapshot.chmod(0o400)
    except OSError as error:
        snapshot.unlink(missing_ok=True)
        raise SaveReadError(f"Could not create read-only save snapshot: {error}") from error
    return snapshot


def decode_save(snapshot: Path) -> dict:
    """Decode the game's raw-DEFLATE UTF-8 JSON without executing data."""
    try:
        value = json.loads(zlib.decompress(snapshot.read_bytes(), -zlib.MAX_WBITS).decode("utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, zlib.error) as error:
        raise SaveReadError(f"Could not decode raw-DEFLATE save: {error}") from error
    if not isinstance(value, dict):
        raise SaveReadError("Save root must be a JSON object.")
    return value


def redacted_source(source: Path) -> dict[str, str]:
    """Metadata safe to include in output JSON."""
    return {"save_file": source.name}
