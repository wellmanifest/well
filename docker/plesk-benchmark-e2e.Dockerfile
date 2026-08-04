# syntax=docker/dockerfile:1.7
FROM python:3.13.5-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/workspace/src
WORKDIR /workspace
COPY pyproject.toml README.md LICENSE VERSION ./
COPY src ./src
COPY tests ./tests
COPY schemas ./schemas
COPY examples ./examples
COPY config ./config
RUN python -m pip install --no-cache-dir '.[dev]'
CMD ["sh", "-ec", "python -m pytest -q tests/test_plesk.py tests/test_llmbench.py && wellm plesk-plan examples/plesk/projects.json --project obslugabiurowa-pl --source-ref workspace:obslugabiurowa-pl=examples/plesk/site/www --workspace-root . --to json >/tmp/plan.json && wellm benchmark-llm examples/benchmark/config.yaml --mock --output-dir /tmp/benchmark && test -s /tmp/benchmark/benchmark-report.json && echo 'plesk/benchmark e2e: PASS'"]
