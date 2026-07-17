"""A4 게이트 — 라우터 단독 검증. 대본 발화 12개 → 행동/조건/플래그 표 (05 §1 A4).

실행: .venv/bin/python tests/demo_router.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.router import route_turn

# (발화, 기대 action 집합, 추가 검사 함수, route_turn kwargs)
CASES = [
    ("월급 받으면 그냥 파킹통장에 두는데 좀 아까워서요.",
     {"ask"}, lambda r: not r.target_stock and not r.region_theme, {}),
    ("결혼자금으로 쓸 수도 있는데, 5년은 넘게 남았어요.",
     {"ask", "search"}, lambda r: r.horizon is not None, {}),
    ("TDF2050 뒤의 숫자가 뭐예요?",
     {"explain"}, lambda r: r.term_to_explain and "TDF" in r.term_to_explain.upper(), {}),
    ("엔비디아 많이 들어가고 비용 낮은 것 몇 개 보여줘.",
     {"search"}, lambda r: r.target_stock == "엔비디아" and r.cost_sensitive, {}),
    ("1번과 3번 비교해줘.",
     {"compare"}, lambda r: sorted(r.compare_targets) == [1, 3],
     {"last_candidates": ["F1", "F2", "F3"]}),
    ("나 엔비디아 직접 갖고 있는데 이 펀드까지 사면 얼마나 겹쳐?",
     {"compare"}, lambda r: r.overlap_request,
     {"last_candidates": ["F1", "F2", "F3"]}),
    ("원금 안 줄어드는 펀드도 있어요?",
     {"explain"}, lambda r: True, {}),
    ("매달 돈이 나오는 상품이 있다던데요.",
     {"explain", "search"}, lambda r: bool(r.fund_type_hint), {}),
    ("요즘 AI 펀드 어때요?",
     {"search"}, lambda r: (r.region_theme or "").upper().find("AI") >= 0, {}),
    ("그래서 뭘 사면 돼요?",
     {"explain", "ask", "search", "compare"}, lambda r: r.delegation_request, {}),
    ("지금 사도 돼요? 더 오를까요?",
     {"explain", "ask", "search", "compare"}, lambda r: r.out_of_scope, {}),
    ("네, 그 정도면 괜찮아요.",
     {"search"}, lambda r: True,  # 오버라이드 규칙 ① 작동 확인
     {"ask_streak": 2, "conditions": {"horizon": "5년 이상", "loss_tolerance": "큰 변동 회피"}}),
]

passed = 0
print(f"{'#':2} {'발화':34} {'action':8} {'조건/플래그 검사':6} 추출 요약")
for i, (utt, expect_actions, extra_check, kwargs) in enumerate(CASES, 1):
    r, overrides = route_turn(utt, **kwargs)
    ok_action = r.action in expect_actions
    ok_extra = extra_check(r)
    ok = ok_action and ok_extra
    passed += ok
    extracted = {k: v for k, v in r.model_dump().items()
                 if v not in (None, False, [], "") and k not in ("action", "action_reason")}
    print(f"{i:2} {utt[:32]:34} {r.action:8} {'✓' if ok else '✗ FAIL':6} {extracted}")
    if overrides:
        print(f"   └ 오버라이드: {overrides}")
    print(f"   └ 이유: {r.action_reason}")

print(f"\n결과: {passed}/12 통과")
sys.exit(0 if passed == 12 else 1)
