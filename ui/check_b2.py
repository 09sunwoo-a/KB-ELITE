# -*- coding: utf-8 -*-
"""B2 게이트 스모크 체크 — 결과 컴포넌트가 04 §4-4~4-7대로 렌더링되는지 검증.

실행: python ui/check_b2.py
(최종 게이트는 시연 코스 ①~④ 눈 체크 — 05 §2 B2)
"""
import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).parent / "streamlit_app.py")

sys.path.insert(0, str(Path(__file__).parent))
from mock_fixtures import COURSE_1, COURSE_2, COURSE_3, COURSE_4  # noqa: E402

results = []


def check(label, cond, detail=""):
    results.append(cond)
    print(("  ✅ " if cond else "  ❌ ") + label + (f"  ({detail})" if detail and not cond else ""))


def all_markdown(at):
    return "\n".join(str(md.value) for md in at.markdown)


print("① 후보 카드 — 코스 ① (최준혁)")
at = AppTest.from_file(APP, default_timeout=60).run()
at.button(key="ai_fab").click().run()
at.chat_input[0].set_value(COURSE_1).run()
md = all_markdown(at)
check("카드 3개 렌더", md.count('class="fund-card"') == 3, f"실제 {md.count('fund-card')}")
check("매칭 뱃지(엔비디아 포함 ✓)", md.count("엔비디아 포함 ✓") == 3)
check("연간 비용 표시(0.66%)", "0.66%" in md)
check("위험등급 태그", "다소높은위험" in md and "높은위험" in md)
check("선정 근거 표시", "선정 근거" in md)
check("기준일 표시", md.count("기준일 2026-06-30") >= 3)
check("일부 차단 고지(4건 제외)", "4건은 투자성향 범위를 초과해 제외했어요" in md)
check("조건 칩바 표시", "관심 종목: 엔비디아" in md and "비용: 낮은 편" in md)
check("운용사 표시", "피델리티자산운용" in md and "KB자산운용" in md)
check("12개월 수익률 기본 표시 + 기준 병기", "8.71%" in md and "(2026-06-30 기준)" in md)
check("주요 보유종목 요약 표시", "엔비디아, 마이크로소프트, 알파벳(구글)" in md)

print("② 비교표 — 코스 ②")
at.chat_input[0].set_value(COURSE_2).run()
md = all_markdown(at)
check("비교표 렌더", 'class="cmp-wrap"' in md)
check("비교 행 7개 + 헤더", md.count('<td class="lbl">') == 8, f"실제 {md.count('lbl')}")
check("상품 라벨 헤더", "1번 피델리티" in md and "3번 KB스타" in md)
check("12개월 수익률 행 + 기준일 행", "12개월 수익률(%)" in md and "기준일" in md)
check("조건 칩바 멀티턴 유지", "관심 종목: 엔비디아" in md)
check("글라이드패스·비중 행 없음", "글라이드패스" not in md and "주식비중" not in md)

print("③ 겹침 — 코스 ③")
at.chat_input[0].set_value(COURSE_3).run()
md = all_markdown(at)
check("겹침 박스 렌더", 'class="overlap-box"' in md)
check("겹친 종목 뱃지 = 엔비디아만", md.count('class="ov-stock"') == 1 and "엔비디아 ✓" in md)
check("한계 고지(비중·중복률 미계산)", "편입 비중과 전체 포트폴리오 중복률은 공개 데이터에 없어" in md)
check("비중 %·막대 없음", "중복률" not in md.replace("중복률은 공개 데이터에 없어", ""))

print("④ 차단 박스 — 코스 ④ (서지우)")
at.radio(key="persona_radio").set_value("P1").run()
at.chat_input[0].set_value(COURSE_4).run()
md = all_markdown(at)
check("차단 박스 렌더", 'class="block-box"' in md)
check("차단 사실·사유(10건)", "10건이 모두" in md and "노출되지 않았어요" in md)
check("후보 카드 없음", 'class="fund-card"' not in md)
last = at.session_state["messages"][-1]
check("대안 칩 2개", last["chips"] == ["가입 가능한 범위에서 찾아보기", "이전 후보로 돌아가기"])
check("스크립트 예외 0건", not at.exception)

passed = sum(results)
print(f"\n결과: {passed}/{len(results)} 통과")
sys.exit(0 if passed == len(results) else 1)
