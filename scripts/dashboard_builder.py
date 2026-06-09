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
.gsp-badge-30 img{height:120px;width:120px;display:block;object-fit:contain;
                  border:none;outline:none;background:transparent}
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
