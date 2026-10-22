# Visavox developer commands (CLAUDE.md). Python via uv.
PYTEST_ARGS ?=
LOCAL_COMPOSE = docker compose -f deploy/local/compose.yaml
# This machine's network address, so the host browser and containers reach the same LiveKit media port (SDD §14).
LIVEKIT_NODE_IP ?= $(shell ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || hostname -I 2>/dev/null | awk '{print $$1}')

.PHONY: setup lint typecheck test test-contract test-local test-media security licence-check local-check up down gpu-check ci

setup:
	uv sync --all-packages

lint:
	uv run ruff check .
	uv run ruff format --check .

typecheck:
	uv run mypy tools/licence_gate/src tools/local_cell/src spikes/s3_livekit_contract/src

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

ci: lint typecheck test licence-check local-check

# Local cell (NFR-O5): every service, LiveKit and the AWS stand-ins on this machine, synthetic data only.
local-check:
	uv run local-cell-check

up: local-check
	@test -n "$(LIVEKIT_NODE_IP)" || { echo "No network address found; run: make up LIVEKIT_NODE_IP=<this machine's IP>"; exit 1; }
	LIVEKIT_NODE_IP=$(LIVEKIT_NODE_IP) $(LOCAL_COMPOSE) up -d --build --wait --wait-timeout 300
	@echo "Local cell up. LiveKit ws://localhost:7880 (media via $(LIVEKIT_NODE_IP)). Next: make test-local"

down:
	LIVEKIT_NODE_IP=$(or $(LIVEKIT_NODE_IP),unused) $(LOCAL_COMPOSE) down -v --remove-orphans

# Linux hosts with an NVIDIA GPU only: proves the NVIDIA Container Toolkit works for the `gpu` profile.
gpu-check:
	LIVEKIT_NODE_IP=$(or $(LIVEKIT_NODE_IP),unused) $(LOCAL_COMPOSE) --profile gpu run --rm gpu-check
