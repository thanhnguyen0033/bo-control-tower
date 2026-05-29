# sheets_config.py – Google Sheets configuration for BO Control Tower
# METHOD: Public CSV export — no Service Account / Google Cloud needed
# REQUIREMENT: Each sheet must be shared as "Anyone with the link can view"

# CSV export URL template (no API key needed for public sheets):
# https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={TAB_NAME}

SHEET_CONFIG = {
    "01_SAN_XUAT": {
        "sheet_id":   "1FDN2w9fh0PbsIPv6V83DJmoxWzF3CTkSbz4rX1D90eQ",
        "tab_name":   "01_SX_PLAN_DO",
        "header_row": 3,
        "description": "Sản Xuất – Plan/DO",
    },
    "02_KHSX_OTIF": {
        # Sheet ID chưa được cung cấp — giữ PENDING để pipeline không lỗi
        "sheet_id":   "PENDING",
        "tab_name":   "02_OTIF_DELIVERY",
        "header_row": 3,
        "description": "KHSX – OTIF Delivery",
    },
    "03_QLCL": {
        "sheet_id":   "1fK3UGw4BGpqX4zay7gIyq9JP5MsLUGYf3ZsJMDSjzTY",
        "tab_name":   "03_QLCL_NCR_CAR",
        "header_row": 3,
        "description": "Chất Lượng – NCR/CAR",
    },
    "04_QLTB_CD": {
        "sheet_id":   "1_HhUXOaX9MeqsJC2I-NeTyPaII12sayyvtXMPFaUk0E",
        "tab_name":   "04_MACHINE_DOWNTIME",
        "header_row": 3,
        "description": "Thiết Bị – Machine Downtime",
    },
    "05_KHO": {
        # GS5/GSQV primary — Kho WIP/FIFO V3 (GS5 variant)
        "sheet_id":   "1G7tWo8KwD91BecbSmlZWVmugeWUad2Hoa73eUtHfppY",
        "tab_name":   "05_WIP_FIFO_KHO",
        "header_row": 3,
        "description": "Kho GS5 – WIP/FIFO",
    },
    "05_KHO_GS1": {
        # GS1/GSHN secondary — Kho WIP/FIFO V3 (GS1 variant)
        "sheet_id":   "1yl8K7TVN5XQXcWT3IlRWptoEg7J4Lb127aBHWE8Ve1s",
        "tab_name":   "05_WIP_FIFO_KHO",
        "header_row": 3,
        "description": "Kho GS1 – WIP/FIFO",
    },
    "06_GSTT": {
        "sheet_id":   "1Xd38NfvIpPUjR2-MWo020hUSl-KGt--mF23udkXTYYs",
        "tab_name":   "06_GSTT_FIELD_LOG",
        "header_row": 3,
        "description": "GSTT – Field Verification",
    },
    "07_CONG_NGHE_SPM": {
        "sheet_id":   "1gegI7IkIb9145n15SXChsQEWww74YJqXS8s88WnGUas",
        "tab_name":   "08_SPM_TECH",   # Tab name is 08_SPM_TECH (not 07)
        "header_row": 3,
        "description": "Công Nghệ – SPM Technology",
    },
    "08_BO_CONTROL": {
        "sheet_id":   "12Bi3CKN1FTXDYmnXWxMNQAErYSTsjpWQF8NIaq4T84Q",
        "tab_name":   "09_ISSUE_ACTION",   # Tab name is 09_ISSUE_ACTION
        "header_row": 3,
        "description": "BO Control – Issue/Action",
    },
}

VALID_SITES = ["GS1", "GS5", "GS6", "GSQV"]
