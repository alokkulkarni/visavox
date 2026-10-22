# Visavox developer commands (CLAUDE.md). Python via uv.
PYTEST_ARGS ?=

.PHONY: setup lint typecheck test test-contract test-local test-media security licence-check ci

setup:
	uv sync --all-packages

lint:
	uv run ruff check .
	uv run ruff format --check .

typecheck:
	uv run mypy tools/licence_gate/src spikes/s3_livekit_contract/src

test:
	uv run pytest -m "not contract and not media and not e2e and not load and not local" --cov --cov-report=term-missing

# Needs a LiveKit server: LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET (defaults: ws://localhost:7880, devkey, secret).
test-contract:
	uv run pytest spikes tests/contract -m "not media and not e2e and not load" --cov=spikes --cov-report=term-missing --cov-fail-under=90 $(PYTEST_ARGS)

# Smoke tests against the running local cell (NFR-O5). Start it first with `make up`.
test-local:
	uv run pytest tests/local -m local --no-cov $(PYTEST_ARGS)

# pytest exits 5 when no tests are collected; an empty suite is not a failure yet.
test-media:
	uv run pytest -m media; status=$$?; [ $$status -eq 0 ] || [ $$status -eq 5 ]

security:
	uvx semgrep scan --config p/default --error --metrics=off
	@command -v gitleaks >/dev/null 2>&1 && gitleaks detect --no-banner --redact || echo "gitleaks not installed locally; runs in CI"

licence-check:
	uv run licence-gate models/registry.yaml

ci: lint typecheck test licence-check
