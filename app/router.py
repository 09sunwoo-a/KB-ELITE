"""라우터 — 02 §4. 행동 분류 + 조건 추출을 structured output 한 번으로.

LLM 판단 위에 코드 오버라이드 규칙(01 5-4)을 적용한다:
  ① ask_streak >= 2면 ask여도 search로 전환 (확보된 조건으로 넓게 검색)
  ② compare인데 직전 후보가 2개 미만이고 겹침 요청도 아니면 search로 폴백
"""

from __future__ import annotations

from typing import Literal, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from app.prompts import ROUTER_SYSTEM

load_dotenv()

_llm = None


class RouteResult(BaseModel):
    action: Literal["explain", "ask", "search", "compare"] = Field(
        description="explain: 용어·구조·위험 질문 / ask: 필수 맥락 부족 / "
                    "search: 조건 충분 또는 구체 조건 명시 / compare: 후보 간 비교·보유 겹침 요청")
    action_reason: str = Field(
        description="행동 선택 이유 한 문장(고객 언어, 정중한 해요체)")
    # 조건 추출 (발화에 있는 것만, 추정 금지)
    region_theme: Optional[str] = Field(None, description="지역 또는 테마. 예: 미국, 중국, AI, 반도체, 나스닥")
    target_stock: Optional[str] = Field(None, description="구체 종목명. 예: 엔비디아")
    loss_tolerance: Optional[str] = Field(None, description="손실 감내 표현. 예: 큰 변동 회피")
    horizon: Optional[str] = Field(None, description="투자 기간 표현. 예: 5년 이상")
    fund_type_hint: Optional[str] = Field(None, description="상품 구조 힌트. 예: 월지급·인컴, TDF, 연금 적격, 채권형")
    cost_sensitive: bool = Field(False, description="비용·수수료가 낮은 것을 원함")
    compare_targets: list[int] = Field(default_factory=list, description="'1번과 3번 비교' → [1, 3]")
    overlap_request: bool = Field(False, description="보유 종목·상품과의 겹침 확인 요청")
    term_to_explain: Optional[str] = Field(None, description="explain일 때 설명할 용어")
    # 가드레일 플래그 (02 §7-1)
    delegation_request: bool = Field(False, description="판단 위임 발화 ('뭘 사면 돼요?')")
    out_of_scope: bool = Field(False, description="수익 예측·매수 타이밍 등 비범위 요청")


def _get_llm():
    global _llm
    if _llm is None:
        from langchain_openai import ChatOpenAI
        _llm = ChatOpenAI(model="gpt-4o-mini", temperature=0).with_structured_output(RouteResult)
    return _llm


_CONDITION_KEYS = ["region_theme", "target_stock", "loss_tolerance",
                   "horizon", "fund_type_hint", "cost_sensitive"]


def route_turn(user_message: str, *, conditions: dict | None = None,
               ask_streak: int = 0, last_candidates: list | None = None,
               history_text: str = "") -> tuple[RouteResult, list[str]]:
    """라우팅 실행. 반환: (RouteResult, 적용된 오버라이드 목록)."""
    conditions = conditions or {}
    last_candidates = last_candidates or []

    context_lines = []
    if conditions:
        context_lines.append(f"이미 확인된 조건: {conditions}")
    context_lines.append(f"직전 후보 수: {len(last_candidates)}개")
    context_lines.append(f"연속 질문 횟수: {ask_streak}")
    if history_text:
        context_lines.append(f"최근 대화:\n{history_text}")

    result: RouteResult = _get_llm().invoke([
        ("system", ROUTER_SYSTEM),
        ("user", "\n".join(context_lines) + f"\n\n고객 발화: {user_message}"),
    ])

    overrides = []
    # 규칙 ① — 연속 질문 2턴 제한 (01 5-4 규칙 5)
    if result.action == "ask" and ask_streak >= 2:
        result.action = "search"
        result.action_reason = "여러 번 여쭙기보다, 지금까지 확인된 조건으로 후보를 넓게 찾아 함께 좁혀볼게요."
        overrides.append("ask_streak>=2 → search")
    # 규칙 ② — 비교 대상 부재 시 폴백
    if result.action == "compare" and not result.overlap_request and len(last_candidates) < 2:
        result.action = "search"
        result.action_reason = "아직 비교할 후보가 없어 먼저 조건에 맞는 후보를 찾아볼게요."
        overrides.append("compare without candidates → search")
    return result, overrides


def merged_conditions(prev: dict, r: RouteResult) -> dict:
    """탐색 노트의 조건 병합 — 새로 말한 것만 갱신, 기존 값 유지."""
    out = dict(prev)
    for key in _CONDITION_KEYS:
        val = getattr(r, key)
        if val not in (None, False, ""):
            out[key] = val
    return out
