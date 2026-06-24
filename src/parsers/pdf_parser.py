from pathlib import Path
from .base import ParsedDocument, ParserUnavailableError


class LiteParseParser:
    """LiteParse 기반 PDF/문서 파서."""

    def __init__(self, ocr_enabled: bool = False):
        try:
            from liteparse import LiteParse
            self._cls = LiteParse
            self._ocr_enabled = ocr_enabled
        except ImportError as e:
            raise ParserUnavailableError("liteparse 패키지가 없습니다: pip install liteparse") from e

    def parse(self, path: Path) -> ParsedDocument:
        from liteparse import LiteParse
        parser = LiteParse(output_format="markdown", ocr_enabled=self._ocr_enabled)
        result = parser.parse(str(path))
        return ParsedDocument(
            source_id=path.stem,
            title=path.stem,
            markdown=result.text,
            metadata={"source": str(path), "parser": "liteparse", "pages": len(result.pages)},
        )


class PyMuPDFParser:
    """pymupdf 기반 경량 PDF 폴백 파서."""

    def parse(self, path: Path) -> ParsedDocument:
        try:
            import pymupdf
        except ImportError as e:
            raise ParserUnavailableError("pymupdf 패키지가 없습니다: pip install pymupdf") from e

        doc = pymupdf.open(str(path))
        pages_text = [page.get_text() for page in doc]
        markdown = "\n\n".join(pages_text)
        return ParsedDocument(
            source_id=path.stem,
            title=path.stem,
            markdown=markdown,
            metadata={"source": str(path), "parser": "pymupdf", "pages": len(pages_text)},
        )
