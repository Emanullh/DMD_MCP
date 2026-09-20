import json
import unittest

from dmd.extractor import extract_raw
from tests.helpers import make_outer, profile_outer, profile_with_repo


class ExtractorTests(unittest.TestCase):
    def test_selects_profile_by_type_key_not_values_zero(self):
        outer = make_outer([
            ("Death.Dialogues.Narrative+SaveableState", "{}"),
            ("Death.App.Profile+ProfileState, Death", json.dumps(profile_with_repo([7], [8]))),
        ])
        raw = extract_raw(outer, {"save_file": "Slot_0.sav"})
        self.assertEqual(raw["repository"]["entries"][0]["Id"]["_value"], 7)

    def test_resolves_stash_and_selected_loadout_references(self):
        raw = extract_raw(profile_outer(profile_with_repo([7], [8])), {"save_file": "Slot_0.sav"})
        items = {item["uid"]: item for item in raw["items"]}
        self.assertEqual(items["7"]["locations"][0]["container"], "stash")
        self.assertEqual(items["8"]["locations"][0]["container"], "equipped")

    def test_keeps_stash_alias_without_double_counting(self):
        raw = extract_raw(profile_outer(profile_with_repo([7], [])), {"save_file": "Slot_0.sav"})
        self.assertTrue(raw["aliases"]["legacy_stash_json"])
        self.assertEqual(raw["counts"]["stash_items"], 1)
        self.assertEqual(raw["counts"]["total_items"], 1)

    def test_keeps_unknown_item_fields_and_missing_references(self):
        profile = profile_with_repo([999], [], repo_ids=[7])
        profile["PlayerRepoState"]["Entries"][0]["Item"]["FutureField"] = {"kept": True}
        raw = extract_raw(profile_outer(profile), {"save_file": "Slot_0.sav"})
        self.assertEqual(raw["items"][0]["raw"]["FutureField"], {"kept": True})
        self.assertEqual(raw["unresolved"][0]["kind"], "missing_repository_reference")


if __name__ == "__main__":
    unittest.main()
