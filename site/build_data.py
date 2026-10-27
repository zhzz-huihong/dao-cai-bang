from __future__ import annotations

import csv
import json
from pathlib import Path


SITE_ROOT = Path(__file__).resolve().parent
WORKSPACE_ROOT = SITE_ROOT.parent
DATA_ROOT = WORKSPACE_ROOT / "data"
OUTPUT = SITE_ROOT / "dist" / "data.json"


def load_csv(name: str) -> list[dict[str, object]]:
    with (DATA_ROOT / name).open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return [{key: convert(value) for key, value in row.items()} for row in rows]


def convert(value: str) -> object:
    if value == "":
        return None
    if value == "true":
        return True
    if value == "false":
        return False
    try:
        number = float(value)
    except ValueError:
        return value
    return int(number) if number.is_integer() else number


def by_key(rows: list[dict[str, object]]) -> dict[tuple[str, int], dict[str, object]]:
    return {(str(row["company_id"]), int(row["year"])): row for row in rows}


def main() -> None:
    companies = load_csv("companies.csv")
    annual = load_csv("company_years.csv")
    welfare = load_csv("employee_welfare.csv")
    derived = load_csv("derived_metrics.csv")
    scores = load_csv("scoring_results.csv")
    annual_map = by_key(annual)
    welfare_map = by_key(welfare)
    derived_map = by_key(derived)
    scores_map = by_key(scores)

    company_payload = []
    for company in companies:
        company_id = str(company["company_id"])
        years = []
        for year in (2023, 2024, 2025):
            key = (company_id, year)
            years.append(
                {
                    "year": year,
                    "financial": annual_map[key],
                    "welfare": welfare_map[key],
                    "derived": derived_map[key],
                    "score": scores_map[key],
                }
            )
        company_payload.append({**company, "years": years})

    payload = {
        "meta": {
            "title": "道财榜·模拟数据演示版",
            "year": 2025,
            "companyCount": len(company_payload),
            "industryCount": 3,
            "scoreVersion": "score_v1.0",
            "notice": "所有企业与数据均为模拟内容，不对应任何真实企业。",
        },
        "companies": company_payload,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Wrote {OUTPUT} with {len(company_payload)} companies")


if __name__ == "__main__":
    main()
