from __future__ import annotations

import csv
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"


def read_csv(name: str) -> list[dict[str, str]]:
    with (DATA_DIR / name).open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    errors: list[str] = []
    derived = read_csv("derived_metrics.csv")
    scores = read_csv("scoring_results.csv")
    overall = read_csv("leaderboard_overall_2025.csv")
    observation = read_csv("observation_group_2025.csv")

    if len(derived) != 90:
        errors.append(f"Expected 90 derived rows, found {len(derived)}")
    if len(scores) != 90:
        errors.append(f"Expected 90 score rows, found {len(scores)}")

    score_keys = {(row["company_id"], row["year"]) for row in scores}
    if len(score_keys) != 90:
        errors.append("Duplicate company-year key in scoring results")

    for row in scores:
        score = float(row["overall_score"])
        raw = float(row["overall_score_raw"])
        completeness = float(row["data_completeness"])
        if not 0 <= score <= 100 or not 0 <= raw <= 100:
            errors.append(f"Score outside 0..100: {row['company_id']}:{row['year']}")
        expected = completeness >= 0.70
        if (row["ranking_eligible"] == "true") != expected:
            errors.append(f"Eligibility mismatch: {row['company_id']}:{row['year']}")
        if row["ranking_eligible"] == "false" and (row["overall_rank"] or row["industry_rank"]):
            errors.append(f"Ineligible company has rank: {row['company_id']}:{row['year']}")

    eligible_2025 = [row for row in scores if row["year"] == "2025" and row["ranking_eligible"] == "true"]
    if len(overall) != len(eligible_2025):
        errors.append("Overall leaderboard count does not match eligible 2025 companies")
    if len(observation) + len(overall) != 30:
        errors.append("2025 leaderboard and observation group do not total 30 companies")

    overall_ranks = sorted(int(row["overall_rank"]) for row in overall)
    if overall_ranks != list(range(1, len(overall) + 1)):
        errors.append("Overall ranks are not continuous")

    industry_counts = Counter(row["industry"] for row in overall)
    for industry in ("manufacturing", "technology", "retail_logistics_service"):
        board = read_csv(f"leaderboard_{industry}_2025.csv")
        if len(board) != industry_counts[industry]:
            errors.append(f"Industry leaderboard count mismatch: {industry}")
        ranks = sorted(int(row["industry_rank"]) for row in board)
        if ranks != list(range(1, len(board) + 1)):
            errors.append(f"Industry ranks are not continuous: {industry}")

    print(f"Derived rows: {len(derived)}")
    print(f"Score rows: {len(scores)}")
    print(f"2025 eligible: {len(overall)}")
    print(f"2025 observation group: {len(observation)}")
    print(f"2025 score range: {min(float(r['overall_score']) for r in scores if r['year'] == '2025'):.1f} - {max(float(r['overall_score']) for r in scores if r['year'] == '2025'):.1f}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        sys.exit(1)
    print("SCORE_VALIDATION_OK")


if __name__ == "__main__":
    main()

