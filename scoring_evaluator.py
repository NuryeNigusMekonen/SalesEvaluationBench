#!/usr/bin/env python3
"""Deterministic evaluator for Tenacious-Bench v0.1 judge-task responses."""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path


VALID_VERDICTS = {"pass", "fail", "needs_human_review"}
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "because",
    "but",
    "by",
    "for",
    "from",
    "if",
    "in",
    "into",
    "is",
    "it",
    "of",
    "on",
    "or",
    "so",
    "that",
    "the",
    "their",
    "then",
    "there",
    "these",
    "this",
    "to",
    "was",
    "with",
}
TOKEN_RE = re.compile(r"[a-z0-9_]+")


@dataclass
class CheckResult:
    name: str
    points: int
    note: str


@dataclass
class ScoreResult:
    task_id: str
    total_score: int
    passed: bool
    checks: list[CheckResult] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "total_score": self.total_score,
            "passed": self.passed,
            "pass_threshold": 70,
            "checks": [
                {"check": check.name, "points": check.points, "note": check.note}
                for check in self.checks
            ],
        }


def normalize_tokens(text: str) -> list[str]:
    return [token for token in TOKEN_RE.findall(text.lower()) if token not in STOPWORDS]


def load_json(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def source_citations(task: dict) -> set[str]:
    raw = task["metadata"]["source_file_or_artifact"]
    parts = [part.strip() for part in raw.split("+")]
    citations = set()
    for part in parts:
        name = Path(part.split(":", 1)[0].strip()).name
        if name:
            citations.add(name.lower())
    return citations


def score_task(task: dict, candidate: dict) -> ScoreResult:
    checks: list[CheckResult] = []
    score = 0

    expected_verdict = task["ground_truth"]["expected_verdict"]
    actual_verdict = candidate.get("verdict", "")
    if actual_verdict in VALID_VERDICTS and actual_verdict == expected_verdict:
        score += 60
        checks.append(
            CheckResult(
                "verdict_match",
                60,
                f"candidate verdict '{actual_verdict}' matches expected verdict '{expected_verdict}'",
            )
        )
    else:
        checks.append(
            CheckResult(
                "verdict_match",
                0,
                f"candidate verdict '{actual_verdict}' does not match expected verdict '{expected_verdict}'",
            )
        )

    expected_reason_tokens = set(normalize_tokens(task["ground_truth"]["expected_reason"]))
    candidate_reason = candidate.get("reason", "")
    reason_overlap = expected_reason_tokens & set(normalize_tokens(candidate_reason))
    if len(reason_overlap) >= 6:
        score += 20
        checks.append(
            CheckResult(
                "reason_grounding_overlap",
                20,
                f"candidate reason shares {len(reason_overlap)} informative tokens with expected reason",
            )
        )
    elif len(reason_overlap) >= 3:
        score += 10
        checks.append(
            CheckResult(
                "reason_grounding_overlap",
                10,
                f"candidate reason shares {len(reason_overlap)} informative tokens with expected reason",
            )
        )
    else:
        checks.append(
            CheckResult(
                "reason_grounding_overlap",
                0,
                "candidate reason does not overlap enough with the expected reason",
            )
        )

    valid_citations = source_citations(task)
    provided_citations = {
        str(citation).lower() for citation in candidate.get("citations", []) if str(citation).strip()
    }
    matched_citations = sorted(valid_citations & provided_citations)
    if matched_citations:
        score += 20
        checks.append(
            CheckResult(
                "citation_match",
                20,
                f"candidate cites source artifact(s): {', '.join(matched_citations)}",
            )
        )
    else:
        checks.append(
            CheckResult(
                "citation_match",
                0,
                f"candidate citations did not match any source artifacts; valid options include: {', '.join(sorted(valid_citations))}",
            )
        )

    return ScoreResult(
        task_id=task["task_id"],
        total_score=score,
        passed=score >= 70,
        checks=checks,
    )


SELF_TEST_TASK = {
    "task_id": "tb_seed_0002",
    "metadata": {
        "source_file_or_artifact": "agent/data/outbox/pros_255661272366_reply_decision.json + docs/tenacious_sales_data/seed/pricing_sheet.md"
    },
    "ground_truth": {
        "expected_verdict": "fail",
        "expected_reason": (
            "The pricing sheet allows public bands and minimums but forbids specific total contract "
            "values for scoped or multi-role engagements. A scope-specific 12-month total must be "
            "routed to a delivery lead."
        ),
    },
}

SELF_TEST_RESPONSE_PASS = {
    "verdict": "fail",
    "reason": (
        "This should fail because the pricing sheet forbids a specific total contract value for a "
        "scoped multi-role engagement, so the question must be routed to a delivery lead."
    ),
    "citations": ["pricing_sheet.md"],
}

SELF_TEST_RESPONSE_FAIL = {
    "verdict": "pass",
    "reason": "The reply is helpful and specific.",
    "citations": ["style_guide.md"],
}


def run_self_test() -> int:
    for label, response in (
        ("expected_pass", SELF_TEST_RESPONSE_PASS),
        ("expected_fail", SELF_TEST_RESPONSE_FAIL),
    ):
        result = score_task(SELF_TEST_TASK, response)
        print(label)
        print(json.dumps(result.to_dict(), indent=2))
    return 0


def main(argv: list[str]) -> int:
    if len(argv) == 2 and argv[1] == "--self-test":
        return run_self_test()
    if len(argv) == 3:
        task = load_json(argv[1])
        candidate = load_json(argv[2])
        result = score_task(task, candidate)
        print(json.dumps(result.to_dict(), indent=2))
        return 0
    print("Usage:")
    print("  python scoring_evaluator.py --self-test")
    print("  python scoring_evaluator.py <task.json> <candidate_response.json>")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
