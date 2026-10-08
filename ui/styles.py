"""Central visual system — NEXUS AI neural-intelligence theme.

Single source of truth for ALL styling (colors, cards, buttons, inputs,
typography, glows, animations). Components reference these classes;
no CSS is scattered across other modules.
"""
from __future__ import annotations

# --- Palette (mirrors the neural-network reference) ---
BG_DEEP = "#03070D"
BG_MAIN = "#050B14"
SURFACE = "#08111D"
SURFACE_2 = "#0B1624"
NEON = "#00E5FF"
BLUE = "#3B82F6"
MAGENTA = "#D946EF"
TEXT_MAIN = "#E8F9FF"
TEXT_DIM = "#8FA8B8"
TEXT_MUTED = "#607786"

GLOBAL_CSS = """
/* ============ NEXUS AI — base ============ */
html, body, [data-testid="stAppViewContainer"] {
    background:
        radial-gradient(1100px 500px at 12% -5%, rgba(0,229,255,0.10), transparent 60%),
        radial-gradient(900px 480px at 88% 8%, rgba(217,70,239,0.08), transparent 60%),
        radial-gradient(1000px 700px at 50% 110%, rgba(59,130,246,0.10), transparent 60%),
        linear-gradient(180deg, #050B14 0%, #03070D 100%);
    color: #E8F9FF;
}
[data-testid="stAppViewContainer"]::before {
    content: "";
    position: fixed; inset: 0; pointer-events: none; z-index: 0;
    background-image:
        linear-gradient(rgba(0,229,255,0.045) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,229,255,0.045) 1px, transparent 1px);
    background-size: 44px 44px;
    mask-image: radial-gradient(ellipse 90% 70% at 50% 20%, black 30%, transparent 75%);
}
[data-testid="stMain"] > div { position: relative; z-index: 1; }
#MainMenu, footer { visibility: hidden; }
[data-testid="stToolbar"] { visibility: hidden; }
[data-testid="stDecoration"] { visibility: hidden; }

/* ============ typography ============ */
.nexus-eyebrow {
    font-size: 11px; letter-spacing: 4px; color: #00E5FF;
    font-weight: 700; text-transform: uppercase;
}
.nexus-hero-title {
    font-size: clamp(30px, 4.5vw, 52px); font-weight: 800; line-height: 1.05;
    background: linear-gradient(92deg, #E8F9FF 20%, #00E5FF 55%, #D946EF 90%);
    -webkit-background-clip: text; background-clip: text; color: transparent;
    margin: 2px 0 6px 0;
}
.nexus-hero-sub { color: #8FA8B8; font-size: 15px; max-width: 640px; }
.nexus-section-title {
    font-size: 12px; letter-spacing: 3px; color: #00E5FF; font-weight: 700;
    text-transform: uppercase; margin: 26px 0 10px 0;
    display: flex; align-items: center; gap: 10px;
}
.nexus-section-title::after {
    content: ""; height: 1px; flex: 1;
    background: linear-gradient(90deg, rgba(0,229,255,0.35), transparent);
}

/* ============ glass cards ============ */
.nexus-card {
    background: rgba(10,20,35,0.65);
    border: 1px solid rgba(0,229,255,0.15);
    border-radius: 2px;
    padding: 20px 22px;
    box-shadow: 0 0 0 1px rgba(0,0,0,0.2), 0 8px 40px rgba(0,229,255,0.06);
    backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);
}
.nexus-card.glow { border-color: rgba(0,229,255,0.35); box-shadow: 0 0 32px rgba(0,229,255,0.12); }
.nexus-card.magenta { border-color: rgba(217,70,239,0.25); }
[data-testid="stVerticalBlockBorderWrapper"] {
    background: rgba(10,20,35,0.65);
    border: 1px solid rgba(0,229,255,0.15);
    border-radius: 2px;
    box-shadow: 0 8px 40px rgba(0,229,255,0.06);
}

/* ============ status pills & dots ============ */
.nexus-pill {
    display: inline-flex; align-items: center; gap: 8px;
    font-size: 11px; letter-spacing: 2px; font-weight: 700;
    border: 1px solid rgba(0,229,255,0.35); border-radius: 2px;
    padding: 6px 14px; color: #00E5FF; background: rgba(0,229,255,0.06);
}
.nexus-dot { width: 8px; height: 8px; border-radius: 50%; background: #00E5FF;
    box-shadow: 0 0 10px #00E5FF; animation: nexus-pulse 2.2s ease-in-out infinite; }
.nexus-dot.ok { background: #34F5C5; box-shadow: 0 0 10px #34F5C5; }
.nexus-dot.warn { background: #FFC857; box-shadow: 0 0 10px #FFC857; animation: none; }
.nexus-dot.off { background: #607786; box-shadow: none; animation: none; }
@keyframes nexus-pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.35; } }

/* ============ pipeline flow ============ */
.nexus-pipe { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; margin: 6px 0 2px 0; }
.nexus-node {
    display: inline-flex; align-items: center; gap: 7px;
    font-size: 10.5px; letter-spacing: 1.5px; font-weight: 700;
    padding: 6px 12px; border-radius: 2px;
    border: 1px solid rgba(143,168,184,0.25); color: #607786;
    background: rgba(8,17,29,0.7);
}
.nexus-node.done { color: #34F5C5; border-color: rgba(52,245,197,0.4); }
.nexus-node.active { color: #00E5FF; border-color: rgba(0,229,255,0.6);
    box-shadow: 0 0 16px rgba(0,229,255,0.25); animation: nexus-pulse 2s infinite; }
.nexus-link { color: rgba(0,229,255,0.4); font-size: 12px; }

/* ============ uploader ============ */
[data-testid="stFileUploader"] {
    background: rgba(10,20,35,0.65);
    border: 1.5px dashed rgba(0,229,255,0.4);
    border-radius: 2px; padding: 26px 20px;
    backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);
    transition: box-shadow 0.25s ease, border-color 0.25s ease;
}
[data-testid="stFileUploader"]:hover {
    border-color: rgba(0,229,255,0.8);
    box-shadow: 0 0 36px rgba(0,229,255,0.15), inset 0 0 30px rgba(0,229,255,0.04);
}
[data-testid="stFileUploader"] small, [data-testid="stFileUploader"] span { color: #8FA8B8 !important; }
[data-testid="stFileUploader"] button {
    border: 1px solid rgba(0,229,255,0.5) !important; color: #00E5FF !important;
    background: rgba(0,229,255,0.07) !important; border-radius: 2px !important;
}

/* ============ inputs ============ */
[data-testid="stTextArea"] textarea {
    background: rgba(8,17,29,0.85) !important; color: #E8F9FF !important;
    border: 1px solid rgba(0,229,255,0.25) !important; border-radius: 2px !important;
    box-shadow: inset 0 0 24px rgba(0,229,255,0.04);
}
[data-testid="stTextArea"] textarea:focus {
    border-color: rgba(0,229,255,0.7) !important;
    box-shadow: 0 0 0 1px rgba(0,229,255,0.4), 0 0 28px rgba(0,229,255,0.15) !important;
}
/* Sliders: style ONLY the thumb + labels. Never blanket-paint inner divs
   (that smears the track and breaks the control's look). */
[data-testid="stSlider"] [role="slider"] {
    background-color: #00E5FF !important;
    border: 2px solid #E8F9FF !important;
    box-shadow: 0 0 12px rgba(0,229,255,0.7) !important;
}
[data-testid="stWidgetLabel"] p, [data-testid="stWidgetLabel"] label { color: #8FA8B8 !important; }

/* ============ buttons (Streamlit 1.46: testid sits ON the <button>) ============ */
div[data-testid="stButton"] > button, div[data-testid="stDownloadButton"] > button {
    border-radius: 2px !important; font-weight: 700 !important;
    letter-spacing: 1px !important; transition: all 0.2s ease !important;
    background: rgba(11,22,36,0.8) !important;
    border: 1px solid rgba(143,168,184,0.3) !important; color: #8FA8B8 !important;
}
div[data-testid="stButton"] > button:hover, div[data-testid="stDownloadButton"] > button:hover {
    border-color: rgba(0,229,255,0.55) !important; color: #00E5FF !important;
    box-shadow: 0 0 18px rgba(0,229,255,0.18) !important;
}
button[data-testid="stBaseButton-primary"] {
    background: linear-gradient(92deg, rgba(0,229,255,0.22), rgba(59,130,246,0.22)) !important;
    border: 1px solid rgba(0,229,255,0.65) !important; color: #E8F9FF !important;
    box-shadow: 0 0 22px rgba(0,229,255,0.25) !important;
}
button[data-testid="stBaseButton-primary"]:hover {
    box-shadow: 0 0 34px rgba(0,229,255,0.45) !important; transform: translateY(-1px);
}

/* ============ expanders / metrics / misc ============ */
[data-testid="stExpander"] {
    background: rgba(10,20,35,0.6); border: 1px solid rgba(0,229,255,0.14);
    border-radius: 2px;
}
[data-testid="stExpander"] summary, [data-testid="stExpander"] summary span { color: #8FA8B8 !important; }
[data-testid="stMetric"] {
    background: rgba(10,20,35,0.6); border: 1px solid rgba(0,229,255,0.14);
    border-radius: 2px; padding: 12px 14px;
}
[data-testid="stMetricValue"] { color: #E8F9FF !important; }
[data-testid="stMetricLabel"] { color: #8FA8B8 !important; }
[data-testid="stProgress"] div div { background: linear-gradient(90deg, #00E5FF, #3B82F6) !important; }
[data-testid="stAlert"] { border-radius: 2px; }
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, rgba(8,17,29,0.95), rgba(5,11,20,0.97));
    border-right: 1px solid rgba(0,229,255,0.12);
}
[data-testid="stCaptionContainer"], .stCaption { color: #607786 !important; }
a { color: #00E5FF !important; }
hr { border-color: rgba(0,229,255,0.12) !important; }

/* ============ quality bars / source cards ============ */
.nexus-qbar { display: flex; align-items: center; gap: 10px; margin: 7px 0; }
.nexus-qbar .lbl { width: 110px; font-size: 11px; letter-spacing: 1.5px; color: #8FA8B8; font-weight: 700; }
.nexus-qbar .track { flex: 1; height: 8px; border-radius: 2px; background: rgba(143,168,184,0.15); overflow: hidden; }
.nexus-qbar .fill { height: 100%; border-radius: 2px;
    background: linear-gradient(90deg, #00E5FF, #3B82F6);
    box-shadow: 0 0 12px rgba(0,229,255,0.5); }
.nexus-qbar .val { width: 44px; text-align: right; font-size: 12px; color: #E8F9FF; font-weight: 700; }
.nexus-src {
    border: 1px solid rgba(0,229,255,0.14); border-radius: 2px;
    padding: 12px 14px; margin: 8px 0; background: rgba(8,17,29,0.7);
    display: flex; gap: 14px; align-items: flex-start;
}
.nexus-src .num {
    font-weight: 800; color: #00E5FF; font-size: 13px; min-width: 30px;
    border: 1px solid rgba(0,229,255,0.35); border-radius: 2px;
    text-align: center; padding: 4px 0; background: rgba(0,229,255,0.06);
}
.nexus-src .meta { font-size: 12.5px; color: #E8F9FF; }
.nexus-src .sub { font-size: 11.5px; color: #607786; }
.nexus-kv { display: grid; grid-template-columns: 110px 1fr; gap: 6px 12px; font-size: 13px; }
.nexus-kv .k { color: #607786; letter-spacing: 1.5px; font-size: 11px; font-weight: 700; }
.nexus-kv .v { color: #E8F9FF; }
code { color: #00E5FF !important; }

/* ============ neural hero svg ============ */
.nexus-node-glow { animation: nexus-pulse 3s ease-in-out infinite; }
.nexus-flow { stroke-dasharray: 6 8; animation: nexus-dash 2.6s linear infinite; }
@keyframes nexus-dash { to { stroke-dashoffset: -28; } }
@media (max-width: 768px) {
    .nexus-hero-title { font-size: 30px; }
    .nexus-kv { grid-template-columns: 1fr; }
}

/* ============ square technical geometry + spacing system ============
   XS 4 / SM 8 / MD 16 / LG 24 / XL 32 / XXL 48. Sharp corners (2px max),
   generous gaps: nothing may look glued to its neighbour. */
.nexus-card, [data-testid="stVerticalBlockBorderWrapper"],
[data-testid="stFileUploader"], [data-testid="stTextArea"] textarea,
[data-testid="stExpander"], [data-testid="stMetric"], [data-testid="stAlert"],
.nexus-src, .nexus-src .num, .nexus-msg {
    border-radius: 2px !important;
}
div[data-testid="stButton"] > button, div[data-testid="stDownloadButton"] > button,
[data-testid="stFileUploader"] button {
    border-radius: 2px !important;
}
.nexus-pill, .nexus-node, .nexus-qbar .track, .nexus-qbar .fill {
    border-radius: 2px !important;
}
/* readable width for prose; intelligence panels still use full width */
.main .block-container { max-width: 1150px; padding-left: 2rem; padding-right: 2rem; }
/* section rhythm */
.nexus-section-title { margin: 32px 0 16px 0 !important; }
.nexus-card { margin: 16px 0 24px 0; padding: 24px; }
/* gaps between side-by-side controls (task chips, chat rows, actions) */
div[data-testid="stHorizontalBlock"] { gap: 12px; }
div[data-testid="stColumn"] { padding: 2px; }
div[data-testid="stButton"], div[data-testid="stDownloadButton"] { margin: 6px 0; }
/* breathing room around inputs and sources */
[data-testid="stTextArea"] { margin: 8px 0 4px 0; }
[data-testid="stFileUploader"] { margin: 8px 0 16px 0; padding: 32px 24px; }
.nexus-src { margin: 12px 0; padding: 16px; }
.nexus-qbar { margin: 10px 0; }
/* chat messages: square panels with clear separation */
.nexus-msg {
    border: 1px solid rgba(143,168,184,0.22);
    background: rgba(8,17,29,0.75);
    padding: 20px 22px; margin: 20px 0;
}
.nexus-msg.ai {
    border-color: rgba(0,229,255,0.22); background: rgba(10,20,35,0.7);
    box-shadow: 0 0 24px rgba(0,229,255,0.05);
}
.nexus-msg .who {
    font-size: 10.5px; letter-spacing: 3px; font-weight: 800; margin-bottom: 10px;
}
.nexus-msg.user .who { color: #8FA8B8; }
.nexus-msg.ai .who { color: #00E5FF; }
.nexus-msg .meta-row {
    margin-top: 14px; padding-top: 12px;
    border-top: 1px solid rgba(0,229,255,0.12);
    font-size: 11.5px; color: #607786; letter-spacing: 1px;
}
.nexus-ask-gap { height: 24px; }
"""


def inject_styles(st) -> None:
    """Inject the whole visual system once per script run."""
    st.markdown(f"<style>{GLOBAL_CSS}</style>", unsafe_allow_html=True)


def neural_hero_svg() -> str:
    """Lightweight animated neural-network visual (pure SVG + CSS, no JS)."""
    return """
<svg viewBox="0 0 560 220" width="100%" height="200" style="display:block" aria-hidden="true">
  <defs>
    <radialGradient id="nx-core" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#00E5FF" stop-opacity="0.9"/>
      <stop offset="45%" stop-color="#3B82F6" stop-opacity="0.45"/>
      <stop offset="100%" stop-color="#3B82F6" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="nx-mag" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#D946EF" stop-opacity="0.85"/>
      <stop offset="100%" stop-color="#D946EF" stop-opacity="0"/>
    </radialGradient>
    <filter id="nx-blur" x="-60%" y="-60%" width="220%" height="220%">
      <feGaussianBlur stdDeviation="6"/>
    </filter>
  </defs>
  <ellipse cx="280" cy="110" rx="150" ry="80" fill="url(#nx-core)" opacity="0.5"/>
  <ellipse cx="120" cy="60" rx="70" ry="45" fill="url(#nx-mag)" opacity="0.28"/>
  <ellipse cx="450" cy="165" rx="70" ry="45" fill="url(#nx-mag)" opacity="0.22"/>
  <g stroke="#00E5FF" stroke-opacity="0.35" stroke-width="1.2" class="nexus-flow">
    <line x1="60" y1="110" x2="200" y2="70"/><line x1="60" y1="110" x2="200" y2="150"/>
    <line x1="200" y1="70" x2="280" y2="110"/><line x1="200" y1="150" x2="280" y2="110"/>
    <line x1="280" y1="110" x2="370" y2="60"/><line x1="280" y1="110" x2="370" y2="160"/>
    <line x1="370" y1="60" x2="500" y2="110"/><line x1="370" y1="160" x2="500" y2="110"/>
    <line x1="120" y1="40" x2="200" y2="70"/><line x1="120" y1="180" x2="200" y2="150"/>
    <line x1="370" y1="60" x2="440" y2="35"/><line x1="370" y1="160" x2="440" y2="185"/>
  </g>
  <g fill="#00E5FF" class="nexus-node-glow">
    <circle cx="60" cy="110" r="5"/><circle cx="200" cy="70" r="4"/>
    <circle cx="200" cy="150" r="4"/><circle cx="370" cy="60" r="4"/>
    <circle cx="370" cy="160" r="4"/><circle cx="500" cy="110" r="5"/>
    <circle cx="120" cy="40" r="3"/><circle cx="120" cy="180" r="3"/>
    <circle cx="440" cy="35" r="3"/><circle cx="440" cy="185" r="3"/>
  </g>
  <g fill="#D946EF" class="nexus-node-glow" style="animation-delay:1.2s">
    <circle cx="200" cy="110" r="3.5"/><circle cx="370" cy="110" r="3.5"/>
  </g>
  <circle cx="280" cy="110" r="16" fill="none" stroke="#00E5FF" stroke-width="2" stroke-opacity="0.9"/>
  <circle cx="280" cy="110" r="24" fill="none" stroke="#00E5FF" stroke-width="1" stroke-opacity="0.35" filter="url(#nx-blur)"/>
  <circle cx="280" cy="110" r="7" fill="#E8F9FF"/>
  <circle cx="280" cy="110" r="11" fill="none" stroke="#00E5FF" stroke-width="1.5" stroke-opacity="0.6"/>
</svg>"""
