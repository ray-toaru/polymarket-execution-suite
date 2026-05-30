from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "polymarket-execution-engine" / "validation" / "check_live_submit_guard.py"


def load_module():
    spec = importlib.util.spec_from_file_location("check_live_submit_guard", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class CheckLiveSubmitGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_module()

    def test_public_contract_terms_reports_present_terms(self) -> None:
        found = self.module.public_contract_terms("signed_payload and post_order are here")
        self.assertEqual(found, {"signed_payload", "post_order"})

    def test_validate_required_tokens_reports_missing_tokens(self) -> None:
        failures = self.module.validate_required_tokens(
            "alpha only",
            tokens=["alpha", "beta"],
            failure_prefix="missing token",
        )
        self.assertEqual(failures, ["missing token: beta"])

    def test_validate_allowed_call_sites_reports_unexpected_site(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            allowed = root / "a.rs"
            extra = root / "b.rs"
            allowed.write_text("client.post_order(x)")
            extra.write_text("client.post_order(y)")
            failures = self.module.validate_allowed_call_sites(
                paths=[allowed, extra],
                pattern=self.module.POST_ORDER_CALL,
                allowed_paths=[allowed],
                relative_root=root,
                failure_prefix="bad call sites",
            )
        self.assertEqual(failures, ["bad call sites; found a.rs, b.rs"])

    def test_validate_idempotency_guard_tokens_reports_missing_token(self) -> None:
        fake_path = Path("/repo/idempotency.rs")
        with mock.patch.object(
            self.module,
            "REQUIRED_IDEMPOTENCY_TOKENS",
            [(fake_path, ["IDEMPOTENCY_LEASE_SECS", "owner_token"])],
        ), mock.patch("pathlib.Path.read_text", autospec=True, return_value="IDEMPOTENCY_LEASE_SECS"), mock.patch.object(
            self.module,
            "ROOT",
            Path("/repo"),
        ):
            failures = self.module.validate_idempotency_guard_tokens()
        self.assertEqual(
            failures,
            ["idempotency lease/owner guard missing token in idempotency.rs: owner_token"],
        )


if __name__ == "__main__":
    unittest.main()
