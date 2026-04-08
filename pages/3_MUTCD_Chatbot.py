"""
3_MUTCD_Chatbot.py
==================
City of Brentwood Engineering AI Assistant - V2
MUTCD Chatbot — question answering grounded in the MUTCD 11th Edition.

ARCHITECTURE:
    This page is structurally identical to 1_QA_Mode.py but uses
    a completely separate RAG engine (mutcd_rag_engine.py) and writes
    flagged responses to a separate Google Sheet (GOOGLE_SHEET_ID_MUTCD).

    No code from the Municipal Code chatbot was modified to create this page.

SOURCE DOCUMENT:
    Manual on Uniform Traffic Control Devices (MUTCD), 11th Edition
    Federal Highway Administration (FHWA)
    953 sections indexed across 83 chapters, Parts 1-9

EMBEDDINGS:
    Voyage AI voyage-3 — same model used to build the corpus in Colab.
    One Voyage API call per user query (fast, fractions of a cent each).

FLAGGING:
    Flags write to the sheet identified by GOOGLE_SHEET_ID_MUTCD in
    Streamlit secrets — a separate Google Sheet from the EPM chatbot.
    Same service account credentials, same column layout.

AUTHOR:  City of Brentwood Engineering Department AI Assistant Project
VERSION: 1.0 — initial MUTCD integration
"""

import sys
from pathlib import Path
import streamlit as st

# pages/ is one level down — add both utils/ and repo root to sys.path
sys.path.append(str(Path(__file__).parent.parent / "utils"))
sys.path.append(str(Path(__file__).parent.parent))

from mutcd_rag_engine import get_mutcd_rag_engine
from database         import AuditLogger
from google_sheets    import log_flagged_response
from theme            import apply_theme, render_sidebar, page_header, section_heading, footer, get_favicon

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="MUTCD Chatbot — Brentwood Engineering AI",
    page_icon=get_favicon(),
    layout="wide",
)

apply_theme()
render_sidebar(active="mutcd")

# ── Session state ──────────────────────────────────────────────────────────────
# Use mutcd_ prefixed keys so this page's state never collides with the
# Municipal Code chatbot's session state variables.
def _init_session_state():
    defaults = {
        "mutcd_current_result":     None,
        "mutcd_current_question":   "",
        "mutcd_show_feedback_form": False,
        "mutcd_feedback_submitted": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ── Display helpers ────────────────────────────────────────────────────────────
# These are intentionally self-contained (not imported from a shared module)
# so that MUTCD display can be customized independently of the EPM chatbot.

def _display_answer(result: dict):
    """
    Render the answer text in the styled answer box.
    Converts markdown bullet lines to HTML list items so they render
    correctly inside the HTML div (plain newlines collapse in HTML).
    """
    answer = result.get("answer", "No answer generated.")

    if result.get("abstained"):
        st.markdown(
            f"""
            <div class="bw-abstain-box">
                <span style="font-weight:600;color:#64748B;">
                    System could not answer from MUTCD documents
                </span><br>
                <span style="font-size:0.93em">{answer}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    def _to_html(text):
        """
        Convert markdown bullet lines to <ul><li> HTML.
        Plain newlines collapse in HTML divs so we must use explicit tags.
        """
        lines   = text.split("\n")
        output  = []
        in_list = False
        for line in lines:
            stripped  = line.strip()
            is_bullet = stripped.startswith("- ") or stripped.startswith("* ")
            if is_bullet:
                if not in_list:
                    output.append('<ul style="margin:0.4em 0 0.4em 1.2em;padding:0">')
                    in_list = True
                output.append(
                    f'<li style="margin-bottom:0.25em">{stripped[2:]}</li>'
                )
            else:
                if in_list:
                    output.append("</ul>")
                    in_list = False
                if stripped:
                    output.append(f'<p style="margin:0.4em 0">{stripped}</p>')
                else:
                    output.append("<br>")
        if in_list:
            output.append("</ul>")
        return "\n".join(output)

    answer_html = _to_html(answer)
    st.markdown(
        f"""
        <div class="bw-answer-box">
            <span class="bw-answer-label">Answer</span>
            {answer_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _display_citations(citations: list):
    """
    Render the numbered MUTCD section citation list below the answer.
    Matches the visual style of the Municipal Code chatbot citations.
    """
    if not citations:
        return

    superscripts = [
        chr(0x00B9), chr(0x00B2), chr(0x00B3),
        chr(0x2074), chr(0x2075), chr(0x2076),
        chr(0x2077), chr(0x2078), chr(0x2079),
    ]

    items_html = ""
    for c in citations:
        num  = c.get("number", 1)
        sup  = superscripts[num - 1] if num <= len(superscripts) else str(num)
        text = c.get("formatted", c.get("source_citation", "MUTCD 11th Edition"))

        # Cap citation display length — section text can be long
        if len(text) > 160:
            cut = text[:160]
            for sep in [". A", ". T", "; A", "; T"]:
                idx = cut.find(sep)
                if idx > 60:
                    cut = cut[:idx]
                    break
            text = cut.rstrip(".,; ") + chr(0x2026)  # ellipsis

        items_html += (
            f"<li>"
            f"<span style='display:inline-block;min-width:1.4rem;"
            f"font-weight:700;color:#F07138;'>{sup}</span>"
            f"<span style='color:#1A2332'>{text}</span>"
            f"</li>"
        )

    st.markdown(
        f"""
        <div class="bw-citation-box">
            <div class="cit-header">MUTCD Sources</div>
            <ol>{items_html}</ol>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    page_header(
        title="MUTCD Chatbot",
        subtitle=(
            "Answers grounded in the Manual on Uniform Traffic Control Devices "
            "(MUTCD) 11th Edition -- FHWA"
        ),
    )

    _init_session_state()

    # ── Load MUTCD RAG engine ──────────────────────────────────────────────
    # get_mutcd_rag_engine() is @st.cache_resource — runs once per server
    # session. Subsequent page loads return instantly from cache.
    # The Voyage AI client initializes quickly (no model download needed).
    engine = get_mutcd_rag_engine()

    if not engine.is_ready():
        st.error(
            f"MUTCD RAG engine not ready: "
            f"{engine.get_init_error() or 'Unknown error'}. "
            "Check that VOYAGE_API_KEY is set in Streamlit secrets and that "
            "vector_database_mutcd/ has been pushed to GitHub."
        )
        if st.button("Return to Dashboard"):
            st.switch_page("app.py")
        return

    if "audit_logger" not in st.session_state:
        st.session_state.audit_logger = AuditLogger()

    # Collection stats for status bar
    stats = engine.get_collection_stats()
    section_count = stats.get("total_chunks", 953)

    st.markdown(
        f"<div class='bw-status-ok' style='margin-bottom:1rem'>"
        f"&#x2705; &nbsp;MUTCD system ready "
        f"&mdash; {section_count:,} sections indexed "
        f"(Parts 1&ndash;9, MUTCD 11th Edition)"
        f"</div>",
        unsafe_allow_html=True,
    )

    # ── Two-column layout ──────────────────────────────────────────────────
    col_main, col_right = st.columns([2, 1], gap="large")

    with col_main:
        section_heading("Your Question")

        question = st.text_area(
            "Enter your MUTCD question:",
            height=100,
            placeholder=(
                "e.g., What are the mounting height requirements for a stop sign?\n"
                "e.g., When is a channelizing device required in a work zone?\n"
                "e.g., What retroreflectivity requirements apply to warning signs?"
            ),
            key="mutcd_question_input",
            label_visibility="collapsed",
        )

        col_ask, col_clear = st.columns([3, 1])
        with col_ask:
            ask_button = st.button(
                "Search MUTCD " + chr(0x2192),
                type="primary",
                use_container_width=True,
            )
        with col_clear:
            if st.button("Clear", use_container_width=True, key="mutcd_clear"):
                st.session_state.mutcd_current_result     = None
                st.session_state.mutcd_current_question   = ""
                st.session_state.mutcd_show_feedback_form = False
                st.session_state.mutcd_feedback_submitted = False
                st.rerun()

        # ── Process question ────────────────────────────────────────────
        if ask_button and question.strip():
            st.session_state.mutcd_show_feedback_form = False
            st.session_state.mutcd_feedback_submitted = False

            with st.spinner("Searching MUTCD 11th Edition..."):
                try:
                    result = engine.query(question)
                    st.session_state.mutcd_current_result   = result
                    st.session_state.mutcd_current_question = question

                    # Log to audit database (same AuditLogger as EPM chatbot)
                    st.session_state.audit_logger.log_query(
                        question        = question,
                        answer          = result.get("answer", ""),
                        sources         = result.get("sources", []),
                        chunks_used     = result.get("chunks_used", 0),
                        model_used      = result.get("model_used", "unknown"),
                        citations       = result.get("citations", []),
                        abstained       = result.get("abstained", False),
                        elapsed_seconds = result.get("elapsed_seconds", 0.0),
                    )

                except Exception as e:
                    st.error(f"Error processing question: {str(e)}")
                    st.session_state.mutcd_current_result = None

        # ── Display results ─────────────────────────────────────────────
        if st.session_state.mutcd_current_result is not None:
            result = st.session_state.mutcd_current_result

            st.markdown(
                f"<div style='font-size:0.85rem;color:#4A5568;margin:1rem 0 0.4rem;'>"
                f"<strong>Question:</strong> "
                f"{st.session_state.mutcd_current_question}"
                f"</div>",
                unsafe_allow_html=True,
            )

            # Answer box
            _display_answer(result)

            # Citation list
            if result.get("citations"):
                _display_citations(result["citations"])

            # Query details (collapsed by default)
            with st.expander("Query details", expanded=False):
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.metric("Sections Retrieved", result.get("chunks_used", 0))
                with c2:
                    st.metric("Sections Cited", len(result.get("citations", [])))
                with c3:
                    st.metric(
                        "Response Time",
                        f"{result.get('elapsed_seconds', 0):.1f}s",
                    )

            # ── Feedback / flagging ─────────────────────────────────────
            # Writes to GOOGLE_SHEET_ID_MUTCD — separate from EPM chatbot sheet
            st.markdown("<hr>", unsafe_allow_html=True)
            section_heading("Feedback")

            if not st.session_state.mutcd_feedback_submitted:
                col_fb1, col_fb2 = st.columns(2)
                with col_fb1:
                    if st.button(
                        chr(0x1F44D) + "  This answer was helpful",
                        use_container_width=True,
                        key="mutcd_thumbs_up",
                    ):
                        st.session_state.mutcd_feedback_submitted = True
                        st.rerun()
                with col_fb2:
                    if st.button(
                        chr(0x1F44E) + "  Needs Improvement",
                        use_container_width=True,
                        type="secondary",
                        key="mutcd_thumbs_down",
                    ):
                        st.session_state.mutcd_show_feedback_form = True
                        st.rerun()

            if (
                st.session_state.mutcd_show_feedback_form
                and not st.session_state.mutcd_feedback_submitted
            ):
                st.markdown(
                    """
                    <div class="bw-feedback-panel">
                        <strong>Report an Issue</strong><br>
                        <span style="font-size:0.9em;color:#4A5568">
                        Help us improve &mdash; describe what was wrong with
                        this MUTCD response.
                        </span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                feedback_text = st.text_area(
                    "What was wrong?",
                    placeholder=(
                        "Examples:\n"
                        "- The cited section number is incorrect\n"
                        "- The answer misquotes a 'shall' as a 'should'\n"
                        "- The requirement applies to a different sign type"
                    ),
                    height=100,
                    key="mutcd_feedback_text",
                )

                col_s1, col_s2 = st.columns(2)
                with col_s1:
                    if st.button(
                        "Submit Feedback",
                        type="primary",
                        use_container_width=True,
                        key="mutcd_submit_feedback",
                    ):
                        # Write to the MUTCD-specific Google Sheet
                        success = log_flagged_response(
                            question        = st.session_state.mutcd_current_question,
                            ai_response     = result.get("answer", ""),
                            user_feedback   = feedback_text,
                            abstained       = result.get("abstained", False),
                            source          = "MUTCD",
                            sheet_id_secret = "GOOGLE_SHEET_ID_MUTCD",
                        )
                        # Also flag locally in the audit log
                        st.session_state.audit_logger.flag_response(
                            question  = st.session_state.mutcd_current_question,
                            flag_type = "negative",
                            reason    = feedback_text,
                            answer    = result.get("answer", ""),
                        )
                        if success:
                            st.session_state.mutcd_feedback_submitted = True
                            st.session_state.mutcd_show_feedback_form = False
                            st.rerun()
                        else:
                            st.error(
                                "Could not submit to Google Sheets. "
                                "Response flagged locally -- check Admin panel."
                            )
                with col_s2:
                    if st.button(
                        "Cancel",
                        use_container_width=True,
                        key="mutcd_cancel_feedback",
                    ):
                        st.session_state.mutcd_show_feedback_form = False
                        st.rerun()

            if st.session_state.mutcd_feedback_submitted:
                st.markdown(
                    """
                    <div class="bw-success-msg">
                        &#x2705; <strong>Thank you for your feedback.</strong>
                        Your report has been submitted for review.
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    # ── Right column ───────────────────────────────────────────────────────
    with col_right:
        section_heading("Example Questions")
        st.markdown(
            """
<div class="bw-card" style="font-size:0.87rem;line-height:1.7;">
<strong style="color:#22427C">Signs</strong><br>
What are the mounting height requirements for a stop sign?<br>
When is a speed limit sign required?<br>
What retroreflectivity standard applies to regulatory signs?<br><br>
<strong style="color:#22427C">Markings</strong><br>
What color is used for no-passing zone centerlines?<br>
When are crosswalk markings required at an intersection?<br><br>
<strong style="color:#22427C">Signals</strong><br>
What is the minimum pedestrian change interval at a signalized crossing?<br>
When is a protected left-turn phase required?<br><br>
<strong style="color:#22427C">Work Zones</strong><br>
When is a flagger required in a work zone?<br>
What is the minimum taper length for a lane closure?
</div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
        section_heading("MUTCD Language Guide")
        st.markdown(
            """
<div class="bw-card" style="font-size:0.87rem;line-height:1.9;">
<span style="color:#22427C"><strong>shall</strong></span> &mdash;
Mandatory requirement<br>
<span style="color:#22427C"><strong>should</strong></span> &mdash;
Advisory recommendation<br>
<span style="color:#22427C"><strong>may</strong></span> &mdash;
Permissive (allowed, not required)<br>
<span style="color:#22427C"><strong>should not</strong></span> &mdash;
Advisory prohibition<br>
<span style="color:#22427C"><strong>shall not</strong></span> &mdash;
Mandatory prohibition<br>
<hr style="margin:0.6rem 0;border-color:#e2e8f0;">
<span style="color:#64748B;font-size:0.82rem;">
These distinctions carry legal weight. Answers preserve the exact modal verb
from the MUTCD source text.
</span>
</div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
        section_heading("About This Source")
        st.markdown(
            """
<div class="bw-card" style="font-size:0.85rem;line-height:1.6;color:#4A5568;">
<strong style="color:#22427C">MUTCD 11th Edition</strong><br>
Federal Highway Administration (FHWA)<br>
Effective: December 2023<br>
953 sections &mdash; 83 chapters &mdash; Parts 1&ndash;9<br>
<hr style="margin:0.6rem 0;border-color:#e2e8f0;">
For official reference:<br>
<span style="color:#22427C">mutcd.fhwa.dot.gov</span>
</div>
            """,
            unsafe_allow_html=True,
        )

    # ── Bottom nav ─────────────────────────────────────────────────────────
    st.markdown("<hr>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button(chr(0x2190) + " Dashboard", use_container_width=True,
                     key="mutcd_nav_home"):
            st.switch_page("app.py")
    with c2:
        if st.button("Municipal Code Chatbot " + chr(0x2192),
                     use_container_width=True, key="mutcd_nav_qa"):
            st.switch_page("pages/1_QA_Mode.py")

    footer()


if __name__ == "__main__":
    main()
