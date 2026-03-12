"""
app.py
======
City of Brentwood Engineering AI Assistant - V2
Main application entry point and dashboard.
"""

# ── PyTorch / Streamlit watcher compatibility fix ─────────────────────────────
# MUST be the very first import — before streamlit and any torch-dependent libs.
# Streamlit 1.43+ file watcher crashes when scanning torch.classes internals.
import torch
torch.classes.__path__ = []

import sys
from pathlib import Path
import streamlit as st

# Add utils/ to path for RAG/DB modules; repo root is already on sys.path
sys.path.append(str(Path(__file__).parent / "utils"))

from drive_loader import load_database, get_db_status_for_admin
from rag_engine   import get_rag_engine
from database     import AuditLogger
from theme        import apply_theme, render_sidebar, page_header, section_heading, footer, get_favicon

st.set_page_config(
    page_title="Engineering AI Assistant — City of Brentwood, TN",
    page_icon=get_favicon(),
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_theme()
render_sidebar(active="home")

# ── Startup ───────────────────────────────────────────────────────────────────
# WHY cache_resource:
#   The old pattern called get_rag_engine() at module level, which Streamlit
#   re-executes on every page render — including during the cold-start websocket
#   handshake before the session is initialized. That race condition causes the
#   "SessionInfo not initialized" popup and requires multiple button clicks before
#   the page responds.
#
#   st.cache_resource runs the function body exactly ONCE per server process and
#   returns the cached result on all subsequent calls. The engine loads once,
#   is shared across all users and all rerenders, and never races with session init.
@st.cache_resource(show_spinner=False)
def _load_engine():
    """Load database and RAG engine once. Cached for the lifetime of the app."""
    db = load_database()
    if not db["success"]:
        return db, False, {}, db.get("error", "Database load failed")
    try:
        eng = get_rag_engine(db["local_path"])
        return db, eng.is_ready(), eng.get_collection_stats(), (
            eng.get_init_error() if not eng.is_ready() else None
        )
    except Exception as e:
        return db, False, {}, str(e)

with st.spinner("Loading AI engine..."):
    db_info, engine_ready, engine_stats, engine_error = _load_engine()

if "audit_logger" not in st.session_state:
    st.session_state.audit_logger = AuditLogger()

# ── Header ────────────────────────────────────────────────────────────────────
page_header(
    title="Engineering AI Assistant",
    subtitle="City of Brentwood, Tennessee — Engineering Department",
)

if not db_info["success"]:
    st.error(
        "The document database could not be loaded. "
        "Q&A Mode and Wizard Mode are unavailable. "
        "Run build_corpus.py in Google Colab, push to GitHub, then reboot this app."
    )
    st.stop()

# ── Mode selection ─────────────────────────────────────────────────────────────
section_heading("Select a Mode")

col_qa, col_wiz = st.columns(2, gap="large")

with col_qa:
    st.markdown("""
    <div class="bw-mode-card">
        <div class="mode-icon">🔍</div>
        <h3>Q&amp;A Mode</h3>
        <p>Ask natural language questions about engineering policy. Answers are
        grounded in the Municipal Code and Engineering Policy Manual with
        precise footnote citations.</p>
        <p style="margin-top:0.6rem;font-size:0.83rem;color:#2F5C9C;font-weight:600;">
        Policy lookups &nbsp;·&nbsp; Setback requirements &nbsp;·&nbsp; Design standards
        </p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)
    if st.button("Open Q&A Mode →", key="qa_btn",
                 use_container_width=True, type="primary"):
        st.switch_page("pages/1_QA_Mode.py")
    if not engine_ready:
        st.caption("⚠ RAG engine not ready — see System Status below")

with col_wiz:
    st.markdown("""
    <div class="bw-mode-card">
        <div class="mode-icon">📋</div>
        <h3>Wizard Mode</h3>
        <p>Step-by-step guided permit review workflows with interactive checklists.
        Export to Word, LAMA CSV, and Bluebeam BAX formats.</p>
        <p style="margin-top:0.6rem;font-size:0.83rem;color:#2F5C9C;font-weight:600;">
        Site plan reviews &nbsp;·&nbsp; Subdivision approvals &nbsp;·&nbsp; Stormwater compliance
        </p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)
    if st.button("Open Wizard Mode →", key="wiz_btn",
                 use_container_width=True, type="primary"):
        st.switch_page("pages/2_Wizard_Mode.py")

# ── Quick start ───────────────────────────────────────────────────────────────
with st.expander("Quick Start Guide", expanded=False):
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("""
**Q&A Mode** — direct policy questions
- Type your question in plain English
- Searches all 26 Brentwood engineering documents
- Answers include footnote citations (¹ ²) to specific code sections
- Flag any response you believe is incorrect
        """)
    with col_b:
        st.markdown("""
**Understanding answer flags**

| Flag | Meaning | Action |
|---|---|---|
| ⚠️ More Restrictive | Policy Manual adds requirements | Follow stricter standard |
| 🔴 Discrepancy | Sources conflict | Verify with City Engineer |
| *(no flag)* | Sources consistent | Use with professional judgment |
        """)

# ── System status ─────────────────────────────────────────────────────────────
with st.expander("System Status", expanded=False):
    col_db, col_engine, col_api = st.columns(3)

    with col_db:
        if db_info["success"]:
            st.markdown(f"""<div class="bw-status-ok">
                ✅ <strong>Document Database</strong><br>
                {db_info.get('size_mb',0)} MB &nbsp;·&nbsp; Ready<br>
                <small>Updated: {db_info.get('sync_timestamp','unknown')}</small>
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"""<div class="bw-status-err">
                ✗ <strong>Document Database</strong><br>
                {db_info.get('error','Unknown error')[:120]}
            </div>""", unsafe_allow_html=True)

    with col_engine:
        if engine_ready:
            st.markdown(f"""<div class="bw-status-ok">
                ✅ <strong>RAG Engine</strong><br>
                {engine_stats.get('total_chunks',0):,} chunks indexed<br>
                <small>Collection: {engine_stats.get('collection_name','')}</small>
            </div>""", unsafe_allow_html=True)
        elif db_info["success"]:
            st.markdown(f"""<div class="bw-status-err">
                ✗ <strong>RAG Engine</strong><br>
                {str(engine_error or 'Initialization failed')[:120]}
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown("""<div class="bw-status-warn">
                ⚠ <strong>RAG Engine</strong><br>Waiting for database
            </div>""", unsafe_allow_html=True)

    with col_api:
        try:
            api_key_set = bool(st.secrets.get("CLAUDE_API_KEY"))
        except Exception:
            api_key_set = False

        if api_key_set and engine_ready:
            st.markdown(f"""<div class="bw-status-ok">
                ✅ <strong>Claude API</strong><br>Configured and ready<br>
                <small>{engine_stats.get('claude_model','claude-sonnet')}</small>
            </div>""", unsafe_allow_html=True)
        elif api_key_set:
            st.markdown("""<div class="bw-status-warn">
                ⚠ <strong>Claude API</strong><br>Key set — engine not ready
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown("""<div class="bw-status-err">
                ✗ <strong>Claude API</strong><br>CLAUDE_API_KEY not set in secrets
            </div>""", unsafe_allow_html=True)

# ── Usage stats — collapsed, below System Status ──────────────────────────────
# Collapsed by default so the dashboard stays clean; staff can expand when needed.
with st.expander("Usage Statistics — Last 7 Days", expanded=False):
    try:
        stats = st.session_state.audit_logger.get_usage_stats(days=7)
        m1, m2, m3, m4 = st.columns(4)
        with m1: st.metric("Total Queries", stats["total_queries"])
        with m2: st.metric("Abstentions", stats["abstention_count"],
                           help="Questions the system could not answer from documents")
        with m3: st.metric("Discrepancy Flags", stats["discrepancy_count"],
                           help="Queries where Code and Policy Manual sources may conflict")
        with m4: st.metric("Flagged by Staff", stats["flagged_responses"],
                           help="Responses marked for review by engineering staff")
    except Exception:
        st.caption("Usage statistics will appear here after first queries.")

footer()
