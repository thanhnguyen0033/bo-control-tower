"""
main_pipeline.py — GSBB BO Control Tower
Orchestrates the full pipeline end-to-end:
  1. Fetch data from Google Sheets (CSV export)
  2. Run Data Quality Gate (DQG)
  3. Calculate KPIs
  4. Build HTML dashboard

Called by GitHub Actions workflow.
Can also be run locally: python main_pipeline.py
"""

import sys
import os

# Ensure scripts/ is importable when run from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "scripts"))

from scripts.data_fetcher   import fetch_all_sheets
from scripts.dqg_validator  import run_dqg
from scripts.kpi_calculator import run_kpi
from scripts.dashboard_builder import main as build_dashboard


def main():
    print("\n" + "=" * 60)
    print("  GSBB BO Control Tower — Full Pipeline")
    print("  Fetch → DQG → KPI → Dashboard")
    print("=" * 60 + "\n")

    # Step 1: Fetch
    print("STEP 1/4 — Fetch data from Google Sheets")
    fetch_results = fetch_all_sheets()
    ok_count = sum(1 for v in fetch_results.values() if v.get("status") == "OK")
    print(f"  → Fetched: {ok_count}/{len(fetch_results)} sheets OK\n")

    # Step 2: DQG
    print("STEP 2/4 — Data Quality Gate")
    dqg_results = run_dqg()
    pass_count = sum(1 for v in dqg_results.values() if v.get("dqg_status") == "PASS")
    print(f"  → DQG: {pass_count}/{len(dqg_results)} PASS\n")

    # Step 3: KPI
    print("STEP 3/4 — KPI Calculation")
    kpi_results = run_kpi()
    kpi_count = sum(1 for v in kpi_results.values() if v.get("official"))
    print(f"  → KPI official: {kpi_count}/{len(kpi_results)} depts\n")

    # Step 4: Dashboard
    print("STEP 4/4 — Build Dashboard")
    build_dashboard()
    print()

    print("=" * 60)
    print("  Pipeline complete.")
    print(f"  Dashboard → docs/index.html")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
