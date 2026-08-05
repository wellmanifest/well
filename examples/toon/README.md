# TOON / code2llm map

`map.toon.yaml` jest rzeczywistym, YAML-kompatybilnym artefaktem mapy projektu.
Wellm zachowuje metadane producenta, artefaktu i wersji schematu oraz może
przekonwertować mapę do JSON, YAML albo pełnego IR.

```bash
wellm parse examples/toon/map.toon.yaml --dialect toon --projection ir
wellm convert examples/toon/map.toon.yaml --from toon --to json
```
