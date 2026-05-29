"""
dashboard_builder.py – Build self-contained HTML dashboard from DQG results
Reads logs/dqg_results.json → writes docs/index.html
"""
import json, os
from datetime import datetime

DQG_FILE   = "logs/dqg_results.json"
OUTPUT_DIR = "docs"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "index.html")
os.makedirs(OUTPUT_DIR, exist_ok=True)

STATUS_COLOR = {
    "PASS":    ("#22c55e", "#f0fdf4", "✅"),
    "WARN":    ("#f59e0b", "#fffbeb", "⚠️"),
    "FAIL":    ("#ef4444", "#fef2f2", "❌"),
    "DEMO":    ("#6366f1", "#eef2ff", "🔵"),
    "NO_DATA": ("#94a3b8", "#f8fafc", "⬜"),
    "ERROR":   ("#dc2626", "#fef2f2", "🔴"),
    "PENDING": ("#64748b", "#f8fafc", "⏳"),
}

DEPT_LABEL = {
    "01_SAN_XUAT":      "01 | Sản Xuất – Plan/DO",
    "02_KHSX_OTIF":     "02 | KHSX – OTIF Delivery",
    "03_QLCL":          "03 | Chất Lượng – NCR/CAR",
    "04_QLTB_CD":       "04 | Thiết Bị – Downtime",
    "05_KHO":           "05 | Kho – WIP/FIFO",
    "06_GSTT":          "06 | GSTT – Field Verify",
    "07_CONG_NGHE_SPM": "07 | Công Nghệ – SPM",
    "08_BO_CONTROL":    "08 | BO Control – Issue/Action",
}

def build_html(dqg: dict) -> str:
    validated_at = dqg.get("validated_at", "N/A")
    summary      = dqg.get("summary", {})
    departments  = dqg.get("departments", {})
    build_time   = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    # ── summary counts ──────────────────────────────────────────────────────
    pass_n    = summary.get("PASS", 0)
    warn_n    = summary.get("WARN", 0)
    fail_n    = summary.get("FAIL", 0)
    total_n   = len(departments)
    demo_mode = summary.get("DEMO", 0) == total_n

    overall_color = "#22c55e"
    overall_label = "OPERATIONAL"
    if fail_n > 0:
        overall_color = "#ef4444"; overall_label = "DATA ISSUES DETECTED"
    elif warn_n > 0:
        overall_color = "#f59e0b"; overall_label = "WARNINGS PRESENT"
    if demo_mode:
        overall_color = "#6366f1"; overall_label = "DEMO MODE"

    # ── dept cards ──────────────────────────────────────────────────────────
    cards_html = ""
    for dept_key, res in departments.items():
        s = res.get("dqg_status", "PENDING")
        color, bg, icon = STATUS_COLOR.get(s, ("#64748b", "#f8fafc", "?"))
        label    = DEPT_LABEL.get(dept_key, dept_key)
        message  = res.get("message", "")
        row_count = res.get("row_count", 0)
        bad_rows  = res.get("bad_rows", 0)
        issues   = res.get("issues_sample", [])

        issues_html = ""
        if issues:
            li_items = "".join(f"<li>{i}</li>" for i in issues[:5])
            issues_html = f"<ul style='margin:6px 0 0 16px;font-size:11px;color:#475569'>{li_items}</ul>"

        cards_html += f"""
        <div style="border:1px solid {color};border-left:5px solid {color};
                    background:{bg};border-radius:8px;padding:14px 16px;margin-bottom:12px">
          <div style="display:flex;justify-content:space-between;align-items:center">
            <span style="font-weight:600;font-size:14px;color:#1e293b">{icon} {label}</span>
            <span style="background:{color};color:#fff;padding:2px 10px;
                         border-radius:20px;font-size:12px;font-weight:700">{s}</span>
          </div>
          <div style="font-size:12px;color:#475569;margin-top:5px">{message}</div>
          <div style="font-size:11px;color:#94a3b8;margin-top:3px">
            Rows fetched: {row_count}
            {f'&nbsp;|&nbsp; Bad rows: <b style="color:{color}">{bad_rows}</b>' if bad_rows else ''}
          </div>
          {issues_html}
        </div>"""

    # ── full HTML ───────────────────────────────────────────────────────────
    html = f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>BO Control Tower – GSBB</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
       background:#f1f5f9;color:#1e293b;padding:16px}}
  .container{{max-width:860px;margin:0 auto}}
  .header{{background:linear-gradient(135deg,#1e293b 0%,#334155 100%);
           color:#fff;padding:20px 24px;border-radius:12px;margin-bottom:20px}}
  .header h1{{font-size:20px;font-weight:700;letter-spacing:.3px}}
  .header .sub{{font-size:13px;color:#94a3b8;margin-top:4px}}
  .overall{{text-align:center;padding:16px;border-radius:10px;margin-bottom:20px;
            background:#fff;border:2px solid {overall_color}}}
  .overall .label{{font-size:22px;font-weight:800;color:{overall_color}}}
  .overall .sub{{font-size:13px;color:#64748b;margin-top:4px}}
  .kpi-row{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:20px}}
  .kpi-box{{background:#fff;border-radius:10px;padding:14px;text-align:center;
            box-shadow:0 1px 4px rgba(0,0,0,.07)}}
  .kpi-box .num{{font-size:28px;font-weight:800}}
  .kpi-box .lbl{{font-size:12px;color:#64748b;margin-top:2px}}
  .section-title{{font-size:15px;font-weight:700;color:#334155;
                  margin-bottom:12px;padding-left:4px;
                  border-left:4px solid #3b82f6;padding-left:10px}}
  .footer{{text-align:center;font-size:11px;color:#94a3b8;margin-top:24px}}
  @media(max-width:500px){{.kpi-row{{grid-template-columns:repeat(2,1fr)}}}}
</style>
</head>
<body>
<div class="container">

  <div class="header">
    <h1>🏭 BO Control Tower – GSBB</h1>
    <div class="sub">Data Quality Gate Dashboard &nbsp;|&nbsp;
      Cập nhật: {build_time} &nbsp;|&nbsp;
      DQG Run: {validated_at[:16].replace("T"," ")} UTC</div>
  </div>

  <div class="overall">
    <div class="label">{overall_label}</div>
    <div class="sub">Tình trạng dữ liệu tổng quan {total_n} bộ phận</div>
  </div>

  <div class="kpi-row">
    <div class="kpi-box">
      <div class="num" style="color:#22c55e">{pass_n}</div>
      <div class="lbl">✅ PASS</div>
    </div>
    <div class="kpi-box">
      <div class="num" style="color:#f59e0b">{warn_n}</div>
      <div class="lbl">⚠️ WARN</div>
    </div>
    <div class="kpi-box">
      <div class="num" style="color:#ef4444">{fail_n}</div>
      <div class="lbl">❌ FAIL / ERROR</div>
    </div>
  </div>

  <div class="section-title">Chi tiết DQG từng bộ phận</div>
  {cards_html}

  <div class="footer">
    GSBB BO Control Tower &nbsp;·&nbsp; Auto-built by GitHub Actions &nbsp;·&nbsp;
    Dữ liệu nguồn: Google Sheets &nbsp;·&nbsp; {build_time}
  </div>

</div>
</body>
</html>"""
    return html

def main():
    print("=== BO Control Tower – Dashboard Builder ===")

    if not os.path.exists(DQG_FILE):
        # Fallback: build "pending" page
        print(f"⚠  {DQG_FILE} not found — building pending page")
        dqg = {"validated_at": datetime.utcnow().isoformat()+"Z",
               "summary": {}, "departments": {}}
    else:
        with open(DQG_FILE, encoding="utf-8") as f:
            dqg = json.load(f)

    html = build_html(dqg)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"✅ Dashboard built → {OUTPUT_FILE}  ({len(html):,} chars)")

if __name__ == "__main__":
    main()
