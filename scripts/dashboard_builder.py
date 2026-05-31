"""
dashboard_builder.py — GSBB BO Control Tower  (Phase 2 — Multi-tab KPI Dashboard)
Reads  : logs/kpi_output.json  (output of kpi_calculator.py)
         logs/dqg_results.json (for DQG status footer)
Outputs: docs/index.html       (self-contained, CSS-only tabs, no CDN)

Tab structure:
  t0  BO Tổng quan
  t1  P&C / OTIF / Plan-DO
  t2  Sản Xuất
  t3  Chất Lượng / CoQ
  t4  Thiết Bị / CMMS
  t5  Kho / Flow
  t6  Kỹ Thuật / SPM
  t7  Action / Escalation
  t8  DQG Status (data governance footer-tab)
"""

import json
import os
from datetime import datetime

# Repo root = parent of scripts/ directory
# Works whether called as: python scripts/dashboard_builder.py  (from repo root)
#                       or: python dashboard_builder.py          (from scripts/)
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT  = os.path.dirname(_SCRIPT_DIR)   # go up from scripts/ to repo root

LOGS_DIR    = os.path.join(_REPO_ROOT, "logs")
KPI_FILE    = os.path.join(LOGS_DIR, "kpi_output.json")
DQG_FILE    = os.path.join(LOGS_DIR, "dqg_results.json")
OUTPUT_DIR  = os.path.join(_REPO_ROOT, "docs")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "index.html")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ─────────────────────────────────────────────────────────────
# RAG helpers
# ─────────────────────────────────────────────────────────────

def rag_color(val, green_min=None, amber_min=None, reverse=False):
    """Return hex color for a KPI value. reverse=True → low is good."""
    if val is None:
        return "#94a3b8"
    if not reverse:
        if green_min is not None and val >= green_min:
            return "#22c55e"
        if amber_min is not None and val >= amber_min:
            return "#f59e0b"
        return "#ef4444"
    else:  # lower is better (e.g. downtime, overdue)
        if green_min is not None and val <= green_min:
            return "#22c55e"
        if amber_min is not None and val <= amber_min:
            return "#f59e0b"
        return "#ef4444"


def kpi_card(label, value, unit="", color="#3b82f6", sublabel=""):
    v = f"{value}{unit}" if value is not None else "N/A"
    return f"""
    <div class="kcard" style="border-top:4px solid {color}">
      <div class="knum" style="color:{color}">{v}</div>
      <div class="klbl">{label}</div>
      {"<div class='ksub'>" + sublabel + "</div>" if sublabel else ""}
    </div>"""


def section_title(text):
    return f'<div class="stitle">{text}</div>'


def badge(text, color="#22c55e", bg="#f0fdf4"):
    return f'<span style="background:{bg};color:{color};padding:2px 10px;border-radius:12px;font-size:12px;font-weight:700">{text}</span>'


def table_row(*cells, header=False):
    tag = "th" if header else "td"
    cols = "".join(f"<{tag}>{c}</{tag}>" for c in cells)
    return f"<tr>{cols}</tr>"


def mini_table(headers, rows, empty_msg="Không có dữ liệu"):
    if not rows:
        return f'<p style="color:#94a3b8;font-size:13px;margin:8px 0">{empty_msg}</p>'
    head = table_row(*headers, header=True)
    body = "".join(table_row(*r) for r in rows)
    return f'<table class="mtable"><thead>{head}</thead><tbody>{body}</tbody></table>'


# ─────────────────────────────────────────────────────────────
# Tab content builders
# ─────────────────────────────────────────────────────────────

def build_tab_overview(kpi_data, build_time):
    """t0 — BO Tổng quan: health heatmap + key numbers from all modules."""
    modules = [
        ("01_SAN_XUAT",      "🏭", "Sản Xuất",    "Plan/DO%"),
        ("02_KHSX_OTIF",     "📦", "KHSX/OTIF",   "OTIF%"),
        ("03_QLCL",          "🔍", "Chất Lượng",  "NCR Open"),
        ("04_QLTB_CD",       "⚙️",  "Thiết Bị",   "Downtime (h)"),
        ("05_KHO",           "🗄️",  "Kho/WIP",    "WIP Qty"),
        ("06_GSTT",          "✅", "GSTT",         "Issues Open"),
        ("07_CONG_NGHE_SPM", "🧪", "Kỹ Thuật",    "Samples Active"),
        ("08_BO_CONTROL",    "🚨", "BO Control",   "Issues Open"),
    ]

    heatmap = '<div class="heatmap">'
    for dept, icon, name, metric in modules:
        d      = kpi_data.get(dept, {})
        dqg_st = d.get("dqg_status", "SKIP")
        kpis   = d.get("kpis") or {}
        official = d.get("official", False)

        if dqg_st == "PASS":
            bg    = "#dcfce7"; border = "#22c55e"; status_text = "PASS"
        elif dqg_st == "WARN":
            bg    = "#fffbeb"; border = "#f59e0b"; status_text = "WARN"
        elif dqg_st == "PENDING":
            bg    = "#f8fafc"; border = "#cbd5e1"; status_text = "PENDING"
        else:
            bg    = "#fef2f2"; border = "#ef4444"; status_text = dqg_st

        # Pick headline KPI
        if dept == "01_SAN_XUAT":
            val = f"{kpis.get('plan_do_pct_avg', 'N/A')}%" if kpis.get('plan_do_pct_avg') is not None else "N/A"
        elif dept == "02_KHSX_OTIF":
            val = f"{kpis.get('otif_pct', 'N/A')}%" if kpis.get('otif_pct') is not None else "—"
        elif dept == "03_QLCL":
            val = str(kpis.get("open", "N/A"))
        elif dept == "04_QLTB_CD":
            val = f"{kpis.get('total_downtime_hrs', 'N/A')}h" if kpis else "N/A"
        elif dept == "05_KHO":
            val = str(int(kpis.get("total_wip_qty", 0))) if kpis else "N/A"
        elif dept == "06_GSTT":
            val = str(kpis.get("open", "N/A"))
        elif dept == "07_CONG_NGHE_SPM":
            val = str(kpis.get("in_progress", "N/A"))
        elif dept == "08_BO_CONTROL":
            val = str(kpis.get("open", "N/A"))
        else:
            val = "N/A"

        heatmap += f"""
        <div class="hcell" style="background:{bg};border:2px solid {border}">
          <div class="hicon">{icon}</div>
          <div class="hname">{name}</div>
          <div class="hval" style="color:{border}">{val}</div>
          <div class="hmetric">{metric}</div>
          <div class="hstatus" style="color:{border}">{status_text}</div>
        </div>"""
    heatmap += "</div>"

    # Quick stats row
    d_sx   = kpi_data.get("01_SAN_XUAT", {}).get("kpis") or {}
    d_qlcl = kpi_data.get("03_QLCL",     {}).get("kpis") or {}
    d_tb   = kpi_data.get("04_QLTB_CD",  {}).get("kpis") or {}
    d_bo   = kpi_data.get("08_BO_CONTROL",{}).get("kpis") or {}

    quick = '<div class="qrow">'
    quick += kpi_card("Plan/DO% Trung bình", d_sx.get("plan_do_pct_avg"), "%",
                      rag_color(d_sx.get("plan_do_pct_avg"), 90, 80), "Sản xuất")
    quick += kpi_card("NCR Đang mở", d_qlcl.get("open"), "",
                      rag_color(d_qlcl.get("open", 0), 0, 2, reverse=True), "Chất lượng")
    quick += kpi_card("Downtime", d_tb.get("total_downtime_hrs"), "h",
                      rag_color(d_tb.get("total_downtime_hrs", 0), 0, 4, reverse=True), "Thiết bị")
    quick += kpi_card("Issues Overdue", d_bo.get("overdue"), "",
                      rag_color(d_bo.get("overdue", 0), 0, 1, reverse=True), "BO Control")
    quick += '</div>'

    return f"""
    {section_title("🏭 Factory Health Heatmap — Tổng quan 8 bộ phận")}
    {heatmap}
    {section_title("📊 KPI Chốt nhanh")}
    {quick}
    <div style="font-size:11px;color:#94a3b8;margin-top:16px">
      Cập nhật: {build_time} &nbsp;|&nbsp;
      Chỉ hiển thị KPI từ nguồn đạt DQG (Data Quality Gate PASS)
    </div>"""


def build_tab_plan_do(kpi_data):
    """t1 — P&C / OTIF / Plan-DO."""
    sx   = kpi_data.get("01_SAN_XUAT", {}).get("kpis") or {}
    otif = kpi_data.get("02_KHSX_OTIF", {})
    otif_kpis = otif.get("kpis") or {}

    html = section_title("📋 Plan / DO — Sản Xuất")
    html += '<div class="qrow">'
    html += kpi_card("Plan_Qty", sx.get("total_plan_qty"), "", "#3b82f6", "Tổng kế hoạch")
    html += kpi_card("Actual_Qty", sx.get("total_actual_qty"), "", "#22c55e", "Thực tế")
    html += kpi_card("NG_Qty", sx.get("total_ng_qty"), "", "#ef4444", "Lỗi/NG")
    html += kpi_card("Plan/DO%", sx.get("plan_do_pct_avg"), "%",
                     rag_color(sx.get("plan_do_pct_avg"), 90, 80), "Trung bình")
    html += kpi_card("NG Rate", sx.get("ng_pct"), "%",
                     rag_color(sx.get("ng_pct", 0), 0, 2, reverse=True), "Tỷ lệ lỗi")
    html += '</div>'

    # RAG table
    rag_r = sx.get("rag_R", 0)
    rag_a = sx.get("rag_A", 0)
    rag_g = sx.get("rag_G", 0)
    total_rag = rag_r + rag_a + rag_g or 1
    html += section_title("🚦 Phân bổ RAG (Work Orders)")
    html += mini_table(
        ["Màu", "Số WO", "Tỷ lệ"],
        [
            [f'<span style="color:#ef4444;font-weight:700">🔴 RED</span>',  str(rag_r), f"{rag_r/total_rag*100:.0f}%"],
            [f'<span style="color:#f59e0b;font-weight:700">🟡 AMBER</span>', str(rag_a), f"{rag_a/total_rag*100:.0f}%"],
            [f'<span style="color:#22c55e;font-weight:700">🟢 GREEN</span>', str(rag_g), f"{rag_g/total_rag*100:.0f}%"],
        ]
    )

    html += section_title("📦 OTIF — Delivery")
    if otif.get("dqg_status") == "PASS" and otif_kpis.get("row_count", 0) > 0:
        html += '<div class="qrow">'
        html += kpi_card("OTIF%", otif_kpis.get("otif_pct"), "%",
                         rag_color(otif_kpis.get("otif_pct"), 95, 90), "On-Time In-Full")
        html += kpi_card("On Time", otif_kpis.get("on_time"), "", "#22c55e")
        html += kpi_card("Late", otif_kpis.get("late"), "", "#ef4444")
        html += '</div>'
    else:
        note = otif.get("note", "Sheet ID chưa được cấu hình — liên hệ Mr Hưng / KHSX")
        html += f'<div class="pending-box">⏳ OTIF data đang chờ: {note}</div>'

    return html


def build_tab_san_xuat(kpi_data):
    """t2 — Sản Xuất (detail)."""
    d = kpi_data.get("01_SAN_XUAT", {}).get("kpis") or {}
    html = section_title("🏭 Sản Xuất — Plan/DO Chi tiết")
    html += '<div class="qrow">'
    html += kpi_card("Plan Qty", d.get("total_plan_qty"), "", "#3b82f6")
    html += kpi_card("Actual Qty", d.get("total_actual_qty"), "", "#22c55e")
    html += kpi_card("NG Qty", d.get("total_ng_qty"), "", "#ef4444")
    html += kpi_card("Plan/DO%", d.get("plan_do_pct_avg"), "%",
                     rag_color(d.get("plan_do_pct_avg"), 90, 80))
    html += kpi_card("NG%", d.get("ng_pct"), "%",
                     rag_color(d.get("ng_pct", 0), 0, 2, reverse=True))
    html += '</div>'
    html += section_title("🚦 RAG Distribution")
    r, a, g = d.get("rag_R", 0), d.get("rag_A", 0), d.get("rag_G", 0)
    total = r + a + g or 1
    html += f"""
    <div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:16px">
      <div class="rag-box" style="background:#fef2f2;border:2px solid #ef4444">
        <div style="font-size:24px;font-weight:800;color:#ef4444">{r}</div>
        <div>🔴 RED</div><div style="font-size:11px;color:#94a3b8">{r/total*100:.0f}%</div>
      </div>
      <div class="rag-box" style="background:#fffbeb;border:2px solid #f59e0b">
        <div style="font-size:24px;font-weight:800;color:#f59e0b">{a}</div>
        <div>🟡 AMBER</div><div style="font-size:11px;color:#94a3b8">{a/total*100:.0f}%</div>
      </div>
      <div class="rag-box" style="background:#f0fdf4;border:2px solid #22c55e">
        <div style="font-size:24px;font-weight:800;color:#22c55e">{g}</div>
        <div>🟢 GREEN</div><div style="font-size:11px;color:#94a3b8">{g/total*100:.0f}%</div>
      </div>
    </div>"""
    rows_count = d.get("row_count", 0)
    html += f'<p style="font-size:12px;color:#64748b">Tổng Work Orders phân tích: {rows_count}</p>'
    return html


def build_tab_chat_luong(kpi_data):
    """t3 — Chất Lượng / CoQ."""
    d = kpi_data.get("03_QLCL", {}).get("kpis") or {}
    html = section_title("🔍 Chất Lượng — NCR / CAR")
    html += '<div class="qrow">'
    html += kpi_card("Tổng NCR", d.get("total_ncr"), "", "#6366f1", "Toàn bộ")
    html += kpi_card("Đang mở", d.get("open"), "",
                     rag_color(d.get("open", 0), 0, 2, reverse=True), "Open")
    html += kpi_card("Đã đóng", d.get("closed"), "", "#22c55e", "Closed")
    html += kpi_card("Quá hạn", d.get("overdue_count"), "",
                     rag_color(d.get("overdue_count", 0), 0, 1, reverse=True), "Overdue")
    html += kpi_card("COPQ ước tính", d.get("copq_estimated"), "",
                     "#ef4444" if (d.get("copq_estimated") or 0) > 0 else "#22c55e",
                     "VNĐ hoặc USD")
    html += '</div>'

    html += section_title("⚠️ Phân loại Severity")
    html += mini_table(
        ["Mức độ", "Số lượng"],
        [
            ["🔴 Critical", str(d.get("severity_critical", 0))],
            ["🟡 Major",    str(d.get("severity_major", 0))],
            ["🟢 Minor",    str(d.get("severity_minor", 0))],
        ]
    )
    return html


def build_tab_thiet_bi(kpi_data):
    """t4 — Thiết Bị / CMMS."""
    d = kpi_data.get("04_QLTB_CD", {}).get("kpis") or {}
    html = section_title("⚙️ Thiết Bị — Machine Downtime")
    html += '<div class="qrow">'
    html += kpi_card("Tổng Downtime", d.get("total_downtime_min"), " min",
                     rag_color(d.get("total_downtime_min", 0), 0, 120, reverse=True), "Tổng")
    html += kpi_card("Downtime (giờ)", d.get("total_downtime_hrs"), "h",
                     rag_color(d.get("total_downtime_hrs", 0), 0, 2, reverse=True))
    html += kpi_card("Sự cố (Breakdown)", d.get("breakdown_events"), "",
                     rag_color(d.get("breakdown_events", 0), 0, 1, reverse=True), "events")
    html += kpi_card("PM thực hiện", d.get("pm_events"), "", "#22c55e", "Bảo trì phòng ngừa")
    html += '</div>'

    top = d.get("top_machines", [])
    if top:
        html += section_title("📊 Top máy theo downtime")
        html += mini_table(
            ["Máy", "Downtime (min)"],
            [[m["machine"], str(m["downtime_min"])] for m in top]
        )
    return html


def build_tab_kho(kpi_data):
    """t5 — Kho / WIP / FIFO."""
    d = kpi_data.get("05_KHO", {}).get("kpis") or {}
    html = section_title("🗄️ Kho — WIP / FIFO / Age Control")
    html += '<div class="qrow">'
    html += kpi_card("Tổng WIP", d.get("total_wip_qty"), "",
                     "#3b82f6", "Bán thành phẩm")
    html += kpi_card("FIFO OK", d.get("fifo_ok"), "", "#22c55e")
    html += kpi_card("FIFO Risk", d.get("fifo_risk"), "",
                     rag_color(d.get("fifo_risk", 0), 0, 1, reverse=True))
    html += kpi_card("FIFO Breach", d.get("fifo_breach"), "",
                     "#ef4444" if d.get("fifo_breach", 0) > 0 else "#22c55e")
    html += kpi_card("Age TB (ngày)", d.get("age_days_avg"), "",
                     rag_color(d.get("age_days_avg", 0), 0, 3, reverse=True))
    html += '</div>'

    html += section_title("🚨 Rủi ro tồn kho")
    html += mini_table(
        ["Mức rủi ro", "Số lô"],
        [
            ["🔴 High",   str(d.get("risk_high", 0))],
            ["🟡 Medium", str(d.get("risk_medium", 0))],
            ["🟢 Low",    str(d.get("risk_low", 0))],
        ]
    )
    wos = d.get("high_risk_wos", [])
    if wos:
        html += f'<p style="font-size:12px;color:#ef4444;margin-top:8px">⚠️ Work Orders rủi ro cao: {", ".join(wos)}</p>'
    return html


def build_tab_ky_thuat(kpi_data):
    """t6 — Kỹ Thuật / SPM Technology."""
    d = kpi_data.get("07_CONG_NGHE_SPM", {}).get("kpis") or {}
    html = section_title("🧪 Kỹ Thuật Công Nghệ — SPM")
    html += '<div class="qrow">'
    html += kpi_card("Tổng mẫu", d.get("total_samples"), "", "#6366f1")
    html += kpi_card("Đang xử lý", d.get("in_progress"), "",
                     "#f59e0b" if (d.get("in_progress") or 0) > 0 else "#22c55e")
    html += kpi_card("Hoàn thành", d.get("completed"), "", "#22c55e")
    html += kpi_card("Lead time TB", d.get("leadtime_avg_days"), " ngày",
                     rag_color(d.get("leadtime_avg_days", 0), 0, 5, reverse=True))
    html += kpi_card("Redo Count", d.get("redo_count_total"), "",
                     rag_color(d.get("redo_count_total", 0), 0, 1, reverse=True), "Số lần làm lại")
    html += kpi_card("Risk High", d.get("risk_high"), "",
                     "#ef4444" if (d.get("risk_high") or 0) > 0 else "#22c55e")
    html += '</div>'

    gstt = kpi_data.get("06_GSTT", {}).get("kpis") or {}
    html += section_title("✅ GSTT — Field Verification")
    html += '<div class="qrow">'
    html += kpi_card("Tổng issues", gstt.get("total_issues"), "", "#6366f1")
    html += kpi_card("Đang mở", gstt.get("open"), "",
                     rag_color(gstt.get("open", 0), 0, 2, reverse=True))
    html += kpi_card("Đã đóng", gstt.get("closed"), "", "#22c55e")
    html += kpi_card("Escalated", gstt.get("escalated"), "",
                     "#ef4444" if (gstt.get("escalated") or 0) > 0 else "#22c55e")
    html += '</div>'
    return html


def build_tab_action(kpi_data):
    """t7 — Action / Escalation (BO Control)."""
    d = kpi_data.get("08_BO_CONTROL", {}).get("kpis") or {}
    html = section_title("🚨 BO Control — Issue / Action / Escalation")
    html += '<div class="qrow">'
    html += kpi_card("Tổng Issues", d.get("total_issues"), "", "#6366f1")
    html += kpi_card("Đang mở", d.get("open"), "",
                     rag_color(d.get("open", 0), 0, 2, reverse=True))
    html += kpi_card("Đã đóng", d.get("closed"), "", "#22c55e")
    html += kpi_card("Quá hạn", d.get("overdue"), "",
                     rag_color(d.get("overdue", 0), 0, 1, reverse=True))
    html += kpi_card("Đã escalate", d.get("escalated"), "",
                     "#ef4444" if (d.get("escalated") or 0) > 0 else "#22c55e")
    html += '</div>'

    html += section_title("⚠️ Severity Issues")
    html += mini_table(
        ["Mức độ", "Số lượng"],
        [
            ["🔴 Critical", str(d.get("severity_critical", 0))],
            ["🟠 High",     str(d.get("severity_high", 0))],
            ["🟡 Medium",   str(d.get("severity_medium", 0))],
        ]
    )

    # GSTT issues that need escalation
    gstt = kpi_data.get("06_GSTT", {}).get("kpis") or {}
    if gstt.get("escalated", 0) > 0:
        html += f"""
        <div style="background:#fef2f2;border-left:4px solid #ef4444;padding:12px;
                    border-radius:6px;margin-top:16px">
          <strong style="color:#ef4444">⚠️ GSTT Escalation cần xử lý:</strong>
          {gstt["escalated"]} vấn đề đã được escalate từ GSTT Field Verification
        </div>"""
    return html


def build_tab_dqg(dqg_data, kpi_data, build_time):
    """t8 — DQG Status (data governance)."""
    departments = dqg_data.get("departments", {})
    STATUS_COLOR = {
        "PASS": ("#22c55e", "#f0fdf4"),
        "WARN": ("#f59e0b", "#fffbeb"),
        "FAIL": ("#ef4444", "#fef2f2"),
        "SKIP": ("#64748b", "#f8fafc"),
    }
    STATUS_ICON = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌", "SKIP": "⏳"}

    html = section_title("🔒 Data Quality Gate — Trạng thái nguồn dữ liệu")
    summary = dqg_data.get("summary", {})
    html += '<div class="qrow">'
    html += kpi_card("PASS", summary.get("PASS", 0), "", "#22c55e")
    html += kpi_card("WARN", summary.get("WARN", 0), "", "#f59e0b")
    html += kpi_card("FAIL", summary.get("FAIL", 0), "", "#ef4444")
    html += kpi_card("SKIP", summary.get("SKIP", 0), "", "#64748b")
    html += '</div>'

    for dept_key, res in departments.items():
        s = res.get("dqg_status", "SKIP")
        color, bg = STATUS_COLOR.get(s, ("#64748b", "#f8fafc"))
        icon = STATUS_ICON.get(s, "?")
        issues = res.get("issues", [])
        issues_html = ""
        if issues:
            lis = "".join(f"<li style='font-size:11px;color:#475569'>{i}</li>" for i in issues[:3])
            issues_html = f"<ul style='margin:6px 0 0 16px'>{lis}</ul>"

        html += f"""
        <div style="border:1px solid {color};border-left:5px solid {color};
                    background:{bg};border-radius:8px;padding:12px 14px;margin-bottom:8px">
          <div style="display:flex;justify-content:space-between;align-items:center">
            <span style="font-weight:600;font-size:13px">{icon} {res.get("description", dept_key)}</span>
            <span style="background:{color};color:#fff;padding:1px 8px;border-radius:20px;font-size:11px;font-weight:700">{s}</span>
          </div>
          <div style="font-size:11px;color:#94a3b8;margin-top:3px">
            Rows: {res.get("row_count", 0)} &nbsp;|&nbsp; Failures: {res.get("fail_count", 0)}
          </div>
          {issues_html}
        </div>"""

    html += f'<p style="font-size:11px;color:#94a3b8;margin-top:12px">DQG Run: {dqg_data.get("generated_at","N/A")[:16].replace("T"," ")} UTC &nbsp;|&nbsp; Build: {build_time}</p>'
    return html


# ─────────────────────────────────────────────────────────────
# Full HTML assembler
# ─────────────────────────────────────────────────────────────

def build_html(kpi_full, dqg_data, build_time):
    # kpi_full = full kpi_output.json dict (has "summary" + "departments")
    # kpi_data = departments dict passed to tab builders
    kpi_data    = kpi_full.get("departments", kpi_full)
    kpi_summary = kpi_full.get("summary", {})

    tabs = [
        ("t0", "🏠 Tổng quan",    build_tab_overview(kpi_data, build_time)),
        ("t1", "📋 Plan/OTIF",    build_tab_plan_do(kpi_data)),
        ("t2", "🏭 Sản Xuất",     build_tab_san_xuat(kpi_data)),
        ("t3", "🔍 Chất Lượng",   build_tab_chat_luong(kpi_data)),
        ("t4", "⚙️ Thiết Bị",     build_tab_thiet_bi(kpi_data)),
        ("t5", "🗄️ Kho/WIP",      build_tab_kho(kpi_data)),
        ("t6", "🧪 Kỹ Thuật",     build_tab_ky_thuat(kpi_data)),
        ("t7", "🚨 Action",        build_tab_action(kpi_data)),
        ("t8", "🔒 DQG Status",   build_tab_dqg(dqg_data, kpi_data, build_time)),
    ]

    # CSS-only radio-tab mechanism (no JS)
    radio_inputs = ""
    radio_labels = ""
    tab_contents = ""

    for i, (tid, label, content) in enumerate(tabs):
        checked = "checked" if i == 0 else ""
        radio_inputs += f'<input type="radio" name="tab" id="{tid}" {checked} style="display:none">\n'
        radio_labels  += f'<label for="{tid}" class="tlabel">{label}</label>\n'
        tab_contents  += f'<div class="tcontent" id="tc_{tid}">{content}</div>\n'

    # Dynamic CSS for active tab (CSS-only)
    tab_css = ""
    for i, (tid, _, _) in enumerate(tabs):
        tab_css += f"#{tid}:checked ~ .tbar label[for='{tid}'] {{ background:#3b82f6;color:#fff;border-color:#3b82f6; }}\n"
        tab_css += f"#{tid}:checked ~ .tabs #tc_{tid} {{ display:block; }}\n"

    # Overall health indicator (use kpi_summary extracted above)
    official = kpi_summary.get("kpi_official", 0)
    total    = kpi_summary.get("total_depts", 8)
    if official == total:
        overall_color = "#22c55e"; overall_label = "OPERATIONAL"
    elif official >= total - 1:
        overall_color = "#f59e0b"; overall_label = "NEAR OPERATIONAL"
    else:
        overall_color = "#ef4444"; overall_label = "PARTIAL DATA"

    return f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>BO Control Tower – GSBB</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
       background:#f1f5f9;color:#1e293b;font-size:14px}}
  .wrap{{max-width:960px;margin:0 auto;padding:12px}}
  .header{{background:linear-gradient(135deg,#1e293b 0%,#334155 100%);
           color:#fff;padding:16px 20px;border-radius:10px;margin-bottom:12px}}
  .header h1{{font-size:18px;font-weight:700}}
  .header .sub{{font-size:12px;color:#94a3b8;margin-top:3px}}
  .overall{{text-align:center;padding:12px;border-radius:8px;margin-bottom:12px;
            background:#fff;border:2px solid {overall_color}}}
  .overall .lbl{{font-size:20px;font-weight:800;color:{overall_color}}}
  .overall .sub{{font-size:12px;color:#64748b;margin-top:2px}}
  /* Tabs */
  .tbar{{display:flex;flex-wrap:wrap;gap:4px;margin-bottom:0;background:#e2e8f0;
         padding:6px;border-radius:8px 8px 0 0}}
  .tlabel{{padding:7px 12px;border-radius:6px;cursor:pointer;font-size:12px;font-weight:600;
           border:1px solid transparent;color:#64748b;transition:.15s}}
  .tlabel:hover{{background:#cbd5e1}}
  .tabs{{background:#fff;border-radius:0 0 8px 8px;padding:16px;
         box-shadow:0 1px 4px rgba(0,0,0,.08)}}
  .tcontent{{display:none}}
  {tab_css}
  /* KPI cards */
  .qrow{{display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));
         gap:10px;margin-bottom:16px}}
  .kcard{{background:#f8fafc;border-radius:8px;padding:12px;text-align:center;
          border:1px solid #e2e8f0}}
  .knum{{font-size:24px;font-weight:800}}
  .klbl{{font-size:11px;color:#64748b;margin-top:2px;line-height:1.3}}
  .ksub{{font-size:10px;color:#94a3b8;margin-top:1px}}
  /* Section title */
  .stitle{{font-size:14px;font-weight:700;color:#334155;
           border-left:4px solid #3b82f6;padding-left:10px;
           margin:16px 0 10px}}
  /* Heatmap */
  .heatmap{{display:grid;grid-template-columns:repeat(auto-fill,minmax(110px,1fr));
            gap:8px;margin-bottom:16px}}
  .hcell{{border-radius:8px;padding:10px;text-align:center}}
  .hicon{{font-size:20px}}
  .hname{{font-size:11px;font-weight:600;color:#334155;margin-top:4px}}
  .hval{{font-size:20px;font-weight:800;margin-top:4px}}
  .hmetric{{font-size:10px;color:#94a3b8}}
  .hstatus{{font-size:10px;font-weight:700;margin-top:2px}}
  /* RAG boxes */
  .rag-box{{padding:12px 20px;border-radius:8px;text-align:center;font-size:13px;font-weight:600}}
  /* Table */
  .mtable{{width:100%;border-collapse:collapse;font-size:12px;margin-bottom:12px}}
  .mtable th{{background:#f1f5f9;padding:7px 10px;text-align:left;font-weight:600;color:#475569}}
  .mtable td{{padding:6px 10px;border-bottom:1px solid #f1f5f9;color:#334155}}
  .mtable tr:hover td{{background:#f8fafc}}
  /* Pending box */
  .pending-box{{background:#f8fafc;border:1px dashed #94a3b8;border-radius:6px;
                padding:12px;font-size:12px;color:#64748b;margin-bottom:12px}}
  .footer{{text-align:center;font-size:11px;color:#94a3b8;margin-top:16px;padding:8px}}
  @media(max-width:600px){{
    .qrow{{grid-template-columns:repeat(2,1fr)}}
    .heatmap{{grid-template-columns:repeat(2,1fr)}}
    .tlabel{{font-size:11px;padding:6px 8px}}
  }}
</style>
</head>
<body>
<div class="wrap">

  <div class="header">
    <h1>🏭 BO Control Tower – GSBB</h1>
    <div class="sub">
      KPI Dashboard &nbsp;|&nbsp; Cập nhật: {build_time} &nbsp;|&nbsp;
      Nguồn: Google Sheets → DQG → KPI &nbsp;|&nbsp;
      Auto-build: GitHub Actions
    </div>
  </div>

  <div class="overall">
    <div class="lbl">{overall_label}</div>
    <div class="sub">KPI chính thức: {official}/{total} bộ phận đạt DQG</div>
  </div>

  {radio_inputs}
  <div class="tbar">{radio_labels}</div>
  <div class="tabs">{tab_contents}</div>

  <div class="footer">
    GSBB BO Control Tower &nbsp;·&nbsp; Auto-built by GitHub Actions
    &nbsp;·&nbsp; Dữ liệu: Google Sheets &nbsp;·&nbsp; {build_time}
  </div>

</div>
</body>
</html>"""


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────

def main():
    print("=== BO Control Tower – Dashboard Builder (Phase 2 – Multi-tab KPI) ===")

    build_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    # Load KPI output
    if not os.path.exists(KPI_FILE):
        print(f"⚠  {KPI_FILE} not found — building placeholder page")
        kpi_data = {"summary": {}, "departments": {}}
    else:
        with open(KPI_FILE, encoding="utf-8") as f:
            kpi_data = json.load(f)

    # Load DQG results (for DQG tab)
    if not os.path.exists(DQG_FILE):
        dqg_data = {"summary": {}, "departments": {}}
    else:
        with open(DQG_FILE, encoding="utf-8") as f:
            dqg_data = json.load(f)

    html = build_html(kpi_data, dqg_data, build_time)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"✅ Dashboard built → {OUTPUT_FILE}  ({len(html):,} chars)")
    print(f"   Tabs: BO Tổng quan | Plan/OTIF | Sản Xuất | Chất Lượng | Thiết Bị | Kho/WIP | Kỹ Thuật | Action | DQG")


if __name__ == "__main__":
    main()
