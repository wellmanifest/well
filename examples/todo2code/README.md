# Wellm + todo2code: badanie intencji w wielu formatach

Każdy plik `intent.*` reprezentuje ten sam kontrakt `new-project.intent/v2`.
Wellm parsuje wszystkie dialekty do jednego modelu, waliduje je przez ten sam
JSON Schema i wykonuje pairwise semantic diff.

```bash
make intent-demo
cat .wellm/intent-demo/report.json
cat .wellm/intent-demo/todo2code-evidence.json

# z zainstalowanym todo2code:
make todo2code-intent
```

Wynik `wellm.todo2code-format-evidence/v1` jest deterministycznym artefaktem
konfiguracyjnym. Umieszczony w analizowanym repozytorium może zostać wczytany
przez `t2c extract config`, a następnie połączony z dowodami Git, AST, TODO,
changelogu i dokumentacji.

```bash
# w repozytorium analizowanym przez todo2code
mkdir -p .intent/input
cp .wellm/intent-demo/todo2code-evidence.json .intent/input/
t2c extract config .intent/input --out .intent/format.intent.jsonl
t2c link .intent/format.intent.jsonl other.intent.jsonl --out .intent/intent.graph.json
```

Do kontrolowanego przykładu driftu porównaj `intent.json` z
`intent-drift.yaml` przez `wellm semantic-diff`.
