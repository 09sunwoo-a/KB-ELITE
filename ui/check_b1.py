# -*- coding: utf-8 -*-
"""B1 게이트 스모크 체크 — AppTest로 화면 골격 동작을 헤드리스 검증.

실행: python ui/check_b1.py
(최종 게이트는 `streamlit run ui/streamlit_app.py` 눈 체크 — 05 §2 B1)
"""
import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).parent / "streamlit_app.py")

sys.path.insert(0, str(Path(__file__).parent))
from mock_fixtures import COURSE_1, COURSE_2, COURSE_3, COURSE_4  # noqa: E402

results = []


def check(label, cond, detail=""):
    results.append((cond, label, detail))
    print(("  ✅ " if cond else "  ❌ ") + label + (f"  ({detail})" if detail and not cond else ""))


def has_badge(at, text="MOCK TRACE"):
    return any(text in str(md.value) for md in at.markdown)


print("① 초기 진입 — 서브메인")
at = AppTest.from_file(APP, default_timeout=60).run()
check("screen == fund_home", at.session_state["screen"] == "fund_home")
check("agent_mode == mock (AGENT_MODE 미설정)", at.session_state["agent_mode"] == "mock")
check("MOCK TRACE 배지 표시(사이드바)", has_badge(at))
check("AI 플로팅 버튼 존재", len(at.button(key="ai_fab")) > 0 if hasattr(at.button(key="ai_fab"), '__len__') else at.button(key="ai_fab") is not None)
check("Prototype 표기 존재", any("Prototype" in str(md.value) for md in at.markdown))

print("② AI 버튼 → Chat 전환 + 오프닝 (최준혁)")
at.button(key="ai_fab").click().run()
check("screen == chat", at.session_state["screen"] == "chat")
msgs = at.session_state["messages"]
check("오프닝 1건 (assistant)", len(msgs) == 1 and msgs[0]["role"] == "assistant")
check("최준혁 오프닝 문구", "최준혁 고객님" in msgs[0]["content"])
check("빠른 시작 칩 3개", len(msgs[0]["chips"]) == 3)
check("thread_id 발급", bool(at.session_state["thread_id"]))
thread_c = at.session_state["thread_id"]
opening_c = msgs[0]["content"]

print("③ 시연 코스 ① 클릭 → Mock 응답 렌더")
at.chat_input[0].set_value(COURSE_1).run()
msgs = at.session_state["messages"]
check("메시지 3건 (오프닝/사용자/응답)", len(msgs) == 3, f"실제 {len(msgs)}건")
check("사용자 메시지 = 코스 ① 문구", msgs[1]["content"].startswith("엔비디아"))
check("Mock 응답에 서술 존재", "엔비디아" in msgs[2]["content"])
check("후속 칩 3개", len(msgs[2]["chips"]) == 3)
check("conditions 갱신(칩바)", at.session_state["conditions"].get("target_stock") == "엔비디아")
check("last_candidates 3건", len(at.session_state["last_candidates"]) == 3)
check("trace_events 누적", len(at.session_state["trace_events"]) == 1)
check("MOCK TRACE 배지 유지", has_badge(at))

print("④ 코스 ② 연속 실행 — 멀티턴")
at.chat_input[0].set_value(COURSE_2).run()
msgs = at.session_state["messages"]
check("메시지 5건", len(msgs) == 5, f"실제 {len(msgs)}건")
check("비교 응답", "차이" in msgs[4]["content"])
check("탐색 기준 유지(멀티턴)", at.session_state["conditions"].get("target_stock") == "엔비디아")

print("⑤ 페르소나 전환 → 초기화 + 오프닝 상이")
at.radio(key="persona_radio").set_value("P1").run()
msgs = at.session_state["messages"]
check("persona_id == P1", at.session_state["persona_id"] == "P1")
check("대화 초기화(오프닝 1건만)", len(msgs) == 1)
check("thread_id 재발급(재사용 금지)", at.session_state["thread_id"] != thread_c)
check("서지우 오프닝 ≠ 최준혁 오프닝", msgs[0]["content"] != opening_c and "서지우 고객님" in msgs[0]["content"])
check("서지우 칩 상이", msgs[0]["chips"][0] == "예금·적금과 펀드는 뭐가 다른가요?")
check("trace_events 초기화", len(at.session_state["trace_events"]) == 0)

print("⑥ 서지우 코스 ④ — 차단 케이스 응답")
at.chat_input[0].set_value(COURSE_4).run()
msgs = at.session_state["messages"]
last = msgs[-1]
check("차단 안내 서술", "후보로 안내해 드리지 않아요" in last["content"])
check("blocked 결과 보관", last["result"]["risk_block"]["blocked"] is True)
check("대안 칩 2개", len(last["chips"]) == 2)

print("⑦ 시연 코스 외 입력 → Mock 고정 안내")
at.chat_input[0].set_value("아무거나 물어볼게요").run()
msgs = at.session_state["messages"]
check("고정 안내 응답", "시연 코스 버튼" in msgs[-1]["content"])

print("⑧ 시연 페르소나 2인 오프닝 상이")
openings = set()
for pid in ["P3", "P1"]:
    at.radio(key="persona_radio").set_value(pid).run()
    openings.add(at.session_state["messages"][0]["content"])
check("오프닝 2종 모두 다름", len(openings) == 2)

print("⑨ 예외·오류")
check("스크립트 예외 0건", not at.exception, str([e.value for e in at.exception]))

passed = sum(1 for c, *_ in results if c)
print(f"\n결과: {passed}/{len(results)} 통과")
sys.exit(0 if passed == len(results) else 1)
