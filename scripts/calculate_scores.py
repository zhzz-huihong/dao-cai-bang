from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
SCORE_VERSION = "score_v1.0"


def read_csv(name: str) -> list[dict[str, str]]:
    with (DATA_DIR / name).open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(name: str, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    with (DATA_DIR / name).open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def num(value: object) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def safe_div(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def interpolate(value: float | None, points: list[tuple[float, float]]) -> float | None:
    if value is None:
        return None
    if value <= points[0][0]:
        return points[0][1]
    if value >= points[-1][0]:
        return points[-1][1]
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        if x0 <= value <= x1:
            ratio = (value - x0) / (x1 - x0)
            return y0 + (y1 - y0) * ratio
    raise RuntimeError("Interpolation interval not found")


def percentile_score(values: Iterable[float | None], current: float | None, higher_better: bool = True) -> float | None:
    if current is None:
        return None
    clean = sorted(value for value in values if value is not None)
    if not clean:
        return None
    if len(clean) == 1:
        return 50.0
    less = sum(value < current for value in clean)
    equal = sum(value == current for value in clean)
    percentile = (less + 0.5 * equal) / len(clean)
    score = percentile * 100.0
    return score if higher_better else 100.0 - score


def component(metrics: list[tuple[float | None, float]], max_points: float) -> tuple[float | None, float]:
    available = [(score, weight) for score, weight in metrics if score is not None]
    if not available:
        return None, 0.0
    weighted = sum(float(score) * weight for score, weight in available)
    weight_total = sum(weight for _, weight in available)
    return clamp(weighted / weight_total) / 100.0 * max_points, max_points


def normalize_known(parts: list[tuple[float | None, float]], max_points: float) -> float:
    available = [(score, part_max) for score, part_max in parts if score is not None]
    if not available:
        return 0.0
    return sum(float(score) for score, _ in available) / sum(part_max for _, part_max in available) * max_points


def derive(
    annual_rows: list[dict[str, str]],
    welfare_by_key: dict[tuple[str, int], dict[str, str]],
    company_by_id: dict[str, dict[str, str]],
) -> list[dict[str, object]]:
    annual_sorted = sorted(annual_rows, key=lambda row: (row["company_id"], int(row["year"])))
    previous_by_company: dict[str, dict[str, object]] = {}
    result: list[dict[str, object]] = []

    completeness_fields_annual = [
        "revenue", "net_profit", "operating_cash_flow", "employee_count_start",
        "employee_count_end", "employee_cash_paid", "highest_executive_pay",
    ]
    completeness_fields_welfare = [
        "p10_annual_income", "median_annual_income", "local_living_wage",
        "average_weekly_hours", "p90_weekly_hours", "overtime_pay_coverage",
        "social_insurance_coverage", "housing_fund_coverage", "paid_leave_usage",
        "turnover_rate", "training_coverage", "work_injury_rate_per_1000",
        "major_fatality_count", "contractor_count", "contractor_welfare_ratio",
        "employee_voice_score",
    ]

    for annual in annual_sorted:
        company_id = annual["company_id"]
        year = int(annual["year"])
        welfare = welfare_by_key[(company_id, year)]
        company = company_by_id[company_id]
        start = num(annual["employee_count_start"])
        end = num(annual["employee_count_end"])
        average_employees = (start + end) / 2.0 if start is not None and end is not None else None
        revenue = num(annual["revenue"])
        net_profit = num(annual["net_profit"])
        operating_cash = num(annual["operating_cash_flow"])
        employee_cash = num(annual["employee_cash_paid"])
        profit_before_tax = num(annual["profit_before_tax"])
        depreciation = num(annual["depreciation_amortization"])
        taxes = num(annual["taxes_paid"])
        dividends = num(annual["cash_dividend"])
        buybacks = num(annual["share_buyback"])
        contractor_count = num(welfare["contractor_count"])

        revenue_per_employee = safe_div(revenue, average_employees)
        per_employee_cash = safe_div(employee_cash, average_employees)
        denominator = None
        if None not in (employee_cash, profit_before_tax, depreciation, taxes):
            denominator = employee_cash + profit_before_tax + depreciation + taxes
        labor_distribution = safe_div(employee_cash, denominator) if denominator and denominator > 0 else None
        shareholder_cash = None if dividends is None or buybacks is None else dividends + buybacks
        employee_shareholder_ratio = safe_div(employee_cash, shareholder_cash) if shareholder_cash and shareholder_cash > 0 else None
        no_shareholder_cash = shareholder_cash == 0 if shareholder_cash is not None else ""
        contractor_ratio = None
        if contractor_count is not None and end is not None:
            contractor_ratio = safe_div(contractor_count, contractor_count + end)

        previous = previous_by_company.get(company_id)
        employee_growth = None
        revenue_per_employee_growth = None
        per_employee_cash_growth = None
        if previous is not None:
            employee_growth = safe_div(end - float(previous["employee_count_end"]), float(previous["employee_count_end"]))
            prev_revenue_per_employee = previous["revenue_per_employee"]
            prev_cash_per_employee = previous["per_employee_cash_investment"]
            if prev_revenue_per_employee:
                revenue_per_employee_growth = revenue_per_employee / float(prev_revenue_per_employee) - 1.0
            if prev_cash_per_employee:
                per_employee_cash_growth = per_employee_cash / float(prev_cash_per_employee) - 1.0
        shared_growth_gap = None
        if revenue_per_employee_growth is not None and per_employee_cash_growth is not None:
            shared_growth_gap = per_employee_cash_growth - revenue_per_employee_growth

        present = sum(annual.get(field, "") != "" for field in completeness_fields_annual)
        present += sum(welfare.get(field, "") != "" for field in completeness_fields_welfare)
        total_fields = len(completeness_fields_annual) + len(completeness_fields_welfare)
        completeness = present / total_fields

        row: dict[str, object] = {
            "company_id": company_id,
            "year": year,
            "industry": company["industry"],
            "average_employee_count": round(average_employees, 1) if average_employees is not None else "",
            "revenue_per_employee": round(revenue_per_employee, 2) if revenue_per_employee is not None else "",
            "net_profit_margin": round(safe_div(net_profit, revenue), 6) if safe_div(net_profit, revenue) is not None else "",
            "operating_cash_flow_margin": round(safe_div(operating_cash, revenue), 6) if safe_div(operating_cash, revenue) is not None else "",
            "per_employee_cash_investment": round(per_employee_cash, 2) if per_employee_cash is not None else "",
            "labor_cash_intensity": round(safe_div(employee_cash, revenue), 6) if safe_div(employee_cash, revenue) is not None else "",
            "living_wage_ratio": round(safe_div(num(welfare["p10_annual_income"]), num(welfare["local_living_wage"])), 4) if safe_div(num(welfare["p10_annual_income"]), num(welfare["local_living_wage"])) is not None else "",
            "labor_distribution_proxy": round(labor_distribution, 6) if labor_distribution is not None else "",
            "executive_worker_gap_proxy": round(safe_div(num(annual["highest_executive_pay"]), per_employee_cash), 4) if safe_div(num(annual["highest_executive_pay"]), per_employee_cash) is not None else "",
            "employee_shareholder_distribution_ratio": round(employee_shareholder_ratio, 4) if employee_shareholder_ratio is not None else "",
            "no_shareholder_cash_distribution": no_shareholder_cash,
            "contractor_ratio": round(contractor_ratio, 6) if contractor_ratio is not None else "",
            "employee_count_growth": round(employee_growth, 6) if employee_growth is not None else "",
            "revenue_per_employee_growth": round(revenue_per_employee_growth, 6) if revenue_per_employee_growth is not None else "",
            "per_employee_cash_growth": round(per_employee_cash_growth, 6) if per_employee_cash_growth is not None else "",
            "shared_growth_gap": round(shared_growth_gap, 6) if shared_growth_gap is not None else "",
            "data_completeness": round(completeness, 6),
        }
        result.append(row)
        previous_by_company[company_id] = {
            "employee_count_end": end,
            "revenue_per_employee": revenue_per_employee,
            "per_employee_cash_investment": per_employee_cash,
        }
    return result


def score_rows(
    derived_rows: list[dict[str, object]],
    annual_by_key: dict[tuple[str, int], dict[str, str]],
    welfare_by_key: dict[tuple[str, int], dict[str, str]],
) -> list[dict[str, object]]:
    groups: dict[tuple[int, str], list[dict[str, object]]] = defaultdict(list)
    for row in derived_rows:
        groups[(int(row["year"]), str(row["industry"]))].append(row)

    results: list[dict[str, object]] = []
    for row in derived_rows:
        company_id = str(row["company_id"])
        year = int(row["year"])
        industry = str(row["industry"])
        peers = groups[(year, industry)]
        annual = annual_by_key[(company_id, year)]
        welfare = welfare_by_key[(company_id, year)]

        def peer_values(field: str) -> list[float | None]:
            return [num(peer.get(field)) for peer in peers]

        revenue_productivity = percentile_score(peer_values("revenue_per_employee"), num(row["revenue_per_employee"]), True)
        profitability = percentile_score(peer_values("net_profit_margin"), num(row["net_profit_margin"]), True)
        cashflow_quality = percentile_score(peer_values("operating_cash_flow_margin"), num(row["operating_cash_flow_margin"]), True)
        employment_stability = interpolate(num(row["employee_count_growth"]), [(-0.20, 0), (-0.10, 30), (-0.05, 55), (0.0, 78), (0.05, 95), (0.12, 100)])
        if employment_stability is None:
            employment_stability = 65.0
        wealth_score, _ = component(
            [(revenue_productivity, 8), (profitability, 7), (cashflow_quality, 5), (employment_stability, 5)],
            25,
        )

        income_score_raw = interpolate(num(row["living_wage_ratio"]), [(0.0, 0), (0.8, 20), (1.0, 60), (1.2, 80), (1.5, 100)])
        income_score, income_available = component([(income_score_raw, 15)], 15)

        labor_distribution_raw = percentile_score(peer_values("labor_distribution_proxy"), num(row["labor_distribution_proxy"]), True)
        shared_growth_raw = interpolate(num(row["shared_growth_gap"]), [(-0.10, 0), (-0.05, 25), (0.0, 60), (0.05, 85), (0.10, 100)])
        employee_shareholder_raw = percentile_score(
            peer_values("employee_shareholder_distribution_ratio"),
            num(row["employee_shareholder_distribution_ratio"]),
            True,
        )
        labor_score, labor_available = component(
            [(labor_distribution_raw, 5), (shared_growth_raw, 4), (employee_shareholder_raw, 3)],
            12,
        )

        internal_gap_raw = percentile_score(peer_values("executive_worker_gap_proxy"), num(row["executive_worker_gap_proxy"]), False)
        internal_gap_score, internal_gap_available = component([(internal_gap_raw, 10)], 10)

        benefits_score, benefits_available = component(
            [
                (None if num(welfare["social_insurance_coverage"]) is None else num(welfare["social_insurance_coverage"]) * 100, 4),
                (None if num(welfare["housing_fund_coverage"]) is None else num(welfare["housing_fund_coverage"]) * 100, 2),
                (None if num(welfare["paid_leave_usage"]) is None else num(welfare["paid_leave_usage"]) * 100, 2),
                (None if num(welfare["overtime_pay_coverage"]) is None else num(welfare["overtime_pay_coverage"]) * 100, 2),
            ],
            10,
        )

        average_hours_raw = interpolate(num(welfare["average_weekly_hours"]), [(36, 100), (40, 100), (44, 90), (48, 70), (52, 45), (56, 20), (60, 5), (65, 0)])
        p90_hours_raw = interpolate(num(welfare["p90_weekly_hours"]), [(40, 100), (45, 100), (50, 85), (55, 60), (60, 35), (65, 15), (70, 0), (80, 0)])
        injury_raw = percentile_score(
            [num(welfare_by_key[(str(peer["company_id"]), year)]["work_injury_rate_per_1000"]) for peer in peers],
            num(welfare["work_injury_rate_per_1000"]),
            False,
        )
        fatalities = num(welfare["major_fatality_count"])
        fatality_raw = None if fatalities is None else (100.0 if fatalities == 0 else 0.0)
        hours_safety_score, hours_safety_available = component(
            [(average_hours_raw, 3), (p90_hours_raw, 1), (injury_raw, 3), (fatality_raw, 1)],
            8,
        )

        turnover_raw = percentile_score(
            [num(welfare_by_key[(str(peer["company_id"]), year)]["turnover_rate"]) for peer in peers],
            num(welfare["turnover_rate"]),
            False,
        )
        training_raw = None if num(welfare["training_coverage"]) is None else num(welfare["training_coverage"]) * 100
        development_score, development_available = component([(training_raw, 3), (turnover_raw, 2)], 5)

        employee_parts = [
            (income_score, income_available),
            (labor_score, labor_available),
            (internal_gap_score, internal_gap_available),
            (benefits_score, benefits_available),
            (hours_safety_score, hours_safety_available),
            (development_score, development_available),
        ]
        employee_welfare_score = normalize_known(employee_parts, 60)

        contractor_welfare_raw = None if num(welfare["contractor_welfare_ratio"]) is None else num(welfare["contractor_welfare_ratio"]) * 100
        contractor_ratio_raw = percentile_score(peer_values("contractor_ratio"), num(row["contractor_ratio"]), False)
        external_score, external_available = component([(contractor_welfare_raw, 4.5), (contractor_ratio_raw, 1.5)], 6)
        voice_raw = num(welfare["employee_voice_score"])
        voice_score, voice_available = component([(voice_raw, 4)], 4)
        governance_operational = normalize_known([(external_score, external_available), (voice_score, voice_available)], 10)
        completeness = float(row["data_completeness"])
        transparency_score = completeness * 5.0
        governance_score = governance_operational + transparency_score

        red_flag_deduction = 0.0 if fatalities is None else fatalities * 12.0
        total = clamp(float(wealth_score or 0) + employee_welfare_score + governance_score - red_flag_deduction)
        eligible = completeness >= 0.70

        results.append(
            {
                "company_id": company_id,
                "year": year,
                "industry": industry,
                "wealth_creation_score": round(float(wealth_score or 0), 4),
                "income_adequacy_score": "" if income_score is None else round(income_score, 4),
                "labor_distribution_score": "" if labor_score is None else round(labor_score, 4),
                "internal_gap_score": "" if internal_gap_score is None else round(internal_gap_score, 4),
                "benefits_score": "" if benefits_score is None else round(benefits_score, 4),
                "hours_safety_score": "" if hours_safety_score is None else round(hours_safety_score, 4),
                "development_dignity_score": "" if development_score is None else round(development_score, 4),
                "employee_welfare_score": round(employee_welfare_score, 4),
                "external_worker_score": "" if external_score is None else round(external_score, 4),
                "employee_voice_score_component": "" if voice_score is None else round(voice_score, 4),
                "transparency_score": round(transparency_score, 4),
                "responsible_governance_score": round(governance_score, 4),
                "red_flag_deduction": round(red_flag_deduction, 4),
                "overall_score_raw": round(total, 8),
                "overall_score": round(total, 1),
                "data_completeness": round(completeness, 4),
                "ranking_eligible": str(eligible).lower(),
                "industry_rank": "",
                "overall_rank": "",
                "score_version": SCORE_VERSION,
            }
        )

    for year in sorted({int(row["year"]) for row in results}):
        eligible_rows = [row for row in results if int(row["year"]) == year and row["ranking_eligible"] == "true"]
        eligible_rows.sort(key=lambda item: float(item["overall_score_raw"]), reverse=True)
        for rank, item in enumerate(eligible_rows, start=1):
            item["overall_rank"] = rank
        for industry in sorted({str(row["industry"]) for row in eligible_rows}):
            industry_rows = [row for row in eligible_rows if row["industry"] == industry]
            industry_rows.sort(key=lambda item: float(item["overall_score_raw"]), reverse=True)
            for rank, item in enumerate(industry_rows, start=1):
                item["industry_rank"] = rank
    return results


def leaderboard_rows(
    scores: list[dict[str, object]],
    companies: dict[str, dict[str, str]],
    year: int,
    industry: str | None = None,
    eligible: bool = True,
) -> list[dict[str, object]]:
    filtered = [
        row for row in scores
        if int(row["year"]) == year
        and (industry is None or row["industry"] == industry)
        and (row["ranking_eligible"] == "true") == eligible
    ]
    filtered.sort(key=lambda item: float(item["overall_score_raw"]), reverse=True)
    output = []
    for row in filtered:
        company = companies[str(row["company_id"])]
        output.append(
            {
                "overall_rank": row["overall_rank"],
                "industry_rank": row["industry_rank"],
                "company_id": row["company_id"],
                "display_name": company["display_name"],
                "industry": row["industry"],
                "primary_archetype": company["primary_archetype"],
                "overall_score": row["overall_score"],
                "wealth_creation_score": round(float(row["wealth_creation_score"]), 1),
                "employee_welfare_score": round(float(row["employee_welfare_score"]), 1),
                "responsible_governance_score": round(float(row["responsible_governance_score"]), 1),
                "red_flag_deduction": row["red_flag_deduction"],
                "data_completeness": row["data_completeness"],
                "ranking_eligible": row["ranking_eligible"],
                "data_notice": "模拟数据，不对应真实企业",
            }
        )
    return output


def main() -> None:
    company_rows = read_csv("companies.csv")
    annual_rows = read_csv("company_years.csv")
    welfare_rows = read_csv("employee_welfare.csv")
    companies = {row["company_id"]: row for row in company_rows}
    annual_by_key = {(row["company_id"], int(row["year"])): row for row in annual_rows}
    welfare_by_key = {(row["company_id"], int(row["year"])): row for row in welfare_rows}

    derived = derive(annual_rows, welfare_by_key, companies)
    scores = score_rows(derived, annual_by_key, welfare_by_key)

    derived_fields = [
        "company_id", "year", "industry", "average_employee_count", "revenue_per_employee",
        "net_profit_margin", "operating_cash_flow_margin", "per_employee_cash_investment",
        "labor_cash_intensity", "living_wage_ratio", "labor_distribution_proxy",
        "executive_worker_gap_proxy", "employee_shareholder_distribution_ratio",
        "no_shareholder_cash_distribution", "contractor_ratio", "employee_count_growth",
        "revenue_per_employee_growth", "per_employee_cash_growth", "shared_growth_gap",
        "data_completeness",
    ]
    score_fields = [
        "company_id", "year", "industry", "wealth_creation_score", "income_adequacy_score",
        "labor_distribution_score", "internal_gap_score", "benefits_score", "hours_safety_score",
        "development_dignity_score", "employee_welfare_score", "external_worker_score",
        "employee_voice_score_component", "transparency_score", "responsible_governance_score",
        "red_flag_deduction", "overall_score_raw", "overall_score", "data_completeness",
        "ranking_eligible", "industry_rank", "overall_rank", "score_version",
    ]
    board_fields = [
        "overall_rank", "industry_rank", "company_id", "display_name", "industry",
        "primary_archetype", "overall_score", "wealth_creation_score", "employee_welfare_score",
        "responsible_governance_score", "red_flag_deduction", "data_completeness",
        "ranking_eligible", "data_notice",
    ]

    write_csv("derived_metrics.csv", derived_fields, derived)
    write_csv("scoring_results.csv", score_fields, scores)
    write_csv("leaderboard_overall_2025.csv", board_fields, leaderboard_rows(scores, companies, 2025))
    for industry in ("manufacturing", "technology", "retail_logistics_service"):
        write_csv(
            f"leaderboard_{industry}_2025.csv",
            board_fields,
            leaderboard_rows(scores, companies, 2025, industry=industry),
        )
    write_csv(
        "observation_group_2025.csv",
        board_fields,
        leaderboard_rows(scores, companies, 2025, eligible=False),
    )

    eligible_2025 = sum(1 for row in scores if int(row["year"]) == 2025 and row["ranking_eligible"] == "true")
    print(f"Derived rows: {len(derived)}")
    print(f"Scoring rows: {len(scores)}")
    print(f"Eligible companies in 2025: {eligible_2025}")
    print(f"Observation companies in 2025: {30 - eligible_2025}")


if __name__ == "__main__":
    main()

