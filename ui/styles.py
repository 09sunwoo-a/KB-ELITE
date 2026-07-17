# -*- coding: utf-8 -*-
"""폰 프레임·카드·배지 CSS (04 §9). B2에서 카드 스타일 확장 예정."""

KB_YELLOW = "#FFCC00"
KB_DARK = "#60584C"

CSS = """
<style>
/* ---- 모드 배지 ---- */
.mode-badge {
  display: inline-block; padding: 3px 12px; border-radius: 999px;
  font-size: 0.78rem; font-weight: 700; letter-spacing: 0.04em;
}
.mode-badge.mock { background: #FFF3CD; color: #7a5c00; border: 1px solid #ffe08a; }
.mode-badge.live { background: #D1F0D9; color: #14532d; border: 1px solid #86dba2; }

/* ---- 현재 탐색 기준 칩바 (04 §4-2) ---- */
.cond-bar {
  background: #F7F5F0; border: 1px solid #E8E4DA; border-radius: 12px;
  padding: 8px 14px; margin-bottom: 10px; font-size: 0.85rem;
}
.cond-bar .cond-title { color: #8a8272; font-weight: 700; margin-right: 8px; }
.cond-chip {
  display: inline-block; background: #fff; border: 1px solid #E0D9C8;
  border-radius: 999px; padding: 2px 11px; margin: 2px 3px; color: #4a4437;
}

/* ---- 스마트폰 프레임 (04 §2 화면 1) ---- */
.st-key-phone_zone { position: relative; width: 410px; margin: 0 auto; }
.phone-frame {
  width: 410px; border: 10px solid #1f1f1f; border-radius: 44px;
  overflow: hidden; background: #F7F5F0; box-shadow: 0 18px 44px rgba(0,0,0,.22);
}
.phone-notch {
  width: 130px; height: 22px; background: #1f1f1f; border-radius: 0 0 14px 14px;
  margin: 0 auto;
}
.phone-screen { min-height: 700px; padding: 10px 16px 70px; }
.phone-screen.capture { padding: 0; min-height: auto; }
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

/* ---- 빠른 시작/후속 칩 버튼 ---- */
.stChatMessage .stButton button, .chip-row .stButton button { border-radius: 999px; }
</style>
"""


def mode_badge_html(agent_mode: str) -> str:
    if agent_mode == "live":
        return '<span class="mode-badge live">● LIVE AGENT</span>'
    return '<span class="mode-badge mock">● MOCK TRACE</span>'
