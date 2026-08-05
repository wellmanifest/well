# syntax=docker/dockerfile:1.7
FROM python:3.13.5-alpine
WORKDIR /device
RUN python -m pip install --no-cache-dir paho-mqtt==2.1.0
COPY examples/iot-three-layer/firmware/device.py ./device.py
RUN adduser -D -u 10001 firmware && mkdir -p /state && chown -R firmware:firmware /device /state
USER firmware
CMD ["python", "device.py"]
