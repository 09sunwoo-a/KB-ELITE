"""LangGraph 그래프 — 02 §2·§3·§5. 노드 6개, 명시적 분기, 턴당 LLM 호출 2회.

START → router →(조건부)→ explain|ask|search|compare → postprocess → END
"""

from __future__ import annotations

import json
import operator
import warnings
from typing import Annotated, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph, add_messages

from app import prompts, store
from app.router import route_turn, merged_conditions
from app.safety import run_safety
from app.tools import calc_annual_cost, match_overlap, search_funds

load_dotenv()
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic.main")

_llm = None


def _get_llm():
    global _llm
    if _llm is None:
        from langchain_openai import ChatOpenAI
        _llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)
    return _llm


class ExploreState(TypedDict, total=False):
    # 대화
    messages: Annotated[list, add_messages]
    # 안전 기준선 + 고객 컨텍스트 (세션 시작 시 load_profile이 채움, 불변)
    profile: dict
    max_risk_score: int
    # 이번 자금·상품 조건 (라우터가 갱신)
    conditions: dict
    # 탐색 이력
    seen_funds: Annotated[list, operator.add]
    explained_terms: Annotated[list, operator.add]
    last_candidates: list          # 직전 후보 카드 (덮어쓰기)
    # 대화 제어
    action: str
    action_reason: str
    ask_streak: int
    route: dict                    # RouteResult dump (행동 노드가 참조)
    draft_answer: str              # 행동 노드의 응답 초안 — postprocess가 안전 처리 후 확정
    # 시연용 trace — TraceEntry {"node","kind","summary","detail"} (04 6-2)
    trace: Annotated[list, operator.add]
    # 턴 결과 (postprocess가 조립 — 04 6-3 AgentTurnResult의 원천)
    turn: dict


def _t(node, kind, summary, detail=None):
    return {"node": node, "kind": kind, "summary": summary, "detail": detail or {}}


def _last_user_message(state) -> str:
    for m in reversed(state["messages"]):
        if m.type == "human":
            return m.content
    return ""


def _history_text(state, n=6) -> str:
    lines = []
    for m in state["messages"][-n:-1]:
        role = "고객" if m.type == "human" else "길잡이"
        lines.append(f"{role}: {m.content[:80]}")
    return "\n".join(lines)


def _profile_brief(profile: dict) -> str:
    """프롬프트용 프로필 요약 — 복창 금지 지시와 함께 주입."""
    ic = profile.get("investment_context", {})
    contrib = ic.get("contribution", {})
    return json.dumps({
        "연령대": f"{profile['age'] // 10 * 10}대",
        "납입방식": contrib.get("type"),
        "계좌": profile.get("account_context", {}).get("account_type"),
        "보유수": len(profile.get("holdings", [])),
        "응답선호": profile.get("interaction_preference", {}),
    }, ensure_ascii=False)


def _generate(state, instruction: str, context: dict) -> str:
    """응답 생성 LLM 호출 (턴당 1회). 재프레이밍 지시는 여기서 결합 (02 §7-1)."""
    route = state.get("route", {})
    parts = [prompts.COMMON_SYSTEM,
             f"\n[고객 컨텍스트(복창 금지)] {_profile_brief(state['profile'])}", instruction]
    if route.get("delegation_request"):
        parts.append(prompts.REFRAME_DELEGATION)
    if route.get("out_of_scope"):
        parts.append(prompts.REFRAME_OUT_OF_SCOPE)
    msgs = [("system", "\n".join(parts))]
    hist = _history_text(state)
    if hist:
        msgs.append(("user", f"[최근 대화]\n{hist}"))
    msgs.append(("user", f"[제공 데이터]\n{json.dumps(context, ensure_ascii=False)}\n\n"
                         f"[고객 발화]\n{_last_user_message(state)}"))
    return _get_llm().invoke(msgs).content


# ── 노드 ────────────────────────────────────────────────────────────

def router_node(state: ExploreState):
    result, overrides = route_turn(
        _last_user_message(state),
        conditions=state.get("conditions", {}),
        ask_streak=state.get("ask_streak", 0),
        last_candidates=state.get("last_candidates", []),
        history_text=_history_text(state),
    )
    conditions = merged_conditions(state.get("conditions", {}), result)
    dump = result.model_dump()
    extracted = {k: v for k, v in dump.items()
                 if v not in (None, False, [], "") and not k.startswith("action")}
    return {
        "action": result.action,
        "action_reason": result.action_reason,
        "conditions": conditions,
        "route": dump,
        "trace": [_t("router", "route",
                     f"행동 선택: {result.action.upper()} — {result.action_reason}",
                     {"extracted": extracted, "overrides": overrides,
                      "conditions": conditions})],
    }


def explain_node(state: ExploreState):
    route = state.get("route", {})
    query = (route.get("term_to_explain") or "") + " " + _last_user_message(state)
    entry = None
    for t in store.terms():
        if t["term"] in query or any(a in query for a in t["aliases"]):
            entry = t
            break
    context = {"용어사전": entry} if entry else \
        {"용어사전": None, "안내": "사전에 없음 — 일반적인 설명임을 밝힐 것"}
    answer = _generate(state, prompts.EXPLAIN_INSTRUCTION, context)
    return {
        "draft_answer": answer,
        "explained_terms": [entry["term"]] if entry else [],
        "trace": [_t("explain", "tool",
                     f"용어 사전 매칭: {entry['term'] if entry else '없음(일반 지식)'}",
                     {"matched": entry["term"] if entry else None,
                      "misconception": bool(entry and entry["misconception"])})],
    }


_ASK_SLOTS = [
    ("horizon", "이 돈을 언제쯤 사용할 가능성이 있는지 (예: 1~2년 내 / 5년 이상 여유)"),
    ("loss_tolerance", "가격이 크게 출렁이는 것을 감내할 수 있는지 (예: 큰 변동은 피하고 싶다 / 감내 가능)"),
    ("region_theme", "관심 있는 지역이나 테마가 있는지 (예: 미국 / 국내 / 특정 산업)"),
]


def ask_node(state: ExploreState):
    conditions = state.get("conditions", {})
    slot_key, slot_desc = next(((k, d) for k, d in _ASK_SLOTS if k not in conditions),
                               _ASK_SLOTS[-1])
    answer = _generate(state, prompts.ASK_INSTRUCTION,
                       {"확인할 항목": slot_desc, "이미 확인된 조건": conditions})
    return {
        "draft_answer": answer,
        "ask_streak": state.get("ask_streak", 0) + 1,
        "trace": [_t("ask", "info", f"미확보 조건 질문: {slot_key}",
                     {"slot": slot_key, "ask_streak": state.get("ask_streak", 0) + 1})],
    }


def search_node(state: ExploreState):
    conditions = state.get("conditions", {})
    # 벡터 질의 = 사용자 원문 + 추출 조건 결합 (03 §8)
    cond_text = " ".join(f"{k}:{v}" for k, v in conditions.items() if v)
    query_text = f"{_last_user_message(state)} ({cond_text})" if cond_text else _last_user_message(state)
    result = search_funds(conditions, state["max_risk_score"], query_text)
    cards = result["candidates"]
    context = {"applied": result["applied"], "ranking_mode": result["ranking_mode"],
               "blocked": result["blocked"], "excluded_by_risk": result["excluded_by_risk"],
               "candidates": cards}
    # 비용 환산: 비용 민감 + 납입 정보가 있으면 1위 후보 기준으로 계산해 제공 (01 4-6)
    contrib = state["profile"].get("investment_context", {}).get("contribution", {})
    cost_note = None
    if cards and conditions.get("cost_sensitive") and contrib.get("amount"):
        cost_note = calc_annual_cost(
            cards[0]["fee_pct"], contrib["amount"], contrib.get("type", "lumpsum"))
        context["비용환산(그대로 인용할 것)"] = cost_note
    answer = _generate(state, prompts.SEARCH_INSTRUCTION, context)
    trace = [_t("search", "tool",
                f"search_funds: 풀 {result['pool_size']}건 → 후보 {len(cards)}개"
                + (f", 성향 초과 {result['excluded_by_risk']}건 제외" if result["excluded_by_risk"] else "")
                + (", 전부 차단(blocked)" if result["blocked"] else ""),
                {"applied": result["applied"], "ranking_mode": result["ranking_mode"],
                 "excluded_by_risk": result["excluded_by_risk"], "blocked": result["blocked"],
                 "codes": [c["fund_code"] for c in cards]})]
    return {
        "draft_answer": answer,
        "seen_funds": [c["fund_code"] for c in cards],
        "last_candidates": cards,
        "ask_streak": 0,
        "trace": trace,
        "turn": {"candidates": cards,
                 "numeric_note": cost_note,
                 "risk_block": ({"excluded_by_risk": result["excluded_by_risk"],
                                 "blocked": result["blocked"]}
                                if result["excluded_by_risk"] or result["blocked"] else None)},
    }


_COMPARE_ROWS = [("유형", "fund_type"), ("지역", "region"), ("위험등급", "risk_grade"),
                 ("연간 비용(%)", "fee_pct")]


def compare_node(state: ExploreState):
    route = state.get("route", {})
    cands = state.get("last_candidates", [])
    targets = [i for i in route.get("compare_targets", []) if 1 <= i <= len(cands)]
    picked = [cands[i - 1] for i in targets] if targets else cands[:2] if not route.get("overlap_request") else cands
    funds = store.funds()

    comparison = None
    if len(picked) >= 2 and not (route.get("overlap_request") and not targets):
        rows = [{"label": lb, "values": [funds[c["fund_code"]][k] for c in picked]}
                for lb, k in _COMPARE_ROWS]
        rows.append({"label": "12개월 수익률(%)",
                     "values": [funds[c["fund_code"]]["returns"]["m12"] for c in picked]})
        rows.append({"label": "주요 종목(공개분)",
                     "values": [", ".join(funds[c["fund_code"]]["matched_aliases"]) or "정보 없음"
                                for c in picked]})
        rows.append({"label": "기준일", "values": [c["as_of"] for c in picked]})
        comparison = {"fund_codes": [c["fund_code"] for c in picked],
                      "labels": [f"{i}번 {c['name'][:20]}" for i, c in zip(targets or range(1, len(picked) + 1), picked)],
                      "rows": rows}

    overlap = None
    trace = [_t("compare", "info",
                f"비교 대상: {[c['fund_code'] for c in picked]}",
                {"targets": targets})] if comparison else []
    if route.get("overlap_request"):
        holdings = state["profile"].get("holdings", [])
        overlap = [match_overlap(holdings, c["fund_code"]) for c in (picked or cands)]
        for ov in overlap:
            trace.append(_t("compare", "tool",
                            f"match_overlap({ov.get('fund_code')}): "
                            + (f"겹침 {ov['overlap_stocks']}" if ov.get("available") else "보유종목 정보 없음"),
                            ov))

    # LLM에는 겹침 결과만 요약 제공 — checked_holdings(고객 보유 목록)는 혼동 소지가 있어 제외
    overlap_for_llm = [{"펀드명": ov.get("fund_name"),
                        "겹치는_종목(이것만_겹침)": ov.get("overlap_stocks"),
                        "기준": ov.get("basis"), "한계": ov.get("note")}
                       if ov.get("available") else
                       {"펀드명": ov.get("fund_name"), "겹침": "보유종목 정보 비공개"}
                       for ov in overlap] if overlap else None
    context = {"comparison": comparison, "overlap": overlap_for_llm}
    answer = _generate(state, prompts.COMPARE_INSTRUCTION, context)
    return {
        "draft_answer": answer,
        "trace": trace,
        "turn": {"comparison": comparison, "overlap": overlap},
    }


def postprocess_node(state: ExploreState):
    """출력 가드레일(02 §7-2) + 후속 칩 + 턴 결과 확정. 최종 메시지는 여기서만 만든다."""
    action = state.get("action")
    turn = dict(state.get("turn") or {})
    risk_block = turn.get("risk_block")
    cands = state.get("last_candidates", [])

    if risk_block and risk_block.get("blocked"):
        chips = ["가입 가능한 범위에서 찾아보기", "이전 후보로 돌아가기"]
    elif action == "search" and cands:
        chips = ["1번 자세히 보기",
                 "1번과 2번 비교하기" if len(cands) >= 2 else "조건 바꿔서 다시 찾기",
                 "보유상품과 겹침 확인하기" if state["profile"].get("holdings") else "조건 바꿔서 다시 찾기"]
    elif action == "explain":
        chips = ["관련 상품 살펴보기", "다른 용어 물어보기", "조건으로 찾아보기"]
    elif action == "ask":
        chips = ["잘 모르겠어요", "이 조건은 건너뛸게요", "처음부터 다시 정할래요"]
    else:  # compare
        chips = ["보유상품과 겹침 확인하기", "다른 후보 더 보기", "조건 바꿔서 다시 찾기"]

    answer, report = run_safety(state.get("draft_answer", ""), turn)
    turn.update({
        "answer": answer,
        "action": action,
        "action_reason": state.get("action_reason", ""),
        "conditions": state.get("conditions", {}),
        "chips": chips,
        "safety": report,
    })
    summary = (f"안전 점검: 금칙 치환 {len(report['banned'])}건, "
               f"수치 교정 {len(report['numeric'])}건, "
               f"안내 {report['notices'] or '해당 없음'}, 고지 {len(report['disclosures'])}건")
    return {"messages": [AIMessage(content=answer)],
            "turn": turn,
            "trace": [_t("postprocess", "safety", summary,
                         {**report, "chips": chips})]}


def build_graph():
    g = StateGraph(ExploreState)
    g.add_node("router", router_node)
    g.add_node("explain", explain_node)
    g.add_node("ask", ask_node)
    g.add_node("search", search_node)
    g.add_node("compare", compare_node)
    g.add_node("postprocess", postprocess_node)
    g.add_edge(START, "router")
    g.add_conditional_edges("router", lambda s: s["action"],
                            {a: a for a in ["explain", "ask", "search", "compare"]})
    for node in ["explain", "ask", "search", "compare"]:
        g.add_edge(node, "postprocess")
    g.add_edge("postprocess", END)
    return g.compile(checkpointer=InMemorySaver())
