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
