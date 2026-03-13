"""
3_Performance.py
================
City of Brentwood Engineering AI Assistant - V2
Performance Profiler — measures render time of every major phase.

HOW TO USE:
    1. Navigate to this page in the app
    2. Every render automatically logs timing data
    3. Click "Run Render Stress Test" to simulate rapid interactions
    4. Read the bottleneck report at the bottom

WHAT IT MEASURES:
    - Theme CSS injection time
    - Sidebar render time
    - Logo base64 encoding time
    - drive_loader / database path check time
    - RAG engine cache lookup time
    - Total page render time
    - Per-phase breakdown with pass/warn/fail thresholds
"""

import streamlit as st
import sys
import time
import traceback
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent / "utils"))
sys.path.append(str(Path(__file__).parent.parent))

# ── Page config — minimal, no get_favicon() to avoid skewing results ──────────
st.set_page_config(
    page_title="Performance Profiler — Brentwood Engineering AI",
    page_icon="⏱️",
    layout="wide",
)

# ── Timing infrastructure ─────────────────────────────────────────────────────

class RenderTimer:
    """Records wall-clock time for each named phase of a render."""
    def __init__(self):
        self.phases = []
        self._start = None
        self._phase_name = None
        self.render_start = time.perf_counter()

    def begin(self, phase_name: str):
        self._phase_name = phase_name
        self._start = time.perf_counter()

    def end(self):
        if self._start is None:
            return
        elapsed_ms = (time.perf_counter() - self._start) * 1000
        self.phases.append((self._phase_name, elapsed_ms))
        self._start = None
        self._phase_name = None
        return elapsed_ms

    def total_ms(self):
        return (time.perf_counter() - self.render_start) * 1000

    def report(self) -> dict:
        return {name: ms for name, ms in self.phases}


timer = RenderTimer()

# ── Initialize session state ──────────────────────────────────────────────────
if "perf_history" not in st.session_state:
    st.session_state.perf_history = []   # list of render reports
if "render_count" not in st.session_state:
    st.session_state.render_count = 0

st.session_state.render_count += 1
render_num = st.session_state.render_count

# ═════════════════════════════════════════════════════════════════════════════
# PHASE 1: theme import + apply_theme + render_sidebar
# ═════════════════════════════════════════════════════════════════════════════
timer.begin("theme_import")
try:
    from theme import apply_theme, render_sidebar, get_favicon, _logo_bytes, _LOGO_CACHE
    theme_imported = True
except Exception as e:
    theme_imported = False
    theme_error = str(e)
theme_import_ms = timer.end()

timer.begin("apply_theme()")
try:
    if theme_imported:
        apply_theme()
except Exception as e:
    pass
apply_theme_ms = timer.end()

timer.begin("render_sidebar()")
try:
    if theme_imported:
        render_sidebar(active="home")
except Exception as e:
    pass
render_sidebar_ms = timer.end()

# ═════════════════════════════════════════════════════════════════════════════
# PHASE 2: Logo encoding
# ═════════════════════════════════════════════════════════════════════════════
timer.begin("get_favicon() call")
try:
    if theme_imported:
        fav = get_favicon()
        favicon_cached = True
except Exception as e:
    favicon_cached = False
favicon_ms = timer.end()

timer.begin("_logo_bytes() call")
try:
    if theme_imported:
        from theme import _logo_bytes
        logo = _logo_bytes(color=True)
        logo_len = len(logo) if logo else 0
except Exception as e:
    logo_len = 0
logo_ms = timer.end()

# ═════════════════════════════════════════════════════════════════════════════
# PHASE 3: drive_loader / database check
# ═════════════════════════════════════════════════════════════════════════════
timer.begin("load_database()")
db_result = None
try:
    from drive_loader import load_database
    db_result = load_database()
    db_success = db_result.get("success", False)
except Exception as e:
    db_success = False
    db_result = {"error": str(e)}
db_ms = timer.end()

# ═════════════════════════════════════════════════════════════════════════════
# PHASE 4: RAG engine cache lookup
# ═════════════════════════════════════════════════════════════════════════════
timer.begin("get_rag_engine() cache lookup")
engine_ready = False
engine_stats = {}
try:
    from rag_engine import get_rag_engine
    if db_result and db_result.get("success"):
        engine = get_rag_engine(db_result["local_path"])
        engine_ready = engine.is_ready()
        engine_stats = engine.get_collection_stats() if engine_ready else {}
except Exception as e:
    pass
engine_ms = timer.end()

# ═════════════════════════════════════════════════════════════════════════════
# PHASE 5: CSS payload size measurement
# ═════════════════════════════════════════════════════════════════════════════
timer.begin("CSS payload measure")
try:
    from theme import _CSS
    css_size_bytes = len(_CSS.encode('utf-8'))
except Exception:
    css_size_bytes = 0
css_ms = timer.end()

# ═════════════════════════════════════════════════════════════════════════════
# PHASE 6: checklist_data import
# ═════════════════════════════════════════════════════════════════════════════
timer.begin("checklist_data import")
try:
    from checklist_data import REVIEW_TYPES, get_checklist_for_review_type
    # Load the most complex checklist to measure parse time
    cl = get_checklist_for_review_type("Hillside Protection Lot")
    total_items = sum(len(s["items"]) for s in cl.values())
    checklist_imported = True
except Exception as e:
    checklist_imported = False
    total_items = 0
checklist_ms = timer.end()

# ═════════════════════════════════════════════════════════════════════════════
# PHASE 7: torch import cost
# ═════════════════════════════════════════════════════════════════════════════
timer.begin("torch import")
torch_available = False
try:
    import importlib
    import importlib.util
    spec = importlib.util.find_spec("torch")
    if spec:
        t0 = time.perf_counter()
        import torch
        torch_ms_actual = (time.perf_counter() - t0) * 1000
        torch_available = True
    else:
        torch_ms_actual = 0
except Exception:
    torch_ms_actual = 0
torch_ms = timer.end()

# Total render time
total_ms = timer.total_ms()

# Store in history
report = {
    "render": render_num,
    "timestamp": datetime.now().strftime("%H:%M:%S.%f")[:-3],
    "total_ms": round(total_ms, 1),
    "theme_import_ms": round(theme_import_ms, 1),
    "apply_theme_ms": round(apply_theme_ms, 1),
    "render_sidebar_ms": round(render_sidebar_ms, 1),
    "favicon_ms": round(favicon_ms, 1),
    "logo_ms": round(logo_ms, 1),
    "db_ms": round(db_ms, 1),
    "engine_ms": round(engine_ms, 1),
    "checklist_ms": round(checklist_ms, 1),
    "css_bytes": css_size_bytes,
    "logo_bytes": logo_len if 'logo_len' in dir() else 0,
}
st.session_state.perf_history.append(report)
# Keep last 50 renders
if len(st.session_state.perf_history) > 50:
    st.session_state.perf_history = st.session_state.perf_history[-50:]

# ═════════════════════════════════════════════════════════════════════════════
# DISPLAY
# ═════════════════════════════════════════════════════════════════════════════

st.markdown("## ⏱️ Performance Profiler")
st.caption(f"Render #{render_num} · {report['timestamp']} · Total: **{report['total_ms']:.1f} ms**")
st.markdown("---")

# ── Current render breakdown ──────────────────────────────────────────────────
st.markdown("### This Render — Phase Breakdown")

def status_icon(ms, warn=50, bad=200):
    if ms < warn:   return "🟢"
    if ms < bad:    return "🟡"
    return "🔴"

phases = [
    ("theme import",        report["theme_import_ms"],   10,  50),
    ("apply_theme() CSS",   report["apply_theme_ms"],    20, 100),
    ("render_sidebar()",    report["render_sidebar_ms"], 20, 100),
    ("get_favicon()",       report["favicon_ms"],         5,  50),
    ("_logo_b64()",         report["logo_ms"],            5,  50),
    ("load_database()",     report["db_ms"],             10, 100),
    ("get_rag_engine()",    report["engine_ms"],         10, 200),
    ("checklist_data",      report["checklist_ms"],       5,  50),
]

col1, col2 = st.columns([2, 3])
with col1:
    for phase_name, ms, warn, bad in phases:
        icon = status_icon(ms, warn, bad)
        bar_pct = min(int(ms / bad * 100), 100)
        st.markdown(
            f"{icon} **{phase_name}** — `{ms:.1f} ms`",
        )

with col2:
    total_accounted = sum(ms for _, ms, _, _ in phases)
    for phase_name, ms, warn, bad in phases:
        pct = ms / max(total_ms, 1) * 100
        color = "#16A34A" if ms < warn else "#D97706" if ms < bad else "#DC2626"
        st.markdown(
            f"<div style='display:flex;align-items:center;gap:8px;margin:4px 0'>"
            f"<div style='background:{color};width:{max(pct*3,2):.0f}px;height:16px;"
            f"border-radius:3px;min-width:2px'></div>"
            f"<span style='font-size:0.85rem;color:#555'>{pct:.0f}% of render</span>"
            f"</div>",
            unsafe_allow_html=True
        )

st.markdown("---")

# ── Payload sizes ─────────────────────────────────────────────────────────────
st.markdown("### Payload Sizes — Data Sent to Browser Per Render")
p1, p2, p3 = st.columns(3)
with p1:
    st.metric("Theme CSS (_CSS)", f"{css_size_bytes/1024:.1f} KB",
              help="Injected via st.markdown() on every single render — including checkbox ticks")
with p2:
    logo_kb = report['logo_bytes']/1024
    st.metric("Logo PNG (bytes)", f"{logo_kb:.1f} KB",
              help="Raw PNG size. Sent ONCE via st.image() — browser caches it. "
                   "No longer embedded as base64 on every render.")
with p3:
    # Only CSS is sent on every render now — logo is browser-cached after first load
    st.metric("Fixed payload/render (CSS only)", f"{css_size_bytes/1024:.1f} KB",
              delta="Logo removed from per-render payload", delta_color="normal",
              help="CSS is still injected every render. Logo is now browser-cached.")

st.markdown("---")

# ── Render history ────────────────────────────────────────────────────────────
if len(st.session_state.perf_history) > 1:
    st.markdown("### Render History")
    
    history = st.session_state.perf_history[-20:]  # last 20
    
    # Mini sparkline using markdown bars
    max_total = max(r["total_ms"] for r in history)
    
    sparkline_html = "<div style='display:flex;align-items:flex-end;gap:2px;height:60px'>"
    for r in history:
        h = max(int(r["total_ms"] / max(max_total, 1) * 55), 3)
        color = "#16A34A" if r["total_ms"] < 100 else "#D97706" if r["total_ms"] < 500 else "#DC2626"
        rn = r["render"]
        rt = r["total_ms"]
        sparkline_html += (
            f"<div title='Render {rn}: {rt}ms' "
            f"style='background:{color};width:14px;height:{h}px;"
            f"border-radius:2px 2px 0 0;cursor:help'></div>"
        )
    sparkline_html += "</div>"
    st.markdown(sparkline_html, unsafe_allow_html=True)
    st.caption("Each bar = one render. Green < 100ms · Yellow < 500ms · Red > 500ms. Hover for details.")

    # Table of last 10
    st.markdown("**Last 10 renders (ms):**")
    header = "| # | Time | Total | theme | sidebar | logo | DB | Engine |"
    divider = "|---|------|-------|-------|---------|------|----|--------|"
    rows = [header, divider]
    for r in history[-10:]:
        rows.append(
            f"| {r['render']} | {r['timestamp']} "
            f"| **{r['total_ms']}** "
            f"| {r['theme_import_ms']} "
            f"| {r['render_sidebar_ms']} "
            f"| {r['logo_ms']} "
            f"| {r['db_ms']} "
            f"| {r['engine_ms']} |"
        )
    st.markdown('\n'.join(rows))

st.markdown("---")

# ── Bottleneck analysis ───────────────────────────────────────────────────────
st.markdown("### Bottleneck Analysis")

bottlenecks = []
if report["apply_theme_ms"] > 50:
    bottlenecks.append(("apply_theme()", report["apply_theme_ms"],
        f"Injecting {css_size_bytes/1024:.1f} KB of CSS on every render. "
        "Fast V1 injects ~1.8 KB. Consider splitting CSS by page."))
if report["render_sidebar_ms"] > 50:
    bottlenecks.append(("render_sidebar()", report["render_sidebar_ms"],
        "7 st.markdown() calls + logo injection on every render. "
        "Fast V1 uses st.sidebar.markdown() which is lighter."))
if report["logo_ms"] > 20:
    bottlenecks.append(("_logo_b64()", report["logo_ms"],
        "Logo PNG encoding not cached yet. Should be instant after first render."))
if report["db_ms"] > 100:
    bottlenecks.append(("load_database()", report["db_ms"],
        "Database path check taking too long. "
        "Should be instant via @st.cache_resource. May indicate cache miss."))
if report["engine_ms"] > 200:
    bottlenecks.append(("get_rag_engine()", report["engine_ms"],
        "RAG engine cache miss — model may be reinitializing. "
        "Should be instant after cold start."))
if css_size_bytes > 8000:
    bottlenecks.append(("CSS payload", css_size_bytes/1024,
        f"{css_size_bytes/1024:.1f} KB CSS injected on every render. "
        "Wizard only uses 3 of 24 defined CSS classes. "
        "Strip unused classes to reduce payload."))

if bottlenecks:
    for name, value, desc in bottlenecks:
        st.warning(f"**🔴 {name}** — {desc}")
else:
    st.success("✅ No significant bottlenecks detected in this render.")

st.markdown("---")

# ── Cache state inspection ────────────────────────────────────────────────────
st.markdown("### Cache State")
c1, c2, c3 = st.columns(3)
with c1:
    logo_cached = theme_imported and bool(_LOGO_CACHE) if theme_imported else False
    st.metric("Logo cache", "HIT ✅" if logo_cached else "MISS ⚠️",
              help="_LOGO_CACHE populated — logo won't be re-encoded this render")
with c2:
    st.metric("DB cache", "HIT ✅" if report["db_ms"] < 5 else "MISS ⚠️",
              help="load_database() @st.cache_resource — should be <5ms after first call")
with c3:
    st.metric("Engine cache", "HIT ✅" if report["engine_ms"] < 50 else "MISS/INIT ⚠️",
              help="get_rag_engine() @st.cache_resource — should be <50ms after init")

st.markdown("---")

# ── Controls ──────────────────────────────────────────────────────────────────
st.markdown("### Controls")
col_a, col_b, col_c = st.columns(3)
with col_a:
    if st.button("🔄 Trigger Rerender", use_container_width=True,
                 help="Click to force a rerender and measure it"):
        st.rerun()
with col_b:
    if st.button("🗑️ Clear History", use_container_width=True):
        st.session_state.perf_history = []
        st.session_state.render_count = 0
        st.rerun()
with col_c:
    if st.button("🏠 Back to Dashboard", use_container_width=True):
        st.switch_page("app.py")

st.markdown("---")
st.caption(
    "Thresholds: 🟢 fast (< warn) · 🟡 acceptable (< bad) · 🔴 slow (> bad). "
    "Times are wall-clock ms measured server-side. Network RTT to your browser is additional."
)
