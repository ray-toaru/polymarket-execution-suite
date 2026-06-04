from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import validate_contracts_governance as module
from validate_contracts_support import ContractValidationError


class ValidateContractsGovernanceTests(unittest.TestCase):
    def test_validate_absent_tokens_rejects_forbidden_token(self) -> None:
        with self.assertRaises(ContractValidationError) as ctx:
            module.validate_absent_tokens("safe text with raw_signature=", "deployment template", ["raw_signature="])
        self.assertIn("deployment template contains forbidden token: raw_signature=", str(ctx.exception))

    def test_require_existing_paths_reports_missing_relative_path(self) -> None:
        missing = ROOT / "does-not-exist-governance-test.json"
        with self.assertRaises(ContractValidationError) as ctx:
            module.require_existing_paths([missing], "governance fixture")
        self.assertIn("governance fixture missing: does-not-exist-governance-test.json", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
