"""
kpi_calculator.py — GSBB BO Control Tower
Reads  : logs/raw_data.json   (output of data_fetcher.py)
Reads  : logs/dqg_results.json (output of dqg_validator.py)
Outputs: logs/kpi_output.json

Only departments with DQG status PASS are used for official KPI.
WARN departments are included with a "use_with_caution" flag.
SKIP/FAIL departments are excluded from KPI.
"""

import json
import os
import datetime

# Absolute path: scripts/ → parent = repo root → logs/
_SCRIPT_DIR    = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT     = os.path.dirname(_SCRIPT_DIR)
LOGS_DIR       = os.path.join(_REPO_ROOT, "logs")
RAW_DATA_FILE  = os.path.join(LOGS_DIR, "raw_data.json")
DQG_FILE       = os.path.join(LOGS_DIR, "dqg_results.json")
KPI_FILE       = os.path.join(LOGS_DIR, "kpi_output.json")


# ─────────────────────────────────────────────────────────────
# Utility helpers
# ─────────────────────────────────────────────────────────────

def safe_float(val, default=0.0):
    """Parse a string to float; return default on failure."""
    try:
        cleaned = str(val).replace(",", ".").replace("%", "").strip()
        return float(cleaned)
    except (ValueError, TypeError):
        return default


def is_overdue(val):
    return str(val).strip().upper() in ("TRUE", "YES", "1", "CÓ", "CO", "X", "OVERDUE")


def rag_label(val):
    v = str(val).strip().upper()
    if v in ("R", "RED", "ĐỎ", "DO"):
        return "R"
    if v in ("A", "AMBER", "YELLOW", "VÀNG", "VANG"):
        return "A"
    if v in ("G", "GREEN", "XANH"):
        return "G"
    return "?"


def status_group(val,
                 open_vals=("OPEN", "IN PROGRESS", "IN_PROGRESS", "ĐANG XỬ LÝ", "PENDING",
                            "CHỚ", "CHƯA XỬ LÝ", "ĐANG LÀM", "MỜI"),
                 closed_vals=("CLOSED", "DONE", "COMPLETE", "COMPLETED", "ĐÃ ĐÓNG", "OK",
                              "HOÀN THàNH", "PASS", "ĐẠT", "XỬ LÝ XONG")):
    v = str(val).strip().upper()
    if v in open_vals:
        return "open"
    if v in closed_vals:
        return "closed"
    return "other"


# ─────────────────────────────────────────────────────────────
# Per-department KPI calculators
# ─────────────────────────────────────────────────────────────

def calc_san_xuat(records):
    """01_SAN_XUAT — Plan/DO, NG, RAG breakdown.
    Actual col names (Vietnamese): SL Ke hoach, SL Thuc te, SL Loi (NG), % Tuan thu KH, RAG
    """
    total_plan   = 0.0
    total_actual = 0.0
    total_ng     = 0.0
    rag_counts   = {"R": 0, "A": 0, "G": 0, "?": 0}
    plan_do_vals = []

    for r in records:
        total_plan   += safe_float(r.get("SL Kế hoạch", r.get("Plan_Qty", 0)))
        total_actual += safe_float(r.get("SL Thực tế", r.get("Actual_Qty", 0)))
        total_ng     += safe_float(r.get("SL Lỗi (NG)", r.get("NG_Qty", 0)))
        pd_raw = r.get("% Tuân thủ KH", r.get("Plan_Do_%", ""))
        pd = safe_float(pd_raw, default=None)
        if pd is not None and str(pd_raw).strip():
            plan_do_vals.append(pd)
        rag_counts[rag_label(r.get("RAG", "?"))] += 1

    plan_do_avg = round(sum(plan_do_vals) / len(plan_do_vals), 1) if plan_do_vals else None
    ng_pct      = round(total_ng / total_actual * 100, 2) if total_actual > 0 else None

    return {
        "total_plan_qty":   int(total_plan),
        "total_actual_qty": int(total_actual),
        "total_ng_qty":     int(total_ng),
        "plan_do_pct_avg":  plan_do_avg,
        "ng_pct":           ng_pct,
        "rag_R":            rag_counts["R"],
        "rag_A":            rag_counts["A"],
        "rag_G":            rag_counts["G"],
        "rag_unknown":      rag_counts["?"],
        "row_count":        len(records),
    }


def calc_qlcl(records):
    """03_QLCL — NCR/CAR count, severity, overdue, COPQ."""
    severity = {"Critical": 0, "Major": 0, "Minor": 0, "Other": 0}
    status   = {"open": 0, "closed": 0, "other": 0}
    overdue_count = 0
    copq_total    = 0.0

    # Actual cols: "Muc do" (severity), "Trang thai" (status), "Qua han?" (overdue), "COPQ uoc tinh (VND)"
    _sev_map = {
        "CRITICAL": "Critical", "NGHIêm TRọNG": "Critical", "NGHÊm TRọNG": "Critical",
        "MAJOR": "Major", "LỚN": "Major", "ĐạI": "Major",
        "MINOR": "Minor", "NHỏ": "Minor",
    }
    for r in records:
        sv_raw = str(r.get("Mức độ", r.get("Severity", ""))).strip()
        sv = _sev_map.get(sv_raw.upper(), "Other")
        if sv in severity:
            severity[sv] += 1
        else:
            severity["Other"] += 1

        st = status_group(r.get("Trạng thái", r.get("Status", "")))
        status[st] += 1

        if is_overdue(r.get("Quá hạn?", r.get("Overdue?", ""))):
            overdue_count += 1

        copq_total += safe_float(r.get("COPQ ước tính (VNĐ)", r.get("COPQ_Estimated", 0)))

    return {
        "total_ncr":        len(records),
        "open":             status["open"],
        "closed":           status["closed"],
        "severity_critical": severity["Critical"],
        "severity_major":   severity["Major"],
        "severity_minor":   severity["Minor"],
        "overdue_count":    overdue_count,
        "copq_estimated":   round(copq_total, 0),
        "row_count":        len(records),
    }


def calc_qltb_cd(records):
    """04_QLTB_CD — Downtime total, Breakdown vs PM, top machines."""
    total_dt  = 0.0
    breakdown = 0
    pm        = 0
    machine_dt = {}

    # Actual cols: "Thoi gian dung (phut)", "Loai dung may", "Ma may"
    _bp_breakdown = {"BREAKDOWN", "BD", "HỊNG MÁY", "SỰ CỐ", "HỊNG"}
    _bp_pm        = {"PM", "PREVENTIVE", "BẢO TRÌ", "BAO TRI", "BẢO DƯỤNG"}
    for r in records:
        dt = safe_float(r.get("Thời gian dừng (phút)", r.get("Downtime_Min", 0)))
        total_dt += dt

        bp = str(r.get("Loại dừng máy", r.get("Breakdown_PM", ""))).strip().upper()
        if bp in _bp_breakdown:
            breakdown += 1
        elif bp in _bp_pm:
            pm += 1

        machine = str(r.get("Mã máy", r.get("Machine", ""))).strip() or "Unknown"
        machine_dt[machine] = machine_dt.get(machine, 0.0) + dt

    top_machines = sorted(machine_dt.items(), key=lambda x: x[1], reverse=True)[:5]

    return {
        "total_downtime_min":  round(total_dt, 1),
        "total_downtime_hrs":  round(total_dt / 60, 2),
        "breakdown_events":    breakdown,
        "pm_events":           pm,
        "top_machines":        [{"machine": m, "downtime_min": round(dt, 1)} for m, dt in top_machines],
        "row_count":           len(records),
    }


def calc_kho(records):
    """05_KHO — WIP total, FIFO breach, age risk."""
    total_wip   = 0.0
    age_vals    = []
    fifo_status = {"OK": 0, "RISK": 0, "BREACH": 0, "Other": 0}
    risk_level  = {"High": 0, "Medium": 0, "Low": 0, "Other": 0}
    high_risk_wos = []

    # Actual cols: "SL ban thanh pham", "So ngay ton", "Trang thai FIFO", "Muc rui ro", "Lenh SX"
    _rl_map = {"CAO": "High", "HIGH": "High",
               "TRUNG BÌNH": "Medium", "MEDIUM": "Medium",
               "THẤP": "Low", "LOW": "Low"}
    for r in records:
        wip = safe_float(r.get("SL bán thành phẩm", r.get("WIP_Qty", 0)))
        total_wip += wip

        age = str(r.get("Số ngày tồn", r.get("Age_Days", ""))).strip()
        if age:
            age_vals.append(safe_float(age))

        fs = str(r.get("Trạng thái FIFO", r.get("FIFO_Status", ""))).strip().upper()
        if fs in ("OK", "ĐẠT", "TỐT"):
            fifo_status["OK"] += 1
        elif fs in ("RISK", "AT RISK", "RỦI RO", "CẦN KIỂM TRA"):
            fifo_status["RISK"] += 1
        elif fs in ("BREACH", "VIOLATED", "VI PHẠM", "QUÁ HẠN"):
            fifo_status["BREACH"] += 1
        else:
            fifo_status["Other"] += 1

        rl_raw = str(r.get("Mức rủi ro", r.get("Risk_Level", ""))).strip()
        rl = _rl_map.get(rl_raw.upper(), "Other")
        if rl in risk_level:
            risk_level[rl] += 1
        else:
            risk_level["Other"] += 1

        if rl == "High":
            high_risk_wos.append(str(r.get("Lệnh SX", r.get("Work_Order", ""))).strip())

    age_avg = round(sum(age_vals) / len(age_vals), 1) if age_vals else None

    return {
        "total_wip_qty":    round(total_wip, 0),
        "fifo_ok":          fifo_status["OK"],
        "fifo_risk":        fifo_status["RISK"],
        "fifo_breach":      fifo_status["BREACH"],
        "age_days_avg":     age_avg,
        "risk_high":        risk_level["High"],
        "risk_medium":      risk_level["Medium"],
        "risk_low":         risk_level["Low"],
        "high_risk_wos":    high_risk_wos[:10],
        "row_count":        len(records),
    }


def calc_gstt(records):
    """06_GSTT — Field verification issues, severity, status, escalation."""
    severity  = {"Critical": 0, "Major": 0, "Minor": 0, "Other": 0}
    status    = {"open": 0, "closed": 0, "other": 0}
    escalated = 0

    for r in records:
        sv = str(r.get("Severity", "")).strip()
        if sv in severity:
            severity[sv] += 1
        else:
            severity["Other"] += 1

        st = status_group(r.get("Status", ""))
        status[st] += 1

        esc = str(r.get("Escalation_Level", "")).strip()
        if esc and esc.upper() not in ("", "NONE", "-", "N/A"):
            escalated += 1

    return {
        "total_issues":      len(records),
        "open":              status["open"],
        "closed":            status["closed"],
        "severity_critical": severity["Critical"],
        "severity_major":    severity["Major"],
        "severity_minor":    severity["Minor"],
        "escalated":         escalated,
        "row_count":         len(records),
    }


def calc_cong_nghe_spm(records):
    """07_CONG_NGHE_SPM — Sample status, leadtime, redo, risk."""
    status   = {"open": 0, "closed": 0, "other": 0}
    lead_vals = []
    redo_total = 0
    risk_high  = 0

    # Actual cols: "Trang thai" (Status); Leadtime_Days, Redo_Count, Risk_Level are English (kept as-is)
    for r in records:
        st = status_group(r.get("Trạng thái", r.get("Status", "")))
        status[st] += 1

        lt = r.get("Leadtime_Days", "").strip()
        if lt:
            lead_vals.append(safe_float(lt))

        redo_total += int(safe_float(r.get("Redo_Count", 0)))

        if str(r.get("Risk_Level", "")).strip() == "High":
            risk_high += 1

    lead_avg = round(sum(lead_vals) / len(lead_vals), 1) if lead_vals else None

    return {
        "total_samples":    len(records),
        "in_progress":      status["open"],
        "completed":        status["closed"],
        "leadtime_avg_days": lead_avg,
        "redo_count_total": redo_total,
        "risk_high":        risk_high,
        "row_count":        len(records),
    }


def calc_bo_control(records):
    """08_BO_CONTROL — Open issues, overdue, severity, escalation."""
    severity  = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0, "Other": 0}
    status    = {"open": 0, "closed": 0, "other": 0}
    overdue_count = 0
    escalated = 0

    for r in records:
        sv = str(r.get("Severity", "")).strip()
        if sv in severity:
            severity[sv] += 1
        else:
            severity["Other"] += 1

        st = status_group(r.get("Status", ""))
        status[st] += 1

        if is_overdue(r.get("Overdue?", "")):
            overdue_count += 1

        esc = str(r.get("Escalation_Level", "")).strip()
        if esc and esc.upper() not in ("", "NONE", "-", "N/A"):
            escalated += 1

    return {
        "total_issues":      len(records),
        "open":              status["open"],
        "closed":            status["closed"],
        "overdue":           overdue_count,
        "severity_critical": severity["Critical"],
        "severity_high":     severity["High"],
        "severity_medium":   severity["Medium"],
        "escalated":         escalated,
        "row_count":         len(records),
    }


def calc_khsx_otif(records):
    """02_KHSX_OTIF — OTIF rate, late count.
    Actual columns: Commit_Date, Actual_Delivery_Date, Site, Customer, Work_Order,
    Committed_Qty, Delivered_Qty, OTIF?, Delay_Days, Delivery_Risk, ...
    """
    if not records:
        return {"note": "No data", "row_count": 0}

    # Actual cols: "Dung han?" (OTIF), "So ngay tre" (delay), "Rui ro giao hang" (risk)
    on_time   = sum(1 for r in records
                    if str(r.get("Đúng hạn?", r.get("OTIF?", ""))).strip().upper()
                    in ("YES", "Y", "ON TIME", "OK", "PASS", "CÓ", "CO", "X", "ĐÚNG"))
    late      = len(records) - on_time
    otif_pct  = round(on_time / len(records) * 100, 1) if records else None

    delay_col = "Số ngày trễ"
    delay_vals = [safe_float(r.get(delay_col, r.get("Delay_Days", "")))
                  for r in records if str(r.get(delay_col, r.get("Delay_Days", ""))).strip()]
    avg_delay  = round(sum(delay_vals) / len(delay_vals), 1) if delay_vals else 0.0

    risk_high = sum(1 for r in records
                    if str(r.get("Rủi ro giao hàng", r.get("Delivery_Risk", ""))).strip().upper()
                    in ("HIGH", "CAO"))

    return {
        "total_orders":  len(records),
        "on_time":       on_time,
        "late":          late,
        "otif_pct":      otif_pct,
        "avg_delay_days": avg_delay,
        "risk_high":     risk_high,
        "row_count":     len(records),
    }


# ─────────────────────────────────────────────────────────────
# KPI dispatcher
# ─────────────────────────────────────────────────────────────

KPI_CALC = {
    "01_SAN_XUAT":      calc_san_xuat,
    "02_KHSX_OTIF":     calc_khsx_otif,
    "03_QLCL":          calc_qlcl,
    "04_QLTB_CD":       calc_qltb_cd,
    "05_KHO":           calc_kho,
    "06_GSTT":          calc_gstt,
    "07_CONG_NGHE_SPM": calc_cong_nghe_spm,
    "08_BO_CONTROL":    calc_bo_control,
}


# ─────────────────────────────────────────────────────────────
# Site breakdown helper
# ─────────────────────────────────────────────────────────────

VALID_SITES = ["GS1", "GS5", "GS6", "GSQV"]


def calc_site_breakdown(dept_key: str, records: list) -> dict:
    """
    Compute per-site KPIs by filtering records on the 'Site' column.
    Returns { "GS1": {...}, "GS5": {...}, "GS6": {...}, "GSQV": {...} }
    Only includes sites that have at least 1 record.
    """
    calc_fn = KPI_CALC.get(dept_key)
    if not calc_fn:
        return {}

    result = {}
    for site in VALID_SITES:
        site_recs = [r for r in records
                     if r.get("Site", r.get("site", r.get("Nhà máy", ""))).strip() == site]
        if site_recs:
            try:
                result[site] = {"kpis": calc_fn(site_recs), "row_count": len(site_recs)}
            except Exception as e:
                result[site] = {"kpis": {}, "row_count": len(site_recs), "error": str(e)}
        else:
            result[site] = {"kpis": None, "row_count": 0, "note": "No data for this site"}
    return result


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────

def run_kpi():
    os.makedirs(LOGS_DIR, exist_ok=True)

    # Load raw data
    if not os.path.exists(RAW_DATA_FILE):
        print("❌ raw_data.json not found — run data_fetcher.py first")
        return {}
    with open(RAW_DATA_FILE, "r", encoding="utf-8") as f:
        raw = json.load(f)

    # Load DQG results
    if not os.path.exists(DQG_FILE):
        print("❌ dqg_results.json not found — run dqg_validator.py first")
        return {}
    with open(DQG_FILE, "r", encoding="utf-8") as f:
        dqg = json.load(f)

    departments_raw = raw.get("departments", {})
    departments_dqg = dqg.get("departments", {})

    print(f"\n{'='*60}")
    print(f"GSBB BO Control Tower — KPI Calculator")
    print(f"Timestamp: {datetime.datetime.utcnow().isoformat()}Z")
    print(f"{'='*60}\n")

    kpi_results = {}

    for dept_key, raw_data in departments_raw.items():
        dqg_result  = departments_dqg.get(dept_key, {})
        dqg_status  = dqg_result.get("dqg_status", "SKIP")
        description = raw_data.get("description", dept_key)
        records     = raw_data.get("records", [])

        icon = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌", "SKIP": "⏳"}.get(dqg_status, "?")

        # Only calculate for PASS (and WARN with caution flag)
        if dqg_status == "PASS":
            calc_fn = KPI_CALC.get(dept_key)
            if calc_fn:
                kpis           = calc_fn(records)
                site_breakdown = calc_site_breakdown(dept_key, records)
                kpi_results[dept_key] = {
                    "dept":           dept_key,
                    "description":    description,
                    "dqg_status":     dqg_status,
                    "official":       True,
                    "kpis":           kpis,
                    "site_breakdown": site_breakdown,
                    "calculated_at":  datetime.datetime.utcnow().isoformat() + "Z",
                }
                print(f"  {icon} [{dept_key}] PASS — KPI calculated: {list(kpis.keys())[:4]}...")
            else:
                kpi_results[dept_key] = {
                    "dept": dept_key, "description": description,
                    "dqg_status": dqg_status, "official": True,
                    "kpis": {}, "note": "No KPI calculator defined for this dept",
                    "calculated_at": datetime.datetime.utcnow().isoformat() + "Z",
                }
                print(f"  {icon} [{dept_key}] PASS — No calculator defined, KPI empty")

        elif dqg_status == "WARN":
            calc_fn = KPI_CALC.get(dept_key)
            if calc_fn:
                kpis = calc_fn(records)
            else:
                kpis = {}
            kpi_results[dept_key] = {
                "dept": dept_key, "description": description,
                "dqg_status": dqg_status, "official": False,
                "use_with_caution": True,
                "kpis": kpis,
                "calculated_at": datetime.datetime.utcnow().isoformat() + "Z",
            }
            print(f"  {icon} [{dept_key}] WARN — KPI calculated (use with caution)")

        else:
            # SKIP / FAIL / PENDING — no KPI
            kpi_results[dept_key] = {
                "dept": dept_key, "description": description,
                "dqg_status": dqg_status, "official": False,
                "kpis": None,
                "note": dqg_result.get("issues", ["No data available"])[0] if dqg_result.get("issues") else "No data",
                "calculated_at": datetime.datetime.utcnow().isoformat() + "Z",
            }
            print(f"  {icon} [{dept_key}] {dqg_status} — Excluded from KPI")

    # Summary
    pass_count = sum(1 for v in kpi_results.values() if v.get("dqg_status") == "PASS")
    skip_count = sum(1 for v in kpi_results.values() if v.get("dqg_status") in ("SKIP", "PENDING"))
    fail_count = sum(1 for v in kpi_results.values() if v.get("dqg_status") == "FAIL")

    summary = {
        "total_depts":    len(kpi_results),
        "kpi_official":   pass_count,
        "kpi_skipped":    skip_count,
        "kpi_excluded":   fail_count,
        "generated_at":   datetime.datetime.utcnow().isoformat() + "Z",
    }

    output = {
        "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
        "summary":      summary,
        "departments":  kpi_results,
    }

    with open(KPI_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"KPI output saved → logs/kpi_output.json")
    print(f"Summary: official={pass_count} | skipped={skip_count} | excluded={fail_count}")
    print(f"{'='*60}\n")

    return kpi_results


if __name__ == "__main__":
    run_kpi()
