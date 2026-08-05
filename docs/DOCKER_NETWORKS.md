# Docker and network preflight

A previous Compose build completed all images but failed while creating the
network because Docker's predefined address pools had already been fully
subnetted. Wellm therefore declares explicit, configurable IPAM networks:

```dotenv
WELLMANIFEST_PUBLIC_SUBNET=172.30.240.0/24
WELLMANIFEST_RUNTIME_SUBNET=172.30.241.0/24
WELLMANIFEST_E2E_SUBNET=172.30.242.0/24
WELLMANIFEST_IOT_SUBNET=172.30.243.0/24
```

Before Compose starts, run:

```bash
make docker-network-doctor
```

The preflight inspects existing Docker networks and fails with a collision
report. Change only the corresponding `.env` CIDR; the same value is consumed
by Compose and the preflight.

```bash
make up          # standard HTTP/WS/MQTT/gRPC stack
make down
make e2e         # local suite + Compose E2E + IoT E2E
```

`make e2e-local` is intentionally separate. `make e2e` is fail-closed when
Docker is unavailable unless `WELLMANIFEST_E2E_ALLOW_LOCAL_FALLBACK=1` is set
explicitly.
