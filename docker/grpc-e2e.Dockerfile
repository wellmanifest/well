# syntax=docker/dockerfile:1.7
FROM python:3.13.5-slim-bookworm
ENV PYTHONPATH=/workspace/src
WORKDIR /workspace
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY proto ./proto
COPY scripts ./scripts
RUN python -m pip install --no-cache-dir '.[grpc]' \
 && ./scripts/generate_proto.sh \
 && python -m pip install --no-cache-dir --no-deps .
CMD ["python", "scripts/e2e-grpc.py"]
