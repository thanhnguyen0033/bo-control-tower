# sheets_config.py – Google Sheets configuration for BO Control Tower
# METHOD: Public CSV export — no Service Account / Google Cloud needed
# REQUIREMENT: Each sheet must be shared as "Anyone with the link can view"

# CSV export URL template (headers=3 tells GVIZ to use row 3 as column headers):
# https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={TAB_NAME}&headers=3
#
# Sheet IDs verified 2026-06-04 against .gsheet files in:
# D:\AI Claude\Dự Án Claude\Dashboard khối BO GSBB\02_Data_Request_and_Templates\
# BO_Control_Tower_Input_Folder_V2_By_Department\

SHEET_CONFIG = {
    "01_SAN_XUAT": {
        # Verified 2026-06-04 — .gsheet doc_id confirmed ✓
        # File: BO_Input_SX_PlanDO_GSBB_V2.gsheet | Tab: 01_SX_PLAN_DO | Row3 col0: Date
        "sheet_id":   "1FDN2w9fh0PbsIPv6V83DJmoxWzF3CTkSbz4rX1D90eQ",
        "tab_name":   "01_SX_PLAN_DO",
        "header_row": 3,
        "description": "Sản Xuất – Plan/DO",
    },
    "02_KHSX_OTIF": {
        # Verified 2026-06-04 — .gsheet doc_id confirmed ✓
        # File: BO_Input_OTIF_Delivery_BySite_GSBB_V2.gsheet | Tab: 02_OTIF_DELIVERY | Row3 col0: Commit_Date
        "sheet_id":   "1YWmcZlXqZ8fRKpw-L0R-ERcofeWUjo68dKwwNc113AQ",
        "tab_name":   "02_OTIF_DELIVERY",
        "header_row": 3,
        "description": "KHSX – OTIF Delivery",
    },
    "03_QLCL": {
        # FIXED 2026-06-04 — old ID was wrong (164Ylw1...). Correct ID from .gsheet file.
        # File: BO_Input_QLCL_NCR_CAR_GSBB_V3_RMA_ECN_Recovery.gsheet | Tab: 03_QLCL_NCR_CAR | Row3 col0: Date
        "sheet_id":   "1fK3UGw4BGpqX4zay7gIyq9JP5MsLUGYf3ZsJMDSjzTY",
        "tab_name":   "03_QLCL_NCR_CAR",
        "header_row": 3,
        "description": "Chất Lượng – NCR/CAR (V3 RMA/ECN/Recovery)",
    },
    "04_QLTB_CD": {
        # FIXED 2026-06-04 — old ID was wrong (1XJ4Jkk...). Correct ID from .gsheet file.
        # File: BO_Input_QLTB_Downtime_GSBB_V2.gsheet | Tab: 04_MACHINE_DOWNTIME | Row3 col0: Date
        "sheet_id":   "1_HhUXOaX9MeqsJC2I-NeTyPaII12sayyvtXMPFaUk0E",
        "tab_name":   "04_MACHINE_DOWNTIME",
        "header_row": 3,
        "description": "Thiết Bị – Machine Downtime",
    },
    "05_KHO": {
        # CORRECTED 2026-06-04 — anh confirmed this is the active KHO sheet.
        # File: BO_Input_Kho_WIP_FIFO_GSBB_V3_Inventory_Capacity_Aging (shared with anh)
        # Tab: 05_WIP_FIFO_KHO | Row3 col0 (Vietnamese): Ngày
        # ⚠️ Sheet must be shared as "Anyone with the link can view" to allow pipeline access.
        "sheet_id":   "1G7tWo8KwD91BecbSmlZWVmugeWUad2Hoa73eUtHfppY",
        "tab_name":   "05_WIP_FIFO_KHO",
        "header_row": 3,
        "description": "Kho – WIP/FIFO (V3 Inventory/Capacity/Aging)",
    },
    "06_GSTT": {
        # FIXED 2026-06-04 — old ID was wrong (1lgY4FT...). Correct ID from .gsheet file.
        # File: BO_Input_GSTT_Field_Verify_GSBB_V2.gsheet | Tab: 06_GSTT_FIELD_LOG | Row3 col0: Check_Date
        "sheet_id":   "1Xd38NfvIpPUjR2-MWo020hUSl-KGt--mF23udkXTYYs",
        "tab_name":   "06_GSTT_FIELD_LOG",
        "header_row": 3,
        "description": "GSTT – Field Verification",
    },
    "07_CONG_NGHE_SPM": {
        # FIXED 2026-06-04 — old ID was wrong (1VdkEFm...). Correct ID from .gsheet file.
        # File: BO_Input_CongNghe_SPM_GSBB_V2.gsheet | Tab: 08_SPM_TECH | Row3 col0: Request_Date
        "sheet_id":   "1gegI7IkIb9145n15SXChsQEWww74YJqXS8s88WnGUas",
        "tab_name":   "08_SPM_TECH",
        "header_row": 3,
        "description": "Công Nghệ – SPM Technology",
    },
    "08_BO_CONTROL": {
        # FIXED 2026-06-04 — old ID was wrong (1DzPrZ2...). Correct ID from .gsheet file.
        # File: BO_Input_BO_Control_Issue_DQG_GSBB_V2.gsheet | Tab: 09_ISSUE_ACTION | Row3 col0: Issue_Date
        "sheet_id":   "12Bi3CKN1FTXDYmnXWxMNQAErYSTsjpWQF8NIaq4T84Q",
        "tab_name":   "09_ISSUE_ACTION",
        "header_row": 3,
        "description": "BO Control – Issue/Action",
    },
}

VALID_SITES = ["GS1", "GS5", "GS6", "GSQV"]
