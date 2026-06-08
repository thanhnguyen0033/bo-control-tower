# sheets_config.py -- Google Sheets configuration for BO Control Tower
# METHOD: Public CSV export -- no Service Account / Google Cloud needed
# REQUIREMENT: Each sheet must be shared as "Anyone with the link can view"
#
# fallback_first_col : fill headers[0] if empty (GVIZ merged first-col)
# fallback_columns   : dict {index: col_name} -- fill mid-table headers
#                      exported as '' by GVIZ due to merged cells.
#                      ADDED 2026-06-04 Session 13: ALL 8 sheets fully mapped

SHEET_CONFIG = {
    "01_SAN_XUAT": {
        # Verified 2026-06-04 -- sheet_id from .gsheet file
        # Tab: 01_SX_PLAN_DO
        # GVIZ merged-cell fix: col0 fallback_first_col; col9 fallback_columns[9]
        # Full header: Ngay,Ca,Nha may,Lenh SX,May/DC,Nhom SP,SL KH,SL TT,SL Loi(NG),[9=% Tuan thu KH],RAG,...
        "sheet_id":           "1FDN2w9fh0PbsIPv6V83DJmoxWzF3CTkSbz4rX1D90eQ",
        "tab_name":           "01_SX_PLAN_DO",
        "description":        "San Xuat - Plan/DO",
        "fallback_first_col": "Ngay",
        # UPDATED Session 14: cols 6,7,8 also empty from GVIZ merged header.
        # Confirmed 2026-06-08: [6]->SL Ke hoach, [7]->SL Thuc te, [8]->SL Loi(NG)
        "fallback_columns":   {
            6: "SL Kế hoạch",
            7: "SL Thực tế",
            8: "SL Lỗi (NG)",
            9: "% Tuân thủ KH",
        },
    },
    "02_KHSX_OTIF": {
        # Verified 2026-06-04 -- sheet_id from .gsheet file
        # Tab: 02_OTIF_DELIVERY
        # GVIZ merged-cell fix: 4 empty cols from mid-table merged headers
        # Full header: Ngay cam ket,[1=Actual_Delivery_Date],Nha may,KH,Lenh SX,
        #              [5=SL cam ket],[6=SL thuc giao],Dung han?,[8=So ngay tre],Rui ro giao hang,...
        "sheet_id":           "1YWmcZlXqZ8fRKpw-L0R-ERcofeWUjo68dKwwNc113AQ",
        "tab_name":           "02_OTIF_DELIVERY",
        "description":        "KHSX - OTIF Delivery",
        "fallback_first_col": "Ngay cam ket",
        "fallback_columns":   {
            1: "Actual_Delivery_Date",
            5: "SL cam kết",
            6: "SL thực giao",
            8: "Số ngày trễ",
        },
    },
    "03_QLCL": {
        # FIXED 2026-06-04 -- old ID wrong (164Ylw1...). Correct from .gsheet file.
        # Tab: 03_QLCL_NCR_CAR
        # GVIZ merged-cell fix: col6='' -> "SL bi anh huong"
        # Full header: Ngay,Nha may,KH,Ma NCR,Nhom loi,Muc do,[6=SL bi anh huong],Trang thai,PIC,...
        "sheet_id":           "1fK3UGw4BGpqX4zay7gIyq9JP5MsLUGYf3ZsJMDSjzTY",
        "tab_name":           "03_QLCL_NCR_CAR",
        "description":        "Chat Luong - NCR/CAR (V3 RMA/ECN/Recovery)",
        "fallback_first_col": "Ngay",
        "fallback_columns":   {6: "SL bị ảnh hưởng"},
    },
    "04_QLTB_CD": {
        # FIXED 2026-06-04 -- old ID wrong (1XJ4Jkk...). Correct from .gsheet file.
        # Tab: 04_MACHINE_DOWNTIME
        # GVIZ merged-cell fix: col0 fallback_first_col; col4='' -> "Thoi gian dung"
        # Full header: Ngay,Ca,Nha may,Ma may,[4=Thoi gian dung (phut)],Loai dung may,...
        "sheet_id":           "1_HhUXOaX9MeqsJC2I-NeTyPaII12sayyvtXMPFaUk0E",
        "tab_name":           "04_MACHINE_DOWNTIME",
        "description":        "Thiet Bi - Machine Downtime",
        "fallback_first_col": "Ngay",
        "fallback_columns":   {4: "Thời gian dừng (phút)"},
    },
    "05_KHO": {
        # FIXED 2026-06-04 Session 13 -- sheet_id corrected (old: 1G7tWo8K...).
        # Anh confirmed 2026-06-04: correct file is 1yl8K7TVN5XQXcWT3IlRWptoEg7J4Lb127aBHWE8Ve1s
        # Tab: 05_WIP_FIFO_KHO
        # GVIZ merged-cell fix: col0 fallback_first_col; col5,col6 fallback_columns
        # Full header: Ngay,Nha may,Khu vuc,Lenh SX,Cong doan,[5=SL ban TP],[6=So ngay ton],Trang thai FIFO,...
        "sheet_id":           "1yl8K7TVN5XQXcWT3IlRWptoEg7J4Lb127aBHWE8Ve1s",
        "tab_name":           "05_WIP_FIFO_KHO",
        "description":        "Kho - WIP/FIFO (V3 Inventory/Capacity/Aging)",
        "fallback_first_col": "Ngay",
        "fallback_columns":   {
            5: "SL bán thành phẩm",
            6: "Số ngày tồn",
        },
    },
    "06_GSTT": {
        # FIXED 2026-06-04 -- old ID wrong (1lgY4FT...). Correct from .gsheet file.
        # Tab: 06_GSTT_FIELD_LOG
        # GVIZ merged-cell fix: col9='' -> "Due_Date"
        # Full header: Check_Date,Shift,Site,Area,Category,Abnormality,Severity,Evidence_Link,Owner_Affected,[9=Due_Date],Status,...
        "sheet_id":           "1Xd38NfvIpPUjR2-MWo020hUSl-KGt--mF23udkXTYYs",
        "tab_name":           "06_GSTT_FIELD_LOG",
        "description":        "GSTT - Field Verification",
        "fallback_first_col": "Check_Date",
        "fallback_columns":   {9: "Due_Date"},
    },
    "07_CONG_NGHE_SPM": {
        # FIXED 2026-06-04 -- old ID wrong (1VdkEFm...). Correct from .gsheet file.
        # Tab: 08_SPM_TECH
        # GVIZ merged-cell fix: col6=Due_Date, col7=Ngay hoan thanh, col9=Leadtime_Days
        # Full header: Ngay,Nha may,KH,Sample_ID,Nhom SP,PIC,[6=Due_Date],[7=Ngay HT],Trang thai,[9=Leadtime],Redo_Count,...
        "sheet_id":           "1gegI7IkIb9145n15SXChsQEWww74YJqXS8s88WnGUas",
        "tab_name":           "08_SPM_TECH",
        "description":        "Cong Nghe - SPM Technology",
        "fallback_first_col": "Ngay",
        "fallback_columns":   {
            6: "Due_Date",
            7: "Ngày hoàn thành",
            9: "Leadtime_Days",
        },
    },
    "08_BO_CONTROL": {
        # FIXED 2026-06-04 -- old ID wrong (1DzPrZ2...). Correct from .gsheet file.
        # Tab: 09_ISSUE_ACTION
        # GVIZ merged-cell fix: col8='' -> "Due_Date"
        # Full header: Issue_Date,Source_Module,Site,Issue_Desc,Severity,Owner,PIC,Action_Required,[8=Due_Date],Status,...
        "sheet_id":           "12Bi3CKN1FTXDYmnXWxMNQAErYSTsjpWQF8NIaq4T84Q",
        "tab_name":           "09_ISSUE_ACTION",
        "description":        "BO Control - Issue/Action",
        "fallback_first_col": "Issue_Date",
        "fallback_columns":   {8: "Due_Date"},
    },
}

VALID_SITES = ["GS1", "GS5", "GS6", "GSQV"]
