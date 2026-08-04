from __future__ import annotations

import pytest

from wellmanifest.security import AuthorizationError, assert_concrete_uri, matches_uri_process


def test_concrete_uri_rejects_wildcard() -> None:
    with pytest.raises(AuthorizationError):
        assert_concrete_uri("youtube://*")


def test_scope_patterns_are_permissions() -> None:
    assert matches_uri_process("youtube://channel/video/query/list", ["youtube://*"])
    assert not matches_uri_process("flow://host/run", ["youtube://*"])
