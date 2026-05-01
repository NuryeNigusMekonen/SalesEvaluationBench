from __future__ import annotations

import importlib.util
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ADAPTER_PATH = PROJECT_ROOT / "outputs" / "models" / "tenacious-judge-v02-simpo-lora"
DEFAULT_BASE_MODEL = "Qwen/Qwen2.5-3B-Instruct"
DEFAULT_MAX_NEW_TOKENS = 256
REVIEW_LOG_PATH = PROJECT_ROOT / "agent" / "data" / "judge_reviews.jsonl"
FALLBACK_REASON = "Local judge adapter unavailable or invalid output, routed to human review."
REQUIRED_ML_DEPS = ("torch", "transformers", "peft", "unsloth")

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


def _env_true_default(name: str, *, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


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


def _dependency_available(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def _last_judge_error() -> str | None:
    if not REVIEW_LOG_PATH.exists():
        return None
    try:
        lines = REVIEW_LOG_PATH.read_text(encoding="utf-8").splitlines()
    except OSError:
        return "Could not read judge review log."
    for line in reversed(lines):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if record.get("mode") != "fallback":
            continue
        reason = str(record.get("reason") or FALLBACK_REASON).strip()
        timestamp = record.get("timestamp_utc")
        return f"{timestamp}: {reason}" if timestamp else reason
    return None


def runtime_status() -> dict:
    adapter_path = _configured_adapter_path()
    deps = {name: _dependency_available(name) for name in REQUIRED_ML_DEPS}
    judge_enabled = _env_true("TENACIOUS_JUDGE_ENABLED")
    outbound_is_live = os.getenv("OUTBOUND_ENABLED", "").strip().lower() in {"1", "true", "yes"}
    adapter_exists = adapter_path.exists()
    openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
    openrouter_model = os.getenv("OPENROUTER_MODEL", "")
    openrouter_available = bool(openrouter_key and openrouter_model)
    if judge_enabled and adapter_exists and all(deps.values()):
        runtime_mode = "real_model"
    elif judge_enabled and openrouter_available:
        runtime_mode = "openrouter_fallback"
    else:
        runtime_mode = "fallback"

    judge_disabled_warning: str | None = None
    if outbound_is_live and not judge_enabled:
        judge_disabled_warning = (
            "Outbound is enabled while Week 11 judge is disabled. "
            "Actions may bypass the trained guardrail."
        )
        logger.warning(judge_disabled_warning)

    return {
        "tenacious_judge_enabled": judge_enabled,
        "tenacious_comparison_mode": _env_true("TENACIOUS_COMPARISON_MODE"),
        "tenacious_comparison_dry_run": _env_true_default(
            "TENACIOUS_COMPARISON_DRY_RUN",
            default=True,
        ),
        "adapter_path": str(adapter_path),
        "adapter_path_exists": adapter_exists,
        "required_ml_deps_available": deps,
        "runtime_mode": runtime_mode,
        "openrouter_fallback_available": openrouter_available,
        "last_judge_error": _last_judge_error(),
        "outbound_is_live": outbound_is_live,
        "judge_disabled_with_live_outbound_warning": judge_disabled_warning is not None,
        "judge_disabled_warning": judge_disabled_warning,
    }


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


def _load_bench_facts() -> dict:
    try:
        from agent.seed.loader import seed_materials
        b = seed_materials.baseline
        return {
            "bench_ready": b.bench_ready,
            "time_to_deploy_days": f"{b.time_to_deploy_min_days}–{b.time_to_deploy_max_days}",
            "overlap_hours": f"{b.overlap_hours_min}–{b.overlap_hours_max}",
            "tenure_months": b.tenure_months,
            "note": "These are verified Tenacious bench facts from bench_summary.json. Claims that match these values are grounded and must not be failed.",
        }
    except Exception:
        return {}


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
        "tenacious_verified_bench_facts": _load_bench_facts(),
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


def _build_compact_judge_prompt(agent_output: str, action_type: str | None) -> str:
    """Compact prompt for OpenRouter fallback — avoids timeouts on long payloads."""
    bench = _load_bench_facts()
    bench_note = (
        f"Verified Tenacious bench facts (PASS if cited): {bench.get('bench_ready')} engineers, "
        f"{bench.get('time_to_deploy_days')} day deployment, "
        f"{bench.get('overlap_hours')}h daily overlap, "
        f"{bench.get('tenure_months')} month average tenure.\n"
    ) if bench else ""
    return (
        "You are a sales-email guardrail. Return JSON only.\n\n"
        "Rules — fail if the output contains: unsupported fixed pricing, guaranteed discounts, "
        "guaranteed savings percentages vs unnamed vendors, invented funding/hiring/layoff data, "
        "or SMS/calendar escalation without consent.\n"
        f"{bench_note}"
        "Pass if the output asks a question, uses hedged language, or cites only verifiable facts "
        "including the verified bench facts above.\n"
        "Use needs_human_review only when genuinely ambiguous.\n\n"
        f"action_type: {action_type or 'email'}\n"
        f"candidate_output: {agent_output[:600]}\n\n"
        'Return: {"verdict":"pass"|"fail"|"needs_human_review","reason":"<short reason>","confidence":0.0}'
    )


def _judge_via_openrouter(prompt: str, *, compact_prompt: str | None = None) -> dict:
    """OpenRouter fallback judge used when the local LoRA adapter is unavailable."""
    from urllib.error import HTTPError

    from agent.config import settings
    from agent.utils.http import request_json

    judge_model = (
        os.getenv("TENACIOUS_JUDGE_OPENROUTER_MODEL", "").strip()
        or settings.openrouter_model
    )
    if not settings.openrouter_api_key or not judge_model:
        return _fallback(raw_output="OpenRouter not configured")

    judge_prompt = compact_prompt or prompt
    try:
        _, response, _ = request_json(
            "POST",
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "HTTP-Referer": settings.app_base_url,
                "X-Title": "The Conversion Engine",
            },
            payload={
                "model": judge_model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a strict sales-email guardrail. Return valid JSON only.",
                    },
                    {"role": "user", "content": judge_prompt},
                ],
                "temperature": 0.0,
                "max_tokens": 128,
            },
            timeout=25,
        )
    except HTTPError as exc:
        return _fallback(raw_output=f"OpenRouter HTTP error: {exc}")
    except Exception as exc:
        return _fallback(raw_output=f"OpenRouter error: {exc}")

    choices = response.get("choices") or []
    if not choices:
        return _fallback(raw_output="OpenRouter returned no choices")
    content = (choices[0].get("message") or {}).get("content") or ""
    if isinstance(content, list):
        content = "".join(
            item.get("text", "") for item in content if isinstance(item, dict)
        ).strip()
    result = _parse_judge_json(str(content).strip(), model_path="openrouter")
    if result.get("mode") != "fallback":
        result = dict(result)
        result["model_path"] = f"openrouter/{judge_model}"
    return result


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
        logger.info(
            "Local judge model unavailable (%s); using OpenRouter fallback.", exc
        )
        compact = _build_compact_judge_prompt(agent_output, action_type)
        or_result = _judge_via_openrouter(prompt, compact_prompt=compact)
        if or_result.get("mode") != "fallback":
            return or_result
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
    # needs_human_review: judge is uncertain or model unavailable.
    # Do not commit customer-facing or CRM/calendar actions automatically.
    return {
        "allow": False,
        "route_to_review": True,
        "judge": judge,
        "reason": judge.get("reason") or FALLBACK_REASON,
    }
