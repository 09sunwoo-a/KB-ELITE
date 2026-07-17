# -*- coding: utf-8 -*-
"""펀드 길잡이 시연 UI 진입점 — screen 분기 + 사이드바 조종석 (04 §2, §3).

실행: streamlit run ui/streamlit_app.py
"""
import base64
import html as html_mod
import sys
import time
import uuid
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

sys.path.insert(0, str(Path(__file__).parent))

from adapter import AdapterConnectionError, create_adapter, default_mode  # noqa: E402
from mock_fixtures import (  # noqa: E402
    COURSE_1, COURSE_2, COURSE_3, COURSE_4,
    PERSONA_ORDER, PERSONAS, RISK_GRADE_BY_SCORE,
)
from styles import AUTOSCROLL_JS, CSS, mode_badge_html  # noqa: E402

ASSETS_DIR = Path(__file__).parent.parent / "assets"

# 노드 단위 처리 상태 문구 (04 §4-3 / §5-1 표시명)
NODE_PROGRESS = {
    "router": "질문을 이해하고 있어요",
    "explain": "용어 설명을 준비하고 있어요",
    "ask": "확인 질문을 준비하고 있어요",
    "search": "관련 펀드를 찾고 있어요",
    "compare": "후보 상품을 비교하고 있어요",
    "postprocess": "표현과 수치를 점검하고 있어요",
}

# 조건 키 → 고객 언어 라벨 (04 §4-2)
COND_LABELS = {
    "target_stock": lambda v: f"관심 종목: {v}",
    "cost_sensitive": lambda v: "비용: 낮은 편" if v else None,
    "region_theme": lambda v: f"테마·지역: {v}",
    "horizon": lambda v: f"기간: {v}",
    "fund_type_hint": lambda v: f"유형: {v}",
}

CHAT_SCROLL_HEIGHT = 440
TYPEWRITER_CHARS_PER_TICK = 3
TYPEWRITER_TICK_SEC = 0.014


# ---------------------------------------------------------------------------
# Session State (04 §6-4 보관 목록)
# ---------------------------------------------------------------------------

def init_state():
    defaults = {
        "screen": "fund_home",
        "persona_id": PERSONA_ORDER[0],
        "thread_id": None,
        "agent_mode": None,          # None → 최초 진입 시 default_mode()로 결정
        "trace_visible": False,
        "messages": [],
        "conditions": {},
        "last_candidates": [],
        "trace_events": [],
        "pending_prompt": None,
        "adapter_error": None,
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)

    if st.session_state.agent_mode is None:
        resolve_agent_mode(default_mode())


def resolve_agent_mode(wanted: str):
    """live 요청 실패 시 Mock으로 위장 전환하지 않고 오류를 보관한다(04 §1-3)."""
    try:
        create_adapter(wanted)
        st.session_state.agent_mode = wanted
        st.session_state.adapter_error = None
    except AdapterConnectionError as exc:
        st.session_state.agent_mode = "error"
        st.session_state.adapter_error = str(exc)


def reset_conversation():
    """새 thread 발급 + 오프닝 재생성. 기존 thread 재사용 금지(04 §3-1)."""
    persona = PERSONAS[st.session_state.persona_id]
    st.session_state.thread_id = str(uuid.uuid4())
    st.session_state.conditions = {}
    st.session_state.last_candidates = []
    st.session_state.trace_events = []
    st.session_state.pending_prompt = None
    st.session_state.messages = [{
        "role": "assistant",
        "content": persona["opening"],   # Live 연결(J1) 후에는 build_opening() 결과
        "chips": list(persona["chips"]),
        "result": None,
    }]


def on_persona_change():
    st.session_state.persona_id = st.session_state.persona_radio
    reset_conversation()


def start_chat():
    st.session_state.screen = "chat"
    reset_conversation()


# ---------------------------------------------------------------------------
# 사이드바 — 시연 조종석 (04 §3)
# ---------------------------------------------------------------------------

def render_sidebar():
    with st.sidebar:
        st.markdown("### 🎛 시연 조종석")
        st.radio(
            "페르소나",
            PERSONA_ORDER,
            format_func=lambda pid: PERSONAS[pid]["label"],
            key="persona_radio",
            index=PERSONA_ORDER.index(st.session_state.persona_id),
            on_change=on_persona_change,
        )

        persona = PERSONAS[st.session_state.persona_id]
        st.markdown("**고객 컨텍스트**")
        for label, value in persona["context"].items():
            st.markdown(
                f"<div style='font-size:0.82rem; color:#5a5344; margin-bottom:2px'>"
                f"<b>{label}</b> — {value}</div>",
                unsafe_allow_html=True,
            )

        st.divider()
        st.markdown("**시연 코스** (클릭 → 실제 입력으로 주입)")
        courses = [
            ("course_1", "① 조건으로 바로 찾기", COURSE_1),
            ("course_2", "② 후보 상품 비교", COURSE_2),
            ("course_3", "③ 보유종목 겹침 확인", COURSE_3),
            ("course_4", "④ AI 펀드 위험 확인", COURSE_4),
        ]
        for key, label, prompt in courses:
            if st.button(label, key=key, use_container_width=True):
                if st.session_state.screen != "chat":
                    start_chat()
                st.session_state.pending_prompt = prompt
                st.rerun()
        st.caption("④는 페르소나에 따라 결과가 달라져요 (정미숙: 차단 / 최준혁: 정상 — 교차는 Live에서)")

        st.divider()
        st.toggle("Agent 동작 보기", key="trace_visible")
        if st.button("대화 초기화", use_container_width=True):
            reset_conversation()
            st.rerun()
        if st.button("펀드 화면으로 돌아가기", use_container_width=True):
            st.session_state.screen = "fund_home"
            st.rerun()

        st.divider()
        st.markdown(mode_badge_html(st.session_state.agent_mode), unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# 화면 1 — 스타뱅킹 펀드 서브메인 (04 §2 화면 1)
# ---------------------------------------------------------------------------

def phone_screen_html() -> tuple[str, str]:
    """(스크린 내용 HTML, phone-screen 추가 클래스)를 반환한다."""
    capture = ASSETS_DIR / "fund_submain.png"
    if capture.exists():
        b64 = base64.b64encode(capture.read_bytes()).decode()
        return f'<img class="submain" src="data:image/png;base64,{b64}" alt="펀드 서브메인"/>', " capture"
    # fallback 목업 (캡처 없음)
    return """
      <div class="pf-appbar"><span>☰&nbsp; 펀드</span><span>🔔</span></div>
      <div class="pf-banner">6월 펀드 시장 브리핑<br><small>글로벌 증시 흐름 한눈에 보기 ›</small></div>
      <div class="pf-grid">
        <div class="pf-menu">🔍 펀드 찾기</div><div class="pf-menu">📁 내 펀드</div>
        <div class="pf-menu">📈 수익률 조회</div><div class="pf-menu">📝 투자성향 진단</div>
      </div>
      <div class="pf-list-title">많이 찾는 펀드 테마</div>
      <div class="pf-item">미국 인덱스 <span>주식형</span></div>
      <div class="pf-item">TDF·연금 <span>자산배분</span></div>
      <div class="pf-item">월지급식·인컴 <span>채권혼합</span></div>
      <div class="pf-item">국공채·MMF <span>안정형 자금</span></div>
    """, ""


def render_fund_home():
    st.markdown(
        "<h4 style='text-align:center; margin-bottom:0.4rem'>스타뱅킹 · 펀드</h4>",
        unsafe_allow_html=True,
    )
    _, mid, _ = st.columns([1, 1.4, 1])
    with mid:
        screen_html, screen_cls = phone_screen_html()
        with st.container(key="phone_zone"):
            st.markdown(
                f"""
                <div class="phone-frame">
                  <div class="phone-notch"></div>
                  <div class="phone-screen{screen_cls}">{screen_html}</div>
                  <div class="pf-caption">Prototype · 실제 스타뱅킹 화면 기반 시연</div>
                </div>
                <div class="fab-bubble">어떤 펀드를 봐야 할지 막막하신가요?</div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("🧭 AI 펀드 길잡이", key="ai_fab"):
                start_chat()
                st.rerun()


# ---------------------------------------------------------------------------
# 화면 2 — Chat UI, 폰 프레임 안에서 진행 (04 §2 화면 2, §4)
# ---------------------------------------------------------------------------

def bubble_html(role: str, text: str, cursor: bool = False) -> str:
    safe = html_mod.escape(text).replace("\n", "<br>")
    if cursor:
        safe += '<span class="cursor">▌</span>'
    kind = "user" if role == "user" else "bot"
    return f'<div class="msg-row {kind}"><div class="bubble {kind}">{safe}</div></div>'


def typing_html(label: str) -> str:
    return (
        '<div class="msg-row bot">'
        '<div class="bubble bot typing"><span class="dots"><i></i><i></i><i></i></span>'
        f'<span class="nlabel">{html_mod.escape(label)}…</span></div></div>'
    )


def chatbar_html() -> str:
    """대화 헤더 + 고객 컨텍스트 서브라인 (04 §4-0 프로필 스트립)."""
    persona = PERSONAS[st.session_state.persona_id]
    cap = RISK_GRADE_BY_SCORE[persona["max_risk_score"]]
    return f"""
    <div class="chatbar">
      <div class="phone-notch"></div>
      <div class="cb-row">
        <span class="cb-back">‹</span>
        <span class="cb-avatar">🧭</span>
        <div class="cb-title">AI 펀드 길잡이<br><small>● 온라인</small></div>
      </div>
      <div class="cb-sub">
        <b>{persona["name"]}님</b> · {persona["risk_profile"]} ·
        <b>{cap}</b>까지 노출 — 투자성향을 넘는 상품은 후보로 노출되지 않아요
      </div>
    </div>
    """


def render_condition_bar():
    """조건이 없으면 내용은 숨기되 자리는 유지한다(프레임 규격 고정)."""
    conds = st.session_state.conditions
    chips = []
    for key, value in conds.items():
        fmt = COND_LABELS.get(key)
        label = fmt(value) if fmt else f"{key}: {value}"
        if label:
            chips.append(f'<span class="cond-chip">{label}</span>')
    empty = "" if chips else " empty"
    st.markdown(
        f'<div class="cond-bar{empty}"><span class="cond-title">현재 탐색 기준</span>{"".join(chips)}</div>',
        unsafe_allow_html=True,
    )


def render_result_placeholders(result):
    """B2에서 카드·비교표·겹침·차단 박스 컴포넌트로 대체된다."""
    if not result:
        return
    notes = []
    if result.get("candidates"):
        notes.append(f"후보 카드 {len(result['candidates'])}건")
    if result.get("comparison"):
        notes.append(f"비교표 {len(result['comparison']['rows'])}행")
    if result.get("overlap"):
        notes.append("겹침 분석 결과")
    if result.get("risk_block") and result["risk_block"].get("blocked"):
        notes.append("성향 초과 차단 안내 박스")
    if notes:
        st.caption("🧩 " + " · ".join(notes) + " — 렌더링은 B2 단계에서 추가됩니다")


def render_chips(message, msg_idx):
    chips = message.get("chips") or []
    if not chips:
        return
    for i, chip in enumerate(chips):
        if st.button(chip, key=f"chip_{msg_idx}_{i}"):
            st.session_state.pending_prompt = chip
            st.rerun()


def run_turn(scroll_area, prompt):
    """사용자 말풍선 표시 → 노드 진행(타이핑 인디케이터) → 답변 타자기 연출."""
    adapter = create_adapter(st.session_state.agent_mode)
    result = None
    with scroll_area:
        st.markdown(bubble_html("user", prompt), unsafe_allow_html=True)
        placeholder = st.empty()
        try:
            for event in adapter.stream_turn(
                prompt, st.session_state.thread_id, st.session_state.persona_id
            ):
                etype = event.get("event_type")
                if etype == "node_started":
                    label = NODE_PROGRESS.get(event.get("node", ""), "처리하고 있어요")
                    placeholder.markdown(typing_html(label), unsafe_allow_html=True)
                elif etype == "turn_completed":
                    result = event["result"]
                elif etype == "turn_error":
                    placeholder.empty()
                    st.error(event.get("error", "일시적인 문제가 발생했어요. 다시 시도해 주세요."))
                    return
        except Exception:
            # stack trace 노출 금지 (04 §8)
            placeholder.empty()
            st.error("일시적인 문제가 발생했어요. 잠시 후 다시 시도해 주세요.")
            return

        if result is None:
            placeholder.empty()
            return

        # 답변 타자기 연출 (04 조정 #6) — postprocess를 통과한 완성본을 표시
        answer = result["answer"]
        for end in range(TYPEWRITER_CHARS_PER_TICK, len(answer) + TYPEWRITER_CHARS_PER_TICK,
                         TYPEWRITER_CHARS_PER_TICK):
            placeholder.markdown(bubble_html("assistant", answer[:end], cursor=True),
                                 unsafe_allow_html=True)
            time.sleep(TYPEWRITER_TICK_SEC)
        placeholder.markdown(bubble_html("assistant", answer), unsafe_allow_html=True)

    st.session_state.messages.append({
        "role": "assistant",
        "content": result["answer"],
        "chips": result["chips"],
        "result": result,
    })
    if result.get("conditions"):
        st.session_state.conditions = result["conditions"]
    if result.get("candidates"):
        st.session_state.last_candidates = result["candidates"]
    st.session_state.trace_events.append({
        "user_message": prompt,
        "action": result["action"],
        "action_reason": result["action_reason"],
        "trace": result["trace"],
    })
    st.rerun()


def render_chat():
    # 모드 오류(Live 연결 실패) — 명시적 전환만 허용 (04 §1-3)
    if st.session_state.agent_mode == "error":
        st.error(st.session_state.adapter_error or "Agent 연결에 실패했습니다.")
        if st.button("Mock 모드로 전환하기"):
            resolve_agent_mode("mock")
            st.rerun()
        return

    if st.session_state.trace_visible:
        chat_col, trace_col = st.columns([1.6, 1.0])
        with trace_col:
            st.markdown(mode_badge_html(st.session_state.agent_mode), unsafe_allow_html=True)
            st.caption("Agent 동작 패널은 B3 단계에서 구현됩니다.")
    else:
        chat_col = st.container()

    prompt = st.session_state.pop("pending_prompt", None)

    with chat_col:
        with st.container(key="chat_phone"):
            st.markdown(chatbar_html(), unsafe_allow_html=True)
            render_condition_bar()

            scroll_area = st.container(height=CHAT_SCROLL_HEIGHT, key="chat_scroll")
            with scroll_area:
                messages = st.session_state.messages
                for idx, msg in enumerate(messages):
                    st.markdown(bubble_html(msg["role"], msg["content"]), unsafe_allow_html=True)
                    if msg["role"] == "assistant":
                        render_result_placeholders(msg.get("result"))
                # 빠른 시작/후속 칩 — 대화 흐름 안, 마지막 말풍선 아래 (진행 중이면 숨김)
                if messages and messages[-1]["role"] == "assistant" and not prompt:
                    render_chips(messages[-1], len(messages) - 1)

            typed = st.chat_input("궁금한 점을 편하게 물어보세요")
            if typed:
                prompt = typed

        st.markdown(
            f"<div style='text-align:center; margin-top:6px'>{mode_badge_html(st.session_state.agent_mode)}"
            "<span style='color:#9a927e; font-size:0.72rem; margin-left:8px'>Prototype · 시연용</span></div>",
            unsafe_allow_html=True,
        )
        components.html(AUTOSCROLL_JS, height=0)

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        run_turn(scroll_area, prompt)


# ---------------------------------------------------------------------------

def main():
    st.set_page_config(page_title="AI 펀드 길잡이 — 시연", page_icon="🧭", layout="wide")
    st.markdown(CSS, unsafe_allow_html=True)
    init_state()
    render_sidebar()
    if st.session_state.screen == "chat":
        render_chat()
    else:
        render_fund_home()


main()
