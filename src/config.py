import os
from dotenv import load_dotenv

load_dotenv()


def require_env(name: str) -> str:
    val = os.environ.get(name)
    if not val:
        raise EnvironmentError(f"환경변수 '{name}'이 설정되지 않았습니다. .env 파일을 확인하세요.")
    return val


def redact_secret(value: str) -> str:
    if not value or len(value) <= 8:
        return "****"
    return value[:4] + "****" + value[-4:]


COMPOSIO_API_KEY = os.environ.get("COMPOSIO_API_KEY", "")
COMPOSIO_CONNECTED_ACCOUNT_ID = os.environ.get("COMPOSIO_CONNECTED_ACCOUNT_ID", "ca_N4Qx8mkzzK3o")
COMPOSIO_AUTH_CONFIG_ID = os.environ.get("COMPOSIO_AUTH_CONFIG_ID", "ac_d5X2ED4uP9ZW")
COMPOSIO_USER_ID = os.environ.get("COMPOSIO_USER_ID", "charly")
TARGET_NOTION_PAGE_ID = os.environ.get("TARGET_NOTION_PAGE_ID", "35e0d17e-cf4a-801d-8166-eff8982245a9")
OPEN_NOTEBOOK_API_URL = os.environ.get("OPEN_NOTEBOOK_API_URL", "http://127.0.0.1:5055")
