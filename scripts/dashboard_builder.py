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
     position:relative;overflow:hidden;
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
.gsp-badge-30{position:absolute;right:16px;top:50%;
             transform:translateY(-50%);display:flex;align-items:center;
             outline:none;text-decoration:none}
.gsp-badge-30 img{height:120px;width:120px;display:block;object-fit:cover;
                  border:none;outline:none;
                  clip-path:circle(50% at 50% 50%);
                  filter:drop-shadow(0 2px 10px rgba(0,0,0,.6))}
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
