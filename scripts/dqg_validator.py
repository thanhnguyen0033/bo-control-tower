"""
dqg_validator.py – Data Quality Gate for BO Control Tower
Reads logs/raw_data.json → validates each dept → writes logs/dqg_results.json
"""
import json, os
from datetime import datetime

RAW_FILE    = "logs/raw_data.json"
OUTPUT_FILE = "logs/dqg_results.json"
os.makedirs("logs", exist_ok=True)

from sheets_config import VALID_SITES

# ── DQG rules per department ───────────────────────────────────────────────────
# required_columns : must not be blank in every data row
# numeric_columns  : must be parseable as float
# site_column      : column whose values must be in VALID_SITES (if present)
DQG_RULES = {
    "01_SAN_XUAT":    {"required": ["Site", "Date", "Plan_Qty", "Actual_Qty", "Owner"],
                       "numeric":  ["Plan_Qty", "Actual_Qty"],
                       "site_col": "Site"},
    "02_KHSX_OTIF":   {"required": ["Site", "Date", "OTIF_Target", "OTIF_Actual", "Owner"],
                       "numeric":  ["OTIF_Target", "OTIF_Actual"],
                       "site_col": "Site"},
    "03_QLCL":        {"required": ["Site", "Date", "NCR_Count", "Owner"],
                       "numeric":  ["NCR_Count"],
                       "site_col": "Site"},
    "04_QLTB_CD":     {"required": ["Site", "Date", "Machine_ID", "Downtime_hrs", "Owner"],
                       "numeric":  ["Downtime_hrs"],
                       "site_col": "Site"},
    "05_KHO":         {"required": ["Site", "Date", "WIP_Qty", "Owner"],
                       "numeric":  ["WIP_Qty"],
                       "site_col": "Site"},
    "06_GSTT":        {"required": ["Site", "Date", "Check_Item", "Result", "Verified_By"],
                       "numeric":  [],
                       "site_col": "Site"},
    "07_CONG_NGHE_SPM": {"required": ["Site", "Date", "SPM_Item", "Status", "Owner"],
                          "numeric":  [],
                          "site_col": "Site"},
    "08_BO_CONTROL":  {"required": ["Issue_ID", "Site", "Description", "Owner", "Deadline"],
                       "numeric":  [],
                       "site_col": "Site"},
}

FAIL_THRESHOLD = 0.10   # >10% bad rows → FAIL

def validate_dept(dept_key, data):
    """Return a validation result dict for one department."""
    status    = data.get("status", "ERROR")
    rows      = data.get("rows", [])
    headers   = data.get("headers", [])
    desc      = data.get("description", dept_key)

    base = {"dept": dept_key, "description": desc,
            "validated_at": datetime.utcnow().isoformat() + "Z",
            "row_count": len(rows)}

    if status == "DEMO":
        return {**base, "dqg_status": "DEMO",
                "message": "Demo mode – not real data"}

    if status in ("ERROR", "NO_DATA"):
        return {**base, "dqg_status": status,
                "message": data.get("error", "No data available")}

    if not rows:
        return {**base, "dqg_status": "NO_DATA",
                "message": "Sheet fetched but 0 data rows found"}

    rules = DQG_RULES.get(dept_key, {"required": [], "numeric": [], "site_col": None})
    req_cols  = rules["required"]
    num_cols  = rules["numeric"]
    site_col  = rules.get("site_col")

    issues = []
    bad_row_count = 0

    for i, row in enumerate(rows, start=1):
        row_issues = []

        # Required columns check
        for col in req_cols:
            val = row.get(col, "").strip()
            if not val:
                row_issues.append(f"Row {i}: '{col}' is blank")

        # Numeric columns check
        for col in num_cols:
            val = row.get(col, "").strip()
            if val:
                try:
                    float(val.replace(",", ""))
                except ValueError:
                    row_issues.append(f"Row {i}: '{col}' = '{val}' is not numeric")

        # Site validation
        if site_col:
            site_val = row.get(site_col, "").strip()
            if site_val and site_val not in VALID_SITES:
                row_issues.append(f"Row {i}: site '{site_val}' not in {VALID_SITES}")

        if row_issues:
            bad_row_count += 1
            issues.extend(row_issues[:3])   # cap per-row issues to avoid noise

    bad_pct = bad_row_count / len(rows) if rows else 0

    if bad_pct == 0:
        dqg_status = "PASS"
        message = f"All {len(rows)} rows passed DQG"
    elif bad_pct <= FAIL_THRESHOLD:
        dqg_status = "WARN"
        message = f"{bad_row_count}/{len(rows)} rows have issues (≤10% threshold)"
    else:
        dqg_status = "FAIL"
        message = f"{bad_row_count}/{len(rows)} rows FAILED DQG (>{FAIL_THRESHOLD*100:.0f}% threshold)"

    return {**base, "dqg_status": dqg_status, "message": message,
            "bad_rows": bad_row_count, "issues_sample": issues[:10]}

def main():
    print("=== BO Control Tower – DQG Validator ===")

    if not os.path.exists(RAW_FILE):
        print(f"ERROR: {RAW_FILE} not found. Run data_fetcher.py first.")
        return

    with open(RAW_FILE, encoding="utf-8") as f:
        raw = json.load(f)

    results = {}
    summary = {"PASS": 0, "WARN": 0, "FAIL": 0,
                "DEMO": 0, "NO_DATA": 0, "ERROR": 0}

    for dept_key, data in raw.items():
        res = validate_dept(dept_key, data)
        results[dept_key] = res
        s = res["dqg_status"]
        summary[s] = summary.get(s, 0) + 1
        icon = {"PASS": "✅", "WARN": "⚠ ", "FAIL": "❌",
                "DEMO": "🔵", "NO_DATA": "⬜", "ERROR": "🔴"}.get(s, "?")
        print(f"  {icon} {dept_key}: {s} — {res['message']}")

    output = {
        "validated_at": datetime.utcnow().isoformat() + "Z",
        "summary": summary,
        "departments": results,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n📊 Summary: {summary}")
    print(f"✅ DQG results saved → {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
