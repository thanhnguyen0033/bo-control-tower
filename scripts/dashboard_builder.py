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
.gsp-badge-30 img{height:100px;width:100px;display:block;object-fit:cover;
                  border-radius:8px;border:none;outline:none;
                  filter:drop-shadow(0 2px 6px rgba(0,0,0,.4))}
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
        f'    <div class="gsp-badge-30"><img src="data:image/png;base64,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" alt="GSP NEXT 30" title="GSP NEXT 30"></div>\n'
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
