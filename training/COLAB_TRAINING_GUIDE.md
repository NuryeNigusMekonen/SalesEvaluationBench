# Colab Training Guide — Tenacious Judge Adapter (SimPO / QLoRA)

This guide walks you through training the Tenacious judge adapter in Google Colab using a T4 GPU.
All code cells are copy-paste ready. Read each section before running.

**Do NOT train from `training/data/tenacious_bench_seed_200.jsonl` (deprecated).**
Use only the validated preference files produced by the conversion script.

---

## Prerequisites

- Google account with Colab access
- Runtime: **T4 GPU** (Runtime → Change runtime type → T4 GPU)
- ~5 GB free Colab disk space

---

## Step 1 — T4 GPU check

Run this first. If no GPU is shown, change the runtime before continuing.

```python
!nvidia-smi
```

Expected output: a table showing `Tesla T4` with ~15 GB memory.

---

## Step 2 — Clone the repository

```python
!git clone https://github.com/<YOUR_GITHUB_USERNAME>/TheConversionEngine.git
%cd TheConversionEngine
```

Verify the benchmark package is present:

```python
import os
assert os.path.exists("tenacious_bench_v0.1/train/tasks.jsonl"), "train split missing"
assert os.path.exists("tenacious_bench_v0.1/dev/tasks.jsonl"), "dev split missing"
assert os.path.exists("tenacious_bench_v0.1/held_out/tasks.jsonl"), "held_out split missing"
print("Benchmark package OK")
```

---

## Step 3 — Install dependencies

```python
!pip install -U --force-reinstall \
  "datasets>=3.4.1,<4.4.0,!=4.0.*,!=4.1.0" \
  "transformers>=4.51.3,<=5.5.0,!=5.0.0,!=5.1.0,!=4.52.0,!=4.52.1,!=4.52.2,!=4.52.3,!=4.53.0,!=4.54.0,!=4.55.0,!=4.55.1,!=4.57.0,!=4.57.4,!=4.57.5" \
  "trl>=0.18.2,<=0.24.0,!=0.19.0" \
  "protobuf>=5.29.1,<6.0.0" \
  unsloth unsloth_zoo

# Verify installations
import unsloth, trl, transformers, datasets
print("Dependencies OK")
print(f"  unsloth:      {unsloth.__version__}")
print(f"  trl:          {trl.__version__}")
print(f"  transformers: {transformers.__version__}")
print(f"  datasets:     {datasets.__version__}")
```

---

## Step 4 — Run benchmark package validator

**Must pass before any training.**

```python
!python3 training/validate_benchmark_package.py
```

Expected output ends with: `PASS — benchmark package is valid and ready for Colab training.`

If it prints `FAIL`, stop and fix the errors before proceeding.

---

## Step 5 — Convert tasks to preference pairs

```python
!python3 training/convert_tasks_to_preferences.py
```

Expected output:
```
[train] ... → training/data/train_preferences.jsonl
  written: 100  skipped: 0
[dev]   ... → training/data/dev_preferences.jsonl
  written: 60   skipped: 0
[held_out] ... → training/data/test_preferences.jsonl
  written: 40   skipped: 0
[OK] preference conversion complete.
```

---

## Step 6 — Run preference split validator

**Must pass before training.**

```python
!python3 training/validate_preference_splits.py
```

Expected output ends with: `PASS — all preference splits valid.`

Inspect the printed distribution summary to confirm risk_focus and task_type
distributions look reasonable across train / dev / test.

---

## Step 7 — Train SimPO QLoRA adapter

**Run only after Steps 4–6 pass.**

```python
# ⚠️  RUN ONLY AFTER VALIDATORS PASS

from unsloth import FastLanguageModel
from trl import SimPOTrainer, SimPOConfig
from datasets import load_dataset
import torch

# -- Load base model with 4-bit quantization --
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="Qwen/Qwen2.5-3B-Instruct",
    max_seq_length=2048,
    load_in_4bit=True,
    dtype=None,  # auto-detect (float16 on T4)
)

# -- Attach LoRA adapters --
model = FastLanguageModel.get_peft_model(
    model,
    r=16,
    lora_alpha=32,
    lora_dropout=0.05,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                    "gate_proj", "up_proj", "down_proj"],
    bias="none",
    use_gradient_checkpointing="unsloth",
    random_state=42,
)

# -- Load preference datasets --
def load_pref(path):
    return load_dataset("json", data_files=path, split="train")

train_ds = load_pref("training/data/train_preferences.jsonl")
dev_ds   = load_pref("training/data/dev_preferences.jsonl")

print(f"train: {len(train_ds)} rows, dev: {len(dev_ds)} rows")

# -- Configure SimPO training --
training_args = SimPOConfig(
    output_dir="outputs/tenacious-judge-simpo-lora",
    num_train_epochs=1,           # start with 1; adjust after seeing dev loss
    per_device_train_batch_size=1,
    gradient_accumulation_steps=8,
    learning_rate=2e-5,
    lr_scheduler_type="cosine",
    warmup_ratio=0.1,
    fp16=True,
    logging_steps=10,
    save_steps=50,
    evaluation_strategy="steps",
    eval_steps=50,
    load_best_model_at_end=True,
    metric_for_best_model="eval_loss",
    beta=2.0,
    gamma_beta_ratio=0.5,
    report_to="none",             # change to "wandb" if you have W&B set up
)

trainer = SimPOTrainer(
    model=model,
    args=training_args,
    train_dataset=train_ds,
    eval_dataset=dev_ds,
    tokenizer=tokenizer,
)

trainer.train()
```

---

## Step 8 — Save the adapter

```python
model.save_pretrained("outputs/tenacious-judge-simpo-lora")
tokenizer.save_pretrained("outputs/tenacious-judge-simpo-lora")
print("Adapter saved to outputs/tenacious-judge-simpo-lora")
```

**Download or push to Hub before the Colab session ends — Colab does not persist files.**

```python
# Option A: download as zip
!zip -r tenacious-judge-simpo-lora.zip outputs/tenacious-judge-simpo-lora/
from google.colab import files
files.download("tenacious-judge-simpo-lora.zip")

# Option B: push to HuggingFace Hub (requires HF_TOKEN env var)
# model.push_to_hub("your-hf-username/tenacious-judge-simpo-lora")
```

---

## Step 9 — Dev evaluation

Run this to measure how well the adapter judges on the dev split.

```python
!python3 scoring_evaluator.py \
    --batch \
    --split-file training/data/dev_preferences.jsonl \
    --output-report outputs/dev_eval_report.json
```

Review `outputs/dev_eval_report.json` for per-risk-focus pass rates.
Target: average score ≥ 70 / 100 across all dev tasks.

---

## Step 10 — Held-out test evaluation

Run this ONLY ONCE after all dev tuning is complete.

```python
!python3 scoring_evaluator.py \
    --batch \
    --split-file training/data/test_preferences.jsonl \
    --output-report outputs/held_out_eval_report.json
```

Do not iterate on hyperparameters using held-out results — that leaks test signal.

---

## Step 11 — Save training and evaluation reports

```python
import json, datetime

summary = {
    "run_date": datetime.datetime.utcnow().isoformat(),
    "base_model": "Qwen/Qwen2.5-3B-Instruct",
    "training_method": "SimPO",
    "adapter": "QLoRA",
    "train_rows": 100,
    "dev_rows": 60,
    "test_rows": 40,
    "epochs_run": 1,
    "adapter_path": "outputs/tenacious-judge-simpo-lora",
}

with open("outputs/training_run_summary.json", "w") as f:
    json.dump(summary, f, indent=2)

print("Reports saved:")
print("  outputs/dev_eval_report.json")
print("  outputs/held_out_eval_report.json")
print("  outputs/training_run_summary.json")
```

---

## Summary checklist

| Step | Command | Must pass? |
|------|---------|-----------|
| 1 | `nvidia-smi` — T4 shown | Yes |
| 2 | `git clone` + split file check | Yes |
| 3 | pip install Unsloth, TRL, etc. | Yes |
| 4 | `validate_benchmark_package.py` | **Yes — stop if FAIL** |
| 5 | `convert_tasks_to_preferences.py` | Yes |
| 6 | `validate_preference_splits.py` | **Yes — stop if FAIL** |
| 7 | SimPO QLoRA training cell | Run after validators pass |
| 8 | Save adapter + download | Yes |
| 9 | Dev evaluation | Yes |
| 10 | Held-out evaluation | Once only |
| 11 | Save reports | Yes |

---

## Notes

- Never substitute `training/data/tenacious_bench_seed_200.jsonl` for the preference files.
- The held-out split (`test_preferences.jsonl`) must not be used for hyperparameter tuning.
- If the Colab session disconnects during training, re-run from Step 2 (clone) — nothing persists.
- Adjust `lora_r`, `learning_rate`, and `epochs` between dev evaluation runs, not between held-out runs.
