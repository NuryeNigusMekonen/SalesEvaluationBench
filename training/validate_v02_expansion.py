#!/usr/bin/env python3
"""Validate the Tenacious-Bench v0.2 seed expansion."""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DATASET = ROOT / "training" / "data" / "tenacious_bench_v0_2_expansion_100.jsonl"
STYLE_GUIDE_V2 = ROOT / "docs" / "Tenacious Style Guide and 12 Good-Bad Examples v2.md"

REQUIRED_FIELDS = {
    "task_id",
    "task_version",
    "split",
    "source_type",
    "source_file_or_artifact",
    "task_type",
    "risk_focus",
    "risk_tags",
    "actual_failure_modes",
    "prospect_context",
    "hiring_signal_brief",
    "competitor_gap_brief",
    "agent_output",
    "judge_instruction",
    "expected_verdict",
    "expected_reason",
    "rubric",
    "chosen",
    "rejected",
    "label_confidence",
    "requires_manual_review",
    "scenario_id",
    "source_provenance",
    "split_contamination_notes",
}

ALLOWED_RISK_TAGS = {
    "directness_failure",
    "grounding_failure",
    "honesty_failure",
    "professionalism_failure",
    "non_condescending_failure",
    "banned_phrase_violation",
    "word_count_violation",
    "multi_ask_violation",
    "bench_language_external",
    "linkedin_roast_risk",
    "channel_rule_violation",
    "cold_attachment_violation",
    "reengagement_without_new_content",
    "fake_urgency_or_discount",
    "signal_fabrication",
}

TARGET_RISK_FOCUS = {
    "overclaimed_signal_or_maturity_claim": 30,
    "wrong_crm_hubspot_calendar_next_action": 25,
    "generic_outreach_ungrounded": 25,
    "reply_escalation_or_objection_failure": 10,
    "unsupported_pricing_or_scope_claim": 10,
}

TARGET_VERDICTS = {
    "fail": 45,
    "pass": 35,
    "needs_human_review": 20,
}


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def word_windows(text: str, size: int = 18) -> set[str]:
    words = re.findall(r"[a-z0-9_\-\$]+", normalize(text))
    return {" ".join(words[i : i + size]) for i in range(0, max(0, len(words) - size + 1))}


def strip_verdict_prefix(text: str) -> str:
    normalized = normalize(text)
    parts = normalized.split(". ", 1)
    return parts[1] if len(parts) == 2 else normalized


def load_rows(path: Path) -> tuple[list[dict], list[str]]:
    errors: list[str] = []
    rows: list[dict] = []
    if not path.exists():
        return rows, [f"missing dataset file: {path}"]

    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            errors.append(f"line {line_number}: invalid JSON: {exc}")
    return rows, errors


def source_paths_exist(source_file_or_artifact: str) -> bool:
    for part in source_file_or_artifact.split(" + "):
        candidate = ROOT / part.strip()
        if not candidate.exists():
            return False
    return True


def main() -> int:
    rows, errors = load_rows(DATASET)
    style_text = STYLE_GUIDE_V2.read_text(encoding="utf-8") if STYLE_GUIDE_V2.exists() else ""
    style_windows = word_windows(style_text)

    if len(rows) != 100:
        errors.append(f"expected 100 rows, found {len(rows)}")

    seen_ids: set[str] = set()
    seen_outputs: set[str] = set()
    risk_counts: Counter[str] = Counter()
    verdict_counts: Counter[str] = Counter()
    risk_tag_counts: Counter[str] = Counter()
    actual_failure_counts: Counter[str] = Counter()
    chosen_text_counts: Counter[str] = Counter()
    rejected_text_counts: Counter[str] = Counter()
    expected_reason_counts: Counter[str] = Counter()
    rejected_core_counts: Counter[str] = Counter()

    for index, row in enumerate(rows, start=1):
        prefix = f"row {index}"
        missing = sorted(REQUIRED_FIELDS - row.keys())
        if missing:
            errors.append(f"{prefix}: missing required fields: {', '.join(missing)}")
            continue

        task_id = row["task_id"]
        expected_id = f"tb_v02_{index:04d}"
        if task_id != expected_id:
            errors.append(f"{prefix}: expected task_id {expected_id}, found {task_id}")
        if task_id in seen_ids:
            errors.append(f"{prefix}: duplicate task_id {task_id}")
        seen_ids.add(task_id)

        if row["task_version"] != "v0.2":
            errors.append(f"{prefix}: task_version must be v0.2")
        if row["split"] != "seed":
            errors.append(f"{prefix}: split must be seed")
        if row["requires_manual_review"] is not True:
            errors.append(f"{prefix}: requires_manual_review must be true")

        domain = row.get("prospect_context", {}).get("company_domain", "")
        if not domain.endswith(".example"):
            errors.append(f"{prefix}: company_domain must end in .example")

        source = str(row["source_file_or_artifact"])
        if "docs/Tenacious Style Guide and 12 Good-Bad Examples v2.md" not in source:
            errors.append(f"{prefix}: source_file_or_artifact must mention style guide v2")
        if ".pdf" in source.lower() or "paper" in source.lower():
            errors.append(f"{prefix}: source_file_or_artifact must not use paper PDFs")
        if not source_paths_exist(source):
            errors.append(f"{prefix}: source_file_or_artifact contains a missing path")

        provenance = row.get("source_provenance", {})
        if provenance.get("paper_content_used") is not False:
            errors.append(f"{prefix}: source_provenance.paper_content_used must be false")

        agent_output = normalize(str(row["agent_output"]))
        if agent_output in seen_outputs:
            errors.append(f"{prefix}: duplicate agent_output")
        seen_outputs.add(agent_output)

        if normalize(str(row["chosen"])) == normalize(str(row["rejected"])):
            errors.append(f"{prefix}: chosen equals rejected")

        chosen_text_counts[normalize(str(row["chosen"]))] += 1
        rejected_text_counts[normalize(str(row["rejected"]))] += 1
        expected_reason_counts[normalize(str(row["expected_reason"]))] += 1
        rejected_core_counts[strip_verdict_prefix(str(row["rejected"]))] += 1

        risk_tags = row["risk_tags"]
        if not isinstance(risk_tags, list) or not risk_tags:
            errors.append(f"{prefix}: risk_tags must be a non-empty list")
        else:
            invalid_tags = sorted(set(risk_tags) - ALLOWED_RISK_TAGS)
            if invalid_tags:
                errors.append(f"{prefix}: invalid risk_tags: {', '.join(invalid_tags)}")
            risk_tag_counts.update(risk_tags)

        actual_failure_modes = row["actual_failure_modes"]
        if not isinstance(actual_failure_modes, list):
            errors.append(f"{prefix}: actual_failure_modes must be a list")
        else:
            if row["expected_verdict"] == "pass" and actual_failure_modes:
                errors.append(f"{prefix}: pass rows must have empty actual_failure_modes")
            if row["expected_verdict"] in {"fail", "needs_human_review"} and not actual_failure_modes:
                errors.append(f"{prefix}: {row['expected_verdict']} rows must have non-empty actual_failure_modes")
            actual_failure_counts.update(actual_failure_modes)

        joined_training_text = " ".join(
            str(row.get(field, ""))
            for field in ("agent_output", "chosen", "rejected", "expected_reason")
        )
        copied_windows = word_windows(joined_training_text) & style_windows
        if copied_windows:
            sample = sorted(copied_windows)[0]
            errors.append(f"{prefix}: possible copied long style-guide example body: {sample!r}")

        risk_counts[row["risk_focus"]] += 1
        verdict_counts[row["expected_verdict"]] += 1

    if dict(risk_counts) != TARGET_RISK_FOCUS:
        errors.append(f"risk_focus distribution mismatch: {dict(risk_counts)}")
    if dict(verdict_counts) != TARGET_VERDICTS:
        errors.append(f"expected_verdict distribution mismatch: {dict(verdict_counts)}")

    duplicate_chosen = [text for text, count in chosen_text_counts.items() if count > 1]
    duplicate_rejected = [text for text, count in rejected_text_counts.items() if count > 1]
    repeated_reasons = [text for text, count in expected_reason_counts.items() if count > 3]
    repeated_rejected_cores = [text for text, count in rejected_core_counts.items() if count > 5]

    for text in duplicate_chosen[:10]:
        errors.append(f"duplicate chosen text: {text[:120]!r}")
    for text in duplicate_rejected[:10]:
        errors.append(f"duplicate rejected text: {text[:120]!r}")
    for text in repeated_reasons[:10]:
        errors.append(f"expected_reason repeated more than 3 times: {text[:120]!r}")
    for text in repeated_rejected_cores[:10]:
        errors.append(f"rejected phrase repeated more than 5 times: {text[:120]!r}")

    print("Tenacious-Bench v0.2 expansion validation")
    print(f"dataset: {DATASET.relative_to(ROOT)}")
    print(f"rows: {len(rows)}")
    print("risk_focus distribution:")
    for key, value in sorted(risk_counts.items()):
        print(f"  {key}: {value}")
    print("expected_verdict distribution:")
    for key, value in sorted(verdict_counts.items()):
        print(f"  {key}: {value}")
    print("risk_tags distribution:")
    for key, value in sorted(risk_tag_counts.items()):
        print(f"  {key}: {value}")
    print("actual_failure_modes distribution:")
    for key, value in sorted(actual_failure_counts.items()):
        print(f"  {key}: {value}")

    if errors:
        print("\nFAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("\nPASS - v0.2 expansion is valid and ready for manual review.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
