#!/usr/bin/env python3
"""Run the source ingestion + qualification refresh pipeline.

This script is intended for cron/weekly scheduling, e.g. every Monday morning.
It pulls from configured enrichment sources, normalizes and stores source signals,
re-qualifies prospects, and writes a JSON summary to stdout.
"""

from __future__ import annotations

import argparse
import json

from agent.orchestration.service import orchestrator


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--max-companies",
        type=int,
        default=150,
        help="Maximum number of consolidated companies to process.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = orchestrator.refresh_active_leads_from_sources(max_companies=args.max_companies)
    print(json.dumps({"ok": True, **result}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
