# -*- coding: utf-8 -*-
"""Trace 패널 — `Agent 동작 보기` (04 §5).

trace 노출 금지(04 §1-5): 모델 CoT, 시스템 프롬프트 원문, API Key,
고객 식별자 원문, 임베딩 벡터, RAG CONTENT 원문 전체. 이 패널은
TraceEntry의 summary/detail(노출 가능 데이터만 담김)만 렌더링한다.
"""
import streamlit as st

from styles import mode_badge_html

# 내부 노드 → 화면 표시명 (04 §5-1)
NODE_LABELS = {
    "router": "질문 의도 파악·행동 선택",
    "explain": "용어 설명 준비",
    "ask": "확인 질문 준비",
    "search": "관련 펀드 탐색",
    "compare": "후보 상품 비교",
    "postprocess": "표현·수치 안전 점검",
}

# 탐색 노트의 detail 키 → 고객 언어 라벨 (04 §5-2)
NOTE_LABELS = {
    "extracted_conditions": "추출한 탐색 조건",
    "compare_targets": "비교 대상(후보 번호)",
    "resolved_codes": "해석된 상품코드",
    "selected_codes": "채택 상품코드",
    "target_fund": "대상 상품코드",
    "overlap_intent": "보유종목 겹침 의도",
    "ask_streak": "연속 확인 질문 수",
}


def _flow_section(trace: list):
    """실행 흐름 — 노드 진행 + 도구 호출 들여쓰기 (04 §5-1)."""
    lines = []
    seen = []
    for entry in trace:
        node = entry.get("node")
        if node not in seen:
            seen.append(node)
            label = NODE_LABELS.get(node, node)
            lines.append(f'<div class="tp-node">✓ {label}</div>')
        if entry.get("kind") == "tool":
            tool = entry.get("detail", {}).get("tool", "도구")
            lines.append(f'<div class="tp-tool">└ 🔧 {tool} — {entry.get("summary", "")}</div>')
    st.markdown("".join(lines), unsafe_allow_html=True)


def _notes_tab(event: dict):
    """탐색 노트 — conditions·후보·행동을 고객 언어 라벨로 (04 §5-2)."""
    st.markdown(f"**이번 행동** — {event.get('action', '?').upper()}")
    shown = False
    for entry in event.get("trace", []):
        if entry.get("kind") != "route":
            continue
        for key, label in NOTE_LABELS.items():
            if key in entry.get("detail", {}):
                st.markdown(f"- {label}: `{entry['detail'][key]}`")
                shown = True
    if not shown:
        st.caption("이번 턴에 기록된 탐색 노트가 없어요.")
    with st.expander("원본 trace 보기"):
        st.json(event.get("trace", []))


def _retrieval_tab(event: dict):
    """검색 근거 — 필터 통과/제외 건수, 벡터 사용 여부 (04 §5-2)."""
    shown = False
    for entry in event.get("trace", []):
        detail = entry.get("detail", {})
        if entry.get("kind") == "tool" and entry["detail"].get("tool") == "search_funds":
            if "alias_matched" in detail:
                st.markdown(f"- 조건 매칭: **{detail['alias_matched']}건**")
            if "passed_filter" in detail:
                st.markdown(f"- 정형 필터 통과: **{detail['passed_filter']}건**")
            if "excluded_by_risk" in detail:
                st.markdown(f"- 성향 범위 초과 제외: **{detail['excluded_by_risk']}건**")
            if detail.get("sort"):
                st.markdown(f"- 정렬: {detail['sort']}")
            if detail.get("selected_codes"):
                st.markdown(f"- 채택: `{'`, `'.join(detail['selected_codes'])}`")
            shown = True
        if entry.get("kind") == "retrieval":
            st.info(entry.get("summary", ""))
            shown = True
    if not shown:
        st.caption("이번 턴에는 검색이 실행되지 않았어요.")


def _tools_tab(event: dict):
    """도구 실행 — 도구명 / 입력 요약 / 결과 요약 (04 §5-2)."""
    tools = [e for e in event.get("trace", []) if e.get("kind") == "tool"]
    if not tools:
        st.caption("이번 턴에 실행된 도구가 없어요.")
        return
    for entry in tools:
        detail = entry.get("detail", {})
        st.markdown(f"**🔧 {detail.get('tool', '도구')}**")
        if detail.get("input_summary") is not None:
            st.caption("입력 요약")
            st.json(detail["input_summary"])
        rest = {k: v for k, v in detail.items() if k not in ("tool", "input_summary")}
        if rest:
            st.caption("결과 요약")
            st.json(rest)


def _safety_tab(event: dict):
    """안전 점검 — postprocess 체크리스트 (04 §5-2)."""
    safety = [e for e in event.get("trace", []) if e.get("kind") == "safety"]
    if not safety:
        st.caption("이번 턴의 안전 점검 기록이 없어요.")
        return
    for entry in safety:
        d = entry.get("detail", {})
        lines = []
        replaced = d.get("banned_replaced", 0)
        lines.append(
            f"✅ 금칙 표현 검사 (치환 {replaced}건)" if not replaced
            else f"⚠ 금칙 표현 {replaced}건 치환"
        )
        mismatch = d.get("numeric_mismatch", 0)
        lines.append(
            f"✅ 수치 대조 (불일치 {mismatch}건)" if not mismatch
            else f"⚠ 수치 불일치 {mismatch}건 치환"
        )
        if d.get("disclosure_inserted"):
            lines.append("✅ 고지 문구 삽입")
        excluded = d.get("excluded_by_risk", 0)
        if excluded or d.get("blocked"):
            lines.append(f"⚠ 성향 초과 상품 {excluded}건 노출 차단")
        for line in lines:
            st.markdown(line)
        extras = {k: v for k, v in d.items() if k not in (
            "banned_replaced", "numeric_mismatch", "disclosure_inserted",
            "excluded_by_risk", "blocked",
        )}
        for value in extras.values():
            st.caption(f"· {value}")


def render_trace_panel(agent_mode: str, trace_events: list):
    """trace 컬럼 전체 렌더링 (04 §5-1 구성: 배지 → 현재 행동 → 흐름 → 탭 4개)."""
    st.markdown(
        f"<div style='margin-top:12px'>{mode_badge_html(agent_mode)}</div>",
        unsafe_allow_html=True,
    )

    if not trace_events:
        st.caption("아직 실행된 턴이 없어요. 시연 코스를 실행해 보세요.")
        return

    # 턴 선택 (기본: 최근 턴)
    if len(trace_events) > 1:
        options = list(range(len(trace_events)))
        idx = st.selectbox(
            "턴 선택", options, index=len(options) - 1,
            format_func=lambda i: f"턴 {i + 1} · {trace_events[i]['user_message'][:18]}",
            label_visibility="collapsed",
        )
    else:
        idx = 0
    event = trace_events[idx]

    st.markdown(
        f'<div class="tp-action"><b>{event.get("action", "?").upper()}</b>'
        f' — {event.get("action_reason", "")}</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="tp-title">실행 흐름</div>', unsafe_allow_html=True)
    _flow_section(event.get("trace", []))

    tab_notes, tab_retrieval, tab_tools, tab_safety = st.tabs(
        ["탐색 노트", "검색 근거", "도구 실행", "안전 점검"]
    )
    with tab_notes:
        _notes_tab(event)
    with tab_retrieval:
        _retrieval_tab(event)
    with tab_tools:
        _tools_tab(event)
    with tab_safety:
        _safety_tab(event)
