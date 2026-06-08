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
                  border:none;outline:none;
                  filter:drop-shadow(0 0 16px rgba(212,160,23,.7))
                          drop-shadow(0 0 32px rgba(212,160,23,.3))}
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
