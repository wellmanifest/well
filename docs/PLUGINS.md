# Plugins and the optional `well` ecosystem

WellManifest is standalone. Dialect and URI Process extensions can be installed
through Python entry-point groups:

```toml
[project.entry-points."wellmanifest.dialects"]
myformat = "my_package:MyDialect"

[project.entry-points."wellmanifest.processes"]
myconnector = "my_package:register_processes"
```

Plugins are loaded by trusted deployment configuration, never by an untrusted
manifest. A document may request a dialect/runtime, but it cannot install a
package or register an adapter.

The requested PyPI `well` package is represented by a conservative discovery
adapter in `wellmanifest.integrations.well`. It reports whether a module is
installed but does not invent an API contract. A real bridge should be added
only against a pinned, documented release and covered by compatibility tests.

The same model applies to additional formats such as OpenAPI, AsyncAPI, Avro,
CBOR or MessagePack: each plugin declares parse/emit capabilities and conversion
quality, then works through the canonical Document/Envelope model.
