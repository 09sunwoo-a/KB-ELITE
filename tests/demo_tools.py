"""A3 게이트 — 도구 3종 대표 케이스 데모 (05 §1 A3 표의 5케이스).

실행: .venv/bin/python tests/demo_tools.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import store
from app.tools import calc_annual_cost, match_overlap, search_funds

fail = 0


def check(cond, msg):
    global fail
    print(f"    {'✓' if cond else '✗ FAIL:'} {msg}")
    fail += (not cond)


def show_cards(res):
    print(f"    풀 {res['pool_size']}건 / 성향초과 제외 {res['excluded_by_risk']}건 / "
          f"blocked={res['blocked']} / {res['ranking_mode']} / 적용조건 {res['applied']}")
    for c in res["candidates"]:
        print(f"      · {c['name'][:40]}")
        print(f"        [{c['risk_grade']}/fee {c['fee_pct']}%/종목 {c['matched_stocks']}]")
        print(f"        근거: {c['selection_reason']} (기준일 {c['as_of']})")


print("【케이스 1】 엔비디아 + 비용 낮은 순, 최준혁(≤5)")
r1 = search_funds({"target_stock": "엔비디아", "cost_sensitive": True}, 5,
                  "엔비디아 많이 들어가고 비용 낮은 펀드")
show_cards(r1)
fees = [c["fee_pct"] for c in r1["candidates"]]
check(2 <= len(r1["candidates"]) <= 4, f"후보 {len(r1['candidates'])}개 (2~4)")
check(all("엔비디아" in c["matched_stocks"] for c in r1["candidates"]), "전원 엔비디아 매칭")
check(fees == sorted(fees), "비용 오름차순")
check(r1["excluded_by_risk"] == 4, f"성향 초과 제외 {r1['excluded_by_risk']}건 (기대 4)")

print("\n【케이스 2】 AI 테마, 정미숙(≤2) — 완전 차단")
r2 = search_funds({"region_theme": "AI"}, 2, "요즘 AI 펀드 어때요")
show_cards(r2)
check(len(r2["candidates"]) == 0 and r2["blocked"], "후보 0건 + blocked=True")
check(r2["excluded_by_risk"] > 0, f"제외 건수 기록됨 ({r2['excluded_by_risk']}건)")

print("\n【케이스 3】 AI 테마, 최준혁(≤5) — 정상 노출")
r3 = search_funds({"region_theme": "AI"}, 5, "요즘 AI 펀드 어때요")
show_cards(r3)
check(len(r3["candidates"]) >= 2 and not r3["blocked"], "후보 존재 + blocked=False")

print("\n【케이스 4】 비용 환산 — calc_annual_cost(0.9%, 월 20만원)")
s = calc_annual_cost(0.9, 200000, "monthly")
print(f"    → {s}")
check("1,200원" in s or "11,700" in s or "약 1" in s, "환산 결과 문자열 생성")
check("달라질 수 있어요" in s, "한계 고지 포함")
s2 = calc_annual_cost(1.51, 20000000, "lumpsum")
print(f"    → {s2}")

print("\n【케이스 5】 겹침 분석 — 최준혁 보유 vs 피델리티 미국")
p3 = store.persona("P3")
ov = match_overlap(p3["holdings"], "KF04001379")
print(f"    → 겹침: {ov['overlap_stocks']} / {ov['basis']} / {ov['as_of']}")
print(f"    → note: {ov['note']}")
check(ov["overlap_stocks"] == ["엔비디아"], "겹침 = [엔비디아] (테슬라·국내주식 제외 정확)")
check("weight" not in str(ov) and "비중" not in str(ov["overlap_stocks"]), "비중 미계산")
ov2 = match_overlap(p3["holdings"], "KF04001560")  # 보유종목 결측 펀드
print(f"    → 결측 펀드: available={ov2['available']} ({ov2['reason']})")
check(ov2["available"] is False, "결측 시 available=False")

print(f"\n{'게이트 FAIL: ' + str(fail) + '건' if fail else '게이트 검증 전체 통과 (0 fail)'}")
sys.exit(1 if fail else 0)
