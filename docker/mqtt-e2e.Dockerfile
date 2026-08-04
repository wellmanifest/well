# syntax=docker/dockerfile:1.7
FROM python:3.13.5-slim-bookworm
WORKDIR /workspace
RUN python -m pip install --no-cache-dir paho-mqtt==2.1.0
COPY scripts/e2e-mqtt.py ./e2e-mqtt.py
CMD ["python", "e2e-mqtt.py"]
