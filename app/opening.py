"""오프닝·빠른 시작 칩 — 코드 템플릿, LLM 호출 없음 (02 §8).

공통 골격(인사→능력 소개→시작 제안)에서 강조점과 칩 소재만 프로필 조건으로 분기한다.
행동 단정·개인 데이터 복창 금지(01 4-4)는 템플릿이므로 자동 보장된다.
"""


def build_opening(profile: dict) -> dict:
    name = profile["name"]
    risk = profile["risk_profile"]
    holdings = profile.get("holdings", [])
    history = " ".join(profile.get("search_history", []))
    monthly = profile.get("investment_context", {}).get("contribution", {}).get("type") == "monthly"
    pension_interest = profile.get("account_context", {}).get("account_type") == "IRP" \
        or any(k in history for k in ["TDF", "연금", "IRP"])
    experienced = risk in ("적극투자형", "공격투자형") and len(holdings) >= 2
    cautious = risk == "안정형"

    if experienced:
        intro = ("종목 비중, 지역, 비용처럼 원하는 조건을 말씀해 주시면 "
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

    # 칩 3개 — 이해하기 · 찾아보기 · 비교하기 역할 1개씩 (01 5-5)
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
    }
