"""Open Notebook API 클라이언트 (http://127.0.0.1:5055)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Generator


@dataclass
class OpenNotebookAnswer:
    answer: str
    sources: list[str] = field(default_factory=list)


class OpenNotebookClient:
    def __init__(self, base_url: str = "http://127.0.0.1:5055") -> None:
        self._base_url = base_url.rstrip("/")

    def is_healthy(self) -> bool:
        try:
            import requests

            resp = requests.get(f"{self._base_url}/health", timeout=3)
            return resp.status_code == 200
        except Exception:
            return False

    def model_count(self) -> int:
        try:
            import requests

            resp = requests.get(f"{self._base_url}/api/models", timeout=5)
            return len(resp.json()) if resp.status_code == 200 else 0
        except Exception:
            return 0

    def source_count(self) -> int:
        try:
            import requests

            resp = requests.get(f"{self._base_url}/api/sources", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                return len(data) if isinstance(data, list) else 0
            return 0
        except Exception:
            return 0

    def _get_default_models(self) -> dict[str, str]:
        import requests

        resp = requests.get(f"{self._base_url}/api/models", timeout=5)
        models = resp.json()
        lang_models = [m for m in models if m.get("model_type") in ("language", None)]
        if not lang_models:
            return {}
        default_id = lang_models[0]["id"]
        small_id = next(
            (m["id"] for m in lang_models if "mini" in m.get("name", "")),
            default_id,
        )
        return {
            "strategy": small_id,
            "answer": small_id,
            "final": default_id,
        }

    def ask(
        self,
        question: str,
        strategy_model: str | None = None,
        answer_model: str | None = None,
        final_answer_model: str | None = None,
        timeout: int = 60,
    ) -> OpenNotebookAnswer:
        import os
        import requests

        strategy_model = strategy_model or os.getenv("OPEN_NOTEBOOK_STRATEGY_MODEL")
        answer_model = answer_model or os.getenv("OPEN_NOTEBOOK_ANSWER_MODEL")
        final_answer_model = final_answer_model or os.getenv("OPEN_NOTEBOOK_FINAL_ANSWER_MODEL")

        if not (strategy_model and answer_model and final_answer_model):
            defaults = self._get_default_models()
            strategy_model = strategy_model or defaults.get("strategy", "")
            answer_model = answer_model or defaults.get("answer", "")
            final_answer_model = final_answer_model or defaults.get("final", "")

        resp = requests.post(
            f"{self._base_url}/api/search/ask",
            json={
                "question": question,
                "strategy_model": strategy_model,
                "answer_model": answer_model,
                "final_answer_model": final_answer_model,
            },
            stream=True,
            timeout=timeout,
        )
        resp.raise_for_status()

        final_answer = ""
        for raw in resp.iter_lines():
            if not raw:
                continue
            line = raw.decode("utf-8", errors="replace")
            if not line.startswith("data: "):
                continue
            try:
                event = json.loads(line[6:])
            except json.JSONDecodeError:
                continue

            t = event.get("type", "")
            if t == "final_answer":
                final_answer = event.get("answer") or event.get("content", "")
            elif t == "complete":
                final_answer = final_answer or event.get("final_answer", "")

        return OpenNotebookAnswer(answer=final_answer)

    def upload_document(self, title: str, content: str, embed: bool = True) -> str:
        """텍스트 문서를 Open Notebook에 업로드하고 source ID를 반환합니다."""
        import requests

        resp = requests.post(
            f"{self._base_url}/api/sources/json",
            json={"type": "text", "title": title, "content": content, "embed": embed},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json().get("id", "")
