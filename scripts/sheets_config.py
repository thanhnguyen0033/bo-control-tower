# sheets_config.py – Google Sheets configuration for BO Control Tower
# METHOD: Public CSV export — no Service Account / Google Cloud needed
# REQUIREMENT: Each sheet must be shared as "Anyone with the link can view"

# CSV export URL template (no API key needed for public sheets):
# https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={TAB_NAME}

SHEET_CONFIG = {
    "01_SAN_XUAT": {
        # Confirmed 2026-05-30 — screenshot verified: 3 data rows, correct structure
        "sheet_id":   "1FDN2w9fh0PbsIPv6V83DJmoxWzF3CTkSbz4rX1D90eQ",
        "tab_name":   "01_SX_PLAN_DO",
        "header_row": 3,
        "description": "Sản Xuất – Plan/DO",
    },
    "02_KHSX_OTIF": {
        # Confirmed 2026-05-31 — BO_Input_OTIF_Delivery_BySite_GSBB_V2
        # Tab: 02_OTIF_DELIVERY | 2 data rows | cols: Commit_Date, Site, Work_Order, OTIF?, Delay_Days
        "sheet_id":   "1YWmcZlXqZ8fRKpw-L0R-ERcofeWUjo68dKwwNc113AQ",
        "tab_name":   "02_OTIF_DELIVERY",
        "header_row": 3,
        "description": "KHSX – OTIF Delivery",
    },
    "03_QLCL": {
        # Updated 2026-06-03 — V3 sheet: BO_Input_QLCL_NCR_CAR_GSBB_V3_RMA_ECN_Recovery
        "sheet_id":   "1fK3UGw4BGpqX4zay7gIyq9JP5MsLUGYf3ZsJMDSjzTY",
        "tab_name":   "03_QLCL_NCR_CAR",
        "header_row": 3,
        "description": "Chất Lượng – NCR/CAR",
    },
    "04_QLTB_CD": {
        # Updated 2026-06-03 — V2 sheet: BO_Input_QLTB_Downtime_GSBB_V2
        "sheet_id":   "1_HhUXOaX9MeqsJC2I-NeTyPaII12sayyvtXMPFaUk0E",
        "tab_name":   "04_MACHINE_DOWNTIME",
        "header_row": 3,
        "description": "Thiết Bị – Machine Downtime",
    },
    "05_KHO": {
        # Updated 2026-06-03 — V3 sheet: BO_Input_Kho_WIP_FIFO_GSBB_V3_Inventory_Capacity_Aging
        "sheet_id":   "1yl8K7TVN5XQXcWT3IlRWptoEg7J4Lb127aBHWE8Ve1s",
        "tab_name":   "05_WIP_FIFO_KHO",
        "header_row": 3,
        "description": "Kho GS5 – WIP/FIFO",
    },
    "06_GSTT": {
        # Link Register INP-GSTT-001
        "sheet_id":   "1lgY4FTcZ2Un6A4YrHDI1kjSE0gtdnrZjcR81IYaN6Ns",
        "tab_name":   "06_GSTT_FIELD_LOG",
        "header_row": 3,
        "description": "GSTT – Field Verification",
    },
    "07_CONG_NGHE_SPM": {
        # Link Register INP-SPM-001
        "sheet_id":   "1VdkEFmfZnUXLda5KQJavEQWaGQrtJ31YkCqPRkvksig",
        "tab_name":   "08_SPM_TECH",
        "header_row": 3,
        "description": "Công Nghệ – SPM Technology",
    },
    "08_BO_CONTROL": {
        # Link Register INP-BO-001
        "sheet_id":   "1DzPrZ2Yw1Hyp3IaSG0r85J_A7GrALeQk1yHGNSRKzIE",
        "tab_name":   "09_ISSUE_ACTION",
        "header_row": 3,
        "description": "BO Control – Issue/Action",
    },
}

VALID_SITES = ["GS1", "GS5", "GS6", "GSQV"]
