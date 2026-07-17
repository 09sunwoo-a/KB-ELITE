# -*- coding: utf-8 -*-
"""폰 프레임·채팅 말풍선·배지 CSS (04 §9). B2에서 카드 스타일 확장 예정.

레이아웃 원칙 (2026-07-18 사용자 결정):
- 화면 1(서브메인)과 화면 2(챗)의 폰 프레임 규격은 410 x 812px로 완전 동일 고정.
- 챗 내부는 헤더/조건바/입력창 고정, 메시지 영역만 flex로 유동. 칩은 대화 흐름 안.
- 룩앤필: iMessage/ChatGPT 톤 (흰 배경, 회색 봇 말풍선, 파란 사용자 말풍선).
"""

PHONE_W = 410
PHONE_H = 812

CSS = f"""
<style>
/* ---- 앱 공통 ---- */
.stApp {{ background: #F6F4EE; }}
.block-container {{ padding-top: 1.2rem; padding-bottom: 1rem; }}

/* ---- 사이드바 고정형 — 접기 버튼 숨김 (04 §3-5) ---- */
[data-testid="stSidebarCollapseButton"] {{ display: none !important; }}
[data-testid="stSidebar"] {{ min-width: 300px; }}

/* ---- 사이드바 고객 시나리오 카드 ---- */
.sb-card {{
  background: #fff; border: 1px solid #E8E4DA; border-radius: 12px;
  padding: 10px 12px; margin: 8px 0;
}}
.sb-card .sb-title {{
  font-size: 0.72rem; font-weight: 800; color: #8a8272;
  margin-bottom: 7px; letter-spacing: 0.02em;
}}
.sb-row {{ font-size: 0.79rem; color: #4a4437; margin-bottom: 4px; line-height: 1.5; }}
.sb-row b {{ color: #2f2b22; }}
.sb-card.sb-pts {{ background: #FFFBEB; border-color: #F5E6A8; }}
.sb-pt {{
  font-size: 0.78rem; color: #6a5a10; margin-bottom: 6px; line-height: 1.5;
  display: flex; gap: 6px;
}}
.sb-pt .arrow {{ flex: 0 0 auto; font-weight: 800; color: #c9a30a; }}
.sb-note {{ font-size: 0.68rem; color: #a89a5a; margin-top: 6px; }}

/* ---- 모드 배지 ---- */
.mode-badge {{
  display: inline-block; padding: 3px 12px; border-radius: 999px;
  font-size: 0.75rem; font-weight: 700; letter-spacing: 0.04em; white-space: nowrap;
}}
.mode-badge.mock {{ background: #FFF3CD; color: #7a5c00; border: 1px solid #ffe08a; }}
.mode-badge.live {{ background: #D1F0D9; color: #14532d; border: 1px solid #86dba2; }}

/* =========================================================
   채팅 폰 프레임 (화면 2) — 규격 완전 고정 {PHONE_W}x{PHONE_H}
   ========================================================= */
.st-key-chat_phone {{
  width: {PHONE_W}px; margin: 12px auto 0;
  height: {PHONE_H}px !important; flex: 0 0 auto !important;
  background: #FFFFFF; border: 10px solid #1f1f1f; border-radius: 44px;
  box-shadow: 0 18px 44px rgba(0,0,0,.22);
  padding: 0 10px 12px; gap: 0.35rem; overflow: hidden;
}}
/* 메시지 영역만 남는 높이를 전부 차지한다 (프레임 규격 고정의 핵심) */
.st-key-chat_phone > div[data-testid="stLayoutWrapper"]:has(> .st-key-chat_scroll) {{
  flex: 1 1 0 !important; height: auto !important; min-height: 0 !important;
}}
.st-key-chat_scroll {{
  height: 100% !important; min-height: 0 !important; border: none !important;
}}
.st-key-chat_scroll > div {{ border: none !important; }}

/* 대화 헤더 (iMessage 톤) */
.chatbar {{ margin: 0 -10px; flex: 0 0 auto; }}
.chatbar .phone-notch {{ margin-bottom: -14px; }}
.chatbar .cb-row {{
  display: flex; align-items: center; gap: 10px;
  background: #fff; padding: 22px 16px 8px; border-bottom: none;
}}
.chatbar .cb-back {{ font-size: 1.5rem; color: #0A84FF; font-weight: 300; line-height: 1; }}
.chatbar .cb-avatar {{
  width: 36px; height: 36px; border-radius: 50%; flex: 0 0 36px;
  background: linear-gradient(135deg, #FFCC00, #FFE066);
  display: flex; align-items: center; justify-content: center; font-size: 19px;
}}
.chatbar .cb-title {{ font-weight: 700; font-size: 0.95rem; color: #1c1c1e; line-height: 1.25; }}
.chatbar .cb-title small {{ font-weight: 500; font-size: 0.7rem; color: #34C759; }}
.chatbar .cb-sub {{
  background: #fff; border-bottom: 1px solid #ECECEE;
  padding: 2px 16px 8px; font-size: 0.72rem; color: #8E8E93;
}}
.chatbar .cb-sub b {{ color: #48484A; font-weight: 600; }}

/* ---- 말풍선 (iMessage 톤) ---- */
.msg-row {{ display: flex; margin: 8px 0; }}
.msg-row.user {{ justify-content: flex-end; }}
.bubble {{
  max-width: 80%; padding: 9px 14px; border-radius: 18px;
  font-size: 0.9rem; line-height: 1.6; word-break: keep-all;
}}
.bubble.bot {{
  background: #F1F1F3; color: #1c1c1e; border-radius: 18px 18px 18px 4px;
}}
.bubble.user {{
  background: #0A84FF; color: #fff; border-radius: 18px 18px 4px 18px;
}}
.bubble .cursor {{ opacity: .65; animation: blink 0.9s infinite; }}
@keyframes blink {{ 50% {{ opacity: 0; }} }}

/* ---- 타이핑 인디케이터 ---- */
.typing {{ display: flex; align-items: center; }}
.typing .dots {{ display: inline-flex; margin-right: 9px; }}
.typing .dots i {{
  width: 7px; height: 7px; background: #B5B5BA; border-radius: 50%;
  display: inline-block; margin-right: 4px; animation: bounce 1.15s infinite;
}}
.typing .dots i:nth-child(2) {{ animation-delay: .15s; }}
.typing .dots i:nth-child(3) {{ animation-delay: .3s; }}
@keyframes bounce {{ 0%,80%,100% {{ transform: translateY(0); }} 40% {{ transform: translateY(-5px); }} }}
.typing .nlabel {{ color: #8E8E93; font-size: 0.82rem; }}

/* ---- 현재 탐색 기준 칩바 (04 §4-2) — 항상 자리 예약(규격 고정) ---- */
.cond-bar {{
  background: #F7F7F9; border-radius: 10px; padding: 5px 10px;
  font-size: 0.74rem; height: 32px; overflow: hidden; white-space: nowrap;
  flex: 0 0 auto;
}}
.cond-bar.empty {{ visibility: hidden; }}
.cond-bar .cond-title {{ color: #8E8E93; font-weight: 600; margin-right: 6px; }}
.cond-chip {{
  display: inline-block; background: #fff; border: 1px solid #E3E3E8;
  border-radius: 999px; padding: 1px 9px; margin: 0 2px; color: #48484A;
}}

/* ---- 후속 칩(빠른 시작) — 대화 흐름 안, 세로 스택 pill ---- */
div[class*="st-key-chip_"] {{ margin: 0; }}
div[class*="st-key-chip_"] button {{
  border-radius: 999px !important; background: #fff; border: 1px solid #D9D9DE;
  color: #0A84FF !important; font-size: 0.78rem; padding: 3px 14px; min-height: 0;
  white-space: normal; line-height: 1.4; text-align: left;
}}
div[class*="st-key-chip_"] button:hover {{
  border-color: #0A84FF; background: #F0F7FF;
}}
div[class*="st-key-chip_"] button p {{ font-size: 0.78rem !important; color: #0A84FF; }}

/* ---- 후보 카드 (04 §4-4) ---- */
.fund-card {{
  background: #fff; border: 1px solid #E3E3E8; border-radius: 14px;
  padding: 10px 12px; margin: 4px 0; max-width: 90%;
  box-shadow: 0 1px 4px rgba(0,0,0,.05);
}}
.fund-card .fc-name {{ font-weight: 700; font-size: 0.8rem; color: #1c1c1e; line-height: 1.45; }}
.fc-tags {{ margin: 5px 0 6px; }}
.fc-tag {{
  display: inline-block; font-size: 0.66rem; border-radius: 6px;
  padding: 1px 7px; margin: 1px 4px 1px 0; background: #F1F1F3; color: #48484A;
}}
.fc-tag.risk {{ background: #FFF4E5; color: #9a5b00; }}
.fc-tag.match {{ background: #E8F5E9; color: #1b7a2f; font-weight: 600; }}
.fc-row {{ display: flex; justify-content: space-between; gap: 10px; font-size: 0.76rem; padding: 2px 0; }}
.fc-row .k {{ color: #8E8E93; flex: 0 0 auto; }}
.fc-row .v {{ color: #1c1c1e; text-align: right; }}
.fc-row .fc-dim {{ color: #AEAEB2; font-size: 0.66rem; }}
.fc-foot {{ font-size: 0.66rem; color: #AEAEB2; margin-top: 5px; }}
.excl-note {{ font-size: 0.7rem; color: #9a8a4a; margin: 2px 0 4px; }}

/* ---- 비교표 (04 §4-5) ---- */
.cmp-wrap {{
  background: #fff; border: 1px solid #E3E3E8; border-radius: 12px;
  overflow: hidden; margin: 4px 0; max-width: 96%;
}}
.cmp-wrap table {{ width: 100%; border-collapse: collapse; font-size: 0.7rem; }}
.cmp-wrap td {{
  padding: 6px 8px; border-bottom: 1px solid #F1F1F3;
  vertical-align: top; text-align: left; color: #1c1c1e; line-height: 1.45;
}}
.cmp-wrap tr:last-child td {{ border-bottom: none; }}
.cmp-wrap td.lbl {{ color: #8E8E93; white-space: nowrap; width: 84px; background: #FAFAFC; }}

/* ---- 겹침 분석 (04 §4-6) ---- */
.overlap-box {{
  background: #fff; border: 1px solid #E3E3E8; border-radius: 14px;
  padding: 10px 12px; margin: 4px 0; max-width: 90%; font-size: 0.78rem; color: #1c1c1e;
}}
.overlap-box .ov-title {{ font-weight: 700; font-size: 0.78rem; line-height: 1.45; }}
.overlap-box .ov-sub {{ font-size: 0.68rem; color: #8E8E93; margin: 2px 0 6px; }}
.ov-stock {{
  display: inline-block; background: #E8F5E9; color: #1b7a2f; border-radius: 999px;
  padding: 2px 10px; font-size: 0.74rem; font-weight: 600; margin: 2px 4px 2px 0;
}}
.ov-none {{ font-size: 0.74rem; color: #8E8E93; }}
.ov-note {{ font-size: 0.66rem; color: #AEAEB2; margin-top: 6px; line-height: 1.5; }}

/* ---- 성향 초과 차단 안내 박스 (04 §4-7) ---- */
.block-box {{
  background: #FFF8E6; border: 1px solid #F5D98B; border-radius: 14px;
  padding: 10px 12px; margin: 4px 0; max-width: 90%;
  font-size: 0.78rem; color: #7a5c00; line-height: 1.6;
}}
.block-box b {{ color: #5a4400; }}

/* ---- 입력창 (프레임 하단 고정) ---- */
.st-key-chat_phone [data-testid="stChatInput"] {{
  background: #F1F1F3; border: 1px solid #E3E3E8; border-radius: 22px;
}}
.st-key-chat_phone [data-testid="stChatInput"]:focus-within {{ border-color: #0A84FF; }}

/* ---- Trace 패널 (04 §5) ---- */
.tp-action {{
  background: #fff; border: 1px solid #E3E3E8; border-radius: 12px;
  padding: 9px 12px; margin: 8px 0; font-size: 0.82rem; color: #1c1c1e; line-height: 1.55;
}}
.tp-title {{ font-size: 0.76rem; font-weight: 700; color: #8E8E93; margin: 4px 0 2px; }}
.tp-node {{ font-size: 0.84rem; color: #1c1c1e; padding: 2px 0; }}
.tp-tool {{ font-size: 0.76rem; color: #6e6e73; padding: 0 0 2px 18px; }}

/* ---- Trace 실행 흐름 — 고정 토폴로지 다이어그램 (04 §5-1) ---- */
.tp-graph {{ margin: 4px 0 6px; }}
.tpg-node {{
  border: 1px solid #E3E3E8; border-radius: 9px; background: #fff;
  padding: 5px 8px; font-size: 0.78rem; text-align: center;
  color: #1c1c1e; line-height: 1.4;
}}
.tpg-branch {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 4px; }}
.tpg-branch .tpg-node {{ padding: 5px 2px; font-size: 0.72rem; }}
.tpg-conn {{ width: 2px; height: 8px; background: #D9D9DE; margin: 2px auto; }}
.tpg-node.on {{ border-color: #0A84FF; background: #EAF3FF; color: #0A5BD3; font-weight: 700; }}
.tpg-node.run {{
  border-color: #0A84FF; background: #0A84FF; color: #fff; font-weight: 700;
  animation: tpg-glow 1s ease-in-out infinite;
}}
.tpg-node.off {{ color: #b9b9c0; background: #FAFAFB; border-style: dashed; }}
.tpg-node.wait {{ color: #8E8E93; border-style: dashed; }}
.tpg-node.err {{ border-color: #B25000; background: #FFF3E8; color: #B25000; font-weight: 700; }}
@keyframes tpg-glow {{
  0%, 100% {{ box-shadow: 0 0 0 0 rgba(10, 132, 255, .35); }}
  50% {{ box-shadow: 0 0 0 5px rgba(10, 132, 255, .12); }}
}}

/* ---- Trace 검색 근거 — 벡터 유사도 막대 (04 §5-2) ---- */
.tp-score-row {{
  display: flex; align-items: center; gap: 6px;
  font-size: 0.72rem; color: #4a4a4f; padding: 2px 0;
}}
.tp-score-code {{ flex: 0 0 86px; font-family: ui-monospace, monospace; }}
.tp-score-bar {{
  flex: 1 1 auto; height: 8px; background: #EFEFF2;
  border-radius: 4px; overflow: hidden;
}}
.tp-score-bar i {{ display: block; height: 100%; background: #0A84FF; border-radius: 4px; }}
.tp-score-val {{ flex: 0 0 40px; text-align: right; font-variant-numeric: tabular-nums; }}

/* ---- Trace 안전 점검 — 가드레일 diff (04 §5-2) ---- */
.tp-diff {{
  font-size: 0.74rem; line-height: 1.6; padding: 4px 8px; margin: 2px 0;
  background: #FAFAFB; border: 1px solid #ECECF0; border-radius: 8px; color: #3a3a3f;
}}
.tp-diff-cat {{
  display: inline-block; font-size: 0.64rem; font-weight: 700; color: #8E8E93;
  border: 1px solid #E3E3E8; border-radius: 6px; padding: 0 5px; margin-right: 6px;
}}
.tp-diff del {{ color: #C0392B; background: #FDEDEB; text-decoration: line-through; }}
.tp-diff ins {{ color: #1E7B34; background: #EAF7EE; text-decoration: none; }}
.tp-diff-arrow {{ margin: 0 5px; color: #8E8E93; }}

/* ---- Trace 안전 점검 — 후속 칩 파이프라인 (04 §5-2) ---- */
.tp-pipe {{ display: flex; align-items: center; gap: 5px; flex-wrap: wrap; }}
.tp-pipe-step {{
  font-size: 0.7rem; font-weight: 700; padding: 2px 8px; border-radius: 8px;
  border: 1px solid #E3E3E8; background: #fff; color: #4a4a4f;
}}
.tp-pipe-step.on {{ border-color: #0A84FF; color: #0A5BD3; background: #EAF3FF; }}
.tp-pipe-step.ok {{ border-color: #34C759; color: #1E7B34; background: #EAF7EE; }}
.tp-pipe-step.fail {{ border-color: #E0A030; color: #9a6a00; background: #FFF8E6; }}
.tp-pipe-arrow {{ color: #8E8E93; font-size: 0.72rem; }}
.tp-pipe-note {{ font-size: 0.68rem; color: #8E8E93; margin-top: 2px; }}

/* ---- Trace 실시간 상태 라벨 (턴 실행 중) ---- */
.tp-live-dot {{
  display: inline-block; width: 8px; height: 8px; border-radius: 50%;
  background: #0A84FF; margin: 0 7px 1px 1px;
  animation: tp-pulse 1s ease-in-out infinite;
}}
.tp-live-label {{ font-size: 0.78rem; color: #0A5BD3; font-weight: 700; margin-top: 2px; }}
.tp-live-label.err {{ color: #B25000; }}
.tp-live-done {{ font-size: 0.74rem; color: #2e9e4f; font-weight: 700; margin-top: 4px; }}
@keyframes tp-pulse {{
  0%, 100% {{ opacity: .25; transform: scale(.75); }}
  50% {{ opacity: 1; transform: scale(1); }}
}}

/* =========================================================
   스마트폰 프레임 (화면 1) — 동일 규격 {PHONE_W}x{PHONE_H}
   ========================================================= */
.st-key-phone_zone {{ position: relative; width: {PHONE_W}px; margin: 12px auto 0; }}
.phone-frame {{
  width: {PHONE_W}px; height: {PHONE_H}px; border: 10px solid #1f1f1f; border-radius: 44px;
  overflow: hidden; background: #F7F5F0; box-shadow: 0 18px 44px rgba(0,0,0,.22);
  display: flex; flex-direction: column;
}}
.phone-notch {{
  width: 130px; height: 22px; background: #1f1f1f; border-radius: 0 0 14px 14px;
  margin: 0 auto; position: relative; z-index: 2; flex: 0 0 auto;
}}
.phone-screen {{ flex: 1 1 0; min-height: 0; padding: 10px 16px; overflow: hidden; }}
.phone-screen.capture {{ padding: 0; margin-top: -22px; }}
.phone-screen img.submain {{
  width: 100%; height: 100%; display: block;
  object-fit: cover; object-position: top;
}}

.pf-appbar {{
  display: flex; justify-content: space-between; align-items: center;
  font-weight: 800; font-size: 1.05rem; color: #333; padding: 8px 2px 12px;
}}
.pf-banner {{
  background: linear-gradient(120deg, #FFCC00, #FFE066); border-radius: 14px;
  padding: 16px; font-weight: 700; color: #4a3f00; margin-bottom: 12px;
}}
.pf-banner small {{ font-weight: 500; color: #6b5d10; }}
.pf-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 14px; }}
.pf-menu {{
  background: #fff; border: 1px solid #ECE7DB; border-radius: 12px;
  padding: 14px 12px; font-size: 0.88rem; font-weight: 600; color: #4a4437;
}}
.pf-list-title {{ font-size: 0.8rem; color: #8a8272; font-weight: 700; margin: 6px 2px; }}
.pf-item {{
  background: #fff; border: 1px solid #ECE7DB; border-radius: 10px;
  padding: 10px 12px; font-size: 0.84rem; color: #4a4437; margin-bottom: 6px;
  display: flex; justify-content: space-between;
}}
.pf-item span {{ color: #b0a890; font-size: 0.75rem; }}
.pf-caption {{
  text-align: center; color: #9a927e; font-size: 0.72rem; padding: 8px 0;
  flex: 0 0 auto; background: #fff;
}}

/* ---- 플로팅 버튼 + 말풍선 ---- */
.fab-bubble {{
  position: absolute; right: 14px; bottom: 128px; z-index: 5;
  background: #fff; border: 1px solid #E0D9C8; border-radius: 14px 14px 2px 14px;
  padding: 8px 12px; font-size: 0.8rem; color: #4a4437;
  box-shadow: 0 4px 14px rgba(0,0,0,.12); max-width: 230px;
}}
.st-key-ai_fab {{ position: absolute; right: 14px; bottom: 68px; width: auto; z-index: 6; }}
.st-key-ai_fab button {{
  border-radius: 999px; background: #FFCC00; color: #3d3200; font-weight: 800;
  border: none; padding: 10px 18px; box-shadow: 0 6px 18px rgba(0,0,0,.25);
}}
.st-key-ai_fab button:hover {{ background: #ffd83d; color: #3d3200; }}
</style>
"""

# 메시지 영역 하단 자동 스크롤 (일반 챗 UI 관례) — 사용자가 위로 스크롤해
# 읽는 중이면 강제하지 않는다. components.html(iframe)에서 부모 DOM 접근.
AUTOSCROLL_JS = """
<script>
(function(){
  const doc = window.parent.document;
  let ticks = 0;
  const iv = setInterval(function(){
    ticks++;
    const wrap = doc.querySelector('.st-key-chat_scroll');
    if (wrap){
      let sc = null;
      const nodes = [wrap].concat(Array.from(wrap.querySelectorAll('div')));
      for (const el of nodes){
        if (el.scrollHeight > el.clientHeight + 8){ sc = el; break; }
      }
      if (sc){
        const nearBottom = sc.scrollHeight - sc.scrollTop - sc.clientHeight < 150;
        if (ticks <= 3 || nearBottom){ sc.scrollTop = sc.scrollHeight; }
      }
    }
    if (ticks > 100) clearInterval(iv);
  }, 300);
})();
</script>
"""


def mode_badge_html(agent_mode: str) -> str:
    if agent_mode == "live":
        return '<span class="mode-badge live">● LIVE AGENT</span>'
    return '<span class="mode-badge mock">● MOCK TRACE</span>'
