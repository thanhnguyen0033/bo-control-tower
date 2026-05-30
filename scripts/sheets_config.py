# sheets_config.py – Google Sheets configuration for BO Control Tower
# METHOD: Public CSV export — no Service Account / Google Cloud needed
# REQUIREMENT: Each sheet must be shared as "Anyone with the link can view"

# CSV export URL template (no API key needed for public sheets):
# https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={TAB_NAME}

SHEET_CONFIG = {
    "01_SAN_XUAT": {
        # Updated 2026-05-30 — Link Register INP-SX-001
        "sheet_id":   "1-muxD7FtR4Mo_2Bg0RlmBzjy4Tk3np_pKsqkajszrUY",
        "tab_name":   "01_SX_PLAN_DO",
        "header_row": 3,
        "description": "Sản Xuất – Plan/DO",
    },
    "02_KHSX_OTIF": {
        # Updated 2026-05-30 — Link Register INP-OTIF-001
        "sheet_id":   "1Yj0b_Dr0D6ZWC_ihyioFW3FluQHaiJd4XpLO765jhgE",
        "tab_name":   "02_OTIF_DELIVERY",
        "header_row": 3,
        "description": "KHSX – OTIF Delivery",
    },
    "03_QLCL": {
        # Updated 2026-05-30 — Link Register INP-QLCL-001
        "sheet_id":   "164Ylw1FqWfnCUg92pVBJD_Z_Q6DUHZmLCIza8UcEonw",
        "tab_name":   "03_QLCL_NCR_CAR",
        "header_row": 3,
        "description": "Chất Lượng – NCR/CAR",
    },
    "04_QLTB_CD": {
        # Updated 2026-05-30 — Link Register INP-QLTB-001
        "sheet_id":   "1XJ4JkkQDyIzqbeyNmrf2pfhD_pK09lgv7YB7zvH9dLs",
        "tab_name":   "04_MACHINE_DOWNTIME",
        "header_row": 3,
        "description": "Thiết Bị – Machine Downtime",
    },
    "05_KHO": {
        # Updated 2026-05-30 — Link Register INP-KHO-001 (single shared Kho sheet)
        "sheet_id":   "1u8x-xlizEubjA5Mf6_PPJNG2yG8Kj9mbdWHp_JqZTL0",
        "tab_name":   "05_WIP_FIFO_KHO",
        "header_row": 3,
        "description": "Kho – WIP/FIFO",
    },
    "06_GSTT": {
        # Updated 2026-05-30 — Link Register INP-GSTT-001
        "sheet_id":   "1lgY4FTcZ2Un6A4YrHDI1kjSE0gtdnrZjcR81IYaN6Ns",
        "tab_name":   "06_GSTT_FIELD_LOG",
        "header_row": 3,
        "description": "GSTT – Field Verification",
    },
    "07_CONG_NGHE_SPM": {
        # Updated 2026-05-30 — Link Register INP-SPM-001
        "sheet_id":   "1VdkEFmfZnUXLda5KQJavEQWaGQrtJ31YkCqPRkvksig",
        "tab_name":   "08_SPM_TECH",
        "header_row": 3,
        "description": "Công Nghệ – SPM Technology",
    },
    "08_BO_CONTROL": {
        # Updated 2026-05-30 — Link Register INP-BO-001
        "sheet_id":   "1DzPrZ2Yw1Hyp3IaSG0r85J_A7GrALeQk1yHGNSRKzIE",
        "tab_name":   "09_ISSUE_ACTION",
        "header_row": 3,
        "description": "BO Control – Issue/Action",
    },
}

VALID_SITES = ["GS1", "GS5", "GS6", "GSQV"]
