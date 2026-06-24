"""GraphRAG 체인 — 온톨로지 그래프 + FAISS 벡터 검색 결합."""

from __future__ import annotations

import os
from typing import Generator

import networkx as nx

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_community.vectorstores import FAISS
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.ontology.builder import build_default_graph
from src.ontology.schema import ConceptType, OntologyNode, SEED_NODES
from src.parsers.base import ParsedDocument
from src.policy_rag_chain import _is_unsafe

_PROMPT = PromptTemplate.from_template(
    "당신은 사내 정책 전문가입니다. 아래 두 가지 정보를 참고하여 한국어로 답변하세요.\n\n"
    "[온톨로지 관계 그래프]\n{graph_context}\n\n"
    "[문서 원문 조각]\n{doc_context}\n\n"
    "질문: {question}\n\n"
    "답변 시 온톨로지 관계를 근거로 논리적 흐름을 설명하고, "
    "원문 조각에서 구체적 수치나 절차를 인용하세요.\n\n답변:"
)


class GraphRAGChain:
    def __init__(self, docs: list[ParsedDocument], openai_api_key: str | None = None) -> None:
        self._api_key = openai_api_key or os.environ.get("OPENAI_API_KEY", "")
        self.graph = build_default_graph(docs)
        self._retriever = self._build_faiss(docs)
        self._llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=self._api_key,
                               streaming=True)
        self._chain = self._build_chain()
        self._last_sources: list[str] = []
        self._last_graph_context: str = ""

    # ── 내부 빌더 ────────────────────────────────────────────────────────────

    def _build_faiss(self, docs: list[ParsedDocument]):
        splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
        lc_docs: list[Document] = []
        for d in docs:
            for chunk in splitter.split_text(d.markdown):
                lc_docs.append(Document(
                    page_content=chunk,
                    metadata={"source": d.title, "source_id": d.source_id},
                ))
        if not lc_docs:
            return None
        embeddings = OpenAIEmbeddings(api_key=self._api_key)
        return FAISS.from_documents(lc_docs, embeddings).as_retriever(
            search_kwargs={"k": 4}
        )

    def _build_chain(self):
        if self._retriever is None:
            return None

        def _retrieve_context(query: str) -> dict:
            graph_ctx = self._graph_context(query)
            retrieved = self._retriever.invoke(query)
            self._last_sources = list(
                {doc.metadata.get("source", "알 수 없음") for doc in retrieved}
            )
            self._last_graph_context = graph_ctx
            return {
                "graph_context": graph_ctx,
                "doc_context": "\n\n".join(d.page_content for d in retrieved),
                "question": query,
            }

        return (
            RunnablePassthrough() | _retrieve_context | _PROMPT | self._llm | StrOutputParser()
        )

    # ── 온톨로지 탐색 ────────────────────────────────────────────────────────

    def _match_concepts(self, query: str) -> list[str]:
        q = query.lower()
        matched: list[str] = []
        for node_id, data in self.graph.nodes(data=True):
            node: OntologyNode | None = data.get("obj")
            if node and node.concept_type != ConceptType.DOCUMENT:
                if any(alias in q for alias in node.aliases):
                    matched.append(node_id)
        return matched

    def _graph_context(self, query: str, depth: int = 2) -> str:
        seed_ids = self._match_concepts(query)
        if not seed_ids:
            return "해당 질문에 매칭되는 온톨로지 개념 없음"

        lines: list[str] = []
        visited: set[str] = set()
        queue: list[tuple[str, int]] = [(nid, 0) for nid in seed_ids]

        while queue:
            node_id, d = queue.pop(0)
            if node_id in visited or d > depth:
                continue
            visited.add(node_id)
            node: OntologyNode | None = self.graph.nodes[node_id].get("obj")
            if node is None:
                continue
            for _, target_id, edge_data in self.graph.out_edges(node_id, data=True):
                rel = edge_data.get("relation", "관련")
                target: OntologyNode | None = self.graph.nodes.get(target_id, {}).get("obj")
                if target and target.concept_type != ConceptType.DOCUMENT:
                    lines.append(f"• [{node.label}] ─{rel}→ [{target.label}]")
                    queue.append((target_id, d + 1))

        return "\n".join(lines) if lines else "관련 온톨로지 관계 없음"

    # ── 공개 인터페이스 ──────────────────────────────────────────────────────

    def ask(self, query: str) -> dict:
        if _is_unsafe(query):
            return {"answer": "⚠️ 보안 정책 위반 가능성이 있어 답변할 수 없습니다.",
                    "sources": [], "unsafe": True}
        if self._chain is None:
            return {"answer": "문서가 없습니다.", "sources": [], "unsafe": False}
        answer = self._chain.invoke(query)
        return {"answer": answer, "sources": self._last_sources,
                "graph_context": self._last_graph_context, "unsafe": False}

    def ask_stream(self, query: str) -> Generator[str, None, None]:
        if _is_unsafe(query):
            yield "⚠️ 보안 정책 위반 가능성이 있어 답변할 수 없습니다."
            return
        if self._chain is None:
            yield "문서가 없습니다."
            return
        # graph_context 와 sources 를 미리 계산해둠
        self._graph_context(query)  # side-effect: _last_graph_context 저장
        retrieved = self._retriever.invoke(query)
        self._last_sources = list(
            {doc.metadata.get("source", "알 수 없음") for doc in retrieved}
        )
        ctx = {
            "graph_context": self._last_graph_context,
            "doc_context": "\n\n".join(d.page_content for d in retrieved),
            "question": query,
        }
        yield from (_PROMPT | self._llm | StrOutputParser()).stream(ctx)
