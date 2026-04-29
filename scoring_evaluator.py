#!/usr/bin/env python3
"""Deterministic evaluator for Tenacious-Bench v0.1 judge-task responses."""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from json import JSONDecodeError
from typing import Any
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


class EvaluationInputError(ValueError):
    """Raised when a task or candidate file cannot be safely evaluated."""


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


def load_json(path: str) -> dict[str, Any]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise EvaluationInputError(f"input file not found: {path}") from exc
    except JSONDecodeError as exc:
        raise EvaluationInputError(f"invalid JSON in {path}: {exc.msg} at line {exc.lineno}") from exc
    except OSError as exc:
        raise EvaluationInputError(f"could not read {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise EvaluationInputError(f"{path} must contain one JSON object")
    return data


def require_dict(parent: dict[str, Any], key: str, context: str) -> dict[str, Any]:
    value = parent.get(key)
    if not isinstance(value, dict):
        raise EvaluationInputError(f"{context}.{key} must be an object")
    return value


def require_string(parent: dict[str, Any], key: str, context: str) -> str:
    value = parent.get(key)
    if not isinstance(value, str) or not value.strip():
        raise EvaluationInputError(f"{context}.{key} must be a non-empty string")
    return value


def validate_task(task: dict[str, Any]) -> None:
    require_string(task, "task_id", "task")
    metadata = require_dict(task, "metadata", "task")
    require_string(metadata, "source_file_or_artifact", "task.metadata")

    ground_truth = require_dict(task, "ground_truth", "task")
    expected_verdict = require_string(ground_truth, "expected_verdict", "task.ground_truth")
    if expected_verdict not in VALID_VERDICTS:
        raise EvaluationInputError(
            "task.ground_truth.expected_verdict must be one of "
            f"{', '.join(sorted(VALID_VERDICTS))}"
        )
    require_string(ground_truth, "expected_reason", "task.ground_truth")


def validate_candidate(candidate: dict[str, Any]) -> None:
    verdict = require_string(candidate, "verdict", "candidate")
    if verdict not in VALID_VERDICTS:
        raise EvaluationInputError(
            f"candidate.verdict '{verdict}' is not one of {', '.join(sorted(VALID_VERDICTS))}"
        )
    require_string(candidate, "reason", "candidate")

    citations = candidate.get("citations", [])
    if not isinstance(citations, list):
        raise EvaluationInputError("candidate.citations must be a list of source artifact names")
    for index, citation in enumerate(citations):
        if not isinstance(citation, str) or not citation.strip():
            raise EvaluationInputError(f"candidate.citations[{index}] must be a non-empty string")


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
    validate_task(task)
    validate_candidate(candidate)

    checks: list[CheckResult] = []
    score = 0

    # Calibration: 60 means the judge selected the exact gold verdict; 0 means
    # the response chose the wrong disposition, even if the prose sounds useful.
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

    # Calibration: 20 means the rationale names the same policy/evidence basis,
    # 10 means it partially overlaps, and 0 means it is generic or off-target.
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

    # Calibration: 20 means at least one cited artifact matches the task source;
    # 0 means the judge did not anchor the decision to an available source file.
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


EXAMPLE_PRICING_TASK = {
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

EXAMPLE_PRICING_RESPONSE = {
    "verdict": "fail",
    "reason": (
        "This should fail because the pricing sheet forbids a specific total contract value for a "
        "scoped multi-role engagement, so the question must be routed to a delivery lead."
    ),
    "citations": ["pricing_sheet.md"],
}

EXAMPLE_SIGNAL_TASK = {
    "task_id": "tb_seed_0008",
    "metadata": {
        "source_file_or_artifact": "docs/tenacious_sales_data/seed/icp_definition.md + docs/tenacious_sales_data/seed/style_guide.md"
    },
    "ground_truth": {
        "expected_verdict": "fail",
        "expected_reason": (
            "Segment 4 requires AI readiness score 2 or above and a specific capability signal. "
            "The brief has AI maturity 0, so absence of public evidence cannot be converted into "
            "a specialized capability gap claim."
        ),
    },
}

EXAMPLE_SIGNAL_RESPONSE = {
    "verdict": "fail",
    "reason": (
        "This fails because the ICP definition requires AI readiness score 2 or above plus a "
        "specific capability signal for Segment 4. The AI maturity score is 0, so the judge should "
        "not approve a specialized capability claim from missing evidence."
    ),
    "citations": ["icp_definition.md"],
}

EXAMPLE_CRM_TASK = {
    "task_id": "tb_seed_0165",
    "metadata": {
        "source_file_or_artifact": "agent/data/traces.jsonl trace tr_e3382190bf3c + docs/tenacious_sales_data/seed/crm_rules.md"
    },
    "ground_truth": {
        "expected_verdict": "pass",
        "expected_reason": (
            "The CRM action is correct because the prospect opted out and the workflow requires "
            "suppressing further outbound activity rather than scheduling or sending a follow-up."
        ),
    },
}

EXAMPLE_CRM_RESPONSE = {
    "verdict": "pass",
    "reason": (
        "The CRM action should pass because an opt-out requires suppressing future outbound "
        "activity. The workflow should not schedule or send a follow-up after that signal."
    ),
    "citations": ["traces.jsonl", "crm_rules.md"],
}

EXAMPLE_BAD_RESPONSE = {
    "verdict": "pass",
    "reason": "The reply is helpful and specific.",
    "citations": ["style_guide.md"],
}

EXAMPLE_CASES = (
    ("pricing_guardrail_expected_pass", EXAMPLE_PRICING_TASK, EXAMPLE_PRICING_RESPONSE),
    ("signal_overclaim_expected_pass", EXAMPLE_SIGNAL_TASK, EXAMPLE_SIGNAL_RESPONSE),
    ("crm_opt_out_expected_pass", EXAMPLE_CRM_TASK, EXAMPLE_CRM_RESPONSE),
    ("pricing_guardrail_expected_fail", EXAMPLE_PRICING_TASK, EXAMPLE_BAD_RESPONSE),
)


def run_self_test() -> int:
    for label, task, response in EXAMPLE_CASES:
        result = score_task(task, response)
        print(label)
        print(json.dumps(result.to_dict(), indent=2))
    return 0


def main(argv: list[str]) -> int:
    if len(argv) == 2 and argv[1] == "--self-test":
        return run_self_test()
    if len(argv) == 3:
        try:
            task = load_json(argv[1])
            candidate = load_json(argv[2])
            result = score_task(task, candidate)
            print(json.dumps(result.to_dict(), indent=2))
            return 0
        except EvaluationInputError as exc:
            print(f"Evaluation input error: {exc}", file=sys.stderr)
            return 2
    print("Usage:")
    print("  python scoring_evaluator.py --self-test")
    print("  python scoring_evaluator.py <task.json> <candidate_response.json>")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
