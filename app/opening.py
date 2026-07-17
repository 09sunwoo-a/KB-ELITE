"""오프닝·빠른 시작 칩 — 하이브리드 (02 §8, 2026-07-18 개정).

인사 골격과 칩 3개는 코드 템플릿, 능력 소개 본문만 LLM이 프로필 기반으로 생성한다.
행동 단정·개인 데이터 복창 금지(01 4-4)는 프롬프트가 아니라 코드 검증(_valid_intro)이
최종 보장한다 — 검증 실패 시 기존 프로필 분기 템플릿으로 폴백.
캐시 없음(2026-07-18 사용자 결정) — 매 진입 새로 생성하고, 생성·검증 과정을
trace(TraceEntry 리스트)로 반환해 UI trace 패널이 로그로 보여준다.
"""

import json
import re
import time

from app.safety import check_banned

_llm = None


def _get_llm():
    global _llm
    if _llm is None:
        from dotenv import load_dotenv
        from langchain_anthropic import ChatAnthropic
        load_dotenv()
        # 응답 생성과 동일 모델 (02 §9) — 오프닝은 캐시되므로 지연은 최초 1회뿐
        _llm = ChatAnthropic(model="claude-haiku-4-5", temperature=0.5, max_tokens=300)
    return _llm


_INTRO_PROMPT = """너는 은행 앱 'AI 펀드 길잡이'의 첫인사 본문을 쓴다.
아래 고객 배경을 참고해, 이 고객에게 지금 가장 유용할 기능을 소개하는 오프닝 본문을 쓴다.
2~3문장, 전체 길이는 공백 포함 150자 이내로 짧게 쓴다.

[고객 배경 — 강조점을 고르는 참고용일 뿐, 문장에 직접 언급·복창 금지]
{brief}

[규칙]
- 정중한 해요체. "저는 ~ 도와드리는 AI 펀드 길잡이예요"처럼 정체성 소개를 포함한다.
- 고객의 투자성향 명칭, 보유상품명, 투자금액, 나이, 과거 검색·조회 행동을 문장에 쓰지 않는다.
  ("~를 찾아보셨네요", "지난번에", "최근에 보신" 같은 표현 금지)
- 할 수 있는 것만 약속한다: 용어·상품 구조 설명 / 조건(특정 종목 포함 여부·지역·테마·비용·상품구조)
  검색 / 후보 비교 / 보유상품과 겹침 확인. 종목별 비중 검색, 수익 예측, 상품 추천은 약속하지 않는다.
- "추천" 계열 표현 금지 — 이 서비스는 추천이 아니라 탐색을 돕는다.
- 마지막 문장은 시작을 여는 짧은 제안이나 질문으로 끝낸다.
- 인사말("안녕하세요, ~님")은 시스템이 따로 붙이므로 쓰지 않는다. 본문만 출력한다."""

# 행동 복창·과거 언급 표현 (01 4-4 / 5-5)
_BEHAVIOR_RECITE = re.compile(r"하셨|셨던|셨네요|지난번|최근에\s?(보|찾|검색|조회)|검색\s?이력|조회하신")
# 시스템이 지킬 수 없는 약속·정체성 위반
_PROMISE_BANNED = re.compile(r"종목\s?비중|비중을|수익\s?예측|얼마나\s?벌|추천|골라\s?드")


def _personal_tokens(profile: dict) -> set:
    """문장에 등장하면 복창으로 간주하는 개인 데이터 토큰."""
    toks = {profile.get("risk_profile", ""), str(profile.get("age", ""))}
    for h in profile.get("holdings", []):
        name = h.get("name") if isinstance(h, dict) else str(h)
        if name:
            toks.add(name)
    amount = profile.get("investment_context", {}).get("contribution", {}).get("amount")
    if amount:
        toks.add(str(amount))
    return {t for t in toks if t}


def _valid_intro(text: str, profile: dict):
    """반환: (통과 텍스트 | None, 실패 사유 | None)."""
    t = " ".join(str(text).split())
    # 길이는 스타일 속성 — 프롬프트로 150자 이내를 유도하고, 검증은 여유 있게 상한만 막는다
    if not (40 <= len(t) <= 220):
        return None, f"길이 {len(t)}자"
    if check_banned(t)[1]:
        return None, "금칙 표현"
    if _BEHAVIOR_RECITE.search(t):
        return None, "행동 복창 표현"
    if _PROMISE_BANNED.search(t):
        return None, "불가 약속·추천 어투"
    hit = next((tok for tok in _personal_tokens(profile) if tok in t), None)
    if hit:
        return None, f"개인 데이터 복창: {hit}"
    return t, None


def _profile_brief(profile: dict) -> str:
    ic = profile.get("investment_context", {})
    return json.dumps({
        "연령대": f"{profile['age'] // 10 * 10}대",
        "투자성향": profile.get("risk_profile"),
        "보유상품 수": len(profile.get("holdings", [])),
        "관심·검색 키워드": profile.get("search_history", []),
        "납입방식": ic.get("contribution", {}).get("type"),
        "계좌": profile.get("account_context", {}).get("account_type"),
    }, ensure_ascii=False)


def _dynamic_intro(profile: dict):
    """LLM 인트로 생성+검증 — 캐시 없이 매번 생성.

    반환: (인트로 | None, 폐기 사유 | None, 소요 초). 실패는 폴백으로 흡수.
    """
    t0 = time.monotonic()
    try:
        raw = _get_llm().invoke(_INTRO_PROMPT.format(brief=_profile_brief(profile))).content
    except Exception as exc:
        return None, f"LLM 호출 실패: {type(exc).__name__}", time.monotonic() - t0
    intro, reason = _valid_intro(raw, profile)
    return intro, reason, time.monotonic() - t0


def build_opening(profile: dict, dynamic: bool = True) -> dict:
    name = profile["name"]
    risk = profile["risk_profile"]
    holdings = profile.get("holdings", [])
    history = " ".join(profile.get("search_history", []))
    monthly = profile.get("investment_context", {}).get("contribution", {}).get("type") == "monthly"
    pension_interest = profile.get("account_context", {}).get("account_type") == "IRP" \
        or any(k in history for k in ["TDF", "연금", "IRP"])
    experienced = risk in ("적극투자형", "공격투자형") and len(holdings) >= 2
    cautious = risk == "안정형"

    # 폴백 템플릿 — 동적 인트로 검증 실패·LLM 불가 시 사용 (01 4-4 자동 보장)
    if experienced:
        intro = ("특정 종목이 담겼는지, 지역, 비용처럼 원하는 조건을 말씀해 주시면 "
                 "해당 조건을 충족하는 후보를 바로 찾아 비교해 드릴게요. 어떤 조건으로 볼까요?")
    elif pension_interest:
        intro = ("저는 TDF나 연금 같은 용어를 쉽게 설명하고, 계좌에서 살펴볼 수 있는 상품을 "
                 "조건별로 찾거나 비교해 드리는 AI 펀드 길잡이예요. 궁금한 것부터 시작해 볼까요?")
    elif cautious:
        intro = ("저는 펀드의 손실 가능성과 분배금 구조를 쉽게 설명하고, 가격 변동이 상대적으로 "
                 "작은 편부터 조건별로 살펴볼 수 있도록 도와드리는 AI 펀드 길잡이예요. "
                 "궁금한 것부터 편하게 물어보세요.")
    else:
        intro = ("저는 어려운 펀드 용어를 쉽게 풀어드리고, 말씀하신 목적과 기간을 바탕으로 "
                 "살펴볼 후보를 함께 좁혀드리는 AI 펀드 길잡이예요. "
                 "펀드가 처음이어도 괜찮아요. 어떤 것부터 알아볼까요?")

    # 개인화 신호 요약 — trace 로그용 (이름·상품명 원문 없이 신호 수준만)
    ic = profile.get("investment_context", {})
    signals = {
        "연령대": f"{profile['age'] // 10 * 10}대",
        "투자성향": risk,
        "보유상품": f"{len(holdings)}건",
        "관심·검색 키워드": profile.get("search_history", []),
        "납입방식": ic.get("contribution", {}).get("type"),
        "계좌": profile.get("account_context", {}).get("account_type"),
    }
    trace = [{"node": "opening", "kind": "info",
              "summary": "개인화 신호 추출: " + " · ".join(
                  f"{k} {v}" for k, v in signals.items()
                  if v and k != "관심·검색 키워드"),
              "detail": signals}]

    source, drop_reason = "rule", None
    if dynamic:
        generated, drop_reason, elapsed = _dynamic_intro(profile)
        if generated:
            intro, source = generated, "llm"
        trace.append({"node": "opening", "kind": "tool",
                      "summary": f"오프닝 본문 생성 — LLM 호출 ({elapsed:.1f}s, 복창 금지 지시 포함)",
                      "detail": {"elapsed_sec": round(elapsed, 2)}})
        trace.append({"node": "opening", "kind": "safety",
                      "summary": ("검증 통과 — LLM 인트로 채택" if source == "llm"
                                  else f"검증 실패({drop_reason}) → 템플릿 폴백"),
                      "detail": {"intro_source": source, "drop_reason": drop_reason,
                                 "checks": ["금칙 3범주", "행동 복창 표현", "불가 약속·추천 어투",
                                            "개인 데이터 토큰(보유상품명·성향·금액·나이)", "길이 40~220자"]}})
    else:
        trace.append({"node": "opening", "kind": "info",
                      "summary": "동적 생성 비활성 — 규칙 템플릿 사용", "detail": {}})

    # 칩 3개 — 이해하기 · 찾아보기 · 비교하기 역할 1개씩 (01 5-5) — 코드 유지
    if "TDF" in history or pension_interest:
        understand = "TDF 숫자의 의미 알아보기"
    elif cautious:
        understand = "펀드도 원금이 보장되나요?"
    elif not holdings:
        understand = "예금·적금과 펀드는 뭐가 다른가요?"
    else:
        understand = "위험등급은 어떻게 봐야 하나요?"

    if experienced and any(k in history for k in ["엔비디아", "나스닥", "반도체"]):
        find = "엔비디아 비중 높은 펀드 보기"
    elif pension_interest:
        find = "IRP에 담을 수 있는 TDF 보기"
    elif cautious:
        find = "가격 변동이 작은 편부터 살펴보기"
    elif monthly:
        find = "매달 나눠 넣는 상품 살펴보기"
    else:
        find = "조건에 맞는 상품 찾아보기"

    compare = "보유상품과 주요 종목 비교하기" if holdings else "후보 상품 비교해보기"

    return {
        "text": f"안녕하세요, {name} 고객님. {intro}",
        "chips": [understand, find, compare],
        "intro_source": source,            # llm | rule — UI 계약 외 참고 필드
        "intro_drop_reason": drop_reason,  # 검증 폐기 사유 (없으면 None)
        "trace": trace,                    # 오프닝 생성·검증 로그 — trace 패널 표시용
    }
