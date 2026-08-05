.PHONY: help setup setup-lite install install-js env-setup env-sync env-check versions versions-sync versions-check \
	verify test test-python test-js governance governance-check schema-demo intent-demo todo2code-intent serve proto \
	up down logs iot-up iot-down iot-e2e docker-network-doctor docker-network-repair compose-check \
	e2e e2e-local e2e-docker package clean

PYTHON ?= python3
VENV ?= .venv
VENV_PYTHON := $(VENV)/bin/python
VENV_PIP := $(VENV)/bin/pip
COMPOSE ?= docker compose

help:
	@printf '%s\n' \
	  'make setup          create .env/.venv and install Python + JS development dependencies' \
	  'make up/down        start or stop the standard HTTP/WS/MQTT/gRPC stack' \
	  'make iot-up/down    start or stop the frontend/backend/firmware IoT example' \
	  'make e2e            run local, Docker and three-layer IoT E2E suites' \
	  'make docker-network-repair select free Docker CIDRs and persist them in .env' \
	  'make verify         run deterministic source, env, version and test checks' \
	  'make todo2code-intent analyze six formats and invoke t2c extract config' \
	  'make package        create source, wheel and npm release artifacts'

setup: env-setup
	@test -x "$(VENV_PYTHON)" || $(PYTHON) -m venv "$(VENV)"
	$(VENV_PYTHON) -m pip install --upgrade pip
	$(VENV_PYTHON) -m pip install -e '.[all,dev]'
	$(MAKE) install-js
	$(VENV_PYTHON) scripts/env_contract.py check

setup-lite: env-setup
	@test -x "$(VENV_PYTHON)" || $(PYTHON) -m venv "$(VENV)"
	$(VENV_PYTHON) -m pip install -e '.[dev,mqtt,grpc]'
	$(MAKE) install-js

install:
	$(PYTHON) -m pip install -e '.[all,dev]'

install-js:
	cd packages/js && npm install --ignore-scripts

env-setup:
	PYTHONPATH=src $(PYTHON) scripts/env_contract.py setup

env-sync:
	PYTHONPATH=src $(PYTHON) scripts/env_contract.py sync

env-check:
	PYTHONPATH=src $(PYTHON) scripts/env_contract.py check

versions:
	PYTHONPATH=src $(PYTHON) -m wellmanifest versions

versions-sync:
	PYTHONPATH=src $(PYTHON) -m wellmanifest versions --write >/dev/null

versions-check:
	PYTHONPATH=src $(PYTHON) -m wellmanifest versions --check >/dev/null

verify: env-check versions-check
	./scripts/verify.sh

test: test-python test-js

test-python:
	PYTHONPATH=src $(PYTHON) -m pytest

test-js:
	cd packages/js && npm test

governance:
	PYTHONPATH=src $(PYTHON) -m wellmanifest governance build examples/governance/wellm.project.yaml

governance-check:
	PYTHONPATH=src $(PYTHON) -m wellmanifest governance build examples/governance/wellm.project.yaml --check

schema-demo:
	mkdir -p .wellm/schema-demo
	PYTHONPATH=src $(PYTHON) -m wellmanifest schema import schemas/status.schema.json -o .wellm/schema-demo/status.schema.wm
	PYTHONPATH=src $(PYTHON) -m wellmanifest schema export .wellm/schema-demo/status.schema.wm -o .wellm/schema-demo/status.schema.roundtrip.json
	PYTHONPATH=src $(PYTHON) -m wellmanifest schema codegen schemas/status.schema.json --language typescript -o .wellm/schema-demo/status.d.ts

intent-demo:
	mkdir -p .wellm/intent-demo
	PYTHONPATH=src $(PYTHON) -m wellmanifest intent analyze examples/todo2code/intent-formats.wellm.yaml \
	  -o .wellm/intent-demo/report.json --todo2code-evidence .wellm/intent-demo/todo2code-evidence.json

todo2code-intent:
	./scripts/todo2code-intent.sh

serve:
	PYTHONPATH=src $(PYTHON) -m wellmanifest serve --host 0.0.0.0 --port 8080

proto:
	./scripts/generate_proto.sh

docker-network-doctor:
	PYTHONPATH=src $(PYTHON) scripts/docker_network_preflight.py --scope all

docker-network-repair: env-setup
	PYTHONPATH=src $(PYTHON) scripts/docker_network_preflight.py --scope all --repair

compose-check: env-setup
	$(COMPOSE) --env-file .env -f compose.yml config >/dev/null
	$(COMPOSE) --env-file .env -f compose.iot.yml config >/dev/null
	$(COMPOSE) --env-file .env -f compose.e2e.yml config >/dev/null

up: env-setup
	PYTHONPATH=src $(PYTHON) scripts/docker_network_preflight.py --scope main --repair
	$(COMPOSE) --env-file .env -f compose.yml up -d --build

down: env-setup
	$(COMPOSE) --env-file .env -f compose.yml down --remove-orphans

logs: env-setup
	$(COMPOSE) --env-file .env -f compose.yml logs -f --tail=200

iot-up: env-setup
	PYTHONPATH=src $(PYTHON) scripts/docker_network_preflight.py --scope iot --repair
	$(COMPOSE) --env-file .env -f compose.iot.yml up -d --build frontend backend broker bridge firmware

iot-down: env-setup
	$(COMPOSE) --env-file .env -f compose.iot.yml down -v --remove-orphans

iot-e2e: env-setup
	./scripts/e2e-iot.sh

e2e: e2e-local e2e-docker iot-e2e

e2e-local:
	./scripts/e2e-local.sh

e2e-docker: env-setup
	./scripts/e2e-docker.sh

package: env-check versions-check
	./scripts/package.sh

clean:
	rm -rf .runtime .wellm dist build target .pytest_cache packages/js/node_modules $(VENV)
