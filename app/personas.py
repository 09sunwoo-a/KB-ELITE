"""프로필 로드 — 그래프 밖 세션 초기화 (02 §2). 성향 → 노출 상한 매핑 (01 4-2)."""

from app import store

MAX_RISK = {"안정형": 2, "안정추구형": 3, "위험중립형": 4, "적극투자형": 5, "공격투자형": 6}

PERSONA_LABELS = {
    "P1": "서지우 · 펀드 초보형",
    "P2": "박서연 · 연금 탐색형",
    "P3": "최준혁 · 조건 명확형",
    "P4": "정미숙 · 원금 민감형",
}


def load_profile(persona_id: str) -> dict:
    """State 초기값: profile + max_risk_score. 세션(thread) 시작 시 1회."""
    profile = store.persona(persona_id)
    return {
        "profile": profile,
        "max_risk_score": MAX_RISK[profile["risk_profile"]],
        "conditions": {},
        "last_candidates": [],
        "ask_streak": 0,
    }
