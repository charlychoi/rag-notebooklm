"""Open Notebook 초기 설정: OpenAI 등록 + 정책 문서 업로드."""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

import requests

BASE_URL = os.getenv("OPEN_NOTEBOOK_API_URL", "http://127.0.0.1:5055")
OPENAI_KEY = os.getenv("OPENAI_API_KEY", "")
SAMPLES_DIR = Path("data/samples")
NOTION_DIR = Path("data/notion_export")


def check_health() -> bool:
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def register_openai() -> str | None:
    existing = requests.get(f"{BASE_URL}/api/credentials", timeout=5).json()
    for cred in existing:
        if cred.get("provider") == "openai":
            print(f"  OpenAI credential 이미 존재: {cred['id']}")
            return cred["id"]

    r = requests.post(
        f"{BASE_URL}/api/credentials",
        json={
            "name": "openai-main",
            "provider": "openai",
            "modalities": ["language", "embedding"],
            "api_key": OPENAI_KEY,
        },
        timeout=10,
    )
    r.raise_for_status()
    cred_id = r.json()["id"]
    print(f"  OpenAI credential 생성: {cred_id}")
    return cred_id


def register_models(cred_id: str) -> None:
    existing_count = len(requests.get(f"{BASE_URL}/api/models", timeout=5).json())
    if existing_count > 0:
        print(f"  모델 이미 {existing_count}개 등록됨 — 스킵")
        return

    requests.post(
        f"{BASE_URL}/api/credentials/{cred_id}/discover", timeout=15
    )
    r = requests.post(
        f"{BASE_URL}/api/credentials/{cred_id}/register-models",
        json={
            "models": [
                {"name": "gpt-4o-mini", "provider": "openai", "model_type": "language"},
                {"name": "gpt-4o", "provider": "openai", "model_type": "language"},
                {"name": "text-embedding-3-small", "provider": "openai", "model_type": "embedding"},
            ]
        },
        timeout=15,
    )
    r.raise_for_status()
    print(f"  모델 등록: {r.json()}")

    auto = requests.post(f"{BASE_URL}/api/models/auto-assign", timeout=10)
    print(f"  기본 모델 자동 배정: {auto.json().get('assigned', {})}")


def upload_documents() -> int:
    existing_sources = requests.get(f"{BASE_URL}/api/sources", timeout=5).json()
    existing_titles = {s.get("title", "") for s in existing_sources}

    docs = list(SAMPLES_DIR.glob("*.md")) + list(NOTION_DIR.glob("*.md"))
    uploaded = 0
    for doc in docs:
        title = doc.stem
        if title in existing_titles or f"{title} [embedded]" in existing_titles:
            print(f"  SKIP (기존): {title}")
            continue
        content = doc.read_text(encoding="utf-8")
        r = requests.post(
            f"{BASE_URL}/api/sources/json",
            json={"type": "text", "title": title, "content": content, "embed": True},
            timeout=30,
        )
        if r.status_code == 200:
            print(f"  OK {title} -> {r.json().get('id')}")
            uploaded += 1
        else:
            print(f"  ERR {title}: {r.status_code}")
    return uploaded


def main() -> None:
    print(f"Open Notebook: {BASE_URL}")

    if not check_health():
        print(
            "[오류] Open Notebook이 실행 중이 아닙니다.\n\n"
            "실행 방법:\n"
            "  1. SurrealDB v2 시작:\n"
            "     ~/.surrealdb/surreal start --user root --pass root "
            "--bind 0.0.0.0:8000 rocksdb:/tmp/surreal_data/db\n"
            "  2. API 서버 시작 (/tmp/open-notebook 에서):\n"
            "     uv run --env-file .env uvicorn api.main:app --host 0.0.0.0 --port 5055\n"
            "  3. Worker 시작:\n"
            "     uv run --env-file .env surreal-commands-worker --import-modules commands\n"
        )
        sys.exit(1)

    print("[1/3] OpenAI credential 등록...")
    cred_id = register_openai()

    print("[2/3] 모델 등록...")
    register_models(cred_id)

    print("[3/3] 정책 문서 업로드...")
    uploaded = upload_documents()
    print(f"  {uploaded}개 신규 문서 업로드 완료")

    models = requests.get(f"{BASE_URL}/api/models", timeout=5).json()
    sources = requests.get(f"{BASE_URL}/api/sources", timeout=5).json()
    print(f"\n완료: 모델 {len(models)}개 / 소스 {len(sources)}개")
    print(f"Streamlit 앱에서 'Open Notebook' 백엔드를 선택하세요.")


if __name__ == "__main__":
    main()
