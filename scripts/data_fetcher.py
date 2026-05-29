"""
data_fetcher.py – Fetch data from Google Sheets for BO Control Tower
Runs inside GitHub Actions. Reads GOOGLE_CREDENTIALS from environment.
"""
import os, json, sys
from datetime import datetime

# ── Try importing gspread (installed via pip in workflow) ──────────────────────
try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSPREAD_OK = True
except ImportError:
    GSPREAD_OK = False

from sheets_config import SHEET_CONFIG

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

OUTPUT_FILE = "logs/raw_data.json"
os.makedirs("logs", exist_ok=True)

def get_gspread_client():
    creds_json = os.environ.get("GOOGLE_CREDENTIALS", "")
    if not creds_json:
        raise ValueError("GOOGLE_CREDENTIALS secret not set")
    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)

def is_demo_mode():
    """Return True if all sheet IDs are still placeholder."""
    return all(v["sheet_id"] == "REPLACE_WITH_ACTUAL_SHEET_ID"
               for v in SHEET_CONFIG.values())

def fetch_demo_data():
    """Return minimal demo dataset so pipeline can still run end-to-end."""
    demo = {}
    for dept_key, cfg in SHEET_CONFIG.items():
        demo[dept_key] = {
            "status": "DEMO",
            "description": cfg["description"],
            "headers": ["Site", "Date", "Value", "Owner", "Evidence"],
            "rows": [
                {"Site": "GS1", "Date": "2026-05-29", "Value": "85",
                 "Owner": "Demo Owner", "Evidence": "Demo evidence"},
            ],
            "fetched_at": datetime.utcnow().isoformat() + "Z",
        }
    return demo

def fetch_sheet(client, dept_key, cfg):
    """Fetch one sheet tab and return dict with headers + rows."""
    sheet_id  = cfg["sheet_id"]
    tab_name  = cfg["tab_name"]
    header_row = cfg["header_row"]   # 1-indexed (usually 3)

    try:
        spreadsheet = client.open_by_key(sheet_id)
        worksheet   = spreadsheet.worksheet(tab_name)
        all_values  = worksheet.get_all_values()

        if len(all_values) < header_row:
            return {"status": "NO_DATA", "headers": [], "rows": [],
                    "description": cfg["description"],
                    "fetched_at": datetime.utcnow().isoformat() + "Z"}

        headers = all_values[header_row - 1]   # 0-indexed
        data_rows = []
        for raw_row in all_values[header_row:]:  # rows after header
            # Pad row to header length, then zip
            padded = raw_row + [""] * (len(headers) - len(raw_row))
            row_dict = {headers[i]: padded[i] for i in range(len(headers))
                        if headers[i]}  # skip blank header cols
            # Only include rows that have at least one non-empty value
            if any(v.strip() for v in row_dict.values()):
                data_rows.append(row_dict)

        return {
            "status": "OK",
            "description": cfg["description"],
            "headers": [h for h in headers if h],
            "rows": data_rows,
            "fetched_at": datetime.utcnow().isoformat() + "Z",
        }

    except gspread.exceptions.SpreadsheetNotFound:
        return {"status": "ERROR", "error": "Spreadsheet not found – check sheet_id",
                "description": cfg["description"],
                "fetched_at": datetime.utcnow().isoformat() + "Z"}
    except gspread.exceptions.WorksheetNotFound:
        return {"status": "ERROR", "error": f"Tab '{tab_name}' not found",
                "description": cfg["description"],
                "fetched_at": datetime.utcnow().isoformat() + "Z"}
    except Exception as e:
        return {"status": "ERROR", "error": str(e),
                "description": cfg["description"],
                "fetched_at": datetime.utcnow().isoformat() + "Z"}

def main():
    print("=== BO Control Tower – Data Fetcher ===")

    if is_demo_mode():
        print("⚠  DEMO MODE: sheet IDs not configured. Using demo data.")
        result = fetch_demo_data()
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"✅ Demo data written to {OUTPUT_FILE}")
        return

    if not GSPREAD_OK:
        print("ERROR: gspread not installed"); sys.exit(1)

    try:
        client = get_gspread_client()
    except Exception as e:
        print(f"ERROR: Cannot create GSheet client – {e}"); sys.exit(1)

    result = {}
    for dept_key, cfg in SHEET_CONFIG.items():
        print(f"  Fetching {dept_key} …", end=" ")
        data = fetch_sheet(client, dept_key, cfg)
        result[dept_key] = data
        rows = len(data.get("rows", []))
        print(f"{data['status']} ({rows} rows)")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"✅ Raw data saved → {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
