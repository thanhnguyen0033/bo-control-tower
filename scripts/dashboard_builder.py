"""
dashboard_builder.py — GSBB BO Control Tower  (V36 Rebuild)
Reads  : logs/kpi_output.json  + logs/dqg_results.json
Outputs: docs/index.html

Tab structure (mirrors V36):
  t1  Tổng BO        — Factory Health Heatmap + Executive KPI + Customer Risk + Inventory + GSTT
  t2  GSHN / GS1     — Mini Control Tower GS1
  t3  GSQV / GS5     — Mini Control Tower GS5
  t4  GSQV / GS6     — Mini Control Tower GS6
  t5  KPI / PIC      — Owner/PIC Performance + BO Lead Governance
  t6  GSTT           — Compliance / Independent Verification
"""

import json
import os
from datetime import datetime

# ─────────────────────────────────────────────────────────────
# Config — cập nhật khi PIC nhập đủ data
# ─────────────────────────────────────────────────────────────
EXPECTED_DATE      = "15/06"        # Session 15: next milestone GS5/GS6 real data
EXPECTED_DATE_FULL = "15/06/2026"   # Dùng trong ghi chú / báo cáo
PEND_TXT           = f"Chờ DQG · {EXPECTED_DATE}"  # Text thay thế PEND_TXT

# ─────────────────────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────────────────────
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT  = os.path.dirname(_SCRIPT_DIR)
LOGS_DIR    = os.path.join(_REPO_ROOT, "logs")
KPI_FILE    = os.path.join(LOGS_DIR, "kpi_output.json")
DQG_FILE    = os.path.join(LOGS_DIR, "dqg_results.json")
OUTPUT_DIR  = os.path.join(_REPO_ROOT, "docs")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "index.html")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ─────────────────────────────────────────────────────────────
# Data helpers
# ─────────────────────────────────────────────────────────────

def get(d, *keys, default=None):
    """Safe nested dict access."""
    for k in keys:
        if not isinstance(d, dict):
            return default
        d = d.get(k, default)
        if d is None:
            return default
    return d


def fmt(val, unit="", decimals=1, default="N/A"):
    """Format a number for display."""
    if val is None:
        return default
    try:
        v = float(val)
        if decimals == 0:
            return f"{int(v)}{unit}"
        return f"{v:.{decimals}f}{unit}"
    except (TypeError, ValueError):
        return str(val)


def rag_color(val, g_min=None, a_min=None, reverse=False):
    """Return CSS class for RAG. reverse=True → lower is better."""
    if val is None:
        return "rag-gray"
    try:
        v = float(val)
    except (TypeError, ValueError):
        return "rag-gray"
    if not reverse:
        if g_min is not None and v >= g_min:
            return "rag-green"
        if a_min is not None and v >= a_min:
            return "rag-amber"
        return "rag-red"
    else:
        if g_min is not None and v <= g_min:
            return "rag-green"
        if a_min is not None and v <= a_min:
            return "rag-amber"
        return "rag-red"


def pending_or(val, unit="", decimals=1):
    """Return formatted value or expected-date placeholder if None."""
    if val is None:
        return f"Chờ DQG · {EXPECTED_DATE}"
    return fmt(val, unit, decimals)


# ─────────────────────────────────────────────────────────────
# HTML component helpers
# ─────────────────────────────────────────────────────────────

def kpi_card(label, value_html, sublabel="", rag="rag-blue", drill_html=""):
    drill = f'<details class="drill"><summary>Xem chi tiết</summary><div class="drill-body">{drill_html}</div></details>' if drill_html else ""
    return f"""
    <div class="kpi-card {rag}">
      <div class="kpi-val">{value_html}</div>
      <div class="kpi-lbl">{label}</div>
      {"<div class='kpi-sub'>" + sublabel + "</div>" if sublabel else ""}
      {drill}
    </div>"""


def rag_badge(text, rag="rpend"):
    colors = {
        "rred":   ("#fef2f2","#dc2626"),
        "ryel":   ("#fffbeb","#d97706"),
        "rgreen": ("#f0fdf4","#16a34a"),
        "rpend":  ("#f5f3ff","#7c3aed"),
        "rblue":  ("#eff6ff","#2563eb"),
    }
    bg, fg = colors.get(rag, ("#f8fafc","#64748b"))
    return f'<span class="badge" style="background:{bg};color:{fg}">{text}</span>'


def progress_bar(pct, rag="green"):
    colors = {"green": "#16a34a", "amber": "#d97706", "red": "#dc2626", "gray": "#9ca3af"}
    c = colors.get(rag, "#9ca3af")
    w = min(max(pct or 0, 0), 100)
    return f'<div class="pbar-bg"><div class="pbar-fill" style="width:{w}%;background:{c}"></div></div>'


def pareto_row(label, pct, rag="blue"):
    colors = {"red": "#dc2626", "amber": "#d97706", "green": "#16a34a", "blue": "#2563eb"}
    c = colors.get(rag, "#2563eb")
    w = min(max(pct or 0, 0), 100)
    return f"""
    <div class="pareto-row">
      <span class="pareto-lbl">{label}</span>
      <div class="pareto-bg"><div class="pareto-fill" style="width:{w}%;background:{c}"></div></div>
      <b>{pct:.0f}%</b>
    </div>"""


def section_title(text):
    return f'<div class="section-title">{text}</div>'


def info_box(text, style="blue"):
    bg = "#eff6ff" if style == "blue" else "#fef2f2"
    border = "#2563eb" if style == "blue" else "#dc2626"
    return f'<div class="info-box" style="background:{bg};border-left-color:{border}">{text}</div>'


def issue_table(rows):
    """rows = list of (issue, rag, owner, action, deadline, close_cond)"""
    if not rows:
        return '<p style="color:#94a3b8;font-size:12px">Chưa có issue/action</p>'
    trs = ""
    for r in rows:
        issue, rag, owner, action, deadline, close_cond = r
        trs += f"<tr><td>{issue}</td><td>{rag_badge(rag, 'r' + rag.lower() if rag != 'Pending' else 'rpend')}</td><td>{owner}</td><td>{action}</td><td>{deadline}</td><td>{close_cond}</td></tr>"
    return f"""
    <div class="tbl-wrap"><table>
      <thead><tr><th>Issue</th><th>RAG</th><th>Owner/PIC</th><th>Action</th><th>Deadline</th><th>Close condition</th></tr></thead>
      <tbody>{trs}</tbody>
    </table></div>"""


def svg_trend(title, note="Dữ liệu thật sẽ thay thế khi đủ dữ liệu theo tháng/tuần."):
    return f"""
    <div class="card">
      <div class="card-title">{title}</div>
      <div class="svg-box">
        <svg viewBox="0 0 620 180" xmlns="http://www.w3.org/2000/svg">
          <rect width="620" height="180" fill="#fff"/>
          <line x1="50" y1="40" x2="590" y2="40" stroke="#dc2626" stroke-dasharray="5,3" stroke-width="1"/>
          <text x="592" y="43" font-size="10" fill="#dc2626">Target</text>
          <polyline points="60,90 120,85 180,95 240,100 300,88 360,80 420,75 480,82 540,78"
                    fill="none" stroke="#2563eb" stroke-width="2.5"/>
          <text x="54" y="165" font-size="10" fill="#6b7280">T1</text>
          <text x="234" y="165" font-size="10" fill="#6b7280">T5</text>
          <text x="414" y="165" font-size="10" fill="#6b7280">T9</text>
          <text x="200" y="165" font-size="10" fill="#94a3b8">(Demo — sẽ cập nhật khi có dữ liệu thực)</text>
        </svg>
      </div>
      <div class="info-box" style="background:#eff6ff;border-left-color:#2563eb;margin-top:8px">{note}</div>
    </div>"""


def mini_kpi_row(kpis_by_site, dept_key, site, label, fmt_fn):
    """Get a KPI value for a specific site from site_breakdown."""
    site_data = get(kpis_by_site, dept_key, "site_breakdown", site, "kpis")
    if site_data is None:
        return PEND_TXT
    return fmt_fn(site_data)


# ─────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────

def bl(vi, en=""):
    """Bilingual label: Tiếng Việt (English) — theo quy ước dự án."""
    if en:
        return f'{vi} <span class="bi-en">({en})</span>'
    return vi


CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',-apple-system,BlinkMacSystemFont,'Inter',sans-serif;background:#f0f4f8;color:#1e293b;font-size:13px;line-height:1.5;margin:0;padding:0}
.bi-en{color:#94a3b8;font-size:10px;font-weight:400}

/* Warning banner */
.warn-banner{position:sticky;top:0;z-index:60;
             background:linear-gradient(90deg,#7f1d1d,#991b1b,#7f1d1d);
             color:#fff;text-align:center;font-size:11px;font-weight:700;
             padding:8px 14px;letter-spacing:.3px}

/* Header */
.hdr{background:linear-gradient(160deg,#0a2e12 0%,#145522 45%,#0a2e12 100%);
     color:#fff;padding:14px 18px 12px;padding-right:240px;
     box-shadow:0 4px 20px rgba(0,0,0,.5);border-bottom:3px solid #d4a017;
     position:relative;overflow:hidden}
/* Brand row */
.hdr-row{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:8px}
.gs-brand{display:flex;align-items:center;gap:8px;flex-shrink:0}
.gs-svg{width:48px;height:48px;flex-shrink:0;border-radius:8px;object-fit:cover}
.gs-txt{display:flex;flex-direction:column;gap:1px}
.gs-name{font-size:15px;font-weight:900;color:#f0c040;letter-spacing:1.8px;line-height:1}
.gs-sub{font-size:8px;color:#86efac;letter-spacing:.7px;font-weight:700;text-transform:uppercase}
.hdr-vline{width:1px;height:36px;background:rgba(255,255,255,.2);flex-shrink:0;
           margin:0 4px}
.hdr-titles{flex:1;min-width:0}
.gsp-pill{display:inline-flex;align-items:center;gap:4px;
          background:linear-gradient(90deg,#b8860b,#f0c040,#b8860b);
          color:#0a2e12;font-size:9px;font-weight:900;padding:2px 10px;
          border-radius:20px;letter-spacing:.8px;margin-bottom:5px;
          text-shadow:none;border:none}
.hdr-titles h1{font-size:16px;font-weight:800;letter-spacing:.3px;
               text-shadow:0 1px 4px rgba(0,0,0,.4);margin:0 0 2px;color:#fff}
.hdr .sub{font-size:10px;color:#86efac;line-height:1.5}
.hdr-tagline{font-size:9px;color:rgba(240,192,64,.7);letter-spacing:1.2px;
             font-weight:700;margin-top:6px;text-transform:uppercase}
/* GSP NEXT 30 badge — right side of header */
.gsp-badge-30{position:absolute;right:14px;top:10px;bottom:10px;
             border-radius:0;overflow:visible;box-shadow:none}
.gsp-badge-30 img{height:100%;width:auto;display:block;object-fit:cover;
                  mix-blend-mode:screen}
@media(max-width:960px){.gsp-badge-30{display:none}.hdr{padding-right:18px}}
.badges{display:flex;gap:7px;flex-wrap:wrap;margin-top:8px}
.bdg{font-size:10px;font-weight:800;border-radius:5px;padding:3px 9px;letter-spacing:.3px}
.bdg-warn{background:rgba(146,64,14,.9);color:#fef3c7;border:1px solid rgba(255,255,255,.15)}
.bdg-ok{background:rgba(20,83,45,.9);color:#d1fae5;border:1px solid rgba(255,255,255,.15)}
.bdg-info{background:rgba(6,78,59,.9);color:#d1fae5;border:1px solid rgba(255,255,255,.15)}
@media(max-width:600px){
  .hdr-vline{display:none}
  .hdr-row{gap:8px}
  .gs-name{font-size:13px}
  .hdr-titles h1{font-size:14px}
}

/* Tab nav */
input[name=tab]{display:none}
.nav{display:flex;background:#152a7a;overflow-x:auto;position:sticky;top:34px;z-index:50;
     border-bottom:3px solid #0f2266;box-shadow:0 2px 8px rgba(0,0,0,.25)}
.nav label{padding:10px 18px;color:rgba(255,255,255,.80);font-weight:700;font-size:13px;
           white-space:nowrap;cursor:pointer;border-radius:6px 6px 0 0;
           background:rgba(255,255,255,.09);border:1px solid rgba(255,255,255,.15);
           border-bottom:3px solid transparent;margin:6px 3px 0;
           transition:.2s;letter-spacing:.2px;margin-bottom:-3px}
.nav label:hover{background:rgba(255,255,255,.18);color:#fff;border-color:rgba(255,255,255,.30)}
#t1:checked~.nav label[for=t1],#t2:checked~.nav label[for=t2],
#t3:checked~.nav label[for=t3],#t4:checked~.nav label[for=t4],
#t5:checked~.nav label[for=t5],#t6:checked~.nav label[for=t6]{
  color:#0f2d87 !important;background:#ffffff;border-color:rgba(255,255,255,.3);
  border-bottom:3px solid #ffffff;font-weight:800}
.panel{display:none;padding:0;max-width:100%;margin:0}
#t1:checked~#c1,#t2:checked~#c2,#t3:checked~#c3,
#t4:checked~#c4,#t5:checked~#c5,#t6:checked~#c6{display:block}

/* Section title */
.section-title{font-size:14px;font-weight:800;color:#0a2e12;margin:18px 0 11px;
               display:flex;align-items:center;gap:9px;letter-spacing:.2px}
.section-title::before{content:'';width:4px;height:20px;
                       background:linear-gradient(180deg,#22c55e,#145522);
                       border-radius:2px;flex-shrink:0;
                       box-shadow:0 2px 5px rgba(20,85,34,.4)}

/* Cards */
.card{background:#fff;border-radius:12px;
      box-shadow:0 2px 10px rgba(0,0,0,.08),0 0 1px rgba(0,0,0,.05);
      padding:16px;margin-bottom:13px}
.card:hover{box-shadow:0 4px 16px rgba(0,0,0,.11)}
.card-title{font-size:13px;font-weight:700;color:#0f2d87;
            border-bottom:2px solid #e2e8f0;padding-bottom:9px;margin-bottom:11px;
            display:flex;align-items:center;gap:6px}

/* KPI cards */
.kpi-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(145px,1fr));gap:11px;margin-bottom:14px}
.kpi-grid-5{display:grid;grid-template-columns:repeat(5,1fr);gap:11px;margin-bottom:14px;align-items:stretch}
.kpi-card{background:#fff;border-radius:12px;padding:15px 13px;text-align:center;
          box-shadow:0 2px 8px rgba(0,0,0,.08),0 0 1px rgba(0,0,0,.04);
          border-top:4px solid #2563eb;transition:transform .15s,box-shadow .15s;min-width:0;
          display:flex;flex-direction:column;align-items:center}
.kpi-card:hover{transform:translateY(-2px);box-shadow:0 6px 18px rgba(0,0,0,.12)}
.kpi-card.rag-green{border-top-color:#16a34a;background:linear-gradient(180deg,#f0fdf4 0%,#fff 35%)}
.kpi-card.rag-amber{border-top-color:#d97706;background:linear-gradient(180deg,#fffbeb 0%,#fff 35%)}
.kpi-card.rag-red{border-top-color:#dc2626;background:linear-gradient(180deg,#fef2f2 0%,#fff 35%)}
.kpi-card.rag-gray{border-top-color:#9ca3af;background:#fff}
.kpi-card.rag-blue{border-top-color:#2563eb;background:linear-gradient(180deg,#eff6ff 0%,#fff 35%)}
.kpi-card.rag-purple{border-top-color:#7c3aed;background:linear-gradient(180deg,#f5f3ff 0%,#fff 35%)}
.kpi-val{font-size:26px;font-weight:900;line-height:1.1;color:#1e293b;width:100%}
.kpi-val.red{color:#dc2626}.kpi-val.green{color:#16a34a}.kpi-val.amber{color:#d97706}
.kpi-val.blue{color:#2563eb}.kpi-val.gray{color:#6b7280}
.kpi-lbl{font-size:11px;font-weight:700;color:#374151;margin-top:5px;line-height:1.35;width:100%}
.kpi-sub{font-size:10px;color:#9ca3af;margin-top:3px;line-height:1.3}

/* Factory heatmap */
.heat-grid{display:grid;grid-template-columns:155px repeat(6,1fr);
           border:1px solid #e2e8f0;border-radius:11px;overflow:hidden;
           background:#fff;overflow-x:auto;min-width:800px;
           box-shadow:0 2px 10px rgba(0,0,0,.07)}
.heat-hdr{background:linear-gradient(180deg,#1a3a8f,#0f2266);
          color:#fff;font-size:11px;font-weight:700;padding:10px 11px;letter-spacing:.3px}
.heat-cell{font-size:11px;padding:10px 11px;border-right:1px solid #e8ecf0;
           border-bottom:1px solid #e8ecf0;min-height:52px}
.heat-cell strong{display:block;font-size:12px;margin-bottom:2px;font-weight:700}
.bg-green{background:linear-gradient(135deg,#f0fdf4,#dcfce7);color:#15803d}
.bg-amber{background:linear-gradient(135deg,#fffbeb,#fef9c3);color:#92400e}
.bg-red{background:linear-gradient(135deg,#fef2f2,#fee2e2);color:#b91c1c}
.bg-pend{background:linear-gradient(135deg,#f5f3ff,#ede9fe);color:#6d28d9}
.bg-gray{background:#f8fafc;color:#334155}

/* Badges */
.badge{display:inline-block;padding:2px 9px;border-radius:20px;font-size:10px;
       font-weight:700;white-space:nowrap;letter-spacing:.2px}

/* Info boxes */
.info-box{border-left:4px solid #2563eb;
          background:linear-gradient(135deg,#eff6ff,#f8faff);
          border-radius:0 8px 8px 0;padding:11px 14px;margin:8px 0;
          font-size:12px;line-height:1.55}
.warn-box{border-left:4px solid #dc2626;
          background:linear-gradient(135deg,#fef2f2,#fff5f5);
          border-radius:0 8px 8px 0;padding:11px 14px;margin:8px 0;
          font-size:12px;line-height:1.55}

/* Tables */
.tbl-wrap{overflow-x:auto;border-radius:8px;
          box-shadow:0 1px 5px rgba(0,0,0,.07)}
table{width:100%;border-collapse:collapse;font-size:12px}
th{background:linear-gradient(180deg,#1a3a8f,#0f2266);color:#fff;text-align:left;
   padding:9px 11px;font-size:11px;white-space:nowrap;letter-spacing:.2px}
td{padding:8px 11px;border-bottom:1px solid #f1f5f9;vertical-align:top;line-height:1.5}
tr:nth-child(even) td{background:#fafbfc}
tr:hover td{background:#f0f7ff;transition:.1s}

/* Progress bars */
.pbar-bg{height:15px;background:#e2e8f0;border-radius:99px;overflow:hidden;min-width:100px}
.pbar-fill{height:100%;border-radius:99px;transition:width .3s}

/* Pareto */
.pareto-row{display:grid;grid-template-columns:140px 1fr 46px;align-items:center;
            gap:9px;margin:8px 0;font-size:12px}
.pareto-lbl{font-weight:600;color:#374151}
.pareto-bg{height:16px;background:#e2e8f0;border-radius:99px;overflow:hidden}
.pareto-fill{height:100%;border-radius:99px}

/* Drill-down */
details.drill{margin-top:9px;border-radius:8px;overflow:hidden;
              border:1px solid #e2e8f0;box-shadow:0 1px 4px rgba(0,0,0,.06)}
details.drill>summary{list-style:none;cursor:pointer;
                       background:linear-gradient(180deg,#f8fafc,#f0f4f9);
                       color:#0f2d87;font-weight:700;font-size:11px;padding:9px 13px;
                       border-bottom:1px solid #e2e8f0;user-select:none;letter-spacing:.2px}
details.drill>summary::before{content:"🔍 "}
details.drill>summary::-webkit-details-marker{display:none}
details.drill[open]>summary::after{content:" ▲";float:right;color:#94a3b8}
details.drill:not([open])>summary::after{content:" ▼";float:right;color:#94a3b8}
.drill-body{padding:13px;background:#fff}

/* GSTT heatmap */
.gstt-grid{display:grid;grid-template-columns:140px repeat(5,1fr);
           border:1px solid #e2e8f0;border-radius:11px;overflow:hidden;
           background:#fff;min-width:720px;overflow-x:auto;
           box-shadow:0 2px 10px rgba(0,0,0,.07)}
.gstt-hdr{background:linear-gradient(180deg,#1a3a8f,#0f2266);
          color:#fff;font-size:11px;font-weight:700;padding:9px 10px;letter-spacing:.3px}
.gstt-cell{font-size:11px;padding:9px 10px;border-right:1px solid #e2e8f0;
           border-bottom:1px solid #e2e8f0}
.gstt-cell strong{display:block;font-size:12px;margin-bottom:2px}

/* Score bars */
.score-bg{height:14px;background:#e2e8f0;border-radius:99px;overflow:hidden;
          min-width:100px;display:inline-block;width:80px;vertical-align:middle}
.score-fill{height:100%;border-radius:99px}

/* SVG chart */
.svg-box{width:100%;background:#fff;border:1px solid #e2e8f0;border-radius:10px;
         padding:10px;overflow-x:auto;box-shadow:0 1px 4px rgba(0,0,0,.05)}
.svg-box svg{min-width:500px;width:100%;height:auto;display:block}

/* Grid layouts */
.grid-2{display:grid;grid-template-columns:repeat(2,1fr);gap:13px;margin-bottom:13px}
.grid-3{display:grid;grid-template-columns:repeat(3,1fr);gap:13px;margin-bottom:13px}
.note{background:linear-gradient(135deg,#fffbeb,#fef9c3);
      border:1px dashed #d97706;border-radius:8px;padding:11px 14px;
      font-size:12px;font-weight:600;color:#92400e;margin:9px 0 15px;line-height:1.55}

/* Footer */
.footer{background:linear-gradient(135deg,#061a0d,#0a2e12);
        color:rgba(255,255,255,.5);text-align:center;font-size:10px;padding:14px;letter-spacing:.3px}

/* Tab content padding — cho tabs GS1/GS5/GS6/KPI-PIC/GSTT (không có sidebar) */
.tab-pad{padding:16px 20px 40px;max-width:100%}

/* Section fold — accordion cho sections phụ */
.sec-fold{border-radius:10px;overflow:visible;margin-bottom:13px}
.sec-fold>summary{list-style:none;cursor:pointer;
                   background:linear-gradient(135deg,#f8fafc,#ecfdf5);
                   color:#0a2e12;font-weight:800;font-size:12px;padding:11px 16px;
                   border:1px solid #86efac;border-radius:10px;user-select:none;
                   display:flex;align-items:center;gap:8px;letter-spacing:.2px}
.sec-fold>summary::-webkit-details-marker{display:none}
.sec-fold[open]>summary{border-radius:10px 10px 0 0;border-bottom:none}
.sec-fold[open]>summary::after{content:"▲";margin-left:auto;color:#94a3b8;font-size:10px}
.sec-fold:not([open])>summary::after{content:"▼";margin-left:auto;color:#94a3b8;font-size:10px}
.sec-fold-body{padding:15px;border:1px solid #86efac;border-top:none;
               border-radius:0 0 10px 10px;background:#fff}

/* ── Sidebar layout ───────────────────────────────────────── */
.panel-sb{display:none}/* obsolete — replaced by tong-bo-layout */
.tong-bo-layout{display:flex;gap:0;align-items:flex-start;
               padding:0;width:100%}
.sb-col{width:240px;flex-shrink:0;position:sticky;top:80px;
        display:flex;flex-direction:column;gap:10px;align-self:flex-start;
        background:#f8fafc;border-right:1px solid #e2e8f0;
        padding:16px 12px 40px}
.sb-card{background:#fff;border-radius:8px;padding:12px;
         border:1px solid #e2e8f0;border-top:3px solid #145522;
         margin-bottom:0}
.sb-title{font-size:10px;font-weight:800;color:#145522;margin-bottom:10px;
          letter-spacing:.5px;text-transform:uppercase;
          display:flex;align-items:center;gap:5px}
.sb-kpi{border-radius:8px;padding:9px 11px;margin-bottom:7px;
        border-left:4px solid #ccc}
.sb-kpi:last-child{margin-bottom:0}
.sb-kpi-lbl{font-size:10px;font-weight:700;color:#374151;margin-bottom:2px;
            white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.sb-kpi-val{font-size:18px;font-weight:900;line-height:1.1}
.sb-link{font-size:11px;color:#166534;padding:5px 0;
         border-bottom:1px solid #f1f5f9;display:block;
         text-decoration:none;white-space:nowrap;
         overflow:hidden;text-overflow:ellipsis}
.sb-link:last-child{border-bottom:none}
.sb-link:hover{color:#14532d;padding-left:3px;transition:.15s}
.main-col{flex:1;min-width:0;overflow:hidden;padding:16px 20px 40px}

/* ── Mobile responsive ── */
.tab-short{display:none}
@media(max-width:960px){
  .kpi-grid-5{grid-template-columns:repeat(2,1fr)}
  .grid-2,.grid-3{grid-template-columns:1fr}
  .heat-grid,.gstt-grid{min-width:700px}
  .panel{padding:12px 12px 30px}
  .nav label{padding:8px 12px;font-size:12px;margin:4px 2px 0;border-radius:5px 5px 0 0}
  .sec-fold>summary{font-size:11px;padding:9px 12px}
  .tong-bo-layout{flex-direction:column;align-items:stretch}
  .main-col{order:1;width:100%}
  .sb-col{order:2;position:static;width:100%;min-height:auto;border-right:none;
          border-top:2px solid #e2e8f0;display:grid;
          grid-template-columns:repeat(2,1fr);gap:8px;padding:12px}
  .sb-card{border-top-width:2px}
  .tab-full{display:none}.tab-short{display:inline}
}
@media(max-width:600px){
  .sb-col{grid-template-columns:1fr}
  .nav label{padding:6px 7px;font-size:11px}
}
"""

# ─────────────────────────────────────────────────────────────
# TAB BUILDERS
# ─────────────────────────────────────────────────────────────

def build_sidebar(kpi, build_time):
    """Sticky left sidebar — Mini KPI + Data Status + Quick Nav."""
    d_sx   = get(kpi, "01_SAN_XUAT",   "kpis") or {}
    d_otif = get(kpi, "02_KHSX_OTIF",  "kpis") or {}
    d_qlcl = get(kpi, "03_QLCL",       "kpis") or {}
    d_tb   = get(kpi, "04_QLTB_CD",    "kpis") or {}
    d_bo   = get(kpi, "08_BO_CONTROL", "kpis") or {}

    pd_val   = fmt(d_sx.get("plan_do_pct_avg"),    "%") if d_sx   else PEND_TXT
    otif_val = fmt(d_otif.get("otif_pct"),          "%") if d_otif else PEND_TXT
    dt_val   = fmt(d_tb.get("total_downtime_hrs"),  "h") if d_tb   else PEND_TXT
    ncr_val  = str(d_qlcl.get("total_ncr", "—"))       if d_qlcl else PEND_TXT
    bo_open  = d_bo.get("open",      "—") if d_bo else "—"
    bo_over  = d_bo.get("overdue",   0)   if d_bo else 0
    bo_esc   = d_bo.get("escalated", 0)   if d_bo else 0

    rag_css = {
        "rag-green":  ("#16a34a", "#f0fdf4"),
        "rag-amber":  ("#d97706", "#fffbeb"),
        "rag-red":    ("#dc2626", "#fef2f2"),
        "rag-gray":   ("#9ca3af", "#f8fafc"),
        "rag-blue":   ("#2563eb", "#eff6ff"),
    }

    def sb_kpi(label, value, rc):
        c, bg = rag_css.get(rc, ("#9ca3af", "#f8fafc"))
        return (f'<div class="sb-kpi" style="background:{bg};border-left-color:{c}">'
                f'<div class="sb-kpi-lbl">{label}</div>'
                f'<div class="sb-kpi-val" style="color:{c}">{value}</div></div>')

    pd_rag = rag_color(d_sx.get("plan_do_pct_avg"),           95, 85)      if d_sx   else "rag-gray"
    ot_rag = rag_color(d_otif.get("otif_pct"),                95, 85)      if d_otif else "rag-gray"
    dt_rag = rag_color(d_tb.get("total_downtime_hrs",  999),   0,  2, True) if d_tb   else "rag-gray"
    nc_rag = rag_color(d_qlcl.get("total_ncr",        999),   0,  3, True) if d_qlcl else "rag-gray"

    bo_color = "#dc2626" if bo_open not in ("—", 0, "0") else "#16a34a"

    def dot(c):
        return f'<span style="display:inline-block;width:9px;height:9px;border-radius:50%;background:{c};margin-right:5px;flex-shrink:0"></span>'

    sites = [
        ("GS1 / GSHN", "8/8 DQG PASS", "#16a34a"),
        ("GS5 / GSQV", f"Dữ liệu thật · {EXPECTED_DATE}", "#9ca3af"),
        ("GS6 / GSQV", f"Dữ liệu thật · {EXPECTED_DATE}", "#9ca3af"),
    ]
    site_rows = "".join(
        f'<div style="font-size:11px;color:#374151;padding:4px 0;border-bottom:1px solid #f1f5f9;'
        f'display:flex;align-items:center">{dot(c)}'
        f'<span style="flex:1">{s}</span>'
        f'<span style="font-size:10px;color:{c};font-weight:600">{st}</span></div>'
        for s, st, c in sites
    )

    return (
        f'<aside class="sb-col">'

        # ── Mini KPI ──────────────────────────────────
        f'<div class="sb-card">'
        f'<div class="sb-title">📊 KPI Tổng hợp</div>'
        f'{sb_kpi("Tuân thủ KH (Plan/DO)", pd_val, pd_rag)}'
        f'{sb_kpi("Giao đúng hạn (OTIF)", otif_val, ot_rag)}'
        f'{sb_kpi("Dừng máy (Downtime)", dt_val, dt_rag)}'
        f'{sb_kpi("Phiếu NC (NCR)", ncr_val, nc_rag)}'
        f'</div>'

        # ── Issues counter ────────────────────────────
        f'<div class="sb-card" style="border-top:3px solid {bo_color}">'
        f'<div class="sb-title" style="color:{bo_color}">🚨 BO Issues</div>'
        f'<div style="text-align:center;padding:6px 0">'
        f'<div style="font-size:36px;font-weight:900;color:{bo_color};line-height:1">{bo_open}</div>'
        f'<div style="font-size:10px;color:#6b7280;margin-top:3px">Đang mở</div>'
        f'</div>'
        f'<div style="display:flex;justify-content:space-around;margin-top:8px;'
        f'padding-top:8px;border-top:1px solid #f1f5f9">'
        f'<div style="text-align:center">'
        f'<div style="font-size:14px;font-weight:800;color:#dc2626">{bo_over}</div>'
        f'<div style="font-size:9px;color:#6b7280">Quá hạn</div></div>'
        f'<div style="text-align:center">'
        f'<div style="font-size:14px;font-weight:800;color:#d97706">{bo_esc}</div>'
        f'<div style="font-size:9px;color:#6b7280">Escalated</div></div>'
        f'</div></div>'

        # ── Data Status ───────────────────────────────
        f'<div class="sb-card">'
        f'<div class="sb-title">📡 Data Status</div>'
        f'{site_rows}'
        f'<div style="font-size:10px;color:#9ca3af;margin-top:8px;padding-top:6px;'
        f'border-top:1px solid #f1f5f9">🕐 {build_time}</div>'
        f'</div>'

        # ── Quick Nav ─────────────────────────────────
        f'<div class="sb-card">'
        f'<div class="sb-title">⚡ Nội dung</div>'
        f'<a class="sb-link" href="#sec1">🗺️ Heatmap sức khỏe NM</a>'
        f'<a class="sb-link" href="#sec2">📊 KPI Cards điều hành</a>'
        f'<a class="sb-link" href="#sec3">📦 Kho / WIP / FIFO</a>'
        f'<a class="sb-link" href="#sec4">🏢 Rủi ro khách hàng</a>'
        f'<a class="sb-link" href="#sec5">📋 Aging / ECN / RMA</a>'
        f'<a class="sb-link" href="#sec6">🛡️ GSTT Compliance</a>'
        f'</div>'

        f'</aside>'
    )


def build_alert_bar(d_bo):
    """Top 3 Issues + Action count — hiển thị đầu Tab Tổng BO, trước Heatmap."""
    open_count    = d_bo.get("open",      "—") if d_bo else "—"
    overdue_count = d_bo.get("overdue",   "—") if d_bo else "—"
    escalated     = d_bo.get("escalated", "—") if d_bo else "—"

    # Top 3 issues — static critical items (sẽ tự động từ 08_BO_CONTROL khi có data)
    top3 = [
        {"issue": "PROD_LOG GS5/GS6 thiếu ORDER_ID — không map được OTIF, cần bổ sung ngay",
         "rag": "Red",    "owner": "Mr Lam / Mr Mạnh",    "deadline": "15/06", "site": "GS5/GS6"},
        {"issue": "OTIF GS1 = 50.0% — chưa có root cause, cần xác nhận với Mr Hào",
         "rag": "Red",    "owner": "Mr Hào",               "deadline": "15/06", "site": "GS1"},
        {"issue": "Machine Log GS1/GS5/GS6 thiếu reason code, start/end time — OEE chưa tính được",
         "rag": "Yellow", "owner": "Mr Thập / Mr Nam",     "deadline": "15/06", "site": "GS1/GS5/GS6"},
    ]

    rag_border = {"Red": "#dc2626", "Yellow": "#d97706", "Green": "#16a34a"}
    rag_icon   = {"Red": "🔴", "Yellow": "🟡", "Green": "🟢"}

    cards_html = ""
    for i, item in enumerate(top3, 1):
        border_c = rag_border.get(item["rag"], "#9ca3af")
        icon     = rag_icon.get(item["rag"], "⚪")
        cards_html += f"""
        <div style="flex:1;min-width:190px;max-width:380px;background:#fff;border-radius:10px;
                    padding:13px 15px;border-left:4px solid {border_c};
                    box-shadow:0 2px 10px rgba(0,0,0,.1)">
          <div style="font-size:10px;font-weight:800;color:#64748b;margin-bottom:5px;letter-spacing:.4px">
            {icon}&nbsp;VẤN ĐỀ #{i}&nbsp;·&nbsp;{item['site']}
          </div>
          <div style="font-size:12px;font-weight:700;color:#1e293b;line-height:1.45;margin-bottom:8px">
            {item['issue']}
          </div>
          <div style="display:flex;gap:6px;flex-wrap:wrap">
            <span style="background:#f1f5f9;color:#374151;padding:2px 8px;border-radius:5px;
                         font-size:10px;font-weight:600">👤 {item['owner']}</span>
            <span style="background:#fef3c7;color:#92400e;padding:2px 8px;border-radius:5px;
                         font-size:10px;font-weight:600">📅 {item['deadline']}</span>
          </div>
        </div>"""

    return f"""
    <div style="background:linear-gradient(135deg,#0c1445 0%,#0f2d87 55%,#1a4fba 100%);
                border-radius:14px;padding:16px 18px;margin-bottom:18px;
                box-shadow:0 4px 20px rgba(15,45,135,.3)">
      <div style="display:flex;align-items:center;justify-content:space-between;
                  margin-bottom:13px;flex-wrap:wrap;gap:8px">
        <div style="font-size:14px;font-weight:900;color:#fff;letter-spacing:.3px">
          🚨 Top 3 Vấn đề cần xử lý ngay
        </div>
        <div style="display:flex;gap:8px;flex-wrap:wrap">
          <span style="background:rgba(220,38,38,.3);color:#fca5a5;padding:4px 12px;
                       border-radius:6px;font-size:11px;font-weight:700;border:1px solid rgba(220,38,38,.4)">
            🔴 Đang mở: {open_count}
          </span>
          <span style="background:rgba(239,68,68,.3);color:#fecaca;padding:4px 12px;
                       border-radius:6px;font-size:11px;font-weight:700;border:1px solid rgba(239,68,68,.4)">
            ⏰ Quá hạn: {overdue_count}
          </span>
          <span style="background:rgba(251,191,36,.2);color:#fde68a;padding:4px 12px;
                       border-radius:6px;font-size:11px;font-weight:700;border:1px solid rgba(251,191,36,.3)">
            🔺 Escalated: {escalated}
          </span>
        </div>
      </div>
      <div style="display:flex;gap:11px;flex-wrap:wrap">
        {cards_html}
      </div>
      <div style="font-size:10px;color:rgba(255,255,255,.45);margin-top:11px;
                  border-top:1px solid rgba(255,255,255,.12);padding-top:9px">
        ✅ Pipeline 8/8 DQG PASS · KPI chính thức từ 08/06/2026 · Dữ liệu thật GS5/GS6 dự kiến: {EXPECTED_DATE_FULL}
      </div>
    </div>"""


def build_tab_tong_bo(kpi, dqg, build_time):
    """Tab 1 — Tổng BO: Factory Health Heatmap + Executive KPI + Inventory + Customer + GSTT."""
    d_sx   = get(kpi, "01_SAN_XUAT",      "kpis") or {}
    d_otif = get(kpi, "02_KHSX_OTIF",     "kpis") or {}
    d_qlcl = get(kpi, "03_QLCL",          "kpis") or {}
    d_tb   = get(kpi, "04_QLTB_CD",       "kpis") or {}
    d_kho  = get(kpi, "05_KHO",           "kpis") or {}
    d_gstt = get(kpi, "06_GSTT",          "kpis") or {}
    d_bo   = get(kpi, "08_BO_CONTROL",    "kpis") or {}

    # Helper: get dqg_status for a dept
    def dqg_st(dept):
        return get(kpi, dept, "dqg_status") or "SKIP"

    def hcell(val, status):
        bg = {"PASS": "bg-pend", "SKIP": "bg-pend", "PENDING": "bg-pend"}.get(status, "bg-pend")
        return f'<div class="heat-cell {bg}"><strong>{val}</strong>{status}</div>'

    # ── 1. Factory Health Heatmap ──────────────────────────────
    plan_do_txt  = fmt(d_sx.get("plan_do_pct_avg"),  "%") if d_sx else PEND_TXT
    otif_txt     = fmt(d_otif.get("otif_pct"),       "%") if d_otif else PEND_TXT
    dt_txt       = fmt(d_tb.get("total_downtime_hrs"), "h") if d_tb else "Blocked"
    ncr_txt      = str(d_qlcl.get("total_ncr", "—")) if d_qlcl else PEND_TXT
    wip_txt      = str(int(d_kho.get("total_wip_qty", 0))) if d_kho else PEND_TXT

    def heat_cell(value, rag_class):
        return f'<div class="heat-cell {rag_class}"><strong>{value}</strong></div>'

    heatmap = f"""
    <div style="overflow-x:auto">
    <div class="heat-grid">
      <div class="heat-hdr">Nhà máy</div>
      <div class="heat-hdr">Tuân thủ KH<br><span style="font-weight:400;opacity:.8">(Plan/DO)</span></div>
      <div class="heat-hdr">Giao đúng hạn<br><span style="font-weight:400;opacity:.8">(OTIF)</span></div>
      <div class="heat-hdr">Hiệu suất máy<br><span style="font-weight:400;opacity:.8">(OEE/Downtime)</span></div>
      <div class="heat-hdr">Chất lượng<br><span style="font-weight:400;opacity:.8">(Quality/NCR)</span></div>
      <div class="heat-hdr">Tồn kho BTP<br><span style="font-weight:400;opacity:.8">(WIP/FIFO)</span></div>
      <div class="heat-hdr">Tổng thể<br><span style="font-weight:400;opacity:.8">(Overall)</span></div>

      <div class="heat-cell bg-gray"><strong>GSHN / GS1</strong>Mr Hào</div>
      {heat_cell(plan_do_txt, "bg-pend")}
      {heat_cell(otif_txt, "bg-pend")}
      {heat_cell(dt_txt if dt_txt != "N/A" else "Blocked", "bg-pend")}
      {heat_cell(ncr_txt, "bg-pend")}
      {heat_cell(wip_txt, "bg-pend")}
      <div class="heat-cell bg-amber"><strong>Yellow</strong>Cần theo dõi</div>

      <div class="heat-cell bg-gray"><strong>GSQV / GS5</strong>Mr Lam</div>
      {heat_cell(f"Chờ · {EXPECTED_DATE}", "bg-pend")}
      {heat_cell(f"Chờ · {EXPECTED_DATE}", "bg-pend")}
      {heat_cell(f"Chờ · {EXPECTED_DATE}", "bg-pend")}
      {heat_cell(f"Chờ · {EXPECTED_DATE}", "bg-pend")}
      {heat_cell(f"Chờ · {EXPECTED_DATE}", "bg-pend")}
      <div class="heat-cell bg-red"><strong>🔴 Chờ data</strong>Dự kiến {EXPECTED_DATE}</div>

      <div class="heat-cell bg-gray"><strong>GSQV / GS6</strong>Mr Mạnh</div>
      {heat_cell(f"Chờ · {EXPECTED_DATE}", "bg-pend")}
      {heat_cell(f"Chờ · {EXPECTED_DATE}", "bg-pend")}
      {heat_cell(f"Chờ · {EXPECTED_DATE}", "bg-pend")}
      {heat_cell(f"Chờ · {EXPECTED_DATE}", "bg-pend")}
      {heat_cell(f"Chờ · {EXPECTED_DATE}", "bg-pend")}
      <div class="heat-cell bg-red"><strong>🔴 Chờ data</strong>Dự kiến {EXPECTED_DATE}</div>
    </div>
    </div>"""

    # ── 2. RACI Owner table ────────────────────────────────────
    raci_table = """
    <div class="tbl-wrap"><table>
      <thead><tr><th>KPI</th><th>Operational Owner</th><th>Data Provider</th><th>Escalation</th></tr></thead>
      <tbody>
        <tr><td>Plan/DO</td><td>GĐNM theo site</td><td>SX/KHSX theo template</td><td>BO Lead</td></tr>
        <tr><td>OTIF</td><td>GS1–Mr Hào; GS5–Mr Lam; GS6–Mr Mạnh</td><td>Mr Hưng (KHSX-Điều độ)</td><td>Ms Ly nếu thiếu dữ liệu</td></tr>
        <tr><td>OEE/Downtime</td><td>Mr Thập (GS1) / Mr Nam (GSQV)</td><td>Machine Log</td><td>Mr Thành / BO Lead</td></tr>
        <tr><td>Quality/NCR</td><td>Mr Đức / Mr Giang</td><td>NCR/CAR Log</td><td>Quality Lead / BO Lead</td></tr>
        <tr><td>WIP/FIFO/Kho</td><td>Mr Dũng (GS1) / Mr Luân (GSQV)</td><td>Kho Log</td><td>BO Lead</td></tr>
        <tr><td>GSTT</td><td>Mr Lâm / GSTT</td><td>Field Check Log</td><td>BO Lead / CEO</td></tr>
      </tbody>
    </table></div>"""

    # ── 3. Executive KPI Cards ─────────────────────────────────
    pd_val   = fmt(d_sx.get("plan_do_pct_avg"),    "%") if d_sx else "Trial data"
    otif_val = fmt(d_otif.get("otif_pct"),         "%") if d_otif else "Pending"
    dt_val   = fmt(d_tb.get("total_downtime_hrs"), "h") if d_tb else "Blocked"
    ncr_val  = str(d_qlcl.get("total_ncr",  "Trial")) if d_qlcl else "Trial data"

    pd_rag   = rag_color(d_sx.get("plan_do_pct_avg"),  95, 85) if d_sx else "rag-gray"
    otif_rag = rag_color(d_otif.get("otif_pct"),       95, 85) if d_otif else "rag-gray"
    dt_rag   = rag_color(d_tb.get("total_downtime_hrs", 999), 0, 2, reverse=True) if d_tb else "rag-gray"
    ncr_rag  = rag_color(d_qlcl.get("total_ncr",  999), 0, 3, reverse=True) if d_qlcl else "rag-gray"

    exec_cards = f"""
    <div class="kpi-grid-5">
      {kpi_card("Tuân thủ kế hoạch (Plan/DO)", f'<span class="{pd_rag.replace("rag-","")}">{pd_val}</span>',
                "Trung bình toàn nhà máy", pd_rag,
                "<table><tr><th>Site</th><th>Actual</th><th>Target</th><th>Owner</th></tr>"
                "<tr><td>GS1</td><td>Trial DQG</td><td>≥95%</td><td>Mr Hào</td></tr>"
                "<tr><td>GS5</td><td>Pending</td><td>≥95%</td><td>Mr Lam</td></tr>"
                "<tr><td>GS6</td><td>Pending</td><td>≥95%</td><td>Mr Mạnh</td></tr></table>")}
      {kpi_card("Giao đúng hàng đúng hạn (OTIF)", f'<span class="{otif_rag.replace("rag-","")}">{otif_val}</span>',
                "On-Time In-Full", otif_rag,
                "<div class='warn-box'>Operational Owner theo site: GS1–Mr Hào, GS5–Mr Lam, GS6–Mr Mạnh.<br>External Data Provider: Mr Hưng (KHSX-Điều độ). Escalation: Ms Ly.</div>")}
      {kpi_card("Hiệu suất máy / Dừng máy (OEE/Downtime)", f'<span class="{dt_rag.replace("rag-","")}">{dt_val}</span>',
                "Tổng thời gian dừng (Downtime)", dt_rag,
                "<div class='warn-box'>OEE cần Machine Log có planned time / run time / downtime start-end / reason code. Owner: Mr Thập (GS1), Mr Nam (GSQV).</div>")}
      {kpi_card("Chất lượng / Phiếu NC (Quality/NCR)", f'<span class="{ncr_rag.replace("rag-","")}">{ncr_val}</span>',
                "Tổng phiếu không phù hợp (NCR)", ncr_rag,
                f"<table><tr><th>Metric</th><th>Giá trị</th><th>Owner</th></tr>"
                f"<tr><td>NCR Total</td><td>{ncr_val}</td><td>Mr Đức / Mr Giang</td></tr>"
                f"<tr><td>Open</td><td>{d_qlcl.get('open','—')}</td><td>Owner theo NCR</td></tr>"
                f"<tr><td>COPQ ước tính</td><td>{d_qlcl.get('copq_estimated','—')}</td><td>Mr Đức + Tài chính</td></tr></table>")}
      {kpi_card("BO Issues", f'<span class="{"red" if (d_bo.get("open") or 0) > 0 else "green"}">{d_bo.get("open", "—")}</span>',
                "Đang mở", "rag-red" if (d_bo.get("open") or 0) > 0 else "rag-green",
                f"<table><tr><th>Metric</th><th>Count</th></tr>"
                f"<tr><td>Total</td><td>{d_bo.get('total_issues','—')}</td></tr>"
                f"<tr><td>Overdue</td><td>{d_bo.get('overdue','—')}</td></tr>"
                f"<tr><td>Escalated</td><td>{d_bo.get('escalated','—')}</td></tr></table>")}
    </div>"""

    # ── 4. Inventory / Warehouse Capacity ─────────────────────
    wip_total   = d_kho.get("total_wip_qty")
    fifo_breach = d_kho.get("fifo_breach", 0)
    fifo_ok     = d_kho.get("fifo_ok", 0)
    risk_high   = d_kho.get("risk_high", 0)

    inv_cards = f"""
    <div class="note">📦 Block theo dõi kho, dòng chảy WIP/BTP, rủi ro quá tải công suất kho theo site.
    {'KPI từ nguồn 05_KHO đã qua DQG.' if d_kho else f'Đang {PEND_TXT} — chờ kết nối dữ liệu từ INP-KHO-001.'}</div>
    <div class="kpi-grid">
      {kpi_card("WIP / BTP tổng kho", f'<span class="blue">{fmt(wip_total, "", 0) if wip_total else PEND_TXT}</span>', "Tổng bán thành phẩm", "rag-blue")}
      {kpi_card("FIFO OK", f'<span class="green">{fifo_ok}</span>' if d_kho else f'<span class="gray">{PEND_TXT}</span>', "Lot FIFO đúng", "rag-green" if d_kho else "rag-gray")}
      {kpi_card("FIFO Breach", f'<span class="red">{fifo_breach}</span>' if d_kho else f'<span class="gray">{PEND_TXT}</span>', "Vi phạm FIFO", "rag-red" if fifo_breach else "rag-green")}
      {kpi_card("Risk High", f'<span class="red">{risk_high}</span>' if d_kho else f'<span class="gray">{PEND_TXT}</span>', "Rủi ro cao", "rag-red" if risk_high else "rag-green")}
    </div>
    <div class="tbl-wrap"><table>
      <thead><tr><th>Site</th><th>Sức chứa (m²)</th><th>Đang dùng</th><th>% Lấp đầy</th><th>Overflow</th><th>WIP Cap</th><th>FIFO OK?</th><th>RAG</th></tr></thead>
      <tbody>
        <tr><td>GS1</td><td>—</td><td>—</td><td>{PEND_TXT}</td><td>Pending</td><td>Pending</td><td>Pending</td><td>{rag_badge("Pending","rpend")}</td></tr>
        <tr><td>GS5</td><td>—</td><td>—</td><td>{PEND_TXT}</td><td>Pending</td><td>Pending</td><td>Pending</td><td>{rag_badge("Pending","rpend")}</td></tr>
        <tr><td>GS6</td><td>—</td><td>—</td><td>{PEND_TXT}</td><td>Pending</td><td>Pending</td><td>Pending</td><td>{rag_badge("Pending","rpend")}</td></tr>
      </tbody>
    </table></div>"""

    # ── 5. Customer Risk ───────────────────────────────────────
    cust_table = f"""
    <div class="tbl-wrap"><table>
      <thead><tr><th>Khách hàng</th><th>Nhà máy</th><th>Nhóm hàng</th><th>Claim</th><th>OTIF Risk</th><th>Quality Risk</th><th>Owner</th><th>RAG</th></tr></thead>
      <tbody>
        <tr><td><strong>Samsung</strong></td><td>GS5/GS6</td><td>Hộp Samsung</td><td>{rag_badge("Pending","rpend")}</td><td>{rag_badge("Pending","rpend")}</td><td>{rag_badge("Pending","rpend")}</td><td>Mr Lam / Mr Mạnh + Mr Đức</td><td>{rag_badge("Pending","rpend")}</td></tr>
        <tr><td><strong>Canon</strong></td><td>GS1/GS5</td><td>Máy in/văn phòng</td><td>{rag_badge("Pending","rpend")}</td><td>{rag_badge("Pending","rpend")}</td><td>{rag_badge("Pending","rpend")}</td><td>Mr Hào / Mr Lam + Mr Đức</td><td>{rag_badge("Pending","rpend")}</td></tr>
        <tr><td><strong>Brother</strong></td><td>GS1/GS5</td><td>Máy in/văn phòng</td><td>{rag_badge("Pending","rpend")}</td><td>{rag_badge("Yellow","ryel")}</td><td>{rag_badge("Pending","rpend")}</td><td>Mr Hào / Mr Lam</td><td>{rag_badge("Yellow","ryel")}</td></tr>
      </tbody>
    </table></div>
    {info_box("Issue nhà máy chỉ được nâng priority khi có impact tới khách hàng: claim, trễ giao, hold/release, thiếu WIP, bottleneck công đoạn hoặc rủi ro chất lượng.", "blue")}"""

    # ── 6. Aging / ECN / RMA ──────────────────────────────────
    aging_cards = f"""
    <div class="kpi-grid">
      {kpi_card("Hàng Aging >30 ngày", f'<span class="gray">{PEND_TXT}</span>', "INP-QLCL-001 / INP-KHO-001", "rag-gray")}
      {kpi_card("ECN đang xử lý",      f'<span class="gray">{PEND_TXT}</span>', "INP-QLCL-001", "rag-gray")}
      {kpi_card("RMA / Hàng hoàn trả", f'<span class="gray">{PEND_TXT}</span>', "INP-QLCL-001", "rag-gray")}
      {kpi_card("Recovery before Scrap",f'<span class="gray">{PEND_TXT}</span>', "INP-QLCL-001", "rag-gray")}
    </div>"""

    # ── 7. GSTT Summary ───────────────────────────────────────
    gstt_open   = d_gstt.get("total_issues",      0) if d_gstt else 0
    gstt_escal  = d_gstt.get("escalated",          0) if d_gstt else 0
    gstt_closed = d_gstt.get("closed",             0) if d_gstt else 0

    gstt_sum = f"""
    <div class="kpi-grid">
      {kpi_card("Chờ kiểm chứng",  f'<span class="red">{gstt_open}</span>',  "GSTT Pending",    "rag-red"   if gstt_open else "rag-gray")}
      {kpi_card("Verified OK",     f'<span class="green">{gstt_closed}</span>', "Pass",           "rag-green" if gstt_closed else "rag-gray")}
      {kpi_card("Escalated",       f'<span class="red">{gstt_escal}</span>',  "Cần escalation",  "rag-red"   if gstt_escal else "rag-green")}
    </div>
    <div class="tbl-wrap"><table>
      <thead><tr><th>Site</th><th>Issue cần kiểm</th><th>Owner/PIC</th><th>Check Type</th><th>GSTT PIC</th><th>Due Check</th><th>Status</th></tr></thead>
      <tbody>
        <tr><td>GS1</td><td>Machine Log / WIP / Quality</td><td>Mr Thập / Mr Dũng / Mr Giang</td><td>Field + SOP</td><td>Mr Lâm</td><td>D+6</td><td>{rag_badge("Pending","rpend")}</td></tr>
        <tr><td>GS5</td><td>PROD_LOG / WIP / NCR</td><td>Mr Lam / Mr Luân / Mr Đức</td><td>Field + Data</td><td>Mr Lâm</td><td>D+5</td><td>{rag_badge("Pending","rpend")}</td></tr>
        <tr><td>GS6</td><td>PROD_LOG / OEE / WIP</td><td>Mr Mạnh / Mr Nam / Mr Luân</td><td>Field + Data</td><td>Mr Lâm</td><td>D+5</td><td>{rag_badge("Pending","rpend")}</td></tr>
      </tbody>
    </table></div>"""

    main_content = f"""
    {build_alert_bar(d_bo)}

    <div id="sec1">{section_title("1. Bản đồ sức khỏe nhà máy — CEO/Lead BO nhìn 10 giây (Factory Health Heatmap)")}</div>
    {heatmap}
    <details class="sec-fold">
      <summary>👥 Phân công Owner / Data Provider / Escalation — xem chi tiết</summary>
      <div class="sec-fold-body">{raci_table}</div>
    </details>

    <div id="sec2">{section_title("2. Chỉ số KPI cấp điều hành (Executive KPI Cards)")}</div>
    {exec_cards}

    <details class="sec-fold" id="sec3">
      <summary>📦 3. Dòng chảy tồn kho & WIP / FIFO — chi tiết</summary>
      <div class="sec-fold-body">{inv_cards}</div>
    </details>

    <details class="sec-fold" id="sec4">
      <summary>🏢 4. Rủi ro khách hàng trọng điểm — Samsung / Canon / Brother</summary>
      <div class="sec-fold-body">{cust_table}</div>
    </details>

    <details class="sec-fold" id="sec5">
      <summary>📋 5. Hàng tồn lâu / ECN / RMA / Recovery Before Scrap — chi tiết</summary>
      <div class="sec-fold-body">{aging_cards}</div>
    </details>

    <details class="sec-fold" id="sec6">
      <summary>🛡️ 6. Kiểm chứng độc lập hiện trường — GSTT (Independent Compliance Check)</summary>
      <div class="sec-fold-body">
        <div class="note">GSTT hiện trường thuộc BG/Ban kiểm soát, PIC: Mr Lâm. Vai trò: kiểm chứng độc lập việc Owner/PIC trục BO đã làm thật, đúng, đủ, có bằng chứng và có hiệu quả tại hiện trường.</div>
        {gstt_sum}
      </div>
    </details>
    """
    # Trả về tuple: (sidebar_html, main_col_html)
    # build_html wrap trong tong-bo-layout flex container
    sidebar = build_sidebar(kpi, build_time)
    main_col = f'<div class="main-col">{main_content}</div>'
    return (f'<div class="tong-bo-layout">{sidebar}{main_col}</div>', '')



def build_tab_site(kpi, site, site_name, giam_doc, issue_rows):
    """Tab 2/3/4 — Mini Control Tower cho từng site."""
    # Get aggregate KPIs (no site breakdown yet when data is sparse)
    d_sx   = get(kpi, "01_SAN_XUAT",   "kpis") or {}
    d_otif = get(kpi, "02_KHSX_OTIF",  "kpis") or {}
    d_qlcl = get(kpi, "03_QLCL",       "kpis") or {}
    d_tb   = get(kpi, "04_QLTB_CD",    "kpis") or {}
    d_kho  = get(kpi, "05_KHO",        "kpis") or {}

    # Try site breakdown first, fallback to PEND_TXT
    def site_kpi(dept, *keys, unit="", decimals=1):
        sb = get(kpi, dept, "site_breakdown", site, "kpis")
        if sb is None:
            return PEND_TXT
        val = sb
        for k in keys:
            val = val.get(k) if isinstance(val, dict) else None
            if val is None:
                return PEND_TXT
        return fmt(val, unit, decimals)

    pd_val   = site_kpi("01_SAN_XUAT",  "plan_do_pct_avg", unit="%")
    ng_val   = site_kpi("01_SAN_XUAT",  "ng_pct",          unit="%")
    ncr_val  = site_kpi("03_QLCL",      "total_ncr",        decimals=0)
    dt_val   = site_kpi("04_QLTB_CD",   "total_downtime_hrs", unit="h")
    wip_val  = site_kpi("05_KHO",       "total_wip_qty",    decimals=0)
    otif_val = site_kpi("02_KHSX_OTIF", "otif_pct",         unit="%")

    rag_pd  = rag_color(None) if pd_val == PEND_TXT else rag_color(float(pd_val.replace("%","")) if pd_val != PEND_TXT else None, 95, 85)

    kpi_cards = f"""
    <div class="kpi-grid-5">
      {kpi_card("Plan/DO",
                f'<span class="{"gray" if pd_val == PEND_TXT else "blue"}">{pd_val}</span>',
                f"Target ≥95% | {giam_doc}", "rag-gray" if pd_val == PEND_TXT else "rag-blue",
                f"<div class='warn-box'>Cần PROD_LOG {site} đúng template. Target ≥95% Plan/DO Adherence.</div>")}
      {kpi_card("OTIF",
                f'<span class="{"gray" if otif_val == PEND_TXT else "blue"}">{otif_val}</span>',
                f"Delivery Risk | {giam_doc}", "rag-gray",
                f"<div class='info-box'>Operational Owner {site}: {giam_doc}. External Data Provider: Mr Hưng (KHSX-Điều độ).</div>")}
      {kpi_card("OEE/Downtime",
                f'<span class="{"gray" if dt_val == PEND_TXT else "amber"}">{dt_val}</span>',
                "Cần Machine Log", "rag-gray" if dt_val == PEND_TXT else "rag-amber",
                "<div class='warn-box'>Cần Machine Log có start/end, reason code, machine mapping.</div>")}
      {kpi_card("Quality/NCR",
                f'<span class="{"gray" if ncr_val == PEND_TXT else "blue"}">{ncr_val}</span>',
                "Tổng NCR", "rag-gray" if ncr_val == PEND_TXT else "rag-blue",
                f"<div class='info-box'>NCR/CAR {site} cần map được với PROD_LOG. Owner: Mr Đức / Mr Giang.</div>")}
      {kpi_card("Kho/WIP/FIFO",
                f'<span class="{"gray" if wip_val == PEND_TXT else "blue"}">{wip_val}</span>',
                "WIP Qty", "rag-gray" if wip_val == PEND_TXT else "rag-blue",
                f"<div class='warn-box'>Cần WIP/FIFO {site}: WO, Customer, Location, Qty, Age, FIFO_Status.</div>")}
    </div>"""

    issue_tbl = issue_table(issue_rows) if issue_rows else '<div class="info-box">Chưa có issue — sẽ tự cập nhật từ 08_BO_CONTROL sheet khi có dữ liệu.</div>'

    return f"""
    {section_title(f"{site_name} — Tháp điều hành mini (Mini Control Tower)")}
    <div class="note">📊 KPI theo site sẽ hiển thị đầy đủ khi PROD_LOG {site} đã qua Cổng kiểm soát dữ liệu (DQG). Hiện đang dùng dữ liệu tổng hợp (aggregate) + {PEND_TXT}.</div>
    {kpi_cards}

    <div class="card">
      <div class="card-title">{site} Issue / Owner Action — bảng theo dõi</div>
      {issue_tbl}
    </div>

    <div class="grid-2">
      {svg_trend(f"Plan/DO Trend — {site}", f"{site} sẽ hiển thị trend theo tháng/tuần/ca khi có đủ dữ liệu PROD_LOG.")}
      <div class="card">
        <div class="card-title">Quality Pareto — {site}</div>
        {pareto_row("TECH", 49.9, "amber")}
        {pareto_row("PRODUCTION", 48.9, "amber")}
        {pareto_row("MATERIAL", 1.1, "green")}
        {info_box(f"{site} Pareto sẽ cập nhật khi NCR/CAR có dữ liệu thực qua DQG.")}
      </div>
    </div>"""


def build_tab_kpi_pic(kpi):
    """Tab 5 — KPI/PIC Performance."""
    owner_rows = [
        ("Mr Hào",   "GĐNM GS1",              "Plan/DO GS1, OTIF execution",      "≥95%", "Trial DQG",  "rpend"),
        ("Mr Lam",   "GĐNM GS5",              "Plan/DO GS5, OTIF Samsung",         "≥95%", "Pending",    "rpend"),
        ("Mr Mạnh",  "GĐNM GS6 / GĐCN",       "Plan/DO GS6, Process/Capacity",    "≥95%", "Pending",    "rpend"),
        ("Mr Hiệu",  "GĐSX 1A GSQV/GS5",      "Data/action SX xưởng 1A",         "Đúng hạn", "Pending","rpend"),
        ("Mr Trường","GĐSX 1B/GS5 và GS6",    "Data/action SX 1B + GS6",          "Đúng hạn", "Pending","rpend"),
        ("Mr Đức",   "Quality Lead / TP QLCL", "NCR/CAR completeness + QLCL QV",  "100%", "Partial",    "ryel"),
        ("Mr Giang", "TPCL GS1",               "NCR/CAR GS1 + Hold-Release",       "Đủ field","Trial",  "ryel"),
        ("Mr Phương","TPCN GS1",               "Process/capacity GS1",             "Master đủ","Pending","rpend"),
        ("Mr Quyết", "TPCN GSQV",              "Process/capacity GSQV",            "Master đủ","Pending","rpend"),
        ("Mr Thập",  "TP QLTB&CĐ GS1",         "Machine Log/Downtime GS1",         "Daily","Blocked",   "rred"),
        ("Mr Nam",   "TP QLTB&CĐ GSQV",         "Machine Log/Downtime GS5/GS6",    "Daily","Blocked",   "rred"),
        ("Mr Dũng",  "TP Kho GS1",              "WIP/FIFO/Staging GS1",            "Daily","Pending",    "rpend"),
        ("Mr Luân",  "TP Kho GSQV",             "WIP/FIFO/Staging GS5/GS6",       "Daily","Pending",    "rpend"),
    ]

    owner_trs = ""
    for owner, role, kpi_desc, target, actual, rag in owner_rows:
        pct = {"Trial": 30, "Partial": 50, "Blocked": 0, "Pending": 0}.get(actual, 0)
        color = {"rred": "red", "ryel": "amber", "rgreen": "green"}.get(rag, "gray")
        owner_trs += f"""<tr>
          <td><strong>{owner}</strong></td><td>{role}</td><td>{kpi_desc}</td>
          <td>{target}</td>
          <td>{actual}</td>
          <td>{progress_bar(pct, color)}</td>
          <td>{rag_badge(actual, rag)}</td>
        </tr>"""

    bo_lead_rows = [
        ("Issue Governance",  "Issue có owner/action/deadline/close condition đầy đủ", "≥95%", "Pending"),
        ("Escalation",        "Issue Red được escalation đúng hạn",                   "≥95%", "Pending"),
        ("Action Closure",    "Action đến hạn được đóng hoặc có lý do/escalation",    "≥90%", "Pending"),
        ("Data Governance",   "DQG pass rate / dashboard update đúng chu kỳ",         "≥80%", "Pending"),
        ("GSTT Alignment",    "Action Done được GSTT xác nhận Pass/Pass with remark", "≥85%", "Pending"),
    ]
    bo_trs = ""
    for grp, kpi_desc, target, actual in bo_lead_rows:
        bo_trs += f"<tr><td><strong>{grp}</strong></td><td>{kpi_desc}</td><td>{target}</td><td>{actual}</td><td>{rag_badge(actual,'rpend')}</td></tr>"

    return f"""
    {section_title("Chỉ số hiệu suất / Owner vận hành — Cơ cấu BO (KPI/PIC Performance)")}
    <div class="warn-box"><strong>Nguyên tắc:</strong> Tab này phục vụ review Mentor 3 tháng/6 tháng. Không dùng kết luận nhân sự chính thức nếu chưa có dữ liệu qua DQG và evidence.</div>
    <div class="info-box"><strong>Role fix V34:</strong> Operational Owner: GĐNM theo site. Mr Hưng (KHSX-Điều độ): External Data Provider cho OTIF. Ms Ly: External Escalation. Mr Thành: BO Lead Governance Review — không đưa vào operational ranking.</div>

    <details class="drill" open><summary>A. Owner/PIC vận hành thuộc trục BO</summary>
    <div class="drill-body tbl-wrap">
    <table>
      <thead><tr><th>Owner/PIC</th><th>Vai trò</th><th>KPI</th><th>Target</th><th>Actual</th><th>% Hoàn thành</th><th>RAG</th></tr></thead>
      <tbody>{owner_trs}</tbody>
    </table>
    </div></details>

    <details class="drill" open><summary>B. BO Lead / Governance Owner — Mr Thành</summary>
    <div class="drill-body">
    <div class="info-box">Mr Thành không chấm theo KPI QLTB&CĐ trực tiếp. KPI tập trung vào chất lượng điều phối, dashboard governance, gắn owner/action/deadline, escalation, closure và mức độ khớp giữa dashboard với hiện trường sau GSTT check.</div>
    <div class="tbl-wrap"><table>
      <thead><tr><th>Nhóm KPI</th><th>KPI Lead BO</th><th>Target</th><th>Actual</th><th>RAG</th></tr></thead>
      <tbody>{bo_trs}</tbody>
    </table></div>
    </div></details>

    <details class="drill"><summary>C. External Data Provider / Escalation — chỉ tham chiếu, không chấm điểm BO</summary>
    <div class="drill-body tbl-wrap">
    <table>
      <thead><tr><th>Nhân sự</th><th>Vai trò</th><th>Dữ liệu liên quan</th><th>Cách hiển thị</th></tr></thead>
      <tbody>
        <tr><td><strong>Mr Hưng</strong> (KHSX-Điều độ)</td><td>External Data Provider</td><td>OTIF / Delivery Risk input</td><td>Chỉ tham chiếu; không đưa vào BO ranking</td></tr>
        <tr><td><strong>Ms Ly</strong></td><td>External Escalation Owner</td><td>Escalation khi thiếu dữ liệu OTIF</td><td>Chỉ hiện trong ghi chú OTIF/Escalation</td></tr>
      </tbody>
    </table>
    </div></details>

    <div class="grid-2">
      {svg_trend("KPI Trend — toàn bộ Owner/PIC (demo)")}
      {svg_trend("BO Lead Governance Trend (demo)")}
    </div>"""


def build_tab_gstt(kpi):
    """Tab 6 — GSTT / Compliance."""
    d_gstt = get(kpi, "06_GSTT", "kpis") or {}
    total  = d_gstt.get("total_issues", 18)
    ok     = d_gstt.get("closed",        0)
    esc    = d_gstt.get("escalated",      0)

    gstt_cards = f"""
    <div class="kpi-grid-5">
      {kpi_card("Chờ kiểm chứng", f'<span class="red">{total}</span>', "Pending GSTT Check", "rag-red",
                "<table><tr><th>Site</th><th>Nhóm issue</th><th>Số việc</th></tr>"
                "<tr><td>GS1</td><td>Machine Log / WIP / Quality</td><td>5</td></tr>"
                "<tr><td>GS5</td><td>PROD_LOG / WIP / NCR</td><td>7</td></tr>"
                "<tr><td>GS6</td><td>PROD_LOG / OEE / WIP</td><td>6</td></tr></table>")}
      {kpi_card("Đạt kiểm chứng", f'<span class="green">{ok}</span>', "Verified OK", "rag-green" if ok > 0 else "rag-gray",
                "<div class='info-box'>Pass khi action hoàn thành đúng hạn, evidence đủ, GSTT đối chiếu hiện trường đạt.</div>")}
      {kpi_card("Đạt có lưu ý",  '<span class="amber">0</span>', "Pass with remark", "rag-amber",
                "<div class='info-box'>Yellow khi có làm nhưng evidence chưa đủ mạnh hoặc cần kiểm lại.</div>")}
      {kpi_card("Không đạt",     '<span class="red">0</span>',   "Not Pass",          "rag-red",
                "<div class='warn-box'>Red khi owner báo done nhưng hiện trường không đạt hoặc issue ảnh hưởng khách hàng trọng điểm.</div>")}
      {kpi_card("Mở lại issue",  '<span class="red">0</span>',   "Re-open",           "rag-red",
                "<div class='warn-box'>Re-open khi issue đã đóng trên dashboard nhưng GSTT phát hiện tái diễn.</div>")}
    </div>"""

    gstt_heatmap = f"""
    <div style="overflow-x:auto">
    <div class="gstt-grid">
      <div class="gstt-hdr">Site</div>
      <div class="gstt-hdr">Thực hiện/Đúng hạn<br><span style="font-weight:400;opacity:.8">(Action/Deadline)</span></div>
      <div class="gstt-hdr">Bằng chứng<br><span style="font-weight:400;opacity:.8">(Evidence)</span></div>
      <div class="gstt-hdr">Hiện trường/Quy trình<br><span style="font-weight:400;opacity:.8">(Field/SOP)</span></div>
      <div class="gstt-hdr">Tái diễn<br><span style="font-weight:400;opacity:.8">(Recurrence)</span></div>
      <div class="gstt-hdr">Tổng thể<br><span style="font-weight:400;opacity:.8">(Overall)</span></div>

      <div class="gstt-cell bg-gray"><strong>GS1</strong>Mr Hào</div>
      <div class="gstt-cell bg-amber"><strong>62</strong>Need evidence</div>
      <div class="gstt-cell bg-amber"><strong>Pending</strong>Log/WIP</div>
      <div class="gstt-cell bg-amber"><strong>Need check</strong>Field</div>
      <div class="gstt-cell bg-pend"><strong>Unknown</strong>No log</div>
      <div class="gstt-cell bg-amber"><strong>Yellow</strong>Monitor</div>

      <div class="gstt-cell bg-gray"><strong>GS5</strong>Mr Lam</div>
      <div class="gstt-cell bg-red"><strong>48</strong>Data risk</div>
      <div class="gstt-cell bg-red"><strong>Weak</strong>PROD_LOG</div>
      <div class="gstt-cell bg-pend"><strong>Pending</strong>Need field</div>
      <div class="gstt-cell bg-pend"><strong>Unknown</strong>No check</div>
      <div class="gstt-cell bg-red"><strong>Red</strong>Action</div>

      <div class="gstt-cell bg-gray"><strong>GS6</strong>Mr Mạnh</div>
      <div class="gstt-cell bg-red"><strong>42</strong>Data risk</div>
      <div class="gstt-cell bg-red"><strong>Weak</strong>Need split</div>
      <div class="gstt-cell bg-pend"><strong>Pending</strong>Need field</div>
      <div class="gstt-cell bg-pend"><strong>Unknown</strong>No check</div>
      <div class="gstt-cell bg-red"><strong>Red</strong>Action</div>
    </div></div>"""

    ranking_rows = [
        ("Mr Hào",   "GĐNM GS1",          "Plan/DO, OTIF, action closure",       "GS1",      72, "amber", "→"),
        ("Mr Lam",   "GĐNM GS5",          "Plan/DO, OTIF, Samsung impact",       "GS5",      48, "red",   "↓"),
        ("Mr Hiệu",  "GĐSX 1A GSQV/GS5", "Data, action SX 1A",                 "GS5/1A",    0, "gray",  "—"),
        ("Mr Trường","GĐSX 1B/GS5,GS6",  "Data, action SX 1B+GS6",             "GS5/GS6",  45, "red",   "↓"),
        ("Mr Mạnh",  "GĐNM GS6 / GĐCN",  "GS6 exec, process/capacity",         "GS6/GSBB", 42, "red",   "↓"),
        ("Mr Đức",   "Quality Lead",      "NCR/CAR, quality governance",         "GSQV/GSBB",60,"amber",  "→"),
        ("Mr Giang", "TPCL GS1",          "NCR/CAR GS1, Hold-Release",           "GS1",      58, "amber", "→"),
        ("Mr Phương","TPCN GS1",          "Process/capacity GS1",                "GS1",       0, "gray",  "—"),
        ("Mr Quyết", "TPCN GSQV",         "Process/capacity GSQV",               "GSQV",      0, "gray",  "—"),
        ("Mr Thập",  "TP QLTB&CĐ GS1",    "Machine Log, downtime, CMMS",         "GS1",      35, "red",   "↓"),
        ("Mr Nam",   "TP QLTB&CĐ GSQV",   "Machine Log GS5/GS6",                "GS5/GS6",  35, "red",   "↓"),
        ("Mr Dũng",  "TP Kho GS1",        "WIP/FIFO/Staging GS1",               "GS1",       0, "gray",  "—"),
        ("Mr Luân",  "TP Kho GSQV",       "WIP/FIFO/Staging GS5/GS6",           "GS5/GS6",  40, "red",   "↓"),
    ]

    rag_map = {"red": "rred", "amber": "ryel", "green": "rgreen", "gray": "rpend"}
    rag_css = {"red": "#dc2626", "amber": "#d97706", "green": "#16a34a", "gray": "#9ca3af"}
    rank_trs = ""
    for owner, role, check, scope, score, rag, trend in ranking_rows:
        score_txt = str(score) if score > 0 else "Pending"
        score_w   = score if score > 0 else 0
        rag_badge_html = rag_badge(score_txt, rag_map.get(rag, "rpend"))
        score_bar = f'<div class="score-bg"><div class="score-fill" style="width:{score_w}%;background:{rag_css.get(rag,"#9ca3af")}"></div></div> {score_txt}'
        rank_trs += f"<tr><td><strong>{owner}</strong></td><td>{role}</td><td>{check}</td><td>{scope}</td><td>{score_bar}</td><td>{trend}</td><td>{rag_badge_html}</td></tr>"

    checklist_rows = [
        ("WIP / BTP không vượt WIP Cap",              "WIP Cap theo site"),
        ("FIFO được thực hiện đúng",                  "Lot cũ xuất trước"),
        ("Kho không bị overflow / lấn lối đi",        "Lối đi ≥ 0.8m"),
        ("Hàng Aging >30 ngày có nhãn cảnh báo",      "Nhãn vàng >30d, đỏ >60d"),
        ("RMA / hàng hoàn trả có khu vực tách biệt",  "Khu RMA tách riêng, có nhãn"),
        ("ECN đã được truyền thông đến kho / SX",      "Biên bản ECN có chữ ký kho + SX"),
        ("Thiết bị PCCC trong kho đủ / đúng vị trí",  "Theo quy định PCCC"),
        ("Recovery before Scrap đang thực hiện",       "Có kế hoạch phục hồi"),
    ]
    check_trs = ""
    for item, std in checklist_rows:
        check_trs += f"<tr><td>{item}</td><td>{std}</td><td style='color:#2563eb'>Chưa kiểm tra</td><td>—</td><td>{rag_badge('Pending','rpend')}</td><td>Chờ data</td></tr>"

    return f"""
    {section_title("Giám sát thực tế / Tuân thủ — Kiểm chứng độc lập (GSTT / Compliance)")}
    <div class="note">Tab này dành riêng cho GSTT hiện trường do Mr Lâm phụ trách. GSTT không thay Owner/PIC xử lý, chỉ xác minh độc lập: action có làm thật không, evidence có đủ không, hiện trường có tuân thủ không, issue có tái diễn không.</div>
    {gstt_cards}

    {section_title("1. Bản đồ cảnh báo GSTT theo nhà máy")}
    <div class="card">{gstt_heatmap}</div>

    {section_title("2. Biểu đồ điểm và xu hướng")}
    <div class="grid-2">
      {svg_trend("Xu hướng điểm GSTT theo Owner — 6 tuần (demo)")}
      <div class="card">
        <div class="card-title">Điểm GSTT theo site — demo</div>
        {pareto_row("GS1", 62, "amber")}
        {pareto_row("GS5", 48, "red")}
        {pareto_row("GS6", 42, "red")}
        <details class="drill"><summary>Cách tính điểm GSTT</summary><div class="drill-body">
        <table><tr><th>Nhóm điểm</th><th>Trọng số</th><th>GSTT kiểm</th></tr>
        <tr><td>Action/Deadline</td><td>30%</td><td>Owner có làm đúng cam kết, đúng hạn không</td></tr>
        <tr><td>Evidence</td><td>25%</td><td>Ảnh/file/log có đủ và khớp hiện trường không</td></tr>
        <tr><td>Field/SOP</td><td>25%</td><td>FIFO, WIP, Machine Log, NCR/CAR có làm thật không</td></tr>
        <tr><td>Effectiveness</td><td>20%</td><td>Issue có cải thiện, không tái diễn không</td></tr></table>
        </div></details>
      </div>
    </div>

    {section_title("3. Owner/PIC Compliance Ranking")}
    <div class="card">
      <div class="card-title">Owner/PIC Compliance Ranking — đầy đủ Owner/PIC vận hành</div>
      <div class="info-box">Không bao gồm Mr Thành (BO Lead Governance Review riêng), Mr Hưng và Ms Ly (External Provider/Escalation).</div>
      <div class="tbl-wrap"><table>
        <thead><tr><th>Owner/PIC</th><th>Vai trò</th><th>Nhóm kiểm chứng</th><th>Site/Phạm vi</th><th>Điểm GSTT</th><th>Trend</th><th>RAG</th></tr></thead>
        <tbody>{rank_trs}</tbody>
      </table></div>
    </div>

    {section_title("4. Verification Queue theo nhà máy")}
    <div class="grid-3">
      <div class="card">
        <div class="card-title">GS1 – Verification Queue</div>
        {pareto_row("Pending", 60, "amber")}
        {pareto_row("Red", 20, "red")}
      </div>
      <div class="card">
        <div class="card-title">GS5 – Verification Queue</div>
        {pareto_row("Pending", 80, "red")}
        {pareto_row("Red", 60, "red")}
      </div>
      <div class="card">
        <div class="card-title">GS6 – Verification Queue</div>
        {pareto_row("Pending", 70, "red")}
        {pareto_row("Red", 60, "red")}
      </div>
    </div>

    {section_title("5. Kho / Inventory / PCCC – GSTT Compliance Checklist")}
    <details class="drill"><summary>📦 Kho / Inventory / Overflow / PCCC – GSTT Compliance Checklist</summary>
    <div class="drill-body tbl-wrap">
    <table>
      <thead><tr><th>Hạng mục kiểm tra</th><th>Tiêu chuẩn</th><th>Kết quả GSTT</th><th>Evidence</th><th>Status</th><th>Ghi chú</th></tr></thead>
      <tbody>{check_trs}</tbody>
    </table>
    </div></details>

    {section_title("6. Cảnh báo và Escalation")}
    <div class="grid-2">
      <div class="card">
        <div class="card-title">Compliance Alert Board</div>
        <table><thead><tr><th>Cảnh báo</th><th>Điều kiện</th><th>Escalation</th></tr></thead>
        <tbody>
          <tr><td>{rag_badge("Red","rred")}</td><td>Not Pass, Re-open, Overdue, ảnh hưởng khách hàng trọng điểm</td><td>BO Lead + CEO nếu critical</td></tr>
          <tr><td>{rag_badge("Yellow","ryel")}</td><td>Pass with remark, cần evidence, action sát hạn</td><td>Owner + BO Lead</td></tr>
          <tr><td>{rag_badge("Green","rgreen")}</td><td>Pass, đủ evidence, hiện trường đạt, không tái diễn</td><td>Close verification</td></tr>
        </tbody></table>
      </div>
      <div class="card">
        <div class="card-title">GSTT Output & Tần suất</div>
        <table><thead><tr><th>Output</th><th>Tần suất</th><th>Người cập nhật</th></tr></thead>
        <tbody>
          <tr><td>GSTT Check Log</td><td>Daily/Weekly</td><td>Mr Lâm / GSTT</td></tr>
          <tr><td>Evidence link</td><td>Theo từng check</td><td>GSTT + Owner/PIC</td></tr>
          <tr><td>Owner score trend</td><td>Weekly</td><td>BO dashboard</td></tr>
          <tr><td>Escalation list</td><td>Khi có Red/Re-open</td><td>BO Lead / CEO</td></tr>
        </tbody></table>
      </div>
    </div>"""



def extract_issue_rows(kpi, site=None):
    d_bo = get(kpi, "08_BO_CONTROL")
    if not d_bo:
        return []
    rows = {
        "GS1": [
            ("Plan/DO GS1 can xac nhan", "Yellow", "Mr Hao",  "Review WO/may/ca",   "D+3", "Co root cause"),
            ("Machine Log GS1 chua du",  "Red",    "Mr Thap", "Gui downtime log",   "D+5", "Du start/end/reason"),
            ("WIP/FIFO GS1 chưa có DL",  "Pending","Mr Dung", "Gửi WIP/FIFO file",  "D+5", "Map OTIF/Customer"),
        ],
        "GS5": [
            ("PROD_LOG GS5 thieu ORDER_ID", "Red",    "Mr Lam",  "Gui dung template","D+5", "Qua DQG"),
            ("WIP/FIFO GS5 chưa có DL",     "Red",    "Mr Luan", "Gửi WIP/FIFO",    "D+5", "Map OTIF"),
            ("Machine Log GS5 chua co",     "Red",    "Mr Nam",  "Gui downtime log", "D+5", "start/end/reason"),
        ],
        "GS6": [
            ("PROD_LOG GS6 tach khoi GS5",  "Red",    "Mr Manh", "Gui file GS6",    "D+5", "Qua DQG"),
            ("Machine Log GS6 chua co",     "Red",    "Mr Nam",  "Gui downtime log", "D+5", "start/end/reason"),
            ("WIP/FIFO GS6 chưa có DL",     "Pending","Mr Luan", "Gửi WIP/FIFO",    "D+5", "Map OTIF"),
        ],
    }
    return rows.get(site, [])


def build_html(kpi_full, dqg_data, build_time):
    kpi      = kpi_full.get("departments", kpi_full)
    summary  = kpi_full.get("summary", {})
    official = summary.get("kpi_official", 0)
    total    = summary.get("total_depts", 8)

    if official >= total:
        overall_label = "OPERATIONAL"
    elif official >= total - 1:
        overall_label = "NEAR OPERATIONAL"
    else:
        overall_label = "PARTIAL DATA"

    dqg_summary = dqg_data.get("summary", {})
    dqg_pass    = dqg_summary.get("PASS", 0)
    dqg_skip    = dqg_summary.get("SKIP", 0)

    t1 = build_tab_tong_bo(kpi, dqg_data, build_time)
    t2 = build_tab_site(kpi, "GS1", "GSHN / GS1", "Mr Hao",  extract_issue_rows(kpi, "GS1"))
    t3 = build_tab_site(kpi, "GS5", "GSQV / GS5", "Mr Lam",  extract_issue_rows(kpi, "GS5"))
    t4 = build_tab_site(kpi, "GS6", "GSQV / GS6", "Mr Manh", extract_issue_rows(kpi, "GS6"))
    t5 = build_tab_kpi_pic(kpi)
    t6 = build_tab_gstt(kpi)

    warn = ""
    if official < total:
        n = total - official
        warn = (f'<div class="warn-banner">'
                f'\u26a0\ufe0f {n}/{total} b&#7897; ph&#7853;n ch&#432;a &#273;&#7841;t C&#7893;ng DL (DQG). '
                f'KPI ch&#237;nh th&#7913;c sau DQG PASS.</div>')

    badge_bg  = "#14532d" if official == total else "#92400e"
    badge_clr = "#d1fae5" if official == total else "#fef3c7"

    return (
        '<!DOCTYPE html>\n'
        '<html lang="vi">\n'
        '<head>\n'
        '<meta charset="UTF-8">\n'
        '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
        f'<title>BO Control Tower - GSBB</title>\n'
        f'<style>{CSS}</style>\n'
        '</head>\n<body>\n'
        + warn +
        f'<div class="hdr">\n'
        f'  <div class="hdr-row">\n'
        f'    <div class="gs-brand">\n'
        '      <img class=\"gs-svg" src="data:image/jpeg;base64,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" alt="Goldsun">\n'
        f'      <div class="gs-txt"><div class="gs-name">GOLDSUN</div>'
        f'      <div class="gs-sub">GSP NEXT 30</div></div>\n'
        f'    </div>\n'
        f'    <div class="hdr-vline"></div>\n'
        f'    <div class="hdr-titles">\n'
        f'      <div class="gsp-pill">&#11088; GSP NEXT 30 &mdash; BO Control Tower</div>\n'
        f'      <h1>Dashboard &#272;i&#7873;u h&#224;nh v&#7853;n h&#224;nh GSBB</h1>\n'
        f'      <div class="sub">'
        f'KPI ch&#237;nh th&#7913;c: {official}/{total} b&#7897; ph&#7853;n &#273;&#7841;t C&#7893;ng DL (DQG)&nbsp;|&nbsp;'
        f'C&#7853;p nh&#7853;t: {build_time}&nbsp;|&nbsp;'
        f'Ngu&#7891;n: Google Sheets &rarr; DQG &rarr; KPI&nbsp;|&nbsp;Auto-build: GitHub Actions'
        f'      </div>\n'
        f'    </div>\n'
        f'    <div class="gsp-badge-30"><img src="data:image/jpeg;base64,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" alt="GSP NEXT 30" title="GSP NEXT 30"></div>\n'
        f'  </div>\n'
        f'  <div class="badges">\n'
        f'    <span class="bdg" style="background:{badge_bg};color:{badge_clr}">'
        f'      {overall_label} &mdash; {official}/{total} PASS</span>\n'
        f'    <span class="bdg bdg-info">C&#7893;ng DL (DQG): {dqg_pass} PASS | {dqg_skip} SKIP</span>\n'
        f'    <span class="bdg bdg-warn">D&#7919; li&#7879;u th&#7917; nghi&#7879;m (Trial) &mdash; qua DQG m&#7899;i l&#224; KPI ch&#237;nh th&#7913;c</span>\n'
        f'  </div>\n'
        f'  <div class="hdr-tagline">TH&#431;&#416;NG HI&#7878;U M&#7898;I &middot; H&#7878; TH&#7888;NG M&#7898;I &middot; T&#431; DUY M&#7898;I</div>\n'
        f'</div>\n'
        '<input type="radio" name="tab" id="t1" checked>\n'
        '<input type="radio" name="tab" id="t2">\n'
        '<input type="radio" name="tab" id="t3">\n'
        '<input type="radio" name="tab" id="t4">\n'
        '<input type="radio" name="tab" id="t5">\n'
        '<input type="radio" name="tab" id="t6">\n'
        '<nav class="nav">\n'
        '  <label for="t1">&#127968; <span class=\"tab-full\">T&#7893;ng BO</span><span class=\"tab-short\">BO</span></label>\n'
                '  <label for="t2">&#127981; <span class=\"tab-full\">GSHN / GS1</span><span class=\"tab-short\">GS1</span></label>\n'
        '  <label for="t3">&#127959; <span class=\"tab-full\">GSQV / GS5</span><span class=\"tab-short\">GS5</span></label>\n'
        '  <label for="t4">&#127959; <span class=\"tab-full\">GSQV / GS6</span><span class=\"tab-short\">GS6</span></label>\n'
        '  <label for="t5">&#128202; <span class=\"tab-full\">Ch&#7881; s&#7889; / Owner (KPI/PIC)</span><span class=\"tab-short\">KPI/PIC</span></label>\n'
        '  <label for="t6">&#128737;&#65039; <span class=\"tab-full\">Gi&#225;m s&#225;t tu&#226;n th&#7911; (GSTT)</span><span class=\"tab-short\">GSTT</span></label>\n'
        '</nav>\n'
        # Tab 1: #c1 IS the grid container (panel-sb layout)
        # t1 is a tuple: (sidebar_html, main_col_html)
        + f'<div id="c1" class="panel">{t1[0]}{t1[1]}</div>\n'
        + f'<div id="c2" class="panel"><div class="tab-pad">{t2}</div></div>\n'
        + f'<div id="c3" class="panel"><div class="tab-pad">{t3}</div></div>\n'
        + f'<div id="c4" class="panel"><div class="tab-pad">{t4}</div></div>\n'
        + f'<div id="c5" class="panel"><div class="tab-pad">{t5}</div></div>\n'
        + f'<div id="c6" class="panel"><div class="tab-pad">{t6}</div></div>\n'
        + '</body>\n</html>\n'
    )


def main():
    import json, os
    from datetime import datetime, timezone

    base = os.path.dirname(os.path.abspath(__file__))
    logs = os.path.join(base, '..', 'logs')
    docs = os.path.join(base, '..', 'docs')

    kpi_path = os.path.join(logs, 'kpi_output.json')
    dqg_path = os.path.join(logs, 'dqg_results.json')
    out_path = os.path.join(docs, 'index.html')

    with open(kpi_path, 'r', encoding='utf-8') as f:
        kpi_full = json.load(f)
    with open(dqg_path, 'r', encoding='utf-8') as f:
        dqg_data = json.load(f)

    build_time = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    html = build_html(kpi_full, dqg_data, build_time)

    os.makedirs(docs, exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'[dashboard_builder] Built: {out_path} ({len(html):,} bytes)')


if __name__ == '__main__':
    main()
