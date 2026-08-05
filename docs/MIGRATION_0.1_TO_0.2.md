# Migrating `wellm` 0.1.x to the 0.2 release candidate

The published `wellm` 0.1.x package exposed a minimal compatibility API through
the `well` Python namespace. The 0.2 release candidate turns the distribution
into the WellManifest protocol/runtime while retaining those imports.

## Existing imports remain valid

```python
from well import hello, greet

assert hello() == "hello from well"
assert greet("Anna") == "Hello, Anna!"
```

The compatibility namespace also exposes the runtime:

```python
from well import Runtime

runtime = Runtime()
```

## New primary API

```python
from wellm import WellManifestRuntime
from wellm.plesk import ProjectRegistry, PleskPublicationPlanner
from wellm.llmbench import BenchmarkConfig, BenchmarkRunner
```

Command-line entry points use `wellm`:

```bash
wellm --version
wellm convert input.yaml --from yaml --to typed
wellm plesk-plan projects.json --project example --source-ref workspace:example=site/www
```

The former `wellmanifest` package and commands remain aliases during the
transition. They should not be used in new examples.

## Versioning

`0.2.0rc3` is intentionally a pre-release. Installing `wellm` without an
explicit pre-release version continues to prefer the latest stable 0.1.x
release until a stable 0.2 release is published.
