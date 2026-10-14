"""Every new host record is scanned without broadening the closed filename map."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import drive


class RecordKindsTests(unittest.TestCase):
    def test_public_config_and_actual_submission_are_unmaskable_host_records(self):
        for name in ("public-config.json", "turn-1.jsonl.launch.json", "turn-12.jsonl.launch.json"):
            with self.subTest(name=name):
                try:
                    kind = drive.record_kind([name])
                except drive.DriveRefused:
                    self.fail(f"actual host record has no scan classification: {name}")
                self.assertEqual(kind, "launch")
        self.assertEqual(drive.record_kind(["turn-1.jsonl"]), "stream")

    def test_nearby_names_and_nested_host_records_still_refuse(self):
        for parts in (["turn-0.jsonl.launch.json"], ["turn-01.jsonl.launch.json"],
                      ["turn--1.jsonl.launch.json"], ["turn-1.jsonl.launch.json.extra"],
                      ["turn-1.launch.json"], ["public-config.json.extra"],
                      ["other", "public-config.json"], ["other", "turn-1.jsonl.launch.json"]):
            with self.subTest(parts=parts), self.assertRaises(drive.DriveRefused):
                drive.record_kind(parts)


if __name__ == "__main__":
    unittest.main()
