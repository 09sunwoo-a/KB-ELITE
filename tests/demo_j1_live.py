"""J1 게이트 사전검증 — LangGraphAgentAdapter 헤드리스 통합 테스트.

Streamlit 없이 ui/adapter.py의 Live 어댑터를 직접 구동해 04 §6 계약을 검사한다.
실행: .venv/bin/python tests/demo_j1_live.py
"""

import os
import sys
import uuid

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "ui"))   # adapter가 mock_fixtures를 같은 폴더에서 import

from adapter import LangGraphAgentAdapter, create_adapter  # noqa: E402

fail = 0


def check(cond, msg):
    global fail
    print(f"  {'✓' if cond else '✗ FAIL:'} {msg}")
    fail += (not cond)


def collect(adapter, thread_id, persona, text):
    events = list(adapter.stream_turn(text, thread_id, persona))
    return events


print("=== 1. Live adapter 생성 + 오프닝 ===")
adapter = create_adapter("live")
check(isinstance(adapter, LangGraphAgentAdapter), "create_adapter('live') → LangGraphAgentAdapter")
for pid in ["P1", "P2", "P3", "P4"]:
    op = adapter.get_opening(pid)
    check(bool(op.get("text")) and len(op.get("chips", [])) == 3, f"{pid} 오프닝 + 칩 3개")

print("\n=== 2. 이벤트 스트림 계약 (P3 시연 코스 ①) ===")
tid = f"j1-{uuid.uuid4().hex[:8]}"
events = collect(adapter, tid, "P3", "엔비디아 많이 들어가고 비용 낮은 펀드 찾아줘")
types = [e["event_type"] for e in events]
check(types[0] == "node_started" and types[-1] == "turn_completed",
      f"이벤트 순서: 시작={types[0]}, 종료={types[-1]}")
check("turn_error" not in types, "오류 이벤트 없음")
completed_nodes = [e["node"] for e in events if e["event_type"] == "node_completed"]
check(completed_nodes[0] == "router" and completed_nodes[-1] == "postprocess",
      f"노드 완료 순서: {completed_nodes}")

result = events[-1]["result"]
REQUIRED_KEYS = ["answer", "action", "action_reason", "conditions", "candidates",
                 "comparison", "overlap", "risk_block", "chips", "trace"]
check(all(k in result for k in REQUIRED_KEYS), "AgentTurnResult 필수 키 10종")
cards = result["candidates"]
check(len(cards) >= 2, f"후보 카드 {len(cards)}개")
fees = [c["fee_pct"] for c in cards]
check(fees == sorted(fees), "비용 오름차순")
c0 = cards[0]
check(c0.get("manager") and c0.get("returns_display", {}).get("period") == "12개월",
      f"카드 보강 필드 (manager={c0.get('manager')}, returns={c0.get('returns_display')})")
check(all({"node", "kind", "summary", "detail"} <= set(t) for t in result["trace"]),
      f"TraceEntry 형식 ({len(result['trace'])}건)")

print("\n=== 3. 멀티턴 — 같은 thread에서 비교 ===")
events2 = collect(adapter, tid, "P3", "1번과 3번 비교해줘")
r2 = events2[-1].get("result", {})
check(events2[-1]["event_type"] == "turn_completed" and r2.get("comparison"),
      "같은 thread에서 번호 비교 성공 (State 유지)")
if r2.get("comparison"):
    check(r2["comparison"]["fund_codes"] == [cards[0]["fund_code"], cards[2]["fund_code"]],
          "비교 대상 = 직전 1·3번 후보")

print("\n=== 4. 차단 흐름 (P4 시연 코스 ④) ===")
tid4 = f"j1-{uuid.uuid4().hex[:8]}"
events4 = collect(adapter, tid4, "P4", "요즘 AI 펀드 어때요?")
r4 = events4[-1]["result"]
check((r4.get("risk_block") or {}).get("blocked") is True, "risk_block.blocked=True")
check(not r4["candidates"] and len(r4["chips"]) == 2, "후보 0 + 대안 칩 2개")
check("초과하여 후보로 안내해 드리지 않았어요" in r4["answer"], "차단 안내 문구 포함")

print("\n=== 5. thread 격리 — 새 thread는 조건 초기화 ===")
tid5 = f"j1-{uuid.uuid4().hex[:8]}"
events5 = collect(adapter, tid5, "P1", "안녕하세요")
r5 = events5[-1].get("result", {})
check(not r5.get("conditions"), f"새 thread 조건 비어있음: {r5.get('conditions')}")

print(f"\n{'게이트 FAIL: ' + str(fail) + '건' if fail else 'J1 사전검증 전체 통과 (0 fail) — Live 연결 준비 완료'}")
sys.exit(1 if fail else 0)
