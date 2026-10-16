# Calendar-half weather contrasts: development results

Exploratory follow-up on 364 frozen development rows, 13 districts, five overlapping district splits. Reserved outcomes were not scored. No application model was changed.

Annual weather and year were retained; June–November minus December–May temperature, rainfall and humidity contrasts were added. Calendar halves are not crop-season labels. Every family received the original 25 candidates and grouped tuning folds.

Errors and widths are q/ha. SD describes variation across overlapping splits, not a confidence interval. Negative RMSE change means lower error. R² is not percentage accuracy.

| Family | MAE | RMSE ± SD | R² | Coverage | Width | Annual-only RMSE | Change vs annual | Change vs year-only |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| classical_rbf_kernel_control | 4.239 | 5.221 ± 1.332 | 0.075 | 92.9% | 20.679 | 4.838 | +0.383 | +0.550 |
| classical_ridge | 3.833 | 4.769 ± 0.824 | 0.248 | 94.8% | 20.358 | 4.621 | +0.148 | +0.098 |
| quantum_simulated_entangled | 5.513 | 6.977 ± 3.937 | -1.083 | 86.9% | 22.916 | 7.252 | -0.275 | +2.306 |

The reused year-only control has mean RMSE 4.671 q/ha. The annual-weather/year comparators come from the previous without-soil sensitivity run; their row keys and outcomes match exactly.

## Interpretation limits

This amendment was chosen after earlier development results. Repeated development comparisons can overfit the study design. This experiment provides no independent external validation, significance claim or quantum-computing advantage. Point weather, omitted management, annual outcomes and limited historical geography remain limitations. Do not deploy solely from these development scores.

## Reproduction

Run `python research/weather_contrasts.py --output research/results/NEW_UNIQUE_DIRECTORY` from the project root with the preserved panel and NASA response cache. The run verifies panel/code/source checksums, daily completeness, annual feature reconstruction, role separation, comparator keys/outcomes and all 15 candidate counts. Source snapshots, input hashes, environment, tuning results and predictions accompany this report.
