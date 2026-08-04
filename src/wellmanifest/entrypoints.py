from __future__ import annotations

import sys

from .cli import main


def _run(dialect: str) -> None:
    main(["run", "--dialect", dialect, *sys.argv[1:]])


def hcl() -> None:
    _run("hcl")


def typed() -> None:
    _run("typed")


def policy() -> None:
    _run("policy")


def yaml() -> None:
    _run("yaml")


def proto3() -> None:
    _run("proto3")
