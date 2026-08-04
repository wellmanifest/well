from __future__ import annotations

from dataclasses import dataclass

from .dialects.registry import DialectRegistry


@dataclass(frozen=True)
class NegotiatedFormat:
    media_type: str
    dialect: str
    conversion_required: bool


class FormatNegotiator:
    def __init__(self, registry: DialectRegistry):
        self.registry = registry

    def negotiate(self, source_dialect: str, accepted: list[str]) -> NegotiatedFormat:
        source = self.registry.get(source_dialect)
        normalized = [item.split(";", 1)[0].strip().lower() for item in accepted]
        if not normalized:
            normalized = ["application/wellmanifest+json"]
        for media_type in normalized:
            if media_type in {"*/*", "application/*"}:
                target = self.registry.get("json")
                return NegotiatedFormat(target.media_types[0], target.name, target.name != source.name)
            try:
                target = self.registry.get(media_type)
            except KeyError:
                continue
            return NegotiatedFormat(media_type, target.name, target.name != source.name)
        raise ValueError(f"No supported format in Accept set: {accepted}")
