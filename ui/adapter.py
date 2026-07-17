# -*- coding: utf-8 -*-
"""AgentAdapter — UI↔Agent 데이터 계약(04 §6-1).

UI는 adapter 종류를 몰라야 한다. `agent_mode`는 배지 표시에만 쓴다.
Live 연결 실패 시 자동으로 Mock으로 위장 전환하지 않는다(04 §1 원칙 3) —
AdapterConnectionError를 올리고, 전환은 사용자가 화면에서 명시적으로 한다.
"""
import os
import time
from typing import Iterable, Literal, Protocol, TypedDict

from mock_fixtures import get_fixture


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


class LangGraphAgentAdapter:
    """compiled_graph.stream(stream_mode="updates") 소비 — J1 단계에서 구현.

    지금은 app.graph가 없거나 미완성이므로 초기화 시점에 명확히 실패한다.
    """

    def __init__(self):
        try:
            from app.graph import graph  # noqa: F401  (트랙 A 산출물 — import만)
        except Exception as exc:
            raise AdapterConnectionError(
                f"Live 연결 실패 — app.graph를 불러올 수 없습니다 ({type(exc).__name__}). "
                "백엔드(A5) 완성 후 J1 단계에서 연결됩니다."
            ) from exc
        raise AdapterConnectionError("LangGraphAgentAdapter 변환부는 J1 단계에서 구현됩니다.")

    def stream_turn(self, user_message, thread_id, persona_id):  # pragma: no cover
        raise NotImplementedError


def default_mode() -> str:
    """환경변수 AGENT_MODE(기본 mock). 04 §7: live는 명시적 opt-in."""
    return os.getenv("AGENT_MODE", "mock").strip().lower()


def create_adapter(mode: str) -> AgentAdapter:
    if mode == "live":
        return LangGraphAgentAdapter()
    return MockAgentAdapter()
