import copy
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "polymarket-execution-engine" / "validation" / "validate_controlled_canary_external_references.py"


def load_module():
    spec = importlib.util.spec_from_file_location("validate_controlled_canary_external_references", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ValidateControlledCanaryExternalReferencesTests(unittest.TestCase):
    def setUp(self):
        self.module = load_module()
        self.example = json.loads(self.module.EXAMPLE.read_text())

    def test_rejects_missing_reference_sha256s(self):
        data = copy.deepcopy(self.example)
        del data["reference_sha256s"]["secret_custody"]["provider_ref"]

        failures = self.module.validate_shape(data, "candidate", allow_placeholders=False)

        self.assertIn("candidate: reference_sha256s.secret_custody.provider_ref must be 64-hex", failures)

    def test_accepts_hash_bound_external_reference_example(self):
        self.assertEqual(self.module.validate_shape(self.example, "candidate", allow_placeholders=False), [])


if __name__ == "__main__":
    unittest.main()
