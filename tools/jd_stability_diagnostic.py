"""Run a repeated JD-parse stability diagnostic.

Usage:
    python tools/jd_stability_diagnostic.py path/to/jd.txt --runs 6

This calls the configured local LLM repeatedly and reports category weight-share
and row-count ranges. It is diagnostic only; it does not write to the database.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from services.jd_parser import parse_jd


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("jd_file")
    parser.add_argument("--runs", type=int, default=6)
    parser.add_argument("--model", default=None)
    args = parser.parse_args()

    text = open(args.jd_file, "r", encoding="utf-8").read()
    runs = []

    for run_number in range(1, args.runs + 1):
        analysis = parse_jd(text, args.model)
        totals = defaultdict(int)
        counts = defaultdict(int)

        for req in analysis.requirements:
            totals[req.category.value] += max(0, int(req.weight or 0))
            counts[req.category.value] += 1

        total_weight = sum(totals.values()) or 1
        shares = {
            category: 100 * weight / total_weight
            for category, weight in totals.items()
        }
        runs.append((shares, dict(counts)))

        print(f"\nRun {run_number}: {len(analysis.requirements)} rows")
        print("  " + " | ".join(
            f"{k}={v:.1f}% ({counts[k]} rows)"
            for k, v in sorted(shares.items())
        ))

        industry_rows = [
            r for r in analysis.requirements
            if r.category.value == "INDUSTRY"
        ]
        if industry_rows:
            print("  INDUSTRY rows:")
            for row in industry_rows:
                print(f"    {row.requirement_id}: {row.name} | source: {row.source_text}")

    categories = sorted({c for shares, _ in runs for c in shares})
    print("\n=== Stability summary ===")
    for category in categories:
        values = [shares.get(category, 0.0) for shares, _ in runs]
        counts = [rows.get(category, 0) for _, rows in runs]
        print(
            f"{category:20} "
            f"weight {min(values):5.1f}% -> {max(values):5.1f}% "
            f"(range {max(values)-min(values):4.1f} pts); "
            f"rows {min(counts)} -> {max(counts)}"
        )


if __name__ == "__main__":
    main()
