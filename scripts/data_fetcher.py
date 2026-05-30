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

        if len(all_rows) < 3:
            # Sheet accessible but even header rows are missing
            return [], "EMPTY"

        # Row 0 = sheet title (skip)
        # Row 1 = instructions/notes (skip)
        # Row 2 = actual column headers  ← header_row=3 in config means index 2
        # Row 3+ = data
        headers = [h.strip() for h in all_rows[2]]
        data_rows = all_rows[3:]

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
            columns = list(records[0].keys())
            print(f"    ✅ OK — {len(records)} data rows, {len(columns)} columns")
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
