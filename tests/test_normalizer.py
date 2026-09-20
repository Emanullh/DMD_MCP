import tempfile
import unittest
from pathlib import Path

from dmd.normalizer import normalize


def raw_item(uid, affix_code):
    return {
        "extractor": {"version": "0.1.0", "save_file": "Slot_0.sav"},
        "save": {"version": 10},
        "heroes": [{"id": "Hero", "selected_loadout": 0, "raw": {}}],
        "items": [{"uid": uid, "raw": {"Code": "base", "Type": 4, "Rarity": 3, "TierIndex": 6, "Affixes": [{"Code": affix_code, "Levels": 17, "Enhanced": True}, {"Unknown": 1}]}, "locations": [{"container": "stash", "index": 3}]}],
        "counts": {"total_items": 1}, "unresolved": [],
    }


class NormalizerTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.catalog = Path(self.tempdir.name) / "affixes.csv"

    def tearDown(self):
        self.tempdir.cleanup()

    def write_catalog(self, text):
        self.catalog.write_text(text, encoding="utf-8")
        return self.catalog

    def test_missing_repository_id_gets_stable_hash_uid(self):
        raw = raw_item(None, "known")
        first, _ = normalize(raw, self.write_catalog("code;name\nknown;Known\n"))
        second, _ = normalize(raw, self.catalog)
        self.assertEqual(first["items"][0]["uid"], second["items"][0]["uid"])
        self.assertTrue(first["items"][0]["uid"].startswith("sha256:"))

    def test_unknown_affix_is_unresolved_without_invented_name(self):
        inventory, unresolved = normalize(raw_item("7", "new_affix"), self.write_catalog("code;name\nold;Old\n"))
        affix = inventory["items"][0]["affixes"][0]
        self.assertIsNone(affix["name"])
        self.assertTrue(affix["unresolved"])
        self.assertEqual(unresolved["unknown_affix_ids"], ["new_affix"])

    def test_preserves_unknown_affix_shape_and_does_not_claim_type_name(self):
        inventory, _ = normalize(raw_item("7", "known"), self.write_catalog("code;name\nknown;Known\n"))
        item = inventory["items"][0]
        self.assertIsNone(item["type_name"])
        self.assertEqual(item["raw"]["Affixes"][1], {"Unknown": 1})


if __name__ == "__main__":
    unittest.main()
