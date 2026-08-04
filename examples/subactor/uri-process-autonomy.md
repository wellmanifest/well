---
{"schema":"subactor.doc/v1","id":"platform.docs.uri.process.autonomy","version":1,"status":"current","updated":"2026-07-21"}
---

# URI Process in autonomous Subactor

A task is an execution contract between the owner of an outcome and an actor. It
contains the expected result, responsible actor, criteria/instruction, URI
Process plan and execution state.

The model separates Contract AQL (who may act and boundaries), OQL (business
operation) and a concrete URI Process. `youtube://*` is only an authority scope;
execution always receives a concrete URI.

The managed invariant is ticket before effect: the Planfile ticket and
`SUBACTOR_PROCESS_MANIFEST_V1` exist before dispatch, the OQL/URI matches the
definition, an idempotency key binds ticket and step, and the bridge writes a
`SUBACTOR_PROCESS_RESULT_V1` plus execution/log references to the same ticket.
Missing evidence fails before connector contact.

Autonomy enters through control and bridge, not a raw subprocess or public node
endpoint. The bridge re-reads the ticket and checks the minimum projection of
ticket and delegated AQL at the last effect boundary.

See `process-manifest.wm.yaml` and `docs/URI_PROCESS.md`.
