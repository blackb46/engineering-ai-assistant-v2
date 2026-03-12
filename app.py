"""
app.py
======
City of Brentwood Engineering AI Assistant - V2
Main application entry point and dashboard.

PURPOSE:
    This is the first file Streamlit runs when the app starts. It:

    1. DOWNLOADS the ChromaDB database from Google Drive (once per session)
    2. INITIALIZES the RAG engine (loads embedding model, connects to DB)
    3. DISPLAYS the dashboard with system status and mode selection
    4. PROVIDES navigation to Q&A Mode and Wizard Mode

V2 CHANGES FROM V1:
    - Triggers drive_loader.load_database() at startup
    - Shows real database sync status (file count, size, timestamp)
    - Shows RAG engine health (chunk count, model, collection name)
    - Removed hardcoded vectorstore/ path check
    - Updated version number and status display

STARTUP SEQUENCE:
    app.py loads
        → drive_loader.load_database()    (downloads ChromaDB from Drive)
        → get_rag_engine(db_path)         (loads embedding model)
        → AuditLogger()                   (opens SQLite)
        → Dashboard renders

AUTHOR:  City of Brentwood Engineering Department AI Assistant Project
VERSION: 2.0
"""

import sys
from pathlib import Path

import streamlit as st

sys.path.append(str(Path(__file__).parent / "utils"))

from drive_loader  import load_database, get_db_status_for_admin
from rag_engine    import get_rag_engine
from database      import AuditLogger

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG — must be first Streamlit call in the file
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Engineering AI Assistant — City of Brentwood",
    page_icon="👷",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# STYLING
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
    [data-testid="stSidebarNav"] { display: none; }

    .main-header {
        background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .main-header h1 { margin: 0; font-size: 2.2rem; }
    .main-header p  { margin: 0.5rem 0 0 0; opacity: 0.9; font-size: 1.05rem; }

    .status-ok {
        background: #d4edda !important;
        color: #155724 !important;
        border: 1px solid #c3e6cb;
        border-left: 4px solid #28a745;
        border-radius: 6px;
        padding: 0.75rem 1rem;
        margin: 0.3rem 0;
        font-size: 0.92em;
    }
    .status-warn {
        background: #fff8e1 !important;
        color: #5d4037 !important;
        border: 1px solid #ffe082;
        border-left: 4px solid #f9a825;
        border-radius: 6px;
        padding: 0.75rem 1rem;
        margin: 0.3rem 0;
        font-size: 0.92em;
    }
    .status-err {
        background: #fff5f5 !important;
        color: #7b2020 !important;
        border: 1px solid #fc8181;
        border-left: 4px solid #e53e3e;
        border-radius: 6px;
        padding: 0.75rem 1rem;
        margin: 0.3rem 0;
        font-size: 0.92em;
    }
    .mode-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        border: 1px solid #e0e0e0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.07);
        height: 100%;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR NAVIGATION
# ─────────────────────────────────────────────────────────────────────────────

st.sidebar.title("🧭 Navigation")
st.sidebar.markdown("---")
st.sidebar.page_link("app.py",                 label="🏡 Dashboard")
st.sidebar.page_link("pages/1_QA_Mode.py",     label="💬 Q&A Mode")
st.sidebar.page_link("pages/2_Wizard_Mode.py", label="🧙‍♂️ Wizard Mode")
st.sidebar.markdown("---")
st.sidebar.markdown("**Engineering AI Assistant**")
st.sidebar.markdown("v2.0 | City of Brentwood, TN")

# ─────────────────────────────────────────────────────────────────────────────
# STARTUP — load database and initialize engine
# These calls are cached by @st.cache_resource — run once per server session.
# ─────────────────────────────────────────────────────────────────────────────

with st.spinner("Loading engineering document database..."):
    db_info = load_database()

# Attempt to initialize RAG engine (even if DB load failed, we try gracefully)
engine_ready  = False
engine_stats  = {}
engine_error  = None

if db_info["success"]:
    try:
        engine = get_rag_engine(db_info["local_path"])
        engine_ready = engine.is_ready()
        engine_stats = engine.get_collection_stats()
        engine_error = engine.get_init_error() if not engine_ready else None
    except Exception as e:
        engine_error = str(e)

# Initialize audit logger (stored in session state so it persists across pages)
if "audit_logger" not in st.session_state:
    st.session_state.audit_logger = AuditLogger()

# ─────────────────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("""
<div class="main-header">
    <h1>👷 Engineering AI Assistant</h1>
    <p>City of Brentwood, Tennessee — Engineering Department</p>
    <p style="font-size: 0.85rem; opacity: 0.75; margin-top: 0.3rem;">
        Answers grounded in the Engineering Policy Manual and Municipal Code
    </p>
</div>
""", unsafe_allow_html=True)

# Hard stop if database failed — app cannot function without it
if not db_info["success"]:
    st.error(
        "The document database could not be loaded. "
        "Q&A Mode and Wizard Mode are unavailable until this is resolved. "
        "Run build_corpus.py in Google Colab and push the database to GitHub "
        "using the notebook's push step, then reboot this app."
    )
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# MODE SELECTION
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("---")
st.subheader("🎯 Choose Your Mode")

col_qa, col_wiz = st.columns(2)

with col_qa:
    st.markdown("""
    <div class="mode-card">
        <h3>💬 Q&A Mode</h3>
        <p>Ask natural language questions about engineering policy and receive
        cited answers grounded in the Municipal Code and Engineering Policy Manual.</p>
        <p><strong>Best for:</strong> Quick policy lookups, setback requirements,
        buffer widths, design standards, permit questions.</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button(
        "🚀 Launch Q&A Mode",
        key="qa_btn",
        disabled=not engine_ready,
        use_container_width=True,
        type="primary",
    ):
        st.switch_page("pages/1_QA_Mode.py")
    if not engine_ready:
        st.caption("⚠️ Unavailable — RAG engine not ready")

with col_wiz:
    st.markdown("""
    <div class="mode-card">
        <h3>🧙‍♂️ Wizard Mode</h3>
        <p>Step-by-step guided workflows for permit reviews and compliance checks.
        Follow interactive checklists tailored to the project type.</p>
        <p><strong>Best for:</strong> Site plan reviews, subdivision approvals,
        stormwater compliance, systematic permit checklists.</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button(
        "🚀 Launch Wizard Mode",
        key="wiz_btn",
        use_container_width=True,
    ):
        st.switch_page("pages/2_Wizard_Mode.py")

# ─────────────────────────────────────────────────────────────────────────────
# USAGE STATS (last 7 days)
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("---")
st.subheader("📊 Usage — Last 7 Days")

try:
    stats = st.session_state.audit_logger.get_usage_stats(days=7)

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Total Queries",      stats["total_queries"])
    with m2:
        st.metric("Abstentions",         stats["abstention_count"],
                  help="Questions the system couldn't answer from documents")
    with m3:
        st.metric("Discrepancy Flags",   stats["discrepancy_count"],
                  help="Queries where Code and Policy Manual sources may conflict")
    with m4:
        st.metric("Flagged by Engineers", stats["flagged_responses"],
                  help="Responses marked for review by engineering staff")

except Exception:
    st.caption("Usage statistics will appear here after first queries.")

# ─────────────────────────────────────────────────────────────────────────────
# QUICK START GUIDE
# ─────────────────────────────────────────────────────────────────────────────

with st.expander("📚 Quick Start Guide"):
    st.markdown("""
    ### Getting Started

    **Q&A Mode** — best for direct policy questions
    - Type your question in plain English
    - The system searches across all 26 Brentwood engineering documents
    - Answers include footnote citations (¹ ²) linked to specific sections
    - Flag any response you believe is incorrect — it goes to the review queue

    **Wizard Mode** — best for systematic permit reviews
    - Select the review type (site plan, subdivision, stormwater, etc.)
    - Work through the step-by-step compliance checklist
    - Generate documentation for the project file

    ### Understanding Answer Flags

    | Flag | Meaning | Action |
    |---|---|---|
    | ⚠️ More Restrictive Policy | Policy Manual adds requirements beyond the Code | Follow the stricter standard — both apply |
    | 🔴 Discrepancy Identified | Sources appear to conflict | Do not act on this answer alone — verify with City Engineer |
    | *(no flag)* | Sources are consistent | Answer can be used with normal professional judgment |

    ### Tips for Best Results
    - Be specific: include measurements, street names, or section numbers when known
    - If the system abstains, try rephrasing or ask about a narrower aspect
    - Always apply professional engineering judgment — this tool supports, not replaces, your expertise
    """)

# ─────────────────────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("---")

# ── System Status (collapsed by default) ──────────────────────────────────────
with st.expander("⚙️ System Status", expanded=False):
    col_db, col_engine, col_api = st.columns(3)

    with col_db:
        if db_info["success"]:
            sync_ts = db_info.get("sync_timestamp", "unknown")
            size_mb = db_info.get("size_mb", 0)
            st.markdown(f"""
            <div class="status-ok">
                ✅ <strong>Document Database</strong><br>
                {size_mb} MB | Ready<br>
                <small>Last updated: {sync_ts}</small>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="status-err">
                ❌ <strong>Document Database</strong><br>
                {db_info.get('error', 'Unknown error')[:120]}
            </div>
            """, unsafe_allow_html=True)

    with col_engine:
        if engine_ready:
            chunk_count = engine_stats.get("total_chunks", 0)
            collection  = engine_stats.get("collection_name", "")
            st.markdown(f"""
            <div class="status-ok">
                ✅ <strong>RAG Engine</strong><br>
                {chunk_count:,} chunks indexed<br>
                <small>Collection: {collection}</small>
            </div>
            """, unsafe_allow_html=True)
        elif db_info["success"]:
            st.markdown(f"""
            <div class="status-err">
                ❌ <strong>RAG Engine</strong><br>
                {str(engine_error or 'Initialization failed')[:120]}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="status-warn">
                ⚠️ <strong>RAG Engine</strong><br>
                Waiting for database
            </div>
            """, unsafe_allow_html=True)

    with col_api:
        try:
            api_key_set = bool(st.secrets.get("CLAUDE_API_KEY"))
        except Exception:
            api_key_set = False

        if api_key_set and engine_ready:
            model = engine_stats.get("claude_model", "claude-sonnet")
            st.markdown(f"""
            <div class="status-ok">
                ✅ <strong>Claude API</strong><br>
                Configured and ready<br>
                <small>{model}</small>
            </div>
            """, unsafe_allow_html=True)
        elif api_key_set:
            st.markdown("""
            <div class="status-warn">
                ⚠️ <strong>Claude API</strong><br>
                Key configured — engine not ready
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="status-err">
                ❌ <strong>Claude API</strong><br>
                CLAUDE_API_KEY not set in secrets
            </div>
            """, unsafe_allow_html=True)

st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #888; font-size: 0.85rem;'>"
    "Engineering AI Assistant v2.0 &nbsp;|&nbsp; "
    "City of Brentwood Engineering Department &nbsp;|&nbsp; "
    "Powered by Claude API &nbsp;|&nbsp; Built with Streamlit"
    "</div>",
    unsafe_allow_html=True,
)
