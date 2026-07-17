"""A2 게이트 점검 — 수작업 데이터 3종(alias/terms/personas) 검증 리포트.

실행: .venv/bin/python tests/check_manual_data.py
"""

import json
import sys

FUNDS = json.load(open("data/funds.json", encoding="utf-8"))
ALIAS = json.load(open("data/alias.json", encoding="utf-8"))
TERMS = json.load(open("data/terms.json", encoding="utf-8"))

# 01 4-2 성향 → 노출 상한 매핑 (A5에서 app/personas.py로 이관 예정)
MAX_RISK = {"안정형": 2, "안정추구형": 3, "위험중립형": 4, "적극투자형": 5, "공격투자형": 6}
EXPECT_CAP = {"P1": 3, "P2": 4, "P3": 6, "P4": 2}  # P3 공격투자형 (2026-07-18)

fail = 0

print("=== 1. 페르소나 4종 ===")
print(f"{'ID':4} {'이름':6} {'성향':8} {'노출상한':6} 보유 (funds.json 존재 / 상한 이내)")
for pid in ["P1", "P2", "P3", "P4"]:
    p = json.load(open(f"data/personas/{pid}.json", encoding="utf-8"))
    cap = MAX_RISK[p["risk_profile"]]
    ok_cap = cap == EXPECT_CAP[pid]
    lines = []
    for h in p["holdings"]:
        if h["kind"] != "fund":
            lines.append(f"{h['name']}(직접주식)")
            continue
        code = h["product_code"]
        exists = code in FUNDS
        within = exists and FUNDS[code]["risk_score"] <= cap
        grade_ok = exists and FUNDS[code]["risk_grade"] == h["risk_grade"]
        if not (exists and within and grade_ok):
            fail += 1
        lines.append(f"{code}({'존재' if exists else '없음!'}/"
                     f"{'상한내' if within else '상한초과!'}/"
                     f"{'등급일치' if grade_ok else '등급불일치!'})")
    if not ok_cap:
        fail += 1
    print(f"{pid:4} {p['name']:6} {p['risk_profile']:8} {cap} {'✓' if ok_cap else '✗'}    "
          + ("; ".join(lines) if lines else "보유 없음"))

print("\n=== 2. alias 사전 — stocks_raw 매칭 건수 ===")
for k in ALIAS:
    n = sum(1 for f in FUNDS.values() if k in f["matched_aliases"])
    print(f"  {k:8} {n:3}건")
nvda = sum(1 for f in FUNDS.values() if "엔비디아" in f["matched_aliases"])
if nvda != 25:
    fail += 1
    print("  ✗ 엔비디아 25건 기대와 불일치")

print(f"\n=== 3. terms.json — {len(TERMS)}항목 ===")
star = ["원금보장", "TDF", "월지급식", "환헤지"]  # 대본 커버 필수(★) 항목
for t in TERMS:
    mark = "★" if t["term"] in star else " "
    mc = "오개념교정" if t["misconception"] else "-"
    print(f"  {mark} {t['term']:14} aliases {len(t['aliases']):2}개  {mc}")
missing = [s for s in star if not any(t["term"] == s and t["misconception"] for t in TERMS)]
banned = ["추천드립", "가입하세요", "적합합니다", "원금 보장돼", "손실이 없"]
tone = [t["term"] for t in TERMS
        if any(b in (t["explain"] + (t["misconception"] or "")) for b in banned)]
if missing:
    fail += 1
    print(f"  ✗ 필수 오개념 항목 누락: {missing}")
if tone:
    fail += 1
    print(f"  ✗ 금칙 표현 포함 항목: {tone}")

print(f"\n{'게이트 FAIL: ' + str(fail) + '건' if fail else '게이트 검증 전체 통과 (0 fail)'}")
sys.exit(1 if fail else 0)
