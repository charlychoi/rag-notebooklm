"""Composio Notion 클라이언트 — tools.execute 래퍼."""
from __future__ import annotations

import logging
from typing import Any

from composio import Composio

from src.config import redact_secret

logger = logging.getLogger(__name__)


class ComposioNotionClient:
    def __init__(self, api_key: str, user_id: str, connected_account_id: str):
        self._client = Composio(api_key=api_key)
        self._user_id = user_id
        self._connected_account_id = connected_account_id
        logger.info("ComposioNotionClient 초기화 (key=%s)", redact_secret(api_key))

    def check_connection(self) -> dict:
        account = self._client.connected_accounts.get(self._connected_account_id)
        return {"id": account.id, "status": account.status}

    def _execute(self, tool: str, arguments: dict[str, Any]) -> Any:
        logger.info("툴 실행: %s args=%s", tool, arguments)
        result = self._client.tools.execute(
            tool=tool,
            arguments=arguments,
            user_id=self._user_id,
        )
        return result

    def get_page_markdown(self, page_id: str) -> str:
        result = self._execute("NOTION_GET_PAGE_MARKDOWN", {"page_id": page_id})
        # result가 dict-like 또는 객체일 수 있으므로 유연하게 추출
        if isinstance(result, dict):
            return result.get("data", {}).get("markdown", "") or result.get("markdown", "") or str(result)
        if hasattr(result, "data"):
            data = result.data
            if isinstance(data, dict):
                return data.get("markdown", "") or str(data)
        return str(result)

    def fetch_block_children(self, block_id: str) -> list[dict]:
        result = self._execute("NOTION_FETCH_BLOCK_CONTENTS", {"block_id": block_id})
        if isinstance(result, dict):
            return result.get("data", {}).get("results", [])
        if hasattr(result, "data") and isinstance(result.data, dict):
            return result.data.get("results", [])
        return []

    def fetch_data(self, fetch_type: str = "pages") -> list[dict]:
        result = self._execute("NOTION_FETCH_DATA", {"fetch_type": fetch_type})
        if isinstance(result, dict):
            return result.get("data", {}).get("results", [])
        if hasattr(result, "data") and isinstance(result.data, dict):
            return result.data.get("results", [])
        return []
