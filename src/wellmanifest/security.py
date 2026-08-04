from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

CONCRETE_URI = re.compile(r"^[a-z][a-z0-9+.-]*://[^\s*]+$", re.IGNORECASE)
SAFE_RUN_ID = re.compile(r"^[a-z0-9._:-]{1,160}$", re.IGNORECASE)


class AuthorizationError(PermissionError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def assert_concrete_uri(uri: str) -> str:
    value = str(uri or "")
    if not CONCRETE_URI.fullmatch(value) or "*" in value:
        raise AuthorizationError("WM-AUTH-001", "uri_process_uri_invalid")
    return value


def assert_safe_run_id(run_id: str) -> str:
    value = str(run_id or "")
    if value and not SAFE_RUN_ID.fullmatch(value):
        raise AuthorizationError("WM-AUTH-002", "uri_process_run_id_invalid")
    return value


def matches_uri_process(uri: str, scopes: list[str] | tuple[str, ...]) -> bool:
    candidate = str(uri or "")
    for raw_scope in scopes:
        scope = str(raw_scope or "")
        if scope == "*":
            return True
        if scope.endswith("*") and candidate.startswith(scope[:-1]):
            return True
        if candidate == scope:
            return True
    return False


class ContractStore:
    def __init__(self, path: str | Path | None = None, contracts: dict[str, Any] | None = None):
        self.path = Path(path) if path else None
        self.contracts = contracts or {}
        if self.path and self.path.exists():
            loaded = json.loads(self.path.read_text(encoding="utf-8"))
            self.contracts = loaded.get("contracts", loaded)

    def resolve_scopes(self, contract_ref: str | None) -> list[str]:
        if not contract_ref:
            return []
        contract = self.contracts.get(contract_ref)
        if not contract:
            raise AuthorizationError("WM-AUTH-003", f"Unknown contract: {contract_ref}")
        if contract.get("status", "active") != "active":
            raise AuthorizationError("WM-AUTH-004", f"Inactive contract: {contract_ref}")
        scopes = contract.get("allowedUriProcesses", [])
        if not isinstance(scopes, list) or not all(isinstance(item, str) for item in scopes):
            raise AuthorizationError("WM-AUTH-005", f"Malformed contract: {contract_ref}")
        return scopes
