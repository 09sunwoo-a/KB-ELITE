"""빌드 산출물 로더 — 앱 시작 시 1회 로드, 재계산 없음 (03 §2).

funds.json이 모든 수치의 단일 출처다. 여기서 로드한 값 외의 수치는 어디서도 만들지 않는다.
"""

import json
import os
from functools import lru_cache

import numpy as np

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _path(*parts):
    return os.path.join(_BASE, *parts)


@lru_cache(maxsize=1)
def funds() -> dict:
    with open(_path("data", "funds.json"), encoding="utf-8") as fp:
        return json.load(fp)


@lru_cache(maxsize=1)
def alias_map() -> dict:
    with open(_path("data", "alias.json"), encoding="utf-8") as fp:
        return json.load(fp)


@lru_cache(maxsize=1)
def terms() -> list:
    with open(_path("data", "terms.json"), encoding="utf-8") as fp:
        return json.load(fp)


@lru_cache(maxsize=1)
def content_codes() -> list:
    with open(_path("data", "contents.jsonl"), encoding="utf-8") as fp:
        return [json.loads(l)["product_code"] for l in fp]


@lru_cache(maxsize=1)
def embeddings() -> np.ndarray:
    return np.load(_path("data", "embeddings.npy"))


@lru_cache(maxsize=1)
def code_index() -> dict:
    return {c: i for i, c in enumerate(content_codes())}


def persona(persona_id: str) -> dict:
    with open(_path("data", "personas", f"{persona_id}.json"), encoding="utf-8") as fp:
        return json.load(fp)
