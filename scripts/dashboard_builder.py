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
