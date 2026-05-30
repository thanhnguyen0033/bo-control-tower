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
        # Link Register INP-OTIF-001 — has 5 rows/2 cols, tab name TBC
        "sheet_id":   "1Yj0b_Dr0D6ZWC_ihyioFW3FluQHaiJd4XpLO765jhgE",
        "tab_name":   "02_OTIF_DELIVERY",
        "header_row": 3,
        "description": "KHSX – OTIF Delivery",
    },
    "03_QLCL": {
        # Link Register INP-QLCL-001
        "sheet_id":   "164Ylw1FqWfnCUg92pVBJD_Z_Q6DUHZmLCIza8UcEonw",
        "tab_name":   "03_QLCL_NCR_CAR",
        "header_row": 3,
        "description": "Chất Lượng – NCR/CAR",
    },
    "04_QLTB_CD": {
        # Link Register INP-QLTB-001
        "sheet_id":   "1XJ4JkkQDyIzqbeyNmrf2pfhD_pK09lgv7YB7zvH9dLs",
        "tab_name":   "04_MACHINE_DOWNTIME",
        "header_row": 3,
        "description": "Thiết Bị – Machine Downtime",
    },
    "05_KHO": {
        # Confirmed 2026-05-30 — screenshot verified: 2 data rows, tab 05_WIP_FIFO_KHO
        "sheet_id":   "1G7tWo8KwD91BecbSmlZWVmugeWUad2Hoa73eUtHfppY",
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
