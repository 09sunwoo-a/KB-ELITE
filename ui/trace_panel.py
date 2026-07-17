# -*- coding: utf-8 -*-
"""Trace 패널 — `Agent 동작 보기` (04 §5).

trace 노출 금지(04 §1-5): 모델 CoT, 시스템 프롬프트 원문, API Key,
고객 식별자 원문, 임베딩 벡터, RAG CONTENT 원문 전체. 이 패널은
TraceEntry의 summary/detail(노출 가능 데이터만 담김)만 렌더링한다.

detail 형식은 app/graph.py가 남기는 실제 trace와 동일하다 (Mock fixture도 정렬).
"""
import html

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

# 라우터가 선택하는 분기 4노드 — 다이어그램 칸에 들어가는 축약 표시명 (04 §5-1)
_BRANCH_NODES = ["explain", "ask", "search", "compare"]
_BRANCH_SHORT = {"explain": "용어 설명", "ask": "확인 질문",
                 "search": "펀드 탐색", "compare": "후보 비교"}


def _graph_html(visited: list, current: str = None,
                error: bool = False, show_pending: bool = False) -> str:
    """고정 토폴로지 다이어그램 — router → 분기 4노드 → postprocess (04 §5-1).

    6노드를 항상 그려서 '라우터가 4가지 행동 중 하나를 선택했다'가 보이게 한다.
    visited: 이번 턴에 실행된 노드 / current: 진행 중 노드(점멸) /
    error: current를 ⚠ 처리 / show_pending: 시작 전 postprocess를 ○ 대기로 표시.
    """
    def box(node, label):
        if node == current:
            state, icon = ("err", "⚠ ") if error else ("run", "")
        elif node in visited:
            state, icon = "on", "✓ "
        elif show_pending and node == "postprocess":
            state, icon = "wait", "○ "
        else:
            state, icon = "off", ""
        return f'<div class="tpg-node {state}">{icon}{label}</div>'

    branch = "".join(box(n, _BRANCH_SHORT[n]) for n in _BRANCH_NODES)
    return (
        '<div class="tp-graph">'
        + box("router", NODE_LABELS["router"])
        + '<div class="tpg-conn"></div>'
        + f'<div class="tpg-branch">{branch}</div>'
        + '<div class="tpg-conn"></div>'
        + box("postprocess", NODE_LABELS["postprocess"])
        + "</div>"
    )


def render_trace_panel_live(agent_mode: str):
    """턴 실행 중 trace 컬럼 — 배지 + 실시간 실행 흐름 슬롯을 만들어 반환한다 (04 §5-1).

    턴이 끝나 rerun되면 render_trace_panel(사후 상세)로 자연히 대체된다.
    """
    st.markdown(
        f"<div style='margin-top:24px'>{mode_badge_html(agent_mode)}</div>",
        unsafe_allow_html=True,
    )
    st.markdown('<div class="tp-title">실행 흐름 — 실시간</div>', unsafe_allow_html=True)
    return st.empty()


def render_live_flow(slot, visited: list, state: str = "running"):
    """node_started 이벤트마다 호출 — 고정 토폴로지에서 진행 노드가 점멸한다 (04 §5-1).

    visited: 지금까지 시작된 노드 순서. 마지막 원소가 진행 중 노드.
    state: "running" | "done" | "error"
    """
    if slot is None:
        return
    current = visited[-1] if visited and state in ("running", "error") else None
    html = _graph_html(visited, current=current, error=(state == "error"),
                       show_pending=(state == "running"))
    if state == "running" and current:
        html += (f'<div class="tp-live-label"><span class="tp-live-dot"></span>'
                 f'{NODE_LABELS.get(current, current)} 중</div>')
    elif state == "error" and current:
        html += (f'<div class="tp-live-label err">⚠ '
                 f'{NODE_LABELS.get(current, current)} — 중단됨</div>')
    elif state == "done":
        html += '<div class="tp-live-done">모든 단계 완료 — 답변 표시 중</div>'
    slot.markdown(html, unsafe_allow_html=True)


def render_opening_live(slot):
    """오프닝 생성 중 — 고정 토폴로지 대신 개인화 진행 라벨 (02 §8, 04 §4-1)."""
    if slot is None:
        return
    slot.markdown(
        '<div class="tp-live-label"><span class="tp-live-dot"></span>'
        '고객 프로필 확인 · 첫인사 개인화 생성 중</div>',
        unsafe_allow_html=True,
    )


def _opening_section(event: dict):
    """오프닝 이벤트 — 그래프 턴이 아니므로 생성·검증 로그 리스트로 표시 (04 §4-1)."""
    st.markdown('<div class="tp-title">개인화 오프닝 — 생성·검증 로그</div>',
                unsafe_allow_html=True)
    for entry in event.get("trace", []):
        kind = entry.get("kind")
        if kind == "safety":
            icon = "✅" if (entry.get("detail") or {}).get("intro_source") == "llm" else "⚠"
        else:
            icon = {"info": "👤", "tool": "🔧"}.get(kind, "·")
        st.markdown(f"{icon} {entry.get('summary', '')}")
        if entry.get("detail"):
            st.json(entry["detail"], expanded=False)


def _flow_section(trace: list):
    """실행 흐름 — 고정 토폴로지에 이번 턴 경로 강조 + 도구 호출 목록 (04 §5-1)."""
    visited, tools = [], []
    for entry in trace:
        node = entry.get("node")
        if node not in visited:
            visited.append(node)
        if entry.get("kind") == "tool":
            tools.append(f'<div class="tp-tool">└ 🔧 {entry.get("summary", "")}</div>')
    st.markdown(_graph_html(visited) + "".join(tools), unsafe_allow_html=True)


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
        # 벡터 랭킹 턴 — 후보별 코사인 유사도 막대 (04 §5-2, 절대 스케일 0~1)
        scores = detail.get("scores") or {}
        if scores:
            rows = []
            for code in detail.get("codes") or scores.keys():
                s = scores.get(code)
                if s is None:
                    continue
                width = max(2.0, min(100.0, s * 100))
                rows.append(
                    f'<div class="tp-score-row"><span class="tp-score-code">{code}</span>'
                    f'<span class="tp-score-bar"><i style="width:{width:.1f}%"></i></span>'
                    f'<span class="tp-score-val">{s:.3f}</span></div>')
            if rows:
                st.markdown(
                    '<div class="tp-title">질의–상품 의미 유사도 (코사인, 0~1 절대 스케일)</div>'
                    + "".join(rows), unsafe_allow_html=True)
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
            _render_diff(b)
        st.markdown(f"✅ 수치 대조 (교정 {len(numeric)}건)" if not numeric
                    else f"⚠ 수치 {len(numeric)}건 교정")
        for n in numeric:
            _render_diff(n)
        if d.get("disclosures"):
            st.markdown(f"✅ 고지 문구 삽입 ({len(d['disclosures'])}건)")
        if "blocked" in (d.get("notices") or []) or blocked:
            st.markdown(f"⚠ 성향 초과 상품 {excluded}건 전부 노출 차단 — 차단 안내 삽입")
        elif "excluded" in (d.get("notices") or []) or excluded:
            st.markdown(f"⚠ 성향 초과 상품 {excluded}건 노출 차단")
        _chips_pipeline(d)


def _render_diff(item):
    """가드레일 개입 1건 — 원문→치환문 diff (04 §5-2). dict가 아니면 텍스트 폴백."""
    if not isinstance(item, dict):
        st.caption(f"· {item}")
        return
    found = html.escape(str(item.get("found", "")))
    replaced = html.escape(str(item.get("replaced", "") or "문장 치환"))
    cat = item.get("category") or ("수치 근거 없음" if "sentence" in item else "")
    cat_html = f'<span class="tp-diff-cat">{html.escape(cat)}</span>' if cat else ""
    st.markdown(
        f'<div class="tp-diff">{cat_html}<del>{found}</del>'
        f'<span class="tp-diff-arrow">→</span><ins>{replaced}</ins></div>',
        unsafe_allow_html=True,
    )


def _chips_pipeline(d: dict):
    """후속 칩 파이프라인 — LLM 생성→코드 검증→채택/폴백 경로 배지 (04 §5-2)."""
    src, drop = d.get("chips_source"), d.get("chips_drop_reason")
    if not src:
        return   # 구 형식 trace(fixture 등)에는 없음 — 조용히 생략
    if src == "llm":
        steps = [("LLM 칩 생성", "on"), ("코드 검증 통과", "on"), ("채택", "ok")]
    elif drop:
        steps = [("LLM 칩 생성", "on"), (f"검증 실패: {drop}", "fail"), ("규칙 칩 폴백", "ok")]
    else:
        steps = [("규칙 기반 칩", "ok"), ("질문·차단·0건 턴은 LLM 생성 없음", "note")]
    inner = '<span class="tp-pipe-arrow">→</span>'.join(
        f'<span class="tp-pipe-step {cls}">{html.escape(label)}</span>'
        for label, cls in steps if cls != "note"
    )
    note = next((label for label, cls in steps if cls == "note"), None)
    st.markdown(
        '<div class="tp-title" style="margin-top:8px">후속 칩 파이프라인</div>'
        f'<div class="tp-pipe">{inner}</div>'
        + (f'<div class="tp-pipe-note">{html.escape(note)}</div>' if note else ""),
        unsafe_allow_html=True,
    )


def render_trace_panel(agent_mode: str, trace_events: list):
    """trace 컬럼 전체 렌더링 (04 §5-1 구성: 배지 → 현재 행동 → 흐름 → 탭 4개)."""
    st.markdown(
        f"<div style='margin-top:24px'>{mode_badge_html(agent_mode)}</div>",
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

    # 오프닝 이벤트는 그래프 턴이 아니다 — 전용 로그 뷰로 종결 (04 §4-1)
    if event.get("action") == "opening":
        _opening_section(event)
        return

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
