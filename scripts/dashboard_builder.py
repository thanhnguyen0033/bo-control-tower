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
        '      <img class=\"gs-svg" src="data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAMCAgMCAgMDAwMEAwMEBQgFBQQEBQoHBwYIDAoMDAsKCwsNDhIQDQ4RDgsLEBYQERMUFRUVDA8XGBYUGBIUFRT/2wBDAQMEBAUEBQkFBQkUDQsNFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBT/wAARCAAwADADASIAAhEBAxEB/8QAGwAAAQUBAQAAAAAAAAAAAAAABQAGBwgJAwH/xAAvEAABBAIABgEDAwMFAAAAAAABAgMEBQYRAAcIEhMhQRQiMRUyMxYjJEJRgYLB/8QAGgEAAQUBAAAAAAAAAAAAAAAABQABAgMGBP/EAC0RAAECBQICCQUAAAAAAAAAAAECEQADBCExBRJBURMiIzJhgbHB8BRicaHx/9oADAMBAAIRAxEAPwDVPhcLiunW5zYuMB5cVuO4u8WMrzGcmngvJV2qZQrXlcCvggKSnfx37+OIqVtDmKJ85NPKVNVgRx5udb+L4JkcjF8UqJ3MPKo+xIh1B0xGI9KDr2iAQfz2ggfgkHh4dNHOa9514tb2t9RwKCREsDFbiwbFE37PGhW1qQSEq2ojtOj6Hr3xmbEr41kxGoqWHLtqKTNVX1FJAc8DuRyWteWbLdHsMpJ+1O9JB7UlPa45xenokxNfJjELimyB6uhTbm3VOjx60urjNJU02gNJdWNEgpOvuVsa+4ngWuvkyZiUz5gTuwCQH/D5gFp1RW11QVBJKBlhYcnLe/izRarhcLhcFo0kLimXXjEeZ5pckrBxfZCVNnQA4f2tyHkNpaJPx7O/+p4ubxF3UhyRic/eVthjLrwh2CVJl1s07/x5SN9ijr32nZSde9KOvYHFcwFSSBHBXyVT6dSEZsR5F/aM4Onq6gYzmWBSLdTcOMqpsMc8skhCItgJC3ChZOggrQ6lOzr+T36B1ofm+d0j+BuxltKgeFoKddltFlqGlPtTi1nQAAG9/wDuuKvZ10N8wGcaj3tculya/tIyFZTjL5LUWbJTvUhhzae17RO1Ao2orIISso4I8guiqNn1K+7zLrs0oGa6b4WMYn3nmhvNhCVBaSlAPbsqToH/AE/njL1mlTKpati9oWnYpw7pvgv1Tc3vwtaB+lVVVp6fpuhcvuSSWALAXYEEWFnByInvpP5w5NzwoMnyO2jR2MdFu7EoHG2FNOvxm/Rcc2o9x2QNgD2lQ164nbgfQUFdi1LDqKiExXVkNpLMeLGQENtIH4AA4IcalCdqQIMyULRLCZinPExAtD1dUuR5HAZh4rka8UsZ6qyFlpjN/QyHkq7CoDv8ni7gR5e3tB/OuOdX1h0Fnd15/pjI4+G2Vn+jQcxejIFdIlFwtpA+/vCFLBSHCnRP+3DeidDNWjIccRMyuVY4Rjdi5ZVGNyK9griKW55SyJf8hYKwCUa96AJ+eCVV0frr5VVTvZ9ay+W1VbC5hYguIyAh1LpeQ2qSPvW0lwlQQR/z88Vdp8+Y/cCUq1C24enh493P3YhwS+qamY5LReYzVBbyYcm1NQ1WNeL6pT31Sow1tfborT69/gjgJa9aeM02PvOysbvYOTs27VK7jE9DEWU1IdbU62pbi3A0G1IQohffo61wFa6N8jbwJ/DjzWfVRIsEWsBj9AY3DkiX9T393f3ObUVDSjr3+PjgpY9Icq1x2/E3PpNnld/PYmWtxZ08WTGmNstqbajqhqHYGkhRI7SFBXvfxwnmQ5XXkBkta/dzd2vzZuDQ4EdVNN9HfPP45ewHabFE5XIizWW2ngyVOJ8PaVfybaJ3+0gggkHhu2PXPhNW3mDcius0T8droVoqEfEHJjMhLKv7J79Et/UI7gdfJGwOBLnQyiBjkCnoOYVtTMuUJxu6WqEzINlDLy3SlIV/AdurSCnekkDXrZ95g9BGN57DyRtV49Ak2EyFJr5SIiVuV7bEVEZTJJUC6haEAnZTpQSfj23axFatR29RIfy5H0LfyP/Z" alt="Goldsun">\n'
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
