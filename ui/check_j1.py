# -*- coding: utf-8 -*-
"""J1 게이트 스모크 체크 — Live(LangGraph) 연결 E2E. 실제 LLM 호출 발생.

실행: python ui/check_j1.py
(최종 게이트는 AGENT_MODE=live streamlit run → 시연 코스 4개 눈 체크 — 05 §3 J1)
"""
import os
import sys
from pathlib import Path

os.environ["AGENT_MODE"] = "live"

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).parent / "streamlit_app.py")

sys.path.insert(0, str(Path(__file__).parent))
from mock_fixtures import COURSE_1, COURSE_2, COURSE_3, COURSE_4  # noqa: E402

results = []


def check(label, cond, detail=""):
    results.append(cond)
    print(("  ✅ " if cond else "  ❌ ") + label + (f"  ({detail})" if detail and not cond else ""))


print("① Live 모드 진입 + 오프닝(build_opening)")
at = AppTest.from_file(APP, default_timeout=180).run()
check("agent_mode == live", at.session_state["agent_mode"] == "live",
      f"{at.session_state['agent_mode']} / {at.session_state['adapter_error']}")
at.button(key="ai_fab").click().run()
md = "\n".join(str(m.value) for m in at.markdown)
check("LIVE AGENT 배지", "LIVE AGENT" in md)
opening = at.session_state["messages"][0]
check("오프닝: 최준혁 build_opening 결과", "최준혁 고객님" in opening["content"])
check("오프닝 칩 3개", len(opening["chips"]) == 3)

print("② 코스 ① Live 실행 — 실제 검색·카드")
at.chat_input[0].set_value(COURSE_1).run()
msgs = at.session_state["messages"]
check("메시지 3건", len(msgs) == 3, f"실제 {len(msgs)}")
result = msgs[-1]["result"]
check("action == search", result["action"] == "search", result["action"])
cards = result["candidates"]
check("후보 2~4개", 2 <= len(cards) <= 4, f"{len(cards)}건")
check("1위 후보 = 피델리티(비용 최저)", cards and cards[0]["fund_code"] == "KF04001379",
      str(cards[0]["fund_code"] if cards else None))
check("카드 보강: 운용사·수익률·보유종목",
      all(c.get("manager") and c.get("returns_display") and c.get("top_stocks_summary")
          for c in cards))
check("카드 위험등급 유효(공격투자형은 전 등급 노출 가능)",
      all(c["risk_grade"] in {"매우낮은위험", "낮은위험", "보통위험", "다소높은위험", "높은위험", "매우높은위험"}
          for c in cards))
check("trace: 실제 search 기록", any(t["node"] == "search" and t["kind"] == "tool"
                                   for t in result["trace"]))
check("conditions 추출", result["conditions"].get("target_stock") is not None,
      str(result["conditions"]))
check("후속 칩 존재(개수 가정 없음 — 04 §4-1)", 1 <= len(result["chips"]) <= 3,
      str(result["chips"]))

print("③ 자유 발화 — trace가 고정 문구가 아님을 확인")
at.chat_input[0].set_value("TDF 2050 숫자가 무슨 뜻이에요?").run()
result2 = at.session_state["messages"][-1]["result"]
check("action == explain", result2["action"] == "explain", result2["action"])
check("trace가 코스①과 다름", [t["summary"] for t in result2["trace"]]
      != [t["summary"] for t in result["trace"]])
check("답변 비어있지 않음", len(result2["answer"]) > 20)

print("④ 서지우 코스 ④ Live — 차단")
at.radio(key="persona_radio").set_value("P1").run()
check("서지우 오프닝 상이", "서지우 고객님" in at.session_state["messages"][0]["content"])
at.chat_input[0].set_value(COURSE_4).run()
result4 = at.session_state["messages"][-1]["result"]
rb = result4.get("risk_block") or {}
check("blocked=True", rb.get("blocked") is True, str(rb))
check("후보 0개", result4["candidates"] == [])
check("대안 칩 2개", result4["chips"] == ["가입 가능한 범위에서 찾아보기", "이전 후보로 돌아가기"],
      str(result4["chips"]))

print("⑤ 안전")
check("스크립트 예외 0건", not at.exception, str([str(e.value) for e in at.exception])[:300])

passed = sum(results)
print(f"\n결과: {passed}/{len(results)} 통과")
sys.exit(0 if passed == len(results) else 1)
