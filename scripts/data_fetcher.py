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


def fetch_csv(url: str, timeout: int = 30) -> list[dict]:
    """
    Fetch CSV from URL, skip rows 0-1 (title + instructions),
    use row index 2 as headers (header_row=3 in config), rows 3+ as data.
    Returns list of dicts.
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
            return []

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

        return records

    except urllib.error.HTTPError as e:
        print(f"    HTTP Error {e.code}: {e.reason}")
        return []
    except urllib.error.URLError as e:
        print(f"    URL Error: {e.reason}")
        return []
    except Exception as e:
        print(f"    Unexpected error: {e}")
        return []


def is_placeholder(sheet_id: str) -> bool:
    """Check if sheet_id is still a placeholder (not yet configured)."""
    return "REPLACE_WITH" in sheet_id or sheet_id.strip() == ""


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

        records = fetch_csv(url)

        if records:
            columns = list(records[0].keys()) if records else []
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
        else:
            print(f"    ❌ FETCH FAILED — 0 rows returned (check share permissions or Sheet ID)")
            results[dept_key] = {
                "status":      "FETCH_ERROR",
                "description": desc,
                "tab_name":    tab_name,
                "sheet_id":    sheet_id,
                "records":     [],
                "columns":     [],
                "row_count":   0,
                "fetched_at":  datetime.datetime.utcnow().isoformat() + "Z",
                "note":        "Fetch failed — verify sheet is shared 'Anyone with link can view'",
            }

    # Save raw data log
    output = {
        "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
        "summary": {
            "total_depts":  total,
            "ok":           sum(1 for v in results.values() if v["status"] == "OK"),
            "pending":      sum(1 for v in results.values() if v["status"] == "PENDING"),
            "fetch_error":  sum(1 for v in results.values() if v["status"] == "FETCH_ERROR"),
        },
        "departments": results,
    }

    with open(RAW_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"Raw data saved → logs/raw_data.json")
    print(f"Summary: OK={output['summary']['ok']} | PENDING={output['summary']['pending']} | ERROR={output['summary']['fetch_error']}")
    print(f"{'='*60}\n")

    return results


if __name__ == "__main__":
    fetch_all_sheets()
