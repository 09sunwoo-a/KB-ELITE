# 02. LangGraph 아키텍처 — 펀드 길잡이 에이전트

> **문서 목적**: `01_펀드_길잡이_서비스_컨셉_대화플로우_v4.md`(이하 01)에서 정의한 탐색 노트·행동 4종·노출 규칙·계산 범위를 LangGraph 구현 구조로 번역한다.
> **설계 기준**: 5분 발표에서 설명 가능한 최소 구조. 수업 내용 중 핵심만 채택하고, 채택하지 않은 패턴은 사유와 함께 명시한다(9장). Claude Code는 이 문서의 구조를 벗어나는 추가 추상화·패턴 도입을 하지 않는다.

---

## 1. 설계 철학 — 명시적 그래프, 제한된 자율성

**ReAct 자율 루프 대신 명시적 분기 그래프를 쓴다.**

- 금융상품 응답은 예측 가능해야 한다. LLM이 도구를 자유 선택하는 ReAct(`create_agent` + `bind_tools`) 대신, **라우터가 행동 4종 중 하나를 고르고 각 행동 노드가 정해진 도구를 코드로 호출**하는 구조를 쓴다.
- LLM의 역할은 2가지로 제한: ① 라우팅+조건 추출(structured output), ② 응답 문장 생성. 검색 필터·비용 계산·겹침 매칭·안내 문구 삽입은 전부 코드가 보장한다.
- 턴당 LLM 호출 2회(라우터 1 + 응답 생성 1)가 기본. 빠르고 저렴하고 디버깅이 쉽다.

이 선택 자체가 발표 논거다: "단순 API 호출도 아니고, 통제 불가능한 자율 에이전트도 아닌, **금융 도메인에 맞게 자율성을 제한한 Agent 설계**."

## 2. 전체 그래프 구조

```
[세션 시작 시 1회] load_profile()  ← 그래프 밖 초기화 함수 (mock 프로필 로드 → State 초기값)

        ┌──────────────────────────────────────────────┐
        │                턴 루프 (매 사용자 발화)          │
        │                                              │
START → router ──(conditional edges)──┬→ explain ──┐   │
        (행동 분류 + 조건 추출,          ├→ ask ──────┤   │
         structured output)            ├→ search ───┼→ postprocess → END
                                       └→ compare ──┘   (안전 후처리 +
        │                                                 후속 칩 생성)
        └──────────────────────────────────────────────┘
```

- 노드 6개: `router`, `explain`, `ask`, `search`, `compare`, `postprocess`
- 엣지: `START → router`, `router → (조건부) 4개 행동 노드`, `각 행동 노드 → postprocess`, `postprocess → END`
- 멀티턴: `InMemorySaver` checkpointer + `thread_id`로 세션별 State 유지 (수업 2주차 06)
- 오프닝·빠른 시작 칩은 그래프가 아니라 **세션 시작 시 코드 함수**로 생성한다(8장). 칩·골격은 코드, 능력 소개 본문만 LLM 동적 생성+검증·폴백(2026-07-18 개정).

## 3. State — 탐색 노트 (01의 5-2를 그대로 번역)

```python
from typing import TypedDict, Annotated, Optional, Literal
from langgraph.graph import add_messages
import operator

class ExploreState(TypedDict):
    # 대화
    messages: Annotated[list, add_messages]

    # 안전 기준선 + 고객 컨텍스트 (load_profile이 채움, 세션 중 불변)
    profile: dict            # 01의 4-1 스키마 원본 (risk_profile, holdings, ...)
    max_risk_score: int      # 성향 → 열람 상한 (01 4-2 매핑, 코드로 산출)

    # 이번 자금 조건 + 상품 조건 (대화에서 갱신, 라우터가 추출)
    conditions: dict         # {goal, horizon, loss_tolerance, region_theme,
                             #  target_stock, cost_sensitive, fund_type, ...} 값 없으면 키 없음

    # 탐색 이력
    seen_funds: Annotated[list[str], operator.add]   # 제시한 상품코드 누적
    explained_terms: Annotated[list[str], operator.add]
    last_candidates: list[dict]                      # 직전 후보 (비교 대상 특정용, 덮어쓰기)

    # 대화 제어
    action: Literal["explain", "ask", "search", "compare"]  # 라우터 출력
    ask_streak: int                                   # 연속 질문 횟수 (01 5-4 규칙 5)

    # 시연용 백단 추적 (04 Streamlit 우측 패널의 데이터 소스)
    trace: Annotated[list[dict], operator.add]       # 각 노드가 TraceEntry 형식으로 append
                                                     # {"node","kind","summary","detail"} — 04 6-2
```

설계 노트:
- `trace`가 이 프로젝트의 차별점이다. 모든 노드는 자기 판단·도구 호출 결과를 `trace`에 남기고, Streamlit이 이를 그대로 렌더링해 "Agent가 어떻게 동작하는지"를 시연한다.
- reducer는 수업 기본형만 사용: `add_messages`, `operator.add`, 나머지는 덮어쓰기. 커스텀 reducer 불필요.

## 4. 라우터 노드 — 행동 분류 + 조건 추출을 한 번에

`with_structured_output`(수업 1주차 02 / 2주차 02) 한 번으로 행동과 조건을 동시에 뽑는다.

```python
from pydantic import BaseModel, Field
from typing import Literal, Optional

class RouteResult(BaseModel):
    action: Literal["explain", "ask", "search", "compare"] = Field(
        description="explain: 용어·구조·위험 질문 / ask: 필수 맥락 부족 / "
                    "search: 조건 충분 또는 구체 조건 명시 / compare: 후보 간 비교 요청")
    action_reason: str = Field(
        description="행동 선택 이유 한 문장(고객 언어). trace·UI 표시용 — 04 5-1")
    # 조건 추출 (발화에 있는 것만, 추정 금지)
    region_theme: Optional[str] = None      # 예: 미국, 나스닥, AI, 연금
    target_stock: Optional[str] = None      # 예: 엔비디아
    loss_tolerance: Optional[str] = None    # 예: 큰 변동 회피
    horizon: Optional[str] = None           # 예: 5년 이상
    fund_type_hint: Optional[str] = None    # 예: 월지급·인컴, TDF
    cost_sensitive: bool = False
    compare_targets: list[int] = []         # "1번 3번 비교" → [1, 3] (직전 후보 순번)
    term_to_explain: Optional[str] = None   # explain일 때 대상 용어
    # 가드레일 플래그 (7장)
    delegation_request: bool = False        # "뭘 사면 돼요?" 등 판단 위임 발화
    out_of_scope: bool = False              # 수익 예측·매수 타이밍 등 비범위 요청
```

라우터 노드 책임:
1. `RouteResult` 획득 → `conditions` 병합, `action` 기록
2. **01 5-4 규칙을 코드로 오버라이드**: ① `ask_streak >= 2`면 action이 ask여도 search로 전환(느슨한 검색), ② compare인데 `last_candidates`가 2개 미만이면 search로 폴백
3. 가드레일 플래그(`delegation_request`, `out_of_scope`) 감지 시 행동 분기는 유지하되, 응답 프롬프트에 재프레이밍 지시를 전달(7-1)
4. `trace`에 분류 결과·추출 조건·플래그 기록

라우터 프롬프트에는 01의 "의도별 필수정보 예시"(5-4) 표를 그대로 넣는다. 슬롯 개수 규칙이 아니라 의도별 판단임을 프롬프트로 지시한다.

## 5. 행동 노드 4종 — 컨텍스트 준비 + 응답 생성

각 노드는 같은 뼈대를 따른다: **(a) 코드로 컨텍스트 준비 → (b) 행동별 프롬프트로 응답 생성 → (c) trace 기록**.

| 노드 | (a) 컨텍스트 준비 (코드) | (b) 응답 프롬프트 핵심 지시 |
|---|---|---|
| `explain` | 용어 설명 지식 조회(03에서 정의: 가이드 문서 또는 사전), `explained_terms` 확인(중복 설명 축약) | 눈높이 반영, 오개념 교정 우선, 탐색으로 잇는 선택지 1개로 마무리 |
| `ask` | 미확보 조건 중 현재 의도에 필요한 것 1개 선정, `ask_streak += 1` | 질문 1개 + 답하기 쉬운 선택지 예시, 개인 데이터 복창 금지 |
| `search` | `search_funds()` 호출(6장) → 후보 2~4개 + 차단 정보(excluded_by_risk·blocked), `seen_funds`·`last_candidates` 갱신, `ask_streak = 0` | 선정 기준 명시, 후보별 근거(위험등급·연간 비용·유형), 판단형 표현 금지. blocked면 후보 없이 차단 사유·대안 안내 |
| `compare` | `compare_targets`로 `last_candidates`에서 대상 특정 → 정형 필드 비교표 데이터 구성, 요청 시 `match_overlap()` 호출 | 공통 기준으로 차이만 서술, 우열 표현 금지, 데이터 한계(비중 없음) 고지 |

응답 생성 LLM 호출 시 시스템 프롬프트 구성(공통): 역할 정의 + 01의 8-2 말투 규칙 + 8-3 고객 언어 사전 + 프로필 요약(눈높이·성향, 복창 금지 지시) + 행동별 지시. 프롬프트 원문은 `prompts.py`에 상수로 두고 03/04와 공유한다.

## 6. 도구 — 순수 함수 3종 (LLM이 아닌 코드가 호출)

```python
def search_funds(conditions: dict, max_risk_score: int, query_text: str) -> SearchResult:
    """01 4-2 노출 규칙(하드 필터) 구현.
    1) 정형 필터(pandas): risk_score <= max_risk_score — 예외 없음, 성향 초과 상품은
       후보로 노출하지 않는다. + 지역/테마 태그, 유형, 종목 alias 포함 여부
    2) 차단 집계: 성향 초과로 제외된 상품 수를 excluded_by_risk로 기록.
       조건 일치 상품이 전부 성향 초과라 범위 내 0건이면 blocked=True
    3) 랭킹: cost_sensitive면 총보수 오름차순, 아니면 벡터 유사도(03의 CONTENT 임베딩) 상위 k
    반환: 후보 리스트(dict) + excluded_by_risk + blocked 플래그
        + 벡터 랭킹 턴은 후보별 유사도 scores {fund_code: float} (정형 정렬 턴은 None —
          trace 검색 근거 탭 표시용, 2026-07-18 추가. 임베딩 벡터 원문은 반환·노출하지 않는다)
    """

def calc_annual_cost(fee_pct: float, amount: int, contribution_type: str) -> str:
    """01 4-6 비용 환산. lumpsum: amount × fee. monthly: 첫해 평균잔액(납입액×6.5개월 근사) × fee.
    '실제 비용은 납입일·기준가격에 따라 달라질 수 있음' 문구를 결과에 포함해 반환."""

def match_overlap(holdings: list[dict], fund_top_holdings: str, alias_map: dict) -> dict:
    """01 4-6 겹침 분석. alias 정규화 → 문자열 매칭 → 겹치는 종목명 리스트만 반환.
    비중 계산 없음. fund_top_holdings가 결측이면 {"available": False} 반환."""
```

- 세 함수 모두 그래프 노드가 아니라 **행동 노드 내부에서 직접 호출**한다. `ToolNode`·`tools_condition` 순환 불필요.
- `search_funds`의 벡터 검색은 03에서 정의하는 고객언어형 CONTENT 임베딩(`InMemoryVectorStore` + `text-embedding-3-small`, 수업 3주차)을 사용한다. 311개 규모라 외부 벡터 DB 불필요.

## 7. 가드레일 — '탐색' 정체성 보장 + 금소법 취지 반영

가드레일은 2층으로 작게 유지한다: **입력**(라우터 플래그 → 재프레이밍)과 **출력**(postprocess 코드 검사). 별도 미들웨어·노드는 추가하지 않는다.

### 7-1. 입력 가드 — 판단 위임·비범위 요청의 재프레이밍

라우터가 두 플래그를 감지하면 행동 분기는 그대로 두고, 응답 프롬프트에 재프레이밍 지시를 추가한다. 차단·거절이 아니라 **탐색으로 되돌리는 것**이 목적이다.

| 플래그 | 감지 예시 | 응답 처리 |
|---|---|---|
| `delegation_request` | "그래서 뭘 사면 돼요?", "제일 좋은 걸로 추천해줘", "대신 골라줘" | 특정 상품을 골라드리거나 추천할 수 없음을 먼저 밝히고, 판단에 필요한 기준·후보 간 차이를 정리해 제시한 뒤 선택권 반환. 검색·비교 자체는 정상 수행 |
| `out_of_scope` | "오를까요?", "지금 사도 돼요?", "얼마나 벌 수 있어요?" | 수익 예측·매수 시점 판단이 불가함을 고지하고, 제공 가능한 것(과거 수익률과 기준기간, 위험등급, 비용)으로 전환 제안 |

"그래서 뭘 사면 돼요?"에 대한 재프레이밍 응답은 서비스 정체성('탐색이지 추천이 아니다')을 가장 직접적으로 보여주는 시연 소재로 쓴다(05 반영).

### 7-2. 출력 가드 — postprocess 노드 (코드가 보장, 01 8-4)

응답 텍스트에 대해 순서대로 실행:

1. **금칙 표현 검사·치환** — 3범주 정규식. 치환 발생 시 trace에 기록한다(시연 포인트: "LLM이 실수해도 코드가 막는다").
   - 판단·권유형: `추천드립|가입하세요|적합합니다|이 상품이 낫|골라드리`
   - 수익 보장·오인형: `원금 보장|원금이 보장|손실 없|손실이 없|확정 수익|반드시 오`
   - 최상급·우위형: `최고의|가장 좋은|무조건`
2. **성향 초과 차단 안내 삽입**: `search` 결과의 `excluded_by_risk > 0` 또는 `blocked=True`면 정해진 상수 문구(제외 사실·사유, blocked면 대안 제안 포함)를 응답 끝에 삽입. LLM에 맡기지 않는다(차단 안내 누락률 0% 목표).
3. **고지 문구 삽입** (상수 2종, 해당 응답에 1회):
   - 후보·수치 포함 시: `※ 본 안내는 특정 상품의 추천·권유가 아닌 정보 제공이며, 최종 판단과 선택은 고객님께 있습니다.`
   - 원금·수익 관련 시: `※ 펀드는 예금과 달리 원금 손실이 발생할 수 있으며, 과거 수익률이 미래 수익을 보장하지 않습니다.`
4. **후속 칩 결정** (2026-07-18 개정 — 하이브리드): 두 층위로 구성한다.
   - **동적 칩(기본)**: explain·compare·search(후보 있음) 턴은 응답 생성 호출(§5)을 structured output(`{answer, chips}`)으로 확장해 **컨텍스트 기반 칩 2개**를 함께 받는다 — LLM 재호출 없음, 턴당 호출 수 불변. postprocess가 코드로 검증(금칙 3범주·길이·개수·중복)하고, **하나라도 실패하면 세트 전체를 버리고 규칙 기반 칩으로 폴백**한다. 칩 출처(llm/rule)와 폐기 사유는 trace에 남긴다. 칩은 "고객이 클릭해 그대로 다음 발화로 전송되는 문장"이므로, 시스템이 지원하는 행동(설명·검색·비교·겹침)만 제안하고 데이터에 없는 것(종목 비중, 글라이드패스, 분배 내역, 수익 전망)과 추천 요청 어투를 금지하는 지시를 프롬프트에 포함한다(01 5-5 표현 원칙 준수).
   - **규칙 칩(고정, LLM 미사용)**: ask 턴(슬롯 답변 선택지 — 클릭만으로 대화 진행), 성향 차단·검색 0건 턴(복구 플로우가 칩 문구와 결합 — 라우터의 '가입 가능한 범위' 문자열 처리)은 규칙 기반을 유지한다. 오프닝 칩도 8장대로 코드 생성.

### 7-3. 금소법 취지 반영 매핑

본 서비스는 판매·권유 행위를 수행하지 않는 정보 제공형 탐색 레이어다. 1차 원칙은 **규제 대상 행위(권유·단정적 판단 제공) 자체를 만들지 않는 것**이고, 그 위에 판매규제의 취지를 설계에 반영한다.

| 금소법 취지 | 구현 장치 |
|---|---|
| 적합성 원칙 | 투자성향 기반 노출 차단(01 4-2 하드 필터): 상한 초과 상품은 후보로 노출하지 않고, 차단 사실·사유를 안내 |
| 설명의무 | 후보 제시 시 위험등급·비용 근거 동시 표기, 원금 손실 가능 고지 문구 |
| 부당권유 금지 | 판단·권유형 금칙 처리(7-2), 판단 위임 재프레이밍(7-1), 단정적 전망 제공 금지 |
| 허위·과장 금지 | 수익 보장·오인형 금칙 처리, 수익률에 기준기간·기준일 표시 |

발표·문서에서는 "금소법을 준수한다"가 아니라 **"판매규제의 취지를 탐색 레이어 설계에 반영했다"**로 표현한다(법적 판단으로 읽히는 과장 방지).

## 8. 오프닝·빠른 시작 칩 — 하이브리드 (2026-07-18 개정)

칩과 골격은 코드, **능력 소개 본문만 LLM 동적 생성**. 동적 칩(§7-2 ④)과 같은 "LLM이 생성하고 코드가 검증·폴백한다" 패턴이다.

```python
def build_opening(profile: dict, dynamic: bool = True) -> dict:
    """01 6장의 페르소나별 오프닝.
    - 인사("안녕하세요, {이름} 고객님.")와 칩 3개(이해·찾기·비교 역할 1개씩, 01 5-5)는
      코드 템플릿 유지 — LLM 미사용.
    - 능력 소개+시작 제안 본문: LLM이 프로필을 참고해 생성하되, 코드가 검증한다 —
      금칙 3범주 / 행동 복창 표현("~하셨네요", "지난번") / 불가 약속(종목 비중·수익 예측·추천) /
      개인 데이터 토큰(보유상품명·투자성향 명칭·금액·나이) 포함 / 길이(40~220자 —
      프롬프트로 150자 이내를 유도하고 검증은 여유 있는 상한만 막는다).
      하나라도 걸리면 기존 프로필 분기 템플릿으로 폴백 (01 4-4는 최종적으로 코드가 보장).
    - 캐시 없음 (2026-07-18 사용자 결정): 채팅 진입·대화 초기화 때마다 새로 생성한다(2~3초).
      UI는 그동안 "고객 프로필 확인" 진행 상태를 표시한다(04 §4-1).
    - 반환에 trace(TraceEntry 리스트) 포함: 신호 추출 → LLM 생성 → 검증(통과/폴백+사유)을
      기록해 UI trace 패널이 오프닝 개인화 과정을 로그로 보여준다.
    """
```

시연의 "장면 0 — 같은 에이전트, 다른 첫인사"는 이 함수에 프로필을 넣은 결과를 나란히 보여주는 것으로 구현된다.

## 9. 수업 내용 채택/비채택 — 기술 선택의 타당성

### 채택 (핵심만)

| 수업 내용 | 사용처 | 채택 이유 |
|---|---|---|
| Chat 모델 추상화 (1주차) | 라우터·응답 생성 | 2026-07-18 교체: Anthropic Claude — 라우터 `claude-sonnet-5`(분류·조건 추출 품질 레버, 토큰 적어 지연 영향 미미) / 응답·칩 생성 `claude-haiku-4-5`(데모 속도·비용). 임베딩은 OpenAI `text-embedding-3-small` 유지(Anthropic은 임베딩 미제공) |
| `with_structured_output` + Pydantic (1주차 02) | RouteResult | 행동 분류+조건 추출을 검증 가능한 형태로 |
| StateGraph·조건부 엣지 (2주차 01~03) | 그래프 전체 | 행동 4종 분기의 직접 번역 |
| `add_messages`·`operator.add` reducer (2주차) | messages, seen_funds, trace | 누적 상태 관리 |
| `InMemorySaver` + thread_id (2주차 06) | 세션 멀티턴 | 페르소나별 세션 격리 |
| RAG: 임베딩·InMemoryVectorStore (3주차) | 자연어 검색 랭킹 | 고객언어 질의 매칭 |
| 프롬프트 상수 분리·가드레일 (1주차 04) | 7장 입력·출력 가드 | 탐색 정체성('추천 아님')과 금소법 취지를 코드로 보장 |

### 비채택 (사유 명시 — 발표 Q&A 방어용)

| 패턴 | 비채택 사유 |
|---|---|
| ReAct 자율 루프 (`create_agent`+`bind_tools`) | 금융 응답의 예측 가능성 우선. 행동이 4종으로 유한해 명시 분기가 더 적합 |
| 멀티에이전트 (Supervisor/Handoff, 2주차 08) | 단일 도메인·단일 여정. 에이전트 분리로 얻는 게 없음 |
| Store 장기기억 (2주차 06) | 01 4-5 결정: 세션 내 개인화만. v2 확장 여지로 문서화 |
| HITL interrupt (2주차 07) | 가입·실행이 비범위(01 10장)라 승인 게이트 대상 없음 |
| Evaluator-Optimizer (2주차 05-1) | 턴당 지연 2배. 품질은 후처리+대본 기반 테스트로 확보 |
| MCP 서버 분리 (4주차) | **P2 스트레치**(05 문서): `search_funds`를 `@mcp.tool()`로 감싸는 확장 구조로 발표에서 언급. 데모 실패 지점을 늘리지 않기 위해 기본은 직접 호출 |
| Langfuse (3주차 05) | trace 필드 + Streamlit 패널이 시연용 관측을 대체. 실서비스 확장 항목으로 언급만 |

## 10. 파일 구조 (Claude Code 작업 기준)

```
app/
  graph.py        # ExploreState, 노드 6개, 그래프 빌드·compile
  router.py       # RouteResult 스키마, 라우터 로직(오버라이드 규칙 포함)
  tools.py        # search_funds, calc_annual_cost, match_overlap
  safety.py       # 가드레일: 금칙 3범주 패턴, 재프레이밍 지시·안내·고지 상수, postprocess 로직
  prompts.py      # 시스템 프롬프트 상수(공통+행동별), 라우터 프롬프트
  opening.py      # build_opening, 후속 칩 규칙
  personas.py     # mock 프로필 4종 로드 (03의 JSON)
data/             # 03에서 정의 (원본 xlsx, 파생 JSON, 임베딩 인덱스)
ui/
  streamlit_app.py  # 04에서 정의
tests/
  test_scripts.py   # 05에서 정의 (01 대본 기반 수용 기준)
```

## 11. 다음 문서와의 연결

| 이 문서에서 참조 | 정의 위치 |
|---|---|
| CONTENT 임베딩, 파생 필드(risk_score·태그), alias 사전, mock 프로필 JSON | 03 |
| trace 렌더링, 페르소나 전환, 오프닝 비교 뷰 | 04 |
| P0/P1/P2 컷라인, 대본 기반 수용 기준, MCP 스트레치 조건 | 05 |
