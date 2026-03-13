"""
2_Wizard_Mode.py
================
City of Brentwood Engineering AI Assistant - V2
Wizard Mode — interactive plan review checklist with export.

V3 UI changes:
  - section_heading replaced with bw-section-header cards (name + progress badge)
  - Yes/No/NA uses horizontal st.radio styled as segmented control pill track
  - "No" comment panel: 2px orange left-border accent, CSS slide-in animation
  - Project setup: 3-column grid (review type + permit + address) then reviewer
  - Step 3 metrics: large thin (font-weight 300) numbers, 10px uppercase labels
"""

import streamlit as st
import sys
import csv
import zlib
import random
import string
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from io import BytesIO, StringIO

_CT = ZoneInfo("America/Chicago")

sys.path.append(str(Path(__file__).parent.parent / "utils"))
sys.path.append(str(Path(__file__).parent.parent))

from checklist_data import (
    REVIEW_TYPES,
    REVIEWERS,
    CHECKLIST_SECTIONS,
    get_checklist_for_review_type,
)
from comments_database import COMMENTS, get_comment
from theme import apply_theme, render_sidebar, page_header, section_heading, footer, get_favicon

try:
    from docx import Document
    from docx.shared import Inches, Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

st.set_page_config(
    page_title = "Wizard Mode — Brentwood Engineering AI",
    page_icon  = get_favicon(),
    layout     = "wide",
)

apply_theme()
render_sidebar(active="wizard")


# ── Session state ──────────────────────────────────────────────────────────────
def initialize_session_state():
    defaults = {
        "wizard_review_type":       None,
        "wizard_permit_number":     "",
        "wizard_address":           "",
        "wizard_reviewer":          None,
        "wizard_checklist_state":   {},
        "wizard_selected_comments": {},
        "wizard_custom_notes":      {},
        "wizard_started":           False,
        "wizard_resubmittal":       "—",
        "wizard_open_section":      None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def reset_checklist():
    st.session_state.wizard_checklist_state   = {}
    st.session_state.wizard_selected_comments = {}
    st.session_state.wizard_custom_notes      = {}
    st.session_state.wizard_resubmittal       = "—"
    st.session_state.wizard_open_section      = None


# ── Comment collection ─────────────────────────────────────────────────────────
def collect_all_comments():
    """
    Collect comments from all 'No' items, then append BB-0045 if resubmittal
    was selected. Returns a list of raw comment strings (no prefix codes).
    Used by all export functions.
    """
    checklist    = get_checklist_for_review_type(st.session_state.wizard_review_type)
    all_comments = []

    for section_id, section_data in checklist.items():
        for item in section_data["items"]:
            item_key = item["id"]
            if st.session_state.wizard_checklist_state.get(item_key) == "No":
                for comment_id in st.session_state.wizard_selected_comments.get(item_key, []):
                    text = COMMENTS.get(comment_id, "")
                    if text:
                        all_comments.append(text)
                custom = st.session_state.wizard_custom_notes.get(item_key, "")
                if custom.strip():
                    all_comments.append(custom.strip())

    if st.session_state.wizard_resubmittal == "Yes":
        resub = COMMENTS.get("BB-0045", "")
        if resub:
            all_comments.append(resub)

    return all_comments


# ── Word export ────────────────────────────────────────────────────────────────
def generate_word_document():
    if not DOCX_AVAILABLE:
        return None

    doc = Document()

    title = doc.add_heading("Engineering Plan Review", 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    doc.add_heading("Project Information", level=1)
    info_table = doc.add_table(rows=5, cols=2)
    info_table.style = "Table Grid"
    info_data = [
        ("Review Type:",   st.session_state.wizard_review_type or "Not specified"),
        ("Permit Number:", st.session_state.wizard_permit_number or "Not specified"),
        ("Address:",       st.session_state.wizard_address or "Not specified"),
        ("Reviewer:",      st.session_state.wizard_reviewer or "Not specified"),
        ("Review Date:",   datetime.now(_CT).strftime("%Y-%m-%d %I:%M %p")),
    ]
    for i, (label, value) in enumerate(info_data):
        info_table.rows[i].cells[0].text = label
        info_table.rows[i].cells[1].text = value
        info_table.rows[i].cells[0].paragraphs[0].runs[0].bold = True
    doc.add_paragraph()

    doc.add_heading("Review Summary", level=1)
    yes_count = sum(1 for v in st.session_state.wizard_checklist_state.values() if v == "Yes")
    no_count  = sum(1 for v in st.session_state.wizard_checklist_state.values() if v == "No")
    na_count  = sum(1 for v in st.session_state.wizard_checklist_state.values() if v == "N/A")
    total     = yes_count + no_count + na_count

    summary_table = doc.add_table(rows=5, cols=2)
    summary_table.style = "Table Grid"
    for i, (label, value) in enumerate([
        ("Total Items Reviewed:", str(total)),
        ("Compliant (Yes):",      str(yes_count)),
        ("Issues Found (No):",    str(no_count)),
        ("Not Applicable:",       str(na_count)),
        ("Resubmittal Comment:",  st.session_state.wizard_resubmittal),
    ]):
        summary_table.rows[i].cells[0].text = label
        summary_table.rows[i].cells[1].text = value
    doc.add_paragraph()

    doc.add_heading("Plan Review Checklist", level=1)
    checklist = get_checklist_for_review_type(st.session_state.wizard_review_type)
    for section_id, section_data in checklist.items():
        doc.add_heading(section_data["name"], level=2)
        for item in section_data["items"]:
            item_key = item["id"]
            status   = st.session_state.wizard_checklist_state.get(item_key, "Not Reviewed")
            para     = doc.add_paragraph()
            para.add_run(f"{item['id']} - {item['description']}")
            para.add_run("\n")
            sr = para.add_run(f"Status: {status}")
            sr.bold = True
            color_map = {"Yes": (0,128,0), "No": (200,0,0), "N/A": (128,128,128)}
            if status in color_map:
                sr.font.color.rgb = RGBColor(*color_map[status])
            if status == "No":
                selected    = st.session_state.wizard_selected_comments.get(item_key, [])
                custom_note = st.session_state.wizard_custom_notes.get(item_key, "")
                if selected or custom_note.strip():
                    para.add_run("\n")
                    cl = para.add_run("Comments:")
                    cl.bold = True; cl.font.color.rgb = RGBColor(0,0,128)
                    for cid in selected:
                        ct = COMMENTS.get(cid, "")
                        if ct:
                            cp = doc.add_paragraph()
                            cp.paragraph_format.left_indent = Inches(0.5)
                            cp.add_run(f"• [{cid}] {ct}").font.size = Pt(10)
                    if custom_note.strip():
                        cp = doc.add_paragraph()
                        cp.paragraph_format.left_indent = Inches(0.5)
                        cr = cp.add_run(f"• [CUSTOM] {custom_note}")
                        cr.font.size = Pt(10); cr.italic = True
        doc.add_paragraph()

    doc.add_page_break()
    doc.add_heading("Comments for Copy/Paste", level=1)
    intro = doc.add_paragraph()
    intro.add_run("Use the comments below for Bluebeam or permit system. ").italic = True
    intro.add_run("Only items marked 'No' with selected comments are included.").italic = True
    if st.session_state.wizard_resubmittal == "Yes":
        intro.add_run(" Resubmittal comment appended at end.").italic = True
    doc.add_paragraph()

    all_comments = collect_all_comments()
    if all_comments:
        for i, comment in enumerate(all_comments, 1):
            p = doc.add_paragraph()
            p.add_run(f"{i}. ").bold = True
            p.add_run(comment)
            doc.add_paragraph()
    else:
        doc.add_paragraph("No comments to include — all items are compliant or N/A.")

    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf


# ── LAMA CSV export ────────────────────────────────────────────────────────────
def generate_lama_csv():
    comments = collect_all_comments()
    if not comments:
        return None
    buf = StringIO()
    w   = csv.writer(buf, quoting=csv.QUOTE_ALL)
    w.writerow(["Comments"])
    for c in comments:
        w.writerow([c])
    return buf.getvalue().encode("utf-8")


# ── Bluebeam BAX export ────────────────────────────────────────────────────────
def _generate_annotation_id():
    return "".join(random.choices(string.ascii_uppercase, k=16))

def _pdf_escape(text):
    return str(text).replace("\\","\\\\").replace("(","\\(").replace(")","\\)")

def _xml_escape(text):
    return (str(text)
            .replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
            .replace('"',"&quot;").replace("'","&apos;"))

def _build_annotation_raw(comment_text, reviewer, annot_id, rect, pdf_date):
    x1, y1, x2, y2 = rect
    html_text = (comment_text
                 .replace("&","&amp;").replace("<","&lt;").replace(">","&gt;"))
    raw_str = (
        '<</DA(0 0.5019608 0 rg /Helv 12 Tf)'
        '/DS(font: Helvetica 12pt; text-align:left; margin:0pt; '
        'line-height:13.8pt; color:#000000)'
        f'/TempBBox[{x1} {y1} {x2} {y2}]'
        '/FillOpacity 0.25'
        f'/T({_pdf_escape(reviewer)})'
        f'/CreationDate({pdf_date})'
        '/RC(<?xml version="1.0"?>'
        '<body xmlns:xfa="http://www.xfa.org/schema/xfa-data/1.0/"'
        ' xfa:contentType="text/html"'
        ' xfa:APIVersion="BluebeamPDFRevu:2018"'
        ' xfa:spec="2.2.0"'
        ' style="font: Helvetica 12pt; text-align:left; margin:0pt; '
        'line-height:13.8pt; color:#000000"'
        ' xmlns="http://www.w3.org/1999/xhtml">'
        f'<p>{_pdf_escape(html_text)}</p></body>)'
        '/Subj(Engineering)'
        f'/NM({annot_id})'
        '/Subtype/FreeText'
        f'/Rect[{x1} {y1} {x2} {y2}]'
        f'/Contents({_pdf_escape(comment_text)})'
        '/F 4'
        '/C[0 0.5019608 0]'
        '/BS<</W 0.75/S/S/Type/Border>>'
        f'/M({pdf_date})>>'
    )
    return zlib.compress(raw_str.encode("utf-8")).hex()

def generate_bluebeam_bax():
    comments = collect_all_comments()
    if not comments:
        return None
    reviewer   = st.session_state.wizard_reviewer or "Engineering"
    now        = datetime.now(_CT)
    iso_date   = now.strftime("%Y-%m-%dT%H:%M:%S") + ".0000000Z"
    pdf_date   = now.strftime("D:%Y%m%d%H%M%S") + "-06'00'"
    pw, ph     = 612, 792
    bw, bh     = 252, 108
    margin, gap = 36, 10
    cur_y_top  = ph - margin
    x1         = margin
    blocks     = []

    for i, comment in enumerate(comments):
        y2 = cur_y_top; y1 = cur_y_top - bh
        if y1 < margin and x1 == margin:
            x1 = margin + bw + margin
            cur_y_top = ph - margin
            y2 = cur_y_top; y1 = cur_y_top - bh
        x2  = x1 + bw
        aid = _generate_annotation_id()
        raw = _build_annotation_raw(comment, reviewer, aid, (x1,y1,x2,y2), pdf_date)
        blocks.append(
            f'    <Annotation>\n'
            f'      <Page>1</Page>\n'
            f'      <Contents>{_xml_escape(comment)}</Contents>\n'
            f'      <ModDate>{iso_date}</ModDate>\n'
            f'      <Color>#008000</Color>\n'
            f'      <Type>FreeText</Type>\n'
            f'      <ID>{aid}</ID>\n'
            f'      <TypeInternal>Bluebeam.PDF.Annotations.AnnotationFreeText</TypeInternal>\n'
            f'      <Raw>{raw}</Raw>\n'
            f'      <Index>{i}</Index>\n'
            f'      <Subject>Engineering</Subject>\n'
            f'      <CreationDate>{iso_date}</CreationDate>\n'
            f'      <Author>{_xml_escape(reviewer)}</Author>\n'
            f'    </Annotation>'
        )
        cur_y_top = y1 - gap

    bax = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<Document Version="1">\n'
        '  <Page Index="0">\n'
        f'    <Label>1</Label>\n'
        f'    <Width>{pw}</Width>\n'
        f'    <Height>{ph}</Height>\n'
        + "\n".join(blocks) + "\n"
        '  </Page>\n'
        '</Document>'
    )
    return b'\xef\xbb\xbf' + bax.replace('\n', '\r\n').encode("utf-8")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    initialize_session_state()

    page_header(
        title      = "Review Wizard",
        subtitle   = "Interactive plan review checklist with automatic comment generation",
        breadcrumb = "Wizard Mode",
    )

    # ═════════════════════════════════════════════════════════════════════
    # STEP 1 — Project Setup (3-col + reviewer row)
    # ═════════════════════════════════════════════════════════════════════
    section_heading("Step 1 — Project Setup")

    col1, col2, col3 = st.columns(3)

    with col1:
        review_type = st.selectbox(
            "Review Type",
            options=[""] + REVIEW_TYPES,
            index=0 if not st.session_state.wizard_review_type
                    else REVIEW_TYPES.index(st.session_state.wizard_review_type) + 1,
            key="review_type_select",
        )
        if review_type and review_type != st.session_state.wizard_review_type:
            st.session_state.wizard_review_type = review_type
            reset_checklist()
            st.rerun()
        elif review_type:
            st.session_state.wizard_review_type = review_type

    with col2:
        permit = st.text_input(
            "Permit Number",
            value=st.session_state.wizard_permit_number,
            placeholder="e.g., SW2024-001",
        )
        st.session_state.wizard_permit_number = permit

    with col3:
        address = st.text_input(
            "Site Address",
            value=st.session_state.wizard_address,
            placeholder="e.g., 1808 Sonoma Trce",
        )
        st.session_state.wizard_address = address

    # Reviewer in its own row (full width selectbox)
    reviewer = st.selectbox(
        "Reviewer",
        options=[""] + REVIEWERS,
        index=0 if not st.session_state.wizard_reviewer
                else REVIEWERS.index(st.session_state.wizard_reviewer) + 1,
    )
    st.session_state.wizard_reviewer = reviewer if reviewer else None

    if not st.session_state.wizard_review_type:
        st.markdown(
            '<div class="bw-status-warn" style="margin-top:16px">'
            'Select a review type above to begin the checklist.'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    # ═════════════════════════════════════════════════════════════════════
    # STEP 2 — Interactive Checklist
    # ═════════════════════════════════════════════════════════════════════
    st.markdown("<hr>", unsafe_allow_html=True)
    section_heading(f"Step 2 — {st.session_state.wizard_review_type} Checklist")

    checklist    = get_checklist_for_review_type(st.session_state.wizard_review_type)
    total_items  = sum(len(s["items"]) for s in checklist.values())
    completed    = len(st.session_state.wizard_checklist_state)

    st.progress(completed / total_items if total_items > 0 else 0)
    st.caption(f"{completed} of {total_items} items reviewed")

    # ── Sections ──────────────────────────────────────────────────────────
    for section_id, section_data in checklist.items():
        # Per-section progress badge
        section_items    = section_data["items"]
        section_done     = sum(
            1 for it in section_items
            if it["id"] in st.session_state.wizard_checklist_state
        )
        section_total    = len(section_items)
        progress_label   = f"{section_done}/{section_total} reviewed"

        # --- section header with progress badge ---
        st.markdown(
            f'<div class="bw-section-header">'
            f'<span>{section_data["name"]}</span>'
            f'<span class="section-progress">{progress_label}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Determine if this section should be in an expander
        # (keep expanded if any item in it has been touched or is active section)
        has_activity = any(
            it["id"] in st.session_state.wizard_checklist_state
            for it in section_items
        )

        expanded_default = has_activity or (
            st.session_state.wizard_open_section == section_id
        )

        with st.expander(
            f"{section_data['name']}  ·  {progress_label}",
            expanded=expanded_default,
        ):
            for item in section_items:
                item_key = item["id"]

                col_desc, col_ctrl = st.columns([3, 1])

                with col_desc:
                    st.markdown(
                        f"<div class='bw-item-row'>"
                        f"<span class='bw-item-id'>{item['id']}</span>"
                        f"<span class='bw-item-desc'>{item['description']}</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

                with col_ctrl:
                    current = st.session_state.wizard_checklist_state.get(item_key, "—")
                    # Segmented control — styled by CSS to look like a pill track
                    status = st.radio(
                        f"status_{item_key}",
                        options=["—", "Yes", "No", "N/A"],
                        index=["—","Yes","No","N/A"].index(current)
                               if current in ["—","Yes","No","N/A"] else 0,
                        key=f"seg_{item_key}",
                        horizontal=True,
                        label_visibility="collapsed",
                    )
                    if status and status != "—":
                        st.session_state.wizard_checklist_state[item_key] = status
                    elif item_key in st.session_state.wizard_checklist_state:
                        del st.session_state.wizard_checklist_state[item_key]

                # Comment panel slides in when "No" selected
                if st.session_state.wizard_checklist_state.get(item_key) == "No":
                    st.markdown('<div class="bw-comment-panel">', unsafe_allow_html=True)
                    st.markdown(
                        "<span class='bw-comment-panel-label'>Select Comments</span>",
                        unsafe_allow_html=True,
                    )

                    comment_ids = item.get("comment_ids", [])
                    if comment_ids:
                        if item_key not in st.session_state.wizard_selected_comments:
                            st.session_state.wizard_selected_comments[item_key] = []

                        for cid in comment_ids:
                            ctext   = COMMENTS.get(cid, "Comment not found")
                            preview = ctext[:140] + "…" if len(ctext) > 140 else ctext
                            is_sel  = cid in st.session_state.wizard_selected_comments[item_key]

                            checked = st.checkbox(
                                f"**{cid}**",
                                value=is_sel,
                                key=f"chk_{item_key}_{cid}",
                            )
                            # Show comment preview text beneath checkbox
                            st.markdown(
                                f"<div class='bw-comment-text'>{preview}</div>",
                                unsafe_allow_html=True,
                            )
                            if checked:
                                if cid not in st.session_state.wizard_selected_comments[item_key]:
                                    st.session_state.wizard_selected_comments[item_key].append(cid)
                            else:
                                if cid in st.session_state.wizard_selected_comments[item_key]:
                                    st.session_state.wizard_selected_comments[item_key].remove(cid)

                            if len(ctext) > 140:
                                with st.expander("View full comment"):
                                    st.write(ctext)

                    st.markdown(
                        "<span class='bw-comment-panel-label' "
                        "style='margin-top:12px;display:block'>Custom Note</span>",
                        unsafe_allow_html=True,
                    )
                    custom = st.text_area(
                        "custom",
                        value=st.session_state.wizard_custom_notes.get(item_key, ""),
                        key=f"custom_{item_key}",
                        height=72,
                        label_visibility="collapsed",
                        placeholder="Add additional comments specific to this review…",
                    )
                    st.session_state.wizard_custom_notes[item_key] = custom
                    st.markdown("</div>", unsafe_allow_html=True)

    # ═════════════════════════════════════════════════════════════════════
    # Standalone Resubmittal Question
    # ═════════════════════════════════════════════════════════════════════
    st.markdown('<div class="bw-resubmittal-box">', unsafe_allow_html=True)
    rc1, rc2 = st.columns([3, 1])

    with rc1:
        st.markdown("**📬 Add standard resubmittal comment?**")
        resub_text = COMMENTS.get("BB-0045", "")
        if resub_text:
            st.caption(f'BB-0045: "{resub_text}"')

    with rc2:
        resubmittal = st.radio(
            "Resubmittal",
            options=["—", "Yes", "N/A"],
            index=["—","Yes","N/A"].index(st.session_state.wizard_resubmittal)
                  if st.session_state.wizard_resubmittal in ["—","Yes","N/A"] else 0,
            key="resubmittal_radio",
            horizontal=True,
            label_visibility="collapsed",
        )
        st.session_state.wizard_resubmittal = resubmittal

    st.markdown("</div>", unsafe_allow_html=True)

    # ═════════════════════════════════════════════════════════════════════
    # STEP 3 — Review Summary & Export
    # ═════════════════════════════════════════════════════════════════════
    st.markdown("<hr>", unsafe_allow_html=True)
    section_heading("Step 3 — Review Summary & Export")

    yes_count  = sum(1 for v in st.session_state.wizard_checklist_state.values() if v == "Yes")
    no_count   = sum(1 for v in st.session_state.wizard_checklist_state.values() if v == "No")
    na_count   = sum(1 for v in st.session_state.wizard_checklist_state.values() if v == "N/A")
    has_comments = no_count > 0 or st.session_state.wizard_resubmittal == "Yes"

    # Metric row — large thin numbers
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric("Compliant",    yes_count)
    with m2: st.metric("Issues Found", no_count)
    with m3: st.metric("N/A",          na_count)
    with m4: st.metric("Total Reviewed", yes_count + no_count + na_count)

    st.markdown('<div class="bw-export-section">', unsafe_allow_html=True)
    st.markdown(
        "<div style='font-size:16px;font-weight:600;color:#22427C;"
        "margin-bottom:14px'>Export Review</div>",
        unsafe_allow_html=True,
    )

    if not has_comments and (yes_count + na_count) > 0:
        st.success("✅ No issues found — all reviewed items are compliant.")
    elif has_comments:
        parts = []
        if no_count > 0:
            parts.append(f"{no_count} issue(s) found")
        if st.session_state.wizard_resubmittal == "Yes":
            parts.append("resubmittal comment included")
        st.warning(f"⚠️ {' + '.join(parts)}.")

    # Row 1: Word doc + Clear
    col1, col2 = st.columns(2)
    with col1:
        if DOCX_AVAILABLE:
            if st.button("📄 Generate Word Document", type="primary", use_container_width=True):
                if not st.session_state.wizard_permit_number:
                    st.error("Please enter a permit number before exporting.")
                elif completed == 0:
                    st.error("Please review at least one item before exporting.")
                else:
                    buf = generate_word_document()
                    if buf:
                        fn = f"Review_{st.session_state.wizard_permit_number}_{datetime.now(_CT).strftime('%Y%m%d')}.docx"
                        st.download_button(
                            label       = "⬇️ Download Word Document",
                            data        = buf,
                            file_name   = fn,
                            mime        = "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            use_container_width=True,
                        )
        else:
            st.warning("python-docx not installed. Add it to requirements.txt.")

    with col2:
        if st.button("🗑️ Clear Review", use_container_width=True):
            reset_checklist()
            st.session_state.wizard_permit_number = ""
            st.session_state.wizard_address       = ""
            st.session_state.wizard_reviewer      = None
            st.rerun()

    # Row 2: LAMA + Bluebeam (only when there are comments)
    if has_comments:
        st.markdown(
            "<div style='font-size:12px;font-weight:700;letter-spacing:0.08em;"
            "text-transform:uppercase;color:#9CA3AF;margin:16px 0 8px'>"
            "Extract Comments</div>",
            unsafe_allow_html=True,
        )
        permit_num = st.session_state.wizard_permit_number or "review"
        datestamp  = datetime.now(_CT).strftime("%Y%m%d")
        ce1, ce2   = st.columns(2)

        with ce1:
            lama = generate_lama_csv()
            if lama:
                st.download_button(
                    label     = "📥 LAMA CSV (Comment Uploader)",
                    data      = lama,
                    file_name = f"LAMA_Comments_{permit_num}_{datestamp}.csv",
                    mime      = "text/csv",
                    use_container_width=True,
                    help      = "Single-column CSV for the LAMA Comment Uploader extension",
                )
        with ce2:
            bax = generate_bluebeam_bax()
            if bax:
                st.download_button(
                    label     = "📐 Bluebeam BAX File",
                    data      = bax,
                    file_name = f"Markups_{permit_num}_{datestamp}.bax",
                    mime      = "application/octet-stream",
                    use_container_width=True,
                    help      = "Import into Bluebeam via Markup → Import (.bax)",
                )

    st.markdown("</div>", unsafe_allow_html=True)  # /bw-export-section

    # Quick copy
    if has_comments:
        st.markdown("<hr>", unsafe_allow_html=True)
        section_heading("Quick Copy — All Comments")
        st.caption("Copy these comments directly into Bluebeam or your permit system:")

        quick_comments = []
        for section_id, section_data in checklist.items():
            for item in section_data["items"]:
                ikey = item["id"]
                if st.session_state.wizard_checklist_state.get(ikey) == "No":
                    for cid in st.session_state.wizard_selected_comments.get(ikey, []):
                        t = COMMENTS.get(cid, "")
                        if t:
                            quick_comments.append(f"[{cid}] {t}")
                    custom = st.session_state.wizard_custom_notes.get(ikey, "")
                    if custom.strip():
                        quick_comments.append(f"[CUSTOM] {custom}")

        if st.session_state.wizard_resubmittal == "Yes":
            rt = COMMENTS.get("BB-0045", "")
            if rt:
                quick_comments.append(f"[BB-0045] {rt}")

        if quick_comments:
            st.text_area(
                "All Comments",
                value="\n\n".join(f"{i+1}. {c}" for i, c in enumerate(quick_comments)),
                height=280,
                label_visibility="collapsed",
            )

    # Navigation
    st.markdown("<hr>", unsafe_allow_html=True)
    n1, n2 = st.columns(2)
    with n1:
        if st.button("← Dashboard", use_container_width=True):
            st.switch_page("app.py")
    with n2:
        if st.button("Q&A Mode →", use_container_width=True):
            st.switch_page("pages/1_QA_Mode.py")


if __name__ == "__main__":
    main()
    footer()
