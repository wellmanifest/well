# syntax=docker/dockerfile:1.7
FROM python:3.13.5-slim-bookworm
ENV PYTHONPATH=/workspace/src
WORKDIR /workspace
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY scripts/e2e-python.py ./scripts/e2e-python.py
RUN python -m pip install --no-cache-dir .
CMD ["python", "scripts/e2e-python.py"]
