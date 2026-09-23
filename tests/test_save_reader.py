import stat
import tempfile
import unittest
from pathlib import Path

import dmd.save_reader as save_reader
from dmd.save_reader import (
    SaveReadError,
    choose_save,
    decode_save,
    discover_saves,
    redacted_source,
    snapshot_save,
)
from tests.helpers import write_deflated


class SaveReaderTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.directory = Path(self.tempdir.name)

    def tearDown(self):
        self.tempdir.cleanup()

    def test_discovers_only_save_files_in_name_order(self):
        (self.directory / "Slot_1.sav").write_bytes(b"1")
        (self.directory / "Slot_0.sav").write_bytes(b"0")
        (self.directory / "notes.txt").write_text("ignore")
        self.assertEqual([path.name for path in discover_saves(self.directory)], ["Slot_0.sav", "Slot_1.sav"])

    def test_uses_locallow_save_directory_on_windows(self):
        directory_for = getattr(save_reader, "default_save_directory", lambda platform: None)
        self.assertEqual(
            directory_for("win32"),
            Path.home() / "AppData/LocalLow/Realm Archive/Death Must Die/Saves",
        )

    def test_selects_the_only_discovered_save(self):
        save = (self.directory / "Slot_0.sav")
        save.write_bytes(b"x")
        self.assertEqual(choose_save(None, self.directory, stdin_isatty=False), save)

    def test_requires_explicit_save_for_multiple_noninteractive_files(self):
        (self.directory / "Slot_0.sav").write_bytes(b"x")
        (self.directory / "Slot_1.sav").write_bytes(b"x")
        with self.assertRaisesRegex(SaveReadError, "--save"):
            choose_save(None, self.directory, stdin_isatty=False)

    def test_snapshot_is_read_only_and_does_not_change_source_metadata(self):
        source = write_deflated(self.directory / "Slot_0.sav", {"Version": 10})
        before = (source.stat().st_size, source.stat().st_mtime_ns)
        snapshot = snapshot_save(source)
        self.addCleanup(snapshot.unlink, missing_ok=True)
        self.addCleanup(snapshot.chmod, stat.S_IWRITE)
        self.assertNotEqual(snapshot.parent, source.parent)
        self.assertEqual(snapshot.stat().st_mode & stat.S_IWRITE, 0)
        self.assertEqual((source.stat().st_size, source.stat().st_mtime_ns), before)

    def test_decodes_bom_prefixed_raw_deflate_json(self):
        save = write_deflated(self.directory / "Slot_0.sav", {"Version": 10})
        self.assertEqual(decode_save(save), {"Version": 10})

    def test_rejects_truncated_save(self):
        broken = self.directory / "broken.sav"
        broken.write_bytes(b"\xec\xbd")
        with self.assertRaisesRegex(SaveReadError, "DEFLATE"):
            decode_save(broken)

    def test_redacts_path_to_filename_only(self):
        self.assertEqual(redacted_source(Path("/Users/name/Library/Slot_0.sav")), {"save_file": "Slot_0.sav"})
