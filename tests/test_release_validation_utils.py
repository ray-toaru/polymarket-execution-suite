import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "release_validation_utils.py"
DIST_INDEX_SCRIPT = ROOT / "scripts" / "check_dist_index.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ReleaseValidationUtilsTests(unittest.TestCase):
    def test_sha256_file_and_load_json_object_are_shared_root_script_helpers(self):
        utils = load_module(SCRIPT, "release_validation_utils")
        dist_index = load_module(DIST_INDEX_SCRIPT, "check_dist_index")
        with tempfile.TemporaryDirectory() as tmp_name:
            path = Path(tmp_name) / "sample.json"
            path.write_text(json.dumps({"ok": True}) + "\n")

            self.assertEqual(utils.sha256_file(path), dist_index.sha256(path))
            self.assertEqual(utils.load_json_object(path), {"ok": True})

    def test_load_json_object_rejects_non_object_json(self):
        utils = load_module(SCRIPT, "release_validation_utils")
        with tempfile.TemporaryDirectory() as tmp_name:
            path = Path(tmp_name) / "sample.json"
            path.write_text("[]\n")

            with self.assertRaisesRegex(ValueError, "must contain a JSON object"):
                utils.load_json_object(path)


if __name__ == "__main__":
    unittest.main()
