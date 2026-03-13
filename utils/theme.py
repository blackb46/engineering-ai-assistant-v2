"""
theme.py  —  City of Brentwood Engineering AI Assistant
========================================================
V3 — "Apple-style" Professional Redesign

Design principles implemented:
  • System font stack ONLY — zero network calls, zero render delay
  • 1px borders in #E2E8F0 — barely there
  • Soft ambient shadows — depth without weight
  • Navy for structure/text, Orange ONLY for primary CTA buttons
  • Strict left-alignment throughout
  • Typography: 24px bold → 16px semibold → 14px body → 11px uppercase label
  • Metric cards: large thin (weight 300) numbers, uppercase 10px labels
  • Segmented control CSS for Yes/No/NA pill track
  • Checklist cards: clean card with chevron + progress badge
  • "No" comment panel: 2px orange left-border accent with CSS slide-in
"""

from pathlib import Path
import streamlit as st

try:
    from PIL import Image as _PILImage
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False

# ── Color tokens ──────────────────────────────────────────────────────────────
NAVY      = "#22427C"
MID_BLUE  = "#2F5C9C"
ORANGE    = "#F07138"
BG        = "#F7F8FA"       # slightly cooler than before
WHITE     = "#FFFFFF"
TEXT_DARK = "#111827"       # near-black — more contrast
TEXT_MID  = "#6B7280"       # gray-500
TEXT_LIGHT= "#9CA3AF"       # gray-400
BORDER    = "#E2E8F0"       # slate-200 — Apple thin
BORDER_MID= "#CBD5E1"       # slate-300

GITHUB_LOGO_URL = (
    "https://raw.githubusercontent.com/blackb46/engineering-ai-assistant-v2"
    "/main/assets/BrentwoodCrestLogo-RGB.png"
)

# ── Logo helpers ──────────────────────────────────────────────────────────────
_LOGO_CACHE: dict = {}

def _get_logo_path(color: bool = True) -> Path:
    name_rgb = "BrentwoodCrestLogo-RGB.png"
    name_bw  = "BrentwoodCrestLogo-BW.png"
    primary  = name_rgb if color else name_bw
    fallback = name_bw  if color else name_rgb
    for name in (primary, fallback):
        for p in [
            Path(__file__).parent.parent / "assets" / name,
            Path(__file__).parent / "assets" / name,
            Path(__file__).parent.parent / name,
        ]:
            if p.exists():
                return p
    return None

def _logo_bytes(color: bool = True):
    key = f"bytes_{'c' if color else 'b'}"
    if key in _LOGO_CACHE:
        return _LOGO_CACHE[key]
    p = _get_logo_path(color)
    if p is None:
        _LOGO_CACHE[key] = None
        return None
    with open(p, "rb") as f:
        data = f.read()
    _LOGO_CACHE[key] = data
    return data

_FAVICON_CACHE: dict = {}

def get_favicon():
    if "fav" in _FAVICON_CACHE:
        return _FAVICON_CACHE["fav"]
    if not _PIL_AVAILABLE:
        _FAVICON_CACHE["fav"] = "🏛"
        return "🏛"
    p = _get_logo_path(color=True)
    if p is None:
        _FAVICON_CACHE["fav"] = "🏛"
        return "🏛"
    try:
        img = _PILImage.open(p)
        img.thumbnail((64, 64), _PILImage.LANCZOS)
        _FAVICON_CACHE["fav"] = img
        return img
    except Exception:
        _FAVICON_CACHE["fav"] = "🏛"
        return "🏛"


# ── Master CSS ─────────────────────────────────────────────────────────────────
# NO @import — system fonts only. Zero render-blocking network calls.
_CSS = """
/* ── Root ─────────────────────────────────────────────────────────── */
:root {
    --font:       -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                  Helvetica, Arial, sans-serif;
    --navy:       #22427C;
    --midblue:    #2F5C9C;
    --orange:     #F07138;
    --bg:         #F7F8FA;
    --white:      #FFFFFF;
    --text:       #111827;
    --text-mid:   #6B7280;
    --text-light: #9CA3AF;
    --border:     #E2E8F0;
    --border-md:  #CBD5E1;
    --sh-xs:      0 1px 2px rgba(0,0,0,0.04);
    --sh-sm:      0 1px 3px rgba(0,0,0,0.06), 0 2px 6px rgba(0,0,0,0.04);
    --sh-md:      0 4px 12px rgba(0,0,0,0.07), 0 1px 3px rgba(0,0,0,0.04);
    --r:          10px;
    --r-sm:       6px;
}

/* ── Base ──────────────────────────────────────────────────────────── */
.stApp {
    background: var(--bg) !important;
    font-family: var(--font) !important;
    font-size: 14px !important;
    line-height: 1.6 !important;
    color: var(--text) !important;
    -webkit-font-smoothing: antialiased;
}
p, li, span, div, label { font-family: var(--font) !important; }

/* ── Kill Streamlit chrome ─────────────────────────────────────────── */
[data-testid="stSidebarNav"], footer,
#MainMenu, [data-testid="stDecoration"] { display: none !important; }

/* ── Sidebar shell ─────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: var(--white) !important;
    border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] > div:first-child { padding-top: 0 !important; }

/* ── Sidebar logo block ────────────────────────────────────────────── */
.bw-sidebar-top {
    padding: 18px 16px 14px;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    gap: 10px;
}
.bw-sidebar-top img {
    width: 30px; height: 30px;
    object-fit: contain; flex-shrink: 0;
}
.bw-sidebar-city  { font-size: 13px; font-weight: 700; color: var(--navy); line-height: 1.25; letter-spacing: -0.01em; }
.bw-sidebar-dept  { font-size: 11px; font-weight: 500; color: var(--text-mid); margin-top: 1px; }

/* ── Sidebar nav ───────────────────────────────────────────────────── */
.bw-nav-section {
    font-size: 10px; font-weight: 700;
    letter-spacing: 0.1em; text-transform: uppercase;
    color: var(--text-light);
    padding: 16px 16px 6px;
}
.bw-nav-divider { border: none; border-top: 1px solid var(--border); margin: 8px 0; }
.bw-version-badge {
    font-size: 11px; color: var(--text-light);
    padding: 8px 16px 20px; line-height: 1.6;
}

/* Style Streamlit's page_link as a nav item */
[data-testid="stPageLink"] a,
[data-testid="stPageLink"] a:visited {
    display: flex !important;
    align-items: center !important;
    padding: 7px 12px !important;
    margin: 1px 8px !important;
    border-radius: var(--r-sm) !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    color: var(--text-mid) !important;
    text-decoration: none !important;
    transition: background 0.12s, color 0.12s !important;
    background: transparent !important;
}
[data-testid="stPageLink"] a:hover {
    background: #F1F5F9 !important;
    color: var(--navy) !important;
}

/* ── Layout ────────────────────────────────────────────────────────── */
.block-container {
    padding-top: 0 !important;
    padding-left: 2.5rem !important;
    padding-right: 2.5rem !important;
    max-width: 1140px !important;
}

/* ── Page header — clean, left-aligned, white bg ─────────────────── */
.bw-page-header {
    padding: 24px 0 18px;
    margin: 0 0 24px;
    border-bottom: 1px solid var(--border);
}
.bw-breadcrumb {
    display: block;
    font-size: 10px; font-weight: 700;
    letter-spacing: 0.1em; text-transform: uppercase;
    color: var(--text-light);
    margin-bottom: 4px;
}
.bw-page-header h1 {
    font-size: 24px !important;
    font-weight: 700 !important;
    color: var(--navy) !important;
    margin: 0 0 3px !important;
    letter-spacing: -0.02em !important;
    line-height: 1.2 !important;
    font-family: var(--font) !important;
}
.bw-page-header .sub {
    font-size: 13px; color: var(--text-mid);
    margin: 0; line-height: 1.4;
}

/* ── Section heading ───────────────────────────────────────────────── */
.bw-section-heading {
    font-size: 10px; font-weight: 700;
    letter-spacing: 0.1em; text-transform: uppercase;
    color: var(--text-light);
    padding-bottom: 8px;
    margin: 28px 0 14px;
    border-bottom: 1px solid var(--border);
}

/* ── Generic card ──────────────────────────────────────────────────── */
.bw-card {
    background: var(--white) !important;
    border: 1px solid var(--border);
    border-radius: var(--r);
    padding: 20px;
    box-shadow: var(--sh-xs);
}

/* ── Mode cards (dashboard) ────────────────────────────────────────── */
.bw-mode-card {
    background: var(--white) !important;
    border: 1px solid var(--border);
    border-radius: var(--r);
    padding: 24px 24px 20px;
    box-shadow: var(--sh-xs);
    height: 100%;
    transition: box-shadow 0.18s, border-color 0.18s, transform 0.18s;
}
.bw-mode-card:hover {
    box-shadow: var(--sh-md);
    border-color: var(--border-md);
    transform: translateY(-1px);
}
.bw-mode-card .mode-icon { font-size: 22px; display: block; margin-bottom: 12px; }
.bw-mode-card h3 {
    font-size: 16px !important; font-weight: 600 !important;
    color: var(--navy) !important;
    margin: 0 0 6px !important; letter-spacing: -0.01em !important;
    font-family: var(--font) !important;
}
.bw-mode-card p { font-size: 13px !important; color: var(--text-mid) !important; line-height: 1.5 !important; margin: 0 !important; }

/* ── Answer display ────────────────────────────────────────────────── */
.bw-answer-box {
    background: var(--white) !important;
    border: 1px solid var(--border);
    border-top: 2px solid var(--navy);
    border-radius: var(--r);
    padding: 20px 24px;
    margin: 12px 0;
    line-height: 1.75;
    font-size: 14px;
    color: var(--text) !important;
    box-shadow: var(--sh-xs);
}
.bw-answer-label {
    display: block;
    font-size: 10px; font-weight: 700;
    letter-spacing: 0.1em; text-transform: uppercase;
    color: var(--text-light); margin-bottom: 10px;
}

/* ── Citation box ──────────────────────────────────────────────────── */
.bw-citation-box {
    background: #FAFBFC !important;
    border: 1px solid var(--border);
    border-radius: var(--r);
    padding: 14px 18px;
    margin: 8px 0;
    font-size: 13px;
    color: var(--text) !important;
}
.bw-citation-box .cit-header {
    font-size: 10px; font-weight: 700;
    letter-spacing: 0.1em; text-transform: uppercase;
    color: var(--text-light); margin-bottom: 10px;
}
.bw-citation-box ol { margin: 0; padding-left: 0; list-style: none; }
.bw-citation-box li {
    padding: 6px 0; border-bottom: 1px solid var(--border);
    color: var(--text) !important; font-size: 13px; line-height: 1.5;
}
.bw-citation-box li:last-child { border-bottom: none; }

/* ── Flag banners ──────────────────────────────────────────────────── */
.bw-flag-restrictive {
    background: #FFFCF0 !important; color: var(--text) !important;
    border: 1px solid #FDE68A; border-left: 3px solid #D97706;
    border-radius: var(--r-sm); padding: 10px 14px; margin: 6px 0; font-size: 13px;
}
.bw-flag-conflict {
    background: #FFF5F5 !important; color: var(--text) !important;
    border: 1px solid #FECACA; border-left: 3px solid #DC2626;
    border-radius: var(--r-sm); padding: 10px 14px; margin: 6px 0; font-size: 13px;
}
.bw-abstain-box {
    background: #F8F9FA !important; color: var(--text-mid) !important;
    border: 1px solid var(--border); border-left: 3px solid var(--border-md);
    border-radius: var(--r-sm); padding: 10px 14px; margin: 6px 0; font-size: 13px;
}

/* ── Status pills ──────────────────────────────────────────────────── */
.bw-status-ok  { background:#F0FDF4 !important; color:#15803D !important; border:1px solid #BBF7D0; border-radius:var(--r-sm); padding:8px 12px; margin:4px 0; font-size:13px; }
.bw-status-warn{ background:#FFFBEB !important; color:#92400E !important; border:1px solid #FDE68A; border-radius:var(--r-sm); padding:8px 12px; margin:4px 0; font-size:13px; }
.bw-status-err { background:#FFF5F5 !important; color:#991B1B !important; border:1px solid #FECACA; border-radius:var(--r-sm); padding:8px 12px; margin:4px 0; font-size:13px; }

/* ── Feedback/success ──────────────────────────────────────────────── */
.bw-feedback-panel {
    background:#FFFCF8 !important; color:var(--text) !important;
    border:1px solid #FED7AA; border-radius:var(--r); padding:16px 18px; margin:12px 0;
}
.bw-success-msg {
    background:#F0FDF4 !important; color:#15803D !important;
    border:1px solid #BBF7D0; border-radius:var(--r-sm); padding:10px 14px; margin:10px 0;
}

/* ═══════════════════════════════════════════════════════════════════
   WIZARD-SPECIFIC STYLES
   ═══════════════════════════════════════════════════════════════════ */

/* ── Wizard section header (replaces bw-section-header) ───────────── */
.bw-section-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: var(--white) !important;
    border: 1px solid var(--border);
    border-left: 3px solid var(--navy);
    border-radius: var(--r-sm);
    padding: 10px 14px;
    margin: 20px 0 4px;
    font-size: 14px;
    font-weight: 600;
    color: var(--navy) !important;
    box-shadow: var(--sh-xs);
}
.bw-section-header .section-progress {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--text-light);
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 99px;
    padding: 2px 8px;
    white-space: nowrap;
}

/* ── Checklist item row ────────────────────────────────────────────── */
.bw-item-row {
    background: var(--white) !important;
    border: 1px solid var(--border);
    border-radius: var(--r-sm);
    padding: 10px 14px;
    margin: 3px 0;
    transition: border-color 0.12s;
}
.bw-item-row:hover { border-color: var(--border-md); }
.bw-item-id {
    font-size: 10px; font-weight: 700;
    letter-spacing: 0.06em; text-transform: uppercase;
    color: var(--text-light); margin-right: 6px;
}
.bw-item-desc { font-size: 13.5px; color: var(--text); line-height: 1.5; }

/* ── Segmented control track ───────────────────────────────────────── */
/* Wraps the st.radio horizontal — pill-shaped track with sliding pill */
.bw-seg-wrap { display: flex; gap: 0; }
[data-testid="stRadio"] > div[role="radiogroup"] {
    display: flex !important;
    gap: 0 !important;
    background: var(--bg) !important;
    border: 1px solid var(--border-md) !important;
    border-radius: 99px !important;
    padding: 2px !important;
    width: fit-content !important;
}
[data-testid="stRadio"] > div[role="radiogroup"] > label {
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    min-width: 52px !important;
    padding: 4px 10px !important;
    border-radius: 99px !important;
    font-size: 12px !important;
    font-weight: 600 !important;
    cursor: pointer !important;
    color: var(--text-mid) !important;
    transition: background 0.15s, color 0.15s !important;
    user-select: none !important;
    line-height: 1.4 !important;
}
[data-testid="stRadio"] > div[role="radiogroup"] > label:has(input:checked) {
    background: var(--white) !important;
    color: var(--navy) !important;
    box-shadow: var(--sh-xs) !important;
}
/* Color the Yes/No segments when selected */
[data-testid="stRadio"] > div[role="radiogroup"] > label:has(input[value="Yes"]:checked) {
    background: #DCFCE7 !important;
    color: #15803D !important;
}
[data-testid="stRadio"] > div[role="radiogroup"] > label:has(input[value="No"]:checked) {
    background: #FEE2E2 !important;
    color: #DC2626 !important;
}
/* Hide the actual radio dot */
[data-testid="stRadio"] input[type="radio"] { display: none !important; }
[data-testid="stRadio"] > label { display: none !important; }

/* ── Comment panel (slides in when "No" selected) ──────────────────── */
.bw-comment-panel {
    border-left: 2px solid var(--orange);
    background: #FFFCFA !important;
    border-radius: 0 var(--r-sm) var(--r-sm) 0;
    padding: 12px 14px;
    margin: 4px 0 6px 16px;
    animation: slideDown 0.18s ease-out;
}
@keyframes slideDown {
    from { opacity: 0; transform: translateY(-6px); }
    to   { opacity: 1; transform: translateY(0); }
}
.bw-comment-panel-label {
    font-size: 10px; font-weight: 700;
    letter-spacing: 0.08em; text-transform: uppercase;
    color: var(--orange); margin-bottom: 8px; display: block;
}

/* ── Comment preview text ──────────────────────────────────────────── */
.bw-comment-text {
    font-size: 12.5px;
    color: var(--text-mid);
    line-height: 1.5;
    margin-top: 2px;
    padding: 4px 0;
    border-bottom: 1px solid var(--border);
}
.bw-comment-text:last-child { border-bottom: none; }

/* ── Resubmittal box ───────────────────────────────────────────────── */
.bw-resubmittal-box {
    background: var(--white) !important;
    border: 1px solid var(--border);
    border-radius: var(--r);
    padding: 16px 20px;
    margin: 20px 0;
    box-shadow: var(--sh-xs);
}

/* ── Export section ────────────────────────────────────────────────── */
.bw-export-section {
    background: var(--white) !important;
    border: 1px solid var(--border);
    border-radius: var(--r);
    padding: 20px;
    margin: 16px 0;
    box-shadow: var(--sh-xs);
}

/* ── Metric cards — thin large numbers ─────────────────────────────── */
[data-testid="stMetric"] {
    background: var(--white) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--r) !important;
    padding: 18px 20px !important;
    box-shadow: var(--sh-xs) !important;
}
[data-testid="stMetricLabel"] {
    font-size: 10px !important; font-weight: 700 !important;
    letter-spacing: 0.1em !important; text-transform: uppercase !important;
    color: var(--text-light) !important; font-family: var(--font) !important;
}
[data-testid="stMetricValue"] {
    font-size: 34px !important; font-weight: 300 !important;
    color: var(--navy) !important; letter-spacing: -0.03em !important;
    line-height: 1.1 !important; font-family: var(--font) !important;
}

/* ── Progress bar ──────────────────────────────────────────────────── */
[data-testid="stProgress"] > div > div {
    background: var(--navy) !important;
    border-radius: 99px !important; height: 4px !important;
}
[data-testid="stProgress"] > div {
    background: var(--border) !important;
    border-radius: 99px !important; height: 4px !important;
}

/* ── Buttons ───────────────────────────────────────────────────────── */
[data-testid="stButton"] button {
    font-family: var(--font) !important;
    font-size: 13px !important; font-weight: 500 !important;
    border-radius: var(--r-sm) !important;
    transition: all 0.12s !important;
}
[data-testid="stButton"] button[kind="primary"] {
    background: var(--orange) !important;
    border: none !important; color: white !important;
    font-weight: 600 !important;
    box-shadow: 0 1px 3px rgba(240,113,56,0.3) !important;
}
[data-testid="stButton"] button[kind="primary"]:hover {
    background: #D95F28 !important;
    box-shadow: 0 2px 8px rgba(240,113,56,0.4) !important;
    transform: translateY(-1px) !important;
}
[data-testid="stButton"] button[kind="secondary"] {
    background: var(--white) !important;
    border: 1px solid var(--border) !important;
    color: var(--text) !important;
}
[data-testid="stButton"] button[kind="secondary"]:hover {
    border-color: var(--border-md) !important;
    background: var(--bg) !important; color: var(--navy) !important;
}

/* ── Inputs ────────────────────────────────────────────────────────── */
[data-testid="stTextArea"] textarea,
[data-testid="stTextInput"] input {
    border: 1px solid var(--border-md) !important;
    border-radius: var(--r-sm) !important;
    font-family: var(--font) !important;
    font-size: 14px !important;
    background: var(--white) !important;
    color: var(--text) !important;
    padding: 8px 12px !important;
    transition: border-color 0.12s, box-shadow 0.12s !important;
}
[data-testid="stTextArea"] textarea:focus,
[data-testid="stTextInput"] input:focus {
    border-color: var(--navy) !important;
    box-shadow: 0 0 0 3px rgba(34,66,124,0.08) !important;
    outline: none !important;
}
[data-testid="stSelectbox"] > div > div {
    border: 1px solid var(--border-md) !important;
    border-radius: var(--r-sm) !important;
    font-family: var(--font) !important;
    font-size: 14px !important;
    background: var(--white) !important;
}
[data-testid="stTextInput"] label,
[data-testid="stTextArea"] label,
[data-testid="stSelectbox"] label {
    font-size: 12px !important; font-weight: 600 !important;
    color: var(--text-mid) !important; letter-spacing: 0.01em !important;
}

/* ── Expander — clean card ─────────────────────────────────────────── */
[data-testid="stExpander"] {
    border: 1px solid var(--border) !important;
    border-radius: var(--r) !important;
    background: var(--white) !important;
    box-shadow: var(--sh-xs) !important;
    margin: 4px 0 !important;
    overflow: hidden !important;
}
[data-testid="stExpander"] > details > summary {
    padding: 12px 16px !important;
    font-size: 14px !important; font-weight: 600 !important;
    color: var(--text) !important;
    background: var(--white) !important;
    cursor: pointer !important;
    transition: background 0.12s !important;
}
[data-testid="stExpander"] > details > summary:hover {
    background: var(--bg) !important;
}
[data-testid="stExpander"] > details[open] > summary {
    border-bottom: 1px solid var(--border) !important;
    background: var(--bg) !important;
}

/* ── Column gap ────────────────────────────────────────────────────── */
[data-testid="stHorizontalBlock"] { gap: 12px !important; }

/* ── HR ────────────────────────────────────────────────────────────── */
hr { border: none !important; border-top: 1px solid var(--border) !important; margin: 20px 0 !important; }

/* ── Typography ────────────────────────────────────────────────────── */
h1, h2, h3, h4 { font-family: var(--font) !important; color: var(--navy) !important; }
h1 { font-size: 24px !important; font-weight: 700 !important; letter-spacing: -0.02em !important; }
h2 { font-size: 20px !important; font-weight: 600 !important; }
h3 { font-size: 16px !important; font-weight: 600 !important; }

/* ── Footer ────────────────────────────────────────────────────────── */
.bw-footer {
    color: var(--text-light); font-size: 11px;
    padding: 20px 0 8px; border-top: 1px solid var(--border); margin-top: 40px;
}
"""


# ── Public API ─────────────────────────────────────────────────────────────────

def apply_theme():
    """Inject master CSS. Call immediately after st.set_page_config()."""
    st.markdown(f"<style>{_CSS}</style>", unsafe_allow_html=True)


def render_sidebar(active: str = "home"):
    """
    Render the compact branded sidebar.
    active: "home" | "qa" | "wizard"
    """
    with st.sidebar:
        # Compact logo row — 30px crest + city/dept text inline
        # GitHub URL → browser caches after first load; 0 bytes on rerenders
        st.markdown(
            f"<div class='bw-sidebar-top'>"
            f"<img src='{GITHUB_LOGO_URL}' alt='Brentwood Seal'>"
            f"<div>"
            f"<div class='bw-sidebar-city'>City of Brentwood</div>"
            f"<div class='bw-sidebar-dept'>Engineering Department</div>"
            f"</div></div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<div class='bw-nav-section'>Navigation</div>",
            unsafe_allow_html=True,
        )
        st.page_link("app.py",                 label="🏛  Dashboard")
        st.page_link("pages/1_QA_Mode.py",     label="🔍  Q&A Mode")
        st.page_link("pages/2_Wizard_Mode.py", label="📋  Wizard Mode")
        # Performance profiler kept in repo — uncomment to re-enable nav link:
        # st.page_link("pages/3_Performance.py", label="⏱️  Performance")
        st.markdown(
            "<hr class='bw-nav-divider'>"
            "<div class='bw-version-badge'>"
            "Engineering AI Assistant v2.0<br>Powered by Claude"
            "</div>",
            unsafe_allow_html=True,
        )


def page_header(title: str, subtitle: str = "", breadcrumb: str = ""):
    """
    Left-aligned, clean page header. No navy band — just type + a bottom rule.
    breadcrumb: small uppercase label above the title
    """
    crumb = f"<span class='bw-breadcrumb'>{breadcrumb}</span>" if breadcrumb else ""
    sub   = f"<p class='sub'>{subtitle}</p>" if subtitle else ""
    st.markdown(
        f"<div class='bw-page-header'>{crumb}<h1>{title}</h1>{sub}</div>",
        unsafe_allow_html=True,
    )


def section_heading(text: str):
    """Small all-caps section divider."""
    st.markdown(f"<div class='bw-section-heading'>{text}</div>", unsafe_allow_html=True)


def footer():
    """Page footer."""
    st.markdown(
        "<div class='bw-footer'>"
        "City of Brentwood &nbsp;·&nbsp; Engineering Department "
        "&nbsp;·&nbsp; AI Assistant v2.0"
        "</div>",
        unsafe_allow_html=True,
    )
