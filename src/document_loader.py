"""RAG용 문서 로더 — samples + notion_export + 사용자 업로드 통합."""
from __future__ import annotations

import logging
from pathlib import Path

from src.parsers.base import ParsedDocument, ParserUnavailableError
from src.parsers.markdown_parser import MarkdownParser
from src.parsers.pdf_parser import LiteParseParser, PyMuPDFParser
from src.parsers.text_parser import TextParser

logger = logging.getLogger(__name__)

SAMPLES_DIR = Path(__file__).parent.parent / "data" / "samples"
NOTION_DIR  = Path(__file__).parent.parent / "data" / "notion_export"
UPLOAD_DIR  = Path(__file__).parent.parent / "data" / "uploads"

_md_parser   = MarkdownParser()
_txt_parser  = TextParser()


def _get_pdf_parser():
    try:
        return LiteParseParser()
    except ParserUnavailableError:
        try:
            return PyMuPDFParser()
        except ParserUnavailableError:
            return None


def _get_docx_parser():
    try:
        from src.parsers.docx_parser import DocxParser
        return DocxParser()
    except ParserUnavailableError:
        return None


def _parse_file(path: Path, pdf_parser, docx_parser) -> ParsedDocument | None:
    suffix = path.suffix.lower()
    try:
        if suffix == ".pdf":
            if pdf_parser is None:
                logger.warning("PDF 파서 없음, 스킵: %s", path.name)
                return None
            return pdf_parser.parse(path)
        elif suffix == ".docx":
            if docx_parser is None:
                logger.warning("DOCX 파서 없음, 스킵: %s", path.name)
                return None
            return docx_parser.parse(path)
        elif suffix in (".md", ".txt"):
            return _txt_parser.parse(path)
        else:
            return None
    except Exception as e:
        logger.error("파싱 실패 %s: %s", path.name, e)
        return None


def load_documents(
    samples_dir: Path = SAMPLES_DIR,
    notion_dir: Path = NOTION_DIR,
    upload_dir: Path = UPLOAD_DIR,
) -> list[ParsedDocument]:
    docs: list[ParsedDocument] = []
    pdf_parser  = _get_pdf_parser()
    docx_parser = _get_docx_parser()

    dirs = [
        (samples_dir, "samples"),
        (notion_dir,  "notion_export"),
        (upload_dir,  "upload"),
    ]

    for directory, label in dirs:
        if not directory.exists():
            continue
        exts = ["*.pdf", "*.docx", "*.md", "*.txt"]
        for pattern in exts:
            for path in sorted(directory.glob(f"**/{pattern}")):
                doc = _parse_file(path, pdf_parser, docx_parser)
                if doc:
                    doc.metadata["label"] = label
                    docs.append(doc)
                    logger.info("[%s] 로드: %s", label, path.name)

    return docs


def save_uploaded_file(uploaded_file) -> Path:
    """Streamlit UploadedFile 을 data/uploads/ 에 저장 후 경로 반환."""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    dest = UPLOAD_DIR / uploaded_file.name
    dest.write_bytes(uploaded_file.read())
    return dest


def summarize(docs: list[ParsedDocument]) -> dict:
    samples = [d for d in docs if d.metadata.get("label") == "samples"]
    notion  = [d for d in docs if d.metadata.get("label") == "notion_export"]
    uploads = [d for d in docs if d.metadata.get("label") == "upload"]
    return {
        "total":   len(docs),
        "samples": len(samples),
        "notion":  len(notion),
        "uploads": len(uploads),
    }
