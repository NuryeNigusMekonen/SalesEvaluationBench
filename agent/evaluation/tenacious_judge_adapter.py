from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ADAPTER_PATH = PROJECT_ROOT / "outputs" / "models" / "tenacious-judge-v02-simpo-lora"
DEFAULT_BASE_MODEL = "Qwen/Qwen2.5-3B-Instruct"
DEFAULT_MAX_NEW_TOKENS = 256
REVIEW_LOG_PATH = PROJECT_ROOT / "agent" / "data" / "judge_reviews.jsonl"
FALLBACK_REASON = "Local judge adapter unavailable or invalid output, routed to human review."

_ALLOWED_VERDICTS = {"pass", "fail", "needs_human_review"}
_MODEL_BUNDLE: "_JudgeModelBundle | None" = None
_MODEL_BUNDLE_KEY: tuple[str, str] | None = None


@dataclass
class _JudgeModelBundle:
    tokenizer: Any
    model: Any
    device: str


def _env_true(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _configured_adapter_path(adapter_path: str | None = None) -> Path:
    raw_path = adapter_path or os.getenv("TENACIOUS_JUDGE_ADAPTER_PATH") or str(DEFAULT_ADAPTER_PATH)
    path = Path(raw_path)
    return path if path.is_absolute() else PROJECT_ROOT / path


def _configured_base_model() -> str:
    return os.getenv("TENACIOUS_JUDGE_BASE_MODEL", DEFAULT_BASE_MODEL)


def _configured_max_new_tokens() -> int:
    raw = os.getenv("TENACIOUS_JUDGE_MAX_NEW_TOKENS", str(DEFAULT_MAX_NEW_TOKENS))
    try:
        return max(1, int(raw))
    except ValueError:
        return DEFAULT_MAX_NEW_TOKENS


def _fallback(raw_output: str = "", model_path: str | None = None) -> dict:
    return {
        "verdict": "needs_human_review",
        "reason": FALLBACK_REASON,
        "confidence": 0.0,
        "raw_output": raw_output,
        "model_path": model_path or "",
        "mode": "fallback",
    }


def _safe_model_dump(value: Any) -> Any:
    if value is None:
        return {}
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return value
    return value


def _json_block(text: str) -> str | None:
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return None


def _parse_judge_json(raw_output: str, *, model_path: str) -> dict:
    try:
        parsed = json.loads(raw_output)
    except json.JSONDecodeError:
        block = _json_block(raw_output)
        if block is None:
            return _fallback(raw_output=raw_output, model_path=model_path)
        try:
            parsed = json.loads(block)
        except json.JSONDecodeError:
            return _fallback(raw_output=raw_output, model_path=model_path)

    verdict = str(parsed.get("verdict", "")).strip().lower()
    if verdict not in _ALLOWED_VERDICTS:
        return _fallback(raw_output=raw_output, model_path=model_path)

    confidence = parsed.get("confidence", 0.0)
    try:
        confidence_float = float(confidence)
    except (TypeError, ValueError):
        confidence_float = 0.0
    confidence_float = max(0.0, min(1.0, confidence_float))

    result = {
        "verdict": verdict,
        "reason": str(parsed.get("reason") or "").strip() or "No reason provided by judge.",
        "confidence": confidence_float,
        "raw_output": raw_output,
        "model_path": model_path,
        "mode": "model",
    }
    risk_focus = parsed.get("risk_focus")
    if risk_focus:
        result["risk_focus"] = str(risk_focus)
    return result


def _rubric_summary() -> str:
    return (
        "v0.2 rubric summary: pass only when the candidate is grounded in the supplied prospect, "
        "hiring signal, competitor-gap, and Tenacious seed constraints. Fail unsupported pricing, "
        "scope, capacity, deployment, maturity, funding, hiring, layoff, leadership, or competitor "
        "claims; generic outreach that ignores the brief; CRM/calendar actions inconsistent with "
        "the conversation state; SMS/calendar/voice escalation without consent or warm-lead gating; "
        "and any response that should be routed to a human instead. Use needs_human_review when "
        "the evidence is ambiguous, context is missing, or the action may create customer-facing risk."
    )


def _build_prompt(
    *,
    prospect_context: dict,
    hiring_signal_brief: dict,
    competitor_gap_brief: dict,
    agent_output: str,
    judge_instruction: str | None,
    action_type: str | None,
) -> str:
    payload = {
        "prospect_context": prospect_context,
        "hiring_signal_brief": hiring_signal_brief,
        "competitor_gap_brief": competitor_gap_brief,
        "action_type": action_type,
        "candidate_sales_agent_output": agent_output,
    }
    instruction = judge_instruction or (
        "Review the candidate sales-agent output before it is sent, logged as final, "
        "or committed to CRM/calendar. Return JSON only."
    )
    return (
        "You are the Tenacious sales-agent judge/critic adapter. You are not the sales agent. "
        "Your job is to block unsafe, ungrounded, or state-inconsistent candidate actions.\n\n"
        f"{instruction}\n\n"
        f"{_rubric_summary()}\n\n"
        "Context payload:\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}\n\n"
        "Return JSON only using this exact schema:\n"
        "{\n"
        '  "verdict": "pass" | "fail" | "needs_human_review",\n'
        '  "reason": "short evidence-grounded reason",\n'
        '  "risk_focus": "optional risk label",\n'
        '  "confidence": 0.0\n'
        "}"
    )


def _get_model_bundle(adapter_path: Path, base_model: str) -> _JudgeModelBundle:
    global _MODEL_BUNDLE, _MODEL_BUNDLE_KEY

    key = (str(adapter_path), base_model)
    if _MODEL_BUNDLE is not None and _MODEL_BUNDLE_KEY == key:
        return _MODEL_BUNDLE

    if not adapter_path.exists():
        raise FileNotFoundError(f"Adapter path does not exist: {adapter_path}")

    try:
        import torch
        from peft import PeftModel
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except Exception as exc:  # pragma: no cover - exercised through fallback tests
        raise RuntimeError(f"Judge ML dependencies are unavailable: {exc}") from exc

    local_files_only = os.getenv("TENACIOUS_JUDGE_LOCAL_FILES_ONLY", "true").strip().lower() not in {
        "0",
        "false",
        "no",
    }
    cuda_available = bool(torch.cuda.is_available())
    torch_dtype = torch.float16 if cuda_available else torch.float32
    device_map = "auto" if cuda_available else None

    tokenizer = AutoTokenizer.from_pretrained(
        base_model,
        local_files_only=local_files_only,
        trust_remote_code=True,
    )
    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        torch_dtype=torch_dtype,
        device_map=device_map,
        local_files_only=local_files_only,
        trust_remote_code=True,
    )
    model = PeftModel.from_pretrained(
        model,
        str(adapter_path),
        local_files_only=local_files_only,
    )
    if not cuda_available:
        model = model.to("cpu")
    model.eval()

    _MODEL_BUNDLE = _JudgeModelBundle(
        tokenizer=tokenizer,
        model=model,
        device="cuda" if cuda_available else "cpu",
    )
    _MODEL_BUNDLE_KEY = key
    return _MODEL_BUNDLE


def _generate_judge_output(prompt: str, *, adapter_path: Path, base_model: str) -> str:
    bundle = _get_model_bundle(adapter_path, base_model)
    tokenizer = bundle.tokenizer
    model = bundle.model

    messages = [
        {
            "role": "system",
            "content": "You are a strict Tenacious guardrail. Return valid JSON only.",
        },
        {"role": "user", "content": prompt},
    ]
    if hasattr(tokenizer, "apply_chat_template"):
        rendered = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
    else:
        rendered = prompt

    inputs = tokenizer(rendered, return_tensors="pt")
    try:
        inputs = {key: value.to(model.device) for key, value in inputs.items()}
    except Exception:
        pass

    output_ids = model.generate(
        **inputs,
        max_new_tokens=_configured_max_new_tokens(),
        do_sample=False,
        temperature=None,
        pad_token_id=getattr(tokenizer, "eos_token_id", None),
    )
    input_length = inputs["input_ids"].shape[-1]
    generated_ids = output_ids[0][input_length:]
    return tokenizer.decode(generated_ids, skip_special_tokens=True).strip()


def judge_candidate(
    prospect_context: dict,
    hiring_signal_brief: dict,
    competitor_gap_brief: dict,
    agent_output: str,
    judge_instruction: str | None = None,
    action_type: str | None = None,
    adapter_path: str | None = None,
) -> dict:
    resolved_adapter_path = _configured_adapter_path(adapter_path)
    model_path = str(resolved_adapter_path)
    prompt = _build_prompt(
        prospect_context=_safe_model_dump(prospect_context),
        hiring_signal_brief=_safe_model_dump(hiring_signal_brief),
        competitor_gap_brief=_safe_model_dump(competitor_gap_brief),
        agent_output=agent_output,
        judge_instruction=judge_instruction,
        action_type=action_type,
    )
    try:
        raw_output = _generate_judge_output(
            prompt,
            adapter_path=resolved_adapter_path,
            base_model=_configured_base_model(),
        )
    except Exception as exc:
        return _fallback(raw_output=str(exc), model_path=model_path)
    return _parse_judge_json(raw_output, model_path=model_path)


def _company_name_from_context(context: dict) -> str | None:
    for key in ("company_name", "company", "name"):
        value = context.get(key)
        if value:
            return str(value)
    prospect = context.get("prospect")
    if isinstance(prospect, dict):
        return _company_name_from_context(prospect)
    return None


def append_judge_review_log(candidate_action: dict, judge: dict) -> None:
    prospect_context = _safe_model_dump(candidate_action.get("prospect_context"))
    if not isinstance(prospect_context, dict):
        prospect_context = {}

    record = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "prospect_id": candidate_action.get("prospect_id") or prospect_context.get("prospect_id"),
        "company_name": _company_name_from_context(prospect_context),
        "action_type": candidate_action.get("action_type"),
        "channel": candidate_action.get("channel"),
        "verdict": judge.get("verdict"),
        "reason": judge.get("reason"),
        "confidence": judge.get("confidence", 0.0),
        "model_path": judge.get("model_path"),
        "mode": judge.get("mode"),
    }
    if judge.get("risk_focus"):
        record["risk_focus"] = judge.get("risk_focus")

    REVIEW_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with REVIEW_LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def review_before_action(
    candidate_action: dict,
    *,
    judge_func: Callable[..., dict] | None = None,
) -> dict:
    if not _env_true("TENACIOUS_JUDGE_ENABLED"):
        return {
            "allow": True,
            "route_to_review": False,
            "judge": {},
            "reason": "judge disabled",
        }

    judge_callable = judge_func or judge_candidate
    judge = judge_callable(
        prospect_context=_safe_model_dump(candidate_action.get("prospect_context")),
        hiring_signal_brief=_safe_model_dump(candidate_action.get("hiring_signal_brief")),
        competitor_gap_brief=_safe_model_dump(candidate_action.get("competitor_gap_brief")),
        agent_output=str(candidate_action.get("agent_output") or ""),
        action_type=candidate_action.get("action_type"),
        adapter_path=candidate_action.get("adapter_path"),
    )
    append_judge_review_log(candidate_action, judge)

    verdict = judge.get("verdict")
    if verdict == "pass":
        return {
            "allow": True,
            "route_to_review": False,
            "judge": judge,
            "reason": judge.get("reason") or "judge passed",
        }
    if verdict == "fail":
        return {
            "allow": False,
            "route_to_review": False,
            "judge": judge,
            "reason": judge.get("reason") or "judge failed",
        }
    return {
        "allow": False,
        "route_to_review": True,
        "judge": judge,
        "reason": judge.get("reason") or FALLBACK_REASON,
    }
