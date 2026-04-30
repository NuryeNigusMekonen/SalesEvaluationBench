# Week 11 Model Artifacts

The trained Tenacious v0.2 judge adapter is stored locally outside GitHub as a zip:

```text
~/Desktop/TRP1/week10/model_artifacts/week11/tenacious-judge-v02-simpo-lora.zip
```

The evaluation report bundle is stored locally as:

```text
~/Desktop/TRP1/week10/model_artifacts/week11/v02_eval_reports.zip
```

This repo expects the unzipped adapter at:

```text
outputs/models/tenacious-judge-v02-simpo-lora/
```

Small evaluation JSON reports live under:

```text
outputs/reports/
```

Adapter files, `.safetensors`, and zip archives are ignored by git. Evaluation reports are small JSON artifacts and can be committed.
