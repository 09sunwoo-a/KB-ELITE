"""A1 게이트 심화 검증 — 임베딩 무결성·품질·검색 품질 수동 평가 스크립트.

실행: .venv/bin/python tests/eval_search_quality.py
pytest가 아닌 눈 확인용 리포트. 검색 튜닝 시 재사용.
"""

import json

import numpy as np
from dotenv import load_dotenv

load_dotenv()

FUNDS = json.load(open("data/funds.json", encoding="utf-8"))
CONTENTS = [json.loads(l) for l in open("data/contents.jsonl", encoding="utf-8")]
EMB = np.load("data/embeddings.npy")
CODES = [r["product_code"] for r in CONTENTS]


def integrity():
    print("=== 1. 무결성 ===")
    assert len(FUNDS) == len(CONTENTS) == EMB.shape[0] == 311
    assert EMB.shape[1] == 1536 and EMB.dtype == np.float32
    assert not np.isnan(EMB).any(), "NaN 벡터 존재"
    assert set(CODES) == set(FUNDS.keys()), "jsonl 코드와 funds.json 키 불일치"
    norms = np.linalg.norm(EMB, axis=1)
    print(f"  건수 정합 311/311, 차원 1536, NaN 없음, 코드 집합 일치")
    print(f"  벡터 norm: min={norms.min():.4f} max={norms.max():.4f} (1.0이면 정규화됨)")
    dup = 311 - len({tuple(np.round(v, 5)) for v in EMB[:, :8]})
    print(f"  선두 8차원 기준 중복 의심 벡터: {dup}건")


def neighbors(code, k=4):
    i = CODES.index(code)
    sims = EMB @ EMB[i]
    order = np.argsort(-sims)
    f = FUNDS[code]
    print(f"\n  기준: {f['name']} [{f['region']}/{f['fund_type']}/{f['risk_grade']}]")
    for j in order[1:k + 1]:
        g = FUNDS[CODES[j]]
        print(f"    {sims[j]:.3f}  {g['name'][:38]} [{g['region']}/{g['fund_type']}]")


def embedding_quality():
    print("\n=== 2. 임베딩 품질 — 최근접 이웃이 같은 부류인가 ===")
    neighbors("KF04001379")  # 미국 주식형 (피델리티)
    neighbors("KF04000398")  # 국내 MMF
    tdf = next(c for c, f in FUNDS.items() if f["tags"]["tdf"])
    neighbors(tdf)           # TDF

    # 분리도: 같은 부류 평균 유사도 vs 다른 부류
    us_eq = [CODES.index(c) for c, f in FUNDS.items()
             if f["region"] == "미국" and f["fund_type"] == "주식형"]
    dom_bond = [CODES.index(c) for c, f in FUNDS.items()
                if f["region"] == "국내" and f["fund_type"] == "채권형"]
    within = np.mean([EMB[a] @ EMB[b] for a in us_eq[:15] for b in us_eq[:15] if a != b])
    across = np.mean([EMB[a] @ EMB[b] for a in us_eq[:15] for b in dom_bond[:15]])
    print(f"\n  미국주식 내부 평균 유사도 {within:.3f} vs 미국주식↔국내채권 {across:.3f}"
          f"  → 차이 {within - across:+.3f} (양수 클수록 좋음)")


def search(query, k=5, max_risk=None):
    from langchain_openai import OpenAIEmbeddings
    qv = np.array(OpenAIEmbeddings(model="text-embedding-3-small").embed_query(query))
    qv /= np.linalg.norm(qv)
    sims = EMB @ qv
    order = np.argsort(-sims)
    out, excluded = [], 0
    for j in order:
        f = FUNDS[CODES[j]]
        if max_risk is not None and f["risk_score"] > max_risk:
            excluded += 1
            continue
        out.append((float(sims[j]), CODES[j], f))
        if len(out) == k:
            break
    return out, excluded


def judge(f, crit):
    checks = {
        "nvda": lambda f: "엔비디아" in f["matched_aliases"],
        "tdf": lambda f: f["tags"]["tdf"],
        "income": lambda f: f["tags"]["income"],
        "low_risk": lambda f: f["risk_score"] <= 3,
        "us": lambda f: f["region"] == "미국",
        "china": lambda f: f["region"] == "중국",
        "cheap": lambda f: f["fee_quartile"] <= 2,
    }
    return all(checks[c](f) for c in crit)


def search_quality():
    print("\n=== 3. 검색 품질 — 고객언어 질의 top-5 ===")
    cases = [
        ("엔비디아 들어간 펀드 찾아줘", ["nvda"], None),
        ("노후 대비로 은퇴 시점에 맞춰 알아서 조정되는 펀드", ["tdf"], None),
        ("매달 분배금 나오는 상품", ["income"], None),
        ("안정적이고 가격 변동이 작은 펀드", ["low_risk"], None),
        ("수수료 싼 미국 펀드", ["us", "cheap"], None),
        ("중국 기술주에 투자하는 펀드", ["china"], None),
    ]
    total_hit = total = 0
    for query, crit, max_risk in cases:
        results, _ = search(query, 5, max_risk)
        hits = sum(judge(f, crit) for _, _, f in results)
        total_hit += hits
        total += 5
        print(f"\n  Q: “{query}”  → 적합 {hits}/5 (기준: {'+'.join(crit)})")
        for sim, code, f in results:
            mark = "○" if judge(f, crit) else "✗"
            print(f"    {mark} {sim:.3f} {f['name'][:36]} "
                  f"[{f['region']}/{f['fund_type']}/{f['risk_grade']}"
                  f"{'/월지급' if f['tags']['income'] else ''}"
                  f"{'/TDF' if f['tags']['tdf'] else ''}]")
    print(f"\n  ▶ 벡터 단독 정확도 P@5: {total_hit}/{total} ({100 * total_hit / total:.0f}%)")

    print("\n=== 4. 하드 필터 결합 — 정미숙(안정형, 상한 2) ===")
    results, excluded = search("매달 분배금 나오는 상품", 5, max_risk=2)
    print(f"  성향 초과 제외: {excluded}건 통과 후 top-{len(results)}:")
    for sim, code, f in results:
        ok = f["risk_score"] <= 2
        print(f"    {'○' if ok else '✗'} {sim:.3f} {f['name'][:36]} "
              f"[{f['risk_grade']}{'/월지급' if f['tags']['income'] else ''}]")
    assert all(f["risk_score"] <= 2 for _, _, f in results), "하드 필터 위반!"
    print("  ▶ 노출 상한 위반 0건 (하드 필터 정상)")


if __name__ == "__main__":
    integrity()
    embedding_quality()
    search_quality()
