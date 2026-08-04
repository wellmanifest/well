# syntax=docker/dockerfile:1.7
FROM python:3.13.5-alpine
WORKDIR /sim
COPY examples/firmware/rpi_client.py ./rpi_client.py
ENTRYPOINT ["python", "/sim/rpi_client.py"]
CMD ["--server", "http://runtime:8080", "--contract", "contract:firmware"]
