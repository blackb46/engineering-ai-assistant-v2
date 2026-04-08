"""
5_Traffic_Calming.py
====================
City of Brentwood Engineering AI Assistant - V2
Traffic Calming Application Review — standalone page.

Previously embedded as a dropdown option inside 2_Wizard_Mode.py.
Extracted to its own page so it appears as a top-level mode alongside
the permit checklists, MUTCD Chatbot, and Municipal Code Chatbot.

SOURCE POLICY:
    Resolution 2026-12, City of Brentwood, TN (adopted 02/09/2026)

SESSION STATE:
    All widget keys use the tc_ prefix (unchanged from the embedded version).
    Saved progress JSON files from the old embedded form are fully compatible
    with this standalone page — key names are identical.

AUTHOR:  City of Brentwood Engineering Department AI Assistant Project
VERSION: 2.1 — extracted from 2_Wizard_Mode.py
"""

import streamlit as st
import sys
import re
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

# Brentwood, TN -- Central Time (handles CST/CDT automatically)
_CT = ZoneInfo("America/Chicago")

# pages/ is one level down -- add both utils/ and repo root
sys.path.append(str(Path(__file__).parent.parent / "utils"))
sys.path.append(str(Path(__file__).parent.parent))

from theme import apply_theme, render_sidebar, page_header, footer, get_favicon

# Traffic Calming data and report modules
try:
    from traffic_calming_data import (
        ARTERIAL_STREETS,
        COLLECTOR_STREETS,
        STREET_CLASSIFICATIONS,
        APPLICATION_TYPES,
        TIER2_STRATEGIES,
        SCORING_CRITERIA,
        APPENDIX_SECTIONS,
    )
    from traffic_calming_report import (
        build_traffic_calming_report,
        build_appendix_document,
    )
    TC_AVAILABLE = True
except ImportError:
    TC_AVAILABLE = False

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Traffic Calming — Brentwood Engineering AI",
    page_icon=get_favicon(),
    layout="wide",
)

apply_theme()
render_sidebar(active="tc")

# ── Page-level CSS ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .bw-step-heading {
        font-family: var(--font-sans);
        font-size: 1.35rem;
        font-weight: 700;
        color: #22427C;
        border-left: 4px solid #F07138;
        padding: 0.4rem 0 0.4rem 0.75rem;
        margin: 1.5rem 0 1rem 0;
        line-height: 1.3;
    }
    #btt-btn {
        position: fixed;
        bottom: 2.5rem;
        right: 2rem;
        z-index: 9999;
        background: #22427C;
        color: white !important;
        border: none;
        border-radius: 50%;
        width: 44px;
        height: 44px;
        font-size: 1.3rem;
        line-height: 44px;
        text-align: center;
        cursor: pointer;
        box-shadow: 0 2px 8px rgba(34,66,124,0.35);
        opacity: 0;
        transition: opacity 0.25s;
        text-decoration: none;
    }
    #btt-btn.visible { opacity: 1; }
    #btt-btn:hover { background: #2F5C9C !important; }
</style>
<div id="page-top"></div>
<a id="btt-btn" href="#page-top" title="Back to top">&#x2191;</a>
<script>
    window.addEventListener('scroll', function() {
        var btn = document.getElementById('btt-btn');
        if (btn) { btn.classList.toggle('visible', window.scrollY > 300); }
    }, {passive: true});
</script>
""", unsafe_allow_html=True)


# ── Session state init ─────────────────────────────────────────────────────────

def _tc_init():
    """
    Initialize all tc_ session state keys before widgets render.
    Uses setdefault() throughout -- safe pattern for widget-bound keys.
    Direct assignment raises StreamlitAPIException when the key is already
    claimed by a widget. setdefault() is a no-op when the key already exists.
    """
    str_keys = [
        "tc_case_num", "tc_street_class", "tc_street_name",
        "tc_street_name_input", "tc_street_segment", "tc_seg_length",
        "tc_app_type", "tc_petitioner_name", "tc_petitioner_contact",
        "tc_hoa_status", "tc_eligible_res", "tc_sigs_received", "tc_init_pct",
        "tc_problem_desc", "tc_data_85th", "tc_data_limit", "tc_data_adt",
        "tc_data_crashes", "tc_data_cutthru", "tc_speed_excess",
        "tc_speed_excess_raw", "tc_data_school_route", "tc_data_sidewalk_status",
        "tc_data_notes", "tc_local_adt", "tc_local_adt_proj", "tc_local_width",
        "tc_local_grade", "tc_local_spd_limit",
        "tc_t1_notes", "tc_pet2_total", "tc_pet2_yes",
        "tc_pet2_pct",
        "tc_cost_direct",
        "tc_cost_contingency", "tc_cost_total", "tc_cost_resident",
        "tc_cost_city", "tc_cost_notes",
        "tc_public_meeting_notes", "tc_board_res_num",
        "tc_staff_rec_notes", "tc_final_notes",
    ]
    date_keys = [
        "tc_app_date",
        "tc_t1_date",
        "tc_t1_review_date",
        "tc_pet2_mail",
        "tc_moratorium_start",
        "tc_public_meeting_date",
        "tc_board_date",
    ]
    bool_keys = [
        "tc_c_hoa_gov", "tc_c_hoa_req", "tc_c_init_pet", "tc_c_pet_format",
        "tc_c_not_private", "tc_c_not_emergency", "tc_c_collector_list",
        "tc_c_data_speed", "tc_c_data_vol", "tc_c_data_crash",
        "tc_c_data_school", "tc_c_data_sidewalk",
        "tc_c_coll_speed_data", "tc_c_coll_2lanes", "tc_c_coll_termini",
        "tc_c_coll_study_vol", "tc_c_coll_study_speed", "tc_c_coll_study_crash",
        "tc_c_coll_study_sidewalk", "tc_c_coll_study_school", "tc_c_coll_study_t2",
        "tc_c_local_lanewidth", "tc_c_local_grade", "tc_c_local_speedlimit",
        "tc_c_local_notarterial", "tc_c_local_cutthru", "tc_c_local_connection",
        "tc_c_hump_spacing", "tc_c_hump_clearance", "tc_c_hump_dims",
        "tc_c_hump_signage", "tc_c_hump_warn", "tc_c_hump_markings",
        "tc_c_hump_drainage", "tc_c_t1_study", "tc_c_t1_petitioner",
        "tc_c_t1_implemented", "tc_c_t1_effective", "tc_c_t1_ineffective",
        "tc_c_t2_validate", "tc_c_t2_trafficeng", "tc_c_t2_sep_petition",
        "tc_c_pet2_mailed", "tc_c_pet2_hoa", "tc_c_pet2_nonresp", "tc_pet2_ext",
        "tc_c_costshare_agree", "tc_c_hoa_letter", "tc_c_cost_payment",
        "tc_c_public_meeting", "tc_c_public_conducted", "tc_c_staff_rec",
        "tc_c_board_res", "tc_c_board_action", "tc_c_design_final",
        "tc_c_payment_rcvd", "tc_c_installed", "tc_c_archived",
        "tc_c_leftover_funds",
    ]
    for k in str_keys:
        st.session_state.setdefault(k, "")
    for k in date_keys:
        st.session_state.setdefault(k, None)
    for k in bool_keys:
        st.session_state.setdefault(k, False)
    st.session_state.setdefault("tc_t2_strategies", [])
    st.session_state.setdefault("tc_total_score", 0)
    if TC_AVAILABLE:
        for crit in SCORING_CRITERIA:
            st.session_state.setdefault(f"tc_score_{crit['id']}", 0)


# ── Helper functions ───────────────────────────────────────────────────────────

def safe_idx(options, value):
    try:
        return options.index(value)
    except ValueError:
        return 0


def tc_date(label, key, help_text=None, override_value=None):
    """
    Render a date_input that stores a datetime.date or None.
    Passes value= only on first render (when key absent from session state)
    to avoid the Streamlit warning about conflicting key + value usage.
    Also writes a formatted string to key + '_str' for the report builder.
    """
    import datetime as dt
    current = st.session_state.get(key, None)

    if current is not None:
        val = st.date_input(label, key=key, help=help_text, format="MM/DD/YYYY")
    else:
        val = st.date_input(
            label, value=override_value, key=key,
            help=help_text, format="MM/DD/YYYY",
        )

    date_str = val.strftime("%m/%d/%Y") if isinstance(val, dt.date) else ""
    st.session_state[key + "_str"] = date_str
    return val


def tc_attachments(appendix_letter):
    """
    Render the attachment checklist for one appendix section.
    Uses st.container() instead of st.expander() -- nested expanders are
    illegal in Streamlit.
    """
    if not TC_AVAILABLE:
        return
    section = next(
        (s for s in APPENDIX_SECTIONS if s["letter"] == appendix_letter), None
    )
    if not section:
        return

    st.markdown(
        f"**" + chr(0x1F4CE) + f" Appendix {appendix_letter} -- {section['title']}** "
        f"*(check attachments included in this packet)*"
    )
    with st.container():
        cols = st.columns(2)
        for i, att_name in enumerate(section["attachments"]):
            key = f"tc_att_{appendix_letter}_{i}"
            st.session_state.setdefault(key, False)
            cols[i % 2].checkbox(att_name, key=key)
        other_key = f"tc_att_{appendix_letter}_other"
        st.session_state.setdefault(other_key, "")
        st.text_input(
            "Other (describe):",
            key=other_key,
            placeholder="Any additional attachments not listed above",
        )
    st.divider()


def _tc_filename():
    """Build filename from case number and street name."""
    from datetime import date
    case   = (st.session_state.get("tc_case_num",   "") or "").strip()
    street = (st.session_state.get("tc_street_name", "") or "").strip()

    def _clean(s):
        s = re.sub(r'[\\/:*?"<>|]', "", s)
        return re.sub(r"  +", " ", s).strip()

    case   = _clean(case)
    street = _clean(street)
    today  = date.today().strftime("%Y%m%d")
    if case and street:
        return f"{case} - {street} progress-{today}.json"
    elif case:
        return f"{case} progress-{today}.json"
    elif street:
        return f"{street} progress-{today}.json"
    else:
        return f"TC progress-{today}.json"


# Widget-only keys that must never be saved or restored
_WIDGET_ONLY_KEYS = {
    "tc_load_uploader",
    "tc_street_class_sel",
    "tc_app_type_sel",
    "tc_hoa_status_sel",
    "tc_data_school_route_sel",
    "tc_data_sidewalk_status_sel",
    "tc_street_name_art",
    "tc_street_name_col",
    "tc_street_name_placeholder",
}


def _save_tc_state() -> bytes:
    """Serialize all tc_ session state keys to JSON bytes."""
    import json
    import datetime as dt
    payload = {}
    for k, v in st.session_state.items():
        if not k.startswith("tc_"):
            continue
        if k in _WIDGET_ONLY_KEYS:
            continue
        if isinstance(v, dt.date):
            payload[k] = {"__date__": v.isoformat()}
        elif isinstance(v, (str, bool, int, float, list, type(None))):
            payload[k] = v
    return json.dumps(payload, indent=2).encode("utf-8")


def _load_tc_state(uploaded_file):
    """
    Stage JSON file contents for pre-render processing.
    Stores the raw payload in _tc_pending_load; main() applies it before
    any widgets render so all widgets see the loaded values as initial state.
    Returns (success: bool, message: str).
    """
    import json
    try:
        raw     = uploaded_file.read()
        payload = json.loads(raw)
    except Exception as e:
        return False, f"Could not read file: {e}"

    if not isinstance(payload, dict):
        return False, "Invalid file format -- expected a JSON object."

    loadable = sum(
        1 for k in payload
        if k.startswith("tc_") and k not in _WIDGET_ONLY_KEYS
    )
    st.session_state["_tc_pending_load"] = payload
    return True, f"Loading {loadable} fields..."


# ── Main render function ───────────────────────────────────────────────────────

def main():
    # ── Process any pending TC load BEFORE any widgets render ─────────────────
    if st.session_state.get("_tc_pending_load"):
        import datetime as _ldt
        _SKIP = _WIDGET_ONLY_KEYS
        _payload = st.session_state["_tc_pending_load"]
        for _k in list(st.session_state.keys()):
            if _k.startswith("tc_") and _k not in _SKIP:
                del st.session_state[_k]
        for _k, _v in _payload.items():
            if not _k.startswith("tc_") or _k in _SKIP:
                continue
            if isinstance(_v, dict) and "__date__" in _v:
                try:
                    st.session_state[_k] = _ldt.date.fromisoformat(_v["__date__"])
                except Exception:
                    pass
            else:
                st.session_state[_k] = _v
        del st.session_state["_tc_pending_load"]

    _tc_init()

    page_header(
        title="Traffic Calming Application Review",
        subtitle="Policy: Resolution 2026-12 " + chr(0x00B7) + " City of Brentwood, TN " + chr(0x00B7) + " Adopted 02/09/2026",
    )

    if not TC_AVAILABLE:
        st.error(
            "Traffic Calming modules not found in utils/. "
            "Please upload traffic_calming_data.py and traffic_calming_report.py "
            "to the utils/ folder in your GitHub repository."
        )
        return

    def safe_idx(options, value):
        try:
            return options.index(value)
        except ValueError:
            return 0

    street_class = st.session_state.get("tc_street_class", "")

    # ── Save / Load bar ────────────────────────────────────────────────────────
    with st.container():
        save_col, load_col = st.columns([1, 2])

        with save_col:
            if st.button(
                chr(0x1F4BE) + " Save Progress",
                use_container_width=True,
                key="btn_tc_save",
                help="Download current form state as a JSON file to resume later",
            ):
                st.session_state["_tc_save_bytes"] = _save_tc_state()
                st.session_state["_tc_save_fname"] = _tc_filename()

            if st.session_state.get("_tc_save_bytes"):
                st.download_button(
                    label=chr(0x2B07) + " Download  " + st.session_state.get("_tc_save_fname", "TC_progress.json"),
                    data=st.session_state["_tc_save_bytes"],
                    file_name=st.session_state.get("_tc_save_fname", "TC_progress.json"),
                    mime="application/json",
                    use_container_width=True,
                    key="btn_tc_save_dl",
                )

        with load_col:
            _uploader_key = f"tc_load_uploader_{st.session_state.get('_tc_uploader_gen', 0)}"
            uploaded_json = st.file_uploader(
                "Load saved progress (.json)",
                type=["json"],
                key=_uploader_key,
                help="Upload a previously saved progress file to restore all form fields",
                label_visibility="collapsed",
            )
            if uploaded_json is not None:
                ok, msg = _load_tc_state(uploaded_json)
                if ok:
                    st.success(chr(0x2713) + " " + msg)
                    st.session_state["_tc_uploader_gen"] = (
                        st.session_state.get("_tc_uploader_gen", 0) + 1
                    )
                    st.rerun()
                else:
                    st.error(f"Load failed: {msg}")

    st.divider()

    # =========================================================================
    # SECTION I: ADMINISTRATIVE REVIEW
    # =========================================================================
    with st.expander("I. Administrative Review", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("Case / File Number", key="tc_case_num",
                          placeholder="e.g. TC-2026-001")
        with col2:
            tc_date("Application Date", key="tc_app_date")

        st.markdown("---")
        st.markdown("**Step 1 -- Street Classification**")

        class_opts = ["-- Select --"] + list(STREET_CLASSIFICATIONS.keys())
        prev_class = st.session_state.get("tc_street_class", "")
        chosen_class = st.selectbox(
            "Street Classification",
            options=class_opts,
            index=safe_idx(class_opts, prev_class),
            key="tc_street_class_sel",
            help="Arterial/Collector show City-designated street lists. Local = free text.",
        )
        street_class = "" if chosen_class == "-- Select --" else chosen_class

        if street_class != prev_class:
            st.session_state["tc_street_class"] = street_class
            st.session_state["tc_street_name"]  = ""
            if "tc_street_name_input" in st.session_state and street_class != "Local Residential Street":
                del st.session_state["tc_street_name_input"]
            st.rerun()
        else:
            st.session_state["tc_street_class"] = street_class

        if street_class == "Collector Street":
            st.success(chr(0x2713) + " **Collector Street** -- Traffic Calming Policy (Part V). 100% City-funded.")
        elif street_class == "Local Residential Street":
            st.info(chr(0x2139) + " **Local Street** -- Speed Hump Policy (Part VII). Residents pay 60% of costs.")
        elif street_class == "Arterial Street":
            st.warning(chr(0x26A0) + " **Arterial Street** -- Standard calming policy does NOT apply. Engineering study required.")

        st.markdown("**Step 2 -- Street Name**")

        if street_class == "Arterial Street":
            art_opts = ["-- Select Arterial --"] + ARTERIAL_STREETS
            chosen_art = st.selectbox(
                "Arterial Street (Municipal Code -- Arterial Designation)",
                options=art_opts,
                index=safe_idx(art_opts, st.session_state.get("tc_street_name", "")),
                key="tc_street_name_art",
            )
            new_name = "" if chosen_art == "-- Select Arterial --" else chosen_art
            if new_name != st.session_state.get("tc_street_name", ""):
                st.session_state["tc_street_name"] = new_name

        elif street_class == "Collector Street":
            col_opts = ["-- Select Collector --"] + COLLECTOR_STREETS
            chosen_col = st.selectbox(
                "Collector Street (Municipal Code -- Collector Designation)",
                options=col_opts,
                index=safe_idx(col_opts, st.session_state.get("tc_street_name", "")),
                key="tc_street_name_col",
            )
            new_name = "" if chosen_col == "-- Select Collector --" else chosen_col
            if new_name != st.session_state.get("tc_street_name", ""):
                st.session_state["tc_street_name"] = new_name

        elif street_class == "Local Residential Street":
            st.text_input(
                "Local Street Name (enter manually)",
                key="tc_street_name_input",
                placeholder="e.g. Oakwood Court",
            )
            current_input = st.session_state.get("tc_street_name_input", "")
            if current_input != st.session_state.get("tc_street_name", ""):
                st.session_state["tc_street_name"] = current_input

        else:
            st.text_input(
                "Street Name (select classification above first)",
                value="",
                disabled=True,
                key="tc_street_name_placeholder",
            )

        st.markdown("**Step 3 - Street Segment / Limits**")
        st.text_input(
            "Segment Description / Limits  (e.g. from Oak Drive to Elm Street)",
            key="tc_street_segment", placeholder="From ________ to ________",
        )
        st.text_input(
            "Approximate Segment Length (ft)  [Part V-a; Part VII]",
            key="tc_seg_length", placeholder="ft",
        )

        st.markdown("---")
        st.markdown("**Step 4 - Application Type**")
        type_opts = ["-- Select --"] + list(APPLICATION_TYPES.keys())
        chosen_type = st.selectbox(
            "Application Type",
            options=type_opts,
            index=safe_idx(type_opts, st.session_state.get("tc_app_type", "")),
            key="tc_app_type_sel",
        )
        st.session_state["tc_app_type"] = "" if chosen_type == "-- Select --" else chosen_type

        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("Petitioner Name / Organization", key="tc_petitioner_name")
        with col2:
            st.text_input("Petitioner Contact (Phone / Email)", key="tc_petitioner_contact")

        st.markdown("**HOA Prerequisite** *(Part V - Procedures; Part VII)*")
        hoa_opts = [
            "-- Select --",
            "HOA submitting request to City",
            "HOA denied - resident proceeding directly",
            "HOA inaction after 90 days - resident proceeding",
            "No HOA - resident petition permitted",
        ]
        chosen_hoa = st.selectbox(
            "HOA Determination",
            options=hoa_opts,
            index=safe_idx(hoa_opts, st.session_state.get("tc_hoa_status", "")),
            key="tc_hoa_status_sel",
        )
        st.session_state["tc_hoa_status"] = "" if chosen_hoa == "-- Select --" else chosen_hoa

        st.checkbox("HOA governance confirmed  [Part V / VII]", key="tc_c_hoa_gov")
        st.checkbox(
            "HOA written request submitted - or bypass justified (denied / 90-day inaction)  [Part V / VII]",
            key="tc_c_hoa_req",
        )

        st.markdown(
            "**Initial Support Petition** - more than 50% of homes within 600 ft; "
            "one signature/name per residence; eligibility ends 100 ft before a stop sign  [Part V / VII]"
        )
        col1, col2, col3 = st.columns(3)
        with col1:
            st.text_input("Eligible Residences (#)", key="tc_eligible_res")
        with col2:
            st.text_input("Signatures Received (#)", key="tc_sigs_received")
        with col3:
            try:
                pct_val = (
                    float(st.session_state.get("tc_sigs_received") or 0)
                    / float(st.session_state.get("tc_eligible_res") or 1) * 100
                )
                pct_str = f"{pct_val:.1f}%"
                st.session_state["tc_init_pct"] = pct_str
                color = "green" if pct_val > 50 else "red"
                st.markdown(f"**Initial Support:** :{color}[{pct_str}]")
                if pct_val <= 50:
                    st.caption("Must exceed 50% to initiate study")
            except Exception:
                st.markdown("**Initial Support:** -")

        st.checkbox("Initial more-than-50% support petition obtained  [Part V / VII]", key="tc_c_init_pet")
        st.checkbox("One signature and printed name per residence confirmed  [Part V]", key="tc_c_pet_format")
        st.text_area("Description of Perceived Problem / Safety Concern",
                     key="tc_problem_desc", height=80)
        tc_attachments("A")

    # =========================================================================
    # SECTION II: ELIGIBILITY
    # =========================================================================
    with st.expander("II. Classification Eligibility Confirmation", expanded=False):
        st.checkbox(
            "Public street confirmed (not a private street in a gated community)  [Part V / VII]",
            key="tc_c_not_private",
        )
        st.checkbox(
            "Confirmed NOT a designated primary emergency route  [Part V]",
            key="tc_c_not_emergency",
        )
        if street_class == "Collector Street":
            st.checkbox(
                "Collector: verified on City identified residential collector street list  [Part V]",
                key="tc_c_collector_list",
            )
            st.caption(
                "Residential collector list per Resolution 2026-12 Part V: Arrowhead Dr, Belle Rive Dr, "
                "Bluff Rd, Carriage Hills Dr, Charity Dr, Concord Pass, Gen. George Patton Dr, "
                "Gordon Petty Rd, Johnson Chapel Rd W, Jones Pkwy, Knox Valley Dr, Lipscomb Dr, "
                "Manley Ln, McGavock Rd, Pinkerton Rd, Stanfield Rd, Steeplechase Dr, "
                "Sunset Rd (N of Concord Rd), Walnut Hills Dr."
            )

    # =========================================================================
    # SECTION III: DATA COLLECTION
    # =========================================================================
    with st.expander("III. Data Collection & Field Review", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.text_input("85th Percentile Speed (mph)  [Part V-a / VII]", key="tc_data_85th")
            st.text_input("ADT (vehicles/day)  [Part V-a / VII]", key="tc_data_adt")
        with col2:
            st.text_input("Posted Speed Limit (mph)", key="tc_data_limit")
            st.text_input("Crash Count (12 months)  [Parts I-II]", key="tc_data_crashes")
        with col3:
            try:
                excess_val = (
                    float(st.session_state.get("tc_data_85th") or 0)
                    - float(st.session_state.get("tc_data_limit") or 0)
                )
                excess_str = f"{excess_val:.1f} mph over limit"
                st.session_state["tc_speed_excess"]     = excess_str
                st.session_state["tc_speed_excess_raw"] = str(excess_val)
                color = "green" if excess_val >= 8 else "red"
                st.markdown(f"**Speed Excess:** :{color}[{excess_str}]")
                if street_class == "Collector Street" and excess_val < 8:
                    st.caption("Collector criterion: 8 mph over limit required [Part V-a]")
            except Exception:
                st.markdown("**Speed Excess:** -")
            st.text_input(
                "Cut-Through Traffic % [Part VII - 35% or more = cut-through]",
                key="tc_data_cutthru",
            )

        col1, col2 = st.columns(2)
        with col1:
            school_opts = [
                "-- Select --",
                "Yes - street is on a school walking route",
                "No - not a school walking route",
            ]
            chosen_sch = st.selectbox(
                "School Walking Route?  [Part V-b-3: 10 pts if yes]",
                options=school_opts,
                index=safe_idx(school_opts, st.session_state.get("tc_data_school_route", "")),
                key="tc_data_school_route_sel",
            )
            st.session_state["tc_data_school_route"] = "" if chosen_sch == "-- Select --" else chosen_sch
        with col2:
            swlk_opts = ["-- Select --", "No continuous sidewalk", "Continuous sidewalk exists"]
            chosen_swlk = st.selectbox(
                "Continuous Sidewalk?  [Part V-b-3: 10 pts if no sidewalk]",
                options=swlk_opts,
                index=safe_idx(swlk_opts, st.session_state.get("tc_data_sidewalk_status", "")),
                key="tc_data_sidewalk_status_sel",
            )
            st.session_state["tc_data_sidewalk_status"] = "" if chosen_swlk == "-- Select --" else chosen_swlk

        st.checkbox("Speed study completed (24-hr weekday minimum for collectors)  [Part V-a]", key="tc_c_data_speed")
        st.checkbox("Traffic count / ADT collected  [Part V-a / VII]", key="tc_c_data_vol")
        st.checkbox("Crash history reviewed (12 months minimum)  [Parts I-II]", key="tc_c_data_crash")
        st.checkbox("School route status confirmed  [Part V-b-3]", key="tc_c_data_school")
        st.checkbox("Continuous sidewalk presence/absence confirmed  [Part V-b-3]", key="tc_c_data_sidewalk")
        st.text_area("Data Collection Notes / Summary", key="tc_data_notes", height=80)
        tc_attachments("B")

    # =========================================================================
    # SECTION IV: STREET-TYPE SPECIFIC
    # =========================================================================
    if street_class == "Collector Street":
        with st.expander("IV. Traffic Calming - Collector Street Criteria (Part V)", expanded=False):
            st.markdown("**Roadway Eligibility Criteria - All must be met [Part V-a]**")
            try:
                adt_ok = float(st.session_state.get("tc_data_adt") or 0) >= 500
                len_ok = float(st.session_state.get("tc_seg_length") or 0) >= 800
                spd_ok = float(str(st.session_state.get("tc_speed_excess_raw") or 0)) >= 8
                if not adt_ok:
                    st.error(f"ADT must be 500 or more vpd - entered: {st.session_state.get('tc_data_adt') or '?'}  [Part V-a Volume]")
                if not len_ok:
                    st.error(f"Segment must be 800 ft or more - entered: {st.session_state.get('tc_seg_length') or '?'} ft  [Part V-a Other Criteria]")
                if not spd_ok:
                    st.error("85th percentile must exceed limit by 8 mph or more  [Part V-a Speed]")
                if adt_ok and len_ok and spd_ok:
                    st.success("All three roadway criteria met - eligible to proceed with study.")
            except Exception:
                pass

            st.checkbox("24-hr weekday speed data collected  [Part V-a Speed]", key="tc_c_coll_speed_data")
            st.checkbox("Street has no more than two traffic lanes (one each direction)  [Part V-a]", key="tc_c_coll_2lanes")
            st.checkbox("Logical termini for calming treatment identifiable  [Part V-a]", key="tc_c_coll_termini")
            st.markdown("**Engineering Study Contents Required [Part V-b-1]**")
            st.checkbox("Study includes traffic volume analysis", key="tc_c_coll_study_vol")
            st.checkbox("Study includes traffic speed analysis", key="tc_c_coll_study_speed")
            st.checkbox("Study includes accident history for subject segment", key="tc_c_coll_study_crash")
            st.checkbox("Study notes presence or absence of sidewalks", key="tc_c_coll_study_sidewalk")
            st.checkbox("Study addresses whether street is on a school walking route  [Part V-b-1 / V-b-3]", key="tc_c_coll_study_school")
            st.checkbox("Study outlines applicable Tier 2 strategies for this location  [Part V-b-1]", key="tc_c_coll_study_t2")

    elif street_class == "Local Residential Street":
        with st.expander("IV. Speed Hump Eligibility - Local Street (Part VII)", expanded=False):
            st.markdown("**Street Eligibility Criteria - All must be met [Part VII]**")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.text_input("Current ADT (vpd) - 500 to 2500 required", key="tc_local_adt")
                st.text_input("Street Width (ft) - less than 30 ft required", key="tc_local_width")
            with col2:
                st.text_input("Projected Full-Build ADT - 2500 or less required", key="tc_local_adt_proj")
                st.text_input("Street Grade (%) - 6% or less required", key="tc_local_grade")
            with col3:
                st.text_input("Posted Speed Limit (mph) - 30 mph or less required", key="tc_local_spd_limit")
                try:
                    adt_v = float(st.session_state.get("tc_local_adt") or 0)
                    if adt_v > 0:
                        if adt_v < 500 or adt_v > 2500:
                            st.error(f"ADT {adt_v:.0f} outside 500-2500 range  [Part VII]")
                        else:
                            st.success(f"ADT {adt_v:.0f} within range")
                except Exception:
                    pass

            st.checkbox("Two-lane street less than 30 ft wide confirmed  [Part VII]", key="tc_c_local_lanewidth")
            st.checkbox("Grade does not exceed 6%  [Part VII]", key="tc_c_local_grade")
            st.checkbox("Posted speed limit is 30 mph or less  [Part VII]", key="tc_c_local_speedlimit")
            st.checkbox("Confirmed NOT an arterial or collector street (speed humps prohibited on those)  [Part VII]", key="tc_c_local_notarterial")
            st.checkbox("Street has identified cut-through or speeding problem confirmed by data  [Part VII]", key="tc_c_local_cutthru")
            st.caption(
                "Cut-through = 35% or more of traffic does not originate or terminate in subdivision. "
                "Speeding = 85th percentile speed exceeds posted limit."
            )
            st.checkbox("Street provides connection between arterial/collector streets or subdivision pass-through  [Part VII]", key="tc_c_local_connection")
            st.markdown("**Design Requirements - verified prior to installation [Part VII]**")
            st.checkbox("Minimum two humps proposed; spacing 300 to 600 ft apart  [Part VII]", key="tc_c_hump_spacing")
            st.checkbox("Each hump 200 ft or more from any intersection and from any curve with radius 150 ft or less  [Part VII]", key="tc_c_hump_clearance")
            st.checkbox("Hump max height 3 to 4 inches; travel length 12 ft per standard dimensions  [Part VII]", key="tc_c_hump_dims")
            st.checkbox("Regulatory Residential Speed Control District signs installed (24x24, black on white)  [Part VII]", key="tc_c_hump_signage")
            st.checkbox("MUTCD advance warning signs: 30x30 SPEED HUMPS sign plus 18x18 15 MPH advisory plate, about 125 ft before first hump  [Part VII]", key="tc_c_hump_warn")
            st.checkbox("Double yellow centerline continued across all humps; 12-in white stripes at 6-inch O.C. per standard details  [Part VII]", key="tc_c_hump_markings")
            st.checkbox("All hump locations reviewed by City Engineer - drainage adequately accommodated  [Part VII]", key="tc_c_hump_drainage")
        tc_attachments("C")

    # =========================================================================
    # SECTION V: TIER 1
    # =========================================================================
    with st.expander("V. Tier 1 - Non-Construction Strategies (Part V-b-1)", expanded=False):
        if street_class == "Local Residential Street":
            st.info(
                "Less dramatic measures such as signs and striping must be evaluated first. "
                "Reevaluate 6 months after installation before final speed hump decision.  [Part VII]"
            )
        col1, col2 = st.columns(2)
        with col1:
            tc_date("Tier 1 Implementation Date", key="tc_t1_date")
        with col2:
            _t1_val = st.session_state.get("tc_t1_date")
            _auto_review = None
            if _t1_val:
                import datetime as _dt
                import calendar as _cal
                _m = _t1_val.month + 6
                _y = _t1_val.year + (_m - 1) // 12
                _m = (_m - 1) % 12 + 1
                _d = min(_t1_val.day, _cal.monthrange(_y, _m)[1])
                _auto_review = _dt.date(_y, _m, _d)
            tc_date(
                "Six-Month Effectiveness Review Date",
                key="tc_t1_review_date",
                help_text="Auto-calculated as 6 months after implementation date. Select a different date to override.",
                override_value=_auto_review,
            )
        st.checkbox("Study recommendation includes one or more Tier 1 strategies  [Part V-b-1]", key="tc_c_t1_study")
        st.checkbox("Staff met with petitioner to outline study recommendations  [Part V-b-1]", key="tc_c_t1_petitioner")
        st.checkbox("Tier 1 strategy implemented  [Part V-b-1]", key="tc_c_t1_implemented")
        col1, col2 = st.columns(2)
        with col1:
            st.checkbox("Tier 1 determined EFFECTIVE after 6 months - no further action  [Part V-b-1]", key="tc_c_t1_effective")
        with col2:
            st.checkbox("Tier 1 determined INEFFECTIVE after 6 months - Tier 2 requested  [Part V-b-1]", key="tc_c_t1_ineffective")
        if st.session_state.get("tc_c_t1_effective") and st.session_state.get("tc_c_t1_ineffective"):
            st.warning("Cannot mark both effective and ineffective - please uncheck one.")
        st.text_area("Tier 1 Notes (strategies applied, effectiveness findings)", key="tc_t1_notes", height=80)

    # =========================================================================
    # SECTION VI: TIER 2 / SECOND PETITION
    # =========================================================================
    with st.expander("VI. Tier 2 / Speed Humps - Second Petition (Parts V-b-2; VII)", expanded=False):
        if street_class == "Collector Street":
            st.caption("Speed humps are NOT eligible on designated collector roads.  [Part V-b Tier 2 Note]")

        st.markdown("**Tier 2 Strategies Proposed [Part V-b Tier 2]**")
        t2_selected = []
        for strat, cite in TIER2_STRATEGIES:
            safe_key = (
                "tc_t2_"
                + strat[:25].replace(" ", "_").replace("/", "_")
                              .replace(",", "").replace("-", "").lower()
            )
            if safe_key not in st.session_state:
                st.session_state[safe_key] = False
            st.checkbox(f"{strat}  [{cite}]", key=safe_key)
            if st.session_state.get(safe_key):
                t2_selected.append(strat)
        st.session_state["tc_t2_strategies"] = t2_selected

        st.markdown("**Required Review Steps [Part V-b-2]**")
        st.checkbox("City conducted second study validating Tier 1 was ineffective  [Part V-b-2]", key="tc_c_t2_validate")
        st.checkbox("Tier 2 strategy reviewed by City Traffic Engineer before recommendation  [Part V-b-2]", key="tc_c_t2_trafficeng")
        st.checkbox("Separate petition prepared for each proposed improvement  [Part V-b-2]", key="tc_c_t2_sep_petition")
        st.caption("For a series of improvements such as speed tables or circles, one petition per improvement required.")

        st.markdown("**Second-Round Petition Process [Part V-b-2; Part VII]**")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.text_input("Total Households - Affected Area (within 600 ft)  [Part V-b-2 / VII]", key="tc_pet2_total")
            tc_date("Petition Mail Date  [Part V-b-2 / VII]", key="tc_pet2_mail")
        with col2:
            st.text_input("Yes Votes Received  [Part V-b-2 / VII]", key="tc_pet2_yes")
            st.checkbox("30-day extension granted  [Part V-b-2 / VII]", key="tc_pet2_ext")
            st.caption("Extension requires extenuating circumstances; request within 7 days of results notification.")
            _mail_val = st.session_state.get("tc_pet2_mail")
            _ext_val  = st.session_state.get("tc_pet2_ext", False)
            if _mail_val:
                import datetime as _dt
                _days     = 45 + (30 if _ext_val else 0)
                _deadline = _mail_val + _dt.timedelta(days=_days)
                _deadline_str = _deadline.strftime("%m/%d/%Y")
                st.session_state["tc_pet2_deadline"] = _deadline_str
                _label = f"45-Day Deadline{' + 30-Day Extension' if _ext_val else ''}"
                st.markdown(f"**{_label}:** {_deadline_str}  *[Part V-b-2 / VII]*")
            else:
                st.session_state["tc_pet2_deadline"] = ""
                st.markdown("**45-Day Deadline:** *(enter petition mail date)*")
        with col3:
            try:
                pct2     = (float(st.session_state.get("tc_pet2_yes") or 0)
                            / float(st.session_state.get("tc_pet2_total") or 1) * 100)
                pct2_str = f"{pct2:.1f}%"
                st.session_state["tc_pet2_pct"] = pct2_str
                color2   = "green" if pct2 >= 66.7 else "red"
                st.markdown(f"**Support:** :{color2}[{pct2_str}]")
                st.caption("Threshold met" if pct2 >= 66.7 else "Need 66.7% (2/3) to proceed")
            except Exception:
                st.markdown("**Support:** -")

        st.checkbox("Petitions mailed by City on petitioner behalf (City mails twice)  [Part V-b-2 / VII]", key="tc_c_pet2_mailed")
        st.checkbox("Vote eligibility confirmed NOT contingent on HOA membership  [Part V-b-2 / VII]", key="tc_c_pet2_hoa")
        st.checkbox("Non-responses confirmed counted as no votes  [Part V-b-2 / VII]", key="tc_c_pet2_nonresp")
        col1, col2 = st.columns(2)
        with col1:
            tc_date(
                "Last Day of Voting Window  [Part V-b-2 / VII]",
                key="tc_moratorium_start",
                help_text="The moratorium clock starts on this date if the petition fails",
            )
        with col2:
            _vote_val = st.session_state.get("tc_moratorium_start")
            if _vote_val:
                import datetime as _dt
                import calendar as _cal
                _resolution_date     = _dt.date(2026, 2, 9)
                _twelve_months_prior = _dt.date(2025, 2, 9)
                _short_moratorium    = (_twelve_months_prior <= _vote_val <= _resolution_date)
                _months = 12 if _short_moratorium else 24
                _m = _vote_val.month + _months
                _y = _vote_val.year + (_m - 1) // 12
                _m = (_m - 1) % 12 + 1
                _d = min(_vote_val.day, _cal.monthrange(_y, _m)[1])
                _end     = _dt.date(_y, _m, _d)
                _end_str = _end.strftime("%m/%d/%Y")
                st.session_state["tc_moratorium_end"] = _end_str
                if _short_moratorium:
                    st.markdown(f"**Moratorium End:** {_end_str} *(12 months -- Res. 2026-12 " + chr(0x00A7) + "3)*")
                    st.caption("Vote occurred within 12 months before adoption -- 12-month moratorium applies.")
                else:
                    st.markdown(f"**Moratorium End:** {_end_str} *(24 months)*")
            else:
                st.session_state["tc_moratorium_end"] = ""
                st.markdown("**Moratorium End:** *(enter last day of voting window)*")
        st.caption(
            "Per Resolution 2026-12 Section 3: petitions with votes within 12 months before "
            "adoption (02/09/2026) use a 12-month moratorium only."
        )

        if street_class == "Local Residential Street":
            st.markdown("**Cost-Share Agreement - Local Streets [Part VII]**")
            st.checkbox("Petition signed by 2/3 or more of households agreeing to pay 60% of direct costs  [Part VII]", key="tc_c_costshare_agree")
            st.checkbox("HOA funding letter on file confirming HOA will cover cost-share  [Part VII]", key="tc_c_hoa_letter")
        tc_attachments("D")

    # =========================================================================
    # SECTION VII: COST & PRIORITIZATION
    # =========================================================================
    with st.expander("VII. Cost Estimates & Prioritization Scoring", expanded=False):
        if street_class == "Collector Street":
            st.markdown("**Tier 2 Prioritization Scoring [Part V-b-3 - used when multiple Tier 2 requests are pending]**")
            total_score = 0
            for crit in SCORING_CRITERIA:
                score_val = st.number_input(
                    f"{crit['label']} - max {crit['max']} pts | {crit['basis']}  [{crit['cite']}]",
                    min_value=0, max_value=crit["max"], step=1,
                    key=f"tc_score_{crit['id']}",
                )
                total_score += score_val
            st.session_state["tc_total_score"] = total_score
            st.metric("Total Priority Score", f"{total_score} / 100")
            st.divider()

        st.markdown("**Cost Estimate**")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.text_input("Estimated Direct Cost ($)  [Part VII]", key="tc_cost_direct")
        with col2:
            try:
                direct        = float(st.session_state.get("tc_cost_direct") or 0)
                conting       = direct * 0.10
                total_c       = direct + conting
                resident_share = total_c * 0.60
                city_share    = total_c * 0.40
                st.session_state["tc_cost_contingency"] = f"${conting:,.2f}"
                st.session_state["tc_cost_total"]       = f"${total_c:,.2f}"
                st.session_state["tc_cost_resident"]    = f"${resident_share:,.2f}"
                st.session_state["tc_cost_city"]        = f"${city_share:,.2f}"
                st.markdown(f"**10% Contingency:** ${conting:,.2f}")
                st.markdown(f"**Total Estimated:** ${total_c:,.2f}")
            except Exception:
                st.markdown("**Total:** -")
        with col3:
            if street_class == "Local Residential Street":
                st.markdown(f"**Resident Share (60%):** {st.session_state.get('tc_cost_resident', '-')}")
                st.markdown(f"**City Share (40%):** {st.session_state.get('tc_cost_city', '-')}")
                st.caption("Petition expires if 60% payment not received within 6 months of Board approval.")
            elif street_class == "Collector Street":
                st.markdown("**Funding:** 100% City-funded (subject to normal budget process)")

        st.checkbox(
            "Resident 60% payment received prior to installation "
            "(local streets - must be within 6 months of Board approval)  [Part VII]",
            key="tc_c_cost_payment",
        )
        st.text_area("Cost / Funding Notes", key="tc_cost_notes", height=100)
        tc_attachments("E")

    # =========================================================================
    # SECTION VIII: BOARD ACTION
    # =========================================================================
    with st.expander("VIII. Public Meeting & Board of Commissioners Action", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            tc_date("Public Meeting Date  [Part V-b-2]", key="tc_public_meeting_date")
            tc_date("Board Meeting Date  [Part VII]", key="tc_board_date")
        with col2:
            st.text_input("Public Meeting Summary / Outcome", key="tc_public_meeting_notes")
            st.text_input("Board Resolution Number  [Part VII]", key="tc_board_res_num",
                          placeholder="e.g. Resolution 2026-XX")
        st.checkbox("Public meeting scheduled by staff after 2/3 or more petition support received  [Part V-b-2]", key="tc_c_public_meeting")
        st.checkbox("Public meeting conducted; input documented  [Part V-b-2]", key="tc_c_public_conducted")
        st.checkbox("Staff recommendation prepared for Board, incorporating petition results and public meeting input  [Part V-b-2 / VII]", key="tc_c_staff_rec")
        st.checkbox("Board resolution approving proposed locations adopted PRIOR to installation  [Part VII]", key="tc_c_board_res")
        st.checkbox("Board action recorded and outcome documented  [Part VII]", key="tc_c_board_action")
        st.checkbox("Final design complete; City Engineer drainage review done at all locations  [Part VII]", key="tc_c_design_final")
        st.checkbox("Resident 60% payment received before construction begins (expires 6 months after Board approval)  [Part VII]", key="tc_c_payment_rcvd")
        st.checkbox("Improvements installed / constructed", key="tc_c_installed")
        st.checkbox("Complete application file archived (petitions, study, Board resolution, cost records)", key="tc_c_archived")
        st.checkbox("Any leftover funds returned to petitioning group upon project completion  [Part VII]", key="tc_c_leftover_funds")
        st.text_area("Staff Recommendation Summary", key="tc_staff_rec_notes", height=80)
        st.text_area("Final / Closeout Notes", key="tc_final_notes", height=100)
        tc_attachments("F")
        tc_attachments("G")

    # =========================================================================
    # EXPORT / CLEAR
    # =========================================================================
    st.divider()
    col1, col2, col3 = st.columns([3, 3, 1])

    with col1:
        if st.button(chr(0x1F4C4) + " Generate Word Document",
                     type="primary", use_container_width=True, key="btn_tc_export"):
            import traceback as _tb
            import datetime as _dt
            try:
                data = {}
                for k, v in st.session_state.items():
                    if not k.startswith("tc_"):
                        continue
                    try:
                        k.encode("ascii")
                    except UnicodeEncodeError:
                        continue
                    if isinstance(v, (_dt.date, _dt.datetime,
                                      str, bool, int, float,
                                      list, dict, type(None))):
                        data[k] = v
                buf = build_traffic_calming_report(
                    data,
                    scoring_criteria=SCORING_CRITERIA if TC_AVAILABLE else [],
                )
                street_raw  = st.session_state.get("tc_street_name") or "TC_Review"
                street_safe = re.sub(r"[^a-zA-Z0-9_\-]", "_", street_raw)[:35]
                filename    = (
                    f"TC_Review_{street_safe}_"
                    f"{datetime.now(_CT).strftime('%Y%m%d')}.docx"
                )
                st.session_state["_tc_doc_bytes"]    = buf.read()
                st.session_state["_tc_doc_filename"] = filename
                st.session_state.pop("_tc_doc_error", None)
            except Exception:
                st.session_state.pop("_tc_doc_bytes", None)
                st.session_state["_tc_doc_error"] = _tb.format_exc()

        if st.session_state.get("_tc_doc_error"):
            st.error("Report generation failed -- details below:")
            st.code(st.session_state["_tc_doc_error"])
            if st.button("Dismiss error", key="btn_tc_err_dismiss"):
                st.session_state.pop("_tc_doc_error", None)
                st.rerun()

        if st.session_state.get("_tc_doc_bytes"):
            st.download_button(
                label=chr(0x2B07) + " Download Checklist + Action Items",
                data=st.session_state["_tc_doc_bytes"],
                file_name=st.session_state.get("_tc_doc_filename", "TC_Review.docx"),
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
                key="btn_tc_download",
            )

    with col2:
        if st.button(chr(0x1F4CE) + " Generate Appendix Document",
                     use_container_width=True, key="btn_tc_appendix"):
            import traceback as _tb
            import datetime as _dt
            try:
                data = {}
                for k, v in st.session_state.items():
                    if not k.startswith("tc_"):
                        continue
                    try:
                        k.encode("ascii")
                    except UnicodeEncodeError:
                        continue
                    if isinstance(v, (_dt.date, _dt.datetime,
                                      str, bool, int, float,
                                      list, dict, type(None))):
                        data[k] = v
                buf = build_appendix_document(
                    data,
                    appendix_sections=APPENDIX_SECTIONS if TC_AVAILABLE else [],
                )
                street_raw  = st.session_state.get("tc_street_name") or "TC_Review"
                street_safe = re.sub(r"[^a-zA-Z0-9_\-]", "_", street_raw)[:35]
                filename    = (
                    f"TC_Appendix_{street_safe}_"
                    f"{datetime.now(_CT).strftime('%Y%m%d')}.docx"
                )
                st.session_state["_tc_app_bytes"]    = buf.read()
                st.session_state["_tc_app_filename"] = filename
                st.session_state.pop("_tc_app_error", None)
            except Exception:
                st.session_state.pop("_tc_app_bytes", None)
                st.session_state["_tc_app_error"] = _tb.format_exc()

        if st.session_state.get("_tc_app_error"):
            st.error("Appendix generation failed -- details below:")
            st.code(st.session_state["_tc_app_error"])
            if st.button("Dismiss error", key="btn_tc_app_err_dismiss"):
                st.session_state.pop("_tc_app_error", None)
                st.rerun()

        if st.session_state.get("_tc_app_bytes"):
            st.download_button(
                label=chr(0x2B07) + " Download Appendix Cover Pages",
                data=st.session_state["_tc_app_bytes"],
                file_name=st.session_state.get("_tc_app_filename", "TC_Appendix.docx"),
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
                key="btn_tc_app_download",
            )

    with col3:
        if st.button("Clear TC Form", use_container_width=True, key="btn_tc_clear"):
            keys_to_clear = [
                k for k in list(st.session_state.keys())
                if k.startswith("tc_") or k.startswith("_tc_")
            ]
            for k in keys_to_clear:
                del st.session_state[k]
            st.rerun()

    # ── Bottom nav ─────────────────────────────────────────────────────────────
    st.markdown("<hr>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button(chr(0x2190) + " Dashboard", use_container_width=True, key="tc_nav_home"):
            st.switch_page("app.py")
    with c2:
        if st.button("Checklist Mode " + chr(0x2192), use_container_width=True, key="tc_nav_checklist"):
            st.switch_page("pages/2_Wizard_Mode.py")

    footer()


if __name__ == "__main__":
    main()
