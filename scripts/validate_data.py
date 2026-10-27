from __future__ import annotations

import csv
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"


def read_csv(name: str) -> list[dict[str, str]]:
    path = DATA_DIR / name
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def number(row: dict[str, str], field: str) -> float | None:
    value = row.get(field, "")
    if value == "":
        return None
    return float(value)


def main() -> None:
    errors: list[str] = []
    warnings: list[str] = []
    companies = read_csv("companies.csv")
    annual = read_csv("company_years.csv")
    welfare = read_csv("employee_welfare.csv")
    evidence = read_csv("metric_evidence.csv")

    company_ids = {row["company_id"] for row in companies}
    if len(companies) != 30:
        errors.append(f"companies.csv should contain 30 rows, found {len(companies)}")
    if len(company_ids) != 30:
        errors.append("company_id values are not unique")
    if any(row.get("is_synthetic") != "true" for row in companies):
        errors.append("All companies must have is_synthetic=true")

    industry_counts = Counter(row["industry"] for row in companies)
    expected_industries = {
        "manufacturing": 10,
        "technology": 10,
        "retail_logistics_service": 10,
    }
    if dict(industry_counts) != expected_industries:
        errors.append(f"Unexpected industry distribution: {dict(industry_counts)}")

    if len(annual) != 90:
        errors.append(f"company_years.csv should contain 90 rows, found {len(annual)}")
    if len(welfare) != 90:
        errors.append(f"employee_welfare.csv should contain 90 rows, found {len(welfare)}")

    annual_keys = {(row["company_id"], row["year"]) for row in annual}
    welfare_keys = {(row["company_id"], row["year"]) for row in welfare}
    if len(annual_keys) != len(annual):
        errors.append("Duplicate company-year key in company_years.csv")
    if len(welfare_keys) != len(welfare):
        errors.append("Duplicate company-year key in employee_welfare.csv")
    if annual_keys != welfare_keys:
        errors.append("Company-year keys do not match between annual and welfare tables")

    annual_by_key = {(row["company_id"], row["year"]): row for row in annual}
    for row in annual:
        key = f"{row['company_id']}:{row['year']}"
        if row["company_id"] not in company_ids:
            errors.append(f"Unknown company ID in annual data: {key}")
        revenue = number(row, "revenue")
        start = number(row, "employee_count_start")
        end = number(row, "employee_count_end")
        if revenue is None or revenue <= 0:
            errors.append(f"Revenue must be positive: {key}")
        if start is None or start <= 0 or end is None or end <= 0:
            errors.append(f"Employee count must be positive: {key}")
        for field in ("operating_cost", "taxes_paid", "depreciation_amortization", "rd_expense", "cash_dividend", "share_buyback"):
            value = number(row, field)
            if value is not None and value < 0:
                errors.append(f"{field} cannot be negative: {key}")
        if number(row, "rd_employee_count") > end:
            errors.append(f"R&D employee count exceeds employees: {key}")
        if number(row, "production_employee_count") > end:
            errors.append(f"Production employee count exceeds employees: {key}")
        margin = number(row, "net_profit") / revenue
        if abs(margin) > 0.50:
            warnings.append(f"Extreme net profit margin {margin:.1%}: {key}")

    ratio_fields = {
        "overtime_pay_coverage", "social_insurance_coverage", "housing_fund_coverage",
        "paid_leave_usage", "turnover_rate", "training_coverage", "contractor_welfare_ratio",
    }
    for row in welfare:
        key_tuple = (row["company_id"], row["year"])
        key = f"{row['company_id']}:{row['year']}"
        for field in ratio_fields:
            value = number(row, field)
            if value is not None and not 0 <= value <= 1:
                errors.append(f"{field} outside 0..1: {key}")
        avg_hours = number(row, "average_weekly_hours")
        p90_hours = number(row, "p90_weekly_hours")
        if avg_hours is not None and p90_hours is not None and p90_hours < avg_hours:
            errors.append(f"P90 hours lower than average hours: {key}")
        p10 = number(row, "p10_annual_income")
        median = number(row, "median_annual_income")
        if p10 is not None and median is not None and p10 >= median:
            errors.append(f"P10 income must be lower than median income: {key}")
        annual_row = annual_by_key[key_tuple]
        cash = number(annual_row, "employee_cash_paid")
        start = number(annual_row, "employee_count_start")
        end = number(annual_row, "employee_count_end")
        per_employee_cash = cash / ((start + end) / 2.0)
        if median is not None and median >= per_employee_cash:
            errors.append(f"Median income must be lower than per-employee cash investment: {key}")
        contractor_count = number(row, "contractor_count")
        if contractor_count is not None and contractor_count < 0:
            errors.append(f"Contractor count cannot be negative: {key}")
        fatalities = number(row, "major_fatality_count")
        injury = number(row, "work_injury_rate_per_1000")
        if fatalities is not None and fatalities < 0:
            errors.append(f"Fatality count cannot be negative: {key}")
        if injury is not None and injury < 0:
            errors.append(f"Injury rate cannot be negative: {key}")

    expected_evidence = len(annual) * 17 + len(welfare) * 16
    if len(evidence) != expected_evidence:
        errors.append(f"metric_evidence.csv expected {expected_evidence} rows, found {len(evidence)}")

    coverage = {}
    if welfare:
        for field in welfare[0]:
            if field in {"company_id", "year"}:
                continue
            present = sum(1 for row in welfare if row.get(field, "") != "")
            coverage[field] = present / len(welfare)

    print(f"Companies: {len(companies)}")
    print(f"Company-year rows: {len(annual)}")
    print(f"Employee-welfare rows: {len(welfare)}")
    print(f"Metric-evidence rows: {len(evidence)}")
    print("Welfare field coverage:")
    for field, value in sorted(coverage.items()):
        print(f"  {field}: {value:.1%}")

    if warnings:
        print(f"Warnings: {len(warnings)}")
        for warning in warnings[:20]:
            print(f"  WARNING: {warning}")
    if errors:
        print(f"Errors: {len(errors)}")
        for error in errors:
            print(f"  ERROR: {error}")
        sys.exit(1)

    print("VALIDATION_OK")


if __name__ == "__main__":
    main()

