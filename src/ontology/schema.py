"""사내 규정집 온톨로지 스키마 — 개념(노드)과 관계(엣지) 정의."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ConceptType(str, Enum):
    POLICY_DOMAIN = "정책영역"
    RULE = "규칙"
    ACTOR = "행위자"
    CONDITION = "조건"
    VALUE = "수치한도"
    PROCEDURE = "절차"
    DOCUMENT = "문서"


class RelationType(str, Enum):
    HAS_RULE = "규칙포함"
    APPLIES_TO = "적용대상"
    REQUIRES = "필요조건"
    HAS_LIMIT = "한도"
    FOLLOWS = "따르는절차"
    DEFINED_IN = "문서출처"
    RELATED_TO = "관련"
    MANAGED_BY = "관리주체"


@dataclass
class OntologyNode:
    id: str
    label: str
    concept_type: ConceptType
    aliases: list[str]
    description: str = ""


@dataclass
class OntologyEdge:
    source_id: str
    target_id: str
    relation: RelationType
    weight: float = 1.0


# ── 씨앗 노드 ────────────────────────────────────────────────────────────────

SEED_NODES: list[OntologyNode] = [
    # 정책 영역
    OntologyNode("annual_leave", "연차휴가", ConceptType.POLICY_DOMAIN,
                 ["연차", "유급휴가", "연차휴가", "휴가", "반차"]),
    OntologyNode("sick_leave", "병가", ConceptType.POLICY_DOMAIN,
                 ["병가", "의료휴가", "질병휴가"]),
    OntologyNode("parental_leave", "육아휴직", ConceptType.POLICY_DOMAIN,
                 ["육아휴직", "출산휴가", "육아"]),
    OntologyNode("special_leave", "경조사휴가", ConceptType.POLICY_DOMAIN,
                 ["경조사", "결혼", "장례", "조의"]),
    OntologyNode("business_trip", "출장비", ConceptType.POLICY_DOMAIN,
                 ["출장", "출장비", "여비", "숙박비", "식비", "교통비"]),
    OntologyNode("it_account", "IT계정", ConceptType.POLICY_DOMAIN,
                 ["계정", "비밀번호", "패스워드", "it계정", "mfa", "다단계인증"]),
    OntologyNode("attendance", "근태", ConceptType.POLICY_DOMAIN,
                 ["근태", "초과근무", "야근", "출퇴근", "지각", "결근"]),
    OntologyNode("remote_work", "재택근무", ConceptType.POLICY_DOMAIN,
                 ["재택", "재택근무", "원격근무"]),
    OntologyNode("overtime", "초과근무", ConceptType.POLICY_DOMAIN,
                 ["초과근무", "야간근무", "휴일근무", "연장근무"]),

    # 행위자
    OntologyNode("employee", "임직원", ConceptType.ACTOR,
                 ["임직원", "직원", "근로자", "사원", "신입사원"]),
    OntologyNode("hr_team", "HR팀", ConceptType.ACTOR,
                 ["hr팀", "인사팀", "hr", "인사"]),
    OntologyNode("it_team", "IT팀", ConceptType.ACTOR,
                 ["it팀", "it헬프데스크", "헬프데스크"]),
    OntologyNode("security_team", "정보보안팀", ConceptType.ACTOR,
                 ["정보보안팀", "보안팀", "정보보안"]),
    OntologyNode("manager", "팀장", ConceptType.ACTOR,
                 ["팀장", "직속상사", "상사", "승인자"]),
    OntologyNode("finance_team", "재경팀", ConceptType.ACTOR,
                 ["재경팀", "회계팀", "경리팀"]),

    # 절차
    OntologyNode("apply_procedure", "신청절차", ConceptType.PROCEDURE,
                 ["신청", "신청절차", "myhr", "hr시스템"]),
    OntologyNode("approval_procedure", "승인절차", ConceptType.PROCEDURE,
                 ["승인", "결재", "허가"]),
    OntologyNode("reimbursement_procedure", "정산절차", ConceptType.PROCEDURE,
                 ["정산", "환급", "청구", "myexpense"]),

    # 수치·한도
    OntologyNode("leave_15days", "연 15일 한도", ConceptType.VALUE,
                 ["15일", "연간 15"]),
    OntologyNode("leave_25days", "최대 25일", ConceptType.VALUE,
                 ["25일", "최대 25"]),
    OntologyNode("trip_lodging_120k", "숙박비 12만원", ConceptType.VALUE,
                 ["120,000", "12만원", "숙박비 한도"]),
    OntologyNode("overtime_150pct", "초과근무 150%", ConceptType.VALUE,
                 ["150%", "통상임금의 150"]),
    OntologyNode("overtime_200pct", "야간·휴일 200%", ConceptType.VALUE,
                 ["200%", "통상임금의 200"]),
    OntologyNode("pw_90days", "비밀번호 90일 주기", ConceptType.VALUE,
                 ["90일", "90일마다"]),
    OntologyNode("remote_2days", "주 2일 재택", ConceptType.VALUE,
                 ["주 2일", "2일 재택"]),

    # 조건
    OntologyNode("min_1yr", "근속 1년 이상", ConceptType.CONDITION,
                 ["1년 이상", "1년 초과", "입사 1년"]),
    OntologyNode("min_3yr", "근속 3년 이상", ConceptType.CONDITION,
                 ["3년 이상", "3년 초과"]),
    OntologyNode("child_under8", "만 8세 이하 자녀", ConceptType.CONDITION,
                 ["만 8세", "초등학교 2학년", "8세 이하"]),
]

# ── 씨앗 엣지 ────────────────────────────────────────────────────────────────

SEED_EDGES: list[OntologyEdge] = [
    # 연차휴가 관계
    OntologyEdge("annual_leave", "leave_15days", RelationType.HAS_LIMIT),
    OntologyEdge("annual_leave", "leave_25days", RelationType.HAS_LIMIT),
    OntologyEdge("annual_leave", "min_1yr", RelationType.REQUIRES),
    OntologyEdge("annual_leave", "apply_procedure", RelationType.FOLLOWS),
    OntologyEdge("annual_leave", "approval_procedure", RelationType.FOLLOWS),
    OntologyEdge("annual_leave", "hr_team", RelationType.MANAGED_BY),
    OntologyEdge("annual_leave", "employee", RelationType.APPLIES_TO),
    OntologyEdge("annual_leave", "sick_leave", RelationType.RELATED_TO),
    OntologyEdge("annual_leave", "parental_leave", RelationType.RELATED_TO),
    OntologyEdge("annual_leave", "special_leave", RelationType.RELATED_TO),

    # 육아휴직
    OntologyEdge("parental_leave", "child_under8", RelationType.REQUIRES),
    OntologyEdge("parental_leave", "employee", RelationType.APPLIES_TO),
    OntologyEdge("parental_leave", "hr_team", RelationType.MANAGED_BY),

    # 출장비
    OntologyEdge("business_trip", "trip_lodging_120k", RelationType.HAS_LIMIT),
    OntologyEdge("business_trip", "reimbursement_procedure", RelationType.FOLLOWS),
    OntologyEdge("business_trip", "finance_team", RelationType.MANAGED_BY),
    OntologyEdge("business_trip", "employee", RelationType.APPLIES_TO),
    OntologyEdge("business_trip", "manager", RelationType.REQUIRES),

    # IT계정
    OntologyEdge("it_account", "pw_90days", RelationType.HAS_LIMIT),
    OntologyEdge("it_account", "it_team", RelationType.MANAGED_BY),
    OntologyEdge("it_account", "security_team", RelationType.RELATED_TO),
    OntologyEdge("it_account", "employee", RelationType.APPLIES_TO),

    # 초과근무
    OntologyEdge("overtime", "overtime_150pct", RelationType.HAS_LIMIT),
    OntologyEdge("overtime", "overtime_200pct", RelationType.HAS_LIMIT),
    OntologyEdge("overtime", "manager", RelationType.REQUIRES),
    OntologyEdge("overtime", "attendance", RelationType.RELATED_TO),

    # 재택근무
    OntologyEdge("remote_work", "remote_2days", RelationType.HAS_LIMIT),
    OntologyEdge("remote_work", "manager", RelationType.REQUIRES),
    OntologyEdge("remote_work", "attendance", RelationType.RELATED_TO),

    # 절차 관계
    OntologyEdge("apply_procedure", "manager", RelationType.FOLLOWS),
    OntologyEdge("approval_procedure", "manager", RelationType.APPLIES_TO),
    OntologyEdge("reimbursement_procedure", "finance_team", RelationType.MANAGED_BY),
]
