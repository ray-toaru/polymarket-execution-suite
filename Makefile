PYTHON ?= python
HERMES_PROFILE ?= local

.PHONY: check-local check-hermes check-package check-current-gates clean-local

check-local:
	$(PYTHON) scripts/check_version_consistency.py
	$(PYTHON) scripts/validate_contracts.py
	$(PYTHON) scripts/check_v28_production_live_candidate.py
	$(PYTHON) -m unittest discover -s tests -p "test_*.py"
	$(PYTHON) -m compileall -q hermes-polymarket-executor-adapter/src scripts tests polymarket-execution-engine/validation
	$(PYTHON) polymarket-execution-engine/validation/check_docs_evidence_governance.py

check-hermes:
	HERMES_PROFILE=$(HERMES_PROFILE) PYTHONPATH=hermes-polymarket-executor-adapter/src $(PYTHON) -m pytest -q hermes-polymarket-executor-adapter/tests
	HERMES_PROFILE=$(HERMES_PROFILE) $(PYTHON) scripts/check_hermes_profile_plugin.py --profile-cmd "$(HERMES_PROFILE)"

check-package:
	$(PYTHON) scripts/clean_local_artifacts.py
	$(PYTHON) polymarket-execution-engine/scripts/check_release_hygiene.py . --dev-worktree

check-current-gates:
	cd polymarket-execution-engine && ./validation/run_current_gates.sh

clean-local:
	$(PYTHON) scripts/clean_local_artifacts.py
