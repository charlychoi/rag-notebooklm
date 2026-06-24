"""Internal Policy RAG Chatbot — Streamlit UI."""
import logging
import os
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from src.document_loader import load_documents, summarize, SAMPLES_DIR, NOTION_DIR
from src.policy_rag_chain import PolicyRAGChain, _is_unsafe
from src.integrations.open_notebook_client import OpenNotebookClient
from src.ontology.graph_rag import GraphRAGChain

logging.basicConfig(level=logging.INFO)

OPEN_NOTEBOOK_URL = os.getenv("OPEN_NOTEBOOK_API_URL", "http://127.0.0.1:5055")

st.set_page_config(page_title="사내 정책 Q&A", page_icon="📋", layout="wide")
st.title("📋 사내 정책 Q&A (RAG)")
st.caption("내부 정책 문서를 기반으로 답변합니다. 법적 효력이 있는 HR/법무 의견이 아닙니다.")

# --- Open Notebook 상태 ---
@st.cache_resource(show_spinner=False, ttl=30)
def get_open_notebook_client() -> OpenNotebookClient:
    return OpenNotebookClient(OPEN_NOTEBOOK_URL)

on_client = get_open_notebook_client()
on_healthy = on_client.is_healthy()
on_model_count = on_client.model_count() if on_healthy else 0
on_source_count = on_client.source_count() if on_healthy else 0

if on_healthy and on_model_count > 0:
    st.success(
        f"Open Notebook 연결됨 — 모델 {on_model_count}개 / 소스 {on_source_count}개 "
        f"({OPEN_NOTEBOOK_URL})"
    )
elif on_healthy:
    st.warning(f"Open Notebook 실행 중이지만 모델 미등록 ({OPEN_NOTEBOOK_URL})")
else:
    st.info("Open Notebook 미실행 — FAISS(OpenAI) 직접 사용 중")

# --- 사이드바: 문서 현황 ---
with st.sidebar:
    st.header("📂 문서 현황")
    if st.button("🔄 문서 다시 로드"):
        st.cache_resource.clear()
        st.rerun()

    st.markdown("---")
    st.markdown(f"**샘플 디렉토리:** `{SAMPLES_DIR}`")
    st.markdown(f"**Notion 내보내기:** `{NOTION_DIR}`")
    st.markdown("---")

    # RAG 백엔드 선택
    st.header("⚙️ RAG 백엔드")
    if on_healthy and on_model_count > 0 and on_source_count > 0:
        backend_options = ["Open Notebook", "FAISS (직접)", "GraphRAG (온톨로지)"]
    else:
        backend_options = ["FAISS (직접)", "GraphRAG (온톨로지)"]
    selected_backend = st.radio("백엔드 선택", backend_options, index=0)

    st.markdown("---")
    st.info("Notion 문서를 추가하려면:\n```\npython scripts/import_composio_notion_docs.py\n```")


@st.cache_resource(show_spinner="문서 로딩 중...")
def get_chain():
    docs = load_documents()
    summary = summarize(docs)
    return PolicyRAGChain(docs), GraphRAGChain(docs), summary


chain, graph_chain, doc_summary = get_chain()

# 문서 카운트 표시
col1, col2, col3 = st.columns(3)
col1.metric("전체 문서", doc_summary["total"])
col2.metric("샘플 문서", doc_summary["samples"])
if doc_summary["notion"] == 0:
    col3.metric("Notion 문서", "0", delta="미연결/미색인", delta_color="off")
else:
    col3.metric("Notion 문서", doc_summary["notion"])

st.markdown("---")

# --- 채팅 UI ---
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sources"):
            with st.expander("📎 출처"):
                for s in msg["sources"]:
                    st.markdown(f"- {s}")

if prompt := st.chat_input("정책에 대해 궁금한 점을 물어보세요..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        use_open_notebook = (
            selected_backend == "Open Notebook"
            and on_healthy
            and on_model_count > 0
            and on_source_count > 0
        )

        answer = ""
        sources = []
        backend_label = ""

        if use_open_notebook:
            # Open Notebook SSE 스트리밍
            import json as _json
            backend_label = "Open Notebook"
            try:
                import requests as _req
                resp = _req.post(
                    f"{OPEN_NOTEBOOK_URL}/api/search/ask",
                    json={
                        "question": prompt,
                        "strategy_model": os.getenv("OPEN_NOTEBOOK_STRATEGY_MODEL"),
                        "answer_model": os.getenv("OPEN_NOTEBOOK_ANSWER_MODEL"),
                        "final_answer_model": os.getenv("OPEN_NOTEBOOK_FINAL_ANSWER_MODEL"),
                    },
                    stream=True,
                    timeout=60,
                )
                placeholder = st.empty()
                for raw in resp.iter_lines():
                    if not raw:
                        continue
                    line = raw.decode("utf-8", errors="replace")
                    if not line.startswith("data: "):
                        continue
                    try:
                        event = _json.loads(line[6:])
                        t = event.get("type", "")
                        if t == "final_answer":
                            answer = event.get("content") or event.get("answer", "")
                            placeholder.markdown(answer)
                        elif t == "complete":
                            answer = answer or event.get("final_answer", "")
                    except Exception:
                        pass
            except Exception as e:
                st.warning(f"Open Notebook 오류 ({e}) — FAISS로 폴백합니다.")
                use_open_notebook = False
                backend_label = "FAISS (폴백)"

        if not use_open_notebook:
            use_graph_rag = selected_backend == "GraphRAG (온톨로지)"

            if _is_unsafe(prompt):
                answer = "⚠️ 해당 질문은 보안 정책 위반 가능성이 있어 답변할 수 없습니다. 정보보안팀에 문의하세요."
                st.warning(answer)
            elif use_graph_rag:
                backend_label = "GraphRAG (온톨로지)"
                answer = st.write_stream(graph_chain.ask_stream(prompt))
                sources = getattr(graph_chain, "_last_sources", [])
            else:
                backend_label = backend_label or "FAISS (직접)"
                answer = st.write_stream(chain.ask_stream(prompt))
                sources = getattr(chain, "_last_sources", [])

        if answer and not answer.startswith("⚠️"):
            st.caption(f"백엔드: {backend_label}")
            # GraphRAG 전용: 온톨로지 관계 expander
            if selected_backend == "GraphRAG (온톨로지)":
                graph_ctx = getattr(graph_chain, "_last_graph_context", "")
                if graph_ctx and graph_ctx != "해당 질문에 매칭되는 온톨로지 개념 없음":
                    with st.expander("🕸️ 온톨로지 관계"):
                        st.code(graph_ctx, language="text")
            if sources:
                with st.expander("📎 출처"):
                    for s in sources:
                        st.markdown(f"- {s}")

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
        "sources": sources,
    })
