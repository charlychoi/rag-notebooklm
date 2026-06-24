"""RAG용 문서 로더 — samples + notion_export 통합."""
from __future__ import annotations

import logging
from pathlib import Path

from src.parsers.base import ParsedDocument
from src.parsers.markdown_parser import MarkdownParser
from src.parsers.pdf_parser import LiteParseParser, PyMuPDFParser, ParserUnavailableError

logger = logging.getLogger(__name__)

SAMPLES_DIR = Path(__file__).parent.parent / "data" / "samples"
NOTION_DIR = Path(__file__).parent.parent / "data" / "notion_export"

_md_parser = MarkdownParser()


def _get_pdf_parser():
    try:
        return LiteParseParser()
    except ParserUnavailableError:
        try:
            return PyMuPDFParser()
        except ParserUnavailableError:
            return None


def load_documents(
    samples_dir: Path = SAMPLES_DIR,
    notion_dir: Path = NOTION_DIR,
) -> list[ParsedDocument]:
    docs: list[ParsedDocument] = []
    pdf_parser = _get_pdf_parser()

    for directory, label in [(samples_dir, "samples"), (notion_dir, "notion_export")]:
        if not directory.exists():
            logger.warning("%s 디렉토리가 없습니다: %s", label, directory)
            continue
        md_files = list(directory.glob("**/*.md"))
        pdf_files = list(directory.glob("**/*.pdf"))

        for path in md_files:
            try:
                doc = _md_parser.parse(path)
                doc.metadata["label"] = label
                docs.append(doc)
                logger.info("[%s] 로드: %s", label, path.name)
            except Exception as e:
                logger.error("Markdown 파싱 실패 %s: %s", path, e)

        for path in pdf_files:
            if pdf_parser is None:
                logger.warning("PDF 파서 없음, 스킵: %s", path)
                continue
            try:
                doc = pdf_parser.parse(path)
                doc.metadata["label"] = label
                docs.append(doc)
                logger.info("[%s] PDF 로드: %s", label, path.name)
            except Exception as e:
                logger.error("PDF 파싱 실패 %s: %s", path, e)

    return docs


def summarize(docs: list[ParsedDocument]) -> dict:
    samples = [d for d in docs if d.metadata.get("label") == "samples"]
    notion = [d for d in docs if d.metadata.get("label") == "notion_export"]
    return {"total": len(docs), "samples": len(samples), "notion": len(notion)}
