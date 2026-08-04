# Digital twins, router and situation profiles

## Portrait, not identity

A WellManifest digital twin is a **read-only portrait of an actor or system**.
It is not a replacement identity and cannot extend authority. A portrait can
contain:

- principal, actor kind, role and queue;
- Contract AQL version and delegating principal;
- permitted models, OQL operations and URI Processes;
- derived specializations;
- workload, waiting-input state and known contract gaps;
- revision hash used to reproduce a routing decision.

Passwords, tokens and vault contents do not belong in a portrait.

## Router order

The router evaluates candidates in this order:

1. current contract exists;
2. contract covers all required OQL/URI capabilities;
3. environment/runtime requirements are available;
4. specialization and evidence fit are sufficient;
5. only then workload and preferences influence ranking.

A preference for a bot never bypasses the same AQL and URI gates applied to a
human or service actor.

Example request:

```json
{
  "ticket": "PLF-1300",
  "requirements": {
    "uri_processes": ["plesk://host/mailbox/query/status"],
    "models": [],
    "environment": "backend"
  },
  "candidates": [
    {
      "principal": "bot:operations-operator-bot",
      "authority": ["plesk://host/mailbox/query/*"],
      "specializations": ["operations", "plesk"],
      "workload": 0.25
    }
  ]
}
```

Invoke the demo router through:

```text
twin://router/delegation/query/decide
```

## Ticket DAG and receipts

An orchestrated execution chain should not advance because a status merely says
`done`. Each edge is released by an accepted intent binding or by verified
receipts for all dependencies. EQL evidence validates the effect at the end of
a ticket.

```text
Intent Contract
      |
      v
Project Composer + ticket DAG
      |
      v
DOQL situation snapshot
      |
      v
Digital Twin Router (AQL + fit + workload)
   /           |            \
 human        bot          service
   \           |            /
    +---- receipt + EQL ----+
              |
              v
        next ticket in DAG
```

A change of executor creates an explicit handoff event.

## False-ready protection

A ticket marked ready but failing contract, actor or exact-URI preflight should
be projected as `false-ready`/`waiting_input` with a stable reason. The
controller should retry only after a relevant contract, actor, dependency or
capability revision changes, rather than repeating the same denial every poll.

## Situation profile

The supplied example is stored as
`examples/situation-profile/public-site.capability-inventory.json`. It defines:

- an inventory snapshot source;
- counts and ratios;
- ordered assessments such as `usable`, `partial`, `ready` and `not_ready`;
- decision candidates with strategy, EQL and evidence references;
- read-only policy and provenance.

Run it locally:

```bash
PYTHONPATH=src python examples/situation-profile/run.py
```

Or remotely:

```bash
curl -fsS http://localhost:8080/v1/runtime/execute \
  -H 'content-type: application/json' \
  -d @- <<'JSON'
{
  "uri": "situation://profile/evaluate/query",
  "contract_ref": "contract:digital-twin-readonly",
  "run_id": "situation:public-site:1",
  "payload": {
    "profile": {},
    "snapshots": {"inventory_rows": []}
  }
}
JSON
```

The reference evaluator supports the operations used by the supplied profile:
`count`, `count_where` and `ratio`, plus safe boolean/comparison expressions.
It does not execute arbitrary Python expressions.

## Lifecycle

A portrait should carry lifecycle state such as `partial`, `active`, `stale` or
`retired`, and an independent `autonomy.enabled` flag. Routing eligibility and
autonomous mutation are separate decisions. A partial portrait can assist a
human routing decision while remaining unable to act autonomously.
