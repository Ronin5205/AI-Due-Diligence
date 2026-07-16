"""Shared types and protocol for search source modules."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class RawDocumentRecord:
    source: str
    external_id: str
    title: str
    content: str
    url: str
    metadata: dict[str, Any] = field(default_factory=dict)


class SearchSource(Protocol):
    name: str

    def is_configured(self) -> bool: ...

    def search(self, query: str, limit: int) -> list[RawDocumentRecord]: ...
