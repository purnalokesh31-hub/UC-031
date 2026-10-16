# Development feature sensitivity

All five original district splits; 25 candidates per family and variant. Final tests remain unscored.

Mean metrics across overlapping splits. RMSE change is relative to the same family's full inputs; positive means worse after removal. Errors and widths are q/ha. These are predictive information-removal checks, not causal effects.

| Family | Feature condition | MAE | RMSE ± SD | R² | Coverage | Width | RMSE change |
|---|---|---:|---:|---:|---:|---:|---:|
| classical_rbf_kernel_control | weather_only | 5.161 | 6.250 ± 0.759 | -0.275 | 91.7% | 23.490 | +1.142 |
| classical_rbf_kernel_control | without_soil | 3.892 | 4.838 ± 0.722 | 0.228 | 94.3% | 19.856 | -0.270 |
| classical_rbf_kernel_control | without_year | 4.865 | 5.954 ± 0.490 | -0.155 | 92.6% | 21.736 | +0.847 |
| classical_ridge | weather_only | 4.889 | 5.945 ± 0.410 | -0.152 | 94.5% | 23.432 | +0.634 |
| classical_ridge | without_soil | 3.707 | 4.621 ± 0.798 | 0.292 | 96.2% | 20.195 | -0.690 |
| classical_ridge | without_year | 4.972 | 6.096 ± 0.589 | -0.210 | 90.2% | 21.130 | +0.785 |
| quantum_simulated_entangled | weather_only | 5.099 | 6.175 ± 0.640 | -0.242 | 92.6% | 23.636 | +0.825 |
| quantum_simulated_entangled | without_soil | 5.559 | 7.252 ± 4.527 | -1.361 | 86.9% | 23.264 | +1.902 |
| quantum_simulated_entangled | without_year | 5.364 | 6.538 ± 0.777 | -0.396 | 88.6% | 21.773 | +1.188 |

Removed columns were set to constant zero to preserve the eight-slot quantum circuit. Each variant was retuned inside the training fold. Ridge and RBF controls were specified before primary aggregate scores were inspected; this is not an exhaustive ablation of every classical family.

Modern mapped soil, point weather, limited geography and overlapping splits remain limitations. See the primary report and protocol for interpretation.
