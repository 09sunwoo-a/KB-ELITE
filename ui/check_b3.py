# -*- coding: utf-8 -*-
"""B3 게이트 스모크 체크 — Trace 패널이 04 §5대로 렌더링되는지 검증.

실행: python ui/check_b3.py
(최종 게이트는 `Agent 동작 보기` 토글 후 눈 체크 — 05 §2 B3)
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


print("① 챗 진입 — 패널 상시 표시 + 빈 상태")
at = AppTest.from_file(APP, default_timeout=60).run()
at.button(key="ai_fab").click().run()
md = all_markdown(at)
check("배지 표시(패널)", md.count("MOCK TRACE") >= 2)  # 사이드바 + 패널
check("빈 상태 안내", any("아직 실행된 턴" in str(c.value) for c in at.caption))

print("② 코스 ① 실행 후 — 현재 행동·실행 흐름·도구 들여쓰기")
at.chat_input[0].set_value(COURSE_1).run()
md = all_markdown(at)
check("현재 행동: action + 이유", "SEARCH" in md and "추가 질문 없이 검색" in md)
check("노드 표시명: 질문 의도 파악·행동 선택", "질문 의도 파악·행동 선택" in md)
check("다이어그램: 실행 분기 강조(펀드 탐색)", 'tpg-node on">✓ 펀드 탐색' in md)
check("다이어그램: 미실행 분기 흐림 3칸", md.count('tpg-node off') >= 3)
check("노드 표시명: 표현·수치 안전 점검", "표현·수치 안전 점검" in md)
check("도구 호출 들여쓰기(search_funds)", 'class="tp-tool"' in md and "search_funds" in md)
tab_labels = [t.label for t in at.tabs]
check("세부 탭 4개", tab_labels == ["탐색 노트", "검색 근거", "도구 실행", "안전 점검"],
      str(tab_labels))

print("③ 탭 내용")
check("검색 근거: 적용 조건·제외 건수", "적용 조건" in md and "성향 범위 초과 제외" in md)
check("검색 근거: 벡터 미사용 표시",
      any("벡터 검색 미사용" in str(i.value) for i in at.info))
check("안전 점검 체크리스트", "✅ 금칙 표현 검사 (치환 0건)" in md and "✅ 수치 대조 (교정 0건)" in md)
check("성향 초과 차단 경고(4건)", "⚠ 성향 초과 상품 4건 노출 차단" in md)
check("탐색 노트: 추출 조건", "이번 발화에서 추출" in md)

print("④ 서지우 코스 ④ — blocked 턴 trace")
at.radio(key="persona_radio").set_value("P1").run()
at.chat_input[0].set_value(COURSE_4).run()
md = all_markdown(at)
check("차단 경고(10건)", "⚠ 성향 초과 상품 10건 전부 노출 차단" in md)
check("blocked 검색 요약", "전부 차단(blocked)" in md)

print("⑤ 노출 금지 항목 부재")
full = md + str([str(c.value) for c in at.caption]) + str([str(j.value) for j in at.json])
check("시스템 프롬프트 원문 없음", "system prompt" not in full.lower() and "시스템 프롬프트" not in full)
check("API 키 노출 없음", "sk-" not in full and "OPENAI_API_KEY" not in full)
check("임베딩 벡터 없음", "embedding" not in full.lower())
check("스크립트 예외 0건", not at.exception, str([str(e.value) for e in at.exception])[:200])

passed = sum(results)
print(f"\n결과: {passed}/{len(results)} 통과")
sys.exit(0 if passed == len(results) else 1)
