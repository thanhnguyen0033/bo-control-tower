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
