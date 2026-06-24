#!/usr/bin/env python3
"""Composio를 통해 Notion 페이지를 Markdown으로 내보내는 스크립트.

Usage:
    python scripts/import_composio_notion_docs.py \
        --page-id 35e0d17e-cf4a-801d-8166-eff8982245a9 \
        --out data/notion_export \
        --recursive
"""
from __future__ import annotations

import argparse
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from src.config import COMPOSIO_API_KEY, COMPOSIO_CONNECTED_ACCOUNT_ID, COMPOSIO_USER_ID, redact_secret
from composio import Composio

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

NOTION_TOOLKIT_VERSION = "20260623_00"


def safe_filename(name: str) -> str:
    name = re.sub(r'[^\w\s\-]', '', name).strip()
    name = re.sub(r'\s+', '-', name)
    return name[:80] or "untitled"


def build_frontmatter(page_id: str, connected_account_id: str) -> str:
    now = datetime.now(timezone.utc).isoformat()
    return f"""---
source: notion_composio
page_id: {page_id}
connected_account_id: {connected_account_id}
exported_at: {now}
---

"""


def extract_markdown(result) -> str:
    """ToolExecutionResponse에서 Markdown 텍스트 추출."""
    if result is None:
        return ""
    # dict
    if isinstance(result, dict):
        data = result.get("data", result)
        if isinstance(data, dict):
            return data.get("markdown", "") or data.get("content", "") or str(data)
        return str(data)
    # pydantic 모델 계열
    for attr in ("data", "response", "result"):
        val = getattr(result, attr, None)
        if val is None:
            continue
        if isinstance(val, dict):
            return val.get("markdown", "") or val.get("content", "") or str(val)
        if isinstance(val, str):
            return val
    return str(result)


def export_page(client: Composio, page_id: str, out_dir: Path, user_id: str, connected_account_id: str) -> str | None:
    logger.info("페이지 내보내기: %s", page_id)
    try:
        result = client.tools.execute(
            slug="NOTION_GET_PAGE_MARKDOWN",
            arguments={"page_id": page_id},
            user_id=user_id,
            version=NOTION_TOOLKIT_VERSION,
        )
    except Exception as e:
        logger.error("NOTION_GET_PAGE_MARKDOWN 실패 (page_id=%s): %s", page_id, e)
        return None

    markdown = extract_markdown(result)
    if not markdown:
        logger.warning("빈 Markdown 반환 (page_id=%s)", page_id)
        return None

    # 제목 추출
    title = page_id
    for line in markdown.splitlines():
        line = line.strip()
        if line.startswith("# "):
            title = line[2:].strip()
            break

    filename = safe_filename(title) + ".md"
    output_path = out_dir / filename
    content = build_frontmatter(page_id, connected_account_id) + markdown

    output_path.write_text(content, encoding="utf-8")
    logger.info("저장 완료: %s (%d chars)", output_path, len(markdown))
    return page_id


def fetch_child_page_ids(client: Composio, block_id: str, user_id: str) -> list[str]:
    try:
        result = client.tools.execute(
            slug="NOTION_FETCH_BLOCK_CONTENTS",
            arguments={"block_id": block_id},
            user_id=user_id,
            version=NOTION_TOOLKIT_VERSION,
        )
        blocks = []
        if isinstance(result, dict):
            blocks = result.get("data", {}).get("results", [])
        elif hasattr(result, "data") and isinstance(result.data, dict):
            blocks = result.data.get("results", [])

        child_ids = []
        for block in blocks:
            if isinstance(block, dict) and block.get("type") == "child_page":
                child_ids.append(block["id"])
        return child_ids
    except Exception as e:
        logger.warning("블록 자식 조회 실패 (block_id=%s): %s", block_id, e)
        return []


def run(page_id: str, out_dir: Path, recursive: bool):
    if not COMPOSIO_API_KEY:
        logger.error("COMPOSIO_API_KEY가 설정되지 않았습니다.")
        sys.exit(1)

    logger.info("Composio API Key: %s", redact_secret(COMPOSIO_API_KEY))
    logger.info("User ID: %s", COMPOSIO_USER_ID)
    logger.info("Connected Account: %s", COMPOSIO_CONNECTED_ACCOUNT_ID)

    out_dir.mkdir(parents=True, exist_ok=True)
    client = Composio(api_key=COMPOSIO_API_KEY)

    # 연결 상태 확인
    try:
        account = client.connected_accounts.get(COMPOSIO_CONNECTED_ACCOUNT_ID)
        logger.info("연결 상태: %s (toolkit=%s)", account.status, account.toolkit)
        if account.status != "ACTIVE":
            logger.error("Connected account가 ACTIVE 상태가 아닙니다: %s", account.status)
            sys.exit(1)
    except Exception as e:
        logger.error("연결 계정 확인 실패: %s", e)
        sys.exit(1)

    exported = set()
    queue = [page_id]

    while queue:
        current_id = queue.pop(0)
        if current_id in exported:
            continue
        result = export_page(client, current_id, out_dir, COMPOSIO_USER_ID, COMPOSIO_CONNECTED_ACCOUNT_ID)
        if result:
            exported.add(current_id)

        if recursive:
            children = fetch_child_page_ids(client, current_id, COMPOSIO_USER_ID)
            for cid in children:
                if cid not in exported:
                    queue.append(cid)

    logger.info("완료: %d개 페이지 내보냄 → %s", len(exported), out_dir)
    return len(exported)


def main():
    parser = argparse.ArgumentParser(description="Composio → Notion → Markdown 익스포터")
    parser.add_argument("--page-id", default="35e0d17e-cf4a-801d-8166-eff8982245a9")
    parser.add_argument("--out", default="data/notion_export")
    parser.add_argument("--recursive", action="store_true", default=True)
    args = parser.parse_args()

    count = run(
        page_id=args.page_id,
        out_dir=Path(args.out),
        recursive=args.recursive,
    )
    sys.exit(0 if count > 0 else 1)


if __name__ == "__main__":
    main()
