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
def _get_logo_path() -> Path:
    """Find the logo file relative to this module."""
    # Works both locally and on Streamlit Cloud
    candidates = [
        # theme.py lives in utils/ — logo is in assets/ at repo root
        Path(__file__).parent.parent / "assets" / "BrentwoodCrestLogo-BW.png",
        # Or directly in utils/assets/
        Path(__file__).parent / "assets" / "BrentwoodCrestLogo-BW.png",
        # Or at repo root
        Path(__file__).parent.parent / "BrentwoodCrestLogo-BW.png",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def _logo_b64() -> str:
    """Return the BW logo as a base64 data URI, or empty string if not found."""
    p = _get_logo_path()
    if p is None:
        return ""
    with open(p, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    return f"data:image/png;base64,{data}"


# ── Master CSS ────────────────────────────────────────────────────────────────
_CSS = """
/* ── Google Fonts ─────────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Barlow:wght@400;500;600;700&family=Barlow+Condensed:wght@600;700&family=Libre+Baskerville:wght@700&display=swap');

/* ── Root tokens ──────────────────────────────────────────────────── */
:root {
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
    font-family: 'Barlow', sans-serif !important;
    color: var(--text-dark) !important;
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
    font-family: 'Barlow', sans-serif;
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
    font-family: 'Barlow', sans-serif;
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
    font-family: 'Barlow', sans-serif;
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
    font-family: 'Libre Baskerville', serif;
    font-size: 1.6rem;
    color: var(--white) !important;
    margin: 0;
    line-height: 1.2;
}
.bw-page-header .subtitle {
    font-family: 'Barlow', sans-serif;
    font-size: 0.88rem;
    color: rgba(255,255,255,0.75);
    margin: 0.2rem 0 0;
}

/* ── Section heading style ────────────────────────────────────────── */
.bw-section-heading {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--midblue);
    border-bottom: 2px solid var(--border);
    padding-bottom: 0.4rem;
    margin: 1.5rem 0 0.8rem;
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
    font-family: 'Barlow Condensed', sans-serif;
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
    font-family: 'Barlow', sans-serif;
    box-shadow: var(--shadow-sm);
}
.bw-answer-label {
    font-family: 'Barlow Condensed', sans-serif;
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
    font-family: 'Barlow Condensed', sans-serif;
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
    font-family: 'Barlow', sans-serif;
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
    font-family: 'Barlow', sans-serif;
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
    font-family: 'Barlow', sans-serif;
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
    font-family: 'Barlow', sans-serif;
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
    font-family: 'Barlow', sans-serif;
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
    font-family: 'Barlow', sans-serif;
}

/* ── Feedback boxes ───────────────────────────────────────────────── */
.bw-feedback-panel {
    background: #FFF8F5 !important;
    color: var(--text-dark) !important;
    border: 1px solid #FDBA74;
    border-radius: var(--radius);
    padding: 1.2rem 1.4rem;
    margin: 0.8rem 0;
    font-family: 'Barlow', sans-serif;
}
.bw-success-msg {
    background: #F0FDF4 !important;
    color: #166534 !important;
    border: 1px solid #BBF7D0;
    border-radius: var(--radius);
    padding: 0.8rem 1.2rem;
    margin: 0.8rem 0;
    font-family: 'Barlow', sans-serif;
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
    font-family: 'Libre Baskerville', serif;
    font-size: 1.3rem;
    margin: 0 0 0.3rem;
}
.bw-wizard-header p {
    color: rgba(255,255,255,0.8) !important;
    font-size: 0.88rem;
    margin: 0;
    font-family: 'Barlow', sans-serif;
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
    font-family: 'Barlow Condensed', sans-serif;
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
    font-family: 'Barlow', sans-serif !important;
    font-size: 0.8rem !important;
    color: var(--text-mid) !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
}
[data-testid="stMetricValue"] {
    font-family: 'Barlow Condensed', sans-serif !important;
    font-size: 2rem !important;
    color: var(--navy) !important;
    font-weight: 700 !important;
}

/* ── Primary buttons ──────────────────────────────────────────────── */
[data-testid="stButton"] button[kind="primary"] {
    background: var(--orange) !important;
    border: none !important;
    color: white !important;
    font-family: 'Barlow', sans-serif !important;
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
    font-family: 'Barlow', sans-serif !important;
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
    font-family: 'Barlow', sans-serif !important;
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
    font-family: 'Barlow', sans-serif !important;
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
    font-family: 'Barlow', sans-serif;
}
.bw-footer strong { color: var(--navy); }

/* ── Page title override ──────────────────────────────────────────── */
h1 {
    font-family: 'Libre Baskerville', serif !important;
    color: var(--navy) !important;
}
h2, h3 {
    font-family: 'Barlow Condensed', sans-serif !important;
    color: var(--navy) !important;
    font-weight: 700 !important;
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
    logo_path = _get_logo_path()

    with st.sidebar:
        # ── Crest + title ───────────────────────────────────────────────
        st.markdown("<div style='padding: 1.2rem 1rem 0.6rem;'>", unsafe_allow_html=True)
        if logo_path:
            st.image(str(logo_path), width=54)
        st.markdown(
            "<div style='"
            "font-family:Barlow Condensed,sans-serif;"
            "font-size:1.05rem;font-weight:700;"
            f"color:{NAVY};line-height:1.2;margin-top:0.4rem;"
            "'>City of Brentwood<br>"
            "<span style='font-weight:400;font-size:0.88rem;"
            f"color:{TEXT_MID};'>Engineering Department</span>"
            "</div>",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<hr class='bw-nav-divider'>", unsafe_allow_html=True)

        # ── Nav links ───────────────────────────────────────────────────
        st.markdown("<div class='bw-nav-section'>Navigation</div>", unsafe_allow_html=True)

        _nav_link("app.py",                 "Dashboard",    active == "home",   "🏛")
        _nav_link("pages/1_QA_Mode.py",     "Q&A Mode",     active == "qa",     "🔍")
        _nav_link("pages/2_Wizard_Mode.py", "Wizard Mode",  active == "wizard", "📋")

        st.markdown("<hr class='bw-nav-divider'>", unsafe_allow_html=True)

        # ── Version tag ─────────────────────────────────────────────────
        st.markdown(
            f"<div class='bw-version-badge'>"
            f"Engineering AI Assistant<br>"
            f"<span style='color:{TEXT_MID}'>v2.0 — Powered by Claude</span>"
            f"</div>",
            unsafe_allow_html=True,
        )


def _nav_link(page: str, label: str, is_active: bool, icon: str = ""):
    """Render a single sidebar nav link as a Streamlit page_link with styling."""
    # Use Streamlit's page_link but wrap it in styled container
    css_class = "bw-nav-link active" if is_active else "bw-nav-link"
    # We use page_link for actual routing; style it via CSS class override
    active_class = "active" if is_active else ""
    st.markdown(
        f"<div class='nav-item-wrap {active_class}'>",
        unsafe_allow_html=True,
    )
    st.page_link(page, label=f"{icon}  {label}")
    st.markdown("</div>", unsafe_allow_html=True)


def page_header(title: str, subtitle: str = "", icon_html: str = ""):
    """
    Render the standard Brentwood navy page header band.

    ARGS:
        title:      Main title text (serif font)
        subtitle:   Smaller subtitle line beneath
        icon_html:  Optional SVG or emoji for the left icon slot
    """
    icon_block = (
        f"<div style='flex-shrink:0;width:44px;height:44px;"
        f"background:rgba(255,255,255,0.15);border-radius:8px;"
        f"display:flex;align-items:center;justify-content:center;"
        f"font-size:1.5rem;'>{icon_html}</div>"
    ) if icon_html else ""

    st.markdown(
        f"""
        <div class="bw-page-header">
            {icon_block}
            <div>
                <h1>{title}</h1>
                {"<p class='subtitle'>"+subtitle+"</p>" if subtitle else ""}
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
