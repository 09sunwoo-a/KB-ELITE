"""시연 코스 라이브 검증 — 01 §7-2 (2026-07-18 개정: 최준혁 3턴 + 서지우 5턴 + 교차).

각 턴의 질문·답변 전문을 출력하고(눈 검증), 턴별 시연 포인트를 프로그램적으로 검사한다.
실행: .venv/bin/python tests/demo_scenario_check.py
"""

import os
import re
import sys
import uuid

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "ui"))

from adapter import create_adapter  # noqa: E402

fail = 0

# 01 5-5 금지 표현 (추천형 화법) + 호칭 규칙(프롬프트 [호칭])
FORBIDDEN = ["추천드립니다", "추천드려요", "추천합니다", "가입하세요",
             "적합합니다", "적합해요", "더 낫습니다", "가장 좋습니다", "당신"]

# 서지우(안정추구, 상한 3) 노출 가능 등급 (01 4-2)
SEO_ALLOWED_GRADES = {"매우낮은위험", "낮은위험", "보통위험"}


def check(cond, msg):
    global fail
    print(f"    {'✓' if cond else '✗ FAIL:'} {msg}")
    fail += (not cond)


def run_turn(adapter, thread_id, persona, text, label):
    print(f"\n──── {label}")
    print(f"  Q: {text}")
    events = list(adapter.stream_turn(text, thread_id, persona))
    last = events[-1]
    if last["event_type"] != "turn_completed":
        print(f"  ✗ 턴 실패: {last}")
        globals()["fail"] += 1
        return {}
    r = last["result"]
    print("  A: " + r["answer"].replace("\n", "\n     "))
    if r["candidates"]:
        cards = ", ".join(f"{i+1}. {c['name'][:26]}…({c['risk_grade']}/{c['fee_pct']}%)"
                          for i, c in enumerate(r["candidates"]))
        print(f"  후보: {cards}")
    if r["chips"]:
        print(f"  칩: {r['chips']}")
    print(f"  [action={r['action']} | 사유: {r['action_reason']}]")
    check(not any(w in r["answer"] for w in FORBIDDEN), "금지 표현(추천형 화법) 없음")
    return r


adapter = create_adapter("live")

print("=" * 70)
print("A. 최준혁 코스 (P3) — 고급 검색 → 상품 비교 → 재프레이밍 (3턴)")
print("=" * 70)
tid_c = f"demo-c-{uuid.uuid4().hex[:8]}"

r1 = run_turn(adapter, tid_c, "P3",
              "엔비디아 들어간 펀드 중에 수수료 낮은 걸로 몇 개만 보여줘", "턴 1 — 고급 검색")
cands = r1.get("candidates", [])
check(r1.get("action") == "search", f"질문 0회 즉시 검색 (action={r1.get('action')})")
check(2 <= len(cands) <= 4, f"후보 {len(cands)}개 (2~4)")
fees = [c["fee_pct"] for c in cands]
check(fees == sorted(fees), f"비용 오름차순 정렬 {fees}")
check(all("엔비디아" in c.get("matched_stocks", []) for c in cands), "전 후보 엔비디아 매칭")
check(bool(re.search(r"비용|수수료", r1.get("answer", ""))) and "낮" in r1.get("answer", ""),
      "정렬 기준(비용 낮은 순)이 답변에 서술됨")
check(any(t.get("kind") == "tool" and "search" in str(t).lower() for t in r1.get("trace", [])),
      "trace에 search_funds 도구 호출 기록")

r2 = run_turn(adapter, tid_c, "P3", "1번이랑 3번은 뭐가 달라?", "턴 2 — 번호 비교 (멀티턴 State)")
comp = r2.get("comparison")
check(bool(comp), "비교표 생성")
if comp and len(cands) >= 3:
    check(comp["fund_codes"] == [cands[0]["fund_code"], cands[2]["fund_code"]],
          "비교 대상 = 직전 후보 1번·3번")

r3 = run_turn(adapter, tid_c, "P3", "그래서 뭘 사는 게 제일 나아?", "턴 3 — 추천 거절 재프레이밍")
check(not r3.get("candidates") or r3.get("action") != "search",
      "단일 상품 지목형 응답 아님 (재프레이밍)")
check(bool(re.search(r"기준|조건|선택|비교", r3.get("answer", ""))),
      "기준 정리·선택권 반환 서술 포함")

print()
print("=" * 70)
print("B. 서지우 코스 (P1) — 초보의 기준 구체화 (5턴, 칩 2회)")
print("=" * 70)
tid_s = f"demo-s-{uuid.uuid4().hex[:8]}"

s1 = run_turn(adapter, tid_s, "P1",
              "월급 받으면 그냥 파킹통장에 두는데 좀 아까워서요", "턴 1 — 막연한 발화")
check(s1.get("action") == "ask", f"질문으로 응답 (action={s1.get('action')})")
check(s1.get("answer", "").count("?") <= 2, "질문은 1개 (물음표 남발 없음)")
check(len(s1.get("chips", [])) >= 2, f"답변 선택지 칩 {len(s1.get('chips', []))}개")

s2 = run_turn(adapter, tid_s, "P1", "5년 이상 여유 있어요", "턴 2 — [칩] 기간 조건")
check(bool(s2.get("conditions")), f"조건 누적: {s2.get('conditions')}")

s3 = run_turn(adapter, tid_s, "P1", "큰 변동은 피하고 싶어요", "턴 3 — [칩] 손실 감내 → 검색 전환")
s3_cands = s3.get("candidates", [])
check(s3.get("action") == "search", f"검색 전환 (action={s3.get('action')})")
check(len(s3_cands) >= 2, f"후보 {len(s3_cands)}개")
bad = [c["name"] for c in s3_cands if c["risk_grade"] not in SEO_ALLOWED_GRADES]
check(not bad, f"전 후보 위험등급 ≤ 보통위험 (위반: {bad or '없음'})")

s4 = run_turn(adapter, tid_s, "P1",
              "첫 번째 건 비용이 많이 들어요? 매달 20만원씩 넣으면요?", "턴 4 — 원 단위 비용 환산")
check("평균잔액" in s4.get("answer", "") and "원" in s4.get("answer", ""),
      "calc_annual_cost 원 단위 환산 문자열 포함 (코드 계산)")
check("달라질 수 있어요" in s4.get("answer", ""), "비용 한계 고지 문구 포함")

s5 = run_turn(adapter, tid_s, "P1",
              "친구가 요즘 AI 펀드 좋다던데 저도 살 수 있어요?", "턴 5 — 성향 초과 완전 차단")
rb = s5.get("risk_block") or {}
check(rb.get("blocked") is True, "risk_block.blocked=True")
check(not s5.get("candidates"), "후보 카드 0개 (완전 차단)")
check(len(s5.get("chips", [])) == 2, f"대안 칩 2개: {s5.get('chips')}")
check("초과" in s5.get("answer", ""), "차단 사유(성향 범위 초과) 서술")

print()
print("=" * 70)
print("C. 교차 장면 — 최준혁 새 thread에 같은 질문")
print("=" * 70)
tid_x = f"demo-x-{uuid.uuid4().hex[:8]}"
x1 = run_turn(adapter, tid_x, "P3", "요즘 AI 펀드 어때요?", "교차 — 공격투자형 전 상품 노출")
check(not (x1.get("risk_block") or {}).get("blocked"), "차단 없음")
check(len(x1.get("candidates", [])) >= 2, f"후보 {len(x1.get('candidates', []))}개 노출")

print()
print("=" * 70)
print(f"{'검증 FAIL: ' + str(fail) + '건' if fail else '시연 코스 전 턴 검증 통과 (0 fail)'}")
sys.exit(1 if fail else 0)
