"""
data_fetcher.py — GSBB BO Control Tower
METHOD: Public CSV export URL — NO Google Cloud, NO Service Account, NO billing required.

Requires: Google Sheets must be shared as "Anyone with the link can view"
CSV URL:  https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={TAB_NAME}&headers=0

FIX 2026-06-04 v3: Adaptive header detection — find header row dynamically.
GVIZ with headers=0 returns different row counts depending on merged cells in rows 1-2.
Some sheets: header at index 2 (rows 1-2 returned). Others: header at index 0 or 1 (rows 1-2 skipped).
Fix: scan for first row starting with a date (YYYY-MM-DD) -> header is the row just before it.
"""

import json
import os
import re
import urllib.request
import urllib.error
import csv
import io
import datetime
from scripts.sheets_config import SHEET_CONFIG

LOGS_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")
RAW_DATA_FILE = os.path.join(LOGS_DIR, "raw_data.json")

# Pattern: data rows start with a date like 2026-06-01
_DATE_PAT = re.compile(r'^\d{4}-\d{2}-\d{2}$')


def _find_header_row(all_rows):
    """
    Find column header row index adaptively.

    Strategy: scan rows 0..14 for the FIRST row whose first cell matches YYYY-MM-DD.
    The header row is immediately before that data row.

    Fallback: return 2 if no date row found in first 15 rows.

    Why needed:
    GVIZ with headers=0 may skip merged title/instruction rows (rows 1-2 of sheet)
    for some sheets but not others, causing column header row to appear at
    different indices (0, 1, or 2) depending on the sheet cell structure.
    """
    for i, row in enumerate(all_rows[:15]):
        if not row:
            continue
        first = row[0].strip()
        if _DATE_PAT.match(first):
            if i == 0:
                return -1  # data starts at row 0, no header above
            return i - 1   # header is the row just before first data row
    return 2  # fallback: original assumption


def build_csv_url(sheet_id, tab_name):
    """Build the public CSV export URL for a Google Sheet tab.
    headers=0: GVIZ returns ALL rows as raw data (no header combining).
    """
    encoded_tab = urllib.request.quote(tab_name)
    return (
        f"https://docs.google.com/spreadsheets/d/{sheet_id}"
        f"/gviz/tq?tqx=out:csv&sheet={encoded_tab}&headers=0"
    )


def fetch_csv(url, timeout=30, config_fallback_first_col="", config_fallback_columns=None):
    """
    Fetch CSV from URL. Adaptively detects header row.

    Args:
        config_fallback_first_col: fill headers[0] if it is empty (GVIZ merged first col).
        config_fallback_columns:   dict {col_index: "col_name"} — fill any header at
                                   that index if it is empty (GVIZ merged mid-table cols).
                                   e.g. {9: "% Tuân thủ KH"} for 01_SAN_XUAT.
                                   FIXED 2026-06-04 Session 13.

    Returns: (records, fetch_status)
        fetch_status = "OK"            accessible + has data rows
                     = "EMPTY"         accessible but 0 data rows
                     = "ACCESS_ERROR"  HTTP 401/403/404
                     = "NETWORK_ERROR" network/DNS/timeout issues
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

        print(f"    DEBUG total CSV rows: {len(all_rows)}")

        if len(all_rows) < 2:
            return [], "EMPTY"

        # Adaptive header detection
        header_idx = _find_header_row(all_rows)
        print(f"    DEBUG header_idx: {header_idx}")
        print(f"    DEBUG rows[0][:5]: {all_rows[0][:5] if all_rows else []}")
        if len(all_rows) > 1:
            print(f"    DEBUG rows[1][:5]: {all_rows[1][:5]}")
        if len(all_rows) > 2:
            print(f"    DEBUG rows[2][:5]: {all_rows[2][:5]}")

        if header_idx < 0:
            return [], "EMPTY"

        raw_headers = all_rows[header_idx]
        headers = [h.strip() for h in raw_headers]
        # Remove trailing empty column names
        while headers and not headers[-1]:
            headers.pop()

        if not headers:
            return [], "EMPTY"

        data_rows = all_rows[header_idx + 1:]

        # Apply fallback_first_col: GVIZ exports merged header cells as ''
        # e.g. "Ngay" col in 01_SAN_XUAT becomes empty string in CSV export
        if config_fallback_first_col and headers and not headers[0]:
            print(f"    DEBUG: first col empty -> fallback '{config_fallback_first_col}'")
            headers[0] = config_fallback_first_col

        # Apply fallback_columns: fix mid-table merged header cols exported as ''
        # e.g. 01_SAN_XUAT index 9 → '% Tuân thủ KH'; 04_QLTB_CD index 4 → 'Thời gian dừng (phút)'
        # FIXED 2026-06-04 Session 13
        if config_fallback_columns:
            for col_idx, col_name in config_fallback_columns.items():
                if col_idx < len(headers) and not headers[col_idx]:
                    print(f"    DEBUG: col[{col_idx}] empty -> fallback '{col_name}'")
                    headers[col_idx] = col_name

        print(f"    DEBUG headers: {headers[:12]}")

        records = []
        for row in data_rows:
            # Skip completely empty rows
            if not any(cell.strip() for cell in row):
                continue
            # Pad short rows
            padded = row + [""] * max(0, len(headers) - len(row))
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


def is_placeholder(sheet_id):
    """Check if sheet_id is still a placeholder (not yet configured)."""
    s = sheet_id.strip().upper()
    return (
        not s
        or s == "PENDING"
        or "REPLACE_WITH" in s
        or "TODO" in s
        or "TBD" in s
    )


def fetch_all_sheets():
    """
    Fetch all configured sheets.
    Returns dict: { dept_key: { "status": ..., "records": [...], ... } }
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
        sheet_id = config["sheet_id"]
        tab_name = config["tab_name"]
        desc     = config.get("description", dept_key)

        print(f"[{dept_key}] {desc}")

        if is_placeholder(sheet_id):
            print(f"    PENDING — Sheet ID not yet configured")
            results[dept_key] = {
                "status":      "PENDING",
                "description": desc,
                "tab_name":    tab_name,
                "sheet_id":    sheet_id,
                "records":     [],
                "columns":     [],
                "row_count":   0,
                "fetched_at":  datetime.datetime.utcnow().isoformat() + "Z",
                "note":        "Sheet ID not yet configured",
            }
            continue

        url = build_csv_url(sheet_id, tab_name)
        print(f"    URL: {url[:80]}...")

        fallback      = config.get("fallback_first_col", "")
        fallback_cols = config.get("fallback_columns", None)
        records, fetch_status = fetch_csv(
            url,
            config_fallback_first_col=fallback,
            config_fallback_columns=fallback_cols,
        )

        if fetch_status == "OK":
            columns = list(records[0].keys())
            print(f"    OK — {len(records)} data rows, {len(columns)} columns")
            print(f"    DEBUG columns: {columns}")
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
            print(f"    EMPTY — Sheet accessible but no data rows yet (tab: {tab_name})")
            results[dept_key] = {
                "status":      "EMPTY",
                "description": desc,
                "tab_name":    tab_name,
                "sheet_id":    sheet_id,
                "records":     [],
                "columns":     [],
                "row_count":   0,
                "fetched_at":  datetime.datetime.utcnow().isoformat() + "Z",
                "note":        f"Tab '{tab_name}' accessible but no data rows",
            }

        elif fetch_status == "ACCESS_ERROR":
            print(f"    ACCESS ERROR — HTTP 401/403/404. Verify sheet is public and Sheet ID is correct.")
            results[dept_key] = {
                "status":      "ACCESS_ERROR",
                "description": desc,
                "tab_name":    tab_name,
                "sheet_id":    sheet_id,
                "records":     [],
                "columns":     [],
                "row_count":   0,
                "fetched_at":  datetime.datetime.utcnow().isoformat() + "Z",
                "note":        "Access denied — set sheet sharing to Anyone with link, or verify Sheet ID",
            }

        else:  # NETWORK_ERROR
            print(f"    NETWORK ERROR — DNS/timeout issue. Will retry on next run.")
            results[dept_key] = {
                "status":      "NETWORK_ERROR",
                "description": desc,
                "tab_name":    tab_name,
                "sheet_id":    sheet_id,
                "records":     [],
                "columns":     [],
                "row_count":   0,
                "fetched_at":  datetime.datetime.utcnow().isoformat() + "Z",
                "note":        "Network/DNS error — transient issue, retry on next run",
            }

    # ── Save raw_data.json ──────────────────────────────────────────
    summary = {
        "total":        total,
        "configured":   configured,
        "ok":           sum(1 for v in results.values() if v["status"] == "OK"),
        "empty":        sum(1 for v in results.values() if v["status"] == "EMPTY"),
        "pending":      sum(1 for v in results.values() if v["status"] == "PENDING"),
        "access_error": sum(1 for v in results.values() if v["status"] == "ACCESS_ERROR"),
        "network_error":sum(1 for v in results.values() if v["status"] == "NETWORK_ERROR"),
    }

    output = {
        "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
        "summary":      summary,
        "departments":  results,
    }

    with open(RAW_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    ok  = summary["ok"]
    err = summary["access_error"] + summary["network_error"]
    print(f"\n{'='*60}")
    print(f"Summary: OK={ok} | EMPTY={summary['empty']} | PENDING={summary['pending']} "
          f"| ACCESS_ERR={summary['access_error']} | NET_ERR={summary['network_error']}")
    print(f"Raw data saved: {RAW_DATA_FILE}")
    print(f"{'='*60}\n")

    return output


if __name__ == "__main__":
    fetch_all_sheets()
