# LLM integration

The built-in `llm://planner/manifest/query/propose` handler is deliberately
deterministic and does not call an external model. It demonstrates the control
boundary:

1. an LLM proposes a manifest or process DAG;
2. WellManifest parses and validates the proposal;
3. Contract AQL limits exact URI Processes;
4. side-effecting steps require the lifecycle and human gates declared by the
   application;
5. receipts and diagnostics are appended to the event stream.

A real provider adapter should implement the same URI handler and return only a
`PROPOSED` artifact. It must not grant itself authority or execute connector
calls directly.
