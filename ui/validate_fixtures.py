# -*- coding: utf-8 -*-
"""B0 게이트 검증 — mock_fixtures가 04 §6-3 스키마를 준수하는지 확인한다.

실행: python ui/validate_fixtures.py
data/funds.json은 읽기 전용으로 대조에만 사용한다(트랙 B 소유권 준수).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from mock_fixtures import (  # noqa: E402
    FIXTURES, FIXTURE_FALLBACK, COURSE_4, AS_OF,
)

# 04 §6-3 AgentTurnResult 필수 키와 타입
RESULT_SCHEMA = {
    "answer": str,
    "action": str,
    "action_reason": str,
    "conditions": dict,
    "candidates": list,
    "comparison": (dict, type(None)),
    "overlap": (list, type(None)),
    "risk_block": (dict, type(None)),
    "chips": list,
    "trace": list,
}

# 04 §6-3 후보 카드 스키마 (정확히 이 키 집합 — 2026-07-18 확장 반영)
CARD_KEYS = {
    "fund_code", "name", "fund_type", "region", "risk_grade",
    "fee_pct", "manager", "matched_stocks", "top_stocks_summary",
    "returns_display", "selection_reason", "as_of",
}

TRACE_NODES = {"router", "explain", "ask", "search", "compare", "postprocess"}
TRACE_KINDS = {"route", "tool", "retrieval", "safety", "info"}

# 데이터에 없어 표시 금지인 개념 (04 조정 #3, 05 B 수용 기준)
FORBIDDEN_KEYS = {"weight", "weight_pct", "overlap_ratio", "overlap_pct", "비중", "중복률"}
FORBIDDEN_ROW_LABELS = {"글라이드패스", "주식비중", "종목 비중"}

errors = []
ok = []


def check(cond, label, detail=""):
    if cond:
        ok.append(label)
    else:
        errors.append(f"{label}  {detail}")


def validate_result(tag, r):
    for key, typ in RESULT_SCHEMA.items():
        check(key in r, f"[{tag}] 필수 키 '{key}' 존재")
        if key in r:
            check(isinstance(r[key], typ), f"[{tag}] '{key}' 타입", f"→ {type(r[key]).__name__}")

    for i, card in enumerate(r.get("candidates", []), 1):
        check(set(card.keys()) == CARD_KEYS, f"[{tag}] 카드{i} 키 집합 = 04 스키마",
              f"차이: {set(card.keys()) ^ CARD_KEYS}")
        check(isinstance(card.get("matched_stocks"), list), f"[{tag}] 카드{i} matched_stocks는 리스트")
        rd = card.get("returns_display")
        check(rd is None or (isinstance(rd, dict) and set(rd) == {"period", "value"}),
              f"[{tag}] 카드{i} returns_display 형식")
        check(not (set(card) & FORBIDDEN_KEYS), f"[{tag}] 카드{i} 금지 키(비중 등) 없음")

    ov_list = r.get("overlap")
    if ov_list is not None:
        required = {"available", "fund_code", "fund_name", "overlap_stocks", "as_of", "note"}
        for j, ov in enumerate(ov_list, 1):
            check(required <= set(ov.keys()),
                  f"[{tag}] overlap{j} 필수 키 포함", f"누락: {required - set(ov.keys())}")
            check(all(isinstance(s, str) for s in ov.get("overlap_stocks", [])),
                  f"[{tag}] overlap{j} overlap_stocks는 종목명 문자열만(비중 없음)")
            check(not ({"weight", "비중", "중복률", "overlap_pct"} & set(ov.keys())),
                  f"[{tag}] overlap{j} 금지 키(비중 등) 없음")

    cp = r.get("comparison")
    if cp is not None:
        check({"fund_codes", "rows"} <= set(cp.keys()) <= {"fund_codes", "rows", "labels"},
              f"[{tag}] comparison 키 집합", f"→ {sorted(cp.keys())}")
        for row in cp.get("rows", []):
            check(set(row.keys()) == {"label", "values"}, f"[{tag}] 비교 행 '{row.get('label')}' 형식")
            check(row.get("label") not in FORBIDDEN_ROW_LABELS,
                  f"[{tag}] 비교 행 '{row.get('label')}' 금지 항목 아님")

    rb = r.get("risk_block")
    if rb is not None:
        check(set(rb.keys()) == {"excluded_by_risk", "blocked"}, f"[{tag}] risk_block 키 집합")

    for j, t in enumerate(r.get("trace", []), 1):
        check(set(t.keys()) == {"node", "kind", "summary", "detail"},
              f"[{tag}] trace{j} 키 집합(node/kind/summary/detail)")
        check(t.get("node") in TRACE_NODES, f"[{tag}] trace{j} node는 02 실제 6노드", f"→ {t.get('node')}")
        check(t.get("kind") in TRACE_KINDS, f"[{tag}] trace{j} kind enum", f"→ {t.get('kind')}")
        check(isinstance(t.get("detail"), dict), f"[{tag}] trace{j} detail은 dict")


def cross_check_funds(tag, r, funds):
    """카드·비교표 수치가 funds.json 실값과 일치하는지 대조 (03: 수치의 단일 출처)."""
    for i, card in enumerate(r.get("candidates", []), 1):
        f = funds.get(card["fund_code"])
        check(f is not None, f"[{tag}] 카드{i} fund_code가 funds.json에 존재", card["fund_code"])
        if f:
            for field in ("name", "fund_type", "region", "risk_grade", "fee_pct", "manager", "as_of"):
                check(card[field] == f[field], f"[{tag}] 카드{i} {field} == funds.json",
                      f"fixture={card[field]!r} data={f[field]!r}")
            rd = card.get("returns_display")
            if rd:
                check(rd["value"] == f["returns"]["m12"], f"[{tag}] 카드{i} 12개월 수익률 == funds.json",
                      f"fixture={rd['value']} data={f['returns']['m12']}")
    for ov in r.get("overlap") or []:
        if ov.get("available"):
            f = funds.get(ov["fund_code"])
            check(f is not None and ov["fund_name"] == f["name"], f"[{tag}] overlap 상품명 == funds.json")


def main():
    for tag, r in list(FIXTURES.items()) + [("FALLBACK", FIXTURE_FALLBACK)]:
        validate_result(tag if len(tag) < 20 else tag[:18] + "…", r)

    funds_path = Path(__file__).parent.parent / "data" / "funds.json"
    if funds_path.exists():
        funds = json.loads(funds_path.read_text(encoding="utf-8"))
        for tag, r in FIXTURES.items():
            cross_check_funds(tag[:18] + "…" if len(tag) >= 20 else tag, r, funds)
    else:
        print("※ data/funds.json 없음 — 실데이터 대조 생략")

    # 05 B0 통과 기준: ④ blocked=true, 후보 0개
    f4 = FIXTURES[COURSE_4]
    check(f4["risk_block"] is not None and f4["risk_block"]["blocked"] is True,
          "[게이트] 코스 ④ blocked=True")
    check(f4["candidates"] == [], "[게이트] 코스 ④ 후보 0개")
    check(len(f4["chips"]) == 2, "[게이트] 코스 ④ 대안 칩 2개(04 §4-7)")

    # 공통: 기준일 상수, 칩 개수
    for tag, r in FIXTURES.items():
        short = tag[:18] + "…" if len(tag) >= 20 else tag
        check(2 <= len(r["chips"]) <= 3, f"[{short}] 후속 칩 2~3개")
        for i, c in enumerate(r["candidates"], 1):
            check(c["as_of"] == AS_OF, f"[{short}] 카드{i} 기준일 {AS_OF}")

    print(f"검사 항목: {len(ok) + len(errors)}개 — 통과 {len(ok)} / 실패 {len(errors)}")
    print()
    if errors:
        print("❌ 실패 항목:")
        for e in errors:
            print("  -", e)
        sys.exit(1)

    print("✅ 전체 통과 — fixture 4종 + fallback")
    print()
    print("게이트 핵심 확인:")
    print(f"  · 코스 ① 후보 {len(FIXTURES[list(FIXTURES)[0]]['candidates'])}개, "
          f"excluded_by_risk={FIXTURES[list(FIXTURES)[0]]['risk_block']['excluded_by_risk']}")
    c2 = list(FIXTURES.values())[1]
    print(f"  · 코스 ② 비교표 {len(c2['comparison']['rows'])}행, 대상 {c2['comparison']['fund_codes']}")
    c3 = list(FIXTURES.values())[2]
    print(f"  · 코스 ③ 겹침 종목 {c3['overlap'][0]['overlap_stocks']} (비중·중복률 키 없음)")
    print(f"  · 코스 ④ blocked=True, 후보 0개, 대안 칩 {f4['chips']}")


if __name__ == "__main__":
    main()
