import tempfile
from pathlib import Path
import pytest

from src.parsers.markdown_parser import MarkdownParser
from src.parsers.pdf_parser import LiteParseParser
from src.parsers.base import ParsedDocument


def test_markdown_parser_basic():
    parser = MarkdownParser()
    with tempfile.NamedTemporaryFile(suffix=".md", mode="w", encoding="utf-8", delete=False) as f:
        f.write("# 연차 정책\n\n연차는 15일입니다.")
        path = Path(f.name)
    doc = parser.parse(path)
    assert isinstance(doc, ParsedDocument)
    assert doc.title == "연차 정책"
    assert "연차" in doc.markdown


def test_markdown_parser_no_heading():
    parser = MarkdownParser()
    with tempfile.NamedTemporaryFile(suffix=".md", mode="w", encoding="utf-8", delete=False) as f:
        f.write("내용만 있는 파일입니다.")
        path = Path(f.name)
    doc = parser.parse(path)
    assert doc.title == path.stem


def test_liteparse_available():
    pytest.importorskip("liteparse")
    parser = LiteParseParser()
    assert parser is not None
