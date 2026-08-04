#!/usr/bin/env sh
set -eu
curl -fsS http://localhost:8080/v1/runtime/execute \
  -H 'content-type: application/json' \
  -d '{
    "uri":"soa://service/http/request/plan",
    "payload":{"method":"POST","url":"https://api.example.invalid/catalog/items","body":{"sku":"WM-001"}},
    "contract_ref":"contract:dev",
    "run_id":"soa:catalog:plan:1",
    "runtime":{"runtime_ref":"backend-python","environment":"backend","execution":"remote","resources":{}}
  }'
