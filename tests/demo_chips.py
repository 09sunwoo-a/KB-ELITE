"""동적 후속 칩(02 §7-2 ④ 개정) 확인 데모.

Live 그래프로 explain/search/compare 턴의 LLM 동적 칩 2개 생성을,
ask/차단 턴의 규칙 칩 유지와 검증 실패 시 규칙 폴백을 확인한다.
실행: .venv/bin/python tests/demo_chips.py
"""

import os
import sys
import uuid

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "ui"))

from adapter import create_adapter  # noqa: E402

from app.graph import postprocess_node  # noqa: E402

fail = 0


def check(cond, msg):
    global fail
    print(f"  {'✓' if cond else '✗ FAIL:'} {msg}")
    fail += (not cond)


def run_turn(adapter, thread_id, persona, text):
    events = list(adapter.stream_turn(text, thread_id, persona))
    result = events[-1]["result"]
    pp = next(t for t in result["trace"] if t["node"] == "postprocess")
    return result, pp["detail"].get("chips_source"), pp["detail"].get("chips_drop_reason")


adapter = create_adapter("live")

print("=== 1. search 턴 — 동적 칩 2개 (P3) ===")
tid = f"chips-{uuid.uuid4().hex[:8]}"
r, src, drop = run_turn(adapter, tid, "P3", "엔비디아 많이 들어가고 비용 낮은 펀드 찾아줘")
print(f"  칩: {r['chips']} (source={src}, drop={drop})")
check(src == "llm" and len(r["chips"]) == 2, "LLM 동적 칩 2개 채택")
check(all(4 <= len(c) <= 28 for c in r["chips"]), "칩 길이 4~28자")

print("\n=== 2. compare 턴 — 같은 thread, 동적 칩 (P3) ===")
r2, src2, _ = run_turn(adapter, tid, "P3", "1번과 2번 비교해줘")
print(f"  칩: {r2['chips']} (source={src2})")
check(src2 == "llm" and len(r2["chips"]) == 2, "compare 턴 동적 칩 2개")

print("\n=== 3. explain 턴 — 동적 칩 (P2) ===")
r3, src3, _ = run_turn(adapter, f"chips-{uuid.uuid4().hex[:8]}", "P2", "TDF 2045에서 숫자가 무슨 뜻이에요?")
print(f"  칩: {r3['chips']} (source={src3})")
check(src3 == "llm" and len(r3["chips"]) == 2, "explain 턴 동적 칩 2개")

print("\n=== 4. ask 턴 — 규칙 칩 유지 (P1) ===")
r4, src4, _ = run_turn(adapter, f"chips-{uuid.uuid4().hex[:8]}", "P1",
                       "월급 받으면 그냥 파킹통장에 두는데 좀 아까워서요")
print(f"  칩: {r4['chips']} (source={src4})")
check(src4 == "rule" and len(r4["chips"]) == 3, "ask 턴은 규칙 칩 3개 (슬롯 선택지)")

print("\n=== 5. 차단 턴 — 규칙 칩 유지 (P4) ===")
r5, src5, _ = run_turn(adapter, f"chips-{uuid.uuid4().hex[:8]}", "P4", "요즘 AI 펀드 어때요?")
print(f"  칩: {r5['chips']} (source={src5})")
check(src5 == "rule" and r5["chips"] == ["가입 가능한 범위에서 찾아보기", "이전 후보로 돌아가기"],
      "차단 턴은 복구 플로우 고정 칩 (라우터 문자열 매칭 보존)")

print("\n=== 6. 검증 실패 → 규칙 폴백 (오프라인, LLM 없이 postprocess 직접) ===")
state = {
    "action": "search",
    "turn": {"candidates": [], "llm_chips": ["이 상품 가입하세요", "비용 낮은 순으로 보기"]},
    "last_candidates": [{"name": "샘플"}, {"name": "샘플2"}],
    "profile": {"holdings": []},
    "draft_answer": "조건에 맞는 후보를 정리했어요.",
}
out = postprocess_node(state)
detail = out["trace"][0]["detail"]
print(f"  칩: {out['turn']['chips']} (source={detail['chips_source']}, drop={detail['chips_drop_reason']})")
check(detail["chips_source"] == "rule" and "금칙" in (detail["chips_drop_reason"] or ""),
      "금칙 칩 세트 폐기 → 규칙 폴백 + trace에 사유 기록")
check("llm_chips" not in out["turn"], "llm_chips는 턴 결과(UI 계약)에 노출되지 않음")

print(f"\n{'FAIL ' + str(fail) + '건' if fail else '동적 칩 데모 전체 통과 (0 fail)'}")
sys.exit(1 if fail else 0)
