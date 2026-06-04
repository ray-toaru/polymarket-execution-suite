from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import validate_contracts_support as module


class ValidateContractsSupportTests(unittest.TestCase):
    def test_extract_string_literal_prefix_reads_first_route_argument(self) -> None:
        self.assertEqual(
            module.extract_string_literal_prefix('   "/v1/admin/:account_id", get(handler)'),
            "/v1/admin/:account_id",
        )
        self.assertIsNone(module.extract_string_literal_prefix("build_path(), get(handler)"))

    def test_find_matching_delimiter_tracks_nested_blocks(self) -> None:
        text = "fn demo() { if ready { ok(); } else { retry(); } }"
        start = text.index("{")
        end = module.find_matching_delimiter(text, start, "{", "}")
        self.assertEqual(text[end], "}")
        self.assertEqual(text[start : end + 1], "{ if ready { ok(); } else { retry(); } }")

    def test_rust_routes_parses_route_calls_without_regex_shortcuts(self) -> None:
        source = """
        Router::new()
            .route(
                "/v1/admin/:account_id",
                get(admin_handler)
            )
            .route(build_dynamic_path(), get(dynamic_handler))
            .route("/v1/submissions", post(submit_plan))
        """
        with mock.patch.object(module, "rust_source_text", return_value=source):
            self.assertEqual(
                module.rust_routes(),
                {"/v1/admin/{account_id}", "/v1/submissions"},
            )

    def test_rust_handler_body_returns_balanced_async_fn_block(self) -> None:
        source = """
        async fn submit_plan() -> ApiResult<()> {
            if ready {
                do_submit();
            } else {
                retry_submit();
            }
        }

        async fn next_handler() -> ApiResult<()> {
            do_next();
        }
        """
        with mock.patch.object(module, "rust_source_text", return_value=source):
            body = module.rust_handler_body("submit_plan")
        self.assertIn("retry_submit();", body)
        self.assertNotIn("next_handler", body)


if __name__ == "__main__":
    unittest.main()
