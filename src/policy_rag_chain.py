"""FAISS + OpenAI 기반 RAG 체인."""
from __future__ import annotations

import logging
import os
from pathlib import Path

from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

from src.parsers.base import ParsedDocument

logger = logging.getLogger(__name__)

# 안전하지 않은 쿼리 키워드
UNSAFE_KEYWORDS = [
    "dlp 우회", "dlp에 안 걸리", "탐지 우회", "보안 우회", "감시 피하",
    "몰래 보내", "암호화해서 숨기", "안 걸리게",
]


def _is_unsafe(query: str) -> bool:
    q = query.lower()
    return any(kw in q for kw in UNSAFE_KEYWORDS)


class PolicyRAGChain:
    def __init__(self, docs: list[ParsedDocument], openai_api_key: str | None = None):
        self._api_key = openai_api_key or os.environ.get("OPENAI_API_KEY", "")
        self._chain, self._retriever = self._build(docs)

    def _build(self, docs: list[ParsedDocument]):
        splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
        langchain_docs: list[Document] = []
        for d in docs:
            chunks = splitter.split_text(d.markdown)
            for chunk in chunks:
                langchain_docs.append(Document(
                    page_content=chunk,
                    metadata={"source": d.title, "source_id": d.source_id},
                ))

        if not langchain_docs:
            logger.warning("로드된 문서가 없습니다.")
            return None, None

        embeddings = OpenAIEmbeddings(api_key=self._api_key)
        vectorstore = FAISS.from_documents(langchain_docs, embeddings)
        retriever = vectorstore.as_retriever(search_kwargs={"k": 4})

        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=self._api_key)

        prompt = PromptTemplate.from_template(
            "다음 컨텍스트를 참고하여 한국어로 질문에 답변하세요.\n\n"
            "컨텍스트:\n{context}\n\n질문: {question}\n\n답변:"
        )

        def format_docs(retrieved_docs):
            return "\n\n".join(d.page_content for d in retrieved_docs)

        chain = (
            {"context": retriever | format_docs, "question": RunnablePassthrough()}
            | prompt
            | llm
            | StrOutputParser()
        )
        return chain, retriever

    def ask(self, query: str) -> dict:
        if _is_unsafe(query):
            return {
                "answer": "⚠️ 해당 질문은 보안 정책 위반 가능성이 있어 답변할 수 없습니다. 정보보안팀에 문의하세요.",
                "sources": [],
                "unsafe": True,
            }

        if self._chain is None:
            return {
                "answer": "문서가 로드되지 않았습니다. 문서를 먼저 추가해주세요.",
                "sources": [],
                "unsafe": False,
            }

        answer = self._chain.invoke(query)
        retrieved = self._retriever.invoke(query)
        sources = list({doc.metadata.get("source", "알 수 없음") for doc in retrieved})
        return {"answer": answer, "sources": sources, "unsafe": False}

    def ask_stream(self, query: str):
        """토큰 단위 스트리밍 제너레이터. (sources, unsafe) 는 마지막에 sentinel로 전달."""
        if _is_unsafe(query):
            yield "⚠️ 해당 질문은 보안 정책 위반 가능성이 있어 답변할 수 없습니다. 정보보안팀에 문의하세요."
            return

        if self._chain is None:
            yield "문서가 로드되지 않았습니다. 문서를 먼저 추가해주세요."
            return

        retrieved = self._retriever.invoke(query)
        self._last_sources = list({doc.metadata.get("source", "알 수 없음") for doc in retrieved})
        yield from self._chain.stream(query)
