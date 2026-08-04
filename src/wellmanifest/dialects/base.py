from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from wellmanifest.models import Document


class DialectError(ValueError):
    def __init__(self, code: str, message: str, *, line: int = 1, column: int = 1):
        super().__init__(message)
        self.code = code
        self.line = line
        self.column = column


class Dialect(ABC):
    name: str
    aliases: tuple[str, ...] = ()
    media_types: tuple[str, ...] = ()
    extensions: tuple[str, ...] = ()
    document_kind: str = "data"

    @abstractmethod
    def parse(self, source: str, *, source_name: str | None = None) -> Document:
        raise NotImplementedError

    @abstractmethod
    def emit(self, document: Document, *, projection: str = "data", pretty: bool = True) -> str:
        raise NotImplementedError

    def can_emit(self, projection: str) -> bool:
        return projection in {"data", "ir"}

    def probe(self, source: str, *, source_name: str | None = None) -> float:
        """Return a confidence score from 0 to 1."""
        return 0.0

    def normalize_input(self, source: Any) -> str:
        if isinstance(source, str):
            return source
        raise TypeError(f"{self.name} expects text input")
