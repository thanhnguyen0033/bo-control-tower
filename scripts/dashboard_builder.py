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
.gsp-badge-30{position:absolute;right:30px;top:6px;bottom:6px;
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
