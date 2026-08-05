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

Before Compose starts, inspect or repair the allocation:

```bash
make docker-network-doctor
make docker-network-repair
```

The preflight and Compose read the same `.env`. `make up`, Docker E2E and IoT
E2E automatically run `--repair`: colliding default or `.env` values are
replaced atomically with free `/24` networks and host ports. Existing Wellm
containers are recognized as valid owners of their published ports. A
process-level override is never rewritten and remains fail-closed. Use
`docker-network-doctor` for a read-only report and `docker-network-repair` for
an explicit repair of all scopes.

If an existing Wellm network has a different subnet, stop its Compose project
before repair. The preflight does not remove Docker networks or containers.

```bash
make up          # standard HTTP/WS/MQTT/gRPC stack
make down
make e2e         # local suite + Compose E2E + IoT E2E
```

`make e2e-local` is intentionally separate. `make e2e` is fail-closed when
Docker is unavailable unless `WELLMANIFEST_E2E_ALLOW_LOCAL_FALLBACK=1` is set
explicitly.

## Known non-blocking warning

`make e2e-docker` may print `StarletteDeprecationWarning` in `plesk-benchmark-e2e`:
`StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.`

This is non-blocking for current E2E pipeline and can be treated as dependency refresh technical debt.

Recommended action:
1. Add `httpx2` (or aligned FastAPI/Starlette versions) in `plesk-benchmark-e2e` dependency set.
2. Keep warning in CI as allowed, but fail build only on test failures/errors.
