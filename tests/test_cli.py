import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.helpers import profile_outer, profile_with_repo, write_deflated


ROOT = Path(__file__).resolve().parents[1]


class CliTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.directory = Path(self.tempdir.name)

    def tearDown(self):
        self.tempdir.cleanup()

    def run_cli(self, *args, cwd=None):
        return subprocess.run([sys.executable, str(ROOT / "dmd_inventory.py"), *args], text=True, capture_output=True, cwd=cwd or ROOT)

    def fixture(self, path):
        return write_deflated(path, profile_outer(profile_with_repo([7], [8])))

    def test_dump_writes_only_output_and_redacts_source_path(self):
        save = self.fixture(self.directory / "saves" / "Slot_0.sav")
        output = self.directory / "output"
        result = self.run_cli("dump", "--save", str(save), "--output", str(output))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((output / "inventory_raw.json").is_file())
        self.assertTrue((output / "inventory.json").is_file())
        self.assertTrue((output / "unresolved.json").is_file())
        self.assertNotIn(str(save.parent), (output / "inventory.json").read_text())
        self.assertFalse(any(save.parent.glob("*.json")))

    def test_inspect_does_not_create_default_output(self):
        save = self.fixture(self.directory / "Slot_0.sav")
        result = self.run_cli("inspect", "--save", str(save), cwd=self.directory)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ProfileState detected: yes", result.stdout)
        self.assertFalse((self.directory / "output").exists())

    def test_validate_reports_valid_inventory(self):
        inventory = self.directory / "inventory.json"
        inventory.write_text(json.dumps({"items": [{"uid": "7", "location": {"container": "stash"}}], "counts": {"total_items": 1}}))
        result = self.run_cli("validate", str(inventory))
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
