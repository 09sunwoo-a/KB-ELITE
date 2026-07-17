"""하이브리드 오프닝(02 §8 개정) 확인 데모.

동적 인트로 생성·검증·캐시와, 검증 실패 시 템플릿 폴백을 확인한다.
실행: .venv/bin/python tests/demo_opening.py
"""

import os
import sys
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from app.opening import _valid_intro, build_opening  # noqa: E402
from app.personas import load_profile  # noqa: E402

fail = 0


def check(cond, msg):
    global fail
    print(f"  {'✓' if cond else '✗ FAIL:'} {msg}")
    fail += (not cond)


print("=== 1. 동적 인트로 — 시연 페르소나 2인 (P3 최준혁 / P1 서지우) ===")
for pid in ["P3", "P1"]:
    profile = load_profile(pid)["profile"]
    t0 = time.time()
    op = build_opening(profile)
    dt = time.time() - t0
    print(f"\n  [{pid} {profile['name']} · {profile['risk_profile']}] ({dt:.1f}s, source={op['intro_source']})")
    print(f"  → {op['text']}")
    check(op["intro_source"] == "llm", "동적 인트로 채택")
    check(op["text"].startswith(f"안녕하세요, {profile['name']} 고객님."), "인사 골격은 코드 유지")
    check(len(op["chips"]) == 3, "칩 3개 (규칙 유지)")
    personal = [h["name"] for h in profile.get("holdings", [])] + [profile["risk_profile"]]
    check(not any(tok in op["text"] for tok in personal), "보유상품명·성향 명칭 복창 없음")

    kinds = [t["kind"] for t in op.get("trace", [])]
    check(kinds == ["info", "tool", "safety"],
          f"trace 로그 3건 (신호 추출→생성→검증): {kinds}")
    check("검증 통과" in op["trace"][-1]["summary"], "검증 로그에 통과 기록")

print("\n=== 2. 페르소나별 차이 — P3 vs P1 인트로가 다른가 ===")
p3 = build_opening(load_profile("P3")["profile"])["text"]
p1 = build_opening(load_profile("P1")["profile"])["text"]
check(p3 != p1, "두 페르소나의 오프닝이 서로 다름")

print("\n=== 3. 검증 규칙 (오프라인) ===")
profile = load_profile("P3")["profile"]
cases = [
    ("최근에 엔비디아를 검색하셨네요. 관련 펀드를 조건별로 살펴볼 수 있어요. 시작해 볼까요?", "행동 복창"),
    ("저는 조건에 맞는 펀드를 추천해 드리는 AI 펀드 길잡이예요. 어떤 조건으로 볼까요?", "추천 어투"),
    ("엔비디아를 보유하고 계시니 겹침 확인부터 도와드릴 수 있어요. 지금 확인해 볼까요?", "보유상품명 복창"),
    ("공격투자형이시니 폭넓은 상품을 조건별로 살펴볼 수 있어요. 어떤 조건부터 볼까요?", "성향 명칭 복창"),
    ("짧아요", "길이 미달"),
]
for text, label in cases:
    ok, reason = _valid_intro(text, profile)
    check(ok is None, f"{label} → 폐기 ({reason})")

good = "저는 원하시는 조건으로 펀드 후보를 찾고 차이를 비교해 드리는 AI 펀드 길잡이예요. 어떤 조건부터 살펴볼까요?"
ok, reason = _valid_intro(good, profile)
check(ok is not None, f"정상 인트로 → 통과 (reason={reason})")

print("\n=== 4. dynamic=False → 템플릿 폴백 ===")
op = build_opening(profile, dynamic=False)
check(op["intro_source"] == "rule" and "특정 종목이 담겼는지" in op["text"],
      "템플릿 사용 + '종목 비중' 문구 교정 반영")
check("종목 비중" not in op["text"], "불가 조건('종목 비중') 약속 제거")

print(f"\n{'FAIL ' + str(fail) + '건' if fail else '하이브리드 오프닝 데모 전체 통과 (0 fail)'}")
sys.exit(1 if fail else 0)
