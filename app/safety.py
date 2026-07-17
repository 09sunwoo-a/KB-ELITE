"""출력 가드레일 — 02 §7-2. LLM이 실수해도 코드가 막는다.

postprocess에서 순서대로 실행:
① 금칙 표현 3범주 검사·치환  ② 성향 초과 차단 안내 삽입(상수)
③ 고지 문구 삽입(상수 2종, 1회)  ④ 수치 대조 lite(03 장치 ③)
모든 개입은 trace에 남긴다 — 시연 포인트.
"""

from __future__ import annotations

import re

# ── ① 금칙 표현 3범주 ──────────────────────────────────────────────
# 판단·권유형: 구문 치환
_JUDGEMENT_REPLACEMENTS = [
    (re.compile(r"추천[을를]?\s?드립니다"), "안내드립니다"),
    (re.compile(r"추천드려요"), "안내드려요"),
    (re.compile(r"추천합니다"), "안내합니다"),
    (re.compile(r"추천해\s?드릴"), "안내해 드릴"),
    (re.compile(r"가입하세요|가입을 권해\s?드려요"), "상세 정보를 확인해 보세요"),
    (re.compile(r"적합합니다"), "조건에 해당합니다"),
    (re.compile(r"적합한 상품"), "조건에 맞는 상품"),
    (re.compile(r"골라\s?드릴게요|골라드리겠습니다"), "기준별로 정리해 드릴게요"),
    (re.compile(r"이 상품이 (더 )?낫습니다"), "두 상품은 이런 차이가 있습니다"),
]
# 수익 보장·오인형: 문장 자체가 위험 → 해당 문장을 안전 문장으로 교체
#   (부정형 "보장되지 않아요", "없어지는 것은 아니에요"는 정상 표현이므로 lookahead로 제외)
_GUARANTEE_PATTERNS = [
    # 단정형 어미가 붙은 보장 '주장'만 잡는다 — 부정형·개념 인용("'원금 보장'과 다르다")은 정상 표현
    re.compile(r"원금[이을]?\s?보장[이]?\s?(됩니다|돼요|되는 상품|되어 있|된다|해\s?드리|해\s?드립)"),
    re.compile(r"손실[이은]?\s?(전혀\s?)?없(습니다|어요|는 상품)"),
    re.compile(r"확정 수익|수익[이을]?\s?보장(합니다|됩니다|돼요|되는 상품)|반드시 오르|무조건 오른"),
]
_GUARANTEE_SAFE_SENTENCE = ("펀드는 예금과 달리 원금 손실이 발생할 수 있고, "
                            "수익이 보장되지 않아요.")
# 최상급·우위형: 구문 치환
_SUPERLATIVE_REPLACEMENTS = [
    (re.compile(r"최고의"), "관련성 높은"),
    (re.compile(r"(가장|제일) 좋은"), "조건에 맞는"),
    (re.compile(r"무조건"), ""),
]

# ── ②③ 상수 문구 ──────────────────────────────────────────────────
BLOCKED_NOTICE = ("※ 조회된 상품이 모두 고객님의 투자성향으로 가입 가능한 위험등급 범위를 "
                  "초과하여 후보로 안내해 드리지 않았어요. 가입 가능 범위는 투자성향 재진단에 "
                  "따라 달라질 수 있습니다.")
EXCLUDED_NOTICE = "※ 조건에 맞는 상품 중 {n}건은 투자성향 가입 가능 범위를 초과해 제외했어요."
DISCLOSURE_INFO = ("※ 본 안내는 특정 상품의 추천·권유가 아닌 정보 제공이며, "
                   "최종 판단과 선택은 고객님께 있습니다.")
DISCLOSURE_LOSS = ("※ 펀드는 예금과 달리 원금 손실이 발생할 수 있으며, "
                   "과거 수익률이 미래 수익을 보장하지 않습니다.")

_NUM_FALLBACK_WITH_CARDS = "자세한 수치는 함께 표시된 카드에서 확인하실 수 있어요."
_NUM_FALLBACK_NO_CARDS = "구체적인 수치는 지금 확인된 데이터에 없어 말씀드리지 않을게요."
_PCT_RE = re.compile(r"(\d+(?:\.\d+)?)\s?%")
_SENT_SPLIT = re.compile(r"((?<=[.!?])\s+)")   # 구분 공백을 캡처해 서식(줄바꿈) 보존


def _split_sentences(text: str) -> list[str]:
    """문장과 문장 사이 공백 토큰을 번갈아 반환 — ''.join으로 원본 서식 복원 가능."""
    return [t for t in _SENT_SPLIT.split(text) if t != ""]


def check_banned(text: str) -> tuple[str, list[dict]]:
    """금칙 3범주 검사·치환. 반환: (치환된 텍스트, 개입 로그)."""
    log = []
    for pat, repl in _JUDGEMENT_REPLACEMENTS + _SUPERLATIVE_REPLACEMENTS:
        for m in pat.finditer(text):
            log.append({"category": "판단·권유형" if (pat, repl) in _JUDGEMENT_REPLACEMENTS
                        else "최상급·우위형", "found": m.group(0), "replaced": repl})
        text = pat.sub(repl, text)
    out, last_sentence = [], None
    for s in _split_sentences(text):
        if not s.strip():          # 문장 사이 공백 토큰 — 서식 그대로 유지
            out.append(s)
            continue
        hit = next((p for p in _GUARANTEE_PATTERNS if p.search(s)), None)
        if hit:
            log.append({"category": "수익보장·오인형", "found": s.strip(),
                        "replaced": _GUARANTEE_SAFE_SENTENCE})
            if last_sentence == _GUARANTEE_SAFE_SENTENCE:
                continue  # 안전 문장 중복 방지
            s = _GUARANTEE_SAFE_SENTENCE
        out.append(s)
        last_sentence = s
    return "".join(out), log


def _allowed_numbers(turn: dict) -> set[float]:
    """이번 턴에 코드가 제공한 수치 집합 + 그 쌍별 차이(예: '0.3%p 낮다')."""
    nums = set()
    for c in turn.get("candidates") or []:
        nums.add(float(c["fee_pct"]))
        rd = c.get("returns_display")
        if rd and rd.get("value") is not None:
            nums.add(float(rd["value"]))
    for row in (turn.get("comparison") or {}).get("rows", []):
        for v in row["values"]:
            if isinstance(v, (int, float)):
                nums.add(float(v))
    for token in re.findall(r"\d+(?:\.\d+)?", turn.get("numeric_note") or ""):
        nums.add(float(token))
    diffs = {round(abs(a - b), 3) for a in nums for b in nums if a != b}
    return nums | diffs


def check_numbers(text: str, turn: dict) -> tuple[str, list[dict]]:
    """수치 대조 lite (03 장치 ③): 응답 속 % 수치가 제공 집합에 없으면 해당 문장 치환."""
    allowed = _allowed_numbers(turn)
    # 카드·비교표가 없는 턴(질문·일반 설명)에서는 "카드에서 확인" 안내가 성립하지 않는다
    fallback = _NUM_FALLBACK_WITH_CARDS if (turn.get("candidates") or turn.get("comparison")) \
        else _NUM_FALLBACK_NO_CARDS
    log, out, last_sentence = [], [], None
    for s in _split_sentences(text):
        if not s.strip():          # 문장 사이 공백 토큰 — 서식 그대로 유지
            out.append(s)
            continue
        bad = None
        for m in _PCT_RE.finditer(s):
            val = float(m.group(1))
            ok = any(abs(val - a) < 0.005 or round(a, 1) == val or round(a, 2) == val
                     for a in allowed)
            if not ok:
                bad = m.group(0)
                break
        if bad:
            log.append({"found": bad, "sentence": s.strip(), "action": "문장 치환"})
            if last_sentence == fallback:
                continue  # 치환 문장 중복 방지
            s = fallback
        out.append(s)
        last_sentence = s
    return "".join(out), log


def run_safety(answer: str, turn: dict) -> tuple[str, dict]:
    """가드레일 전체 실행. 반환: (최종 응답, 점검 리포트 — trace·UI 안전점검 탭용)."""
    report = {"banned": [], "numeric": [], "notices": [], "disclosures": []}

    answer, report["banned"] = check_banned(answer)
    answer, report["numeric"] = check_numbers(answer, turn)

    # ② 성향 초과 차단 안내 — LLM에 맡기지 않는다 (누락률 0% 목표)
    rb = turn.get("risk_block")
    if rb:
        notice = BLOCKED_NOTICE if rb.get("blocked") \
            else EXCLUDED_NOTICE.format(n=rb["excluded_by_risk"])
        answer += "\n\n" + notice
        report["notices"].append("blocked" if rb.get("blocked") else "excluded")

    # ③ 고지 문구 (상수 2종, 각 1회)
    has_numbers = bool(turn.get("candidates") or turn.get("comparison")
                       or _PCT_RE.search(answer))
    if has_numbers:
        answer += "\n\n" + DISCLOSURE_INFO
        report["disclosures"].append("info")
    if re.search(r"원금|수익|분배|손실", answer) and DISCLOSURE_LOSS not in answer:
        answer += "\n" + DISCLOSURE_LOSS
        report["disclosures"].append("loss")

    return answer, report
