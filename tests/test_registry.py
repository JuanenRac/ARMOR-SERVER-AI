import hashlib
import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, "src")
from armor_server_ai import EngineRegistryError, discover_engines


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = pathlib.Path(self._tmp.name)

    def engines(self, day=b"day-engine", night=b"night-engine"):
        (self.root / "daylight.engine").write_bytes(day)
        (self.root / "low_light.engine").write_bytes(night)

    def manifest(self, day=b"day-engine", night=b"night-engine"):
        (self.root / "engines.json").write_text(json.dumps({"daylight": sha(day), "low_light": sha(night)}), encoding="utf-8")

    def test_requires_both_non_empty_engines(self):
        (self.root / "daylight.engine").write_bytes(b"x")
        with self.assertRaises(EngineRegistryError):
            discover_engines(self.root)
        (self.root / "low_light.engine").write_bytes(b"")
        with self.assertRaises(EngineRegistryError):
            discover_engines(self.root)

    def test_a_missing_directory_is_refused(self):
        with self.assertRaises(EngineRegistryError):
            discover_engines(self.root / "absent")

    def test_without_a_manifest_the_engines_are_accepted_but_unverified(self):
        self.engines()
        self.assertFalse(discover_engines(self.root).verified)

    def test_a_matching_manifest_verifies_the_engines(self):
        self.engines()
        self.manifest()
        found = discover_engines(self.root)
        self.assertTrue(found.verified)
        self.assertEqual(found.daylight.name, "daylight.engine")

    def test_a_swapped_engine_is_refused(self):
        self.engines()
        self.manifest()
        (self.root / "low_light.engine").write_bytes(b"tampered")
        with self.assertRaises(EngineRegistryError) as caught:
            discover_engines(self.root)
        self.assertIn("low_light.engine", str(caught.exception))

    def test_a_malformed_manifest_is_refused_not_ignored(self):
        self.engines()
        for content in ("{not json", "[]", json.dumps({"daylight": sha(b"x")}), json.dumps({"daylight": "abc", "low_light": "def"}),
                        json.dumps({"daylight": sha(b"x"), "low_light": sha(b"y"), "extra": "z"}), json.dumps({"daylight": sha(b"x").upper(), "low_light": sha(b"y")})):
            (self.root / "engines.json").write_text(content, encoding="utf-8")
            with self.assertRaises(EngineRegistryError, msg=content):
                discover_engines(self.root)


if __name__ == "__main__":
    unittest.main()
