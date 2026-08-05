# Wellmanifest PR template

## Summary
- [ ] What was changed (brief)
- [ ] Why this change is needed

## Validation
- [ ] Ran `make compose-check`
- [ ] Ran `make up`
- [ ] Verified `make up` starts healthy services
- [ ] Ran `make e2e-docker`
- [ ] Ran `python3 scripts/docker_network_preflight.py --scope main` and addressed any failures
- [ ] Ran `python3 scripts/docker_network_preflight.py --scope e2e` and addressed any failures
- [ ] Confirmed `docker compose -f compose.e2e.yml --env-file .env ps --all` is clean after test run

## Operational notes
- [ ] Main stack cleanup (`make down`) run when local validation completed
- [ ] Reviewed new/updated `.env` changes and checked for intentional network/port adjustments

## Risks
- [ ] Backward compatibility impact
- [ ] Runtime/network impact
- [ ] Known warnings accepted (e.g. deprecation warnings)

## Review focus
- [ ] Tests pass
- [ ] Code quality/guardrails improved or kept
- [ ] Documentation updated where needed
