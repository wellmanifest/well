# syntax=docker/dockerfile:1.7
FROM python:3.13.5-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app/src \
    WELLMANIFEST_HOST=0.0.0.0 \
    WELLMANIFEST_PORT=8080 \
    WELLMANIFEST_CONTRACTS=/app/config/contracts.json \
    WELLMANIFEST_EVENT_STORE=/data/events.jsonl

WORKDIR /app
RUN addgroup --system --gid 10001 wellmanifest \
 && adduser --system --uid 10001 --ingroup wellmanifest --home /app wellmanifest \
 && mkdir -p /data \
 && chown -R wellmanifest:wellmanifest /data /app

COPY --chown=wellmanifest:wellmanifest pyproject.toml README.md LICENSE VERSION ./
COPY --chown=wellmanifest:wellmanifest src ./src
COPY --chown=wellmanifest:wellmanifest config ./config
COPY --chown=wellmanifest:wellmanifest schemas ./schemas
COPY --chown=wellmanifest:wellmanifest proto ./proto
COPY --chown=wellmanifest:wellmanifest scripts ./scripts
COPY --chown=wellmanifest:wellmanifest www ./www

RUN python -m pip install --no-cache-dir '.[all]' \
 && ./scripts/generate_proto.sh

USER 10001:10001
EXPOSE 8080 50051
VOLUME ["/data"]
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=12 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=2)" || exit 1
ENTRYPOINT ["wellm-server"]
