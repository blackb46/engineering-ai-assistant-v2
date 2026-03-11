"""
1_QA_Mode.py
============
City of Brentwood Engineering AI Assistant - V2
Q&A Mode — direct policy question answering with footnote citations.

PURPOSE:
    Primary interface for engineers to ask natural language questions
    about municipal engineering policy and receive grounded, cited answers.

V2 CHANGES FROM V1:
    - Uses V2 RAGEngine (get_rag_engine) loaded from Drive database
    - Displays footnote-style citations (¹ ² ³) in a numbered list
    - Shows discrepancy flags (⚠️ more restrictive / 🔴 conflict)
    - Passes discrepancy_flag and abstained to google_sheets logger
    - Passes full V2 fields to AuditLogger
    - Removed chunk/similarity score display (replaced by citation list)

V1 COMPATIBILITY:
    AuditLogger.log_query() and log_flagged_response() V1 signatures
    still accepted — no changes needed to those imports.

AUTHOR:  City of Brentwood Engineering Department AI Assistant Project
VERSION: 2.0
"""

import sys
from pathlib import Path

import streamlit as st

sys.path.append(str(Path(__file__).parent.parent / "utils"))

from drive_loader import load_database
from rag_engine   import get_rag_engine
from database     import AuditLogger
from google_sheets import log_flagged_response

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Q&A Mode — Brentwood Engineering AI",
    page_icon="💬",
    layout="wide",
)

# ─────────────────────────────────────────────────────────────────────────────
# STYLING
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
    [data-testid="stSidebarNav"] { display: none; }

    .answer-box {
        background: #e7f3ff !important;
        color: #1a1a2e !important;
        border: 1px solid #bee5eb;
        border-radius: 8px;
        padding: 1.2rem 1.5rem;
        margin: 1rem 0;
        line-height: 1.7;
        font-size: 1rem;
    }
    .citation-box {
        background: #f8f9fa !important;
        color: #1a1a2e !important;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 1rem 1.5rem;
        margin: 0.5rem 0;
        font-size: 0.9em;
    }
    .citation-box ol {
        margin: 0;
        padding-left: 1.5rem;
    }
    .citation-box li {
        margin-bottom: 0.4rem;
        line-height: 1.5;
    }
    .flag-more-restrictive {
        background: #fff8e1 !important;
        color: #1a1a2e !important;
        border: 1px solid #ffe082;
        border-left: 4px solid #f9a825;
        border-radius: 8px;
        padding: 0.8rem 1.2rem;
        margin: 0.5rem 0;
        font-size: 0.92em;
    }
    .flag-conflict {
        background: #fff5f5 !important;
        color: #1a1a2e !important;
        border: 1px solid #fc8181;
        border-left: 4px solid #e53e3e;
        border-radius: 8px;
        padding: 0.8rem 1.2rem;
        margin: 0.5rem 0;
        font-size: 0.92em;
    }
    .abstain-box {
        background: #f7f7f7 !important;
        color: #555 !important;
        border: 1px solid #ccc;
        border-left: 4px solid #999;
        border-radius: 8px;
        padding: 0.8rem 1.2rem;
        margin: 0.5rem 0;
        font-size: 0.95em;
    }
    .feedback-popup {
        background: #fff5f5 !important;
        color: #1a1a2e !important;
        border: 2px solid #fc8181;
        border-radius: 8px;
        padding: 1.5rem;
        margin: 1rem 0;
    }
    .success-message {
        background: #d4edda !important;
        color: #155724 !important;
        border: 1px solid #c3e6cb;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR NAVIGATION
# ─────────────────────────────────────────────────────────────────────────────

st.sidebar.title("🧭 Navigation")
st.sidebar.markdown("---")
st.sidebar.page_link("app.py",                  label="🏡 Dashboard")
st.sidebar.page_link("pages/1_QA_Mode.py",      label="💬 Q&A Mode")
st.sidebar.page_link("pages/2_Wizard_Mode.py",  label="🧙‍♂️ Wizard Mode")
st.sidebar.markdown("---")
st.sidebar.markdown("**Engineering AI Assistant**")
st.sidebar.markdown("v2.0 | City of Brentwood, TN")


# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE INITIALIZATION
# ─────────────────────────────────────────────────────────────────────────────

def _init_session_state():
    defaults = {
        "current_result":      None,
        "current_question":    "",
        "show_feedback_form":  False,
        "feedback_submitted":  False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# ─────────────────────────────────────────────────────────────────────────────
# DISPLAY HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _display_discrepancy_flag(flag: str, note: str):
    """
    Render the discrepancy warning banner above the answer.

    ⚠️  More Restrictive Policy — amber/yellow banner
    🔴  Discrepancy Identified  — red banner
    """
    if flag == "more_restrictive":
        st.markdown(f"""
        <div class="flag-more-restrictive">
            ⚠️ <strong>More Restrictive Policy Applies</strong><br>
            {note}
        </div>
        """, unsafe_allow_html=True)

    elif flag == "conflict":
        st.markdown(f"""
        <div class="flag-conflict">
            🔴 <strong>Discrepancy Identified — Do Not Rely on This Response Alone</strong><br>
            {note}
        </div>
        """, unsafe_allow_html=True)


def _display_answer(result: dict):
    """
    Render the answer box.
    Abstained answers get a grey box instead of the blue answer box.
    """
    answer = result.get("answer", "No answer generated.")

    if result.get("abstained"):
        st.markdown(f"""
        <div class="abstain-box">
            {answer}
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="answer-box">
            {answer}
        </div>
        """, unsafe_allow_html=True)


def _display_citations(citations: list):
    """
    Render the numbered citation list below the answer.
    Each line: ¹ Full citation string
    """
    if not citations:
        return

    superscripts = ["¹","²","³","⁴","⁵","⁶","⁷","⁸","⁹","¹⁰"]

    items_html = ""
    for c in citations:
        num  = c.get("number", 1)
        sup  = superscripts[num - 1] if num <= len(superscripts) else str(num)
        text = c.get("formatted", c.get("source_citation", "Unknown source"))
        items_html += f"<li><strong>{sup}</strong> {text}</li>"

    st.markdown(f"""
    <div class="citation-box">
        <strong>Sources</strong>
        <ol style="list-style: none; padding-left: 0;">
            {items_html}
        </ol>
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN PAGE
# ─────────────────────────────────────────────────────────────────────────────

def main():
    st.title("💬 Engineering Q&A Mode")
    st.markdown(
        "Ask questions about Brentwood municipal engineering policy. "
        "All answers are grounded in the Engineering Policy Manual and Municipal Code."
    )

    _init_session_state()

    # ── Load database and initialize engine ───────────────────────────────
    db_info = load_database()
    if not db_info["success"]:
        st.error(f"❌ Database not available: {db_info['error']}")
        st.info("Return to the Dashboard and check system status.")
        if st.button("🏠 Return to Dashboard"):
            st.switch_page("app.py")
        return

    engine = get_rag_engine(db_info["local_path"])
    if not engine.is_ready():
        st.error(
            f"❌ RAG engine not ready: {engine.get_init_error() or 'Unknown error'}"
        )
        if st.button("🏠 Return to Dashboard"):
            st.switch_page("app.py")
        return

    # Initialize audit logger
    if "audit_logger" not in st.session_state:
        st.session_state.audit_logger = AuditLogger()

    st.success("✅ Q&A system ready")

    # ── Two-column layout ─────────────────────────────────────────────────
    col_main, col_sidebar = st.columns([2, 1])

    with col_main:

        # ── Question input ─────────────────────────────────────────────
        st.subheader("❓ Ask Your Question")
        question = st.text_area(
            "Enter your engineering policy question:",
            height=100,
            placeholder=(
                "e.g., What is the minimum riparian buffer width for a perennial stream?\n"
                "e.g., What are the setback requirements for retaining walls?\n"
                "e.g., What design storm frequency is required for subdivision drainage?"
            ),
            key="question_input",
        )

        col_ask, col_clear = st.columns([1, 1])
        with col_ask:
            ask_button = st.button("🔍 Get Answer", type="primary")
        with col_clear:
            if st.button("🗑️ Clear"):
                st.session_state.current_result     = None
                st.session_state.current_question   = ""
                st.session_state.show_feedback_form = False
                st.session_state.feedback_submitted = False
                st.rerun()

        # ── Process new question ───────────────────────────────────────
        if ask_button and question.strip():
            st.session_state.show_feedback_form = False
            st.session_state.feedback_submitted = False

            with st.spinner("Searching Brentwood engineering documents..."):
                try:
                    result = engine.query(question)

                    st.session_state.current_result   = result
                    st.session_state.current_question = question

                    # Log to audit database (V2 full signature)
                    row_id = st.session_state.audit_logger.log_query(
                        question         = question,
                        answer           = result.get("answer", ""),
                        sources          = result.get("sources", []),
                        chunks_used      = result.get("chunks_used", 0),
                        model_used       = result.get("model_used", "unknown"),
                        citations        = result.get("citations", []),
                        discrepancy_flag = result.get("discrepancy_flag"),
                        abstained        = result.get("abstained", False),
                        elapsed_seconds  = result.get("elapsed_seconds", 0.0),
                    )

                    # Log discrepancy separately if flagged
                    if result.get("discrepancy_flag"):
                        st.session_state.audit_logger.log_discrepancy(
                            question         = question,
                            flag_type        = result["discrepancy_flag"],
                            flag_note        = result.get("discrepancy_note", ""),
                            doc_ids_involved = [
                                c.get("doc_id", "") for c in result.get("citations", [])
                            ],
                            query_log_id     = row_id,
                        )

                except Exception as e:
                    st.error(f"❌ Error processing question: {str(e)}")
                    st.session_state.current_result = None

        # ── Display results ────────────────────────────────────────────
        if st.session_state.current_result is not None:
            result = st.session_state.current_result

            st.markdown("---")
            st.markdown(f"**Question:** {st.session_state.current_question}")

            # Discrepancy flag banner (shown above answer)
            if result.get("discrepancy_flag") and result.get("discrepancy_note"):
                _display_discrepancy_flag(
                    result["discrepancy_flag"],
                    result["discrepancy_note"],
                )

            # Answer
            st.markdown("### 📝 Answer")
            _display_answer(result)

            # Citations
            if result.get("citations"):
                _display_citations(result["citations"])

            # Performance info (collapsed by default — engineers don't need it)
            with st.expander("📊 Query details", expanded=False):
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.metric("Chunks Searched", result.get("chunks_used", 0))
                with c2:
                    st.metric("Sources Cited", len(result.get("citations", [])))
                with c3:
                    elapsed = result.get("elapsed_seconds", 0)
                    st.metric("Response Time", f"{elapsed:.1f}s")

            # ── Feedback section ───────────────────────────────────────
            st.markdown("---")
            st.markdown("### 📢 Was this answer helpful?")

            if not st.session_state.feedback_submitted:
                col_fb1, col_fb2 = st.columns(2)

                with col_fb1:
                    if st.button("👍 Yes, this helped!", use_container_width=True):
                        st.session_state.feedback_submitted = True
                        st.rerun()

                with col_fb2:
                    if st.button(
                        "👎 Needs Improvement",
                        use_container_width=True,
                        type="secondary",
                    ):
                        st.session_state.show_feedback_form = True
                        st.rerun()

            # Feedback form
            if (
                st.session_state.show_feedback_form
                and not st.session_state.feedback_submitted
            ):
                st.markdown("""
                <div class="feedback-popup">
                    <h4>🚩 Report an Issue</h4>
                    <p>Help us improve! Tell us what was wrong with this response.</p>
                </div>
                """, unsafe_allow_html=True)

                feedback_text = st.text_area(
                    "What was wrong with the response? (optional but helpful)",
                    placeholder=(
                        "Examples:\n"
                        "- The cited section number is wrong\n"
                        "- Missing the exception for lots under 1 acre\n"
                        "- The answer contradicts what I see in the manual"
                    ),
                    height=120,
                    key="feedback_text_input",
                )

                col_s1, col_s2 = st.columns(2)
                with col_s1:
                    if st.button(
                        "📤 Submit Feedback",
                        type="primary",
                        use_container_width=True,
                    ):
                        # Send to Google Sheets (V2 signature with flags)
                        success = log_flagged_response(
                            question         = st.session_state.current_question,
                            ai_response      = result.get("answer", ""),
                            user_feedback    = feedback_text,
                            discrepancy_flag = result.get("discrepancy_flag"),
                            abstained        = result.get("abstained", False),
                        )

                        # Also log to local SQLite
                        st.session_state.audit_logger.flag_response(
                            question     = st.session_state.current_question,
                            flag_type    = "negative",
                            reason       = feedback_text,
                            answer       = result.get("answer", ""),
                        )

                        if success:
                            st.session_state.feedback_submitted = True
                            st.session_state.show_feedback_form = False
                            st.rerun()
                        else:
                            st.error(
                                "❌ Could not submit to Google Sheets. "
                                "Response flagged locally — check Admin panel."
                            )

                with col_s2:
                    if st.button("❌ Cancel", use_container_width=True):
                        st.session_state.show_feedback_form = False
                        st.rerun()

            # Success message after feedback
            if st.session_state.feedback_submitted:
                st.markdown("""
                <div class="success-message">
                    ✅ <strong>Thank you for your feedback!</strong><br>
                    Your report has been submitted for review.
                </div>
                """, unsafe_allow_html=True)

    # ── Right column: tips + recent queries ───────────────────────────────
    with col_sidebar:
        st.subheader("💡 Usage Tips")
        st.markdown("""
        **Ask specific questions:**
        - "What is the minimum riparian buffer for a perennial stream?"
        - "What permits are required for a retaining wall over 4 feet?"
        - "What design storm frequency applies to subdivision drainage?"

        **Understanding flags:**
        - ⚠️ **More Restrictive** — Policy Manual adds requirements beyond the Code. Both apply.
        - 🔴 **Discrepancy** — Sources conflict. Verify with City Engineer before acting.

        **If the system abstains:**
        - Try rephrasing with more specific terms
        - Reference the section number if known
        - Consult the Engineering Manual directly
        """)

        st.subheader("🔍 Recent Queries")
        try:
            recent = st.session_state.audit_logger.get_recent_queries(limit=5)
            if recent:
                for q in recent:
                    preview = q["question"][:45] + "..." \
                              if len(q["question"]) > 45 else q["question"]
                    flag_icon = ""
                    if q.get("discrepancy_flag") == "conflict":
                        flag_icon = " 🔴"
                    elif q.get("discrepancy_flag") == "more_restrictive":
                        flag_icon = " ⚠️"
                    elif q.get("abstained"):
                        flag_icon = " ○"

                    with st.expander(f"📝 {preview}{flag_icon}"):
                        ts = q.get("timestamp", "")[:19]
                        st.write(f"**Asked:** {ts}")
                        st.write(f"**Sources:** {q.get('sources_count', 0)}")
                        if q.get("discrepancy_flag"):
                            st.write(f"**Flag:** {q['discrepancy_flag']}")
            else:
                st.write("No recent queries yet.")
        except Exception:
            st.write("Query history will appear here.")

    # ── Bottom navigation ─────────────────────────────────────────────────
    st.markdown("---")
    nav1, nav2 = st.columns(2)
    with nav1:
        if st.button("🏠 Dashboard"):
            st.switch_page("app.py")
    with nav2:
        if st.button("🧙‍♂️ Wizard Mode"):
            st.switch_page("pages/2_Wizard_Mode.py")


if __name__ == "__main__":
    main()
