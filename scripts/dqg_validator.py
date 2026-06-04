"""
dqg_validator.py — GSBB BO Control Tower
Data Quality Gate (DQG): validates raw data before promoting to official KPI.

Rules:
- PASS  = all required columns present + 0 failing rows
- WARN  = ≤10% rows fail validation checks
- FAIL  = >10% rows fail OR required columns missing
- SKIP  = dept is PENDING (Sheet ID not configured yet)
"""

import json
import os
import datetime

LOGS_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")
RAW_DATA_FILE  = os.path.join(LOGS_DIR, "raw_data.json")
DQG_RESULT_FILE = os.path.join(LOGS_DIR, "dqg_results.json")

# ──────────────────────────────────────────────────────────────
# DQG RULES per department
# required_columns : must all exist in the sheet header (Row 3)
# numeric_columns  : these cells must be numeric (or empty = warning only)
# site_column      : if present, value must be in VALID_SITES
# ──────────────────────────────────────────────────────────────
DQG_RULES = {

    "01_SAN_XUAT": {
        # UPDATED 2026-06-04 Session 14: fallback_first_col loses diacritics on Windows mount.
        # Actual column[0] fetched = 'Ngay' (no diacritics) — confirmed from GitHub Actions log.
        # Tab: 01_SX_PLAN_DO | Row3 actual headers (14 cols):
        # Ngay, Ca, Nhà máy, Lệnh SX, Máy / Dây chuyền, Nhóm sản phẩm,
        # SL Kế hoạch, SL Thực tế, SL Lỗi (NG), % Tuân thủ KH, RAG,
        # Hạng mục vấn đề, Ghi chú, Người kiểm tra DL
        "required_columns": [
            "Ngay", "Ca", "Nhà máy", "Lệnh SX",
            "Nhóm sản phẩm", "SL Kế hoạch", "SL Thực tế", "% Tuân thủ KH", "RAG",
        ],
        "numeric_columns": ["SL Kế hoạch", "SL Thực tế", "SL Lỗi (NG)", "% Tuân thủ KH"],
        "site_column": "Nhà máy",
        "date_column": "Ngay",
    },

    "02_KHSX_OTIF": {
        # UPDATED 2026-06-04: Google Sheet uses mixed Vietnamese/English headers.
        # Tab: 02_OTIF_DELIVERY | Row3 actual headers:
        # Ngày cam kết, Actual_Delivery_Date, Nhà máy, Khách hàng, Lệnh SX,
        # SL cam kết, SL thực giao, Đúng hạn?, Số ngày trễ, Rủi ro giao hàng, ...
        "required_columns": [
            "Ngày cam kết", "Nhà máy", "Lệnh SX", "Đúng hạn?",
        ],
        "numeric_columns": ["Số ngày trễ"],
        "site_column": "Nhà máy",
        "date_column": "Ngày cam kết",
    },

    "03_QLCL": {
        # UPDATED 2026-06-04: Google Sheet uses Vietnamese column headers.
        # Tab: 03_QLCL_NCR_CAR | Row3 actual headers:
        # Ngày, Nhà máy, Khách hàng, Mã NCR/CAR, Nhóm lỗi, Mức độ,
        # SL bị ảnh hưởng, Trạng thái, PIC trực tiếp, ...
        "required_columns": [
            "Ngày", "Nhà máy", "Mã NCR/CAR", "Mức độ", "Trạng thái", "PIC trực tiếp",
        ],
        "numeric_columns": ["SL bị ảnh hưởng"],
        "site_column": "Nhà máy",
        "date_column": "Ngày",
    },

    "04_QLTB_CD": {
        # UPDATED 2026-06-04 Session 14: fallback_first_col loses diacritics on Windows mount.
        # Actual column[0] fetched = 'Ngay' (no diacritics) — confirmed from GitHub Actions log.
        # Tab: 04_MACHINE_DOWNTIME | Row3 actual headers (12 cols):
        # Ngay, Ca, Nhà máy, Mã máy, Thời gian dừng (phút), Loại dừng máy,
        # Mã nguyên nhân, Loại sự cố, PIC trực tiếp, Hành động cần làm, Trạng thái, Link bằng chứng
        "required_columns": [
            "Ngay", "Nhà máy", "Mã máy", "Thời gian dừng (phút)", "Trạng thái",
        ],
        "numeric_columns": ["Thời gian dừng (phút)"],
        "site_column": "Nhà máy",
        "date_column": "Ngay",
    },

    "05_KHO": {
        # UPDATED 2026-06-04: Google Sheet uses Vietnamese column headers.
        # Tab: 05_WIP_FIFO_KHO | Row3 actual headers:
        # Ngày, Nhà máy, Khu vực, Lệnh SX, Công đoạn, SL bán thành phẩm,
        # Số ngày tồn, Trạng thái FIFO, PIC trực tiếp, Mức rủi ro, ...
        "required_columns": [
            "Ngày", "Nhà máy", "Lệnh SX", "SL bán thành phẩm", "Trạng thái FIFO",
        ],
        "numeric_columns": ["SL bán thành phẩm", "Số ngày tồn"],
        "site_column": "Nhà máy",
        "date_column": "Ngày",
    },

    "05_KHO_GS1": {
        # Same structure as 05_KHO
        "required_columns": [
            "Ngày", "Nhà máy", "Lệnh SX", "SL bán thành phẩm", "Trạng thái FIFO",
        ],
        "numeric_columns": ["SL bán thành phẩm", "Số ngày tồn"],
        "site_column": "Nhà máy",
        "date_column": "Ngày",
    },

    "06_GSTT": {
        # FIXED 2026-06-04: xlsx row3 col0 = "Check_Date" (verified from xlsx).
        # With headers=3 in GVIZ URL, this will be correctly extracted.
        "required_columns": [
            "Check_Date", "Site", "Category", "Severity", "Status",
        ],
        "numeric_columns": [],
        "site_column": "Site",
        "date_column": "Check_Date",
    },

    "07_CONG_NGHE_SPM": {
        # FIXED 2026-06-04 Session 14: required_columns updated to match actual fetched headers.
        # Actual headers (14 cols) from GitHub Actions log:
        # Ngay, Nhà máy, Khách hàng, Sample_ID, Nhóm sản phẩm, PIC,
        # Due_Date, Ngày hoàn thành, Trạng thái, Leadtime_Days,
        # Redo_Count, Risk_Level, Customer_Impact, Remark
        # NOTE: col0='Ngay' (no diacritics) — fallback_first_col encoding issue.
        "required_columns": [
            "Ngay", "Nhà máy", "Sample_ID", "Trạng thái",
        ],
        "numeric_columns": ["Leadtime_Days", "Redo_Count"],
        "site_column": "Nhà máy",
        "date_column": "Ngay",
    },

    "08_BO_CONTROL": {
        # FIXED 2026-06-04: xlsx row3 col0 = "Issue_Date" (verified from xlsx).
        "required_columns": [
            "Issue_Date", "Source_Module", "Site", "Severity", "Owner", "Status",
        ],
        "numeric_columns": [],
        "site_column": "Site",
        "date_column": "Issue_Date",
    },
}

VALID_SITES = ["GS1", "GS5", "GS6", "GSQV"]


def is_numeric(value: str) -> bool:
    """Return True if value can be parsed as a number (int or float).
    Handles multiple formats:
      - US thousands comma:   '28,800.00' → remove comma → 28800.00 ✓
      - European decimal comma: '109,3'   → if no period, replace comma→period ✓
      - European thousands dot: '1.062'   → already parseable ✓
      - Percentage:            '109,3%'   → strip % then handle comma ✓
    """
    try:
        cleaned = str(value).replace("%", "").strip()
        if not cleaned:
            return False
        # If both comma and period present: comma = thousands separator → remove it
        # e.g. '28,800.00' → '28800.00'
        if "," in cleaned and "." in cleaned:
            cleaned = cleaned.replace(",", "")
        # If only comma (no period): ambiguous, but treat as decimal separator
        # e.g. '109,3' → '109.3'  OR  '1,062' → '1.062' (close enough for DQG)
        elif "," in cleaned:
            cleaned = cleaned.replace(",", ".")
        # Only period: already standard decimal or European thousands e.g. '1.062'
        float(cleaned)
        return True
    except (ValueError, TypeError):
        return False


def validate_dept(dept_key: str, dept_data: dict) -> dict:
    """Run DQG for one department. Returns a result dict."""
    status_from_fetch = dept_data.get("status", "PENDING")

    if status_from_fetch == "PENDING":
        return {
            "dept": dept_key,
            "dqg_status": "SKIP",
            "description": dept_data.get("description", dept_key),
            "row_count": 0,
            "fail_count": 0,
            "warn_count": 0,
            "missing_columns": [],
            "issues": ["Sheet ID not configured yet — Pending DQG"],
            "validated_at": datetime.datetime.utcnow().isoformat() + "Z",
        }

    if status_from_fetch in ("ACCESS_ERROR", "FETCH_ERROR"):
        return {
            "dept": dept_key,
            "dqg_status": "FAIL",
            "description": dept_data.get("description", dept_key),
            "row_count": 0,
            "fail_count": 0,
            "warn_count": 0,
            "missing_columns": [],
            "issues": ["Access denied — verify sheet is set to 'Anyone with link can view' AND Sheet ID is correct"],
            "validated_at": datetime.datetime.utcnow().isoformat() + "Z",
        }

    if status_from_fetch == "NETWORK_ERROR":
        return {
            "dept": dept_key,
            "dqg_status": "SKIP",
            "description": dept_data.get("description", dept_key),
            "row_count": 0,
            "fail_count": 0,
            "warn_count": 0,
            "missing_columns": [],
            "issues": ["Network/DNS error — transient, will retry on next run"],
            "validated_at": datetime.datetime.utcnow().isoformat() + "Z",
        }

    if status_from_fetch == "EMPTY":
        return {
            "dept": dept_key,
            "dqg_status": "SKIP",
            "description": dept_data.get("description", dept_key),
            "row_count": 0,
            "fail_count": 0,
            "warn_count": 0,
            "missing_columns": [],
            "issues": [f"Tab accessible but contains no data rows yet — waiting for input"],
            "validated_at": datetime.datetime.utcnow().isoformat() + "Z",
        }

    rules   = DQG_RULES.get(dept_key, {})
    records = dept_data.get("records", [])
    columns = dept_data.get("columns", [])

    required_cols   = rules.get("required_columns", [])
    numeric_cols    = rules.get("numeric_columns", [])
    site_col        = rules.get("site_column")

    issues          = []
    fail_count      = 0
    warn_count      = 0

    # ── DEBUG: print actual columns for diagnosis ──
    print(f"    🔍 DQG [{dept_key}] actual columns ({len(columns)}): {columns}")
    print(f"    🔍 DQG [{dept_key}] required     ({len(required_cols)}): {required_cols}")

    # ── 1. Check required columns exist ──
    missing_cols = [c for c in required_cols if c not in columns]
    if missing_cols:
        issues.append(f"Missing required columns: {missing_cols}")
        return {
            "dept": dept_key,
            "dqg_status": "FAIL",
            "description": dept_data.get("description", dept_key),
            "row_count": len(records),
            "fail_count": len(records),
            "warn_count": 0,
            "missing_columns": missing_cols,
            "issues": issues,
            "validated_at": datetime.datetime.utcnow().isoformat() + "Z",
        }

    # ── 2. Row-level checks ──
    for i, row in enumerate(records, start=4):   # row 4 = first data row in sheet
        row_issues = []

        # Check numeric columns
        for col in numeric_cols:
            val = row.get(col, "").strip()
            if val and not is_numeric(val):
                row_issues.append(f"Row {i} col '{col}' = '{val}' is not numeric")

        # Check site validity
        if site_col:
            site_val = row.get(site_col, "").strip()
            if site_val and site_val not in VALID_SITES:
                row_issues.append(f"Row {i} col '{site_col}' = '{site_val}' not in {VALID_SITES}")

        if row_issues:
            fail_count += 1
            issues.extend(row_issues)

    # ── 3. Determine DQG status ──
    total_rows = len(records)
    fail_pct   = (fail_count / total_rows * 100) if total_rows > 0 else 0

    if total_rows == 0:
        dqg_status = "WARN"
        issues.append("No data rows found — sheet may be empty")
    elif fail_count == 0:
        dqg_status = "PASS"
    elif fail_pct <= 10:
        dqg_status = "WARN"
    else:
        dqg_status = "FAIL"

    return {
        "dept": dept_key,
        "dqg_status": dqg_status,
        "description": dept_data.get("description", dept_key),
        "row_count": total_rows,
        "fail_count": fail_count,
        "warn_count": warn_count,
        "fail_pct": round(fail_pct, 1),
        "missing_columns": [],
        "issues": issues[:20],   # cap at 20 to keep log readable
        "validated_at": datetime.datetime.utcnow().isoformat() + "Z",
    }


def run_dqg() -> dict:
    """Load raw_data.json, run DQG for all depts, save dqg_results.json."""
    os.makedirs(LOGS_DIR, exist_ok=True)

    if not os.path.exists(RAW_DATA_FILE):
        print("❌ raw_data.json not found — run data_fetcher.py first")
        return {}

    with open(RAW_DATA_FILE, "r", encoding="utf-8") as f:
        raw = json.load(f)

    departments = raw.get("departments", {})

    print(f"\n{'='*60}")
    print(f"GSBB BO Control Tower — Data Quality Gate (DQG)")
    print(f"Timestamp: {datetime.datetime.utcnow().isoformat()}Z")
    print(f"{'='*60}\n")

    results = {}
    for dept_key, dept_data in departments.items():
        result = validate_dept(dept_key, dept_data)
        results[dept_key] = result
        icon = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌", "SKIP": "⏳"}.get(result["dqg_status"], "?")
        print(f"  {icon} [{dept_key}] {result['dqg_status']} — {result['row_count']} rows, {result['fail_count']} failures")
        for issue in result["issues"][:3]:
            print(f"       → {issue}")

    summary = {
        "PASS": sum(1 for v in results.values() if v["dqg_status"] == "PASS"),
        "WARN": sum(1 for v in results.values() if v["dqg_status"] == "WARN"),
        "FAIL": sum(1 for v in results.values() if v["dqg_status"] == "FAIL"),
        "SKIP": sum(1 for v in results.values() if v["dqg_status"] == "SKIP"),
    }

    output = {
        "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
        "raw_data_from": raw.get("generated_at", ""),
        "summary": summary,
        "departments": results,
    }

    with open(DQG_RESULT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"DQG results saved → logs/dqg_results.json")
    print(f"Summary: PASS={summary['PASS']} | WARN={summary['WARN']} | FAIL={summary['FAIL']} | SKIP={summary['SKIP']}")
    print(f"{'='*60}\n")

    return results


if __name__ == "__main__":
    run_dqg()
