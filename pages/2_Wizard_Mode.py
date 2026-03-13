"""
2_Wizard_Mode.py
================
City of Brentwood Engineering AI Assistant - V2
Wizard Mode — interactive plan review checklist with export.
"""

import streamlit as st
import sys
import re
import csv
import zlib
import random
import string
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

# Brentwood, TN — Central Time (handles CST/CDT automatically)
_CT = ZoneInfo("America/Chicago")
from io import BytesIO, StringIO

# pages/ is one level down — add both utils/ and repo root
sys.path.append(str(Path(__file__).parent.parent / "utils"))
sys.path.append(str(Path(__file__).parent.parent))

from checklist_data import (
    REVIEW_TYPES,
    REVIEWERS,
    CHECKLIST_SECTIONS,
    get_checklist_for_review_type
)
from comments_database import COMMENTS, get_comment
from theme import apply_theme, render_sidebar, page_header, section_heading, footer, get_favicon

try:
    from docx import Document
    from docx.shared import Inches, Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.style import WD_STYLE_TYPE
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

st.set_page_config(page_title="Wizard Mode — Brentwood Engineering AI",
                   page_icon=get_favicon(), layout="wide")

apply_theme()
render_sidebar(active="wizard")

# Wizard-specific CSS: comment boxes, back-to-top button, button active states
st.markdown("""
<style>
    /* ── Step headings (Step 1, Step 2, Step 3) ──────────────────────── */
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
    /* ── Checklist section header ─────────────────────────────────────── */
    .bw-section-header {
        background: #EEF2F9 !important;
        color: #22427C !important;
        padding: 0.65rem 1rem;
        border-left: 4px solid #F07138;
        margin: 1.2rem 0 0.5rem 0;
        font-size: 0.97rem;
        font-weight: 700;
        letter-spacing: 0.02em;
        border-radius: 0 6px 6px 0;
    }
    /* ── Comment box (shown when No selected) ────────────────────────── */
    .bw-comment-box {
        background: #FFFBF0 !important;
        color: #1A2332 !important;
        border: 1px solid #F6D860;
        border-left: 3px solid #E8A000;
        border-radius: 6px;
        padding: 0.75rem 1rem;
        margin: 0.4rem 0 0.4rem 1.5rem;
        font-size: 0.9em;
    }
    .bw-resubmittal-box {
        background: #EEF2F9 !important;
        color: #1A2332 !important;
        border: 2px solid #2F5C9C;
        border-radius: 8px;
        padding: 1rem 1.2rem;
        margin: 1rem 0;
    }
    .bw-export-section {
        background: #F0FDF4 !important;
        color: #1A2332 !important;
        border: 1px solid #BBF7D0;
        border-left: 4px solid #16A34A;
        border-radius: 8px;
        padding: 1rem 1.2rem;
        margin: 1rem 0;
    }
    /* ── Back-to-top floating button ─────────────────────────────────── */
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
<!-- Back-to-top anchor + button -->
<div id="page-top"></div>
<a id="btt-btn" href="#page-top" title="Back to top">↑</a>
<script>
    window.addEventListener('scroll', function() {
        var btn = document.getElementById('btt-btn');
        if (btn) {
            btn.classList.toggle('visible', window.scrollY > 300);
        }
    }, {passive: true});
</script>
""", unsafe_allow_html=True)

def initialize_session_state():
    """Initialize session state variables"""
    if 'wizard_review_type' not in st.session_state:
        st.session_state.wizard_review_type = None
    if 'wizard_permit_number' not in st.session_state:
        st.session_state.wizard_permit_number = ""
    if 'wizard_address' not in st.session_state:
        st.session_state.wizard_address = ""
    if 'wizard_reviewer' not in st.session_state:
        st.session_state.wizard_reviewer = None
    if 'wizard_checklist_state' not in st.session_state:
        st.session_state.wizard_checklist_state = {}
    if 'wizard_selected_comments' not in st.session_state:
        st.session_state.wizard_selected_comments = {}
    if 'wizard_custom_notes' not in st.session_state:
        st.session_state.wizard_custom_notes = {}
    if 'wizard_started' not in st.session_state:
        st.session_state.wizard_started = False
    if 'wizard_resubmittal' not in st.session_state:
        st.session_state.wizard_resubmittal = "—"


def reset_checklist():
    """Reset checklist state when review type changes"""
    st.session_state.wizard_checklist_state = {}
    st.session_state.wizard_selected_comments = {}
    st.session_state.wizard_custom_notes = {}
    st.session_state.wizard_resubmittal = "—"


def collect_all_comments():
    """
    Collect all comments from checklist items marked 'No', then append
    the resubmittal comment (BB-0045) at the very end if the standalone
    resubmittal question was answered 'Yes'.

    Returns a list of raw comment strings (no prefix codes).
    Used by all export functions to ensure consistent output.
    """
    checklist = get_checklist_for_review_type(st.session_state.wizard_review_type)
    all_comments = []

    # Gather comments from all checklist items marked "No"
    for section_id, section_data in checklist.items():
        for item in section_data["items"]:
            item_key = item["id"]
            if st.session_state.wizard_checklist_state.get(item_key) == "No":
                selected = st.session_state.wizard_selected_comments.get(item_key, [])
                custom_note = st.session_state.wizard_custom_notes.get(item_key, "")

                for comment_id in selected:
                    comment_text = COMMENTS.get(comment_id, "")
                    if comment_text:
                        all_comments.append(comment_text)

                if custom_note.strip():
                    all_comments.append(custom_note.strip())

    # Append resubmittal comment at the very end if "Yes" was selected
    if st.session_state.wizard_resubmittal == "Yes":
        resubmittal_text = COMMENTS.get("BB-0045", "")
        if resubmittal_text:
            all_comments.append(resubmittal_text)

    return all_comments


def generate_word_document():
    """Generate a Word document with review comments"""
    if not DOCX_AVAILABLE:
        return None
    
    doc = Document()
    
    # =========================================================================
    # TITLE
    # =========================================================================
    title = doc.add_heading('Engineering Plan Review', 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # =========================================================================
    # PROJECT INFORMATION
    # =========================================================================
    doc.add_heading('Project Information', level=1)
    info_table = doc.add_table(rows=5, cols=2)
    info_table.style = 'Table Grid'
    
    info_data = [
        ('Review Type:', st.session_state.wizard_review_type or 'Not specified'),
        ('Permit Number:', st.session_state.wizard_permit_number or 'Not specified'),
        ('Address:', st.session_state.wizard_address or 'Not specified'),
        ('Reviewer:', st.session_state.wizard_reviewer or 'Not specified'),
        ('Review Date:', datetime.now(_CT).strftime('%Y-%m-%d %I:%M %p')),
    ]
    
    for i, (label, value) in enumerate(info_data):
        info_table.rows[i].cells[0].text = label
        info_table.rows[i].cells[1].text = value
        info_table.rows[i].cells[0].paragraphs[0].runs[0].bold = True
    
    doc.add_paragraph()
    
    # =========================================================================
    # SUMMARY STATISTICS
    # =========================================================================
    doc.add_heading('Review Summary', level=1)
    
    yes_count = sum(1 for v in st.session_state.wizard_checklist_state.values() if v == "Yes")
    no_count = sum(1 for v in st.session_state.wizard_checklist_state.values() if v == "No")
    na_count = sum(1 for v in st.session_state.wizard_checklist_state.values() if v == "N/A")
    total = yes_count + no_count + na_count
    
    summary_table = doc.add_table(rows=5, cols=2)
    summary_table.style = 'Table Grid'
    summary_data = [
        ('Total Items Reviewed:', str(total)),
        ('Compliant (Yes):', str(yes_count)),
        ('Issues Found (No):', str(no_count)),
        ('Not Applicable:', str(na_count)),
        ('Resubmittal Comment:', st.session_state.wizard_resubmittal),
    ]
    for i, (label, value) in enumerate(summary_data):
        summary_table.rows[i].cells[0].text = label
        summary_table.rows[i].cells[1].text = value
    
    doc.add_paragraph()
    
    # =========================================================================
    # FULL CHECKLIST WITH STATUS AND COMMENTS
    # =========================================================================
    doc.add_heading('Plan Review Checklist', level=1)
    
    checklist = get_checklist_for_review_type(st.session_state.wizard_review_type)
    
    for section_id, section_data in checklist.items():
        section_heading = doc.add_heading(section_data["name"], level=2)
        
        for item in section_data["items"]:
            item_key = item["id"]
            status = st.session_state.wizard_checklist_state.get(item_key, "Not Reviewed")
            
            para = doc.add_paragraph()
            item_run = para.add_run(f"{item['id']} - {item['description']}")
            item_run.bold = False
            
            para.add_run("\n")
            status_run = para.add_run(f"Status: {status}")
            status_run.bold = True
            
            if status == "Yes":
                status_run.font.color.rgb = RGBColor(0, 128, 0)
            elif status == "No":
                status_run.font.color.rgb = RGBColor(200, 0, 0)
            elif status == "N/A":
                status_run.font.color.rgb = RGBColor(128, 128, 128)
            else:
                status_run.font.color.rgb = RGBColor(255, 165, 0)
            
            if status == "No":
                selected = st.session_state.wizard_selected_comments.get(item_key, [])
                custom_note = st.session_state.wizard_custom_notes.get(item_key, "")
                
                if selected or custom_note.strip():
                    para.add_run("\n")
                    comments_label = para.add_run("Comments:")
                    comments_label.bold = True
                    comments_label.font.color.rgb = RGBColor(0, 0, 128)
                    
                    for comment_id in selected:
                        comment_text = COMMENTS.get(comment_id, "")
                        if comment_text:
                            comment_para = doc.add_paragraph()
                            comment_para.paragraph_format.left_indent = Inches(0.5)
                            comment_run = comment_para.add_run(f"• [{comment_id}] {comment_text}")
                            comment_run.font.size = Pt(10)
                    
                    if custom_note.strip():
                        custom_para = doc.add_paragraph()
                        custom_para.paragraph_format.left_indent = Inches(0.5)
                        custom_run = custom_para.add_run(f"• [CUSTOM] {custom_note}")
                        custom_run.font.size = Pt(10)
                        custom_run.italic = True
        
        doc.add_paragraph()
    
    # =========================================================================
    # RESUBMITTAL STATUS IN DOCUMENT
    # =========================================================================
    if st.session_state.wizard_resubmittal == "Yes":
        doc.add_heading('Resubmittal', level=2)
        resub_para = doc.add_paragraph()
        resub_run = resub_para.add_run("Standard resubmittal comment included (BB-0045)")
        resub_run.bold = True
        resub_run.font.color.rgb = RGBColor(0, 0, 128)
    
    # =========================================================================
    # COMMENTS FOR COPY/PASTE (Only "No" items + resubmittal)
    # =========================================================================
    doc.add_page_break()
    doc.add_heading('Comments for Copy/Paste', level=1)
    
    intro_para = doc.add_paragraph()
    intro_para.add_run("Use the comments below for Bluebeam or permit system. ").italic = True
    intro_para.add_run("Only items marked 'No' with selected comments are included.").italic = True
    if st.session_state.wizard_resubmittal == "Yes":
        intro_para.add_run(" Resubmittal comment appended at end.").italic = True
    doc.add_paragraph()
    
    all_comments = collect_all_comments()
    
    if all_comments:
        for i, comment in enumerate(all_comments, 1):
            para = doc.add_paragraph()
            num_run = para.add_run(f"{i}. ")
            num_run.bold = True
            para.add_run(comment)
            doc.add_paragraph()
    else:
        doc.add_paragraph("No comments to include - all items are compliant or N/A.")
    
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer


# =============================================================================
# LAMA CSV EXPORT
# =============================================================================

def generate_lama_csv():
    """
    Generate CSV for the LAMA Comment Uploader chrome extension.
    Format: Single column with header 'Comments', RFC 4180 quoting.
    Includes resubmittal comment at end if selected.
    """
    comments = collect_all_comments()
    if not comments:
        return None

    buffer = StringIO()
    writer = csv.writer(buffer, quoting=csv.QUOTE_ALL)
    writer.writerow(["Comments"])
    for comment in comments:
        writer.writerow([comment])

    return buffer.getvalue().encode('utf-8')


# =============================================================================
# BLUEBEAM BAX EXPORT (Bluebeam Markup Archive)
# =============================================================================

def _generate_annotation_id():
    """Generate a 16-character uppercase letter ID matching Bluebeam convention."""
    return ''.join(random.choices(string.ascii_uppercase, k=16))


def _pdf_escape(text):
    """Escape special characters for PDF string literals inside ()."""
    return (str(text)
            .replace("\\", "\\\\")
            .replace("(", "\\(")
            .replace(")", "\\)"))


def _xml_escape(text):
    """Escape special characters for XML text content."""
    return (str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;"))


def _build_annotation_raw(comment_text, reviewer, annot_id, rect, pdf_date):
    """
    Build the zlib-compressed, hex-encoded Raw field for a BAX annotation.
    Contains the full PDF annotation dictionary with styling:
      - Green (#008000) border and fill
      - 25% fill opacity
      - Helvetica 12pt black text
      - 0.75pt solid border
    """
    x1, y1, x2, y2 = rect
    pdf_text = _pdf_escape(comment_text)
    pdf_reviewer = _pdf_escape(reviewer)
    html_text = (comment_text
                 .replace("&", "&amp;")
                 .replace("<", "&lt;")
                 .replace(">", "&gt;"))
    rc_text = _pdf_escape(html_text)

    raw_str = (
        '<</DA(0 0.5019608 0 rg /Helv 12 Tf)'
        '/DS(font: Helvetica 12pt; text-align:left; margin:0pt; '
        'line-height:13.8pt; color:#000000)'
        f'/TempBBox[{x1} {y1} {x2} {y2}]'
        '/FillOpacity 0.25'
        f'/T({pdf_reviewer})'
        f'/CreationDate({pdf_date})'
        '/RC(<?xml version="1.0"?>'
        '<body xmlns:xfa="http://www.xfa.org/schema/xfa-data/1.0/"'
        ' xfa:contentType="text/html"'
        ' xfa:APIVersion="BluebeamPDFRevu:2018"'
        ' xfa:spec="2.2.0"'
        ' style="font: Helvetica 12pt; text-align:left; margin:0pt; '
        'line-height:13.8pt; color:#000000"'
        ' xmlns="http://www.w3.org/1999/xhtml">'
        f'<p>{rc_text}</p></body>)'
        '/Subj(Engineering)'
        f'/NM({annot_id})'
        '/Subtype/FreeText'
        f'/Rect[{x1} {y1} {x2} {y2}]'
        f'/Contents({pdf_text})'
        '/F 4'
        '/C[0 0.5019608 0]'
        '/BS<</W 0.75/S/S/Type/Border>>'
        f'/M({pdf_date})>>'
    )

    compressed = zlib.compress(raw_str.encode('utf-8'))
    return compressed.hex()


def generate_bluebeam_bax():
    """
    Generate a Bluebeam BAX file with fully styled FreeText annotations.
    Includes resubmittal comment at end if selected.
    """
    comments = collect_all_comments()
    if not comments:
        return None

    reviewer = st.session_state.wizard_reviewer or "Engineering"
    now = datetime.now(_CT)
    iso_date = now.strftime("%Y-%m-%dT%H:%M:%S") + ".0000000Z"
    pdf_date = now.strftime("D:%Y%m%d%H%M%S") + "-06'00'"

    page_width, page_height = 612, 792
    box_width, box_height = 252, 108
    margin, gap = 36, 10
    current_y_top = page_height - margin
    x1 = margin

    annotation_blocks = []

    for i, comment in enumerate(comments):
        y2 = current_y_top
        y1 = current_y_top - box_height

        if y1 < margin and x1 == margin:
            x1 = margin + box_width + margin
            current_y_top = page_height - margin
            y2 = current_y_top
            y1 = current_y_top - box_height

        x2 = x1 + box_width
        rect = (x1, y1, x2, y2)
        annot_id = _generate_annotation_id()
        raw_hex = _build_annotation_raw(comment, reviewer, annot_id, rect, pdf_date)

        annotation_xml = (
            '    <Annotation>\n'
            '      <Page>1</Page>\n'
            f'      <Contents>{_xml_escape(comment)}</Contents>\n'
            f'      <ModDate>{iso_date}</ModDate>\n'
            '      <Color>#008000</Color>\n'
            '      <Type>FreeText</Type>\n'
            f'      <ID>{annot_id}</ID>\n'
            '      <TypeInternal>Bluebeam.PDF.Annotations.AnnotationFreeText'
            '</TypeInternal>\n'
            f'      <Raw>{raw_hex}</Raw>\n'
            f'      <Index>{i}</Index>\n'
            '      <Subject>Engineering</Subject>\n'
            f'      <CreationDate>{iso_date}</CreationDate>\n'
            f'      <Author>{_xml_escape(reviewer)}</Author>\n'
            '    </Annotation>'
        )

        annotation_blocks.append(annotation_xml)
        current_y_top = y1 - gap

    annotations_str = '\n'.join(annotation_blocks)

    bax_content = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<Document Version="1">\n'
        '  <Page Index="0">\n'
        '    <Label>1</Label>\n'
        f'    <Width>{page_width}</Width>\n'
        f'    <Height>{page_height}</Height>\n'
        f'{annotations_str}\n'
        '  </Page>\n'
        '</Document>'
    )

    bax_crlf = bax_content.replace('\n', '\r\n')
    return b'\xef\xbb\xbf' + bax_crlf.encode('utf-8')


@st.fragment
def _render_checklist():
    """
    Checklist + resubmittal section as a st.fragment.

    st.fragment causes ONLY this section to rerender when a Yes/No/NA button
    is clicked. The page header, sidebar, CSS injection, and Step 3 summary
    do NOT rerender — button clicks feel instantaneous.
    """
    review_type = st.session_state.wizard_review_type
    if not review_type:
        return

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown(f"<div class='bw-step-heading'>Step 2 — {review_type} Checklist</div>", unsafe_allow_html=True)

    checklist     = get_checklist_for_review_type(review_type)
    total_items   = sum(len(s["items"]) for s in checklist.values())
    completed_items = len(st.session_state.wizard_checklist_state)

    st.progress(completed_items / total_items if total_items > 0 else 0)
    st.caption(f"Progress: {completed_items} of {total_items} items reviewed")

    # ── Sections as collapsed expanders ───────────────────────────────────
    # wizard_open_section tracks which section the user last clicked in,
    # so the expander stays open after a button press.
    if "wizard_open_section" not in st.session_state:
        st.session_state.wizard_open_section = list(checklist.keys())[0]

    # Sequential display counters — these control what numbers the user SEES.
    # The internal item["id"] values (e.g. "6.3", "16.2") never change because
    # they are used as session state keys, comment lookups, and export labels.
    # We simply replace the hard-coded numbers in the display with a clean
    # 1, 2, 3… for sections and 1.1, 1.2… for items so there are never gaps
    # caused by deleted items or permit-type filtering.
    display_section_num = 0

    for section_id, section_data in checklist.items():
        section_items = section_data["items"]
        section_done  = sum(
            1 for it in section_items
            if it["id"] in st.session_state.wizard_checklist_state
        )
        section_total = len(section_items)
        all_done      = section_done == section_total

        # Increment the visible section number for each section that appears
        display_section_num += 1

        # Strip the original hard-coded number from the section name
        # e.g. "6. Retaining Walls" → "Retaining Walls", then prepend display num
        raw_name = section_data["name"]
        # Remove leading digits and period/dot if present (e.g. "6. " or "16. ")
        clean_name = re.sub(r'^\d+\.\s*', '', raw_name)
        display_section_name = f"{display_section_num}. {clean_name}"

        status_icon     = "✅" if all_done else "📋"
        expander_label  = (
            f"{status_icon} {display_section_name}  "
            f"({section_done}/{section_total} reviewed)"
        )

        default_open = (section_id == st.session_state.wizard_open_section)

        with st.expander(expander_label, expanded=default_open):
            # Sequential item counter resets for each section: 1.1, 1.2, 1.3…
            display_item_num = 0

            for item in section_items:
                item_key       = item["id"]
                current_status = st.session_state.wizard_checklist_state.get(item_key, "—")

                display_item_num += 1
                display_item_label = f"{display_section_num}.{display_item_num}"

                # ── Item row: description + Yes / No / N/A buttons ────────────
                desc_col, yes_col, no_col, na_col = st.columns([5, 1, 1, 1])

                with desc_col:
                    st.markdown(
                        f"<div style='padding:0.4rem 0;font-size:0.93rem;'>"
                        f"<strong style='color:#22427C'>{display_item_label}</strong>"
                        f" — {item['description']}</div>",
                        unsafe_allow_html=True
                    )

                with yes_col:
                    def _set_yes(k=item_key, s=section_id):
                        st.session_state.wizard_checklist_state[k] = "Yes"
                        st.session_state.wizard_selected_comments.pop(k, None)
                        st.session_state.wizard_open_section = s
                    yes_type = "primary" if current_status == "Yes" else "secondary"
                    st.button("✓ Yes", key=f"yes_{item_key}", type=yes_type,
                              use_container_width=True, on_click=_set_yes)

                with no_col:
                    def _set_no(k=item_key, s=section_id):
                        st.session_state.wizard_checklist_state[k] = "No"
                        st.session_state.wizard_open_section = s
                    no_type = "primary" if current_status == "No" else "secondary"
                    st.button("✗ No", key=f"no_{item_key}", type=no_type,
                              use_container_width=True, on_click=_set_no)

                with na_col:
                    def _set_na(k=item_key, s=section_id):
                        st.session_state.wizard_checklist_state[k] = "N/A"
                        st.session_state.wizard_selected_comments.pop(k, None)
                        st.session_state.wizard_open_section = s
                    na_type = "primary" if current_status == "N/A" else "secondary"
                    st.button("N/A", key=f"na_{item_key}", type=na_type,
                              use_container_width=True, on_click=_set_na)

                # ── Comment panel (only when No selected) ─────────────────────
                if st.session_state.wizard_checklist_state.get(item_key) == "No":
                    with st.container():
                        st.markdown('<div class="bw-comment-box">', unsafe_allow_html=True)
                        st.markdown("**📝 Select applicable comments:**")

                        comment_ids = item.get("comment_ids", [])
                        if comment_ids:
                            if item_key not in st.session_state.wizard_selected_comments:
                                st.session_state.wizard_selected_comments[item_key] = []

                            for comment_id in comment_ids:
                                comment_text = COMMENTS.get(comment_id, "Comment not found")
                                display_text = comment_text[:150] + "..." if len(comment_text) > 150 else comment_text
                                is_selected  = comment_id in st.session_state.wizard_selected_comments[item_key]

                                if st.checkbox(
                                    f"**{comment_id}**: {display_text}",
                                    value=is_selected,
                                    key=f"comment_{item_key}_{comment_id}"
                                ):
                                    if comment_id not in st.session_state.wizard_selected_comments[item_key]:
                                        st.session_state.wizard_selected_comments[item_key].append(comment_id)
                                else:
                                    if comment_id in st.session_state.wizard_selected_comments[item_key]:
                                        st.session_state.wizard_selected_comments[item_key].remove(comment_id)

                                # Nested expanders are illegal in Streamlit —
                                # show the full text as a small caption instead.
                                if len(comment_text) > 150:
                                    st.caption(comment_text)

                        st.markdown("**✏️ Custom notes (optional):**")
                        custom_note = st.text_area(
                            "Custom note",
                            value=st.session_state.wizard_custom_notes.get(item_key, ""),
                            key=f"custom_{item_key}",
                            height=80,
                            label_visibility="collapsed",
                            placeholder="Add any additional comments specific to this review..."
                        )
                        st.session_state.wizard_custom_notes[item_key] = custom_note
                        st.markdown('</div>', unsafe_allow_html=True)

                st.markdown("---")


def main():
    """Main function for Wizard Mode"""
    initialize_session_state()

    page_header(
        title="Engineering Checklist Mode",
        subtitle="Interactive plan review checklist with automatic comment generation",
    )

    # =========================================================================
    # STEP 1: PROJECT SETUP
    # =========================================================================
    st.markdown("<div class='bw-step-heading'>Step 1 — Project Setup</div>", unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        review_type = st.selectbox(
            "Review Type",
            options=[""] + REVIEW_TYPES,
            index=0 if not st.session_state.wizard_review_type else REVIEW_TYPES.index(st.session_state.wizard_review_type) + 1,
            key="review_type_select"
        )
        
        if review_type and review_type != st.session_state.wizard_review_type:
            st.session_state.wizard_review_type = review_type
            reset_checklist()
            st.rerun()
        elif review_type:
            st.session_state.wizard_review_type = review_type
    
    with col2:
        permit_number = st.text_input(
            "Permit Number",
            value=st.session_state.wizard_permit_number,
            placeholder="e.g., SW2024-001"
        )
        st.session_state.wizard_permit_number = permit_number
    
    with col3:
        address = st.text_input(
            "Address",
            value=st.session_state.wizard_address,
            placeholder="e.g., 1808 Sonoma Trce"
        )
        st.session_state.wizard_address = address
    
    with col4:
        reviewer = st.selectbox(
            "Reviewer",
            options=[""] + REVIEWERS,
            index=0 if not st.session_state.wizard_reviewer else REVIEWERS.index(st.session_state.wizard_reviewer) + 1
        )
        st.session_state.wizard_reviewer = reviewer if reviewer else None
    
    if not st.session_state.wizard_review_type:
        st.markdown('<div class="bw-status-warn">Select a review type above to begin the checklist.</div>', unsafe_allow_html=True)
        return
    
    # =========================================================================
    # STEP 2: INTERACTIVE CHECKLIST
    # Wrapped in @st.fragment so only this section rerenders on button clicks.
    # Sections are st.expanders (collapsed by default) — only the active section
    # renders its items, keeping the widget count low.
    # =========================================================================
    _render_checklist()

    # =========================================================================
    # STANDALONE RESUBMITTAL QUESTION
    # Positioned between the checklist and Step 3, inside its own styled box
    # =========================================================================
    st.markdown('<div class="bw-resubmittal-box">', unsafe_allow_html=True)
    
    resub_col1, resub_col2 = st.columns([3, 1])
    
    with resub_col1:
        st.markdown("**📬 Add standard resubmittal comment?**")
        # Show preview of what BB-0045 says
        resub_text = COMMENTS.get("BB-0045", "")
        if resub_text:
            st.caption(f'BB-0045: "{resub_text}"')
    
    with resub_col2:
        resubmittal = st.radio(
            "Resubmittal",
            options=["—", "Yes", "N/A"],
            index=["—", "Yes", "N/A"].index(st.session_state.wizard_resubmittal) if st.session_state.wizard_resubmittal in ["—", "Yes", "N/A"] else 0,
            key="resubmittal_radio",
            horizontal=True,
            label_visibility="collapsed"
        )
        st.session_state.wizard_resubmittal = resubmittal
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # =========================================================================
    # STEP 3: REVIEW SUMMARY & EXPORT
    # =========================================================================
    st.markdown("---")
    st.markdown("<div class='bw-step-heading'>📊 Step 3 — Review Summary &amp; Export</div>", unsafe_allow_html=True)
    
    yes_count = sum(1 for v in st.session_state.wizard_checklist_state.values() if v == "Yes")
    no_count = sum(1 for v in st.session_state.wizard_checklist_state.values() if v == "No")
    na_count = sum(1 for v in st.session_state.wizard_checklist_state.values() if v == "N/A")
    
    # Include resubmittal in the "has comments" logic
    has_comments = no_count > 0 or st.session_state.wizard_resubmittal == "Yes"
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("✅ Compliant", yes_count)
    with col2:
        st.metric("❌ Issues Found", no_count)
    with col3:
        st.metric("➖ N/A", na_count)
    with col4:
        st.metric("📝 Total Reviewed", yes_count + no_count + na_count)
    
    # Export section
    st.markdown('<div class="bw-export-section">', unsafe_allow_html=True)
    st.markdown("### 📤 Export Review")
    
    if not has_comments and (yes_count + na_count) > 0:
        st.success("✅ No issues found! All reviewed items are compliant.")
    elif has_comments:
        comment_parts = []
        if no_count > 0:
            comment_parts.append(f"{no_count} issue(s) found")
        if st.session_state.wizard_resubmittal == "Yes":
            comment_parts.append("resubmittal comment included")
        st.warning(f"⚠️ {' + '.join(comment_parts)}.")
    
    # Row 1: Word Document + Clear Review
    col1, col2 = st.columns(2)
    
    with col1:
        if DOCX_AVAILABLE:
            if st.button("📄 Generate Word Document", type="primary", use_container_width=True):
                if not st.session_state.wizard_permit_number:
                    st.error("Please enter a permit number before exporting.")
                elif completed_items == 0:
                    st.error("Please review at least one item before exporting.")
                else:
                    doc_buffer = generate_word_document()
                    if doc_buffer:
                        filename = f"Review_{st.session_state.wizard_permit_number}_{datetime.now(_CT).strftime('%Y%m%d')}.docx"
                        st.download_button(
                            label="⬇️ Download Word Document",
                            data=doc_buffer,
                            file_name=filename,
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            use_container_width=True
                        )
        else:
            st.warning("python-docx not available. Install it to enable Word export.")
    
    with col2:
        if st.button("🗑️ Clear Review", use_container_width=True):
            reset_checklist()
            st.session_state.wizard_permit_number = ""
            st.session_state.wizard_address = ""
            st.session_state.wizard_reviewer = None
            st.rerun()

    # Row 2: LAMA CSV + Bluebeam BAX (shown when there are any comments)
    if has_comments:
        st.markdown("#### 📊 Extract Comments")

        permit_num = st.session_state.wizard_permit_number or "review"
        datestamp = datetime.now(_CT).strftime('%Y%m%d')

        col_e1, col_e2 = st.columns(2)

        with col_e1:
            lama_data = generate_lama_csv()
            if lama_data:
                st.download_button(
                    label="📥 Create CSV File of Comments",
                    data=lama_data,
                    file_name=f"LAMA_Comments_{permit_num}_{datestamp}.csv",
                    mime="text/csv",
                    use_container_width=True,
                    help="Single-column CSV for the LAMA Comment Uploader extension"
                )

        with col_e2:
            bax_data = generate_bluebeam_bax()
            if bax_data:
                st.download_button(
                    label="📐 Create Bluebeam Comments File",
                    data=bax_data,
                    file_name=f"Markups_{permit_num}_{datestamp}.bax",
                    mime="application/octet-stream",
                    use_container_width=True,
                    help="Import into Bluebeam via Markup → Import (.bax format with full styling)"
                )
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Quick copy section for comments
    if has_comments:
        st.markdown("---")
        st.subheader("📋 Quick Copy - All Comments")
        st.caption("Copy these comments directly into Bluebeam or your permit system:")
        
        all_comments = []
        checklist = get_checklist_for_review_type(st.session_state.wizard_review_type)
        for section_id, section_data in checklist.items():
            for item in section_data["items"]:
                item_key = item["id"]
                if st.session_state.wizard_checklist_state.get(item_key) == "No":
                    selected = st.session_state.wizard_selected_comments.get(item_key, [])
                    custom_note = st.session_state.wizard_custom_notes.get(item_key, "")
                    
                    for comment_id in selected:
                        comment_text = COMMENTS.get(comment_id, "")
                        if comment_text:
                            all_comments.append(f"[{comment_id}] {comment_text}")
                    
                    if custom_note.strip():
                        all_comments.append(f"[CUSTOM] {custom_note}")
        
        # Append resubmittal at the end
        if st.session_state.wizard_resubmittal == "Yes":
            resub_text = COMMENTS.get("BB-0045", "")
            if resub_text:
                all_comments.append(f"[BB-0045] {resub_text}")
        
        if all_comments:
            comments_text = "\n\n".join(f"{i+1}. {c}" for i, c in enumerate(all_comments))
            st.text_area(
                "All Comments",
                value=comments_text,
                height=300,
                label_visibility="collapsed"
            )
    
    # Navigation
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🏠 Home"):
            st.switch_page("app.py")
    with col2:
        if st.button("💬 Q&A Mode"):
            st.switch_page("pages/1_QA_Mode.py")


if __name__ == "__main__":
    main()
    footer()
