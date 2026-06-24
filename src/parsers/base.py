from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


@dataclass
class ParsedDocument:
    source_id: str
    title: str
    markdown: str
    metadata: dict = field(default_factory=dict)


class DocumentParser(Protocol):
    def parse(self, path: Path) -> ParsedDocument: ...


class ParserUnavailableError(RuntimeError):
    pass
