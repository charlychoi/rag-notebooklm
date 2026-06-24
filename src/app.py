"""Internal Policy RAG Chatbot — Streamlit UI."""
import logging
import os
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from src.document_loader import load_documents, summarize, save_uploaded_file, SAMPLES_DIR, NOTION_DIR, UPLOAD_DIR
from src.policy_rag_chain import PolicyRAGChain, _is_unsafe
from src.integrations.open_notebook_client import OpenNotebookClient
from src.ontology.graph_rag import GraphRAGChain

logging.basicConfig(level=logging.INFO)

OPEN_NOTEBOOK_URL = os.getenv("OPEN_NOTEBOOK_API_URL", "http://127.0.0.1:5055")


def _get_file_hash() -> str:
    """data/ 디렉토리의 파일 목록+크기로 해시 생성 — 변경 시에만 체인 재빌드."""
    import hashlib
    exts = {".pdf", ".docx", ".md", ".txt"}
    parts = []
    for root in [SAMPLES_DIR, NOTION_DIR, UPLOAD_DIR]:
        if root.exists():
            for f in sorted(root.rglob("*")):
                if f.suffix.lower() in exts:
                    parts.append(f"{f.name}:{f.stat().st_size}")
    return hashlib.md5("|".join(parts).encode()).hexdigest()[:12]

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

# --- 사이드바 ---
with st.sidebar:
    # ── 문서 업로드 ──────────────────────────────────────────
    st.header("📤 문서 업로드")
    uploaded_files = st.file_uploader(
        "규정집 파일을 업로드하세요",
        type=["pdf", "docx", "txt", "md"],
        accept_multiple_files=True,
        help="PDF · DOCX · TXT · MD 형식 지원. 저장 버튼을 누르면 색인됩니다.",
    )
    if uploaded_files:
        if st.button("💾 저장 및 색인", type="primary"):
            saved, failed = [], []
            for uf in uploaded_files:
                try:
                    save_uploaded_file(uf)
                    saved.append(uf.name)
                except Exception as e:
                    failed.append(f"{uf.name}: {e}")
            if failed:
                st.error("\n".join(failed))
            if saved:
                st.toast(f"✅ {len(saved)}개 저장 완료! 다음 질의부터 반영됩니다.", icon="📄")
                st.session_state["doc_version"] = _get_file_hash()
                st.rerun()

    st.markdown("---")

    # ── 문서 현황 ─────────────────────────────────────────────
    st.header("📂 문서 현황")
    if st.button("🔄 문서 다시 로드"):
        st.session_state["doc_version"] = _get_file_hash()
        st.rerun()

    # 업로드 파일 목록
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    uploaded_list = sorted(UPLOAD_DIR.glob("*.*"))
    if uploaded_list:
        with st.expander(f"업로드된 파일 ({len(uploaded_list)}개)"):
            for f in uploaded_list:
                col_f, col_del = st.columns([4, 1])
                col_f.markdown(f"📄 {f.name}")
                if col_del.button("🗑", key=f"del_{f.name}"):
                    f.unlink()
                    st.session_state["doc_version"] = _get_file_hash()
                    st.rerun()

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


@st.cache_resource(show_spinner="문서 색인 중... (채팅은 완료 후 가능)")
def get_chain(file_hash: str):  # 해시가 같으면 캐시 재사용, 달라지면 재색인
    docs = load_documents()
    summary = summarize(docs)
    return PolicyRAGChain(docs), GraphRAGChain(docs), summary


# 현재 파일 해시 (세션 state 에 없으면 계산)
if "doc_version" not in st.session_state:
    st.session_state["doc_version"] = _get_file_hash()

chain, graph_chain, doc_summary = get_chain(st.session_state["doc_version"])

# 문서 카운트 표시
col1, col2, col3, col4 = st.columns(4)
col1.metric("전체 문서", doc_summary["total"])
col2.metric("샘플 문서", doc_summary["samples"])
if doc_summary["notion"] == 0:
    col3.metric("Notion 문서", "0", delta="미연결", delta_color="off")
else:
    col3.metric("Notion 문서", doc_summary["notion"])
col4.metric("업로드 문서", doc_summary.get("uploads", 0))

st.markdown("---")

# --- FAQ 메뉴 ---
FAQ = {
    "🟢 심플": [
        "연차는 1년에 며칠 주어지나요?",
        "연차는 며칠 전에 신청해야 하나요?",
        "반차 신청은 어떻게 하나요?",
        "비밀번호는 얼마나 자주 바꿔야 하나요?",
        "재택근무는 주 최대 몇 일 가능한가요?",
    ],
    "🟡 중간": [
        "국내 출장 2박 3일 시 숙박비·식비·일비를 합산하면 총 얼마까지 받을 수 있나요?",
        "비밀번호를 5번 틀려 계정이 잠겼을 때 해제 절차는 무엇인가요?",
        "초과근무 수당과 보상휴가 중 어느 것이 유리한지 계산 방법을 알려주세요.",
        "육아휴직 첫 3개월 급여는 얼마나 지급되나요?",
        "경조사 휴가 종류별 일수를 모두 알려주세요.",
    ],
    "🔴 복잡": [
        "입사 2년차 직원이 병가를 30일 쓰면 그 해 남은 연차는 몇 개인가요?",
        "출장 중 야간 초과근무를 3시간 했을 때 수당 계산 방법과 정산 절차를 알려주세요.",
        "신입사원이 입사 첫 달에 출장을 가면 출장비·연차·초과근무 중 어떤 항목이 적용되지 않나요?",
        "재택근무 중 업무용 노트북이 고장났을 때 IT 계정 보안, 장비 대체, 근태 처리를 동시에 어떻게 해야 하나요?",
        "경조사 휴가와 연차가 겹치는 날이 있으면 어느 쪽으로 처리되며, 팀장 부재 시 승인은 어떻게 받나요?",
    ],
}

with st.expander("💡 FAQ — 자주 묻는 질문 예시", expanded=False):
    tabs = st.tabs(list(FAQ.keys()))
    for tab, (level, questions) in zip(tabs, FAQ.items()):
        with tab:
            for q in questions:
                if st.button(q, key=f"faq_{q[:20]}"):
                    st.session_state["faq_prompt"] = q
                    st.rerun()

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

# FAQ 버튼 클릭 시 자동 입력
_faq_auto = st.session_state.pop("faq_prompt", None)

if prompt := (st.chat_input("정책에 대해 궁금한 점을 물어보세요...") or _faq_auto):
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
