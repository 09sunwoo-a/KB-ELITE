# -*- coding: utf-8 -*-
"""시연 코스 ①~④ Mock fixture — 04 §7 / 스키마는 04 §6-3 AgentTurnResult.

- 모든 수치·상품 정보는 data/funds.json 실데이터에서 그대로 옮긴 값이다
  (기준일 2026-06-30). LLM 서술(answer)만 대본(01 v4) 톤으로 작성.
- 코스 ④는 정미숙(안정형, 노출 상한 risk_score 2) 기준의 risk_block 케이스.
  최준혁 교차 시연은 J1 Live 연결에서만 가능하다.
- 종목 편입 비중·중복률은 데이터에 없으므로 어떤 fixture에도 넣지 않는다(04 조정 #3).
"""

AS_OF = "2026-06-30"

OVERLAP_NOTE = (
    "2026-06-30 공개된 주요 보유종목 기준이며, 펀드 내 편입 비중과 "
    "전체 포트폴리오 중복률은 공개 데이터에 없어 계산하지 않습니다."
)

DISCLOSURE = "투자 판단과 선택은 고객님께 있으며, 펀드는 원금이 보장되지 않습니다."

# 시연 코스 버튼 문구 (04 §3과 동일해야 한다)
COURSE_1 = "엔비디아 많이 들어가고 비용 낮은 펀드 찾아줘"
COURSE_2 = "1번과 3번 비교해줘"
COURSE_3 = "나 엔비디아 직접 갖고 있는데 얼마나 겹쳐?"
COURSE_4 = "요즘 AI 펀드 어때요?"

# ---------------------------------------------------------------------------
# 코스 ① — 조건으로 바로 찾기 (search)
# 최준혁(적극투자형, 상한 5). 엔비디아 alias 매칭 25건 중 성향 초과 4건 제외,
# has_holdings_info 기준 통과 후 fee_pct 오름차순 상위 3건. (data/funds.json 실값)
# ---------------------------------------------------------------------------

FIXTURE_COURSE_1 = {
    "answer": (
        "공개된 주요 보유종목에 엔비디아가 포함된 상품을 찾고, "
        "연간 비용이 낮은 순으로 정리했어요. 세 후보 모두 미국 주식형이지만 "
        "①은 종목을 선별해 담는 방식이고 ②·③은 지수를 따라가는 "
        "인덱스(파생형)라는 차이가 있어요. 종목별 편입 비중은 공개 데이터에 "
        "없어 표시하지 않아요. " + DISCLOSURE
    ),
    "action": "search",
    "action_reason": "관심 종목과 비용 조건이 명확해 추가 질문 없이 검색합니다.",
    "conditions": {"target_stock": "엔비디아", "cost_sensitive": True},
    "candidates": [
        {
            "fund_code": "KF04001379",
            "name": "피델리티 미국 증권 자투자신탁(주식-재간접형) Ce",
            "fund_type": "주식형",
            "region": "미국",
            "risk_grade": "다소높은위험",
            "fee_pct": 0.662,
            "manager": "피델리티자산운용",
            "matched_stocks": ["엔비디아"],
            "top_stocks_summary": "엔비디아, 마이크로소프트, 알파벳(구글)",
            "returns_display": {"period": "12개월", "value": 8.71},
            "selection_reason": "엔비디아를 주요 종목으로 담고 있고 후보 중 연간 비용이 가장 낮은 편",
            "as_of": AS_OF,
        },
        {
            "fund_code": "KF04000498",
            "name": "KB스타 미국S&P500인덱스 증권자투자신탁(주식-파생형)(H)-C-E",
            "fund_type": "주식형",
            "region": "미국",
            "risk_grade": "높은위험",
            "fee_pct": 1.0,
            "manager": "KB자산운용",
            "matched_stocks": ["엔비디아"],
            "top_stocks_summary": "S&P500 ETF, 엔비디아, 애플",
            "returns_display": {"period": "12개월", "value": 22.87},
            "selection_reason": "S&P500 지수를 추종하며 주요 보유종목에 엔비디아 포함, 비용은 후보 중 중간 수준",
            "as_of": AS_OF,
        },
        {
            "fund_code": "KF04003097",
            "name": "KB스타 미국 나스닥 100 인덱스 증권자투자신탁(주식-파생형)(H) C-E",
            "fund_type": "주식형",
            "region": "미국",
            "risk_grade": "높은위험",
            "fee_pct": 1.0,
            "manager": "KB자산운용",
            "matched_stocks": ["엔비디아"],
            "top_stocks_summary": "나스닥100 ETF(QQQ 등), 엔비디아",
            "returns_display": {"period": "12개월", "value": 33.07},
            "selection_reason": "나스닥100 지수를 추종하며 주요 보유종목에 엔비디아 포함, 비용은 후보 중 중간 수준",
            "as_of": AS_OF,
        },
    ],
    "comparison": None,
    "overlap": None,
    "risk_block": {"excluded_by_risk": 4, "blocked": False},
    "chips": [COURSE_2, COURSE_3, "수익률도 같이 보여줘"],
    "trace": [
        {
            "node": "router",
            "kind": "route",
            "summary": "행동 선택: SEARCH — 종목·비용 조건이 명확해 바로 검색",
            "detail": {
                "action": "search",
                "action_reason": "관심 종목과 비용 조건이 명확해 추가 질문 없이 검색합니다.",
                "extracted_conditions": {"target_stock": "엔비디아", "cost_sensitive": True},
                "ask_streak": 0,
            },
        },
        {
            "node": "search",
            "kind": "tool",
            "summary": "search_funds — 정형 필터 21건 통과, 비용 오름차순 상위 3건 채택",
            "detail": {
                "tool": "search_funds",
                "input_summary": {"target_stock": "엔비디아", "cost_sensitive": True, "max_risk_score": 5},
                "alias_matched": 25,
                "passed_filter": 21,
                "excluded_by_risk": 4,
                "sort": "fee_pct 오름차순",
                "selected_codes": ["KF04001379", "KF04000498", "KF04003097"],
            },
        },
        {
            "node": "search",
            "kind": "retrieval",
            "summary": "벡터 검색 미사용 — 정형 필터+정렬로 종결",
            "detail": {"vector_used": False, "reason": "정형 조건(종목·비용)이 명확해 필터+정렬로 충분"},
        },
        {
            "node": "postprocess",
            "kind": "safety",
            "summary": "표현·수치 안전 점검 통과 (치환 0건, 성향 초과 4건 노출 차단)",
            "detail": {
                "banned_replaced": 0,
                "numeric_mismatch": 0,
                "disclosure_inserted": True,
                "excluded_by_risk": 4,
                "blocked": False,
            },
        },
    ],
}

# ---------------------------------------------------------------------------
# 코스 ② — 후보 상품 비교 (compare): 코스 ① 결과의 1번·3번
# ---------------------------------------------------------------------------

FIXTURE_COURSE_2 = {
    "answer": (
        "①번과 ③번의 차이를 정리했어요. ①번은 미국 성장주를 선별해 담는 "
        "방식이고 연간 비용이 낮은 편이에요. ③번은 나스닥100 지수를 그대로 "
        "따라가는 인덱스(파생형)이고 위험등급이 한 단계 높아요. 최근 12개월 "
        "수익률은 두 상품이 다르지만, 과거 수익률이 앞으로의 수익을 보장하지는 "
        "않아요. 어떤 기준이 더 중요하신지에 따라 선택이 달라질 수 있어요. "
        + DISCLOSURE
    ),
    "action": "compare",
    "action_reason": "직전 검색 결과의 1번과 3번을 비교 대상으로 해석했습니다.",
    "conditions": {"target_stock": "엔비디아", "cost_sensitive": True},
    "candidates": [],
    "comparison": {
        "fund_codes": ["KF04001379", "KF04003097"],
        "rows": [
            {"label": "상품명", "values": [
                "피델리티 미국 증권 자투자신탁(주식-재간접형) Ce",
                "KB스타 미국 나스닥 100 인덱스 증권자투자신탁(주식-파생형)(H) C-E",
            ]},
            {"label": "유형", "values": ["주식형(재간접)", "주식형(인덱스-파생)"]},
            {"label": "지역", "values": ["미국", "미국"]},
            {"label": "위험등급", "values": ["다소높은위험", "높은위험"]},
            {"label": "연간 비용", "values": ["0.66%", "1.00%"]},
            {"label": "12개월 수익률 (2026-06-30 기준)", "values": ["8.71%", "33.07%"]},
            {"label": "주요 보유종목", "values": [
                "엔비디아, 마이크로소프트, 알파벳(구글)",
                "나스닥100 ETF(QQQ 등), 엔비디아",
            ]},
            {"label": "기준일", "values": [AS_OF, AS_OF]},
        ],
    },
    "overlap": None,
    "risk_block": None,
    "chips": [COURSE_3, "두 상품 비용을 원 단위로 알려줘", "다른 후보도 보여줘"],
    "trace": [
        {
            "node": "router",
            "kind": "route",
            "summary": "행동 선택: COMPARE — '1번과 3번'을 직전 후보 목록에서 해석",
            "detail": {
                "action": "compare",
                "action_reason": "직전 검색 결과의 1번과 3번을 비교 대상으로 해석했습니다.",
                "compare_targets": [1, 3],
                "resolved_codes": ["KF04001379", "KF04003097"],
            },
        },
        {
            "node": "compare",
            "kind": "info",
            "summary": "비교표 조립 — funds.json 원본 값으로 8개 항목 구성",
            "detail": {
                "source": "funds.json",
                "fund_codes": ["KF04001379", "KF04003097"],
                "row_labels": ["상품명", "유형", "지역", "위험등급", "연간 비용", "12개월 수익률", "주요 보유종목", "기준일"],
            },
        },
        {
            "node": "postprocess",
            "kind": "safety",
            "summary": "표현·수치 안전 점검 통과 (우열 표현 0건, 수치 불일치 0건)",
            "detail": {
                "banned_replaced": 0,
                "numeric_mismatch": 0,
                "disclosure_inserted": True,
            },
        },
    ],
}

# ---------------------------------------------------------------------------
# 코스 ③ — 보유종목 겹침 확인 (compare/overlap)
# 최준혁 직접 보유: 엔비디아·테슬라. ①번(피델리티) stocks_raw 기준 겹침은
# 엔비디아 1종목뿐이다(테슬라 미포함 — 실데이터).
# ---------------------------------------------------------------------------

FIXTURE_COURSE_3 = {
    "answer": (
        "직접 보유하신 종목(엔비디아, 테슬라) 기준으로 확인했어요. "
        "①번 피델리티 미국 펀드의 공개된 상위 보유종목에는 고객님이 직접 "
        "보유한 종목 중 1개(엔비디아)가 포함되어 있어요. 테슬라는 공개된 "
        "주요 보유종목에 없어요. 겹침이 있다는 사실 자체가 좋거나 나쁜 것은 "
        "아니고, 특정 종목에 대한 노출이 커질 수 있다는 참고 정보예요. "
        + DISCLOSURE
    ),
    "action": "compare",
    "action_reason": "직접 보유 종목과 후보 펀드의 공개 보유종목 겹침을 확인합니다.",
    "conditions": {"target_stock": "엔비디아", "cost_sensitive": True},
    "candidates": [],
    "comparison": None,
    "overlap": {
        "available": True,
        "fund_code": "KF04001379",
        "fund_name": "피델리티 미국 증권 자투자신탁(주식-재간접형) Ce",
        "overlap_stocks": ["엔비디아"],
        "as_of": AS_OF,
        "note": OVERLAP_NOTE,
    },
    "risk_block": None,
    "chips": ["③번 펀드와도 겹치는지 봐줘", COURSE_2, "다른 조건으로 다시 찾아보기"],
    "trace": [
        {
            "node": "router",
            "kind": "route",
            "summary": "행동 선택: COMPARE(겹침) — 직접 보유 종목과의 중복 확인 의도",
            "detail": {
                "action": "compare",
                "action_reason": "직접 보유 종목과 후보 펀드의 공개 보유종목 겹침을 확인합니다.",
                "overlap_intent": True,
                "target_fund": "KF04001379",
            },
        },
        {
            "node": "compare",
            "kind": "tool",
            "summary": "match_overlap — 보유 2종목 중 1종목(엔비디아) 겹침",
            "detail": {
                "tool": "match_overlap",
                "input_summary": {"customer_stocks": ["엔비디아", "테슬라"], "fund_code": "KF04001379"},
                "overlap_stocks": ["엔비디아"],
                "available": True,
                "note": "종목명 리스트만 반환 — 편입 비중·중복률 계산 없음",
            },
        },
        {
            "node": "postprocess",
            "kind": "safety",
            "summary": "표현·수치 안전 점검 통과 + 겹침 한계 고지 삽입",
            "detail": {
                "banned_replaced": 0,
                "numeric_mismatch": 0,
                "disclosure_inserted": True,
                "limit_notice": "편입 비중·중복률 미계산 고지 포함",
            },
        },
    ],
}

# ---------------------------------------------------------------------------
# 코스 ④ — AI 펀드 (search → 전부 차단): 정미숙(안정형, 상한 2) 케이스
# AI 테마 상품은 전원 risk_score 4 이상(실데이터) → 후보 0개, blocked.
# ---------------------------------------------------------------------------

FIXTURE_COURSE_4 = {
    "answer": (
        "확인해 보니 현재 조회되는 AI 관련 펀드는 모두 '다소높은위험' 이상 "
        "등급이에요. 고객님의 공식 투자성향(안정형)으로 가입 가능한 위험등급 "
        "범위를 넘어서, 이 화면에서는 후보로 안내해 드리지 않아요. 가입 가능 "
        "범위는 투자성향 재진단에 따라 달라질 수 있어요. 이전에 보시던 후보로 "
        "돌아갈까요, 아니면 가입 가능한 범위에서 다른 조건으로 찾아볼까요?"
    ),
    "action": "search",
    "action_reason": "AI 테마 검색 결과가 전부 투자성향 노출 상한을 초과해 차단 안내로 전환합니다.",
    "conditions": {"region_theme": "AI"},
    "candidates": [],
    "comparison": None,
    "overlap": None,
    "risk_block": {"excluded_by_risk": 10, "blocked": True},
    "chips": ["가입 가능한 범위에서 찾아보기", "이전 후보로 돌아가기"],
    "trace": [
        {
            "node": "router",
            "kind": "route",
            "summary": "행동 선택: SEARCH — AI 테마 상품 탐색",
            "detail": {
                "action": "search",
                "action_reason": "AI 테마 검색 의도가 명확해 검색을 실행합니다.",
                "extracted_conditions": {"region_theme": "AI"},
            },
        },
        {
            "node": "search",
            "kind": "tool",
            "summary": "search_funds — AI 매칭 10건 전원 성향 초과, 통과 0건 (blocked)",
            "detail": {
                "tool": "search_funds",
                "input_summary": {"region_theme": "AI", "max_risk_score": 2},
                "alias_matched": 10,
                "passed_filter": 0,
                "excluded_by_risk": 10,
                "blocked": True,
            },
        },
        {
            "node": "postprocess",
            "kind": "safety",
            "summary": "성향 초과 상품 10건 노출 차단 — 차단 안내·대안 칩 삽입",
            "detail": {
                "banned_replaced": 0,
                "numeric_mismatch": 0,
                "disclosure_inserted": True,
                "excluded_by_risk": 10,
                "blocked": True,
                "block_notice": "차단 사실·사유(성향 범위 초과)·대안 안내 삽입",
            },
        },
    ],
}

# ---------------------------------------------------------------------------
# 그 외 입력 — 고정 안내 (04 §7)
# ---------------------------------------------------------------------------

FIXTURE_FALLBACK = {
    "answer": "Mock 모드에서는 시연 코스 버튼을 사용해 주세요. (사이드바의 시연 코스 ①~④)",
    "action": "ask",
    "action_reason": "Mock 모드는 시연 코스 4개 입력에만 응답합니다.",
    "conditions": {},
    "candidates": [],
    "comparison": None,
    "overlap": None,
    "risk_block": None,
    "chips": [COURSE_1, COURSE_2, COURSE_4],
    "trace": [
        {
            "node": "router",
            "kind": "info",
            "summary": "Mock 모드 — 시연 코스 외 입력 고정 응답",
            "detail": {"mock": True},
        },
    ],
}

FIXTURES = {
    COURSE_1: FIXTURE_COURSE_1,
    COURSE_2: FIXTURE_COURSE_2,
    COURSE_3: FIXTURE_COURSE_3,
    COURSE_4: FIXTURE_COURSE_4,
}


def get_fixture(user_message: str) -> dict:
    """입력 문구에 해당하는 AgentTurnResult fixture를 반환한다(없으면 fallback)."""
    return FIXTURES.get(user_message.strip(), FIXTURE_FALLBACK)


# ---------------------------------------------------------------------------
# Mock 페르소나 프로필 — 01 v4 §6 원문 기반 (트랙 A의 data/personas/ 완성 전
# 프론트 개발용. 오프닝·칩 문구는 01 §6 대본 그대로다.)
# 런타임은 페르소나 ID로 분기하지 않는다 — 오프닝·컨텍스트 표시에만 사용.
# ---------------------------------------------------------------------------

PERSONA_ORDER = ["P3", "P4", "P2", "P1"]  # 사이드바 순서 (04 §3)

# risk_score → 위험등급 텍스트 (03 §4). 노출 상한 표시(04 §4-0)에 사용.
RISK_GRADE_BY_SCORE = {
    1: "매우낮은위험", 2: "낮은위험", 3: "보통위험",
    4: "다소높은위험", 5: "높은위험", 6: "매우높은위험",
}

PERSONAS = {
    "P3": {
        "name": "최준혁",
        "label": "최준혁 · 조건 명확형",
        "risk_profile": "적극투자형",
        "max_risk_score": 5,
        "context": {
            "투자성향": "적극투자형 (노출 상한: 높은위험)",
            "투자방식": "거치식 2,000만원",
            "관심분야": "나스닥 · 반도체 · 엔비디아",
            "보유 요약": "엔비디아·테슬라 주식, 국내 주식형 펀드 1건",
        },
        "opening": (
            "안녕하세요, 최준혁 고객님. 종목 비중, 지역, 비용처럼 원하는 조건을 "
            "말씀해 주시면 해당 조건을 충족하는 후보를 바로 찾아 비교해 드릴게요. "
            "어떤 조건으로 볼까요?"
        ),
        "chips": ["엔비디아 비중 높은 펀드 보기", "나스닥 펀드 비용 낮은 순으로 보기", "보유 종목과 중복 확인하기"],
    },
    "P4": {
        "name": "정미숙",
        "label": "정미숙 · 원금 민감형",
        "risk_profile": "안정형",
        "max_risk_score": 2,
        "context": {
            "투자성향": "안정형 (노출 상한: 낮은위험)",
            "투자방식": "거치식 5,000만원",
            "관심분야": "배당 · 월지급식 · 원금보장",
            "보유 요약": "MMF 1건, 국공채 채권형 펀드 1건",
        },
        "opening": (
            "안녕하세요, 정미숙 고객님. 저는 펀드의 손실 가능성과 분배금 구조를 "
            "쉽게 설명하고, 가격 변동이 상대적으로 작은 편부터 조건별로 살펴볼 수 "
            "있도록 도와드리는 AI 펀드 길잡이예요. 궁금한 것부터 편하게 물어보세요."
        ),
        "chips": ["펀드도 원금이 보장되나요?", "월지급식은 어떻게 지급되나요?", "가격 변동이 작은 편부터 살펴보기"],
    },
    "P2": {
        "name": "박서연",
        "label": "박서연 · 연금 탐색형",
        "risk_profile": "위험중립형",
        "max_risk_score": 4,
        "context": {
            "투자성향": "위험중립형 (노출 상한: 다소높은위험)",
            "투자방식": "적립식 월 50만원 (IRP)",
            "관심분야": "TDF · 연금저축 · IRP",
            "보유 요약": "미국 주식형 펀드 1건",
        },
        "opening": (
            "안녕하세요, 박서연 고객님. 저는 TDF나 연금 같은 용어를 쉽게 설명하고, "
            "계좌에서 살펴볼 수 있는 상품을 조건별로 찾거나 비교해 드리는 "
            "AI 펀드 길잡이예요. 궁금한 것부터 시작해 볼까요?"
        ),
        "chips": ["TDF 2050의 숫자는 무슨 뜻인가요?", "IRP에서 담을 수 있는 TDF 보기", "보유 펀드와 자산구성 비교하기"],
    },
    "P1": {
        "name": "서지우",
        "label": "서지우 · 펀드 초보형",
        "risk_profile": "안정추구형",
        "max_risk_score": 3,
        "context": {
            "투자성향": "안정추구형 (노출 상한: 보통위험)",
            "투자방식": "적립식 월 20만원",
            "관심분야": "첫 탐색 (검색 이력 없음)",
            "보유 요약": "보유 상품 없음",
        },
        "opening": (
            "안녕하세요, 서지우 고객님. 저는 어려운 펀드 용어를 쉽게 풀어드리고, "
            "말씀하신 목적과 기간을 바탕으로 살펴볼 후보를 함께 좁혀드리는 "
            "AI 펀드 길잡이예요. 펀드가 처음이어도 괜찮아요. 어떤 것부터 알아볼까요?"
        ),
        "chips": ["예금·적금과 펀드는 뭐가 다른가요?", "펀드도 원금 손실이 날 수 있나요?", "매달 나눠 넣는 상품부터 보고 싶어요"],
    },
}
