"""데이터 빌드 파이프라인 — 03_rag_data_design.md 구현.

펀드정보.xlsx → 정제 → 파생 필드 → funds.json / contents.jsonl / embeddings.npy
실행: .venv/bin/python build_data.py          (전체 빌드)
      SKIP_EMBED=1 .venv/bin/python build_data.py   (임베딩 생략 — 정제·검증만)
"""

import json
import os
import re
import sys
import unicodedata

import numpy as np
import pandas as pd

RAW_XLSX = "data/raw/펀드정보.xlsx"
FUNDS_JSON = "data/funds.json"
CONTENTS_JSONL = "data/contents.jsonl"
EMBEDDINGS_NPY = "data/embeddings.npy"
ALIAS_JSON = "data/alias.json"

AS_OF = "2026-06-30"  # 01 11-3: 기준일 컬럼 없음 → 전 상품 상수 가정
RISK_SCORE = {
    "매우낮은위험": 1, "낮은위험": 2, "보통위험": 3,
    "다소높은위험": 4, "높은위험": 5, "매우높은위험": 6,
}
PERSONA_CODES = ["KF04001379", "KF04000529", "KF04000398", "KF04001560"]


def norm_text(v):
    """전각 기호 정규화(NFKC) + 공백 정리. 결측은 None."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    s = unicodedata.normalize("NFKC", str(v)).strip()
    return s if s else None


def round_pct(v):
    if v is None or pd.isna(v):
        return None
    return round(float(v), 2)


def parse_share_class(name: str):
    m = re.search(r"(C-E|C-e|CE|Ce|C)(적)?\s*$", name)
    return (m.group(1) + (m.group(2) or "")) if m else None


def parse_tags(name: str, features: str, one_liner: str):
    up = name.upper()
    text = " ".join(filter(None, [name, features, one_liner]))
    tdf = "TDF" in up
    vintage = None
    if tdf:
        m = re.search(r"(20\d\d)", name)
        if m and 2015 <= int(m.group(1)) <= 2055:
            vintage = int(m.group(1))
    hedge = None
    if re.search(r"\(UH\)|UH\b", name):
        hedge = "UH"
    elif re.search(r"\(H\)", name):
        hedge = "H"
    return {
        "tdf": tdf,
        "tdf_vintage": vintage,
        "pension_eligible": "적격" in name,
        "hedge": hedge,
        "income": bool(re.search(r"인컴|배당|월지급", text)),
        "index_derivative": ("인덱스" in name and "파생" in name),
    }


def match_aliases(stocks_raw, alias_map):
    """stocks_raw에 alias 패턴이 포함된 고객 표기(한글 키) 목록."""
    if not stocks_raw:
        return []
    up = stocks_raw.upper()
    return [k for k, pats in alias_map.items()
            if any(p.upper() in up for p in pats)]


def build_funds(df, alias_map):
    funds = {}
    fees = df["총보수(%)"].astype(float)
    quartiles = pd.qcut(fees, 4, labels=[1, 2, 3, 4])
    for i, row in df.iterrows():
        code = str(row["브랜드상품코드"]).strip()
        name = norm_text(row["브랜드상품명"])
        features = norm_text(row["상품특징내용"])
        one_liner = norm_text(row["상품정보(한줄정보/추천사유)"])
        stocks_raw = norm_text(row["주요보유종목"])
        risk_grade = norm_text(row["위험등급"])
        funds[code] = {
            "name": name,
            "fee_pct": round(float(row["총보수(%)"]), 4),
            "one_liner": one_liner,
            "returns": {
                "m1": round_pct(row["수익률1개월(%)"]),
                "m3": round_pct(row["수익률3개월(%)"]),
                "m6": round_pct(row["수익률6개월(%)"]),
                "m12": round_pct(row["수익률12개월(%)"]),
            },
            "fund_type": norm_text(row["펀드유형"]),
            "risk_grade": risk_grade,
            "risk_score": RISK_SCORE[risk_grade],
            "manager": norm_text(row["운용사"]),
            "region": norm_text(row["투자국가"]),
            "features": features,
            "stocks_raw": stocks_raw,
            "has_holdings_info": stocks_raw is not None,
            "matched_aliases": match_aliases(stocks_raw, alias_map),
            "tags": parse_tags(name, features or "", one_liner or ""),
            "share_class": parse_share_class(name),
            "fee_quartile": int(quartiles.iloc[i]),
            "as_of": AS_OF,
        }
    return funds


RISK_PHRASE = {
    1: "가격 변동이 매우 작은 편이지만 손실 가능성은 있음",
    2: "가격 변동이 상대적으로 작은 편이지만 손실 가능성은 있음",
    3: "가격 변동이 중간 수준인 편",
    4: "가격 변동과 손실 가능성이 다소 큰 편",
    5: "가격 변동과 손실 가능성이 큰 편",
    6: "가격 변동과 손실 가능성이 매우 큰 편",
}
FEE_PHRASE = {1: "연간 수수료 부담이 낮은 편", 2: "연간 수수료 부담이 보통 수준",
              3: "연간 수수료 부담이 보통 수준", 4: "연간 수수료 부담이 높은 편"}


def make_content(code, f):
    """고객언어형 검색 CONTENT (03 §7). 정확한 수치는 넣지 않는다."""
    lines = [f"[{code}] {f['name']}"]
    lines.append(
        f"{f['region'] or ''} {f['fund_type']} 펀드. "
        f"{RISK_PHRASE[f['risk_score']]}({f['risk_grade']}). "
        f"{FEE_PHRASE[f['fee_quartile']]}."
    )
    if f["one_liner"]:
        lines.append(f["one_liner"])
    if f["matched_aliases"]:
        lines.append(", ".join(f["matched_aliases"]) + " 등을 주요 종목으로 담고 있음.")
    elif not f["has_holdings_info"]:
        lines.append("주요 보유종목 정보는 공개되지 않은 상품.")

    q = [f"{f['region'] or ''} {f['fund_type']}".strip()]
    t = f["tags"]
    if t["tdf"]:
        q += ["TDF", "은퇴 시점에 맞춰 자산을 조정하는 펀드", "노후 준비 연금 펀드"]
        if t["tdf_vintage"]:
            q.append(f"TDF{t['tdf_vintage']}")
    if t["income"]:
        q += ["월지급식", "배당 인컴 펀드", "매달 분배금이 나오는 상품",
              "매월 정기적으로 현금을 받고 싶을 때", "용돈처럼 나눠 받는 펀드"]
    if t["pension_eligible"]:
        q.append("연금저축이나 IRP에 담을 수 있는 펀드")
    if f["fee_quartile"] == 1:
        q.append(f"수수료 낮은 {f['region'] or ''} 펀드".strip())
    if f["risk_score"] <= 2:
        q.append("안정적인, 가격 변동이 작은 상품")
    q += [f"{a} 포함 펀드" for a in f["matched_aliases"]]
    lines.append("이런 검색에 맞는 상품: " + ", ".join(q) + ".")
    return "\n".join(lines)


def validate(funds, contents, alias_map):
    """03 §12 빌드 검증 — 실패 시 빌드 중단. (실측값, 기대값) 출력."""
    checks = []

    def check(label, actual, expect):
        ok = (actual == expect) if not callable(expect) else expect(actual)
        checks.append((label, actual, ok))
        return ok

    nvda = [c for c, f in funds.items() if "엔비디아" in f["matched_aliases"]]
    nvda_le5 = [c for c in nvda if funds[c]["risk_score"] <= 5]
    tdf = [c for c, f in funds.items() if f["tags"]["tdf"]]
    vintages = [funds[c]["tags"]["tdf_vintage"] for c in tdf if funds[c]["tags"]["tdf_vintage"]]
    stable_income = [c for c, f in funds.items()
                     if f["risk_score"] <= 2 and f["tags"]["income"]]
    ai_kw = [c for c, f in funds.items()
             if re.search(r"\bAI\b|인공지능|반도체", " ".join(
                 filter(None, [f["name"], f["one_liner"], f["features"]])))]
    ai_min_risk = min((funds[c]["risk_score"] for c in ai_kw), default=None)

    check("총 상품 수 == 311", len(funds), 311)
    check("risk_score 결측 0건", sum(1 for f in funds.values() if not f.get("risk_score")), 0)
    check("엔비디아 alias 매칭 25건", len(nvda), 25)
    check("엔비디아 매칭 중 risk_score≤5 21건", len(nvda_le5), 21)
    check("TDF 태그 32건", len(tdf), 32)
    check("TDF vintage 2015~2055 범위", all(2015 <= v <= 2055 for v in vintages), True)
    check("안정형 풀(≤2) income 6건", len(stable_income), 6)
    check("AI·반도체 키워드 상품 최소 risk_score ≥ 4", ai_min_risk, lambda a: a is not None and a >= 4)
    check("페르소나 보유코드 4종 존재", all(c in funds for c in PERSONA_CODES), True)
    check("CONTENT 수 == funds 수", len(contents), len(funds))

    print("\n=== 빌드 검증 (03 §12) ===")
    failed = 0
    for label, actual, ok in checks:
        print(f"  {'PASS' if ok else 'FAIL'}  {label}  (실측: {actual})")
        failed += (not ok)
    if failed:
        print(f"\n빌드 중단: {failed}개 검증 실패")
        sys.exit(1)
    return {"nvda": len(nvda), "tdf": len(tdf), "stable_income": len(stable_income),
            "ai_kw": len(ai_kw)}


def report(df, funds):
    print("=== 빌드 리포트 ===")
    print(f"원본 행수: {len(df)}")
    print("\n위험등급 분포:")
    for g, n in df["위험등급"].value_counts().items():
        print(f"  {g}: {n}")
    t = [f["tags"] for f in funds.values()]
    print(f"\n파생 필드: TDF {sum(x['tdf'] for x in t)}건 / "
          f"income {sum(x['income'] for x in t)}건 / "
          f"연금적격 {sum(x['pension_eligible'] for x in t)}건 / "
          f"환헤지표기 {sum(1 for x in t if x['hedge'])}건 / "
          f"인덱스파생 {sum(x['index_derivative'] for x in t)}건")
    print(f"보유종목 결측: {sum(1 for f in funds.values() if not f['has_holdings_info'])}건 / "
          f"운용사 결측: {sum(1 for f in funds.values() if not f['manager'])}건 / "
          f"share_class 파싱 실패: {sum(1 for f in funds.values() if not f['share_class'])}건")


def main():
    with open(ALIAS_JSON, encoding="utf-8") as fp:
        alias_map = json.load(fp)
    df = pd.read_excel(RAW_XLSX)

    funds = build_funds(df, alias_map)
    contents = [{"product_code": c, "content": make_content(c, f)}
                for c, f in funds.items()]

    report(df, funds)
    validate(funds, contents, alias_map)

    with open(FUNDS_JSON, "w", encoding="utf-8") as fp:
        json.dump(funds, fp, ensure_ascii=False, indent=1)
    with open(CONTENTS_JSONL, "w", encoding="utf-8") as fp:
        for row in contents:
            fp.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"\n저장: {FUNDS_JSON} ({len(funds)}건), {CONTENTS_JSONL} ({len(contents)}건)")

    if os.environ.get("SKIP_EMBED") == "1":
        print("SKIP_EMBED=1 — 임베딩 생략")
    else:
        from dotenv import load_dotenv
        load_dotenv()
        from langchain_openai import OpenAIEmbeddings
        emb = OpenAIEmbeddings(model="text-embedding-3-small")
        vectors = emb.embed_documents([r["content"] for r in contents])
        arr = np.array(vectors, dtype=np.float32)
        assert arr.shape == (len(contents), 1536), f"임베딩 shape 오류: {arr.shape}"
        np.save(EMBEDDINGS_NPY, arr)
        print(f"저장: {EMBEDDINGS_NPY} shape={arr.shape}")

    print("\n=== 샘플 (눈 확인용) ===")
    sample_code = "KF04001379"
    print(json.dumps({sample_code: funds[sample_code]}, ensure_ascii=False, indent=1))
    print("\n--- CONTENT 샘플 ---")
    print(next(r["content"] for r in contents if r["product_code"] == sample_code))


if __name__ == "__main__":
    main()
