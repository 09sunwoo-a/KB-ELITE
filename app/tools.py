"""도구 3종 — 02 §6. LLM이 아니라 행동 노드의 코드가 직접 호출한다.

- search_funds:     01 4-2 하드 필터 → 정형 조건 필터 → 랭킹(비용 정렬 or 벡터)
- calc_annual_cost: 01 4-6 비용 원 단위 환산 (반환 문자열을 그대로 응답에 삽입)
- match_overlap:    01 4-6 겹침 분석 (종목명 리스트만, 비중 계산 없음)
"""

from __future__ import annotations

import re

import numpy as np

from app import store

AS_OF = "2026-06-30"

# 데이터의 투자국가 값 집합 — region_theme가 지역인지 테마인지 구분용
_REGIONS = None

_embedder = None


def _embed_query(text: str) -> np.ndarray:
    global _embedder
    if _embedder is None:
        from dotenv import load_dotenv
        load_dotenv()
        from langchain_openai import OpenAIEmbeddings
        _embedder = OpenAIEmbeddings(model="text-embedding-3-small")
    v = np.array(_embedder.embed_query(text))
    return v / np.linalg.norm(v)


def _regions() -> set:
    global _REGIONS
    if _REGIONS is None:
        _REGIONS = {f["region"] for f in store.funds().values() if f["region"]}
    return _REGIONS


def _resolve_alias_key(word: str) -> str | None:
    """고객 표기(예: '엔비디아', 'NVDA')를 alias 사전의 키로 정규화."""
    if not word:
        return None
    w = word.strip().upper()
    for key, patterns in store.alias_map().items():
        if w == key.upper() or any(w == p.upper() for p in patterns):
            return key
    return None


def _resolve_stock_list(text: str | None) -> list[str]:
    """'테슬라랑 엔비디아', '테슬라, 엔비디아' 같은 복수 종목 표기를 alias 키 목록으로."""
    if not text:
        return []
    whole = _resolve_alias_key(text)
    if whole:
        return [whole]
    keys = []
    for tok in re.split(r"[,·/&]|\s+", text):
        tok = re.sub(r"(이랑|랑|하고|와|과|도)$", "", tok.strip())
        key = _resolve_alias_key(tok)
        if key and key not in keys:
            keys.append(key)
    return keys


def _fund_text(f: dict) -> str:
    return " ".join(filter(None, [f["name"], f["one_liner"], f["features"]]))


def _theme_match(theme: str, f: dict) -> bool:
    """테마 키워드 매칭. 영문 키워드는 단어 경계 필수(예: 'AI'가 'sustainable'에 걸리지 않게)."""
    text = _fund_text(f)
    if re.fullmatch(r"[A-Za-z0-9&+\- ]+", theme):
        pat = r"(?<![A-Za-z])" + re.escape(theme) + r"(?![A-Za-z])"
        return re.search(pat, text, re.IGNORECASE) is not None
    return theme.upper() in text.upper()


def _make_card(code: str, f: dict, reasons: list[str], target_stocks: list[str]) -> dict:
    """04 §6-3 후보 카드 — funds.json 필드만 사용, selection_reason은 코드 생성."""
    matched = [s for s in target_stocks if s in f["matched_aliases"]] \
        or f["matched_aliases"][:3]
    m12 = f["returns"]["m12"]
    return {
        "fund_code": code,
        "name": f["name"],
        "fund_type": f["fund_type"],
        "region": f["region"],
        "risk_grade": f["risk_grade"],
        "fee_pct": f["fee_pct"],
        "manager": f["manager"],
        "matched_stocks": matched,
        "top_stocks_summary": (", ".join(f["matched_aliases"]) or None)
                              if f["has_holdings_info"] else None,
        # 04 §6-3 (2026-07-18): 기본 12개월 수익률 표시, 기준기간·기준일 병기
        "returns_display": {"period": "12개월", "value": m12} if m12 is not None else None,
        "selection_reason": ", ".join(reasons) if reasons else "탐색 조건과의 관련성 순",
        "as_of": f["as_of"],
    }


def search_funds(conditions: dict, max_risk_score: int, query_text: str, k: int = 3) -> dict:
    """반환: {candidates, excluded_by_risk, blocked, pool_size, ranking_mode, applied}"""
    funds = store.funds()
    target_stocks = _resolve_stock_list(conditions.get("target_stock"))
    # alias로 풀리지 않는 종목(예: 비트코인)은 조용히 버리지 않고 테마 키워드로 취급 —
    # 데이터에 없으면 0건으로 정직하게 떨어진다
    unresolved_stock = conditions.get("target_stock") if (
        conditions.get("target_stock") and not target_stocks) else None
    region_theme = conditions.get("region_theme")
    fund_type_hint = conditions.get("fund_type_hint") or ""
    cost_sensitive = bool(conditions.get("cost_sensitive"))

    region = region_theme if region_theme in _regions() else None
    theme_kw = None if (region or not region_theme) else region_theme
    want_income = bool(re.search(r"월지급|인컴|배당|분배", fund_type_hint))
    want_tdf = "TDF" in fund_type_hint.upper() or (theme_kw or "").upper() == "TDF"
    want_pension = bool(re.search(r"연금|IRP|적격", fund_type_hint)) \
        or bool(re.search(r"연금|IRP", theme_kw or ""))
    direct_type = fund_type_hint if fund_type_hint in \
        {f["fund_type"] for f in funds.values()} else None

    applied = [x for x, on in [
        (f"종목: {', '.join(target_stocks)}", target_stocks),
        (f"종목(별칭 미등록, 키워드 검색): {unresolved_stock}", unresolved_stock),
        (f"지역: {region}", region),
        (f"테마: {theme_kw}", theme_kw and not want_tdf and not want_pension),
        ("월지급·인컴", want_income), ("TDF", want_tdf), ("연금 적격", want_pension),
        (f"유형: {direct_type}", direct_type), ("비용 낮은 순", cost_sensitive)] if on]

    pool, excluded_by_risk = [], 0
    for code, f in funds.items():
        if target_stocks and not all(s in f["matched_aliases"] for s in target_stocks):
            continue
        if unresolved_stock and not _theme_match(unresolved_stock, f) \
                and unresolved_stock.upper() not in (f["stocks_raw"] or "").upper():
            continue
        if region and f["region"] != region:
            continue
        if theme_kw and not want_tdf and not want_pension \
                and not _theme_match(theme_kw, f):
            continue
        if want_income and not f["tags"]["income"]:
            continue
        if want_tdf and not f["tags"]["tdf"]:
            continue
        if want_pension and not f["tags"]["pension_eligible"]:
            continue
        if direct_type and f["fund_type"] != direct_type:
            continue
        if f["risk_score"] > max_risk_score:   # 01 4-2 하드 필터 — 예외 없음
            excluded_by_risk += 1
            continue
        pool.append(code)

    blocked = (len(pool) == 0 and excluded_by_risk > 0)

    if cost_sensitive:
        ranked = sorted(pool, key=lambda c: funds[c]["fee_pct"])
        ranking_mode = "연간 비용 낮은 순 (정형 정렬)"
    elif query_text and len(pool) > k:
        qv = _embed_query(query_text)
        emb, idx = store.embeddings(), store.code_index()
        ranked = sorted(pool, key=lambda c: -(emb[idx[c]] @ qv))
        ranking_mode = "조건 일치 상품 내 의미 유사도 순 (벡터)"
    else:
        ranked = sorted(pool, key=lambda c: funds[c]["fee_pct"])
        ranking_mode = "조건 일치 상품 (비용 순 표시)"

    candidates = []
    for rank, code in enumerate(ranked[:k]):
        f = funds[code]
        reasons = []
        if target_stocks:
            reasons.append(f"{', '.join(target_stocks)}를 주요 종목으로 담고 있음")
        if want_tdf and f["tags"]["tdf_vintage"]:
            reasons.append(f"목표 시점 {f['tags']['tdf_vintage']}년 상품")
        if want_pension:
            reasons.append("연금계좌에 담을 수 있는 적격 상품")
        if want_income:
            reasons.append("분배금을 지급하는 구조")
        if cost_sensitive and rank == 0:
            reasons.append("후보 중 연간 비용이 가장 낮음")
        elif f["fee_quartile"] == 1:
            reasons.append("전체 상품 중 연간 비용이 낮은 편")
        if f["risk_score"] <= 2:
            reasons.append("가격 변동이 상대적으로 작은 편")
        candidates.append(_make_card(code, f, reasons, target_stocks))

    return {"candidates": candidates, "excluded_by_risk": excluded_by_risk,
            "blocked": blocked, "pool_size": len(pool),
            "ranking_mode": ranking_mode, "applied": applied}


def calc_annual_cost(fee_pct: float, amount: int, contribution_type: str) -> str:
    """01 4-6 비용 환산. 반환 문자열을 응답에 그대로 삽입한다 (LLM 재서술 금지, 03 §6)."""
    if contribution_type == "monthly":
        avg_balance = amount * 6.5          # 첫해 예상 평균잔액 근사 (매달 납입 누적)
        cost = avg_balance * fee_pct / 100
        base = (f"매달 {amount:,}원씩 납입한다고 단순 가정하면, 첫해 예상 비용은 "
                f"평균잔액(약 {round(avg_balance):,}원) 기준 연 약 {round(cost, -2):,.0f}원 수준이에요.")
    else:
        cost = amount * fee_pct / 100
        base = (f"{amount:,}원을 운용한다고 단순 가정하면, 연간 비용은 "
                f"약 {round(cost, -2):,.0f}원 수준이에요.")
    return base + " 실제 비용은 납입일과 기준가격에 따라 달라질 수 있어요."


def match_overlap(holdings: list[dict], fund_code: str) -> dict:
    """01 4-6 겹침 분석 — alias 정규화 후 종목명 리스트만 반환. 비중 계산 없음."""
    funds = store.funds()
    f = funds.get(fund_code)
    if f is None:
        return {"available": False, "reason": "fund_not_found", "fund_code": fund_code}
    if not f["has_holdings_info"]:
        return {"available": False, "reason": "no_holdings_info",
                "fund_code": fund_code, "fund_name": f["name"]}

    customer_names = []
    for h in holdings:
        if h["kind"] == "stock":
            customer_names.append(h["name"])
        elif h["kind"] == "fund":
            customer_names.extend(t["name"] for t in h.get("top_holdings", []))

    fund_stocks_upper = f["stocks_raw"].upper()
    overlap, checked = [], []
    for name in dict.fromkeys(customer_names):   # 중복 제거, 순서 유지
        key = _resolve_alias_key(name)
        checked.append(name)
        patterns = store.alias_map().get(key, [name]) if key else [name]
        if any(p.upper() in fund_stocks_upper for p in patterns):
            overlap.append(key or name)

    return {
        "available": True,
        "fund_code": fund_code,
        "fund_name": f["name"],
        "overlap_stocks": overlap,
        "checked_holdings": checked,
        "basis": "공개된 상위 보유종목 기준",
        "as_of": f["as_of"],
        "note": "종목별 편입 비중과 전체 포트폴리오 중복률은 공개 데이터에 없어 계산하지 않습니다.",
    }
