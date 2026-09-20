# Death Must Die Read-Only Inventory Extractor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Build a dependency-free Python CLI that snapshots a Death Must Die save and emits faithful and normalized inventory JSON.

**Architecture:** save_reader owns discovery, snapshots, and raw-DEFLATE decoding. extractor finds ProfileState by type key and resolves current repository-backed item references. normalizer creates a stable LLM view, validator checks it, and the CLI owns only command parsing and project-local output.

**Tech Stack:** Python 3.11+ standard library: argparse, csv, hashlib, json, pathlib, shutil, tempfile, unittest, zlib.

**Spec:** docs/superpowers/specs/2026-09-20-dmd-readonly-inventory-design.md

## Global Constraints

- Read only .sav files; never write, move, rename, delete, or serialize a game save.
- Snapshot the input to a temporary external file with permission 0400 before parsing.
- Write output only below the project output directory; never include an absolute source path or username.
- Decode raw-DEFLATE UTF-8 JSON only; no BinaryFormatter, NRBF, or third-party decoder.
- Preserve unknown fields and unresolved fragments; do not infer current labels from the historical editor.
- Use repository IDs as UIDs, otherwise a deterministic SHA-256 UID.
- Treat the historical affix CSV as a reference catalog only.

## Review Focus

- BOM-prefixed raw DEFLATE must decode; a truncated stream fails without an inventory output. (Task 1)
- ProfileState must be found by type key even when it is not values[0]. (Task 2)
- StashJson must remain raw evidence but not double-count Stashes.StashJsons[0]. (Task 2)
- Missing UIDs and unknown affix codes must survive normalization as deterministic/unresolved data. (Task 3)
- Several default saves must demand explicit selection in non-interactive mode. (Task 4)

### Task 1: Safe discovery, snapshot, and decode

**Files:**
- Create: dmd/__init__.py
- Create: dmd/save_reader.py
- Create: tests/__init__.py
- Create: tests/helpers.py
- Create: tests/test_save_reader.py

**Interfaces:**
- Produces SaveReadError, discover_saves(directory: Path) -> list[Path], choose_save(save: str | None, directory: Path, stdin_isatty: bool) -> Path, snapshot_save(source: Path) -> Path, decode_save(snapshot: Path) -> dict, and redacted_source(source: Path) -> dict[str, str].
- Later tasks receive decoded dicts and redacted metadata only.

- [ ] **Step 1: Write failing tests**

    def test_noninteractive_multiple_saves_requires_explicit_path(self):
        with self.assertRaisesRegex(SaveReadError, "--save"):
            choose_save(None, self.saves_with("Slot_0.sav", "Slot_1.sav"), False)

    def test_decoder_accepts_bom_prefixed_raw_deflate(self):
        save = write_deflated(self.tmp / "Slot_0.sav", {"Version": 10})
        self.assertEqual(decode_save(save)["Version"], 10)

    def test_snapshot_is_readonly_and_source_metadata_is_unchanged(self):
        source = write_deflated(self.tmp / "Slot_0.sav", {"Version": 10})
        before = (source.stat().st_size, source.stat().st_mtime_ns)
        snapshot = snapshot_save(source)
        self.addCleanup(snapshot.unlink, missing_ok=True)
        self.assertEqual(snapshot.stat().st_mode & 0o777, 0o400)
        self.assertEqual((source.stat().st_size, source.stat().st_mtime_ns), before)

    def test_truncated_save_raises_clear_error(self):
        broken = self.tmp / "broken.sav"
        broken.write_bytes(b"\xec\xbd")
        with self.assertRaisesRegex(SaveReadError, "DEFLATE"):
            decode_save(broken)

- [ ] **Step 2: Verify RED**

Run: python3 -m unittest tests.test_save_reader -v

Expected: FAIL because dmd.save_reader does not exist.

- [ ] **Step 2a: Add the reusable synthetic-save fixture**

    def write_deflated(path: Path, value: dict) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        compressor = zlib.compressobj(wbits=-zlib.MAX_WBITS)
        payload = ("\ufeff" + json.dumps(value)).encode("utf-8")
        path.write_bytes(compressor.compress(payload) + compressor.flush())
        return path

- [ ] **Step 3: Implement the minimal reader**

    class SaveReadError(RuntimeError):
        pass

    def discover_saves(directory: Path) -> list[Path]:
        return sorted(path for path in directory.glob("*.sav") if path.is_file())

    def choose_save(save: str | None, directory: Path, stdin_isatty: bool) -> Path:
        if save:
            path = Path(save).expanduser()
            if path.is_file() and path.suffix.lower() == ".sav":
                return path
            raise SaveReadError(f"Save not found or invalid: {path}")
        saves = discover_saves(directory)
        if len(saves) == 1:
            return saves[0]
        if len(saves) > 1 and not stdin_isatty:
            raise SaveReadError("Multiple saves found; pass --save PATH.")
        raise SaveReadError("No save selected; pass --save PATH.")

    def decode_save(snapshot: Path) -> dict:
        try:
            value = json.loads(zlib.decompress(snapshot.read_bytes(), -zlib.MAX_WBITS).decode("utf-8-sig"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, zlib.error) as error:
            raise SaveReadError(f"Could not decode raw-DEFLATE save: {error}") from error
        if not isinstance(value, dict):
            raise SaveReadError("Save root must be an object.")
        return value

- [ ] **Step 4: Verify GREEN and commit**

Run: python3 -m unittest tests.test_save_reader -v && python3 -m unittest discover -v

Expected: PASS.

    git add dmd tests
    git commit -m "feat: safely read game saves"

### Task 2: Profile extraction and locations

**Files:**
- Create: dmd/extractor.py
- Create: tests/test_extractor.py
- Modify: tests/helpers.py

**Interfaces:**
- Consumes the decoded outer dict.
- Produces extract_raw(outer: dict, source: dict[str, str]) -> dict with profile_state, repository, containers, items, aliases, counts, and unresolved.
- Throws ExtractionError for an invalid outer structure, but records unknown data for valid ProfileStates.

- [ ] **Step 1: Write failing tests**

    def test_profile_is_selected_by_type_key_not_index(self):
        outer = make_outer([
            ("Death.Dialogues.Narrative+SaveableState", "{}"),
            ("Death.App.Profile+ProfileState", json.dumps(profile_with_repo([7], [8]))),
        ])
        raw = extract_raw(outer, {"filename": "Slot_0.sav"})
        self.assertEqual(raw["repository"]["entries"][0]["Id"]["_value"], 7)

    def test_selected_loadout_and_stash_references_resolve(self):
        raw = extract_raw(make_profile_outer(profile_with_repo([7], [8])), {"filename": "Slot_0.sav"})
        items = {item["uid"]: item for item in raw["items"]}
        self.assertEqual(items["7"]["locations"][0]["container"], "stash")
        self.assertEqual(items["8"]["locations"][0]["container"], "equipped")

    def test_stash_alias_is_preserved_but_not_counted_twice(self):
        raw = extract_raw(make_profile_outer(profile_with_repo([7], [])), {"filename": "Slot_0.sav"})
        self.assertTrue(raw["aliases"]["legacy_stash_json"])
        self.assertEqual(raw["counts"]["stash_items"], 1)

    def test_missing_repo_reference_and_future_field_are_not_lost(self):
        profile = profile_with_repo([999], [])
        profile["PlayerRepoState"]["Entries"][0]["Item"]["FutureField"] = {"kept": True}
        raw = extract_raw(make_profile_outer(profile), {"filename": "Slot_0.sav"})
        self.assertEqual(raw["items"][0]["raw"]["FutureField"], {"kept": True})
        self.assertEqual(raw["unresolved"][0]["kind"], "missing_repository_reference")

- [ ] **Step 2: Verify RED**

Run: python3 -m unittest tests.test_extractor -v

Expected: FAIL because dmd.extractor does not exist.

- [ ] **Step 2a: Add a minimal current-format fixture builder**

    def profile_with_repo(stash_ids, loadout_ids):
        entries = [
            {"Id": {"_value": item_id}, "Item": {"Code": f"item_{item_id}", "Type": 0,
             "Rarity": 0, "TierIndex": 0, "Affixes": [], "FutureField": None}}
            for item_id in sorted(set(stash_ids + loadout_ids + [7]))
        ]
        slots = lambda ids: [{"Id": {"_value": value}, "IsEmpty": False} for value in ids]
        page = {"Width": 1, "Height": 1, "Items": [], "ItemSlots": slots(stash_ids)}
        loadout = {"Items": [], "ItemSlots": slots(loadout_ids)}
        hero = {"CharacterCode": "Hero", "Json": json.dumps({"SelectedLoadout": 0,
            "EquipmentState": {"Items": [], "ItemSlots": []}, "LoadoutStates": [loadout]})}
        return {"PlayerRepoState": {"Entries": entries}, "InventoryData": [hero],
                "Stashes": {"StashJsons": [json.dumps({"Pages": [page]})]},
                "StashJson": json.dumps({"Pages": [page]}), "LibraryState": {"Items": [], "ItemSlots": []},
                "BackpackState": {"Items": [], "ItemSlots": []}, "StashState": {"Items": [], "ItemSlots": []}}

- [ ] **Step 3: Implement lookup and reference resolution**

    def find_profile(outer: dict) -> tuple[int, dict]:
        data = outer.get("serializedSaveData", {})
        keys, values = data.get("keys"), data.get("values")
        if not isinstance(keys, list) or not isinstance(values, list):
            raise ExtractionError("serializedSaveData needs keys and values lists.")
        for index, type_key in enumerate(keys):
            if isinstance(type_key, str) and "ProfileState" in type_key and index < len(values):
                return index, parse_json_value(values[index], "ProfileState")
        raise ExtractionError("ProfileState was not found.")

    def parse_json_value(value, label: str) -> dict:
        if not isinstance(value, str):
            raise ExtractionError(f"{label} must be JSON text.")
        try:
            decoded = json.loads(value.lstrip("\ufeff"))
        except json.JSONDecodeError as error:
            raise ExtractionError(f"Invalid {label} JSON: {error}") from error
        if not isinstance(decoded, dict):
            raise ExtractionError(f"{label} must decode to an object.")
        return decoded

    def repository_index(profile: dict) -> dict[int, dict]:
        entries = profile.get("PlayerRepoState", {}).get("Entries", [])
        return {
            entry["Id"]["_value"]: entry["Item"]
            for entry in entries
            if isinstance(entry, dict) and isinstance(entry.get("Id"), dict)
            and isinstance(entry["Id"].get("_value"), int) and isinstance(entry.get("Item"), dict)
        }

    def add_reference(index, items, unresolved, container, slot, ref_id, extra=None):
        if ref_id not in index:
            unresolved.append({"kind": "missing_repository_reference", "container": container, "index": slot, "id": ref_id})
            return
        item = items.setdefault(str(ref_id), {"uid": str(ref_id), "raw": index[ref_id], "locations": []})
        item["locations"].append({"container": container, "index": slot, **(extra or {})})

- [ ] **Step 4: Verify GREEN and commit**

Run: python3 -m unittest tests.test_extractor -v && python3 -m unittest discover -v

Expected: PASS.

    git add dmd/extractor.py tests/helpers.py tests/test_extractor.py
    git commit -m "feat: extract repository-backed inventory"

### Task 3: Normalization and validation

**Files:**
- Create: dmd/normalizer.py
- Create: dmd/validator.py
- Create: data/legacy_affixes.csv
- Create: tests/test_normalizer.py
- Create: tests/test_validator.py

**Interfaces:**
- Consumes raw extraction plus the bundled historical CSV.
- Produces normalize(raw: dict, catalog: Path) -> tuple[dict, dict] and validate_inventory(inventory: dict) -> list[str].
- inventory contains schema_version, source, heroes, items, unresolved, and counts; unresolved is a dedicated output document.

- [ ] **Step 1: Write failing tests**

    def test_missing_repository_id_gets_stable_hash_uid(self):
        raw = raw_item_without_uid(container="stash", index=3)
        first, _ = normalize(raw, self.catalog(["old"]))
        second, _ = normalize(raw, self.catalog(["old"]))
        self.assertEqual(first["items"][0]["uid"], second["items"][0]["uid"])
        self.assertTrue(first["items"][0]["uid"].startswith("sha256:"))

    def test_unknown_affix_is_unresolved_without_invented_name(self):
        inventory, unresolved = normalize(raw_with_affix("new_affix"), self.catalog(["old_affix"]))
        affix = inventory["items"][0]["affixes"][0]
        self.assertIsNone(affix["name"])
        self.assertTrue(affix["unresolved"])
        self.assertEqual(unresolved["unknown_affix_ids"], ["new_affix"])

    def test_validator_reports_duplicate_uid_and_bad_total(self):
        errors = validate_inventory({"items": [{"uid": "7"}, {"uid": "7"}], "counts": {"total_items": 3}})
        self.assertIn("duplicate uid: 7", errors)
        self.assertIn("total_items does not equal item list length", errors)

- [ ] **Step 2: Verify RED**

Run: python3 -m unittest tests.test_normalizer tests.test_validator -v

Expected: FAIL because normalizer and validator do not exist.

- [ ] **Step 3: Implement conservative normalized values**

    def fallback_uid(raw: dict, location: dict) -> str:
        payload = json.dumps({"location": location, "raw": raw}, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return "sha256:" + hashlib.sha256(payload.encode()).hexdigest()

    def normalize_affix(value: dict, catalog: dict[str, str]) -> dict:
        code = value.get("Code")
        return {
            "id": code, "name": catalog.get(code), "value": value.get("Levels"),
            "enhanced": value.get("Enhanced"), "implicit": None,
            "unresolved": code not in catalog, "raw": value,
        }

    def validate_inventory(inventory: dict) -> list[str]:
        errors, seen = [], set()
        for item in inventory.get("items", []):
            uid = item.get("uid")
            if uid in seen:
                errors.append(f"duplicate uid: {uid}")
            seen.add(uid)
        if inventory.get("counts", {}).get("total_items") != len(inventory.get("items", [])):
            errors.append("total_items does not equal item list length")
        return errors

- [ ] **Step 4: Verify GREEN and commit**

Run: python3 -m unittest tests.test_normalizer tests.test_validator -v && python3 -m unittest discover -v

Expected: PASS.

    git add dmd data tests
    git commit -m "feat: normalize and validate inventory"

### Task 4: CLI, docs, and end-to-end verification

**Files:**
- Create: dmd_inventory.py
- Create: tests/test_cli.py
- Create: docs/save-format.md
- Create: README.md
- Create: requirements.txt

**Interfaces:**
- Consumes Tasks 1-3.
- Produces dump [--save PATH] [--verbose] [--debug-dump], inspect --save PATH, and validate output/inventory.json.
- dump writes inventory_raw.json, inventory.json, unresolved.json, and optional debug_structure.json only to its output argument (default project output).

- [ ] **Step 1: Write failing CLI tests**

    def test_dump_writes_only_project_output_and_redacts_source_path(self):
        save = write_current_fixture(self.tmp / "saves" / "Slot_0.sav")
        result = run_cli("dump", "--save", str(save), "--output", str(self.tmp / "output"))
        self.assertEqual(result.returncode, 0, result.stderr)
        inventory = (self.tmp / "output" / "inventory.json").read_text()
        self.assertNotIn(str(save.parent), inventory)
        self.assertTrue((self.tmp / "output" / "inventory_raw.json").is_file())
        self.assertTrue((self.tmp / "output" / "unresolved.json").is_file())
        self.assertFalse(any(save.parent.glob("*.json")))

    def test_inspect_creates_no_output_directory(self):
        save = write_current_fixture(self.tmp / "Slot_0.sav")
        result = run_cli("inspect", "--save", str(save), cwd=self.tmp)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.tmp / "output").exists())

- [ ] **Step 2: Verify RED**

Run: python3 -m unittest tests.test_cli -v

Expected: FAIL because dmd_inventory.py does not exist.

- [ ] **Step 3: Implement dispatch and output writer**

    def write_json(output_dir: Path, filename: str, value: dict) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        target = output_dir / filename
        temporary = target.with_suffix(target.suffix + ".tmp")
        temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        temporary.replace(target)
        return target

    def main(argv=None) -> int:
        args = build_parser().parse_args(argv)
        if args.command == "validate":
            return run_validate(args)
        return run_save_command(args)

- [ ] **Step 4: Add documents**

README must give four macOS steps: install Python 3.11+, close the game, run python3 dmd_inventory.py dump, and find the three outputs. It must explain raw, normalized, and unresolved output.

docs/save-format.md must document raw-DEFLATE JSON, ProfileState lookup by type key, old direct-item storage versus current PlayerRepoState references, selected loadouts, duplicated StashJson, historical-only affix names, and the explicit absence of NRBF.

requirements.txt contains exactly: # No third-party dependencies.

- [ ] **Step 5: Verify GREEN, run smoke test, and commit**

Run: python3 -m unittest discover -v && python3 -m compileall -q dmd dmd_inventory.py && python3 dmd_inventory.py dump --save /tmp/dmd-save-snapshot.XXXXXX.sav --output /tmp/dmd-inventory-smoke-output && python3 dmd_inventory.py validate /tmp/dmd-inventory-smoke-output/inventory.json

Expected: all tests PASS, compileall is silent, dump succeeds from the read-only snapshot, validation succeeds, and no file is written beside the snapshot.

    git add dmd_inventory.py docs README.md requirements.txt tests
    git commit -m "feat: add read-only inventory CLI"
