"""
1_QA_Mode.py
============
City of Brentwood Engineering AI Assistant - V2
Chatbot Mode — policy question answering with footnote citations.
"""

import sys
from pathlib import Path
import streamlit as st

# pages/ is one level down — add both utils/ and repo root
sys.path.append(str(Path(__file__).parent.parent / "utils"))
sys.path.append(str(Path(__file__).parent.parent))

from drive_loader  import load_database
from rag_engine    import get_rag_engine
from database      import AuditLogger
from google_sheets import log_flagged_response
from theme         import apply_theme, render_sidebar, page_header, section_heading, footer, get_favicon

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Chatbot Mode — Brentwood Engineering AI",
    page_icon=get_favicon(),
    layout="wide",
)

apply_theme()
render_sidebar(active="qa")

# ── Session state ─────────────────────────────────────────────────────────────
def _init_session_state():
    defaults = {
        "current_result":     None,
        "current_question":   "",
        "show_feedback_form": False,
        "feedback_submitted": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

# ── Display helpers ───────────────────────────────────────────────────────────

def _display_flag(flag: str, note: str):
    if flag == "more_restrictive":
        st.markdown(f"""
        <div class="bw-flag-restrictive">
            ⚠️ <strong>More Restrictive Policy Applies</strong><br>
            <span style="font-size:0.9em">{note}</span>
        </div>
        """, unsafe_allow_html=True)
    elif flag == "conflict":
        st.markdown(f"""
        <div class="bw-flag-conflict">
            🔴 <strong>Discrepancy Identified — Do Not Rely on This Response Alone</strong><br>
            <span style="font-size:0.9em">{note}</span>
        </div>
        """, unsafe_allow_html=True)


def _display_answer(result: dict):
    answer = result.get("answer", "No answer generated.")
    if result.get("abstained"):
        st.markdown(f"""
        <div class="bw-abstain-box">
            <span style="font-weight:600;color:#64748B;">System could not answer from documents</span><br>
            <span style="font-size:0.93em">{answer}</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="bw-answer-box">
            <span class="bw-answer-label">Answer</span>
            {answer}
        </div>
        """, unsafe_allow_html=True)


def _display_citations(citations: list):
    if not citations:
        return

    superscripts = ["¹","²","³","⁴","⁵","⁶","⁷","⁸","⁹","¹⁰"]
    items_html = ""
    for c in citations:
        num  = c.get("number", 1)
        sup  = superscripts[num - 1] if num <= len(superscripts) else str(num)
        text = c.get("formatted", c.get("source_citation", "Unknown source"))
        # Truncate citations that accidentally contain section body text
        # (happens when zoning chunks have long source_citation fields).
        # Split at semicolons/periods that follow a section number pattern,
        # and cap at 160 chars to keep the source box clean.
        if len(text) > 160:
            # Keep up to first sentence-ending after a reasonable length
            cut = text[:160]
            for sep in [". A", ". T", ". Any", "; A", "; T"]:
                idx = cut.find(sep)
                if idx > 60:
                    cut = cut[:idx]
                    break
            text = cut.rstrip(".,; ") + "…"
        items_html += (
            f"<li>"
            f"<span style='display:inline-block;min-width:1.4rem;"
            f"font-weight:700;color:#F07138;'>{sup}</span>"
            f"<span style='color:#1A2332'>{text}</span>"
            f"</li>"
        )

    st.markdown(f"""
    <div class="bw-citation-box">
        <div class="cit-header">Sources</div>
        <ol>{items_html}</ol>
    </div>
    """, unsafe_allow_html=True)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    page_header(
        title="Engineering Chatbot Mode",
        subtitle="Answers grounded in the Brentwood Municipal Code and Engineering Policy Manual",
    )

    _init_session_state()

    # ── Load engine ───────────────────────────────────────────────────────
    db_info = load_database()
    if not db_info["success"]:
        st.error(f"Database not available: {db_info['error']}")
        if st.button("Return to Dashboard"):
            st.switch_page("app.py")
        return

    # NOTE: No st.spinner() here — spinner calls trigger SessionInfo before
    # the websocket is initialized, causing "Bad message format" popups.
    # get_rag_engine() is @st.cache_resource so after the first cold start
    # it returns instantly from cache. On cold start the status bar shows
    # activity naturally without needing an explicit spinner.
    engine = get_rag_engine(db_info["local_path"])
    if not engine.is_ready():
        st.error(f"RAG engine not ready: {engine.get_init_error() or 'Unknown error'}")
        if st.button("Return to Dashboard"):
            st.switch_page("app.py")
        return

    if "audit_logger" not in st.session_state:
        st.session_state.audit_logger = AuditLogger()

    st.markdown(
        "<div class='bw-status-ok' style='margin-bottom:1rem'>"
        "✅ &nbsp;Chatbot system ready — 26 Brentwood engineering documents indexed"
        "</div>",
        unsafe_allow_html=True,
    )

    # ── Two-column layout ─────────────────────────────────────────────────
    col_main, col_right = st.columns([2, 1], gap="large")

    with col_main:
        section_heading("Your Question")

        question = st.text_area(
            "Enter your engineering policy question:",
            height=100,
            placeholder=(
                "e.g., What is the minimum riparian buffer width for a perennial stream?\n"
                "e.g., What are the maximum retaining wall heights inside the building envelope?\n"
                "e.g., What design storm frequency is required for subdivision drainage?"
            ),
            key="question_input",
            label_visibility="collapsed",
        )

        col_ask, col_clear = st.columns([3, 1])
        with col_ask:
            ask_button = st.button(
                "Search Documents →",
                type="primary",
                use_container_width=True,
            )
        with col_clear:
            if st.button("Clear", use_container_width=True):
                st.session_state.current_result     = None
                st.session_state.current_question   = ""
                st.session_state.show_feedback_form = False
                st.session_state.feedback_submitted = False
                st.rerun()

        # ── Process question ───────────────────────────────────────────
        if ask_button and question.strip():
            st.session_state.show_feedback_form = False
            st.session_state.feedback_submitted = False

            with st.spinner("Searching Brentwood Documents..."):
                try:
                    result = engine.query(question)
                    st.session_state.current_result   = result
                    st.session_state.current_question = question

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
                    st.error(f"Error processing question: {str(e)}")
                    st.session_state.current_result = None

        # ── Display results ────────────────────────────────────────────
        if st.session_state.current_result is not None:
            result = st.session_state.current_result

            st.markdown(
                f"<div style='font-size:0.85rem;color:#4A5568;margin:1rem 0 0.4rem;'>"
                f"<strong>Question:</strong> {st.session_state.current_question}"
                f"</div>",
                unsafe_allow_html=True,
            )

            # Flag banner
            if result.get("discrepancy_flag") and result.get("discrepancy_note"):
                _display_flag(result["discrepancy_flag"], result["discrepancy_note"])

            # Answer
            _display_answer(result)

            # Citations
            if result.get("citations"):
                _display_citations(result["citations"])

            # Performance details (collapsed)
            with st.expander("Query details", expanded=False):
                c1, c2, c3 = st.columns(3)
                with c1: st.metric("Chunks Searched", result.get("chunks_used", 0))
                with c2: st.metric("Sources Cited", len(result.get("citations", [])))
                with c3: st.metric("Response Time",
                                   f"{result.get('elapsed_seconds', 0):.1f}s")

            # ── Feedback ───────────────────────────────────────────────
            st.markdown("<hr>", unsafe_allow_html=True)
            section_heading("Feedback")

            if not st.session_state.feedback_submitted:
                col_fb1, col_fb2 = st.columns(2)
                with col_fb1:
                    if st.button("👍  This answer was helpful", use_container_width=True):
                        st.session_state.feedback_submitted = True
                        st.rerun()
                with col_fb2:
                    if st.button("👎  Needs Improvement",
                                 use_container_width=True, type="secondary"):
                        st.session_state.show_feedback_form = True
                        st.rerun()

            if (st.session_state.show_feedback_form
                    and not st.session_state.feedback_submitted):
                st.markdown("""
                <div class="bw-feedback-panel">
                    <strong>Report an Issue</strong><br>
                    <span style="font-size:0.9em;color:#4A5568">
                    Help us improve — describe what was wrong with this response.
                    </span>
                </div>
                """, unsafe_allow_html=True)

                feedback_text = st.text_area(
                    "What was wrong?",
                    placeholder=(
                        "Examples:\n"
                        "- The cited section number is incorrect\n"
                        "- Missing the exception for lots under 1 acre\n"
                        "- The answer contradicts the manual"
                    ),
                    height=100,
                    key="feedback_text_input",
                )

                col_s1, col_s2 = st.columns(2)
                with col_s1:
                    if st.button("Submit Feedback", type="primary",
                                 use_container_width=True):
                        success = log_flagged_response(
                            question         = st.session_state.current_question,
                            ai_response      = result.get("answer", ""),
                            user_feedback    = feedback_text,
                            discrepancy_flag = result.get("discrepancy_flag"),
                            abstained        = result.get("abstained", False),
                        )
                        st.session_state.audit_logger.flag_response(
                            question  = st.session_state.current_question,
                            flag_type = "negative",
                            reason    = feedback_text,
                            answer    = result.get("answer", ""),
                        )
                        if success:
                            st.session_state.feedback_submitted = True
                            st.session_state.show_feedback_form = False
                            st.rerun()
                        else:
                            st.error(
                                "Could not submit to Google Sheets. "
                                "Response flagged locally — check Admin panel."
                            )
                with col_s2:
                    if st.button("Cancel", use_container_width=True):
                        st.session_state.show_feedback_form = False
                        st.rerun()

            if st.session_state.feedback_submitted:
                st.markdown("""
                <div class="bw-success-msg">
                    ✅ <strong>Thank you for your feedback.</strong>
                    Your report has been submitted for review.
                </div>
                """, unsafe_allow_html=True)

    # ── Right column ──────────────────────────────────────────────────────
    with col_right:
        section_heading("Example Questions")
        st.markdown("""
<div class="bw-card" style="font-size:0.87rem;line-height:1.7;">
<strong style="color:#22427C">Driveways</strong><br>
What is the maximum driveway grade for a residential lot?<br>
What is the minimum inside turning radius for a driveway?<br><br>
<strong style="color:#22427C">Retaining Walls</strong><br>
What is the maximum retaining wall height inside the building envelope?<br>
When does a retaining wall require a PE stamp?<br><br>
<strong style="color:#22427C">Stormwater</strong><br>
What design storm frequency applies to subdivision drainage?<br>
What are the riparian buffer widths for a perennial stream?<br><br>
<strong style="color:#22427C">Pools & Fences</strong><br>
How long must pool water be de-chlorinated before discharge?<br>
What fence materials are prohibited in Brentwood?
</div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
        section_heading("Understanding Flags")
        st.markdown("""
<div class="bw-card" style="font-size:0.87rem;line-height:1.8;">
<span style="color:#E8A000">⚠️ <strong>More Restrictive</strong></span><br>
Policy Manual adds requirements beyond the Code. Both apply — follow the stricter standard.<br><br>
<span style="color:#DC2626">🔴 <strong>Discrepancy</strong></span><br>
Sources conflict. Do not act on this answer alone — verify with the City Engineer.
</div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
        section_heading("Recent Queries")
        try:
            recent = st.session_state.audit_logger.get_recent_queries(limit=5)
            if recent:
                for q in recent:
                    preview = q["question"][:50] + "..." \
                              if len(q["question"]) > 50 else q["question"]
                    flag_icon = ""
                    if q.get("discrepancy_flag") == "conflict":      flag_icon = " 🔴"
                    elif q.get("discrepancy_flag") == "more_restrictive": flag_icon = " ⚠️"
                    elif q.get("abstained"):                          flag_icon = " ○"
                    with st.expander(f"{preview}{flag_icon}"):
                        st.caption(f"Asked: {q.get('timestamp','')[:19]}")
                        if q.get("discrepancy_flag"):
                            st.caption(f"Flag: {q['discrepancy_flag']}")
            else:
                st.caption("No recent queries yet.")
        except Exception:
            st.caption("Query history will appear here.")

    # ── Bottom nav ─────────────────────────────────────────────────────────
    st.markdown("<hr>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("← Dashboard", use_container_width=True):
            st.switch_page("app.py")
    with c2:
        if st.button("Checklist Mode →", use_container_width=True):
            st.switch_page("pages/2_Wizard_Mode.py")

    footer()


if __name__ == "__main__":
    main()
