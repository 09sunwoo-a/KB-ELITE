"""CLI 대화 루프 — A5 게이트 확인용. 매 턴 trace를 pretty-print한다.

실행: .venv/bin/python -m app.cli --persona P3
      echo "발화1\n발화2" | .venv/bin/python -m app.cli --persona P3   (스크립트 모드)
명령: :p P1~P4 = 페르소나 전환(새 thread) / :q = 종료
"""

import argparse
import sys
import uuid

from langchain_core.messages import HumanMessage

from app.graph import build_graph
from app.opening import build_opening
from app.personas import PERSONA_LABELS, load_profile


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("--persona", default="P1", choices=list(PERSONA_LABELS))
    args = parser.parse_args()

    graph = build_graph()
    persona_id = args.persona
    thread_id, first_turn = None, True

    def new_session(pid):
        nonlocal persona_id, thread_id, first_turn
        persona_id, thread_id, first_turn = pid, f"{pid}-{uuid.uuid4().hex[:6]}", True
        opening = build_opening(load_profile(pid)["profile"])
        print(f"\n{'=' * 60}\n[세션 시작] {PERSONA_LABELS[pid]}  (thread {thread_id})")
        print(f"\n길잡이: {opening['text']}")
        print(f"빠른 시작: {' · '.join(opening['chips'])}\n")

    new_session(persona_id)

    for line in sys.stdin if not sys.stdin.isatty() else iter(lambda: input("고객 > "), None):
        text = line.strip()
        if not text:
            continue
        if text == ":q":
            break
        if text.startswith(":p "):
            new_session(text.split()[1])
            continue

        if not sys.stdin.isatty():
            print(f"고객 > {text}")
        payload = {"messages": [HumanMessage(content=text)]}
        if first_turn:
            payload.update(load_profile(persona_id))
            first_turn = False
        config = {"configurable": {"thread_id": thread_id}}

        before = len(graph.get_state(config).values.get("trace", [])) \
            if graph.get_state(config).values else 0
        state = graph.invoke(payload, config)

        print("  ┌─ trace " + "─" * 46)
        for e in state["trace"][before:]:
            print(f"  │ [{e['node']:11}] {e['summary']}")
        turn = state.get("turn", {})
        conds = turn.get("conditions") or {}
        if conds:
            print(f"  │ [탐색 기준  ] {conds}")
        print("  └" + "─" * 54)
        print(f"\n길잡이: {turn.get('answer', '')}")
        if turn.get("candidates"):
            for i, c in enumerate(turn["candidates"], 1):
                print(f"   [카드{i}] {c['name'][:38]} | {c['risk_grade']} | "
                      f"fee {c['fee_pct']}% | {c['matched_stocks']} | {c['as_of']}")
                print(f"          근거: {c['selection_reason']}")
        if turn.get("comparison"):
            comp = turn["comparison"]
            print(f"   [비교표] {comp['labels']}")
            for row in comp["rows"]:
                print(f"          {row['label']}: {row['values']}")
        if turn.get("overlap"):
            for ov in turn["overlap"]:
                if ov.get("available"):
                    print(f"   [겹침] {ov['fund_name'][:30]}: {ov['overlap_stocks']} ({ov['basis']}, {ov['as_of']})")
                else:
                    print(f"   [겹침] {ov.get('fund_name', ov['fund_code'])}: 보유종목 정보 비공개")
        if turn.get("risk_block"):
            print(f"   [차단] {turn['risk_block']}")
        print(f"   후속 칩: {' · '.join(turn.get('chips', []))}\n")


if __name__ == "__main__":
    run()
