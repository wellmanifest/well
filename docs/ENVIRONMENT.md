# Environment configuration

`config/env-contract.json` is the single source of names, defaults, types,
secret classification and descriptions for Wellm environment variables.

```bash
make env-sync       # regenerate .env.example and the packaged contract
make env-setup      # create .env only when it does not exist
make env-check      # schema validation + reference scan + value validation
make setup          # env setup, venv and development dependencies
```

`make env-setup` does not overwrite a local `.env`. Use
`wellm env setup --force` only when replacement is intentional. `.env` is
created with restrictive permissions where the platform supports them.

Compose commands always use the same file:

```bash
make up
make down
make iot-up
make iot-down
make e2e
```

The verifier scans Python, JavaScript, shell, examples, Docker Compose,
Dockerfile and Makefile references. A product-owned variable used in code but
missing from the contract is `WM-ENV-002`. Unknown variables in `.env` are
`WM-ENV-004`. Secret variables have empty development defaults and are never
returned with runtime values by `/v1/env-contract`.
