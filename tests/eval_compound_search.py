"""복합조건 검색 검증 — 03 §9 검색 플로우(정형 필터 → 벡터/비용 랭킹) 프로토타입.

실행: .venv/bin/python tests/eval_compound_search.py
A3에서 구현할 app/tools.py search_funds의 사전 검증. 눈 확인용 리포트.
"""

import json

import numpy as np
from dotenv import load_dotenv

load_dotenv()

FUNDS = json.load(open("data/funds.json", encoding="utf-8"))
CONTENTS = [json.loads(l) for l in open("data/contents.jsonl", encoding="utf-8")]
EMB = np.load("data/embeddings.npy")
CODES = [r["product_code"] for r in CONTENTS]
IDX = {c: i for i, c in enumerate(CODES)}

_embedder = None


def embed_query(q):
    global _embedder
    if _embedder is None:
        from langchain_openai import OpenAIEmbeddings
        _embedder = OpenAIEmbeddings(model="text-embedding-3-small")
    v = np.array(_embedder.embed_query(q))
    return v / np.linalg.norm(v)


def search_funds_proto(max_risk, query_text=None, k=4, *, region=None, fund_type=None,
                       target_stock=None, tag=None, vintage_range=None,
                       cost_sensitive=False):
    """03 §9 플로우: ① 정형 필터 ② 차단 집계 ③ 랭킹(비용 정렬 or 벡터)."""
    pool, excluded_by_risk = [], 0
    for c, f in FUNDS.items():
        if region and f["region"] != region:
            continue
        if fund_type and f["fund_type"] != fund_type:
            continue
        if target_stock and target_stock not in f["matched_aliases"]:
            continue
        if tag and not f["tags"][tag]:
            continue
        if vintage_range and not (f["tags"]["tdf_vintage"]
                                  and vintage_range[0] <= f["tags"]["tdf_vintage"] <= vintage_range[1]):
            continue
        if f["risk_score"] > max_risk:          # 01 4-2 하드 필터 (예외 없음)
            excluded_by_risk += 1
            continue
        pool.append(c)

    blocked = (len(pool) == 0 and excluded_by_risk > 0)
    if cost_sensitive:
        ranked = sorted(pool, key=lambda c: FUNDS[c]["fee_pct"])
        mode = "비용 오름차순 (벡터 미사용)"
    elif query_text and pool:
        qv = embed_query(query_text)
        ranked = sorted(pool, key=lambda c: -(EMB[IDX[c]] @ qv))
        mode = "정형 필터 풀 내 벡터 랭킹"
    else:
        ranked = pool
        mode = "필터만"
    return ranked[:k], excluded_by_risk, blocked, len(pool), mode


def show(title, persona, **kwargs):
    top, excl, blocked, pool, mode = search_funds_proto(**kwargs)
    print(f"\n【{title}】 ({persona})")
    print(f"  풀 {pool}건 / 성향 초과 제외 {excl}건 / blocked={blocked} / 랭킹: {mode}")
    for c in top:
        f = FUNDS[c]
        extra = "/".join(filter(None, [
            "TDF" + str(f["tags"]["tdf_vintage"] or "") if f["tags"]["tdf"] else None,
            "월지급" if f["tags"]["income"] else None,
            "적격" if f["tags"]["pension_eligible"] else None,
            ",".join(f["matched_aliases"][:3]) if f["matched_aliases"] else None]))
        print(f"    · {f['name'][:42]}")
        print(f"      [{f['region']}/{f['fund_type']}/{f['risk_grade']}/fee {f['fee_pct']}%"
              f"{'/' + extra if extra else ''}]")


if __name__ == "__main__":
    print("=== 복합조건 검색 검증 (정형 필터 → 랭킹) ===")

    show("① 종목+비용: 엔비디아 편입 & 비용 낮은 순", "최준혁·적극투자형(≤5)",
         max_risk=5, target_stock="엔비디아", cost_sensitive=True)

    show("② 계좌+상품군+시점: 연금적격 TDF 2045~2055", "박서연·위험중립형(≤4)",
         max_risk=4, tag="pension_eligible", vintage_range=(2045, 2055),
         query_text="2050년쯤 은퇴 예정, 노후 준비")

    show("③ 지역+분배: 중국 & 월지급", "최준혁·적극투자형(≤5)",
         max_risk=5, region="중국", tag="income",
         query_text="중국에 투자하면서 배당도 받고 싶어")

    show("④ 지역+유형+뉘앙스: 국내 채권형 중 꾸준한 것", "정미숙·안정형(≤2)",
         max_risk=2, region="국내", fund_type="채권형",
         query_text="꾸준하고 안정적으로 이자처럼 쌓이는 상품")

    show("⑤ 순수 모호 질의 (필터 없음, 벡터가 주역)", "서지우·안정추구형(≤3)",
         max_risk=3,
         query_text="여유돈을 굴려보고 싶은데 반토막 나는 건 무섭고 은행 예금보단 나았으면")

    show("⑥ 충돌 케이스: 엔비디아 원하지만 성향이 안정형", "정미숙·안정형(≤2)",
         max_risk=2, target_stock="엔비디아")
    print("\n  → ⑥이 blocked=True면 '완전 차단 + 차단 안내' 시나리오(01 4-2 원칙 3) 성립")
