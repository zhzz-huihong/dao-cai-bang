from __future__ import annotations

import csv
import math
import random
from pathlib import Path


SEED = 20261027
GENERATOR_VERSION = "synthetic_generator_v1"
YEARS = (2023, 2024, 2025)

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
COMPANIES_PATH = DATA_DIR / "companies.csv"

INDUSTRY = {
    "manufacturing": {
        "revenue_per_employee": 800_000,
        "profit_margin": 0.075,
        "cash_per_employee": 145_000,
        "gross_margin": 0.25,
        "hours": 46.0,
        "contractor_ratio": 0.18,
        "injury_rate": 3.0,
        "rd_ratio": 0.045,
        "asset_ratio": 1.35,
        "exec_multiple": 13.0,
    },
    "technology": {
        "revenue_per_employee": 1_400_000,
        "profit_margin": 0.16,
        "cash_per_employee": 300_000,
        "gross_margin": 0.55,
        "hours": 46.0,
        "contractor_ratio": 0.12,
        "injury_rate": 0.4,
        "rd_ratio": 0.15,
        "asset_ratio": 0.75,
        "exec_multiple": 18.0,
    },
    "retail_logistics_service": {
        "revenue_per_employee": 450_000,
        "profit_margin": 0.055,
        "cash_per_employee": 105_000,
        "gross_margin": 0.20,
        "hours": 48.0,
        "contractor_ratio": 0.28,
        "injury_rate": 2.0,
        "rd_ratio": 0.02,
        "asset_ratio": 0.65,
        "exec_multiple": 11.0,
    },
}

SIZE_EMPLOYEES = {
    "small": 650,
    "medium": 2_600,
    "large": 12_000,
    "very_large": 50_000,
}

REGION_LIVING_WAGE_2023 = {
    "tier_1": 82_000,
    "new_tier_1": 68_000,
    "other_city": 54_000,
    "multi_region": 65_000,
}

WELFARE_FIELDS = [
    "p10_annual_income",
    "median_annual_income",
    "local_living_wage",
    "average_weekly_hours",
    "p90_weekly_hours",
    "overtime_pay_coverage",
    "social_insurance_coverage",
    "housing_fund_coverage",
    "paid_leave_usage",
    "turnover_rate",
    "training_coverage",
    "work_injury_rate_per_1000",
    "major_fatality_count",
    "contractor_count",
    "contractor_welfare_ratio",
    "employee_voice_score",
]

WELFARE_FIELD_FACTOR = {
    "p10_annual_income": 0.62,
    "median_annual_income": 0.70,
    "local_living_wage": 0.92,
    "average_weekly_hours": 0.62,
    "p90_weekly_hours": 0.50,
    "overtime_pay_coverage": 0.58,
    "social_insurance_coverage": 0.92,
    "housing_fund_coverage": 0.78,
    "paid_leave_usage": 0.52,
    "turnover_rate": 0.62,
    "training_coverage": 0.75,
    "work_injury_rate_per_1000": 0.82,
    "major_fatality_count": 0.90,
    "contractor_count": 0.55,
    "contractor_welfare_ratio": 0.40,
    "employee_voice_score": 0.48,
}

YEARLY_TRENDS = {
    "improving": [(0.08, 0.035), (0.11, 0.045), (0.12, 0.05)],
    "stable": [(0.045, 0.015), (0.05, 0.018), (0.05, 0.018)],
    "deteriorating": [(0.035, 0.005), (0.015, -0.025), (-0.01, -0.04)],
    "volatile": [(0.12, 0.06), (-0.055, -0.035), (0.15, 0.07)],
}


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def jitter(rng: random.Random, value: float, spread: float) -> float:
    return value * rng.uniform(1.0 - spread, 1.0 + spread)


def round_money(value: float) -> int:
    return int(round(value / 1000.0) * 1000)


def read_companies() -> list[dict[str, str]]:
    with COMPANIES_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 30:
        raise ValueError(f"Expected 30 companies, found {len(rows)}")
    return rows


def archetype_adjustments(company: dict[str, str]) -> dict[str, float]:
    labels = {company["primary_archetype"], company["secondary_archetype"]}
    adj = {
        "profit": 1.0,
        "cash": 1.0,
        "hours": 0.0,
        "benefits": 0.0,
        "turnover": 0.0,
        "exec": 1.0,
        "payout": 0.28,
        "buyback": 0.03,
        "contractor": 0.0,
        "contractor_welfare": 0.0,
        "cash_growth": 0.0,
        "voice": 0.0,
    }

    if labels & {"高财富、高分享"}:
        adj.update(profit=1.28, cash=1.22, benefits=0.09, voice=8.0)
    if labels & {"高分享型"}:
        adj.update(cash=1.22, benefits=0.10, voice=9.0)
    if labels & {"高财富、低分享"}:
        adj["profit"] *= 1.30
        adj["cash"] *= 0.83
        adj["cash_growth"] -= 0.025
    if labels & {"低财富、高善待"}:
        adj["profit"] *= 0.66
        adj["cash"] *= 1.10
        adj["benefits"] += 0.10
        adj["payout"] *= 0.55
        adj["voice"] += 10.0
    if labels & {"高薪、高工时"}:
        adj["cash"] *= 1.20
        adj["hours"] += 8.0
        adj["turnover"] += 0.04
    if labels & {"低薪、低工时"}:
        adj["cash"] *= 0.76
        adj["hours"] -= 4.0
    if labels & {"低薪、高工时"}:
        adj["cash"] *= 0.72
        adj["hours"] += 8.0
        adj["turnover"] += 0.10
    if labels & {"低薪、高流动"}:
        adj["cash"] *= 0.76
        adj["turnover"] += 0.14
    if labels & {"高工时型"}:
        adj["hours"] += 7.0
        adj["turnover"] += 0.06
    if labels & {"高管差距型"}:
        adj["exec"] *= 2.35
    if labels & {"股东优先型"}:
        adj["payout"] = 0.62
        adj["buyback"] = 0.10
        adj["cash_growth"] -= 0.02
    if labels & {"共同成长型"}:
        adj["cash_growth"] += 0.035
        adj["benefits"] += 0.04
    if labels & {"持续改善型"}:
        adj["cash_growth"] += 0.025
        adj["benefits"] += 0.03
        adj["voice"] += 5.0
    if labels & {"外包规避型"}:
        adj["contractor"] += 0.28
        adj["contractor_welfare"] -= 0.26
    if labels & {"数据透明型"}:
        adj["voice"] += 4.0
    if labels & {"就业稳定型"}:
        adj["turnover"] -= 0.055
    if labels & {"快速扩张型"}:
        adj["turnover"] += 0.05

    return adj


def benefit_value(base: float, adj: dict[str, float], year_index: int, trend: str) -> float:
    trend_delta = 0.0
    if trend == "improving":
        trend_delta = 0.025 * year_index
    elif trend == "deteriorating":
        trend_delta = -0.025 * year_index
    return clamp(base + adj["benefits"] + trend_delta, 0.0, 1.0)


def apply_missingness(
    rng: random.Random,
    values: dict[str, object],
    profile: str,
) -> dict[str, object]:
    missing_ranges = {
        "high": (0, 2),
        "medium": (3, 5),
        "low": (6, 8),
    }
    target = rng.randint(*missing_ranges[profile])
    protected = {"local_living_wage"}
    if float(values["major_fatality_count"]) > 0:
        protected.add("major_fatality_count")
    candidates = [field for field in WELFARE_FIELDS if field not in protected]
    missing: set[str] = set()
    while len(missing) < target and candidates:
        weights = [max(0.05, 1.0 - WELFARE_FIELD_FACTOR[field]) for field in candidates]
        selected = rng.choices(candidates, weights=weights, k=1)[0]
        missing.add(selected)
        candidates.remove(selected)
    return {field: ("" if field in missing else values[field]) for field in WELFARE_FIELDS}


def generate_company(
    rng: random.Random,
    company: dict[str, str],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    params = INDUSTRY[company["industry"]]
    adj = archetype_adjustments(company)
    trend = company["trend_profile"]
    size_base = SIZE_EMPLOYEES[company["size_band"]]
    start_employees = max(1, int(jitter(rng, size_base, 0.20)))
    revenue_per_employee = jitter(rng, params["revenue_per_employee"], 0.18)
    base_cash_per_employee = jitter(rng, params["cash_per_employee"] * adj["cash"], 0.10)
    base_profit_margin = jitter(rng, params["profit_margin"] * adj["profit"], 0.15)
    previous_revenue: float | None = None
    previous_cash_per_employee: float | None = None
    company_year_rows: list[dict[str, object]] = []
    welfare_rows: list[dict[str, object]] = []

    for year_index, year in enumerate(YEARS):
        revenue_growth, employee_growth = YEARLY_TRENDS[trend][year_index]
        revenue_growth += rng.uniform(-0.018, 0.018)
        employee_growth += rng.uniform(-0.012, 0.012)

        if year_index == 0:
            employee_start = start_employees
            employee_end = max(1, int(employee_start * (1.0 + employee_growth)))
            avg_employees = (employee_start + employee_end) / 2.0
            revenue = avg_employees * revenue_per_employee
            cash_per_employee = base_cash_per_employee
        else:
            employee_start = int(company_year_rows[-1]["employee_count_end"])
            employee_end = max(1, int(employee_start * (1.0 + employee_growth)))
            avg_employees = (employee_start + employee_end) / 2.0
            revenue = float(previous_revenue) * (1.0 + revenue_growth)
            cash_growth = 0.035 + adj["cash_growth"]
            if trend == "improving":
                cash_growth += 0.025
            elif trend == "deteriorating":
                cash_growth -= 0.025
            elif trend == "volatile":
                cash_growth += 0.05 if year == 2025 else -0.025
            cash_growth += rng.uniform(-0.012, 0.012)
            cash_per_employee = float(previous_cash_per_employee) * (1.0 + cash_growth)

        previous_revenue = revenue
        previous_cash_per_employee = cash_per_employee

        margin = base_profit_margin
        if trend == "improving":
            margin *= 1.0 + 0.06 * year_index
        elif trend == "deteriorating":
            margin *= 1.0 - 0.10 * year_index
        elif trend == "volatile":
            margin *= (1.0, 0.68, 1.12)[year_index]
        margin = clamp(margin + rng.uniform(-0.008, 0.008), -0.12, 0.36)

        operating_cost = revenue * clamp(1.0 - params["gross_margin"] + rng.uniform(-0.03, 0.03), 0.25, 1.08)
        profit_before_tax = revenue * margin
        net_profit = profit_before_tax * (0.76 if profit_before_tax >= 0 else 0.90)
        total_assets = revenue * jitter(rng, params["asset_ratio"], 0.12)
        depreciation = total_assets * jitter(rng, 0.04, 0.15)
        operating_cash_flow = net_profit + depreciation + revenue * rng.uniform(-0.025, 0.035)
        taxes_paid = max(0.0, profit_before_tax * 0.18) + revenue * jitter(rng, 0.009, 0.18)
        rd_expense = revenue * jitter(rng, params["rd_ratio"], 0.16)
        employee_cash_paid = avg_employees * cash_per_employee
        executive_pay = cash_per_employee * params["exec_multiple"] * adj["exec"] * rng.uniform(0.88, 1.12)
        payout_base = max(0.0, net_profit)
        cash_dividend = payout_base * clamp(adj["payout"] + rng.uniform(-0.045, 0.045), 0.0, 0.85)
        share_buyback = payout_base * clamp(adj["buyback"] + rng.uniform(-0.015, 0.02), 0.0, 0.22)
        rd_count = int(employee_end * clamp(params["rd_ratio"] * 1.8 + rng.uniform(-0.02, 0.025), 0.02, 0.52))
        production_share = 0.56 if company["industry"] == "manufacturing" else 0.08
        if company["industry"] == "retail_logistics_service":
            production_share = 0.34
        production_count = int(employee_end * clamp(production_share + rng.uniform(-0.04, 0.04), 0.0, 0.72))

        company_year = {
            "company_id": company["company_id"],
            "year": year,
            "revenue": round_money(revenue),
            "operating_cost": round_money(max(0.0, operating_cost)),
            "profit_before_tax": round_money(profit_before_tax),
            "net_profit": round_money(net_profit),
            "total_assets": round_money(total_assets),
            "operating_cash_flow": round_money(operating_cash_flow),
            "taxes_paid": round_money(taxes_paid),
            "depreciation_amortization": round_money(depreciation),
            "rd_expense": round_money(rd_expense),
            "cash_dividend": round_money(cash_dividend),
            "share_buyback": round_money(share_buyback),
            "employee_count_start": employee_start,
            "employee_count_end": employee_end,
            "employee_cash_paid": round_money(employee_cash_paid),
            "highest_executive_pay": round_money(executive_pay),
            "rd_employee_count": rd_count,
            "production_employee_count": production_count,
        }
        company_year_rows.append(company_year)

        median_ratio = clamp(0.63 + adj["benefits"] * 0.12 + rng.uniform(-0.025, 0.025), 0.53, 0.74)
        median_income = cash_per_employee * median_ratio
        p10_ratio = clamp(0.62 + adj["benefits"] * 0.18 + rng.uniform(-0.04, 0.04), 0.48, 0.76)
        p10_income = median_income * p10_ratio
        living_wage = REGION_LIVING_WAGE_2023[company["region_type"]] * (1.03 ** year_index)
        hours = params["hours"] + adj["hours"] + rng.uniform(-1.4, 1.4)
        if trend == "improving":
            hours -= 0.8 * year_index
        elif trend == "deteriorating":
            hours += 0.9 * year_index
        hours = clamp(hours, 36.0, 64.0)
        p90_hours = clamp(hours + rng.uniform(5.0, 12.0), hours, 78.0)
        overtime_coverage = benefit_value(0.74, adj, year_index, trend)
        social_coverage = benefit_value(0.88, adj, year_index, trend)
        housing_coverage = benefit_value(0.72, adj, year_index, trend)
        leave_usage = benefit_value(0.61, adj, year_index, trend)
        training_coverage = benefit_value(0.68, adj, year_index, trend)
        voice_score = clamp(58.0 + adj["voice"] + (3.0 * year_index if trend == "improving" else 0.0) + rng.uniform(-5, 5), 20, 95)
        income_pressure = max(0.0, 1.0 - p10_income / living_wage)
        turnover = 0.12 + adj["turnover"] + max(0.0, hours - 45.0) * 0.006 + income_pressure * 0.12
        turnover -= (social_coverage - 0.8) * 0.18
        if trend == "improving":
            turnover -= 0.018 * year_index
        elif trend == "deteriorating":
            turnover += 0.02 * year_index
        turnover = clamp(turnover + rng.uniform(-0.018, 0.018), 0.025, 0.58)
        injury = params["injury_rate"] * rng.uniform(0.65, 1.35)
        if trend == "improving":
            injury *= 1.0 - 0.08 * year_index
        elif trend == "deteriorating":
            injury *= 1.0 + 0.10 * year_index
        contractor_ratio = clamp(params["contractor_ratio"] + adj["contractor"] + rng.uniform(-0.04, 0.04), 0.01, 0.72)
        contractor_count = int(employee_end * contractor_ratio / max(0.01, 1.0 - contractor_ratio))
        contractor_welfare = clamp(0.79 + adj["contractor_welfare"] + adj["benefits"] * 0.3 + rng.uniform(-0.04, 0.04), 0.35, 0.98)
        fatalities = 0
        if company["company_id"] == "SYN-MFG-006" and year == 2024:
            fatalities = 1
        if company["company_id"] == "SYN-SVC-002" and year == 2025:
            fatalities = 1

        welfare_raw = {
            "p10_annual_income": round_money(p10_income),
            "median_annual_income": round_money(median_income),
            "local_living_wage": round_money(living_wage),
            "average_weekly_hours": round(hours, 1),
            "p90_weekly_hours": round(p90_hours, 1),
            "overtime_pay_coverage": round(overtime_coverage, 4),
            "social_insurance_coverage": round(social_coverage, 4),
            "housing_fund_coverage": round(housing_coverage, 4),
            "paid_leave_usage": round(leave_usage, 4),
            "turnover_rate": round(turnover, 4),
            "training_coverage": round(training_coverage, 4),
            "work_injury_rate_per_1000": round(max(0.0, injury), 3),
            "major_fatality_count": fatalities,
            "contractor_count": contractor_count,
            "contractor_welfare_ratio": round(contractor_welfare, 4),
            "employee_voice_score": round(voice_score, 1),
        }
        welfare = {"company_id": company["company_id"], "year": year}
        welfare.update(apply_missingness(rng, welfare_raw, company["disclosure_profile"]))
        welfare_rows.append(welfare)

    return company_year_rows, welfare_rows


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def build_evidence(
    company_year_rows: list[dict[str, object]],
    welfare_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    units = {
        "revenue": "CNY",
        "operating_cost": "CNY",
        "profit_before_tax": "CNY",
        "net_profit": "CNY",
        "total_assets": "CNY",
        "operating_cash_flow": "CNY",
        "taxes_paid": "CNY",
        "depreciation_amortization": "CNY",
        "rd_expense": "CNY",
        "cash_dividend": "CNY",
        "share_buyback": "CNY",
        "employee_count_start": "person",
        "employee_count_end": "person",
        "employee_cash_paid": "CNY",
        "highest_executive_pay": "CNY/year",
        "rd_employee_count": "person",
        "production_employee_count": "person",
        "p10_annual_income": "CNY/year",
        "median_annual_income": "CNY/year",
        "local_living_wage": "CNY/year",
        "average_weekly_hours": "hour/week",
        "p90_weekly_hours": "hour/week",
        "overtime_pay_coverage": "ratio",
        "social_insurance_coverage": "ratio",
        "housing_fund_coverage": "ratio",
        "paid_leave_usage": "ratio",
        "turnover_rate": "ratio/year",
        "training_coverage": "ratio",
        "work_injury_rate_per_1000": "per_1000",
        "major_fatality_count": "person",
        "contractor_count": "person",
        "contractor_welfare_ratio": "ratio",
        "employee_voice_score": "score_0_100",
    }
    result: list[dict[str, object]] = []
    for table_rows in (company_year_rows, welfare_rows):
        for row in table_rows:
            for metric_id, value in row.items():
                if metric_id in {"company_id", "year"}:
                    continue
                missing = value == "" or value is None
                result.append(
                    {
                        "company_id": row["company_id"],
                        "year": row["year"],
                        "metric_id": metric_id,
                        "metric_value": value,
                        "metric_unit": units[metric_id],
                        "data_origin": "missing" if missing else "synthetic",
                        "confidence_level": "not_available" if missing else "demo",
                        "generation_method": f"{GENERATOR_VERSION}_seed_{SEED}",
                        "source_reference": "演示模型参数，不对应真实企业",
                        "review_status": "validated",
                        "note": "主动缺失" if missing else "模拟数据",
                    }
                )
    return result


def main() -> None:
    rng = random.Random(SEED)
    companies = read_companies()
    company_year_rows: list[dict[str, object]] = []
    welfare_rows: list[dict[str, object]] = []
    for company in companies:
        annual, welfare = generate_company(rng, company)
        company_year_rows.extend(annual)
        welfare_rows.extend(welfare)

    company_fields = [
        "company_id", "year", "revenue", "operating_cost", "profit_before_tax",
        "net_profit", "total_assets", "operating_cash_flow", "taxes_paid",
        "depreciation_amortization", "rd_expense", "cash_dividend", "share_buyback",
        "employee_count_start", "employee_count_end", "employee_cash_paid",
        "highest_executive_pay", "rd_employee_count", "production_employee_count",
    ]
    welfare_fields = ["company_id", "year", *WELFARE_FIELDS]
    evidence_fields = [
        "company_id", "year", "metric_id", "metric_value", "metric_unit",
        "data_origin", "confidence_level", "generation_method", "source_reference",
        "review_status", "note",
    ]

    write_csv(DATA_DIR / "company_years.csv", company_fields, company_year_rows)
    write_csv(DATA_DIR / "employee_welfare.csv", welfare_fields, welfare_rows)
    evidence_rows = build_evidence(company_year_rows, welfare_rows)
    write_csv(DATA_DIR / "metric_evidence.csv", evidence_fields, evidence_rows)

    print(f"Generated {len(company_year_rows)} company-year rows")
    print(f"Generated {len(welfare_rows)} employee-welfare rows")
    print(f"Generated {len(evidence_rows)} metric-evidence rows")


if __name__ == "__main__":
    main()

