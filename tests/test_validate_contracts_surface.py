from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import validate_contracts_surface as module


class ValidateContractsSurfaceTests(unittest.TestCase):
    def test_iter_json_strings_walks_nested_values_and_keys(self) -> None:
        payload = {"a": ["x", {"b": "y"}], "c": {"d": 1}}
        self.assertEqual(set(module.iter_json_strings(payload)), {"a", "x", "b", "y", "c", "d"})

    def test_validate_no_public_forbidden_tokens_uses_structural_spec_scan(self) -> None:
        spec = {
            "components": {
                "schemas": {
                    "Example": {
                        "type": "object",
                        "properties": {"danger": {"type": "string", "description": "signed_payload"}},
                    }
                }
            }
        }
        with self.assertRaises(SystemExit) as ctx:
            module.validate_no_public_forbidden_tokens(spec)
        self.assertIn("forbidden token in public OpenAPI: signed_payload", str(ctx.exception))

    def test_validate_no_public_forbidden_tokens_scans_control_sources(self) -> None:
        fake_file = mock.Mock()
        fake_file.read_text.return_value = "private_key"
        fake_file.relative_to.return_value = Path("hermes-polymarket-executor-adapter/src/fake.py")
        fake_src = mock.Mock()
        fake_src.rglob.return_value = [fake_file]
        fake_control = mock.Mock()
        fake_control.__truediv__ = mock.Mock(return_value=fake_src)
        fake_control.parent = ROOT
        with mock.patch.object(module, "CONTROL", fake_control):
            with self.assertRaises(SystemExit) as ctx:
                module.validate_no_public_forbidden_tokens({"openapi": "clean"})
        self.assertIn("forbidden token private_key in control package", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
