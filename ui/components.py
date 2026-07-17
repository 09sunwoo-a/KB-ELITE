# -*- coding: utf-8 -*-
"""결과 컴포넌트 — 후보 카드·비교표·겹침·차단 박스·조건 칩바 (04 §4).

원칙(04 §1-4, 03 장치 ①): 모든 수치는 AgentTurnResult에 담긴 funds.json 유래
값을 코드가 그대로 조립해 표시한다. LLM 서술(answer)은 말풍선이 담당한다.
종목 편입 비중·중복률 등 데이터에 없는 수치는 어떤 컴포넌트도 만들지 않는다.
"""
import html as html_mod

import streamlit as st

CIRCLED = "①②③④⑤⑥⑦⑧⑨"

# 조건 키 → 고객 언어 라벨 (04 §4-2)
COND_LABELS = {
    "target_stock": lambda v: f"관심 종목: {v}",
    "cost_sensitive": lambda v: "비용: 낮은 편" if v else None,
    "region_theme": lambda v: f"테마·지역: {v}",
    "horizon": lambda v: f"기간: {v}",
    "fund_type_hint": lambda v: f"유형: {v}",
}


def _esc(value) -> str:
    return html_mod.escape(str(value))


def render_condition_bar(conditions: dict):
    """현재 탐색 기준 칩바 — 조건이 없으면 내용은 숨기되 자리는 유지(규격 고정)."""
    chips = []
    for key, value in (conditions or {}).items():
        fmt = COND_LABELS.get(key)
        label = fmt(value) if fmt else f"{key}: {value}"
        if label:
            chips.append(f'<span class="cond-chip">{_esc(label)}</span>')
    empty = "" if chips else " empty"
    st.markdown(
        f'<div class="cond-bar{empty}"><span class="cond-title">현재 탐색 기준</span>{"".join(chips)}</div>',
        unsafe_allow_html=True,
    )


def render_candidates(candidates: list):
    """후보 카드 2~4개 (04 §4-4). 수치는 전부 funds.json 유래 값."""
    for i, card in enumerate(candidates):
        no = CIRCLED[i] if i < len(CIRCLED) else str(i + 1)
        tags = [
            f'<span class="fc-tag">{_esc(card["fund_type"])}</span>',
            f'<span class="fc-tag risk">{_esc(card["risk_grade"])}</span>',
        ]
        for stock in card.get("matched_stocks") or []:
            tags.append(f'<span class="fc-tag match">{_esc(stock)} 포함 ✓</span>')

        rows = []
        if card.get("manager"):
            rows.append(
                f'<div class="fc-row"><span class="k">운용사</span>'
                f'<span class="v">{_esc(card["manager"])}</span></div>'
            )
        rows.append(
            f'<div class="fc-row"><span class="k">지역</span><span class="v">{_esc(card["region"])}</span></div>'
        )
        rows.append(
            f'<div class="fc-row"><span class="k">연간 비용</span>'
            f'<span class="v"><b>{card["fee_pct"]:.2f}%</b></span></div>'
        )
        rd = card.get("returns_display")
        if rd:
            rows.append(
                f'<div class="fc-row"><span class="k">{_esc(rd["period"])} 수익률</span>'
                f'<span class="v">{rd["value"]:.2f}% <span class="fc-dim">({_esc(card["as_of"])} 기준)</span></span></div>'
            )
        stocks = card.get("top_stocks_summary")
        rows.append(
            f'<div class="fc-row"><span class="k">주요 보유종목</span>'
            f'<span class="v">{_esc(stocks) if stocks else "정보가 공개되지 않은 상품"}</span></div>'
        )
        reason = card.get("selection_reason")
        if reason:
            rows.append(
                f'<div class="fc-row"><span class="k">선정 근거</span>'
                f'<span class="v">{_esc(reason)}</span></div>'
            )

        st.markdown(
            f"""
            <div class="fund-card">
              <div class="fc-name">{no} {_esc(card["name"])}</div>
              <div class="fc-tags">{"".join(tags)}</div>
              {"".join(rows)}
              <div class="fc-foot">기준일 {_esc(card["as_of"])}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_comparison(comparison: dict):
    """비교표 (04 §4-5). 차이 서술은 answer 말풍선이 담당한다."""
    if not comparison or not comparison.get("rows"):
        return
    body = []
    for row in comparison["rows"]:
        values = "".join(f"<td>{_esc(v)}</td>" for v in row["values"])
        body.append(f'<tr><td class="lbl">{_esc(row["label"])}</td>{values}</tr>')
    st.markdown(
        f'<div class="cmp-wrap"><table><tbody>{"".join(body)}</tbody></table></div>',
        unsafe_allow_html=True,
    )


def render_overlap(overlap: dict):
    """겹침 분석 (04 §4-6) — 종목명 리스트만. 비중 막대·중복률 % 금지(데이터 없음)."""
    if not overlap:
        return
    if not overlap.get("available"):
        st.markdown(
            '<div class="overlap-box">이 상품은 보유종목 정보가 공개되지 않아 '
            "비교할 수 없어요.</div>",
            unsafe_allow_html=True,
        )
        return
    stocks = "".join(
        f'<span class="ov-stock">{_esc(s)} ✓</span>' for s in overlap.get("overlap_stocks", [])
    ) or '<span class="ov-none">겹치는 종목 없음</span>'
    note = overlap.get("note")
    note_html = f'<div class="ov-note">※ {_esc(note)}</div>' if note else ""
    st.markdown(
        f"""
        <div class="overlap-box">
          <div class="ov-title">겹침 확인 — {_esc(overlap["fund_name"])}</div>
          <div class="ov-sub">공개된 상위 보유종목 기준 (기준일 {_esc(overlap["as_of"])})</div>
          <div class="ov-stocks">{stocks}</div>
          {note_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_risk_block(risk_block: dict):
    """전부 차단 안내 박스 (04 §4-7). 대안 버튼 2개는 후속 칩이 담당한다."""
    n = risk_block.get("excluded_by_risk", 0)
    st.markdown(
        f"""
        <div class="block-box">
          <b>⚠ 투자성향 범위 초과 안내</b><br>
          조회된 상품 {n}건이 모두 고객님의 가입 가능 위험등급 범위를 넘어서,
          이 화면에서는 후보로 노출되지 않았어요. 가입 가능 범위는 투자성향
          재진단에 따라 달라질 수 있어요.
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_result(result: dict):
    """AgentTurnResult의 구조화 결과를 answer 말풍선 아래에 렌더링한다."""
    if not result:
        return
    risk_block = result.get("risk_block")

    if result.get("candidates"):
        render_candidates(result["candidates"])
        if risk_block and risk_block.get("excluded_by_risk", 0) > 0 and not risk_block.get("blocked"):
            st.markdown(
                f'<div class="excl-note">조건에 맞는 상품 중 {risk_block["excluded_by_risk"]}건은 '
                "투자성향 범위를 초과해 제외했어요</div>",
                unsafe_allow_html=True,
            )
    if result.get("comparison"):
        render_comparison(result["comparison"])
    if result.get("overlap"):
        render_overlap(result["overlap"])
    if risk_block and risk_block.get("blocked"):
        render_risk_block(risk_block)
