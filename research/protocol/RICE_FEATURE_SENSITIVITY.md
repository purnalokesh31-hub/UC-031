# Rice pilot feature sensitivity: development analysis

Declared 25 September 2026 while the primary five-split benchmark was running, before its aggregate scores were read. This supplements the development investigation; it does not change or open the frozen reserved cohorts.

## Fixed comparisons

Use Ridge, classical RBF kernel ridge, and the main two-layer centered simulated quantum kernel. These are fixed linear and kernel controls, not the best model selected after observing outer scores. Retune each with its original 25 candidates and original five district-grouped inner folds, for all five original seeds.

Three input removals: (1) soil removed, retaining weather and year; (2) year removed, retaining soil and weather; (3) soil and year removed, retaining weather only. Set removed input columns to zero before fitting. This keeps eight input slots and the quantum circuit structure fixed while eliminating the removed information. StandardScaler handles constant columns. The classical models receive exactly the same masked columns. These are information-removal ablations, not alternative optimal quantum encodings.

Reproduce the outer train/calibration/test assignments from the original code. Verify matching test row keys and outcomes against the corresponding full-feature run. Report every variant and family, mean MAE/RMSE/R², empirical 90% coverage, width, and paired RMSE changes per split. Positive change means worse error after removal. Split SD is descriptive; repeats overlap. Do not choose a final model or make causal feature-importance claims from these changes.

Inputs must match the frozen panel checksum, verified role hashes and frozen benchmark/model code hashes. Only fit-role rows are exposed to fitting/scoring. Save source snapshot, plan hash, tuning details and predictions. No reserved evaluation or model activation is performed.

This study does not address within-district soil representativeness, measurement error propagation, new regions or independently sourced external observations. Those remain separate investigations.
