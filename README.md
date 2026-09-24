# CropGuard AI — UC-031

A local crop-yield research prototype with classical and simulated quantum regression, plus a separate pretrained leaf-image classifier.

## Start the app

The workspace has a Python 3.12 environment at `.venv`. From the project root:

```powershell
.\start_all.ps1
```

Or start the services in separate terminals:

```powershell
.\.venv\Scripts\python.exe -X utf8 -m uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8000
cd frontend
npm run dev -- --host 127.0.0.1 --strictPort
```

Open http://127.0.0.1:5173. The frontend sends `/api` requests through Vite's backend proxy. A deployed frontend needs the equivalent reverse proxy, or `VITE_API_BASE_URL` set when building. Direct cross-origin access can be configured with `CROPGUARD_CORS_ORIGINS`.

## How predictions work

1. Select one of six crops and enter N, P, K, pH, moisture, temperature, humidity and rainfall. Defaults use the middle of that crop's training range.
2. The backend loads the crop's complete fitted pipelines from the active model release. All eight features are retained; there is no shared four-component PCA bottleneck.
3. Classical candidates include ridge regression, quadratic ridge, SVR and gradient boosting. The quantum candidate encodes eight inputs using RY/RZ rotations on four simulated qubits and fits ridge regression to exact squared state overlaps. It is a simulation, not a physical quantum computer.
4. The model with the lowest training cross-validation RMSE supplies the selected estimate and demo yield status. Both estimates and their crop-specific test errors remain visible.
5. Separate calibration examples provide a 90% split-conformal prediction interval. Outside training feature ranges, the app reports extrapolation and withholds calibrated intervals and yield alerts. Yield predictions do not diagnose pests or nutrient deficiencies.

## Retrain reproducibly

```powershell
.\.venv\Scripts\python.exe -X utf8 -u backend\training\train_validated.py
```

The script reads the existing dataset without regenerating it. Per crop, 60% of rows fit the model with four-fold cross-validation, 20% calibrate intervals, and the final 20% evaluate both model families on identical examples. Preprocessing and target scaling are fitted inside each fold. The search compares 24 classical and nine quantum configurations per crop. Test scores never select parameters or the recommended model.

Every completed run writes models, split indices, candidate CV scores, predictions and a report into `backend/saved_models/releases/<id>/`. It publishes the full set by atomically replacing `backend/saved_models/active_release.json`. The API follows that pointer and reloads automatically when it changes. Older releases and the historical standalone model files remain available.

Older `train.py`, `train_per_crop.py`, `train_per_crop_resume.py` and `retrain_rice.py` entry points now run the complete validated workflow, preventing partial scaler/model replacement.

For a fresh environment, use Python 3.12, create `.venv`, and install `backend/requirements.txt`. ONNX Runtime 1.20.1 is pinned after reproducing a native import crash with 1.30.0 and scikit-learn on this Windows machine.

## Current results

Release: `20260922T172817101454Z`. Training took 127.5 seconds on this machine. Every crop uses 300 training, 100 calibration and 100 test rows.

| Crop | Classical R² | Classical MAE (q/ha) | Quantum R² | Quantum MAE (q/ha) | Selected interval coverage |
|---|---:|---:|---:|---:|---:|
| Rice | 0.918 | 0.87 | 0.882 | 1.06 | 91% |
| Wheat | 0.938 | 0.75 | 0.887 | 0.95 | 94% |
| Maize | 0.915 | 0.81 | 0.921 | 0.80 | 91% |
| Cotton | 0.924 | 0.39 | 0.790 | 0.64 | 89% |
| Sugarcane | 0.908 | 13.23 | 0.919 | 12.43 | 86% |
| Groundnut | 0.943 | 0.29 | 0.830 | 0.50 | 100% |

Classical models were selected for all crops by cross-validation. Quantum happened to score better on the final Maize and Sugarcane test sets; those test outcomes were not used to change the selected models. R² is not percentage accuracy. MAE is the mean absolute prediction error in quintals/hectare. The 90% intervals have observed coverage shown above; small test sets and distribution changes limit their interpretation.

## Limits of the evidence

The 3,000-row dataset is synthetic, with narrow crop-specific feature ranges. Internal held-out scores are not independent field validation; the dataset was already used in earlier experiments. There are no farm/season identifiers for grouped or chronological evaluation. Better real-world evidence needs measured harvests, varied farms and seasons, and independent tests grouped by farm and time. No changes were made to the data generator or targets to inflate scores.

Disease scanning uses a separate pretrained image model. This yield training does not improve or validate its disease accuracy. See the existing disease-training guide only as a separate workflow requiring labeled images.

## Verification

```powershell
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s backend/tests -v
cd frontend
npm run build
```

Tests cover all-crop HTTP inference, saved prediction reproducibility, disjoint splits, interval calibration, exact quantum-kernel determinism and PSD, invalid inputs, missing releases, extrapolation, duplicate scans and upload limits.

## Method references

- [Scikit-learn: avoid leakage with pipelines](https://scikit-learn.org/1.8/common_pitfalls.html)
- [IBM Qiskit: Statevector and inner products](https://docs.quantum.ibm.com/api/qiskit/qiskit.quantum_info.Statevector)

Detailed metrics and provenance: [training report](backend/saved_models/releases/20260922T172817101454Z/report.json).
