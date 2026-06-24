"""TXT / MD 텍스트 파서."""
from __future__ import annotations

from pathlib import Path

from src.parsers.base import ParsedDocument


class TextParser:
    def parse(self, path: Path) -> ParsedDocument:
        text = path.read_text(encoding="utf-8", errors="replace")
        return ParsedDocument(
            source_id=path.stem,
            title=path.stem.replace("_", " "),
            markdown=text,
            metadata={"source": path.name, "format": path.suffix.lstrip(".")},
        )
