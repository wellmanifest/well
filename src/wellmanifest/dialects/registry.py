from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .base import Dialect
from .json_dialect import JsonDialect
from .policy import PolicyDialect
from .proto import Proto3Dialect
from .structured import HclDialect, TypedDialect
from .toml_dialect import TomlDialect
from .toon import ToonDialect
from .typescript import TypeScriptDialect
from .yaml_dialect import YamlDialect


class DialectRegistry:
    def __init__(self, dialects: Iterable[Dialect] | None = None):
        self._dialects: dict[str, Dialect] = {}
        for dialect in dialects or self.default_dialects():
            self.register(dialect)

    @staticmethod
    def default_dialects() -> list[Dialect]:
        return [JsonDialect(), ToonDialect(), YamlDialect(), TomlDialect(), TypeScriptDialect(), HclDialect(), TypedDialect(), PolicyDialect(), Proto3Dialect()]

    def register(self, dialect: Dialect) -> None:
        for name in (dialect.name, *dialect.aliases, *dialect.media_types):
            self._dialects[name.lower()] = dialect

    def get(self, name: str) -> Dialect:
        normalized = name.strip().lower()
        if normalized not in self._dialects:
            raise KeyError(f"Unknown WellManifest dialect: {name}")
        return self._dialects[normalized]

    def detect(self, source: str, *, source_name: str | None = None) -> Dialect:
        extension_matches: list[Dialect] = []
        if source_name:
            suffixes = "".join(Path(source_name).suffixes).lower()
            for dialect in self.unique():
                if any(suffixes.endswith(extension.lower()) for extension in dialect.extensions):
                    extension_matches.append(dialect)
        candidates = self.unique()
        scores = [(dialect.probe(source, source_name=source_name), dialect) for dialect in candidates]
        if extension_matches:
            scores.extend((0.85, dialect) for dialect in extension_matches)
        score, dialect = max(scores, key=lambda item: item[0])
        if score <= 0:
            raise KeyError("Unable to detect dialect; pass --dialect explicitly")
        return dialect

    def unique(self) -> list[Dialect]:
        unique: dict[str, Dialect] = {}
        for dialect in self._dialects.values():
            unique[dialect.name] = dialect
        return list(unique.values())

    def describe(self) -> list[dict[str, object]]:
        return [
            {
                "name": dialect.name,
                "aliases": list(dialect.aliases),
                "mediaTypes": list(dialect.media_types),
                "extensions": list(dialect.extensions),
                "documentKind": dialect.document_kind,
            }
            for dialect in self.unique()
        ]
