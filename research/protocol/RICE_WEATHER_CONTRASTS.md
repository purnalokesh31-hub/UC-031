# Annual rice weather-contrast investigation

Declared 27 September 2026 after inspecting the primary and feature-removal development results, before running this experiment. This is an exploratory, outcome-informed design amendment, not a preregistered confirmatory analysis.

## Question and fixed features

Does retaining within-year weather variation help transfer across development districts compared with annual weather plus year? Use the already archived daily NASA POWER point responses. No new outcomes or geography enter this experiment.

Retain the annual temperature mean, rainfall total, humidity mean and year in their existing eight-slot positions (4–7). Replace zeroed soil slots 0–2 with June–November minus December–May differences in mean temperature, total rainfall and mean humidity; slot 3 stays constant zero. These are fixed calendar halves, **not crop seasons or observed planting/harvest windows**. Both halves must have every expected daily record, including leap days. Annual summaries must reproduce the frozen panel within numerical tolerance. No missing-value imputation or target-driven window selection.

Use only the frozen 364 fit-role records from 13 districts. This remains retrospective annual district yield estimation; full-year weather cannot support an in-season forecast. Modern mapped soil stays excluded in both the baseline and augmented representation.

## Fixed comparisons

Ridge, classical RBF kernel ridge and the two-layer centered quantum-kernel model simulated classically. Exactly the existing 25 candidates per family, five original seeds, original grouped inner folds, and separate outer training/calibration/test districts. Preserve the eight-slot encoding and annual-feature slot positions. Adding features changes the geometry of both kernels; this is one specified representation, not an exhaustive or optimal encoding search.

Fit 15 new family/split combinations. Compare each to its already executed `without_soil` feature-sensitivity result on exactly the same outer row keys and outcomes. Also report the original year-only control. These fixed linear/kernel controls do not replace the stronger tree baselines in the primary study. Previously reported baseline scores are reused, not retuned after seeing this experiment.

## Reporting and safeguards

Report every split, MAE, RMSE, R², empirical 90% interval coverage and width, tuning time/settings and paired RMSE changes against annual-weather/year and year-only controls. Report means and split SD; overlapping splits are not independent repetitions or confidence intervals. Do not interpret R² or coverage as percentage accuracy. No claim of significance, agricultural utility or quantum advantage follows from an exploratory rank.

Verify frozen panel and code hashes, cached weather hashes, role isolation, matching split row keys and baseline outcomes, and completed candidate counts. Save this plan and source snapshots, a started receipt before fitting, the source manifest, development-only features/predictions, a completion manifest and a readable report in a new directory. Do not overwrite existing runs, score reserved outcomes, activate a model, or modify the original frozen protocol.

Spatial representativeness, irrigation/management omissions, historical boundary assumptions and absent independent external validation remain unresolved. Retain negative findings. A better development score alone does not justify deployment or an IEEE submission.
