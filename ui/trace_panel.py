# -*- coding: utf-8 -*-
"""Trace 패널 — `Agent 동작 보기` (04 §5).

trace 노출 금지(04 §1-5): 모델 CoT, 시스템 프롬프트 원문, API Key,
고객 식별자 원문, 임베딩 벡터, RAG CONTENT 원문 전체. 이 패널은
TraceEntry의 summary/detail(노출 가능 데이터만 담김)만 렌더링한다.

detail 형식은 app/graph.py가 남기는 실제 trace와 동일하다 (Mock fixture도 정렬).
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


def _flow_section(trace: list):
    """실행 흐름 — 노드 진행 + 도구 호출 들여쓰기 (04 §5-1)."""
    lines = []
    seen = []
    for entry in trace:
        node = entry.get("node")
        if node not in seen:
            seen.append(node)
            lines.append(f'<div class="tp-node">✓ {NODE_LABELS.get(node, node)}</div>')
        if entry.get("kind") == "tool":
            lines.append(f'<div class="tp-tool">└ 🔧 {entry.get("summary", "")}</div>')
    st.markdown("".join(lines), unsafe_allow_html=True)


def _notes_tab(event: dict):
    """탐색 노트 — 라우터 추출·오버라이드·누적 조건 (04 §5-2)."""
    st.markdown(f"**이번 행동** — {event.get('action', '?').upper()}")
    shown = False
    for entry in event.get("trace", []):
        if entry.get("kind") != "route":
            continue
        detail = entry.get("detail", {})
        if detail.get("extracted"):
            st.markdown(f"- 이번 발화에서 추출: `{detail['extracted']}`")
            shown = True
        if detail.get("conditions"):
            st.markdown(f"- 누적 탐색 기준: `{detail['conditions']}`")
            shown = True
        for ov in detail.get("overrides") or []:
            st.markdown(f"- 규칙 오버라이드: {ov}")
            shown = True
    for entry in event.get("trace", []):
        if entry.get("node") == "ask" and entry.get("kind") == "info":
            st.markdown(f"- {entry.get('summary', '')}")
            shown = True
    if not shown:
        st.caption("이번 턴에 기록된 탐색 노트가 없어요.")
    with st.expander("원본 trace 보기"):
        st.json(event.get("trace", []))


def _retrieval_tab(event: dict):
    """검색 근거 — 적용 조건, 랭킹 방식(벡터 사용 여부), 제외 건수 (04 §5-2)."""
    shown = False
    for entry in event.get("trace", []):
        if entry.get("node") != "search" or entry.get("kind") != "tool":
            continue
        detail = entry.get("detail", {})
        st.markdown(f"**{entry.get('summary', '')}**")
        if detail.get("applied"):
            st.markdown("- 적용 조건: " + " · ".join(detail["applied"]))
        ranking = detail.get("ranking_mode", "")
        if ranking:
            if "벡터" in ranking:
                st.info(f"벡터 검색 사용 — {ranking}")
            else:
                st.info(f"벡터 검색 미사용 — 정형 필터+정렬로 종결 ({ranking})")
        if detail.get("excluded_by_risk"):
            st.markdown(f"- 성향 범위 초과 제외: **{detail['excluded_by_risk']}건**"
                        + (" → **전부 차단**" if detail.get("blocked") else ""))
        if detail.get("codes"):
            st.markdown(f"- 채택: `{'`, `'.join(detail['codes'])}`")
        shown = True
    if not shown:
        st.caption("이번 턴에는 검색이 실행되지 않았어요.")


def _tools_tab(event: dict):
    """도구 실행 — 도구 요약 + 민감정보 없는 입력·결과 detail (04 §5-2)."""
    tools = [e for e in event.get("trace", []) if e.get("kind") == "tool"]
    if not tools:
        st.caption("이번 턴에 실행된 도구가 없어요.")
        return
    for entry in tools:
        st.markdown(f"**🔧 {entry.get('summary', '')}**")
        if entry.get("detail"):
            st.json(entry["detail"], expanded=False)


def _safety_tab(event: dict):
    """안전 점검 — postprocess 체크리스트 (04 §5-2)."""
    safety = [e for e in event.get("trace", []) if e.get("kind") == "safety"]
    if not safety:
        st.caption("이번 턴의 안전 점검 기록이 없어요.")
        return
    # 성향 초과 건수는 search trace에서 가져온다
    excluded, blocked = 0, False
    for entry in event.get("trace", []):
        detail = entry.get("detail", {})
        if entry.get("node") == "search" and "excluded_by_risk" in detail:
            excluded = detail.get("excluded_by_risk") or 0
            blocked = bool(detail.get("blocked"))
    for entry in safety:
        d = entry.get("detail", {})
        banned, numeric = d.get("banned", []), d.get("numeric", [])
        st.markdown(f"✅ 금칙 표현 검사 (치환 {len(banned)}건)" if not banned
                    else f"⚠ 금칙 표현 {len(banned)}건 치환")
        for b in banned:
            st.caption(f"· {b}")
        st.markdown(f"✅ 수치 대조 (교정 {len(numeric)}건)" if not numeric
                    else f"⚠ 수치 {len(numeric)}건 교정")
        for n in numeric:
            st.caption(f"· {n}")
        if d.get("disclosures"):
            st.markdown(f"✅ 고지 문구 삽입 ({len(d['disclosures'])}건)")
        if "blocked" in (d.get("notices") or []) or blocked:
            st.markdown(f"⚠ 성향 초과 상품 {excluded}건 전부 노출 차단 — 차단 안내 삽입")
        elif "excluded" in (d.get("notices") or []) or excluded:
            st.markdown(f"⚠ 성향 초과 상품 {excluded}건 노출 차단")


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
