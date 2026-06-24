"""문서에서 NetworkX 지식 그래프를 구축하는 빌더."""

from __future__ import annotations

import re
from typing import Optional

import networkx as nx

from src.ontology.schema import (
    ConceptType, OntologyEdge, OntologyNode, RelationType,
    SEED_NODES, SEED_EDGES,
)
from src.parsers.base import ParsedDocument

# 문서 텍스트에서 동적으로 추출하는 패턴
_PATTERNS: list[tuple[str, ConceptType, str]] = [
    (r"(\d+)\s*일\s*(한도|이내|이하|까지)", ConceptType.VALUE, "days_limit"),
    (r"(\d+)\s*만\s*원", ConceptType.VALUE, "won_limit"),
    (r"(\d+)\s*년\s*이상", ConceptType.CONDITION, "yr_condition"),
    (r"(\d+)\s*개월\s*이상", ConceptType.CONDITION, "month_condition"),
    (r"통상임금의\s*(\d+)%", ConceptType.VALUE, "pct_wage"),
]


class OntologyBuilder:
    def __init__(self) -> None:
        self.graph: nx.DiGraph = nx.DiGraph()
        self._load_seed()

    def _load_seed(self) -> None:
        for node in SEED_NODES:
            self.graph.add_node(node.id, obj=node, label=node.label,
                                concept_type=node.concept_type.value)
        for edge in SEED_EDGES:
            self.graph.add_edge(
                edge.source_id, edge.target_id,
                relation=edge.relation.value,
                weight=edge.weight,
            )

    def build_from_docs(self, docs: list[ParsedDocument]) -> nx.DiGraph:
        for doc in docs:
            self._link_document(doc)
        return self.graph

    def _link_document(self, doc: ParsedDocument) -> None:
        doc_node = OntologyNode(
            id=f"doc_{doc.source_id}",
            label=doc.title,
            concept_type=ConceptType.DOCUMENT,
            aliases=[doc.title, doc.source_id],
        )
        self.graph.add_node(doc_node.id, obj=doc_node, label=doc_node.label,
                            concept_type=doc_node.concept_type.value)

        text_lower = doc.markdown.lower()
        for node_id, node_data in list(self.graph.nodes(data=True)):
            node: Optional[OntologyNode] = node_data.get("obj")
            if node is None or node.concept_type == ConceptType.DOCUMENT:
                continue
            if any(alias in text_lower for alias in node.aliases):
                self.graph.add_edge(
                    node_id, doc_node.id,
                    relation=RelationType.DEFINED_IN.value,
                    weight=1.0,
                )

        self._extract_value_nodes(doc)

    def _extract_value_nodes(self, doc: ParsedDocument) -> None:
        text = doc.markdown
        for pattern, ctype, prefix in _PATTERNS:
            for m in re.finditer(pattern, text):
                val = m.group(1)
                node_id = f"{prefix}_{val}_{doc.source_id[:8]}"
                if node_id not in self.graph:
                    label = m.group(0).strip()
                    new_node = OntologyNode(
                        id=node_id, label=label,
                        concept_type=ctype, aliases=[label],
                    )
                    self.graph.add_node(node_id, obj=new_node,
                                        label=label, concept_type=ctype.value)
                self.graph.add_edge(
                    f"doc_{doc.source_id}", node_id,
                    relation=RelationType.HAS_LIMIT.value
                    if ctype == ConceptType.VALUE else RelationType.REQUIRES.value,
                    weight=0.8,
                )


def build_default_graph(docs: list[ParsedDocument]) -> nx.DiGraph:
    builder = OntologyBuilder()
    return builder.build_from_docs(docs)
