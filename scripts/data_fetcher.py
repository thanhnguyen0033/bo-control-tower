"""
data_fetcher.py — GSBB BO Control Tower
METHOD: Public CSV export URL — NO Google Cloud, NO Service Account, NO billing required.

Requires: Google Sheets must be shared as "Anyone with the link can view"
CSV URL:  https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={TAB_NAME}
"""

import json
import os
import urllib.request
import urllib.error
import csv
import io
import datetime
from scripts.sheets_config import SHEET_CONFIG

LOGS_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")
RAW_DATA_FILE = os.path.join(LOGS_DIR, "raw_data.json")

# ─────────────────────────────────────────────────────────────
# Column Normalizer — Việt hóa tiêu đề Google Sheet
# PIC nhập liệu dùng tên tiếng Việt, pipeline nội bộ dùng tên chuẩn EN
# Thêm alias mới tại đây khi sheet thay đổi header
# ─────────────────────────────────────────────────────────────
COLUMN_MAP = {
    # ── Chung (dùng trong nhiều sheet) ──────────────────────
    "Nhà máy":              "Site",
    "Ngày":                 "Date",
    "Ca":                   "Shift",
    "Lệnh SX":              "Work_Order",
    "Máy / Dây chuyền":     "Machine_Line",
    "Nhóm sản phẩm":        "Product_Group",
    "SL Kế hoạch":          "Plan_Qty",
    "SL Thực tế":           "Actual_Qty",
    "SL Lỗi (NG)":          "NG_Qty",
    "% Tuân thủ KH":        "Plan_Do_%",
    "Mức độ":               "Severity",
    "Trạng thái":           "Status",
    "Quá hạn?":             "Overdue?",
    "Mức rủi ro":           "Risk_Level",
    "Cấp độ leo thang":     "Escalation_Level",

    # ── 02_KHSX_OTIF ────────────────────────────────────────
    "Ngày cam kết":         "Commit_Date",
    "Đúng hạn?":            "OTIF?",
    "Rủi ro giao hàng":     "Delivery_Risk",
    "SL cam kết":           "Committed_Qty",
    "SL thực giao":         "Delivered_Qty",
    "Số ngày trễ":          "Delay_Days",

    # ── 03_QLCL ─────────────────────────────────────────────
    "Mã NCR/CAR":           "NCR_CAR_ID",
    "PIC trực tiếp":        "Owner_Direct",
    "SL bị ảnh hưởng":      "Qty_Affected",
    "COPQ ước tính (VNĐ)":  "COPQ_Estimated",

    # ── 04_QLTB_CD ──────────────────────────────────────────
    "Mã máy":               "Machine",
    "Thời gian dừng (phút)": "Downtime_Min",
    "Loại sự cố":           "Breakdown_PM",

    # ── 05_KHO ──────────────────────────────────────────────
    "SL bán thành phẩm":    "WIP_Qty",
    "Trạng thái FIFO":      "FIFO_Status",
    "Số ngày tồn":          "Age_Days",

    # ── 06_GSTT ─────────────────────────────────────────────
    "Ngày kiểm tra":        "Check_Date",
    "Hạng mục":             "Category",

    # ── 07_CONG_NGHE_SPM ────────────────────────────────────
    "Ngày yêu cầu":         "Request_Date",
    "Mã mẫu":               "Sample_ID",
    "Lead time (ngày)":     "Leadtime_Days",
    "Số lần làm lại":       "Redo_Count",

    # ── 08_BO_CONTROL ───────────────────────────────────────
    "Ngày phát sinh":       "Issue_Date",
    "Nguồn":                "Source_Module",
    "PIC chịu trách nhiệm": "Owner",

    # ── 03_QLCL V3 — cột bổ sung ────────────────────────────
    "Khách hàng":            "Customer",
    "Nhóm lỗi":              "Defect_Group",
    "Ngày hạn xử lý":        "Due_Date",
    "Nhóm nguyên nhân gốc":  "Root_Cause_Category",
    "Tóm tắt hành động":     "Action_Summary",

    # ── 04_QLTB_CD V2 — cột bổ sung ─────────────────────────
    "Loại dừng máy":         "Downtime_Type",
    "Mã nguyên nhân":        "Reason_Code",
    "Hành động cần làm":     "Action_Required",

    # ── Cột phụ chung (ghi chú, kiểm tra) ──────────────────
    "Hạng mục vấn đề":      "Main_Issue_Category",
    "Ghi chú":              "Remark",
    "Người kiểm tra DL":    "Data_Checker",
    "Khu vực":              "Area",
    "Công đoạn":            "Stage",
    "Khu vực lưu trữ":      "Storage_Area",
    "Mã vị trí":            "Location_Code",
    "Loại tồn kho":         "Inventory_Type",
    "Nhóm tuổi tồn":        "Aging_Bucket",
    "Mã Issue liên quan":   "Linked_Issue_ID",
    "Link bằng chứng":      "Evidence_Link",
    "Ghi chú kiểm tra DL":  "Data_Check_Note",
}


def normalize_columns(records: list[dict]) -> list[dict]:
    """
    Đổi tên cột tiếng Việt → tên chuẩn nội bộ (EN) theo COLUMN_MAP.
    Cột không có trong map → giữ nguyên (backward compatible).
    Chạy 1 lần ngay sau khi fetch CSV, trước khi lưu raw_data.json.
    """
    if not records:
        return records
    normalized = []
    for row in records:
        new_row = {COLUMN_MAP.get(k, k): v for k, v in row.items()}
        normalized.append(new_row)
    return normalized


def build_csv_url(sheet_id: str, tab_name: str) -> str:
    """Build the public CSV export URL for a Google Sheet tab."""
    encoded_tab = urllib.request.quote(tab_name)
    return (
        f"https://docs.google.com/spreadsheets/d/{sheet_id}"
        f"/gviz/tq?tqx=out:csv&sheet={encoded_tab}"
    )


def fetch_csv(url: str, timeout: int = 30) -> tuple[list[dict], str]:
    """
    Fetch CSV from URL, skip rows 0-1 (title + instructions),
    use row index 2 as headers (header_row=3 in config), rows 3+ as data.

    Returns: (records, fetch_status)
        fetch_status = "OK"           — accessible + has data rows
                     = "EMPTY"        — accessible but 0 data rows (tab not filled yet)
                     = "ACCESS_ERROR" — HTTP error (401/403/404 — permission or wrong ID)
                     = "NETWORK_ERROR"— network/DNS/timeout issues
    """
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (GSBB-BO-Control-Tower/1.0)"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw_bytes = response.read()
            content = raw_bytes.decode("utf-8", errors="replace")

        reader = csv.reader(io.StringIO(content))
        all_rows = list(reader)

        # GVIZ CSV structure for these sheets (due to merged title/instruction cells):
        # row[0] = merged: col[0] = "Title + Instructions + ColName_A", col[1+] = actual header names
        # row[1:] = actual data rows
        # Extract column A name = last word of the long merged text in col[0]
        print(f"    🔍 DEBUG total CSV rows: {len(all_rows)}")

        if len(all_rows) < 2:
            return [], "EMPTY"

        raw_headers = all_rows[0]
        # Column 0: combined text ending with actual column name e.g. "...Dashboard. Date"
        col0_text = raw_headers[0].strip() if raw_headers else ""
        col0_name = col0_text.split()[-1] if col0_text else ""
        headers = [col0_name] + [h.strip() for h in raw_headers[1:]]
        # Remove trailing empty column names
        while headers and not headers[-1]:
            headers.pop()

        data_rows = all_rows[1:]
        print(f"    🔍 DEBUG headers (fixed): {headers[:8]}")

        records = []
        for row in data_rows:
            # Skip completely empty rows
            if not any(cell.strip() for cell in row):
                continue
            # Pad short rows
            padded = row + [""] * (len(headers) - len(row))
            record = {headers[i]: padded[i].strip() for i in range(len(headers))}
            records.append(record)

        if not records:
            return [], "EMPTY"

        return records, "OK"

    except urllib.error.HTTPError as e:
        print(f"    HTTP Error {e.code}: {e.reason}")
        return [], "ACCESS_ERROR"
    except urllib.error.URLError as e:
        print(f"    URL Error: {e.reason}")
        return [], "NETWORK_ERROR"
    except Exception as e:
        print(f"    Unexpected error: {e}")
        return [], "NETWORK_ERROR"


def is_placeholder(sheet_id: str) -> bool:
    """Check if sheet_id is still a placeholder (not yet configured)."""
    s = sheet_id.strip().upper()
    return (
        not s
        or s == "PENDING"
        or "REPLACE_WITH" in s
        or "TODO" in s
        or "TBD" in s
    )


def fetch_all_sheets() -> dict:
    """
    Fetch all configured sheets.
    Returns dict: { dept_key: { "status": ..., "records": [...], "columns": [...], ... } }
    """
    os.makedirs(LOGS_DIR, exist_ok=True)

    results = {}
    total = len(SHEET_CONFIG)
    configured = sum(1 for v in SHEET_CONFIG.values() if not is_placeholder(v["sheet_id"]))

    print(f"\n{'='*60}")
    print(f"GSBB BO Control Tower — Data Fetcher")
    print(f"Mode: Public CSV Export (no Google Cloud required)")
    print(f"Sheets configured: {configured}/{total}")
    print(f"Timestamp: {datetime.datetime.utcnow().isoformat()}Z")
    print(f"{'='*60}\n")

    for dept_key, config in SHEET_CONFIG.items():
        sheet_id  = config["sheet_id"]
        tab_name  = config["tab_name"]
        desc      = config.get("description", dept_key)

        print(f"[{dept_key}] {desc}")

        if is_placeholder(sheet_id):
            print(f"    ⏳ PENDING — Sheet ID not yet configured")
            results[dept_key] = {
                "status":      "PENDING",
                "description": desc,
                "tab_name":    tab_name,
                "sheet_id":    sheet_id,
                "records":     [],
                "columns":     [],
                "row_count":   0,
                "fetched_at":  datetime.datetime.utcnow().isoformat() + "Z",
                "note":        "Sheet ID not yet configured — replace REPLACE_WITH_ACTUAL_SHEET_ID",
            }
            continue

        url = build_csv_url(sheet_id, tab_name)
        print(f"    URL: {url[:80]}...")

        records, fetch_status = fetch_csv(url)

        if fetch_status == "OK":
            records = normalize_columns(records)   # VI → EN column names
            columns = list(records[0].keys())
            print(f"    ✅ OK — {len(records)} data rows, {len(columns)} columns")
            print(f"    🔍 DEBUG columns (normalized): {columns}")
            results[dept_key] = {
                "status":      "OK",
                "description": desc,
                "tab_name":    tab_name,
                "sheet_id":    sheet_id,
                "records":     records,
                "columns":     columns,
                "row_count":   len(records),
                "fetched_at":  datetime.datetime.utcnow().isoformat() + "Z",
                "note":        "",
            }

        elif fetch_status == "EMPTY":
            print(f"    ⚠️  EMPTY — Sheet accessible but no data rows yet (tab: {tab_name})")
            results[dept_key] = {
                "status":      "EMPTY",
                "description": desc,
                "tab_name":    tab_name,
                "sheet_id":    sheet_id,
                "records":     [],
                "columns":     [],
                "row_count":   0,
                "fetched_at":  datetime.datetime.utcnow().isoformat() + "Z",
                "note":        f"Tab '{tab_name}' is accessible but contains no data rows — please enter data",
            }

        elif fetch_status == "ACCESS_ERROR":
            print(f"    ❌ ACCESS ERROR — HTTP 401/403/404. Verify sheet is public AND Sheet ID is correct.")
            results[dept_key] = {
                "status":      "ACCESS_ERROR",
                "description": desc,
                "tab_name":    tab_name,
                "sheet_id":    sheet_id,
                "records":     [],
                "columns":     [],
                "row_count":   0,
                "fetched_at":  datetime.datetime.utcnow().isoformat() + "Z",
                "note":        "Access denied — set sheet sharing to 'Anyone with link can view', or verify Sheet ID",
            }

        else:  # NETWORK_ERROR
            print(f"    ❌ NETWORK ERROR — DNS/timeout issue. Will retry on next run.")
            results[dept_key] = {
                "status":      "NETWORK_ERROR",
                "description": desc,
                "tab_name":    tab_name,
                "sheet_id":    sheet_id,
                "records":     [],
                "columns":     [],
                "row_count":   0,
                "fetched_at":  datetime.datetime.utcnow().isoformat() + "Z",
                "note":        "Network/DNS error — transient issue, retry on next scheduled run",
            }

    # Save raw data log
    output = {
        "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
        "summary": {
            "total_depts":   total,
            "ok":            sum(1 for v in results.values() if v["status"] == "OK"),
            "empty":         sum(1 for v in results.values() if v["status"] == "EMPTY"),
            "pending":       sum(1 for v in results.values() if v["status"] == "PENDING"),
            "access_error":  sum(1 for v in results.values() if v["status"] == "ACCESS_ERROR"),
            "network_error": sum(1 for v in results.values() if v["status"] == "NETWORK_ERROR"),
        },
        "departments": results,
    }

    with open(RAW_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"Raw data saved → logs/raw_data.json")
    s = output['summary']
    print(f"Summary: OK={s['ok']} | EMPTY={s['empty']} | PENDING={s['pending']} | ACCESS_ERR={s['access_error']} | NET_ERR={s['network_error']}")
    print(f"{'='*60}\n")

    return results


if __name__ == "__main__":
    fetch_all_sheets()
