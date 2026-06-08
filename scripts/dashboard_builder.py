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
.gsp-badge-30{position:absolute;right:18px;top:8px;bottom:8px;
             display:flex;align-items:center}
.gsp-badge-30 img{height:100%;width:auto;display:block;
                  mix-blend-mode:screen;
                  filter:drop-shadow(0 0 12px rgba(212,160,23,.75))}
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
