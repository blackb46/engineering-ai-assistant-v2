"""
theme.py
========
City of Brentwood Engineering AI Assistant — Shared Visual Theme

Centralizes all CSS, color tokens, and sidebar rendering so that
app.py, 1_QA_Mode.py, and 2_Wizard_Mode.py are visually identical.

BRENTWOOD COLOR PALETTE
    Navy (primary)    #22427C   — headers, sidebar accents, buttons
    Mid Blue          #2F5C9C   — section headings, secondary elements
    Orange (accent)   #F07138   — active states, highlights, badges
    Cool Gray BG      #F4F6F9   — page background
    White             #FFFFFF   — cards, sidebar
    Text Dark         #1A2332   — primary text
    Text Mid          #4A5568   — secondary text
    Border            #DDE3EC   — card borders, dividers

USAGE
    import sys
    sys.path.append(str(Path(__file__).parent.parent / "utils"))
    # OR for pages:
    sys.path.append(str(Path(__file__).parent.parent))
    from theme import apply_theme, render_sidebar

    # In each page, before any st calls after set_page_config:
    apply_theme()
    render_sidebar(active="qa")   # active = "home" | "qa" | "wizard"
"""

from pathlib import Path
import base64
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
BG        = "#F4F6F9"
WHITE     = "#FFFFFF"
TEXT_DARK = "#1A2332"
TEXT_MID  = "#4A5568"
BORDER    = "#DDE3EC"

# ── Logo loader ───────────────────────────────────────────────────────────────
def _get_logo_path(color: bool = True) -> Path:
    """
    Find the City crest logo file relative to this module.
    color=True  → BrentwoodCrestLogo-RGB.png  (color version, used everywhere)
    color=False → BrentwoodCrestLogo-BW.png   (fallback)
    """
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


# Module-level cache for base64-encoded logos.
# Populated once on first call, reused on every subsequent Streamlit rerender.
# Without this, every button click / checkbox tick re-encodes the 300 KB PNG
# and sends ~780 KB of HTML to the browser — the main cause of page sluggishness.
_LOGO_CACHE: dict = {}


def _logo_bytes(color: bool = True) -> bytes | None:
    """
    Return raw PNG bytes for the City crest logo.
    Cached at module level — file is read exactly once per server process.
    Use with st.image() which handles browser-level caching automatically,
    avoiding the 3.5 MB base64 string being sent over the websocket every render.
    """
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
    """
    Return the color crest logo as a base64 data URI.
    KEPT for backward compatibility only. Prefer _logo_bytes() + st.image()
    to avoid embedding 3.5 MB into the websocket on every render.
    """
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


# Cache favicon so PIL file I/O only happens once per server session,
# not on every page render / rerender.
_FAVICON_CACHE: dict = {}


def get_favicon():
    """
    Return the City crest as a PIL Image for use as set_page_config(page_icon=...).
    Falls back to a string emoji if PIL or the logo file is unavailable.
    Result is cached so the file is only opened once per server process.
    """
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
/* ── Font stack — system fonts only, no external network calls ─────── */
/* Inter ships as a system font on Windows 11, macOS 13+, and most     */
/* modern Linux distros. Falls back gracefully on all other platforms.  */
/* Georgia handles serif headings (was Source Serif 4).                 */
/* No @import — zero network round-trips on every page render.          */

/* ── Root tokens ──────────────────────────────────────────────────── */
:root {
    --font-sans:   'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI',
                   Roboto, Oxygen, Ubuntu, Cantarell, 'Helvetica Neue',
                   Arial, sans-serif;
    --font-serif:  Georgia, 'Times New Roman', Times, serif;
    --font-tight:  -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
    --navy:      #22427C;
    --midblue:   #2F5C9C;
    --orange:    #F07138;
    --bg:        #F4F6F9;
    --white:     #FFFFFF;
    --text-dark: #1A2332;
    --text-mid:  #4A5568;
    --border:    #DDE3EC;
    --shadow-sm: 0 1px 3px rgba(34,66,124,0.08);
    --shadow-md: 0 4px 12px rgba(34,66,124,0.12);
    --radius:    8px;
}

/* ── Page background ──────────────────────────────────────────────── */
.stApp {
    background-color: var(--bg) !important;
    font-family: var(--font-sans) !important;
    font-size: 0.95rem !important;
    line-height: 1.6 !important;
    color: var(--text-dark) !important;
}
p, li, span, div {
    font-family: var(--font-sans);
}

/* ── Hide default Streamlit nav ───────────────────────────────────── */
[data-testid="stSidebarNav"] { display: none !important; }

/* ── Sidebar ──────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: var(--white) !important;
    border-right: 1px solid var(--border) !important;
    padding-top: 0 !important;
}
[data-testid="stSidebar"] > div:first-child {
    padding-top: 0 !important;
}

/* ── Sidebar nav links ─────────────────────────────────────────────── */
.bw-nav-link {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    padding: 0.6rem 1rem;
    border-radius: var(--radius);
    color: var(--text-mid) !important;
    font-family: var(--font-sans);
    font-size: 0.92rem;
    font-weight: 500;
    text-decoration: none;
    margin: 0.15rem 0;
    transition: background 0.15s, color 0.15s;
    cursor: pointer;
    border: none;
    background: transparent;
    width: 100%;
    text-align: left;
}
.bw-nav-link:hover {
    background: #EEF2F9 !important;
    color: var(--navy) !important;
}
.bw-nav-link.active {
    background: #EEF2F9 !important;
    color: var(--navy) !important;
    font-weight: 600;
    border-left: 3px solid var(--orange);
    padding-left: calc(1rem - 3px);
}
.bw-nav-section {
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--text-mid);
    padding: 0.8rem 1rem 0.3rem;
    font-family: var(--font-sans);
}
.bw-nav-divider {
    border: none;
    border-top: 1px solid var(--border);
    margin: 0.5rem 0;
}
.bw-version-badge {
    font-size: 0.75rem;
    color: var(--text-mid);
    padding: 0.4rem 1rem 1rem;
    font-family: var(--font-sans);
}

/* ── Page header band ─────────────────────────────────────────────── */
.bw-page-header {
    background: var(--navy);
    border-bottom: 3px solid var(--orange);
    padding: 1.5rem 2rem;
    margin: -1rem -1rem 1.5rem -1rem;
    display: flex;
    align-items: center;
    gap: 1.2rem;
}
.bw-page-header h1 {
    font-family: var(--font-serif);
    font-size: 1.75rem;
    font-weight: 700;
    color: var(--white) !important;
    margin: 0;
    line-height: 1.2;
    letter-spacing: -0.01em;
}
.bw-page-header .subtitle {
    font-family: var(--font-sans);
    font-size: 0.93rem;
    font-weight: 400;
    color: rgba(255,255,255,0.8);
    margin: 0.3rem 0 0;
    letter-spacing: 0.01em;
    text-align: center;
}

/* ── Section heading style ────────────────────────────────────────── */
.bw-section-heading {
    font-family: var(--font-sans);
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--midblue);
    border-bottom: 2px solid var(--border);
    padding-bottom: 0.5rem;
    margin: 1.8rem 0 1rem;
}

/* ── Cards ────────────────────────────────────────────────────────── */
.bw-card {
    background: var(--white) !important;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1.5rem;
    box-shadow: var(--shadow-sm);
}
.bw-card-accent {
    border-left: 4px solid var(--navy);
}

/* ── Mode cards (dashboard) ───────────────────────────────────────── */
.bw-mode-card {
    background: var(--white) !important;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1.5rem 1.5rem 1rem;
    box-shadow: var(--shadow-sm);
    height: 100%;
    transition: box-shadow 0.2s, border-color 0.2s;
}
.bw-mode-card:hover {
    box-shadow: var(--shadow-md);
    border-color: var(--midblue);
}
.bw-mode-card .mode-icon {
    width: 40px;
    height: 40px;
    background: #EEF2F9;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 0.8rem;
}
.bw-mode-card h3 {
    font-family: var(--font-tight);
    font-size: 1.25rem;
    font-weight: 700;
    color: var(--navy) !important;
    margin: 0 0 0.5rem;
}
.bw-mode-card p {
    font-size: 0.9rem;
    color: var(--text-mid) !important;
    line-height: 1.5;
    margin: 0;
}

/* ── Answer display ───────────────────────────────────────────────── */
.bw-answer-box {
    background: var(--white) !important;
    border: 1px solid var(--border);
    border-top: 3px solid var(--navy);
    border-radius: var(--radius);
    padding: 1.4rem 1.6rem;
    margin: 0.8rem 0;
    line-height: 1.75;
    font-size: 0.97rem;
    color: var(--text-dark) !important;
    font-family: var(--font-sans);
    box-shadow: var(--shadow-sm);
}
.bw-answer-label {
    font-family: var(--font-tight);
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--navy);
    margin-bottom: 0.6rem;
    display: block;
}

/* ── Citation box ─────────────────────────────────────────────────── */
.bw-citation-box {
    background: #F8FAFC !important;
    border: 1px solid var(--border);
    border-top: 2px solid var(--orange);
    border-radius: var(--radius);
    padding: 1rem 1.4rem;
    margin: 0.5rem 0;
    font-size: 0.86em;
    color: var(--text-dark) !important;
}
.bw-citation-box .cit-header {
    font-family: var(--font-tight);
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--orange);
    margin-bottom: 0.6rem;
}
.bw-citation-box ol {
    margin: 0;
    padding-left: 0;
    list-style: none;
}
.bw-citation-box li {
    margin-bottom: 0.35rem;
    line-height: 1.5;
    padding: 0.3rem 0;
    border-bottom: 1px solid var(--border);
    color: var(--text-dark) !important;
}
.bw-citation-box li:last-child { border-bottom: none; }

/* ── Flag banners ─────────────────────────────────────────────────── */
.bw-flag-restrictive {
    background: #FFFBF0 !important;
    color: var(--text-dark) !important;
    border: 1px solid #F6D860;
    border-left: 4px solid #E8A000;
    border-radius: var(--radius);
    padding: 0.8rem 1.2rem;
    margin: 0.5rem 0;
    font-size: 0.91em;
    font-family: var(--font-sans);
}
.bw-flag-conflict {
    background: #FFF5F5 !important;
    color: var(--text-dark) !important;
    border: 1px solid #FCA5A5;
    border-left: 4px solid #DC2626;
    border-radius: var(--radius);
    padding: 0.8rem 1.2rem;
    margin: 0.5rem 0;
    font-size: 0.91em;
    font-family: var(--font-sans);
}
.bw-abstain-box {
    background: #F7F8FA !important;
    color: var(--text-mid) !important;
    border: 1px solid var(--border);
    border-left: 4px solid #94A3B8;
    border-radius: var(--radius);
    padding: 0.8rem 1.2rem;
    margin: 0.5rem 0;
    font-size: 0.94em;
    font-family: var(--font-sans);
}

/* ── Status pills ─────────────────────────────────────────────────── */
.bw-status-ok {
    background: #F0FDF4 !important;
    color: #166534 !important;
    border: 1px solid #BBF7D0;
    border-left: 4px solid #16A34A;
    border-radius: var(--radius);
    padding: 0.7rem 1rem;
    margin: 0.3rem 0;
    font-size: 0.88em;
    font-family: var(--font-sans);
}
.bw-status-warn {
    background: #FFFBEB !important;
    color: #92400E !important;
    border: 1px solid #FDE68A;
    border-left: 4px solid #D97706;
    border-radius: var(--radius);
    padding: 0.7rem 1rem;
    margin: 0.3rem 0;
    font-size: 0.88em;
    font-family: var(--font-sans);
}
.bw-status-err {
    background: #FFF5F5 !important;
    color: #7F1D1D !important;
    border: 1px solid #FECACA;
    border-left: 4px solid #DC2626;
    border-radius: var(--radius);
    padding: 0.7rem 1rem;
    margin: 0.3rem 0;
    font-size: 0.88em;
    font-family: var(--font-sans);
}

/* ── Feedback boxes ───────────────────────────────────────────────── */
.bw-feedback-panel {
    background: #FFF8F5 !important;
    color: var(--text-dark) !important;
    border: 1px solid #FDBA74;
    border-radius: var(--radius);
    padding: 1.2rem 1.4rem;
    margin: 0.8rem 0;
    font-family: var(--font-sans);
}
.bw-success-msg {
    background: #F0FDF4 !important;
    color: #166534 !important;
    border: 1px solid #BBF7D0;
    border-radius: var(--radius);
    padding: 0.8rem 1.2rem;
    margin: 0.8rem 0;
    font-family: var(--font-sans);
}

/* ── Wizard review header ─────────────────────────────────────────── */
.bw-wizard-header {
    background: var(--navy) !important;
    color: white !important;
    padding: 1.2rem 1.5rem;
    border-radius: var(--radius);
    border-left: 5px solid var(--orange);
    margin-bottom: 1rem;
}
.bw-wizard-header h2 {
    color: white !important;
    font-family: var(--font-serif);
    font-size: 1.3rem;
    margin: 0 0 0.3rem;
}
.bw-wizard-header p {
    color: rgba(255,255,255,0.8) !important;
    font-size: 0.88rem;
    margin: 0;
    font-family: var(--font-sans);
}

/* ── Wizard checklist items ───────────────────────────────────────── */
.bw-checklist-section {
    background: var(--white) !important;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    overflow: hidden;
    margin: 0.8rem 0;
}
.bw-checklist-section-header {
    background: #EEF2F9 !important;
    color: var(--navy) !important;
    padding: 0.7rem 1rem;
    font-family: var(--font-tight);
    font-size: 0.95rem;
    font-weight: 700;
    letter-spacing: 0.03em;
    border-bottom: 1px solid var(--border);
}

/* ── Metric cards ─────────────────────────────────────────────────── */
[data-testid="stMetric"] {
    background: var(--white) !important;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1rem !important;
    box-shadow: var(--shadow-sm);
}
[data-testid="stMetricLabel"] {
    font-family: var(--font-sans) !important;
    font-size: 0.8rem !important;
    color: var(--text-mid) !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
}
[data-testid="stMetricValue"] {
    font-family: var(--font-tight) !important;
    font-size: 2rem !important;
    color: var(--navy) !important;
    font-weight: 700 !important;
}

/* ── Primary buttons ──────────────────────────────────────────────── */
[data-testid="stButton"] button[kind="primary"] {
    background: var(--orange) !important;
    border: none !important;
    color: white !important;
    font-family: var(--font-sans) !important;
    font-weight: 600 !important;
    border-radius: var(--radius) !important;
    transition: background 0.15s, box-shadow 0.15s !important;
}
[data-testid="stButton"] button[kind="primary"]:hover {
    background: #D95F28 !important;
    box-shadow: 0 2px 8px rgba(240,113,56,0.35) !important;
}
[data-testid="stButton"] button[kind="secondary"] {
    background: var(--white) !important;
    border: 1px solid var(--border) !important;
    color: var(--text-dark) !important;
    font-family: var(--font-sans) !important;
    font-weight: 500 !important;
    border-radius: var(--radius) !important;
}
[data-testid="stButton"] button[kind="secondary"]:hover {
    border-color: var(--navy) !important;
    color: var(--navy) !important;
}

/* ── Text inputs / textarea ───────────────────────────────────────── */
[data-testid="stTextArea"] textarea,
[data-testid="stTextInput"] input {
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    font-family: var(--font-sans) !important;
    font-size: 0.94rem !important;
    background: var(--white) !important;
    color: var(--text-dark) !important;
    transition: border-color 0.15s !important;
}
[data-testid="stTextArea"] textarea:focus,
[data-testid="stTextInput"] input:focus {
    border-color: var(--navy) !important;
    box-shadow: 0 0 0 3px rgba(34,66,124,0.12) !important;
    outline: none !important;
}

/* ── Selectbox ────────────────────────────────────────────────────── */
[data-testid="stSelectbox"] > div > div {
    border-color: var(--border) !important;
    border-radius: var(--radius) !important;
    font-family: var(--font-sans) !important;
}

/* ── Expander ─────────────────────────────────────────────────────── */
[data-testid="stExpander"] {
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    background: var(--white) !important;
}

/* ── Footer ───────────────────────────────────────────────────────── */
.bw-footer {
    text-align: center;
    color: var(--text-mid);
    font-size: 0.82rem;
    padding: 1.5rem 0 0.5rem;
    border-top: 1px solid var(--border);
    font-family: var(--font-sans);
}
.bw-footer strong { color: var(--navy); }

/* ── Page title override ──────────────────────────────────────────── */
h1 {
    font-family: var(--font-serif) !important;
    font-size: 1.85rem !important;
    font-weight: 700 !important;
    letter-spacing: -0.02em !important;
    color: var(--navy) !important;
}
h2 {
    font-family: var(--font-serif) !important;
    font-size: 1.35rem !important;
    font-weight: 600 !important;
    color: var(--navy) !important;
}
h3 {
    font-family: var(--font-tight) !important;
    font-size: 1.05rem !important;
    font-weight: 700 !important;
    color: var(--navy) !important;
    letter-spacing: 0.01em !important;
}

/* ── Dividers ─────────────────────────────────────────────────────── */
hr {
    border: none !important;
    border-top: 1px solid var(--border) !important;
    margin: 1.2rem 0 !important;
}
"""

# ── Public API ────────────────────────────────────────────────────────────────

def apply_theme():
    """
    Inject the master CSS into the current Streamlit page.
    Call this immediately after st.set_page_config() in every page.
    """
    st.markdown(f"<style>{_CSS}</style>", unsafe_allow_html=True)


def render_sidebar(active: str = "home"):
    """
    Render the branded sidebar with the City crest and nav links.

    ARGS:
        active: "home" | "qa" | "wizard"
    """
    with st.sidebar:
        # ── Department title ABOVE logo, centered ────────────────────────
        st.markdown(
            f"<div style='"
            f"padding:1.2rem 1rem 0.4rem;"
            f"text-align:center;"
            f"'>"
            f"<div style='"
            f"font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;"
            f"font-size:1.15rem;"
            f"font-weight:700;"
            f"color:{NAVY};"
            f"line-height:1.3;"
            f"letter-spacing:0.01em;"
            f"'>City of Brentwood</div>"
            f"<div style='"
            f"font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;"
            f"font-size:1.0rem;"
            f"font-weight:600;"
            f"color:{MID_BLUE};"
            f"letter-spacing:0.02em;"
            f"margin-top:0.2rem;"
            f"'>Engineering Department</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

        # ── Color crest via GitHub raw URL ─────────────────────────────────
        # Using a URL instead of bytes/base64 means the browser fetches and
        # caches the image by URL. After the first load, 0 bytes are sent
        # over the websocket for the logo on every subsequent render.
        # GitHub raw URLs are served from a CDN with cache headers.
        st.markdown(
            "<div style='display:flex;justify-content:center;padding:0.4rem 0 0.8rem;'>"
            "<img src='https://raw.githubusercontent.com/blackb46/engineering-ai-assistant-v2/main/assets/BrentwoodCrestLogo-RGB.png' "
            "style='width:120px;height:auto;' "
            "alt='City of Brentwood Seal'>"
            "</div>",
            unsafe_allow_html=True,
        )
        # ── Divider + nav label + version — combined into 1 st.markdown call ──
        # (merging these reduces websocket message count from 11 to 7 per render)
        st.markdown(
            f"<hr class='bw-nav-divider'>"
            f"<div class='bw-nav-section'>Navigation</div>",
            unsafe_allow_html=True,
        )

        _nav_link("app.py",                     "Dashboard",    active == "home",   "🏛")
        _nav_link("pages/1_QA_Mode.py",         "Q&A Mode",     active == "qa",     "🔍")
        _nav_link("pages/2_Wizard_Mode.py",     "Wizard Mode",  active == "wizard", "📋")
        # Performance profiler hidden from nav — file kept in repo at pages/3_Performance.py
        # To re-enable: uncomment the line below and redeploy
        # _nav_link("pages/3_Performance.py",   "Performance",  active == "perf",   "⏱️")

        st.markdown(
            f"<hr class='bw-nav-divider'>"
            f"<div class='bw-version-badge'>"
            f"Engineering AI Assistant<br>"
            f"<span style='color:{TEXT_MID}'>v2.0 — Powered by Claude</span>"
            f"</div>",
            unsafe_allow_html=True,
        )


def _nav_link(page: str, label: str, is_active: bool, icon: str = ""):
    """Render a single sidebar nav link as a Streamlit page_link.
    Wrapper divs removed — active state handled by CSS targeting the
    [data-testid='stPageLink'] element directly, saving 2 st.markdown()
    calls per nav item (8 fewer widget messages per render).
    """
    st.page_link(page, label=f"{icon}  {label}")


def page_header(title: str, subtitle: str = ""):
    """
    Render the standard Brentwood navy page header band with color crest logo.
    Uses st.columns + st.image so the logo is never embedded as a base64 string.
    st.image() sends PNG bytes once; browser caches on subsequent renders.
    """
    sub_block = f"<p class='subtitle'>{subtitle}</p>" if subtitle else ""

    # Navy header band — logo served via GitHub URL (browser-cached after first load)
    st.markdown(
        f"""
        <div class="bw-page-header">
            <img src="https://raw.githubusercontent.com/blackb46/engineering-ai-assistant-v2/main/assets/BrentwoodCrestLogo-RGB.png"
                 style="height:80px;width:auto;flex-shrink:0;
                        filter:drop-shadow(0 2px 4px rgba(0,0,0,0.35));"
                 alt="City of Brentwood Seal">
            <div style="flex:1;text-align:center;">
                <h1>{title}</h1>
                {sub_block}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_heading(text: str):
    """Render a small all-caps section divider heading."""
    st.markdown(
        f"<div class='bw-section-heading'>{text}</div>",
        unsafe_allow_html=True,
    )


def footer():
    """Render the standard page footer."""
    st.markdown(
        "<div class='bw-footer'>"
        "<strong>City of Brentwood</strong> Engineering AI Assistant v2.0 &nbsp;·&nbsp; "
        "Engineering Department &nbsp;·&nbsp; Powered by Claude API"
        "</div>",
        unsafe_allow_html=True,
    )
