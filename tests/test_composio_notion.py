"""Composio Notion 클라이언트 유닛 테스트 (mock 사용)."""
import pytest
from unittest.mock import MagicMock, patch


def test_check_connection_active():
    from src.integrations.composio_notion import ComposioNotionClient

    mock_account = MagicMock()
    mock_account.status = "ACTIVE"
    mock_account.id = "ca_test"

    with patch("src.integrations.composio_notion.Composio") as MockComposio:
        instance = MockComposio.return_value
        instance.connected_accounts.get.return_value = mock_account

        client = ComposioNotionClient("fake_key", "user1", "ca_test")
        info = client.check_connection()

    assert info["status"] == "ACTIVE"
    assert info["id"] == "ca_test"


def test_get_page_markdown_dict_response():
    from src.integrations.composio_notion import ComposioNotionClient

    with patch("src.integrations.composio_notion.Composio") as MockComposio:
        instance = MockComposio.return_value
        instance.tools.execute.return_value = {"data": {"markdown": "# 테스트 페이지\n내용"}}

        client = ComposioNotionClient.__new__(ComposioNotionClient)
        client._client = instance
        client._user_id = "user1"
        client._connected_account_id = "ca_test"

        md = client.get_page_markdown("page-123")

    assert "테스트 페이지" in md
