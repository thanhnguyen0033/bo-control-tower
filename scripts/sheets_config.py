# ============================================================
# sheets_config.py - Cau hinh ID cac Google Sheet tung bo phan
# Anh chi can dien Sheet ID thuc te vao day
# ============================================================
#
# Cach lay Sheet ID:
# Mo Google Sheet -> copy phan giua /d/ va /edit trong URL:
# https://docs.google.com/spreadsheets/d/[SHEET_ID]/edit
#

SHEET_CONFIG = {
    "01_SAN_XUAT": {
        "sheet_id": "REPLACE_WITH_ACTUAL_SHEET_ID",
        "tab_name": "01_SX_PLAN_DO",
        "header_row": 3,
        "description": "San xuat - Plan DO"
    },
    "02_KHSX_OTIF": {
        "sheet_id": "REPLACE_WITH_ACTUAL_SHEET_ID",
        "tab_name": "02_OTIF_DELIVERY",
        "header_row": 3,
        "description": "KHSX - OTIF Delivery"
    },
    "03_QLCL": {
        "sheet_id": "REPLACE_WITH_ACTUAL_SHEET_ID",
        "tab_name": "03_QLCL_NCR_CAR",
        "header_row": 3,
        "description": "Chat luong - NCR CAR"
    },
    "04_QLTB_CD": {
        "sheet_id": "REPLACE_WITH_ACTUAL_SHEET_ID",
        "tab_name": "04_MACHINE_DOWNTIME",
        "header_row": 3,
        "description": "Thiet bi - Machine Downtime"
    },
    "05_KHO": {
        "sheet_id": "REPLACE_WITH_ACTUAL_SHEET_ID",
        "tab_name": "05_WIP_FIFO_KHO",
        "header_row": 3,
        "description": "Kho - WIP FIFO"
    },
    "06_GSTT": {
        "sheet_id": "REPLACE_WITH_ACTUAL_SHEET_ID",
        "tab_name": "06_GSTT_FIELD_LOG",
        "header_row": 3,
        "description": "GSTT - Field Verification"
    },
    "07_CONG_NGHE_SPM": {
        "sheet_id": "REPLACE_WITH_ACTUAL_SHEET_ID",
        "tab_name": "08_SPM_TECH",
        "header_row": 3,
        "description": "Cong nghe - SPM Technology"
    },
    "08_BO_CONTROL": {
        "sheet_id": "REPLACE_WITH_ACTUAL_SHEET_ID",
        "tab_name": "09_ISSUE_ACTION",
        "header_row": 3,
        "description": "BO Control - Issue Action"
    },
}

VALID_SITES = ["GS1", "GS5", "GS6", "GSQV"]
