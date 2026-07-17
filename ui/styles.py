# -*- coding: utf-8 -*-
"""폰 프레임·채팅 말풍선·배지 CSS (04 §9). B2에서 카드 스타일 확장 예정."""

KB_YELLOW = "#FFCC00"
KB_DARK = "#60584C"

CSS = """
<style>
/* ---- 앱 공통 ---- */
.stApp { background: #F6F4EE; }
.block-container { padding-top: 1.4rem; padding-bottom: 1rem; }

/* ---- 모드 배지 ---- */
.mode-badge {
  display: inline-block; padding: 3px 12px; border-radius: 999px;
  font-size: 0.75rem; font-weight: 700; letter-spacing: 0.04em; white-space: nowrap;
}
.mode-badge.mock { background: #FFF3CD; color: #7a5c00; border: 1px solid #ffe08a; }
.mode-badge.live { background: #D1F0D9; color: #14532d; border: 1px solid #86dba2; }

/* =========================================================
   채팅 폰 프레임 (화면 2 — 04 §2)
   ========================================================= */
.st-key-chat_phone {
  width: 434px; margin: 0 auto; background: #F9F7F1;
  border: 10px solid #1f1f1f; border-radius: 44px;
  box-shadow: 0 18px 44px rgba(0,0,0,.22);
  padding: 0 10px 12px; gap: 0.4rem;
}

/* 대화 헤더 */
.chatbar { margin: 0 -10px; }
.chatbar .phone-notch { margin-bottom: -14px; }
.chatbar .cb-row {
  display: flex; align-items: center; gap: 10px;
  background: #fff; padding: 20px 16px 10px; border-bottom: 1px solid #EEE8DB;
}
.chatbar .cb-back { font-size: 1.5rem; color: #8a8272; font-weight: 300; line-height: 1; }
.chatbar .cb-avatar {
  width: 38px; height: 38px; border-radius: 50%; flex: 0 0 38px;
  background: linear-gradient(135deg, #FFCC00, #FFE066);
  display: flex; align-items: center; justify-content: center; font-size: 20px;
  box-shadow: 0 2px 6px rgba(0,0,0,.12);
}
.chatbar .cb-title { font-weight: 800; font-size: 0.98rem; color: #3a352a; line-height: 1.25; }
.chatbar .cb-title small { font-weight: 600; font-size: 0.72rem; color: #47a56b; }
.chatbar .cb-sub {
  background: #FFFBEB; border-bottom: 1px solid #F5E6A8;
  padding: 6px 16px; font-size: 0.74rem; color: #7a6c2a;
}
.chatbar .cb-sub b { color: #5a4a00; }

/* 스크롤 메시지 영역 — 컨테이너 기본 테두리 제거 */
.st-key-chat_scroll, .st-key-chat_scroll > div { border: none !important; }
[data-testid="stVerticalBlockBorderWrapper"].st-key-chat_scroll { border: none !important; }

/* ---- 말풍선 ---- */
.msg-row { display: flex; margin: 10px 0; align-items: flex-end; }
.msg-row.user { justify-content: flex-end; }
.msg-row .avatar {
  flex: 0 0 30px; width: 30px; height: 30px; border-radius: 50%;
  background: linear-gradient(135deg, #FFCC00, #FFE066);
  display: flex; align-items: center; justify-content: center;
  font-size: 16px; margin-right: 7px; box-shadow: 0 2px 6px rgba(0,0,0,.12);
}
.bubble {
  max-width: 82%; padding: 10px 14px; border-radius: 16px;
  font-size: 0.88rem; line-height: 1.65; word-break: keep-all;
}
.bubble.bot {
  background: #fff; border: 1px solid #EDE7D9; color: #3a352a;
  border-radius: 3px 16px 16px 16px; box-shadow: 0 2px 8px rgba(0,0,0,.05);
}
.bubble.user {
  background: #FFCC00; color: #3d3200; font-weight: 600;
  border-radius: 16px 3px 16px 16px; box-shadow: 0 2px 8px rgba(0,0,0,.08);
}
.bubble .cursor { opacity: .65; animation: blink 0.9s infinite; }
@keyframes blink { 50% { opacity: 0; } }

/* ---- 타이핑 인디케이터 ---- */
.typing { display: flex; align-items: center; }
.typing .dots { display: inline-flex; margin-right: 9px; }
.typing .dots i {
  width: 7px; height: 7px; background: #d4c98f; border-radius: 50%;
  display: inline-block; margin-right: 4px; animation: bounce 1.15s infinite;
}
.typing .dots i:nth-child(2) { animation-delay: .15s; }
.typing .dots i:nth-child(3) { animation-delay: .3s; }
@keyframes bounce { 0%,80%,100% { transform: translateY(0); } 40% { transform: translateY(-5px); } }
.typing .nlabel { color: #8a8272; font-size: 0.82rem; }

/* ---- 현재 탐색 기준 칩바 (04 §4-2) ---- */
.cond-bar {
  background: #fff; border: 1px dashed #D9D2C0; border-radius: 10px;
  padding: 5px 10px; font-size: 0.75rem;
}
.cond-bar .cond-title { color: #8a8272; font-weight: 700; margin-right: 6px; }
.cond-chip {
  display: inline-block; background: #F6F4EE; border: 1px solid #E0D9C8;
  border-radius: 999px; padding: 1px 9px; margin: 1px 2px; color: #4a4437;
}

/* ---- 후속 칩(빠른 시작) 버튼 ---- */
div[class*="st-key-chip_"] button {
  border-radius: 999px; background: #fff; border: 1px solid #E4DCC8;
  color: #5a4a00; font-size: 0.76rem; padding: 5px 10px; min-height: 0;
  box-shadow: 0 1px 4px rgba(0,0,0,.04); white-space: normal; line-height: 1.3;
}
div[class*="st-key-chip_"] button:hover {
  border-color: #FFCC00; background: #FFFBEB; color: #3d3200;
}

/* ---- 입력창 (프레임 하단 인라인) ---- */
.st-key-chat_phone [data-testid="stChatInput"] {
  background: #fff; border: 1px solid #E4DCC8; border-radius: 24px;
}
.st-key-chat_phone [data-testid="stChatInput"]:focus-within { border-color: #FFCC00; }

/* =========================================================
   스마트폰 프레임 (화면 1 — 04 §2)
   ========================================================= */
.st-key-phone_zone { position: relative; width: 410px; margin: 0 auto; }
.phone-frame {
  width: 410px; border: 10px solid #1f1f1f; border-radius: 44px;
  overflow: hidden; background: #F7F5F0; box-shadow: 0 18px 44px rgba(0,0,0,.22);
}
.phone-notch {
  width: 130px; height: 22px; background: #1f1f1f; border-radius: 0 0 14px 14px;
  margin: 0 auto; position: relative; z-index: 2;
}
.phone-screen { min-height: 700px; padding: 10px 16px 70px; }
.phone-screen.capture { padding: 0; min-height: auto; margin-top: -22px; }
.phone-screen img.submain { width: 100%; display: block; }

.pf-appbar {
  display: flex; justify-content: space-between; align-items: center;
  font-weight: 800; font-size: 1.05rem; color: #333; padding: 8px 2px 12px;
}
.pf-banner {
  background: linear-gradient(120deg, #FFCC00, #FFE066); border-radius: 14px;
  padding: 16px; font-weight: 700; color: #4a3f00; margin-bottom: 12px;
}
.pf-banner small { font-weight: 500; color: #6b5d10; }
.pf-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 14px; }
.pf-menu {
  background: #fff; border: 1px solid #ECE7DB; border-radius: 12px;
  padding: 14px 12px; font-size: 0.88rem; font-weight: 600; color: #4a4437;
}
.pf-list-title { font-size: 0.8rem; color: #8a8272; font-weight: 700; margin: 6px 2px; }
.pf-item {
  background: #fff; border: 1px solid #ECE7DB; border-radius: 10px;
  padding: 10px 12px; font-size: 0.84rem; color: #4a4437; margin-bottom: 6px;
  display: flex; justify-content: space-between;
}
.pf-item span { color: #b0a890; font-size: 0.75rem; }
.pf-caption { text-align: center; color: #9a927e; font-size: 0.72rem; padding: 10px 0 2px; }

/* ---- 플로팅 버튼 + 말풍선 ---- */
.fab-bubble {
  position: absolute; right: 14px; bottom: 118px; z-index: 5;
  background: #fff; border: 1px solid #E0D9C8; border-radius: 14px 14px 2px 14px;
  padding: 8px 12px; font-size: 0.8rem; color: #4a4437;
  box-shadow: 0 4px 14px rgba(0,0,0,.12); max-width: 230px;
}
.st-key-ai_fab { position: absolute; right: 14px; bottom: 58px; width: auto; z-index: 6; }
.st-key-ai_fab button {
  border-radius: 999px; background: #FFCC00; color: #3d3200; font-weight: 800;
  border: none; padding: 10px 18px; box-shadow: 0 6px 18px rgba(0,0,0,.25);
}
.st-key-ai_fab button:hover { background: #ffd83d; color: #3d3200; }
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
