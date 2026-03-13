"""
theme.py
========
City of Brentwood Engineering AI Assistant — Shared Visual Theme (v2 Premium UI)

BRENTWOOD COLOR PALETTE (official — unchanged)
    Navy (primary)    #22427C
    Mid Blue          #2F5C9C
    Orange (accent)   #F07138
    Cool Gray BG      #F4F6F9
    White             #FFFFFF
    Text Dark         #1A2332
    Text Mid          #4A5568
    Border            #DDE3EC
"""

from pathlib import Path
import base64
import streamlit as st
try:
    from PIL import Image as _PILImage
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False

# ── Color tokens (official Brentwood palette — do not change) ─────────────────
NAVY      = "#22427C"
MID_BLUE  = "#2F5C9C"
ORANGE    = "#F07138"
BG        = "#F4F6F9"
WHITE     = "#FFFFFF"
TEXT_DARK = "#1A2332"
TEXT_MID  = "#4A5568"
BORDER    = "#DDE3EC"

# ── Logo loader ───────────────────────────────────────────────────────────────
def _get_logo_path(color: bool = True) -> Path:
    name_rgb = "BrentwoodCrestLogo-RGB.png"
    name_bw  = "BrentwoodCrestLogo-BW.png"
    primary  = name_rgb if color else name_bw
    fallback = name_bw  if color else name_rgb
    for name in (primary, fallback):
        candidates = [
            Path(__file__).parent.parent / "assets" / name,
            Path(__file__).parent / "assets" / name,
            Path(__file__).parent.parent / name,
        ]
        for p in candidates:
            if p.exists():
                return p
    return None

_LOGO_CACHE: dict = {}

def _logo_bytes(color: bool = True) -> bytes | None:
    key = ("bytes_color" if color else "bytes_bw")
    if key in _LOGO_CACHE:
        return _LOGO_CACHE[key]
    p = _get_logo_path(color=color)
    if p is None:
        _LOGO_CACHE[key] = None
        return None
    with open(p, "rb") as f:
        data = f.read()
    _LOGO_CACHE[key] = data
    return data

def _logo_b64(color: bool = True) -> str:
    key = "color" if color else "bw"
    if key in _LOGO_CACHE:
        return _LOGO_CACHE[key]
    p = _get_logo_path(color=color)
    if p is None:
        _LOGO_CACHE[key] = ""
        return ""
    with open(p, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    result = f"data:image/png;base64,{data}"
    _LOGO_CACHE[key] = result
    return result

_FAVICON_CACHE: dict = {}

def get_favicon():
    if "favicon" in _FAVICON_CACHE:
        return _FAVICON_CACHE["favicon"]
    if not _PIL_AVAILABLE:
        _FAVICON_CACHE["favicon"] = "🏛"
        return "🏛"
    p = _get_logo_path(color=True)
    if p is None:
        _FAVICON_CACHE["favicon"] = "🏛"
        return "🏛"
    try:
        img = _PILImage.open(p)
        img.thumbnail((64, 64), _PILImage.LANCZOS)
        _FAVICON_CACHE["favicon"] = img
        return img
    except Exception:
        _FAVICON_CACHE["favicon"] = "🏛"
        return "🏛"

# ── Master CSS ────────────────────────────────────────────────────────────────
_CSS = """
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&display=swap');

:root {
    --navy:      #22427C;
    --midblue:   #2F5C9C;
    --orange:    #F07138;
    --bg:        #F4F6F9;
    --white:     #FFFFFF;
    --text-dark: #1A2332;
    --text-mid:  #4A5568;
    --border:    #DDE3EC;
    --surface-1: #FFFFFF;
    --surface-2: #F8FAFD;
    --surface-3: #EEF2F9;
    --gray-100:  #F1F5F9;
    --gray-200:  #E2E8F0;
    --gray-300:  #CBD5E1;
    --gray-400:  #94A3B8;
    --font-display: 'DM Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    --font-body:    'DM Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    --text-xs:   0.72rem;
    --text-sm:   0.83rem;
    --text-base: 0.94rem;
    --text-md:   1.05rem;
    --text-lg:   1.2rem;
    --text-xl:   1.5rem;
    --text-2xl:  1.875rem;
    --shadow-xs: 0 1px 2px rgba(30,50,90,0.06);
    --shadow-sm: 0 1px 4px rgba(30,50,90,0.08), 0 0 0 1px rgba(30,50,90,0.04);
    --shadow-md: 0 4px 16px rgba(30,50,90,0.10), 0 1px 4px rgba(30,50,90,0.06);
    --shadow-lg: 0 8px 32px rgba(30,50,90,0.12), 0 2px 8px rgba(30,50,90,0.08);
    --shadow-orange: 0 4px 16px rgba(240,113,56,0.30);
    --radius-sm: 6px;
    --radius:    10px;
    --radius-lg: 14px;
    --radius-full: 999px;
}

.stApp {
    background-color: var(--bg) !important;
    font-family: var(--font-body) !important;
    font-size: var(--text-base) !important;
    line-height: 1.65 !important;
    color: var(--text-dark) !important;
}
p, li, span, div, label { font-family: var(--font-body) !important; }

[data-testid="stSidebarNav"] { display: none !important; }
.stDeployButton { display: none !important; }
.main .block-container {
    padding-top: 0 !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
    max-width: 1100px !important;
}

/* ── Sidebar ───────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: var(--white) !important;
    border-right: 1px solid var(--border) !important;
    padding-top: 0 !important;
    min-width: 240px !important;
    max-width: 240px !important;
}
[data-testid="stSidebar"] > div:first-child {
    padding-top: 0 !important;
    padding-left: 0 !important;
    padding-right: 0 !important;
}
.bw-sidebar-brand {
    background: var(--navy);
    padding: 20px 16px 16px;
    text-align: center;
    border-bottom: 3px solid var(--orange);
}
.bw-sidebar-city {
    font-family: var(--font-display);
    font-size: 0.88rem;
    font-weight: 700;
    color: white;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    margin: 0;
    line-height: 1.3;
}
.bw-sidebar-dept {
    font-family: var(--font-body);
    font-size: 0.75rem;
    font-weight: 400;
    color: rgba(255,255,255,0.70);
    letter-spacing: 0.03em;
    margin-top: 2px;
}
.bw-sidebar-logo-wrap {
    margin: 12px auto 0;
    width: 72px;
    height: 72px;
    border-radius: 50%;
    background: white;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 2px 12px rgba(0,0,0,0.25);
    overflow: hidden;
    padding: 4px;
}
.bw-sidebar-logo-wrap img { width: 64px; height: 64px; object-fit: contain; }
.bw-nav-section-label {
    font-family: var(--font-body);
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.11em;
    text-transform: uppercase;
    color: var(--gray-400);
    padding: 12px 16px 4px;
    display: block;
}
[data-testid="stPageLink"] a {
    display: flex !important;
    align-items: center !important;
    gap: 8px !important;
    padding: 8px 12px !important;
    border-radius: var(--radius-sm) !important;
    color: var(--text-mid) !important;
    font-family: var(--font-body) !important;
    font-size: var(--text-sm) !important;
    font-weight: 500 !important;
    text-decoration: none !important;
    transition: background 0.15s, color 0.15s !important;
    margin: 2px 0 !important;
}
[data-testid="stPageLink"] a:hover {
    background: var(--surface-3) !important;
    color: var(--navy) !important;
}
.bw-sidebar-divider { border: none; border-top: 1px solid var(--border); margin: 8px 16px; }
.bw-sidebar-footer { padding: 8px 16px 16px; font-size: var(--text-xs); color: var(--gray-400); font-family: var(--font-body); line-height: 1.5; }

/* ── Page header ────────────────────────────────────────────────── */
.bw-page-header {
    background: var(--navy);
    border-bottom: 3px solid var(--orange);
    padding: 28px 32px;
    margin: -1rem -2rem 32px -2rem;
    display: flex;
    align-items: center;
    gap: 20px;
}
.bw-page-header-text { flex: 1; }
.bw-page-header h1 {
    font-family: var(--font-display) !important;
    font-size: var(--text-xl) !important;
    font-weight: 700 !important;
    color: white !important;
    margin: 0 !important;
    line-height: 1.2 !important;
    letter-spacing: -0.02em !important;
}
.bw-page-header .subtitle {
    font-family: var(--font-body) !important;
    font-size: var(--text-sm) !important;
    font-weight: 400 !important;
    color: rgba(255,255,255,0.70) !important;
    margin: 6px 0 0 !important;
}

/* ── Section heading ────────────────────────────────────────────── */
.bw-section-heading {
    font-family: var(--font-body);
    font-size: var(--text-xs);
    font-weight: 700;
    letter-spacing: 0.13em;
    text-transform: uppercase;
    color: var(--midblue);
    border-bottom: 2px solid var(--border);
    padding-bottom: 8px;
    margin: 32px 0 16px;
}

/* ── Step heading (Step 1, Step 2 in Checklist Mode) ────────────── */
.bw-step-heading {
    font-family: var(--font-display);
    font-size: 1.25rem;
    font-weight: 700;
    color: var(--navy);
    border-left: 4px solid var(--orange);
    padding: 10px 16px;
    margin: 28px 0 16px;
    background: var(--surface-3);
    border-radius: 0 var(--radius) var(--radius) 0;
    line-height: 1.3;
    letter-spacing: -0.01em;
}

/* ── Expander section headers — larger, bolder ───────────────────── */
[data-testid="stExpander"] summary {
    font-family: var(--font-display) !important;
    font-weight: 700 !important;
    font-size: 1.05rem !important;
    color: var(--navy) !important;
    padding: 14px 16px !important;
    letter-spacing: -0.01em !important;
}
[data-testid="stExpander"] summary:hover {
    background: var(--surface-2) !important;
    border-radius: var(--radius) !important;
}
[data-testid="stExpander"] summary p {
    font-family: var(--font-display) !important;
    font-weight: 700 !important;
    font-size: 1.05rem !important;
    color: var(--navy) !important;
    margin: 0 !important;
}

/* ── Cards ──────────────────────────────────────────────────────── */
.bw-card { background: var(--white) !important; border: 1px solid var(--border); border-radius: var(--radius); padding: 24px; box-shadow: var(--shadow-sm); }
.bw-card-accent { border-left: 4px solid var(--navy); }

/* ── Mode cards ─────────────────────────────────────────────────── */
.bw-mode-card {
    background: var(--white) !important;
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    padding: 28px 24px 20px;
    box-shadow: var(--shadow-sm);
    height: 100%;
    position: relative;
    transition: box-shadow 0.2s ease, border-color 0.2s ease, transform 0.2s ease;
    overflow: hidden;
}
.bw-mode-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: linear-gradient(90deg, var(--navy), var(--midblue));
    border-radius: var(--radius-lg) var(--radius-lg) 0 0;
}
.bw-mode-card:hover { box-shadow: var(--shadow-md); border-color: var(--midblue); transform: translateY(-2px); }
.bw-mode-card .mode-icon { width: 44px; height: 44px; background: var(--surface-3); border-radius: 10px; display: flex; align-items: center; justify-content: center; margin-bottom: 14px; font-size: 1.25rem; }
.bw-mode-card h3 { font-family: var(--font-display) !important; font-size: var(--text-md) !important; font-weight: 700 !important; color: var(--navy) !important; margin: 0 0 8px !important; letter-spacing: -0.01em !important; }
.bw-mode-card p { font-size: var(--text-sm) !important; color: var(--text-mid) !important; line-height: 1.6 !important; margin: 0 !important; }

/* ── Answer display ─────────────────────────────────────────────── */
.bw-answer-box {
    background: var(--white) !important;
    border: 1px solid var(--border);
    border-top: 3px solid var(--navy);
    border-radius: var(--radius);
    padding: 24px 28px;
    margin: 16px 0;
    line-height: 1.8;
    font-size: var(--text-base);
    color: var(--text-dark) !important;
    font-family: var(--font-body);
    box-shadow: var(--shadow-sm);
}
.bw-answer-label {
    font-family: var(--font-body);
    font-size: var(--text-xs);
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--navy);
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 6px;
}
.bw-answer-label::after { content: ''; flex: 1; height: 1px; background: var(--border); }

/* ── Citation box ───────────────────────────────────────────────── */
.bw-citation-box {
    background: var(--surface-2) !important;
    border: 1px solid var(--border);
    border-top: 2px solid var(--orange);
    border-radius: var(--radius);
    padding: 16px 20px;
    margin: 8px 0;
    font-size: 0.88em;
    color: var(--text-dark) !important;
}
.bw-citation-box .cit-header {
    font-family: var(--font-body);
    font-size: var(--text-xs);
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--orange);
    margin-bottom: 10px;
    display: flex;
    align-items: center;
    gap: 6px;
}
.bw-citation-box .cit-header::after { content: ''; flex: 1; height: 1px; background: rgba(240,113,56,0.25); }
.bw-citation-box ol { margin: 0; padding-left: 0; list-style: none; }
.bw-citation-box li { margin-bottom: 0; line-height: 1.6; padding: 6px 0; border-bottom: 1px solid var(--gray-200); color: var(--text-dark) !important; display: flex; align-items: flex-start; gap: 8px; }
.bw-citation-box li:last-child { border-bottom: none; }

/* ── Flag banners ───────────────────────────────────────────────── */
.bw-flag-restrictive { background: #FFFBF0 !important; color: var(--text-dark) !important; border: 1px solid #F6D860; border-left: 4px solid #E8A000; border-radius: var(--radius); padding: 12px 18px; margin: 8px 0; font-size: 0.91em; font-family: var(--font-body); }
.bw-flag-conflict { background: #FFF5F5 !important; color: var(--text-dark) !important; border: 1px solid #FCA5A5; border-left: 4px solid #DC2626; border-radius: var(--radius); padding: 12px 18px; margin: 8px 0; font-size: 0.91em; font-family: var(--font-body); }
.bw-abstain-box { background: var(--gray-100) !important; color: var(--text-mid) !important; border: 1px solid var(--border); border-left: 4px solid var(--gray-300); border-radius: var(--radius); padding: 12px 18px; margin: 8px 0; font-size: 0.94em; font-family: var(--font-body); }

/* ── Status pills ───────────────────────────────────────────────── */
.bw-status-ok { background: #F0FDF4 !important; color: #166534 !important; border: 1px solid #BBF7D0; border-left: 4px solid #16A34A; border-radius: var(--radius); padding: 12px 16px; margin: 6px 0; font-size: 0.88em; font-family: var(--font-body); }
.bw-status-warn { background: #FFFBEB !important; color: #92400E !important; border: 1px solid #FDE68A; border-left: 4px solid #D97706; border-radius: var(--radius); padding: 12px 16px; margin: 6px 0; font-size: 0.88em; font-family: var(--font-body); }
.bw-status-err { background: #FFF5F5 !important; color: #7F1D1D !important; border: 1px solid #FECACA; border-left: 4px solid #DC2626; border-radius: var(--radius); padding: 12px 16px; margin: 6px 0; font-size: 0.88em; font-family: var(--font-body); }

/* ── Feedback / success ─────────────────────────────────────────── */
.bw-feedback-panel { background: #FFF8F5 !important; color: var(--text-dark) !important; border: 1px solid #FDBA74; border-radius: var(--radius); padding: 20px 24px; margin: 16px 0; font-family: var(--font-body); }
.bw-success-msg { background: #F0FDF4 !important; color: #166534 !important; border: 1px solid #BBF7D0; border-radius: var(--radius); padding: 12px 18px; margin: 16px 0; font-family: var(--font-body); }

/* ── Wizard elements ────────────────────────────────────────────── */
.bw-wizard-header { background: var(--navy) !important; color: white !important; padding: 20px 24px; border-radius: var(--radius); border-left: 5px solid var(--orange); margin-bottom: 16px; }
.bw-wizard-header h2 { color: white !important; font-family: var(--font-display); font-size: var(--text-lg); margin: 0 0 4px; font-weight: 700; }
.bw-wizard-header p { color: rgba(255,255,255,0.75) !important; font-size: var(--text-sm); margin: 0; }
.bw-checklist-section { background: var(--white) !important; border: 1px solid var(--border); border-radius: var(--radius); overflow: hidden; margin: 12px 0; }
.bw-checklist-section-header { background: var(--surface-3) !important; color: var(--navy) !important; padding: 10px 16px; font-family: var(--font-body); font-size: var(--text-sm); font-weight: 700; letter-spacing: 0.03em; border-bottom: 1px solid var(--border); }
.bw-section-header { background: #EEF2F9 !important; color: #22427C !important; padding: 0.65rem 1rem; border-left: 4px solid #F07138; margin: 1.2rem 0 0.5rem 0; font-size: 0.97rem; font-weight: 700; letter-spacing: 0.02em; border-radius: 0 6px 6px 0; }
.bw-comment-box { background: #FFFBF0 !important; color: #1A2332 !important; border: 1px solid #F6D860; border-left: 3px solid #E8A000; border-radius: var(--radius-sm); padding: 12px 16px; margin: 6px 0 6px 20px; font-size: 0.9em; }
.bw-resubmittal-box { background: var(--surface-3) !important; color: var(--text-dark) !important; border: 1px solid var(--border); border-left: 4px solid var(--midblue); border-radius: var(--radius); padding: 16px 20px; margin: 16px 0; }
.bw-export-section { background: #F0FDF4 !important; color: #1A2332 !important; border: 1px solid #BBF7D0; border-left: 4px solid #16A34A; border-radius: var(--radius); padding: 20px 24px; margin: 16px 0; }

/* ── Progress bar ───────────────────────────────────────────────── */
[data-testid="stProgress"] > div { border-radius: var(--radius-full) !important; background: var(--gray-200) !important; height: 8px !important; }
[data-testid="stProgress"] > div > div { background: linear-gradient(90deg, var(--navy), var(--midblue)) !important; border-radius: var(--radius-full) !important; height: 8px !important; transition: width 0.4s ease !important; }

/* ── Metrics ────────────────────────────────────────────────────── */
[data-testid="stMetric"] { background: var(--white) !important; border: 1px solid var(--border); border-radius: var(--radius); padding: 16px !important; box-shadow: var(--shadow-xs); position: relative; overflow: hidden; }
[data-testid="stMetric"]::after { content: ''; position: absolute; bottom: 0; left: 0; right: 0; height: 3px; background: linear-gradient(90deg, var(--navy), var(--midblue)); opacity: 0.6; }
[data-testid="stMetricLabel"] { font-family: var(--font-body) !important; font-size: var(--text-xs) !important; color: var(--text-mid) !important; font-weight: 600 !important; text-transform: uppercase !important; letter-spacing: 0.08em !important; }
[data-testid="stMetricValue"] { font-family: var(--font-display) !important; font-size: 2rem !important; color: var(--navy) !important; font-weight: 700 !important; line-height: 1.1 !important; }

/* ── Buttons ────────────────────────────────────────────────────── */
[data-testid="stButton"] button[kind="primary"] { background: var(--orange) !important; border: none !important; color: white !important; font-family: var(--font-body) !important; font-weight: 600 !important; font-size: var(--text-sm) !important; border-radius: var(--radius) !important; padding: 8px 20px !important; transition: background 0.15s, box-shadow 0.15s, transform 0.1s !important; }
[data-testid="stButton"] button[kind="primary"]:hover { background: #D95F28 !important; box-shadow: var(--shadow-orange) !important; transform: translateY(-1px) !important; }
[data-testid="stButton"] button[kind="secondary"] { background: var(--white) !important; border: 1px solid var(--border) !important; color: var(--text-dark) !important; font-family: var(--font-body) !important; font-weight: 500 !important; font-size: var(--text-sm) !important; border-radius: var(--radius) !important; transition: border-color 0.15s, color 0.15s, background 0.15s !important; }
[data-testid="stButton"] button[kind="secondary"]:hover { border-color: var(--navy) !important; color: var(--navy) !important; background: var(--surface-3) !important; }
[data-testid="stDownloadButton"] button { background: var(--navy) !important; color: white !important; border: none !important; font-family: var(--font-body) !important; font-weight: 600 !important; font-size: var(--text-sm) !important; border-radius: var(--radius) !important; transition: background 0.15s, box-shadow 0.15s !important; }
[data-testid="stDownloadButton"] button:hover { background: var(--midblue) !important; box-shadow: var(--shadow-md) !important; }

/* ── Form inputs ────────────────────────────────────────────────── */
[data-testid="stTextArea"] textarea,
[data-testid="stTextInput"] input { border: 1px solid var(--gray-300) !important; border-radius: var(--radius) !important; font-family: var(--font-body) !important; font-size: var(--text-base) !important; background: var(--white) !important; color: var(--text-dark) !important; transition: border-color 0.15s, box-shadow 0.15s !important; padding: 10px 14px !important; }
[data-testid="stTextArea"] textarea:focus,
[data-testid="stTextInput"] input:focus { border-color: var(--navy) !important; box-shadow: 0 0 0 3px rgba(34,66,124,0.12) !important; outline: none !important; }
[data-testid="stSelectbox"] > div > div { border-color: var(--gray-300) !important; border-radius: var(--radius) !important; font-family: var(--font-body) !important; transition: border-color 0.15s !important; }
[data-testid="stSelectbox"] > div > div:focus-within { border-color: var(--navy) !important; box-shadow: 0 0 0 3px rgba(34,66,124,0.12) !important; }

/* ── Expander ───────────────────────────────────────────────────── */
[data-testid="stExpander"] { border: 1px solid var(--border) !important; border-radius: var(--radius) !important; background: var(--white) !important; box-shadow: var(--shadow-xs) !important; margin-bottom: 8px !important; }

/* ── Back-to-top button ─────────────────────────────────────────── */
#btt-btn {
    position: fixed; bottom: 2.5rem; right: 2rem; z-index: 9999;
    background: var(--navy); color: white !important; border: none;
    border-radius: 50%; width: 48px; height: 48px; font-size: 1.2rem;
    line-height: 48px; text-align: center; cursor: pointer;
    box-shadow: var(--shadow-md); opacity: 0; transition: opacity 0.25s, transform 0.25s;
    text-decoration: none; display: flex; align-items: center; justify-content: center;
}
#btt-btn.visible { opacity: 1; }
#btt-btn:hover { background: var(--midblue) !important; transform: translateY(-2px); box-shadow: var(--shadow-lg); }

/* ── Typography ─────────────────────────────────────────────────── */
h1 { font-family: var(--font-display) !important; font-size: var(--text-2xl) !important; font-weight: 700 !important; letter-spacing: -0.025em !important; color: var(--navy) !important; line-height: 1.2 !important; }
h2 { font-family: var(--font-display) !important; font-size: var(--text-xl) !important; font-weight: 600 !important; color: var(--navy) !important; letter-spacing: -0.015em !important; line-height: 1.3 !important; }
h3 { font-family: var(--font-body) !important; font-size: var(--text-md) !important; font-weight: 700 !important; color: var(--navy) !important; letter-spacing: -0.01em !important; }
h4 { font-family: var(--font-body) !important; font-size: var(--text-base) !important; font-weight: 600 !important; color: var(--text-dark) !important; }
hr { border: none !important; border-top: 1px solid var(--border) !important; margin: 24px 0 !important; }
[data-testid="stCaptionContainer"] { font-family: var(--font-body) !important; font-size: var(--text-xs) !important; color: var(--text-mid) !important; }
[data-testid="stAlert"] { border-radius: var(--radius) !important; font-family: var(--font-body) !important; font-size: var(--text-sm) !important; }
[data-testid="stCheckbox"] { font-family: var(--font-body) !important; font-size: var(--text-sm) !important; }
[data-testid="stRadio"] label { font-family: var(--font-body) !important; font-size: var(--text-sm) !important; }

/* ── Footer ─────────────────────────────────────────────────────── */
.bw-footer { text-align: center; color: var(--gray-400); font-size: var(--text-xs); padding: 24px 0 8px; border-top: 1px solid var(--border); font-family: var(--font-body); letter-spacing: 0.02em; }
.bw-footer strong { color: var(--navy); }
"""


# ── Public API ────────────────────────────────────────────────────────────────

def apply_theme():
    """Inject the master CSS into the current Streamlit page."""
    st.markdown(f"<style>{_CSS}</style>", unsafe_allow_html=True)


def render_sidebar(active: str = "home"):
    """Render the branded sidebar. active = 'home' | 'qa' | 'wizard'"""
    with st.sidebar:
        st.markdown(
            """
            <div class="bw-sidebar-brand">
                <div class="bw-sidebar-city">City of Brentwood</div>
                <div class="bw-sidebar-dept">Engineering Department</div>
                <div class="bw-sidebar-logo-wrap">
                    <img src="https://raw.githubusercontent.com/blackb46/engineering-ai-assistant-v2/main/assets/BrentwoodCrestLogo-RGB.png"
                         alt="City of Brentwood Seal">
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("<span class='bw-nav-section-label'>Navigation</span>", unsafe_allow_html=True)
        _nav_link("app.py",                 "Dashboard",      active == "home",   "⬛")
        _nav_link("pages/1_QA_Mode.py",     "Chatbot Mode",   active == "qa",     "🔍")
        _nav_link("pages/2_Wizard_Mode.py", "Checklist Mode", active == "wizard", "📋")
        st.markdown(
            """<hr class="bw-sidebar-divider">
            <div class="bw-sidebar-footer">
                Engineering AI Assistant<br>
                <span style="color:#94A3B8">v2.0 &nbsp;·&nbsp; Powered by Claude</span>
            </div>""",
            unsafe_allow_html=True,
        )


def _nav_link(page: str, label: str, is_active: bool, icon: str = ""):
    st.page_link(page, label=f"{icon}  {label}")


def page_header(title: str, subtitle: str = ""):
    """Render the standard Brentwood navy page header band."""
    sub_block = f"<p class='subtitle'>{subtitle}</p>" if subtitle else ""
    st.markdown(
        f"""<div class="bw-page-header">
            <img src="https://raw.githubusercontent.com/blackb46/engineering-ai-assistant-v2/main/assets/BrentwoodCrestLogo-RGB.png"
                 style="height:72px;width:auto;flex-shrink:0;
                        filter:drop-shadow(0 2px 6px rgba(0,0,0,0.30));
                        border-radius:50%;background:white;padding:4px;"
                 alt="City of Brentwood Seal">
            <div class="bw-page-header-text"><h1>{title}</h1>{sub_block}</div>
        </div>""",
        unsafe_allow_html=True,
    )


def section_heading(text: str):
    """Render a small all-caps section divider heading."""
    st.markdown(f"<div class='bw-section-heading'>{text}</div>", unsafe_allow_html=True)


def footer():
    """Render the standard page footer."""
    st.markdown(
        "<div class='bw-footer'>"
        "<strong>City of Brentwood</strong> Engineering AI Assistant v2.0 &nbsp;·&nbsp; "
        "Engineering Department &nbsp;·&nbsp; Powered by Claude API"
        "</div>",
        unsafe_allow_html=True,
    )
