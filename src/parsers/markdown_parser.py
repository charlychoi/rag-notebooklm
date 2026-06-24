from pathlib import Path
from .base import ParsedDocument


class MarkdownParser:
    """Notion Markdown 및 로컬 .md 파일용 패스스루 파서."""

    def parse(self, path: Path) -> ParsedDocument:
        text = path.read_text(encoding="utf-8")
        title = self._extract_title(text, path.stem)
        return ParsedDocument(
            source_id=path.stem,
            title=title,
            markdown=text,
            metadata={"source": str(path), "parser": "markdown_passthrough"},
        )

    @staticmethod
    def _extract_title(text: str, fallback: str) -> str:
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("# "):
                return line[2:].strip()
        return fallback
