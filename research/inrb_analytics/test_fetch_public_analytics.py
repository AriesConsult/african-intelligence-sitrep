"""Offline safety/syntax smoke tests for the manual INRB public acquisition module."""
import importlib.util
import io
import pathlib
import tempfile
import unittest

SCRIPT = pathlib.Path(__file__).with_name("fetch_public_analytics.py")
spec = importlib.util.spec_from_file_location("inrb_acquire", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class AcquisitionTests(unittest.TestCase):
    def test_csv_structure(self):
        x = module.inspect_bytes("ct_weekly_national", b"week,cases\n20,1\n21,\n")
        self.assertEqual(x["rows"], 2)
        self.assertEqual(x["empty_by_column"]["cases"], 1)
    def test_malformed_csv(self):
        with self.assertRaises(ValueError):
            module.inspect_bytes("ct_weekly_national", b"week,week\n20,1\n")
    def test_json_structure(self):
        self.assertEqual(module.inspect_bytes("ct_dashboard_meta", b'{"source":"public"}')["type"], "json")
    def test_rejects_unknown_repo_before_io(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                module.collect(folder, "2026-11-22", {"OtherRepo": "a"*40})
    def test_requires_commit_pins(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                module.collect(folder, "2026-11-22", {})

if __name__ == "__main__":
    unittest.main()
