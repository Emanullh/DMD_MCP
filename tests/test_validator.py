import unittest

from dmd.validator import validate_inventory


class ValidatorTests(unittest.TestCase):
    def test_reports_duplicate_uid_and_bad_total(self):
        errors = validate_inventory({"items": [{"uid": "7"}, {"uid": "7"}], "counts": {"total_items": 3}})
        self.assertIn("duplicate uid: 7", errors)
        self.assertIn("total_items does not equal item list length", errors)

    def test_reports_unresolved_item_location(self):
        errors = validate_inventory({"items": [{"uid": "7", "location": None}], "counts": {"total_items": 1}})
        self.assertIn("item 7 has no location", errors)


if __name__ == "__main__":
    unittest.main()
