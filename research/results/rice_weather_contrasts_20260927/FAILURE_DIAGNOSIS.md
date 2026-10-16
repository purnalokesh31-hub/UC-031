# Weather-contrast failure investigation

Post-hoc descriptive analysis of development predictions only. No new fitting or final-test access. Training min/max checks are a coarse shift indicator; they are neither a density model nor evidence of causation.

## Largest quantum district errors

| Split seed | District | RMSE q/ha | Bias q/ha | 90% coverage | Rows outside any training input range |
|---|---|---:|---:|---:|---:|
| 41 | DLD1966-54 | 22.220 | -21.626 | 7.1% | 82.1% |
| 41 | DLD1966-50 | 9.201 | +7.386 | 89.3% | 85.7% |
| 67 | DLD1966-44 | 9.042 | +8.489 | 60.7% | 21.4% |
| 17 | DLD1966-49 | 6.112 | -5.365 | 100.0% | 0.0% |
| 29 | DLD1966-61 | 6.077 | +4.812 | 82.1% | 0.0% |

## What this suggests investigating

The largest district error occurs at seed 41, DLD1966-54. Its quantum fit used `{'alpha': 1e-08, 'angle_scale': 0.01, 'center_kernel': True, 'layers': 2}` selected inside grouped training CV. Very weak regularization is one possible contributor to instability; this observational association does not establish the cause.

A future, separately declared development experiment could compare a regularization floor or a more conservative inner-CV selection rule for both quantum and classical kernel models. Keep the current results, candidate accounting and unchanged outer assignments. Do not choose a threshold by minimizing these outer test errors or open reserved outcomes to settle it.

Also investigate weather support and omitted irrigation/management. Better numerical stability alone would not validate the district point inputs, add independent evidence, or establish agronomic usefulness.

All district/family errors and every feature's training/test min/max are retained in the two diagnostic CSV files. District identifiers follow the frozen historical DLD panel; they are not current administrative units.
