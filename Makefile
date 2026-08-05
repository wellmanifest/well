.PHONY: install verify test test-python test-js governance governance-check e2e e2e-docker serve proto package clean

PYTHON ?= python3

install:
	$(PYTHON) -m pip install -e '.[all,dev]'

verify:
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

serve:
	PYTHONPATH=src $(PYTHON) -m wellmanifest serve --host 0.0.0.0 --port 8080

proto:
	./scripts/generate_proto.sh

e2e:
	./scripts/e2e-local.sh

e2e-docker:
	./scripts/e2e-docker.sh

package:
	./scripts/package.sh

clean:
	rm -rf .runtime dist build target .pytest_cache packages/js/node_modules
