# 04. Streamlit 시연 UI 설계 — 펀드 길잡이 에이전트

> **문서 목적**: 발표용 Streamlit 시연 사이트의 화면 구조, UI↔Agent 데이터 계약, trace 렌더링을 정의한다. 이 문서는 **백엔드 세션(app/)과 프론트 세션(ui/)의 계약서**다. 두 세션은 이 문서의 스키마(6장)를 기준으로 독립 작업한다.
> **상위 문서**: 01(페르소나·오프닝·칩·시연 시나리오), 02(그래프 구조·State·trace), 03(데이터 스키마·계산 한계).
> **원본 기획안**: `AI_펀드_길잡이_Streamlit_시연화면_기획안.md`를 기반으로 하되, 02·03과 충돌하는 부분을 0장 기준으로 조정했다. 충돌 시 **이 문서가 우선**한다.

---

## 0. 기획안 대비 조정 사항 (Claude Code는 이 조정을 준수한다)

| # | 기획안 | 조정 | 사유 |
|---|---|---|---|
| 1 | 11개 노드 trace (`understand_turn`, `retrieve_fund_docs`, `validate_fund_data` 등) | **02의 실제 6노드**(router / explain / ask / search / compare / postprocess) + 노드 내 도구 호출 이벤트 | trace는 실제 실행의 증명이다. 존재하지 않는 노드명을 표시하면 자기모순 |
| 2 | 행동 5종(겹침 분석 포함) | **행동 4종**. 겹침은 compare(또는 search 후속) 노드 안의 `match_overlap` 도구 호출로 trace에 표시 | 02 4장 |
| 3 | 후보 카드 "엔비디아 비중 14.2%", 겹침 "펀드 내 비중" 막대 | **종목 비중 표시 불가** → 카드는 `엔비디아 포함` 매칭 뱃지, 겹침은 겹치는 종목명 리스트 + 한계 고지 문구 | 03 4장: stocks_raw는 비중 없는 종목명 문자열. `match_overlap`은 종목명 리스트만 반환 |
| 4 | `fund_detail_tool`, `validate_fund_data`(수치 검증 단계) | 없음. 수치는 처음부터 funds.json에서 코드가 조립(03 장치 ①). postprocess의 수치 대조(03 장치 ③)가 검증 역할 | 03 6장 |
| 5 | `graph/`, `tools/`, `rag/`, `pages/` 파일 구조 | **02 10장의 `app/` 구조 유지**. UI만 `ui/` 아래 세분화(9장) | 세션 간 소유권 경계 유지 |
| 6 | 최종 답변 token streaming | 노드 단위 진행 표시 + **완성된 answer의 문자 단위 타자기 연출**(사용자 결정 2026-07-17). Live의 실제 LLM token 스트림 연결은 P2 유지 | 챗봇다운 체감. 표시되는 문장은 postprocess를 통과한 완성본이므로 연출이 정합성에 영향 없음 |
| 7 | reason_code 체계(`ENOUGH_SEARCH_CONDITIONS` 등) | 코드 enum 대신 **`action_reason` 한 문장**(라우터 structured output에 필드 추가 — 02 RouteResult 소폭 수정) | 표시 목적에는 문장이면 충분, enum 관리 비용 절감 |
| 8 | 성향 초과 후보를 노출하고 안내 문구 표시(기획안 10장) | **성향 초과 상품은 노출 자체를 차단**(01 4-2 하드 필터). 차단 안내 박스 + 대안 버튼으로 대체(4-7) | 사용자 결정(2026-07-17): 투자성향은 가입 가능 위험등급의 상한 |

채택 유지: AgentAdapter(Mock/Live) 분리, MOCK/LIVE 배지 정직성, trace 노출 금지 목록, 화면 1(서브메인+플로팅 버튼), 시연 코스 버튼의 실제 Agent 호출, 사이드바 조종석, 오류 fallback, `pending_prompt` 패턴.

## 1. 핵심 원칙

1. **고객 화면이 주인공이다.** trace 패널은 챗 화면 옆에 상시 표시되는 보조 화면이다(사용자 결정 2026-07-18: 토글 없이 항상 켜짐).
2. **Live 모드의 trace는 실제 LangGraph 실행에서 생성된 State의 `trace` 필드만 렌더링한다.** UI가 문구를 지어내지 않는다.
3. **Mock을 실제처럼 위장하지 않는다.** Mock 모드는 항상 `MOCK TRACE` 배지, Live는 `LIVE AGENT` 배지를 표시한다. Live 연결 실패 시 자동으로 Mock으로 위장 전환하지 않고, 오류 안내 후 사용자가 명시적으로 전환한다.
4. **상품 수치는 LLM 텍스트가 아니라 코드가 조립한 카드로 표시한다**(03 장치 ①). LLM 응답(answer)은 서술만 담당한다.
5. **trace 노출 금지**: 모델 내부 사고과정(CoT), 시스템 프롬프트 원문, API Key, 고객 식별자 원문, 임베딩 벡터, RAG CONTENT 원문 전체.
6. 시연 대본 입력(빠른 시작 칩 포함)도 고정 응답이 아니라 실제 `AgentAdapter`를 통과한다.

## 2. 화면 구조 — 2 스크린

멀티페이지 대신 `st.session_state.screen` 분기 (`"fund_home"` | `"chat"`).

### 화면 1 — 스타뱅킹 펀드 서브메인 (`fund_home`)

목적: 별도 실험용 챗봇이 아니라 **기존 펀드 고객 여정에 들어가는 기능**임을 보여준다.

- 중앙 스마트폰 프레임(폭 390~430px, 높이 720px+), `assets/fund_submain.png` 캡처를 배경으로 사용. 이미지 없으면 단순 목업 fallback.
- 캡처는 개인정보 제거본만 사용(이름·계좌·잔액·내부 메뉴·서버 주소). 하단에 `Prototype · 실제 스타뱅킹 화면 기반 시연` 표기.
- 우측 하단 `AI 펀드 길잡이` 플로팅 버튼 + 말풍선 "어떤 펀드를 봐야 할지 막막하신가요?"
- 클릭 시: `screen="chat"`, 선택 페르소나 프로필 로드, 새 thread_id 발급, `build_opening()` 결과 표시.

### 화면 2 — Chat UI (`chat`)

채팅도 화면 1과 동일한 **스마트폰 프레임 안**에서 진행한다(모바일 여정 연속성 — 사용자 결정 2026-07-17). **두 화면의 프레임 규격은 410×812px로 완전 동일 고정**이며, 칩·조건바 등 내용 변화가 프레임 크기에 영향을 주지 않는다(메시지 영역만 유동, 사용자 결정 2026-07-18). 룩앤필은 iMessage/ChatGPT 톤(흰 배경, 회색 봇·파란 사용자 말풍선). 프레임 내부는 일반적인 AI 챗 UI 구성을 따른다:

1. 대화 헤더(아바타 · `AI 펀드 길잡이` · 고객 컨텍스트 서브라인 — §4-0의 프로필 스트립 역할)
2. 현재 탐색 기준 칩바(§4-2)
3. 스크롤 메시지 영역(고정 높이, 새 메시지 도착 시 하단 자동 스크롤)
4. 빠른 시작/후속 칩(입력창 위)
5. 입력창(프레임 하단 인라인)

폰 프레임 옆에는 trace 컬럼이 항상 열려 있다(사용자 결정 2026-07-18 — 토글 제거):

```python
chat_col, trace_col = st.columns([1.6, 1.0])   # chat_col 안에 폰 프레임
```

## 3. 사이드바 — 고객 시나리오 패널 (2026-07-18 개편: "시연 조종석" 헤더 제거)

발표자 전용. 목적: **"이런 배경의 고객이 로그인하면 → 개인화가 이렇게 진행된다"의 인과를 상시 보여준다.** 위에서부터:

1. **고객 시나리오 선택** (라디오 + 한 줄 배경 캡션): **`app.personas.DEMO_PERSONAS` 2인만 노출** (2026-07-18 확정) — 최준혁(42)·공격투자형 / 서지우(26)·안정추구형. 라벨은 `이름 (나이) · 투자성향`, 캡션은 01 §6 한 줄 소개. 박서연·정미숙은 테스트 데이터로만 유지.
   변경 시 초기화: messages, thread_id, trace_events, last_candidates, 오프닝·칩 재생성. **기존 thread 재사용 금지.**
2. **🏦 은행이 이미 아는 고객 정보** 카드: 투자성향(노출 상한) / 투자방식 / 관심분야 / 보유 요약.
2-1. **✨ 그래서 에이전트는 이렇게 달라져요** 카드: 이 배경이 만드는 개인화 3가지(오프닝 강조점 / 칩 소재 / 노출 상한, 01 §6 시연 하이라이트 기반) + "개인 데이터 복창·선제 권유 없음" 주석.
3. ~~시연 코스 버튼~~ (사용자 결정 2026-07-18 제거 — 시연은 빠른 시작 칩과 직접 입력으로 진행한다.
   시연 대본은 01 §7-2 (2인 코스, 2026-07-18 확정·같은 날 개정 4턴→3턴):
   **최준혁 3턴** — ① `엔비디아 들어간 펀드 중에 수수료 낮은 걸로 몇 개만 보여줘` ② `1번이랑 3번은 뭐가 달라?`
   ③ `그래서 뭘 사는 게 제일 나아?` (겹침 분석은 시연 코스 제외 — 기능·테스트로 유지)
   **서지우 5턴** — ① `월급 받으면 그냥 파킹통장에 두는데 좀 아까워서요` ②③ [후속 칩 클릭: 5년 이상 → 큰 변동 회피]
   ④ `첫 번째 건 비용이 많이 들어요? 매달 20만원씩 넣으면요?` ⑤ `친구가 요즘 AI 펀드 좋다던데 저도 살 수 있어요?`
   **교차** — 최준혁 상태에서 `요즘 AI 펀드 어때요?` (전 상품 노출 vs 서지우 차단))
4. **대화 초기화** / **펀드 화면으로 돌아가기** (trace 패널은 상시 표시 — 토글 없음)
5. 사이드바는 **고정형**(접기 버튼 숨김 — 사용자 결정 2026-07-18)
6. **모드 표시**: `LIVE AGENT` 또는 `MOCK TRACE` 배지(패널 상단에도 중복 표시).

## 4. Chat UI 컴포넌트

### 4-0. 고객 프로필 스트립 (개인화 가시화 — 2026-07-17 추가)

채팅 상단에 로그인 고객 기준의 개인화 컨텍스트를 상시 표시한다: `이름 · 투자성향 · 가입 가능 위험등급 상한 · "성향 초과 상품은 후보로 노출되지 않아요"`. 노출 규칙(01 4-2)이 이 고객에게 어떻게 적용되는지를 시연 내내 보여주는 장치다. 값은 프로필(테스트 데이터)에서 오며, 런타임이 페르소나 ID로 분기하는 것은 아니다.

### 4-1. 오프닝 + 빠른 시작 칩

- 세션 시작 시 `build_opening(profile)`(02 8장 — 2026-07-18 개정: 능력 소개 본문은 LLM 동적 생성+코드 검증·폴백) 결과를 첫 assistant 메시지로 표시.
- 캐시·프리페치 없음(2026-07-18 사용자 결정 — 매 진입 새로 생성, 2~3초 감수). 생성 동안 타이핑 인디케이터로 "고객 프로필을 확인하고 첫인사를 준비하고 있어요"를 표시하고, trace 패널에 오프닝 생성 로그(신호 추출→LLM 생성→검증 통과/폴백)를 하나의 이벤트로 기록한다.
- 칩 3개는 버튼. 명칭은 `빠른 시작`(`추천 질문` 금지 — 01 5-5). 클릭 시 문구가 사용자 메시지로 전송.
- 매 턴 응답 후에는 `AgentTurnResult.chips`를 후속 칩으로 표시 (2026-07-18 개정 — 02 §7-2 ④: 탐색·설명·비교 턴은 LLM 동적 생성 2개+코드 검증, 질문·차단·0건 턴은 규칙 기반 3개. UI는 개수 가정 없이 리스트를 그대로 렌더).

### 4-2. 현재 탐색 기준 (조건 칩바)

- State `conditions`를 고객 언어로 변환해 채팅 상단에 고정 표시: `[관심 종목: 엔비디아] [비용: 낮은 편] [기간: 5년 이상]`
- 조건이 하나도 없으면 영역 숨김. 1차 범위는 **조회 전용**(수정 UI 없음).

### 4-3. 처리 상태

- Agent 실행 중 노드 단위 진행 문구를 갱신: router → "질문을 이해하고 있어요", search → "관련 펀드를 찾고 있어요", postprocess → "표현과 수치를 점검하고 있어요". 메신저형 타이핑 인디케이터(점 3개)와 함께 표시.
- **고정 타이머 연출 금지.** 실제 stream 이벤트 도착 시점에 갱신한다.
- `turn_completed` 수신 후 answer 서술은 문자 단위 타자기 효과로 표시한다(조정 #6). 표시 문장은 이미 postprocess를 통과한 완성본이다.

### 4-4. 후보 카드 (search 결과)

`AgentTurnResult.candidates`를 카드 2~4개로 렌더링. **모든 수치는 funds.json 유래 값**(6-3 스키마).

```text
① 피델리티 미국 증권 자투자신탁(주식-재간접형) Ce
   [주식형] [다소높은위험] [엔비디아 포함 ✓]   ← matched_stocks 뱃지
   운용사        피델리티자산운용
   지역          미국
   연간 비용     0.66%
   12개월 수익률  8.71%  (2026-06-30 기준)
   주요 보유종목  엔비디아, 마이크로소프트, 알파벳(구글)
   선정 근거     엔비디아를 주요 종목으로 담고 있고, 후보 중 연간 비용이 낮은 편
   기준일 2026-06-30
```

표시 원칙:
- 카드에는 12개월 수익률·주요 보유종목·운용사를 기본 표시한다(사용자 결정 2026-07-18 — 비교표 수준의 메타를 카드에서 바로 확인). 수익률은 반드시 기준기간·기준일 병기, 다른 기간은 요청 시 교체 표시. 미래 수익을 암시하는 표현 금지.
- 결측 필드는 `정보 없음`(예: `has_holdings_info=false`면 "주요 보유종목 정보가 공개되지 않은 상품").
- 종목별 편입 비중은 데이터에 없으므로 **표시하지 않는다**(조정 #3).
- 성향 초과 상품은 카드로 노출되지 않는다(01 4-2 하드 필터). 차단이 발생한 턴은 4-7의 안내 박스로 표시.

### 4-5. 비교표 (compare 결과)

`AgentTurnResult.comparison`을 `st.dataframe` 또는 markdown 표로 렌더링. 행: 유형 / 지역 / 위험등급 / 연간 비용 / 12개월 수익률(기준기간 병기) / 주요 보유종목(문자열 요약) / 기준일. 표 위에 LLM의 차이 요약 서술(answer). 우열·추천 표현은 postprocess가 차단.

### 4-6. 겹침 분석 결과

`AgentTurnResult.overlap` 렌더링:

```text
공개된 상위 보유종목 기준으로, ①번 펀드는 고객님이 직접 보유한
종목 중 2개(엔비디아, 테슬라)를 담고 있어요.

겹치는 종목:  엔비디아 ✓   테슬라 ✓

※ 2026-06-30 공개된 주요 보유종목 기준이며, 펀드 내 편입 비중과
  전체 포트폴리오 중복률은 공개 데이터에 없어 계산하지 않습니다.
```

- 종목별 비중 막대·중복률 % 계산 **금지**(데이터 없음). `available=false`면 "이 상품은 보유종목 정보가 공개되지 않아 비교할 수 없어요".

### 4-7. 성향 초과 차단 안내 박스

`risk_block`이 존재하는 턴에는 postprocess가 삽입한 차단 안내(제외 사실·사유)를 경고 박스로 표시한다.

- **전부 차단**(`blocked=true`): 후보 카드 없이 안내 박스만 표시하고, 대안 버튼 2개를 후속 칩으로 제공 — `가입 가능한 범위에서 찾아보기` / `이전 후보로 돌아가기`
- **일부 차단**(`excluded_by_risk > 0`): 카드 아래에 "조건에 맞는 상품 중 n건은 투자성향 범위를 초과해 제외했어요"를 표시

## 5. Trace 패널 (상시 표시)

### 5-1. 구성 (위→아래)

1. **배지**: `● LIVE AGENT` 또는 `● MOCK TRACE` (항상 표시)
2. **현재 행동**: State의 `action` + `action_reason` — 예: `SEARCH — 관심 종목과 비용 조건이 명확해 추가 질문 없이 검색합니다.`
3. **실행 흐름**: **고정 토폴로지 다이어그램**(2026-07-18 개선) — 6노드 전체를 항상
   그려두고(`router` → 분기 4노드 → `postprocess`), 이번 턴에 실행된 노드만 강조,
   선택되지 않은 분기는 흐리게 표시한다. "라우터가 4가지 행동 중 하나를 **선택**했다"가
   화면에서 보이는 것이 목적이다.
   턴 실행 중에는 어댑터의 `node_started` 이벤트를 받아 **실시간으로 갱신**한다 —
   완료 노드 `✓`, 진행 중 노드는 점멸 강조, 아직 시작 전인 `postprocess`는 `○` 대기.
   이 동안 trace 패널은 배지+실시간 흐름만 표시하고(세부 탭 없음), 턴 완료 후 rerun되면
   아래 사후 구성(행동 → 흐름 → 탭 4개)으로 전환된다.

| 내부 노드 (02 실제) | 화면 표시명 (다이어그램 분기 칸은 축약명) |
|---|---|
| `router` | 질문 의도 파악·행동 선택 |
| `explain` | 용어 설명 준비 (축약: 용어 설명) |
| `ask` | 확인 질문 준비 (축약: 확인 질문) |
| `search` | 관련 펀드 탐색 (축약: 펀드 탐색) |
| `compare` | 후보 상품 비교 (축약: 후보 비교) |
| `postprocess` | 표현·수치 안전 점검 |

```text
┌ ✓ 질문 의도 파악·행동 선택 ┐
│ 용어설명 확인질문 [✓펀드탐색] 후보비교 │   ← 실행된 분기만 강조, 나머지 흐림
└ ✓ 표현·수치 안전 점검 ┘
```

도구 호출(`search_funds`, `calc_annual_cost`, `match_overlap`)은 노드가 아니라 다이어그램 아래 `└ 🔧 요약` 목록으로 표시한다.

4. **세부 탭 4개**: `[탐색 노트] [검색 근거] [도구 실행] [안전 점검]`

### 5-2. 세부 탭 내용 (trace entry의 `detail`을 렌더링)

- **탐색 노트**: conditions·후보 코드·ask_streak·직전 행동을 고객 언어 라벨로 표시. 원본 State JSON은 `원본 State 보기` expander에만.
- **검색 근거**: 정형 필터 통과 건수 → (벡터 사용 시) 질의문·상품코드·유사도 상위 k → 채택/제외 및 제외 사유(성향 범위 제외 n건, 보유종목 정보 없음 제외 n건). 정형 정렬로 종결된 경우 "벡터 검색 미사용 — 정형 필터+정렬로 종결"을 그대로 표시(발표 논거: RAG를 쓰되 필요한 곳에만).
  벡터 랭킹 턴은 detail의 `scores`(후보별 코사인 유사도, 2026-07-18 추가)를 **후보별 가로 막대**로 표시한다 — 막대 폭은 절대 스케일(0~1, 상대 확대 금지: 수치 정직성), 값 병기. 임베딩 벡터 원문은 표시하지 않는다(§1-5).
- **도구 실행**: 도구명 / 민감정보 없는 입력 요약 / 결과 요약.
- **안전 점검**: postprocess 체크리스트 —

```text
✅ 금칙 표현 검사 (치환 0건)          ← 치환 발생 시 "⚠ 1건 치환" + 원문→치환문 diff
✅ 수치 대조 (불일치 0건)
✅ 고지 문구 삽입
⚠ 성향 초과 상품 4건 노출 차단        ← excluded_by_risk > 0 또는 blocked인 턴
```

  개입이 발생한 턴은 **before→after diff**로 표시한다(2026-07-18 추가) — 금칙 치환은
  `범주 · ~~원문~~ → 치환문`, 수치 교정은 근거 없는 수치와 치환된 문장. 데이터는
  postprocess trace detail의 `banned`(category/found/replaced)·`numeric`(found/sentence)이다.
  하단에 **후속 칩 파이프라인**(2026-07-18 추가)을 표시한다 — detail의
  `chips_source`·`chips_drop_reason`으로 `LLM 생성 → 코드 검증 → 채택` /
  `검증 실패(사유) → 규칙 폴백` / `규칙 기반(질문·차단·0건 턴)` 3가지 경로를 단계 배지로 그린다.

금칙어 치환·수치 대조 경고가 발생한 턴은 **그대로 보여준다**(시연 포인트: "LLM이 실수해도 코드가 막는다").

## 6. UI ↔ Agent 데이터 계약 (두 세션의 공통 기준)

### 6-1. AgentAdapter

```python
from typing import Protocol, Iterable

class AgentAdapter(Protocol):
    def stream_turn(
        self, user_message: str, thread_id: str, persona_id: str,
    ) -> Iterable["TurnEvent"]: ...
    # 스트림 마지막 이벤트는 반드시 완성된 AgentTurnResult를 담는다

class MockAgentAdapter:   ...  # 스키마를 준수하는 고정 fixture 반환, MOCK 배지 강제
class LangGraphAgentAdapter: ...  # compiled_graph.stream(..., stream_mode="updates") 소비
```

- Live 구현: `graph.stream({"messages": [...]}, config={"configurable": {"thread_id": ...}}, stream_mode="updates")`를 소비해 노드별 State 갱신을 `TurnEvent`로 변환. 새 thread의 첫 턴에는 adapter가 `load_profile(persona_id)` 결과(profile·max_risk_score)를 State 초기값으로 함께 주입한다(02 2장). 오프닝은 그래프 밖 `build_opening()` 직접 호출(02 8장).
- UI는 adapter 종류를 몰라야 한다. `st.session_state.agent_mode`(`"mock"|"live"`)는 배지 표시에만 사용.

### 6-2. TurnEvent / TraceEntry

```python
class TurnEvent(TypedDict, total=False):
    event_type: Literal["node_started", "node_completed", "turn_completed", "turn_error"]
    node: str                      # router|explain|ask|search|compare|postprocess
    trace: list["TraceEntry"]      # 이 노드가 새로 append한 trace
    result: "AgentTurnResult"      # turn_completed에만 존재

class TraceEntry(TypedDict):       # 02 State.trace의 원소 형식 (02 3장 {"node","detail"}를 구체화)
    node: str
    kind: Literal["route", "tool", "retrieval", "safety", "info"]
    summary: str                   # 패널 한 줄 표시용, 고객 언어
    detail: dict                   # 세부 탭 렌더링용. 노출 가능 데이터만 담는다
```

**백엔드 세션 의무**: 02의 각 노드는 위 형식으로 `trace`에 append한다(02 3장 소폭 구체화). 라우터의 structured output에 `action_reason: str`(한 문장) 필드를 추가한다(조정 #7).

### 6-3. AgentTurnResult

```python
class AgentTurnResult(TypedDict):
    answer: str                    # postprocess 통과한 최종 서술 (수치 카드는 별도)
    action: str
    action_reason: str
    conditions: dict               # State.conditions 스냅샷 → 탐색 기준 칩바
    candidates: list[dict]         # 아래 후보 카드 스키마. search 턴이 아니면 []
    comparison: dict | None        # {"fund_codes": [...], "labels": [...](선택),
                                   #  "rows": [{"label", "values": [...]}]}
    overlap: list[dict] | None     # 펀드별 1항목 (2026-07-18: 복수 펀드 겹침 지원 — dict → list)
                                   # 각 항목: {"available", "fund_code", "fund_name",
                                   #  "overlap_stocks": ["엔비디아", ...], "as_of", "note"}
                                   # (+basis·checked_holdings 등 추가 키 허용, UI는 필수 키만 렌더)
    risk_block: dict | None        # {"excluded_by_risk": int, "blocked": bool}
                                   # 성향 초과 차단 안내 박스(4-7) 렌더링용
    chips: list[str]               # 후속 칩 2~3개 (02 §7-2 ④ — 동적 2 / 규칙 3)
    trace: list[TraceEntry]        # 이번 턴 전체 trace
```

후보 카드 스키마 (**funds.json 필드만 사용**, 03 5장):

```json
{
  "fund_code": "KF04001379",
  "name": "피델리티 미국 증권 자투자신탁(주식-재간접형) Ce",
  "fund_type": "주식형",
  "region": "미국",
  "risk_grade": "다소높은위험",
  "fee_pct": 0.662,
  "manager": "피델리티자산운용",
  "matched_stocks": ["엔비디아"],
  "top_stocks_summary": "엔비디아, 마이크로소프트, 알파벳(구글)",
  "returns_display": {"period": "12개월", "value": 8.71},
  "selection_reason": "엔비디아를 주요 종목으로 담고 있고 후보 중 연간 비용이 낮은 편",
  "as_of": "2026-06-30"
}
```

- `returns_display`: **기본 12개월**을 채워서 반환한다(사용자 결정 2026-07-18). 다른 기간 요청 시 해당 기간으로 교체. `null`이면 카드에서 해당 행 생략.
- `manager`: 결측(운용사 null 1건)이면 `null` → 카드에서 행 생략.
- `top_stocks_summary`: stocks_raw를 alias 사전으로 한글 병기한 요약 문자열(코드 생성). `has_holdings_info=false`면 `null` → "주요 보유종목 정보가 공개되지 않은 상품"으로 표시.
- `selection_reason`은 정형 근거(fee_quartile, 매칭 종목, risk_score)로 코드가 생성한다. LLM 생성 아님.
- **(백엔드 A 세션 확인 필요)** 2026-07-18 스키마 확장: `manager`·`top_stocks_summary` 추가, `returns_display` 기본 채움 — search/compare 노드의 candidates 조립(`tools._make_card`)에 반영할 것. **반영 전까지는 `LangGraphAgentAdapter`가 funds.json에서 임시 보강한다** (수치 단일 출처 동일, 백엔드 반영 시 어댑터 보강은 자동 무시됨).

### 6-4. Session State 보관 목록

```python
st.session_state: screen, persona_id, thread_id, agent_mode,
                  messages, conditions, last_candidates, trace_events, pending_prompt
```

- 버튼 클릭 중복 실행 방지: `prompt = st.session_state.pop("pending_prompt", None)` 처리 후 즉시 제거.

## 7. Mock 모드 fixture

- 시연 코스 ①~④ 입력에 대응하는 `AgentTurnResult` fixture 4개를 6-3 스키마 그대로 작성(`ui/mock_fixtures.py`). 데이터 값은 03의 실제 funds.json 예시 수준으로 현실적으로.
- 그 외 입력에는 "Mock 모드에서는 시연 코스 버튼을 사용해 주세요" 고정 응답.
- Live 전환: 환경변수 `AGENT_MODE=live` + `app.graph` import 성공 시. 실패 시 오류 안내 → 사용자가 명시적으로 Mock 전환(1장 원칙 3).

## 8. 오류·Fallback

| 상황 | 고객 화면 | trace |
|---|---|---|
| 검색 0건 | "조건을 모두 충족하는 상품을 찾지 못했어요. 조건 하나를 완화해 볼까요?" + 완화 칩(비용 완화/테마 확장/조건 재설정) | `SEARCH_EMPTY → 완화 제안` |
| structured output 실패 | 1회 재시도 → 실패 시 ask로 fallback | retry 표시 |
| 도구 오류 | "수치 확인 중 문제가 발생해, 확인된 정보만 보여드릴게요" | `tool · ERROR + fallback` |
| Agent 전체 오류 | stack trace 노출 금지, 짧은 안내만 | 오류 코드 표시 |

발표 보험: 라이브 시연과 동일한 데모 영상을 별도 준비(앱 외부).

## 9. 파일 구조 (02 10장에 UI 세분화 반영 — 세션 B 소유 범위)

```
ui/
  streamlit_app.py     # 진입점, screen 분기, 사이드바
  adapter.py           # AgentAdapter Protocol, MockAgentAdapter, LangGraphAgentAdapter
  mock_fixtures.py     # 시연 코스 4개 fixture
  components.py        # 후보 카드·비교표·겹침·조건 칩바·성향 초과 박스
  trace_panel.py       # 5장 렌더링
  styles.py            # 폰 프레임·카드 CSS
assets/
  fund_submain.png     # 개인정보 제거 캡처 (없으면 fallback 목업)
```

`app/`, `data/`, `build_data.py`, `tests/`는 백엔드 세션 소유 — UI 세션은 **읽기만** 한다(단, `adapter.py`의 Live 연결부는 백엔드 완성 후 합류 단계에서 연결).

## 10. 구현 순서와 완료 조건

**순서**: ① Mock adapter + 화면 골격(서브메인→챗→카드→비교→겹침→trace 패널) → ② 시연 코스 4개가 Mock으로 end-to-end 동작 → ③ (백엔드 완성 후) Live 연결·배지 전환 → ④ 01 시연 코스 리허설 + 페르소나 전환·재실행 안정성 테스트.

**완료 조건 체크리스트**:
- [ ] 서브메인 → AI 버튼 → Chat 진입, 페르소나별 오프닝·칩 상이
- [ ] 탐색 기준 칩바가 멀티턴 유지, 카드·비교표·겹침 렌더링
- [ ] 서지우 ⑤(AI 질문)에서 성향 초과 차단 안내 + 대안 버튼 표시(후보 카드 없음), 최준혁 동일 질문에서는 정상 후보 노출 (교차)
- [ ] Live trace가 실제 6노드 실행 이벤트에서 생성, 도구 호출·안전 점검 표시
- [ ] Mock/Live 배지 명확 구분, 시연 코스 버튼이 실제 adapter 호출
- [ ] 종목 비중·중복률 등 데이터에 없는 수치가 화면 어디에도 없음
- [ ] API Key·개인정보 하드코딩 없음, stack trace 미노출

## 11. 다음 문서와의 연결

| 이 문서에서 정의 | 사용처 |
|---|---|
| TraceEntry 형식, action_reason 필드 | 02 노드 구현 시 준수 (백엔드 세션) |
| AgentTurnResult·후보 카드 스키마 | 02 행동 노드 결과 조립, 05 수용 기준 |
| Mock fixture 4종 | 세션 B 선행 개발, 05 리허설 |
| 겹침·비중 표시 불가 결정 | 01 v4 4-6·대본에 반영 완료. 05: 대본 기반 수용 기준에 동일 기준 적용 |
