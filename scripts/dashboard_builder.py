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
                  filter:drop-shadow(0 0 14px rgba(212,160,23,.85))
                          drop-shadow(0 0 28px rgba(34,197,94,.3))}
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
