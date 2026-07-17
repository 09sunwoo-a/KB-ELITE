# AI 펀드 길잡이 — Streamlit 시연 화면 기획안

> **문서 목적**  
> Claude Code가 최종발표용 Streamlit 시연 사이트를 구현할 수 있도록, 고객 화면의 사용자 경험과 실제 Agent 실행 Trace 화면의 요구사항을 정의한다.
>
> **핵심 원칙**  
> 이 사이트는 단순한 채팅 목업이 아니다.  
> 고객이 보는 AI 펀드 탐색 경험과, 그 요청을 처리한 **실제 LangGraph Agent의 실행 과정**을 한 화면에서 증명하는 발표용 애플리케이션이다.

---

## 0. Claude Code에 대한 최우선 지시

1. 이 문서의 화면 구조와 컴포넌트 요구사항을 기준으로 Streamlit 앱을 구현한다.
2. UI와 Agent 백엔드는 `AgentAdapter` 인터페이스로 분리한다.
3. Agent 연동 전에는 `MockAgentAdapter`, 실제 연동 후에는 `LangGraphAgentAdapter`를 사용한다.
4. **Mock 실행을 실제 Trace처럼 위장하지 않는다.**
   - Mock 사용 중에는 화면에 `MOCK MODE` 또는 `MOCK TRACE` 배지를 표시한다.
   - 실제 Agent가 연결되면 `LIVE AGENT` 배지로 변경한다.
5. 실제 모드의 Agent Trace는 미리 작성한 문구가 아니라 LangGraph 실행 중 발생한 이벤트와 State 변경을 기반으로 생성한다.
6. 모델의 숨겨진 추론 과정이나 Chain-of-Thought를 화면에 노출하지 않는다.
   - 표시 가능: 선택된 행동, 구조화된 의도, 추출 조건, 노드명, Tool 입력·결과 요약, 검색 근거, 안전성 검사 결과
   - 표시 금지: 모델의 내부 사고 과정, 원문 시스템 프롬프트, 전체 비공개 프롬프트, 민감정보
7. 발표 중 오류를 방지하기 위해 라이브 입력과 별도로 검증된 `시연 코스 버튼`을 제공한다.
8. 시연 코스 버튼도 고정 결과를 출력해서는 안 된다. 실제 Agent 입력으로 전달되어 동일한 실행 파이프라인을 거쳐야 한다.
9. 코드에 API Key, 내부 URL, 고객 개인정보를 하드코딩하지 않는다.
10. 고객에게 보이는 상품 수치는 LLM 생성값이 아니라 정형 상품 데이터 또는 Tool 결과만 사용한다.

---

# 1. 시연에서 전달해야 하는 핵심 메시지

시연 화면은 다음 다섯 가지를 2분 안에 증명해야 한다.

1. 기존 펀드 서브메인에 작은 AI 진입점이 자연스럽게 추가된다.
2. 고객의 자연어가 상품 검색조건으로 구조화된다.
3. Agent가 현재 요청에 맞춰 `질문·설명·검색·비교·겹침 분석` 중 행동을 선택한다.
4. RAG는 의미 기반 후보 탐색을 수행하고, 정형 Tool이 상품 수치를 검증한다.
5. 고객 데이터는 상품을 대신 결정하는 데 쓰지 않고 질문을 줄이거나 필요한 위험 맥락을 제공하는 데 사용된다.

한 줄 메시지:

> **AI가 펀드를 대신 골라주는 것이 아니라, 고객의 언어와 상품 데이터 사이의 탐색 공백을 메운다.**

---

# 2. 전체 사용자 여정

```text
[스타뱅킹 펀드 서브메인]
        │
        │ 우측 하단 'AI 펀드 길잡이' 클릭
        ▼
[고객용 전체화면 Chat UI]
        │
        │ 자연어 질문
        ▼
[LangGraph Agent 실행]
        │
        ├─ 고객 프로필 로드
        ├─ 발화 의도·조건 추출
        ├─ 행동 선택
        ├─ RAG / Tool 실행
        ├─ 안전성 검사
        └─ 응답 생성
        │
        ▼
[채팅 결과 + 상품 카드/비교표/겹침 분석]
        │
        │ 발표자가 'Agent 동작 보기' 활성화
        ▼
[고객 화면 + 실제 Agent Trace 패널]
```

화면 이동은 복잡한 멀티페이지 앱보다 `st.session_state` 또는 query parameter를 이용한 두 개의 주요 상태로 구현한다.

- `screen = "fund_home"`
- `screen = "chat"`

---

# 3. 화면 1 — 스타뱅킹 펀드 서브메인

## 3-1. 목적

발표 시작과 동시에 이 서비스가 별도의 실험용 챗봇이 아니라 **기존 스타뱅킹 펀드 고객 여정 안에 들어가는 기능**이라는 점을 보여준다.

## 3-2. 구현 방식

기존 펀드 서브메인 전체를 새로 개발하지 않는다.

- 개인정보와 내부정보를 제거한 실제 화면 캡처를 배경 이미지로 사용
- 이미지 위 우측 하단에 AI 플로팅 버튼만 HTML/CSS로 오버레이
- 이미지가 없을 때를 위한 단순 펀드 서브메인 목업 fallback 제공

권장 파일 경로:

```text
assets/fund_submain.png
```

권장 컨테이너 구조:

```html
<div class="phone-frame">
  <img class="fund-submain-image" />
  <button class="ai-fund-launcher">AI 펀드 길잡이</button>
</div>
```

CSS 기준:

```css
.phone-frame {
  position: relative;
}

.ai-fund-launcher {
  position: absolute;
  right: 18px;
  bottom: 24px;
}
```

## 3-3. 화면 요소

### 스마트폰 프레임

- 중앙 정렬
- 약 390~430px 폭
- 실제 모바일 앱처럼 둥근 외곽선
- 발표용 데스크톱에서 너무 작아 보이지 않도록 높이 720px 이상

### AI 플로팅 버튼

권장 표현:

```text
AI
펀드 길잡이
```

버튼 위 작은 말풍선:

> 어떤 펀드를 봐야 할지 막막하신가요?

버튼 클릭 시:

- `screen = "chat"`
- 선택된 페르소나 프로필 로드
- 새 대화 thread/session 생성
- 개인화 오프닝 표시

## 3-4. 캡처 보안 요구사항

다음 정보가 보이지 않도록 원본 이미지를 편집한다.

- 고객 이름
- 계좌번호
- 잔액
- 알림 내용
- 운영 서버 주소
- 테스트 계정
- 사번
- 미공개 상품 또는 내부 전용 메뉴

이미지 하단 또는 화면 외곽에 작게 다음 문구를 표시할 수 있다.

```text
Prototype · 실제 스타뱅킹 화면 기반 시연
```

---

# 4. 화면 2 — 고객용 AI 펀드 길잡이 Chat UI

## 4-1. 전체 레이아웃

기본 고객 모드:

```text
┌──────────────────────────────────────────┐
│ ←  AI 펀드 길잡이        Agent 동작 보기 │
├──────────────────────────────────────────┤
│ 현재 탐색 기준                           │
│ [엔비디아 편입] [비용 낮음]               │
│                                          │
│ AI 오프닝                                │
│ 빠른 시작 질문                           │
│                                          │
│ 사용자 메시지                            │
│ AI 응답                                  │
│ 상품 카드 / 비교표 / 겹침 결과            │
│                                          │
├──────────────────────────────────────────┤
│ 메시지를 입력하세요                 전송  │
└──────────────────────────────────────────┘
```

발표 모드에서 Trace 활성화:

```text
┌──────────── 고객 Chat UI ──────────────┬──── 실제 Agent Trace ────┐
│                                       │                         │
│ 고객 질문                              │ 현재 행동: SEARCH        │
│ AI 응답                                │ 행동 선택 이유            │
│ 후보 상품 카드                         │ 실행 노드 진행 상태        │
│ 비교표                                  │ State / RAG / Tool / Safe │
│ 겹침 분석                              │                         │
└───────────────────────────────────────┴─────────────────────────┘
```

권장 Streamlit 비율:

```python
chat_col, trace_col = st.columns([2.1, 1.0])
```

고객 화면이 항상 주인공이어야 한다.

---

# 5. 사이드바 — 시연 조종석

사이드바는 일반 사용자용 메뉴가 아니라 발표자가 안정적으로 데모를 진행하기 위한 조종석이다.

## 5-1. 페르소나 선택

```text
● 최준혁 · 조건 명확형
○ 정미숙 · 원금 민감형
○ 박서연 · 연금 탐색형
○ 서지우 · 펀드 초보형
```

페르소나 변경 시 다음을 초기화한다.

- 대화 메시지
- LangGraph thread ID
- 탐색 조건
- 후보 상품
- 비교 대상
- Trace 이벤트
- 개인화 오프닝
- 빠른 시작 질문

## 5-2. 고객 컨텍스트 요약

전체 고객정보가 아니라 발표에 필요한 정보만 표시한다.

최준혁 예시:

```text
투자성향   적극투자형
투자방식   목돈
관심분야   나스닥·반도체
보유종목   NVDA·TSLA
```

정미숙 예시:

```text
투자성향   안정형
투자방식   목돈
관심분야   월지급식·낮은 위험
보유종목   MMF·국내채권형
```

## 5-3. 시연 코스 버튼

```text
① 조건으로 바로 찾기
② 후보 상품 비교
③ 보유종목 겹침 확인
④ AI 펀드 위험 확인
```

각 버튼이 Agent에 전달할 실제 입력:

```text
① 엔비디아 많이 들어가고 비용 낮은 펀드 찾아줘
② 1번과 3번 비교해줘
③ 나 엔비디아 직접 갖고 있는데 얼마나 겹쳐?
④ 요즘 AI 펀드 어때요?
```

버튼 클릭 시에도 반드시 실제 `AgentAdapter.run_turn()` 또는 `stream_turn()`을 호출한다.

---

# 6. Chat UI 세부 컴포넌트

## 6-1. 상단 헤더

```text
AI 펀드 길잡이
대화로 조건을 발견하고 상품을 비교합니다.
```

오른쪽 기능:

- `Agent 동작 보기` 토글
- `대화 초기화`
- `펀드 화면으로 돌아가기`

## 6-2. 개인화 오프닝

최준혁:

> 안녕하세요, 최준혁 고객님. 종목 비중, 지역, 비용처럼 원하는 조건을 말씀해 주시면 해당 조건을 충족하는 후보를 바로 찾아 비교해 드릴게요. 어떤 조건으로 볼까요?

정미숙:

> 안녕하세요, 정미숙 고객님. 펀드의 손실 가능성과 분배금 구조를 쉽게 설명하고, 위험 수준이 낮은 편부터 조건별로 살펴볼 수 있도록 도와드리는 AI 펀드 길잡이예요. 궁금한 것부터 편하게 물어보세요.

## 6-3. 빠른 시작

화면 명칭은 `추천 질문`이 아니라 `빠른 시작`으로 표시한다.

최준혁:

- 엔비디아 비중 높은 펀드 보기
- 나스닥 펀드 비용 낮은 순으로 보기
- 보유종목과 중복 확인하기

정미숙:

- 펀드도 원금이 보장되나요?
- 월지급식은 어떻게 지급되나요?
- 위험이 낮은 편부터 살펴보기

버튼 클릭 시 문구가 사용자 메시지로 들어가고 실제 Agent를 실행한다.

## 6-4. 현재 탐색 기준

LangGraph State의 검색 조건 슬롯을 고객 언어로 보여준다.

예시:

```text
현재 탐색 기준
[관심 종목: 엔비디아] [비용: 낮은 편]
```

조건이 없는 첫 화면에서는 영역을 숨긴다.

고객이 조건을 수정하거나 제외할 수 있도록 확장 가능하지만, 최종발표 1차 범위에서는 조회 전용으로 구현한다.

## 6-5. 처리 상태

실제 Agent 이벤트와 연결해 현재 진행 상태를 표시한다.

예시:

```text
고객의 질문을 이해하고 있어요
관련 펀드를 찾고 있어요
상품 데이터를 확인하고 있어요
응답의 표현과 수치를 점검하고 있어요
```

고정 타이머로 순서대로 보여주지 않는다. 실제 Trace 이벤트가 도착했을 때 해당 문구를 갱신한다.

---

# 7. 검색 결과 — 펀드 후보 카드

검색 결과는 긴 텍스트가 아니라 3개의 카드로 보여준다.

## 카드 필수 정보

- 후보 번호
- 펀드명
- 고객 요청과 직접 연결되는 핵심 수치
- 연간 비용
- 위험등급
- 선정 근거
- 데이터 기준일

엔비디아 검색 카드 예시:

```text
① 글로벌 반도체 리더스 펀드

엔비디아 비중   14.2%
연간 비용        0.58%
위험등급         높은위험

선정 근거
엔비디아 편입 비중이 높고,
후보 중 연간 비용이 낮은 편입니다.

기준일 2026-06-30
```

## 카드 표시 원칙

- 최근 수익률은 고객이 요청하지 않았다면 첫 카드에 넣지 않는다.
- 상품 수치가 없는 경우 `정보 없음`으로 표시한다.
- LLM이 임의로 수치를 보완하지 않는다.
- `추천`, `적합`, `가입 권유` 표현을 사용하지 않는다.

---

# 8. 상품 비교 컴포넌트

사용자 발화:

> 1번과 3번 비교해줘.

Agent는 이전 턴의 `current_candidates`를 State에서 읽어 비교 대상을 결정한다.

비교표:

| 비교항목 | ① 글로벌 반도체 | ③ 미국 혁신기업 |
|---|---:|---:|
| 엔비디아 비중 | 14.2% | 7.1% |
| 연간 비용 | 0.58% | 0.41% |
| 위험등급 | 높은위험 | 높은위험 |
| 주요 투자대상 | 반도체 중심 | 미국 성장주 전반 |
| 보유종목 중복 | NVDA, TSLA | NVDA |

표 위 차이 요약:

> ①은 엔비디아와 반도체 집중도가 높고, ③은 엔비디아 비중은 낮지만 투자대상이 더 넓고 연간 비용이 낮아요.

금지 문구:

- ①이 더 좋습니다.
- 고객님께는 ③이 적합합니다.
- ①을 추천합니다.

---

# 9. 보유종목 겹침 분석 컴포넌트

사용자 발화:

> 나 엔비디아 직접 갖고 있는데 얼마나 겹쳐?

## 결과 요약

```text
공개된 상위 보유종목 기준으로
①번 펀드는 현재 보유종목 중 2개와 중복됩니다.
```

## 종목별 표시

```text
엔비디아   펀드 내 14.2%
테슬라      펀드 내 4.8%
```

가능하면 `st.progress()` 또는 가로 막대로 시각화한다.

## 해석 문구

> 엔비디아와 테슬라를 직접 보유하고 있어, 이 펀드를 추가하면 해당 종목에 대한 직접·간접 노출이 함께 늘어납니다.

## 하단 기준 문구

> 2026년 6월 말 공개된 상위 보유종목 기준입니다. 고객 전체 포트폴리오 비중이 아니라 펀드 내 편입 비중입니다.

고객 보유 평가금액과 전체 자산 비중이 없다면 `전체 포트폴리오 중복률`을 계산해서는 안 된다.

---

# 10. 정미숙 — 투자성향 초과 안내

질문:

> 요즘 AI 펀드 어때요?

Agent는 AI 관련 후보를 검색하고 정형 데이터에서 위험등급을 확인한다.

정미숙 고객에게는 후보 카드와 함께 추가 안내를 표시한다.

```text
투자성향 범위 초과 안내

현재 조회된 AI 관련 후보는 모두 높은위험 등급으로,
고객님의 투자성향 범위보다 위험 수준이 높습니다.
가격 변동과 손실 가능성을 확인한 뒤 계속 살펴볼지 선택해 주세요.
```

선택 버튼:

- `AI 펀드 계속 살펴보기`
- `위험이 낮은 후보로 돌아가기`

최준혁에게 동일 질문을 했을 때:

- 기본 위험등급과 손실 가능성 정보는 동일하게 표시
- 별도의 투자성향 초과 안내는 표시하지 않음

개인화는 상품정보를 다르게 만드는 것이 아니라 **추가로 확인해야 할 맥락을 다르게 제공하는 것**이다.

---

# 11. Agent Trace의 정확한 정의

## 11-1. 결론

시연 화면의 오른쪽 패널은 **실제 Agent 실행 Trace가 맞다.**

다만 이는 모델의 내부 생각을 보여주는 화면이 아니다.

다음 데이터를 실제 실행 결과에서 받아 시각화한다.

```text
사용자 입력
→ 실행된 LangGraph 노드
→ 각 노드가 State에 반영한 구조화된 결과
→ 라우터가 선택한 다음 행동
→ Retriever 검색 질의와 채택 문서
→ Tool 이름·입력·결과 요약
→ 안전성 검사 결과
→ 최종 응답
```

## 11-2. 표시 가능한 Trace

- 실행 시작·종료 시간
- run/thread ID의 일부
- 실행 노드명
- 노드 상태: 대기 / 실행 중 / 완료 / 오류
- 구조화된 intent
- 구조화된 search slots
- 선택 action
- action reason code 또는 짧은 설명
- 검색 query
- 검색된 문서 ID·상품코드·점수
- 호출 Tool 이름
- 민감정보가 제거된 Tool 입력
- Tool 결과 요약
- State 변경 내역
- 안전성 검사 항목
- 최종 후보 상품코드
- 오류·fallback 발생 여부

## 11-3. 표시하면 안 되는 Trace

- 모델의 숨겨진 Chain-of-Thought
- 프롬프트 원문 전체
- 시스템 메시지
- 내부 보안 정책 원문
- 고객 식별자 원문
- 계좌번호
- 인증 토큰
- API Key
- 임베딩 벡터 전체
- RAG 원문 전체
- 내부 서버 주소
- 디버깅용 민감 로그

행동 선택 이유는 모델의 긴 사고과정이 아니라 구조화된 결과로 반환한다.

권장 형태:

```json
{
  "action": "search",
  "reason_code": "ENOUGH_SEARCH_CONDITIONS",
  "reason_summary": "관심 종목과 비용 조건이 명확해 추가 질문 없이 검색합니다."
}
```

---

# 12. Trace 수집 방식

## 12-1. 권장 방식

`LangGraphAgentAdapter`가 LangGraph의 스트리밍 실행을 소비하고, UI가 이해할 수 있는 `TraceEvent`로 변환한다.

개념 구조:

```python
class AgentAdapter(Protocol):
    def stream_turn(
        self,
        user_message: str,
        customer_profile: dict,
        thread_id: str,
    ) -> Iterable["AgentUIEvent"]:
        ...
```

실제 구현:

```python
class LangGraphAgentAdapter:
    def stream_turn(...):
        for graph_event in compiled_graph.stream(...):
            yield map_graph_event_to_ui_event(graph_event)
```

LangGraph 버전에 따라 정확한 호출 방식은 현재 설치된 공식 API에 맞춰 구현한다.

권장 스트림 역할:

- `updates`: 노드별 State 변경
- `values`: 단계별 또는 최종 State snapshot
- `messages`: 최종 답변 token streaming
- `custom`: 노드 내부의 검색·검증 진행 상황
- 필요 시 `tasks` 또는 debug 계열 이벤트는 개발 환경에서만 사용

## 12-2. UI용 Trace 이벤트 스키마

```python
from typing import Any, Literal, TypedDict


class AgentUIEvent(TypedDict, total=False):
    run_id: str
    thread_id: str
    timestamp: str

    event_type: Literal[
        "run_started",
        "node_started",
        "node_completed",
        "state_updated",
        "retrieval_started",
        "retrieval_completed",
        "tool_started",
        "tool_completed",
        "safety_completed",
        "token",
        "run_completed",
        "run_error",
    ]

    node_name: str
    display_name: str
    status: Literal["waiting", "running", "completed", "error"]

    summary: str
    safe_payload: dict[str, Any]
```

`safe_payload`는 화면에 노출 가능한 데이터만 담는다.

## 12-3. UI에서 보관할 Session State

```python
st.session_state.messages
st.session_state.thread_id
st.session_state.customer_profile
st.session_state.search_slots
st.session_state.current_candidates
st.session_state.selected_funds
st.session_state.trace_events
st.session_state.latest_state
st.session_state.agent_mode       # mock | live
st.session_state.trace_visible
```

---

# 13. Trace 패널 화면 설계

## 13-1. 상단 배지

실제 연결:

```text
● LIVE AGENT
```

Mock 연결:

```text
● MOCK TRACE
```

이 배지는 항상 보여야 한다.

## 13-2. 현재 AI 행동

```text
현재 행동
SEARCH

관심 종목과 비용 조건이 명확해
추가 질문 없이 상품을 검색합니다.
```

이 정보는 Agent State의 `action`, `action_reason`을 사용한다.

## 13-3. 실행 흐름

고객 친화적 표시명으로 보여준다.

| 내부 노드명 | 화면 표시명 |
|---|---|
| `load_profile` | 고객 컨텍스트 불러오기 |
| `understand_turn` | 질문 의도 파악 |
| `update_exploration_note` | 탐색 조건 정리 |
| `route_action` | 다음 행동 선택 |
| `search_funds` | 관련 펀드 탐색 |
| `retrieve_fund_docs` | 상품 설명 검색 |
| `validate_fund_data` | 상품 수치 검증 |
| `compare_funds` | 후보 상품 비교 |
| `analyze_overlap` | 보유종목 중복 계산 |
| `safety_guard` | 위험·표현 안전성 점검 |
| `generate_response` | 고객 답변 생성 |

상태 표시:

```text
✓ 고객 컨텍스트 불러오기
✓ 질문 의도 파악
✓ 탐색 조건 정리
● 관련 펀드 탐색 중
○ 상품 수치 검증
○ 안전성 점검
```

## 13-4. 세부 탭

```text
[탐색 노트] [검색 근거] [Tool 실행] [안전 점검]
```

### 탐색 노트

```text
고객 의도       상품 검색
관심 종목       엔비디아
비용 선호       낮음
현재 후보       F001, F003, F007
질문 횟수       0
```

State 원본 JSON은 기본적으로 숨기고 `원본 State 보기` expander에서만 표시한다.

### 검색 근거

```text
변환된 검색문
"엔비디아 편입 비중이 높고 연간 비용이 낮은 주식형 펀드"

검색 결과
1. F001 · score 0.89 · 채택
2. F003 · score 0.84 · 채택
3. F007 · score 0.81 · 채택
4. F011 · score 0.74 · 제외
```

제외 사유가 있으면 표시한다.

```text
제외 사유: 판매 불가 / 조건 불일치 / 정형 데이터 누락
```

### Tool 실행

```text
fund_detail_tool

입력
fund_codes: F001, F003, F007

확인 항목
엔비디아 비중
연간 비용
위험등급
판매 가능 여부

결과
3개 모두 데이터 검증 완료
```

민감하거나 긴 결과는 요약만 표시한다.

### 안전 점검

```text
✅ 상품 수치 출처 확인
✅ 판매 가능 상품 확인
✅ 투자권유 표현 없음
✅ 수익보장 표현 없음
✅ 데이터 기준일 표시
◻ 투자성향 초과 안내 해당 없음
```

정미숙 AI 펀드 검색:

```text
⚠ 투자성향 초과 안내 적용
```

---

# 14. UI와 Agent의 데이터 계약

Agent는 UI 문구와 HTML을 직접 생성하지 않는다.

Agent는 구조화된 결과를 반환하고, UI가 이를 렌더링한다.

권장 최종 State 또는 응답 DTO:

```python
class AgentTurnResult(TypedDict):
    answer: str

    action: str
    action_reason_code: str
    action_reason_summary: str

    search_slots: dict
    current_candidates: list[dict]
    selected_funds: list[str]

    comparison: dict | None
    overlap_result: dict | None

    quick_actions: list[dict]
    safety_result: dict

    trace_events: list[AgentUIEvent]
```

상품 후보 예시:

```json
{
  "fund_code": "F001",
  "fund_name": "글로벌 반도체 리더스 펀드",
  "risk_grade": "높은위험",
  "annual_fee": 0.58,
  "matched_metrics": [
    {
      "label": "엔비디아 비중",
      "value": 14.2,
      "unit": "%"
    }
  ],
  "selection_reason": "엔비디아 편입 비중이 높고 후보 중 연간 비용이 낮은 편",
  "as_of_date": "2026-06-30"
}
```

---

# 15. Mock 모드와 Live 모드

## 15-1. Mock 모드 목적

- 백엔드 완성 전 UI 개발
- 발표 리허설
- Agent 장애 시 화면 구조 점검

Mock 모드에서도 다음 데이터 계약을 지킨다.

```python
MockAgentAdapter.stream_turn() -> Iterable[AgentUIEvent]
```

단, 화면에 반드시 `MOCK TRACE`라고 표시한다.

## 15-2. Live 모드 목적

- 실제 LangGraph 실행
- 실제 RAG 검색
- 실제 Tool 호출
- 실제 State 변경
- 실제 안전성 검사 결과 표시

설정 예시:

```text
AGENT_MODE=live
```

환경변수가 없거나 Agent 연결에 실패했다고 자동으로 Mock 결과를 실제처럼 보여주지 않는다.

권장 처리:

```text
LIVE AGENT 연결 실패
→ 오류 안내
→ 사용자가 명시적으로 'Mock 모드로 전환' 선택
```

---

# 16. Streamlit 상태 관리 주의사항

Streamlit은 버튼 클릭 때마다 스크립트를 다시 실행하므로 다음을 반드시 `st.session_state`에 보관한다.

- 대화 메시지
- 현재 페르소나
- 현재 화면
- thread ID
- Agent mode
- 후보 상품
- 검색 조건
- Trace 이벤트
- 비교 대상
- Trace 표시 여부

버튼 클릭 후 같은 메시지가 중복 실행되지 않도록 `pending_prompt`를 처리한 뒤 즉시 제거한다.

```python
prompt = st.session_state.pop("pending_prompt", None)
```

페르소나 변경 시 기존 thread를 재사용하지 않는다.

---

# 17. 오류 및 Fallback 화면

## 검색 결과 0건

```text
말씀하신 조건을 모두 충족하는 판매 가능 상품을 찾지 못했어요.
조건 하나를 완화해서 다시 살펴볼까요?
```

선택:

- 비용 조건 완화
- 관심 종목 대신 관련 테마로 확장
- 검색 조건 다시 정하기

Trace에는 다음을 표시한다.

```text
SEARCH_EMPTY
→ RELAX_CONDITION 제안
```

## Tool 오류

고객 화면:

```text
상품의 최신 수치를 확인하는 중 문제가 발생했어요.
확인되지 않은 수치를 제외하고 탐색 결과만 보여드릴게요.
```

Trace:

```text
fund_detail_tool · ERROR
Fallback: unverified metrics hidden
```

## LLM 구조화 출력 오류

- 1회 재시도
- 계속 실패하면 `ASK` fallback
- Trace에 retry 발생 표시

## Agent 전체 오류

- 고객 화면에 기술적인 stack trace를 노출하지 않음
- 발표자 Trace 패널에 짧은 오류 코드 표시
- 데모 영상으로 전환할 수 있도록 앱 외부에 영상 준비

---

# 18. 권장 파일 구조

```text
fund-guide-demo/
├── app.py
├── pages/
│   ├── fund_home.py
│   └── chat_demo.py
├── ui/
│   ├── styles.py
│   ├── chat_components.py
│   ├── fund_cards.py
│   ├── comparison.py
│   ├── overlap.py
│   └── trace_panel.py
├── agent/
│   ├── adapter.py
│   ├── mock_adapter.py
│   ├── langgraph_adapter.py
│   ├── event_mapper.py
│   └── schemas.py
├── graph/
│   ├── builder.py
│   ├── state.py
│   ├── nodes.py
│   └── router.py
├── tools/
│   ├── fund_search.py
│   ├── fund_detail.py
│   ├── compare.py
│   ├── overlap.py
│   └── safety.py
├── rag/
│   ├── retriever.py
│   └── vectorstore/
├── data/
│   ├── personas.json
│   ├── funds.json
│   └── guides.json
├── assets/
│   ├── fund_submain.png
│   └── logo.png
├── tests/
│   ├── test_event_mapper.py
│   ├── test_demo_scenarios.py
│   └── test_safety.py
├── .streamlit/
│   └── config.toml
├── requirements.txt
└── README.md
```

앱 규모가 작다면 `pages/`를 사용하지 않고 `app.py` 안에서 screen 상태를 분기해도 된다. 다만 UI 컴포넌트와 Agent Adapter는 반드시 분리한다.

---

# 19. 구현 순서

## Phase 1 — 화면 골격

1. 펀드 서브메인 캡처 화면
2. AI 플로팅 버튼
3. Chat UI
4. 사이드바 페르소나 선택
5. 상품 카드
6. 비교표
7. 겹침 분석
8. Trace 패널

이 단계는 Mock Adapter로 진행하되 `MOCK TRACE` 배지를 표시한다.

## Phase 2 — Agent 데이터 계약

1. `AgentUIEvent` 정의
2. `AgentTurnResult` 정의
3. `AgentAdapter` Protocol 정의
4. Mock Adapter를 새 계약에 맞춰 리팩터링
5. UI가 Adapter 종류를 몰라도 렌더링되도록 구성

## Phase 3 — 실제 LangGraph 연결

1. 고객 프로필과 thread ID 전달
2. 실제 graph streaming 연결
3. State update → UI event 변환
4. RAG 검색 이벤트 연결
5. Tool 호출 이벤트 연결
6. 안전성 검사 결과 연결
7. 최종 응답 token streaming 연결
8. `LIVE AGENT` 배지 전환

## Phase 4 — 시연 안정화

1. 메인 3턴 시나리오 반복 테스트
2. 정미숙 AI 펀드 시나리오 테스트
3. 새 세션 재실행 테스트
4. API 오류 fallback 테스트
5. 화면 크기 테스트
6. 데모 영상 녹화

---

# 20. 핵심 시연 시나리오

## 시나리오 A — 최준혁

### Turn 1

사용자:

> 엔비디아 많이 들어가고 비용 낮은 펀드 찾아줘.

기대 Agent 동작:

```text
intent = fund_search
slots = {holding_stock: NVDA, fee_preference: low}
action = search
question_count = 0
```

기대 Trace:

```text
질문 의도 파악
→ 조건 추출
→ SEARCH 선택
→ RAG 검색
→ 정형 데이터 검증
→ 안전성 검사
→ 후보 3개 응답
```

### Turn 2

사용자:

> 1번과 3번 비교해줘.

기대 Agent 동작:

```text
현재 후보를 State에서 불러옴
→ action = compare
→ fund_compare_tool 호출
```

핵심 증명:

- 상품명을 다시 입력하지 않아도 이전 후보를 기억
- 멀티턴 State 관리

### Turn 3

사용자:

> 나 엔비디아 직접 갖고 있는데 얼마나 겹쳐?

기대 Agent 동작:

```text
고객 보유종목 조회
→ 선택/직전 펀드 확인
→ overlap_tool 호출
→ 중복 종목과 펀드 내 편입 비중 계산
```

핵심 증명:

- 고객 프로필 활용
- 코드 기반 계산
- 판단이 아닌 사실 제공

## 시나리오 B — 정미숙

사용자:

> 요즘 AI 펀드 어때요?

기대 Agent 동작:

```text
AI 테마 검색
→ 후보 위험등급 검증
→ 투자성향 범위 비교
→ safety_context = profile_risk_exceeded
→ 추가 안내
```

핵심 증명:

- 후보를 차단하지 않음
- 기본 상품정보는 동일
- 고객에게 필요한 추가 위험 맥락 제공

---

# 21. 완료 조건

다음 조건이 모두 충족되면 시연 화면 구현 완료로 판단한다.

## 고객 경험

- [ ] 펀드 서브메인에서 AI 버튼을 눌러 Chat UI로 이동한다.
- [ ] 페르소나별 오프닝과 빠른 시작이 달라진다.
- [ ] 현재 탐색 조건이 멀티턴으로 유지된다.
- [ ] 상품 검색 결과가 카드로 표시된다.
- [ ] 번호 기반 비교가 작동한다.
- [ ] 보유종목 겹침 결과가 표시된다.
- [ ] 정미숙에게 성향 초과 안내가 표시된다.

## 실제 Agent 연결

- [ ] LIVE 모드의 Trace가 실제 LangGraph 실행 이벤트에서 생성된다.
- [ ] 노드 실행 순서가 화면에 표시된다.
- [ ] State 변경이 탐색 노트에 반영된다.
- [ ] Retriever 결과가 검색 근거 탭에 표시된다.
- [ ] Tool 호출이 Tool 실행 탭에 표시된다.
- [ ] Safety 결과가 안전 점검 탭에 표시된다.
- [ ] 모델의 Chain-of-Thought는 표시하지 않는다.
- [ ] Mock과 Live 모드가 명확히 구분된다.

## 발표 안정성

- [ ] 시연 코스 버튼이 실제 Agent를 호출한다.
- [ ] 새 세션에서 메인 시나리오가 반복 가능하다.
- [ ] 오류가 고객 화면에 stack trace로 노출되지 않는다.
- [ ] 데이터 기준일이 표시된다.
- [ ] API Key와 개인정보가 코드·화면에 없다.
- [ ] 라이브 시연과 동일한 데모 영상이 준비되어 있다.

---

# 22. 최종 화면의 의도

시연은 다음 순서로 보이게 한다.

1. 실제 펀드 서브메인에 AI 진입점이 추가된 모습을 보여준다.
2. 고객 화면에서 검색 → 비교 → 겹침 분석을 수행한다.
3. `Agent 동작 보기`를 켠다.
4. 같은 대화가 실제로 어떤 노드·State·RAG·Tool을 거쳐 생성됐는지 보여준다.
5. 정미숙 고객으로 전환해 개인화된 위험 맥락을 보여준다.

최종적으로 심사위원이 다음을 이해해야 한다.

> 이 결과는 미리 정해진 챗봇 답변이 아니라, LangGraph가 대화 상태를 유지하고 현재 요청에 맞는 행동과 도구를 선택해 만든 결과다. 동시에 고객에게는 복잡한 기술 구조를 숨기고 자연스러운 펀드 탐색 경험만 제공한다.
