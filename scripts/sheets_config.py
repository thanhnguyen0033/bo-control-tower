# sheets_config.py -- Google Sheets configuration for BO Control Tower
# METHOD: Public CSV export -- no Service Account / Google Cloud needed
# REQUIREMENT: Each sheet must be shared as "Anyone with the link can view"
#
# fallback_first_col : fill headers[0] if empty (GVIZ merged first-col)
# fallback_columns   : dict {index: name} -- fill mid-table headers exported as '' by GVIZ
#                      ADDED 2026-06-04 Session 13 for 01_SAN_XUAT & 04_QLTB_CD

SHEET_CONFIG = {
    "01_SAN_XUAT": {
        # Verified 2026-06-04 -- sheet_id confirmed from .gsheet file
        # Tab: 01_SX_PLAN_DO | Row3 col0: Ngay
        # GVIZ merged-cell: col0='' -> fallback_first_col; col9='' -> fallback_columns[9]
        # Header: Ngay,Ca,Nha may,Lenh SX,May/DC,Nhom SP,SL KH,SL TT,SL Loi(NG),[9='% Tuan thu KH'],RAG
        "sheet_id":           "1FDN2w9fh0PbsIPv6V83DJmoxWzF3CTkSbz4rX1D90eQ",
        "tab_name":           "01_SX_PLAN_DO",
        "description":        "San Xuat - Plan/DO",
        "fallback_first_col": "Ngay",
        "fallback_columns":   {9: "% Tuan thu KH"},
    },
    "02_KHSX_OTIF": {
        # Verified 2026-06-04 -- sheet_id confirmed from .gsheet file
        # Tab: 02_OTIF_DELIVERY | Row3 col0: Ngay cam ket
        "sheet_id":           "1YWmcZlXqZ8fRKpw-L0R-ERcofeWUjo68dKwwNc113AQ",
        "tab_name":           "02_OTIF_DELIVERY",
        "description":        "KHSX - OTIF Delivery",
        "fallback_first_col": "Ngay cam ket",
    },
    "03_QLCL": {
        # FIXED 2026-06-04 -- old ID wrong (164Ylw1...). Correct ID from .gsheet file.
        # Tab: 03_QLCL_NCR_CAR | Row3 col0: Ngay
        "sheet_id":           "1fK3UGw4BGpqX4zay7gIyq9JP5MsLUGYf3ZsJMDSjzTY",
        "tab_name":           "03_QLCL_NCR_CAR",
        "description":        "Chat Luong - NCR/CAR (V3 RMA/ECN/Recovery)",
        "fallback_first_col": "Ngay",
    },
    "04_QLTB_CD": {
        # FIXED 2026-06-04 -- old ID wrong (1XJ4Jkk...). Correct ID from .gsheet file.
        # Tab: 04_MACHINE_DOWNTIME | Row3 col0: Ngay
        # GVIZ merged-cell: col0='' -> fallback_first_col; col4='' -> fallback_columns[4]
        # Header: Ngay,Ca,Nha may,Ma may,[4='Thoi gian dung (phut)'],Loai dung may,...
        "sheet_id":           "1_HhUXOaX9MeqsJC2I-NeTyPaII12sayyvtXMPFaUk0E",
        "tab_name":           "04_MACHINE_DOWNTIME",
        "description":        "Thiet Bi - Machine Downtime",
        "fallback_first_col": "Ngay",
        "fallback_columns":   {4: "Thoi gian dung (phut)"},
    },
    "05_KHO": {
        # CORRECTED 2026-06-04 -- confirmed active KHO sheet
        # Tab: 05_WIP_FIFO_KHO | Row3 col0: Ngay
        "sheet_id":           "1G7tWo8KwD91BecbSmlZWVmugeWUad2Hoa73eUtHfppY",
        "tab_name":           "05_WIP_FIFO_KHO",
        "description":        "Kho - WIP/FIFO (V3 Inventory/Capacity/Aging)",
        "fallback_first_col": "Ngay",
    },
    "06_GSTT": {
        # FIXED 2026-06-04 -- old ID wrong (1lgY4FT...). Correct ID from .gsheet file.
        # Tab: 06_GSTT_FIELD_LOG | Row3 col0: Check_Date
        "sheet_id":           "1Xd38NfvIpPUjR2-MWo020hUSl-KGt--mF23udkXTYYs",
        "tab_name":           "06_GSTT_FIELD_LOG",
        "description":        "GSTT - Field Verification",
        "fallback_first_col": "Check_Date",
    },
    "07_CONG_NGHE_SPM": {
        # FIXED 2026-06-04 -- old ID wrong (1VdkEFm...). Correct ID from .gsheet file.
        # Tab: 08_SPM_TECH | Row3 col0: Ngay
        "sheet_id":           "1gegI7IkIb9145n15SXChsQEWww74YJqXS8s88WnGUas",
        "tab_name":           "08_SPM_TECH",
        "description":        "Cong Nghe - SPM Technology",
        "fallback_first_col": "Ngay",
    },
    "08_BO_CONTROL": {
        # FIXED 2026-06-04 -- old ID wrong (1DzPrZ2...). Correct ID from .gsheet file.
        # Tab: 09_ISSUE_ACTION | Row3 col0: Issue_Date
        "sheet_id":           "12Bi3CKN1FTXDYmnXWxMNQAErYSTsjpWQF8NIaq4T84Q",
        "tab_name":           "09_ISSUE_ACTION",
        "description":        "BO Control - Issue/Action",
        "fallback_first_col": "Issue_Date",
    },
}

VALID_SITES = ["GS1", "GS5", "GS6", "GSQV"]
