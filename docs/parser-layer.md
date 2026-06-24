# Parser Layer Notes: LLMParse / LiteParse / PDF / Markdown

Goal: avoid coupling RAG ingestion to one document format.

Recommended interface:

```python
@dataclass
class ParsedDocument:
    source_id: str
    title: str
    markdown: str
    metadata: dict

class DocumentParser(Protocol):
    def parse(self, path: Path) -> ParsedDocument: ...
```

Backends:

1. `markdown_passthrough` — required for Notion Markdown.
2. `pymupdf` or `pymupdf4llm` — lightweight PDF fallback.
3. `llmparse` / `liteparse` adapter — optional; verify actual package/repo before installing.

Important: Notion Markdown ingestion must work even when PDF/LLMParse dependencies are unavailable.
