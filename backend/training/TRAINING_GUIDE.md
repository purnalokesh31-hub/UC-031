# CropGuard AI — Disease Model Training Guide

## Current model and planned retraining

The checked-in ONNX/H5 classifier has **38 PlantVillage classes across 14 crops**. The separate retraining script defines a 60-class output: those 38 classes plus 22 classes for rice, wheat, cotton, sugarcane, and groundnut (19 crop names total; maize is already represented as Corn in PlantVillage). The 60-class dataset and model are not present in this workspace, so the 60-class model has not been trained or validated here.

| Crop Group | Crops | Classes |
|---|---|---|
| Crop disease classes added by the training script | Rice, Wheat, Cotton, Sugarcane, Groundnut | 22 |
| PlantVillage classes already in the shipped model | 14 crop names, including Corn/Maize | 38 |

The inference service accepts both the shipped 38-output model and the script's 60-output model, and reports the active model's output class count. Its confidence tiers are thresholds on model scores, not calibration or field-accuracy guarantees.

---

## Step 1 — Install PyTorch (Python 3.14 compatible)

```powershell
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install onnx kaggle
```

> **GPU available?** Use the CUDA wheel instead for 10x faster training:
> `pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121`

---

## Step 2 — Get Kaggle API credentials

1. Go to **https://www.kaggle.com/account**
2. Click **"Create New API Token"** — downloads `kaggle.json`
3. Place it at `C:\Users\PURNA\.kaggle\kaggle.json`

The script will auto-download all 6 datasets (~2 GB total):

| Dataset | Kaggle Slug | New Crops |
|---|---|---|
| PlantVillage | `emmarex/plantdisease` | 14 crops, 54,305 images |
| Rice | `vbookshelf/rice-image-dataset` | Rice (4 diseases) |
| Wheat | `olyadanilova/wheat-rust-diseases` | Wheat (3 diseases) |
| Cotton | `janmejaybhoi/cotton-disease-dataset` | Cotton (3 diseases) |
| Sugarcane | `rishabhdhyani/sugarcane-diseases-dataset` | Sugarcane (4 diseases) |
| Groundnut | `taruntiwarihp/groundnut-disease` | Groundnut (3 diseases) |

---

## Step 3 — Run training

```powershell
cd c:\Users\PURNA\OneDrive\Desktop\UC-031\backend
python training/train_disease_model.py
```

### Training flags

| Flag | Default | Description |
|---|---|---|
| `--epochs-phase1` | 5 | Head-only warmup epochs |
| `--epochs-phase2` | 15 | Fine-tune top 3 blocks |
| `--batch-size` | 32 | Lower to 16 if RAM is tight |
| `--skip-download` | off | Skip Kaggle, use existing data |
| `--data-dir PATH` | `training/multi_crop_data` | Custom dataset root |
| `--lr1` | 1e-3 | Phase 1 learning rate |
| `--lr2` | 2e-4 | Phase 2 learning rate |

### Time estimates

| Hardware | Phase 1 (5ep) | Phase 2 (15ep) | Total |
|---|---|---|---|
| CPU (Intel i5/i7) | ~2-3 h | ~6-9 h | ~8-12 h |
| Google Colab T4 GPU | ~5 min | ~20 min | ~25 min |
| NVIDIA RTX GPU | ~8 min | ~30 min | ~40 min |

> **Recommended: use Google Colab (free T4 GPU)**
> Upload `training/train_disease_model.py`, run it, download the `.onnx` file.

---

## Step 4 — Activate the new model

The script auto-saves to:
```
backend/disease_engine/plant_disease_model.onnx
```
Old model is backed up as `.onnx.bak` automatically.

Restart the backend:
```powershell
$env:PYTHONUTF8="1"; python -m uvicorn main:app --port 8000
```

---

## Model Architecture

```
EfficientNetB3  (ImageNet pre-trained, ~12M params)
    |
    +--> features[0..5]  frozen during Phase 1
    +--> features[6..8]  unfrozen in Phase 2 (fine-tuning)
    |
    v
Dropout(0.4) -> Linear(1536->512) -> SiLU -> Dropout(0.3) -> Linear(512->60)
    |
    v
ONNX opset 17  (Python 3.14 + onnxruntime 1.29 compatible)
```

### Training techniques
- **Augmentation**: RandomCrop, H/V Flip, Rotation 35deg, ColorJitter, GaussianBlur, RandomErasing
- **Loss**: CrossEntropyLoss + class weights (balances rare crops) + label smoothing 0.1
- **Sampler**: WeightedRandomSampler — Groundnut/Sugarcane seen as often as Tomato
- **Phase 1**: OneCycleLR scheduler (fast head warmup)
- **Phase 2**: CosineAnnealingWarmRestarts (smooth fine-tune)
- **Gradient clipping**: max_norm=1.0

### Accuracy evidence required

There is no measured accuracy claim for the checked-in classifier in this project. The training script's current random, per-class 85/15 image split is a training-validation split, not an independent field test; related images from the same source may appear on both sides. Do not use its best validation epoch as an estimate of deployment accuracy. Before making an accuracy claim, reserve independent images grouped by plant, capture session, farm, or source dataset; report per-class precision/recall, macro-F1, confusion matrix, and confidence calibration on that untouched set. Test on representative field images as well as the curated image sources.

---

## Manual download (if Kaggle API fails)

Download each dataset from Kaggle manually and extract to:

```
backend/training/multi_crop_data/
  plantvillage/   <- emmarex/plantdisease
  rice/           <- vbookshelf/rice-image-dataset
  wheat/          <- olyadanilova/wheat-rust-diseases
  cotton/         <- janmejaybhoi/cotton-disease-dataset
  sugarcane/      <- rishabhdhyani/sugarcane-diseases-dataset
  groundnut/      <- taruntiwarihp/groundnut-disease
```

Then:
```powershell
python training/train_disease_model.py --skip-download
```
