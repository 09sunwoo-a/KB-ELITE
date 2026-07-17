# -*- coding: utf-8 -*-
"""AgentAdapter — UI↔Agent 데이터 계약(04 §6-1).

UI는 adapter 종류를 몰라야 한다. `agent_mode`는 배지 표시에만 쓴다.
Live 연결 실패 시 자동으로 Mock으로 위장 전환하지 않는다(04 §1 원칙 3) —
AdapterConnectionError를 올리고, 전환은 사용자가 화면에서 명시적으로 한다.

J1: LangGraphAgentAdapter는 app/을 import만 한다(05 §5-4 소유권).
"""
import json
import os
import sys
import time
from pathlib import Path
from typing import Iterable, Literal, Protocol, TypedDict

from mock_fixtures import get_fixture

_REPO_ROOT = Path(__file__).parent.parent


class TraceEntry(TypedDict):
    """02 State.trace 원소 (04 §6-2)."""
    node: str
    kind: Literal["route", "tool", "retrieval", "safety", "info"]
    summary: str
    detail: dict


class TurnEvent(TypedDict, total=False):
    event_type: Literal["node_started", "node_completed", "turn_completed", "turn_error"]
    node: str
    trace: list
    result: dict          # AgentTurnResult — turn_completed에만 존재
    error: str            # turn_error에만 존재 (짧은 안내, stack trace 금지)


class AgentAdapter(Protocol):
    def stream_turn(
        self, user_message: str, thread_id: str, persona_id: str,
    ) -> Iterable[TurnEvent]:
        """스트림 마지막 이벤트는 반드시 완성된 AgentTurnResult를 담는다."""
        ...


class AdapterConnectionError(RuntimeError):
    """Live adapter 초기화 실패 — UI는 오류 안내 후 명시적 전환을 요구한다."""


class MockAgentAdapter:
    """스키마를 준수하는 고정 fixture 반환. MOCK TRACE 배지 강제(04 §7)."""

    NODE_DELAY_SEC = 0.45  # 처리 상태 연출용 — 이벤트는 이 시점에 실제로 발행된다

    def stream_turn(self, user_message, thread_id, persona_id):
        result = get_fixture(user_message)
        nodes = []
        for entry in result["trace"]:
            if entry["node"] not in nodes:
                nodes.append(entry["node"])
        for node in nodes:
            yield {"event_type": "node_started", "node": node, "trace": []}
            time.sleep(self.NODE_DELAY_SEC)
            yield {
                "event_type": "node_completed",
                "node": node,
                "trace": [t for t in result["trace"] if t["node"] == node],
            }
        yield {
            "event_type": "turn_completed",
            "node": nodes[-1] if nodes else "postprocess",
            "trace": result["trace"],
            "result": result,
        }


# ── Live ────────────────────────────────────────────────────────────
# 그래프(InMemorySaver 포함)와 스레드 기록은 프로세스 수명 동안 유지돼야
# 하므로 모듈 전역 싱글턴으로 둔다 (Streamlit rerun에도 살아남는다).
_GRAPH = None
_SEEN_THREADS: set = set()
_FUNDS = None


def _funds() -> dict:
    """카드 임시 보강용 funds.json (읽기 전용 — 04 §6-3 백엔드 반영 전까지)."""
    global _FUNDS
    if _FUNDS is None:
        _FUNDS = json.loads(
            (_REPO_ROOT / "data" / "funds.json").read_text(encoding="utf-8"))
    return _FUNDS


class LangGraphAgentAdapter:
    """compiled_graph.stream(stream_mode="updates") 소비 → TurnEvent 변환 (04 §6-1)."""

    def __init__(self):
        if str(_REPO_ROOT) not in sys.path:
            sys.path.insert(0, str(_REPO_ROOT))
        try:
            from app.graph import build_graph
            from app.opening import build_opening
            from app.personas import load_profile
        except Exception as exc:
            raise AdapterConnectionError(
                f"Live 연결 실패 — app 모듈을 불러올 수 없습니다 ({type(exc).__name__}). "
                "백엔드 산출물과 .env(OPENAI_API_KEY)를 확인해 주세요."
            ) from exc
        global _GRAPH
        if _GRAPH is None:
            _GRAPH = build_graph()
        self._graph = _GRAPH
        self._load_profile = load_profile
        self._build_opening = build_opening

    def get_opening(self, persona_id: str) -> dict:
        """그래프 밖 build_opening() 직접 호출 (02 §8) → {"text", "chips"}."""
        return self._build_opening(self._load_profile(persona_id)["profile"])

    def stream_turn(self, user_message, thread_id, persona_id):
        from langchain_core.messages import HumanMessage

        payload = {"messages": [HumanMessage(content=user_message)]}
        if thread_id not in _SEEN_THREADS:
            # 새 thread 첫 턴 — 프로필·노출 상한을 State 초기값으로 주입 (02 §2)
            payload.update(self._load_profile(persona_id))
            _SEEN_THREADS.add(thread_id)
        config = {"configurable": {"thread_id": thread_id}}

        turn, turn_trace = None, []
        yield {"event_type": "node_started", "node": "router", "trace": []}
        try:
            for update in self._graph.stream(payload, config, stream_mode="updates"):
                for node, output in update.items():
                    output = output or {}
                    new_trace = output.get("trace") or []
                    turn_trace.extend(new_trace)
                    yield {"event_type": "node_completed", "node": node, "trace": new_trace}
                    if node == "postprocess":
                        turn = output.get("turn")
                    else:
                        # updates 모드는 완료 시점만 알려주므로 다음 노드 시작을 유도한다
                        next_node = output.get("action") if node == "router" else "postprocess"
                        if next_node:
                            yield {"event_type": "node_started", "node": next_node, "trace": []}
        except Exception as exc:
            # stack trace 노출 금지 (04 §8) — 오류 코드만 trace에 남긴다
            yield {
                "event_type": "turn_error",
                "error": "에이전트 실행 중 문제가 발생했어요. 잠시 후 다시 시도해 주세요.",
                "trace": [{"node": "postprocess", "kind": "info",
                           "summary": f"turn_error: {type(exc).__name__}", "detail": {}}],
            }
            return

        if not turn or not turn.get("answer"):
            yield {"event_type": "turn_error",
                   "error": "응답을 완성하지 못했어요. 다시 한번 물어봐 주세요.", "trace": []}
            return

        yield {
            "event_type": "turn_completed",
            "node": "postprocess",
            "trace": turn_trace,
            "result": self._to_result(turn, turn_trace),
        }

    def _to_result(self, turn: dict, trace: list) -> dict:
        """postprocess의 turn dict → 04 §6-3 AgentTurnResult."""
        return {
            "answer": turn.get("answer", ""),
            "action": turn.get("action", ""),
            "action_reason": turn.get("action_reason", ""),
            "conditions": turn.get("conditions") or {},
            "candidates": [self._enrich_card(c) for c in (turn.get("candidates") or [])],
            "comparison": turn.get("comparison"),
            "overlap": turn.get("overlap"),          # list[dict] | None
            "risk_block": turn.get("risk_block"),
            "chips": turn.get("chips") or [],
            "trace": trace,
        }

    @staticmethod
    def _enrich_card(card: dict) -> dict:
        """04 §6-3 확장 필드(manager·top_stocks_summary·returns_display) 임시 보강.

        백엔드 _make_card가 채우기 전까지 funds.json(수치 단일 출처)에서 직접
        보강한다. 백엔드가 채우면 여기는 자동으로 건너뛴다.
        """
        f = _funds().get(card.get("fund_code"))
        if not f:
            return card
        card = dict(card)
        if card.get("manager") is None:
            card["manager"] = f.get("manager")
        if not card.get("top_stocks_summary"):
            card["top_stocks_summary"] = ", ".join(f.get("matched_aliases") or []) or None
        if not card.get("returns_display"):
            m12 = (f.get("returns") or {}).get("m12")
            if m12 is not None:
                card["returns_display"] = {"period": "12개월", "value": m12}
        return card


def default_mode() -> str:
    """환경변수 AGENT_MODE(기본 mock). 04 §7: live는 명시적 opt-in."""
    return os.getenv("AGENT_MODE", "mock").strip().lower()


def create_adapter(mode: str) -> AgentAdapter:
    if mode == "live":
        return LangGraphAgentAdapter()
    return MockAgentAdapter()
