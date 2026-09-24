"""
train_disease_model.py
======================
Trains EfficientNetB3 on a MERGED multi-source dataset covering 60 disease classes:
  • 38 PlantVillage classes  (Kaggle: emmarex/plantdisease)
  • 5  Rice classes           (Kaggle: vbookshelf/rice-image-dataset)
  • 4  Wheat classes          (Kaggle: olyadanilova/wheat-rust-diseases)
  • 4  Cotton classes         (Kaggle: janmejaybhoi/cotton-disease-dataset)
  • 5  Sugarcane classes      (Kaggle: rishabhdhyani/sugarcane-diseases-dataset)
  • 4  Groundnut classes      (Kaggle: taruntiwarihp/groundnut-disease)

These exactly match the AP Agriculture yield predictor crops:
  Rice • Wheat • Maize/Corn • Cotton • Sugarcane • Groundnut

Requirements:
    pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
    pip install onnx kaggle

Quick start:
    1. Put kaggle.json in ~/.kaggle/   (get from kaggle.com/account → Create API Token)
    2. python training/train_disease_model.py
    3. After training finishes, restart the backend server

Flags:
    --skip-download        Dataset folders already exist
    --data-dir PATH        Custom data directory
    --epochs-phase1 N      Head-only epochs (default 5)
    --epochs-phase2 N      Fine-tune epochs (default 15)
    --batch-size N         Batch size (default 32)
"""

from __future__ import annotations
import argparse, json, os, shutil, sys, time, zipfile
from pathlib import Path
from collections import defaultdict

# ── Paths ──────────────────────────────────────────────────────────────── #
SCRIPT_DIR  = Path(__file__).parent
BACKEND_DIR = SCRIPT_DIR.parent
ENGINE_DIR  = BACKEND_DIR / "disease_engine"
ONNX_OUT    = ENGINE_DIR  / "plant_disease_model.onnx"
DATA_ROOT   = SCRIPT_DIR  / "multi_crop_data"

IMG_SIZE    = 224
SEED        = 42
BATCH_SIZE  = 32

# ── Canonical 60-class list (must match inference.py) ─────────────────── #
CLASS_NAMES = [
    # PlantVillage original 38
    "Apple___Apple_scab", "Apple___Black_rot", "Apple___Cedar_apple_rust",
    "Apple___healthy", "Blueberry___healthy",
    "Cherry_(including_sour)___Powdery_mildew", "Cherry_(including_sour)___healthy",
    "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot",
    "Corn_(maize)___Common_rust_", "Corn_(maize)___Northern_Leaf_Blight",
    "Corn_(maize)___healthy", "Grape___Black_rot",
    "Grape___Esca_(Black_Measles)", "Grape___Leaf_blight_(Isariopsis_Leaf_Spot)",
    "Grape___healthy", "Orange___Haunglongbing_(Citrus_greening)",
    "Peach___Bacterial_spot", "Peach___healthy",
    "Pepper,_bell___Bacterial_spot", "Pepper,_bell___healthy",
    "Potato___Early_blight", "Potato___Late_blight", "Potato___healthy",
    "Raspberry___healthy", "Soybean___healthy", "Squash___Powdery_mildew",
    "Strawberry___Leaf_scorch", "Strawberry___healthy",
    "Tomato___Bacterial_spot", "Tomato___Early_blight", "Tomato___Late_blight",
    "Tomato___Leaf_Mold", "Tomato___Septoria_leaf_spot",
    "Tomato___Spider_mites Two-spotted_spider_mite", "Tomato___Target_Spot",
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus", "Tomato___Tomato_mosaic_virus",
    "Tomato___healthy",
    # Rice (5)
    "Rice___Brown_Spot", "Rice___Hispa", "Rice___Leaf_Blast",
    "Rice___Neck_Blast", "Rice___healthy",
    # Wheat (4)
    "Wheat___Brown_Rust", "Wheat___Loose_Smut",
    "Wheat___Yellow_Rust", "Wheat___healthy",
    # Cotton (4)
    "Cotton___Bacterial_Blight", "Cotton___Curl_Virus",
    "Cotton___Fusarium_Wilt",    "Cotton___healthy",
    # Sugarcane (5)
    "Sugarcane___Bacterial_Blight", "Sugarcane___Red_Rot",
    "Sugarcane___Rust", "Sugarcane___Yellow_Disease", "Sugarcane___healthy",
    # Groundnut (4)
    "Groundnut___Early_Leaf_Spot", "Groundnut___Late_Leaf_Spot",
    "Groundnut___Rust",           "Groundnut___healthy",
]
NUM_CLASSES = len(CLASS_NAMES)   # 60

# ── Kaggle dataset configs ─────────────────────────────────────────────── #
# Each entry: (kaggle_slug, local_subdir, folder_name_→_class_name mapping)
DATASETS = [
    {
        "slug":    "emmarex/plantdisease",
        "subdir":  "plantvillage",
        # Folder names in this dataset directly match CLASS_NAMES (normalised)
        "mapping": "auto",
    },
    {
        "slug":    "vbookshelf/rice-image-dataset",
        "subdir":  "rice",
        # Explicit folder → class mapping for this dataset
        "mapping": {
            "Brown Spot":  "Rice___Brown_Spot",
            "Hispa":       "Rice___Hispa",
            "Leaf Blast":  "Rice___Leaf_Blast",
            "Normal":      "Rice___healthy",
            # Neck blast sometimes labelled differently
            "Neck Blast":  "Rice___Neck_Blast",
        },
    },
    {
        "slug":    "olyadanilova/wheat-rust-diseases",
        "subdir":  "wheat",
        "mapping": {
            "Brown_rust":   "Wheat___Brown_Rust",
            "Loose_smut":   "Wheat___Loose_Smut",
            "Yellow_rust":  "Wheat___Yellow_Rust",
            "Healthy":      "Wheat___healthy",
            "healthy":      "Wheat___healthy",
        },
    },
    {
        "slug":    "janmejaybhoi/cotton-disease-dataset",
        "subdir":  "cotton",
        "mapping": {
            "Bacterial Blight": "Cotton___Bacterial_Blight",
            "Curl Virus":       "Cotton___Curl_Virus",
            "Fusarium Wilt":    "Cotton___Fusarium_Wilt",
            "Healthy":          "Cotton___healthy",
            "healthy":          "Cotton___healthy",
        },
    },
    {
        "slug":    "rishabhdhyani/sugarcane-diseases-dataset",
        "subdir":  "sugarcane",
        "mapping": {
            "Bacterial Blight": "Sugarcane___Bacterial_Blight",
            "Red Rot":          "Sugarcane___Red_Rot",
            "Rust":             "Sugarcane___Rust",
            "Yellow":           "Sugarcane___Yellow_Disease",
            "Healthy":          "Sugarcane___healthy",
            "healthy":          "Sugarcane___healthy",
        },
    },
    {
        "slug":    "taruntiwarihp/groundnut-disease",
        "subdir":  "groundnut",
        "mapping": {
            "Early Leaf Spot":  "Groundnut___Early_Leaf_Spot",
            "Late Leaf Spot":   "Groundnut___Late_Leaf_Spot",
            "Rust":             "Groundnut___Rust",
            "Healthy":          "Groundnut___healthy",
            "healthy":          "Groundnut___healthy",
        },
    },
]


# ═══════════════════════════════════════════════════════════════════════════ #
#  Dependency check                                                           #
# ═══════════════════════════════════════════════════════════════════════════ #
def check_deps():
    missing = []
    for pkg in ["torch", "torchvision", "onnx"]:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        print("\n[ERROR] Missing packages:", ", ".join(missing))
        print("\nInstall with:")
        print("  pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu")
        print("  pip install onnx")
        sys.exit(1)


# ═══════════════════════════════════════════════════════════════════════════ #
#  Dataset download helpers                                                   #
# ═══════════════════════════════════════════════════════════════════════════ #
def ensure_kaggle():
    """Check Kaggle credentials and import."""
    kaggle_json = Path.home() / ".kaggle" / "kaggle.json"
    if not kaggle_json.exists():
        print("\n[ERROR] Kaggle API credentials not found.")
        print(f"  1. Go to https://www.kaggle.com/account")
        print(f"  2. Click 'Create New API Token' → downloads kaggle.json")
        print(f"  3. Place it at: {kaggle_json}")
        print()
        print("  OR manually download each dataset and extract to:")
        print(f"  {DATA_ROOT}/<subdir>/")
        print()
        print("  Then re-run with: --skip-download")
        sys.exit(1)
    try:
        import kaggle
        kaggle.api.authenticate()
        return kaggle
    except ImportError:
        print("[ERROR] kaggle package not installed. Run: pip install kaggle")
        sys.exit(1)


def download_dataset(kaggle_api, slug: str, dest: Path):
    """Download and unzip a Kaggle dataset into dest."""
    if dest.exists() and any(dest.iterdir()):
        print(f"  [SKIP] {slug} — already at {dest}")
        return
    dest.mkdir(parents=True, exist_ok=True)
    print(f"  [DOWN] {slug} → {dest}")
    kaggle_api.dataset_download_files(slug, path=str(dest), unzip=True)
    print(f"  [OK]   {slug}")


# ═══════════════════════════════════════════════════════════════════════════ #
#  Image collection — walk dataset dirs, apply class mapping                  #
# ═══════════════════════════════════════════════════════════════════════════ #
EXTS = {".jpg", ".jpeg", ".png", ".JPG", ".JPEG", ".PNG", ".bmp", ".BMP"}

def normalise(s: str) -> str:
    """Lowercase, strip punctuation for fuzzy matching."""
    return s.lower().replace(" ", "_").replace(",", "").replace("(", "").replace(")", "").replace("-", "_")

# Pre-build normalised lookup for CLASS_NAMES
_NORM_CLASSES = {normalise(c): c for c in CLASS_NAMES}


def _auto_map_folder(folder_name: str) -> str | None:
    """Try to resolve a folder name to a canonical class name (auto mode)."""
    norm = normalise(folder_name)
    if norm in _NORM_CLASSES:
        return _NORM_CLASSES[norm]
    # Prefix match (e.g. "Tomato___Early_blight" == "tomato___early_blight")
    for cn, cv in _NORM_CLASSES.items():
        if norm == cn or norm.startswith(cn[:12]):
            return cv
    return None


def collect_samples(data_root: Path, datasets: list[dict]) -> list[tuple[Path, int]]:
    """
    Walk all dataset subdirectories, map folder names → class indices,
    and return a flat list of (image_path, class_index).
    """
    class_to_idx = {c: i for i, c in enumerate(CLASS_NAMES)}
    all_samples: list[tuple[Path, int]] = []
    per_class_counts = defaultdict(int)

    for ds in datasets:
        subdir  = data_root / ds["subdir"]
        mapping = ds["mapping"]

        if not subdir.exists():
            print(f"  [WARN] Dataset subdir not found: {subdir} — skipping")
            continue

        # Find the actual image root (might be nested)
        image_root = _find_image_root(subdir)

        for folder in sorted(image_root.iterdir()):
            if not folder.is_dir():
                continue

            # Resolve class name
            if mapping == "auto":
                class_name = _auto_map_folder(folder.name)
            else:
                class_name = mapping.get(folder.name)
                if class_name is None:
                    # Try normalised
                    norm_f = normalise(folder.name)
                    for k, v in mapping.items():
                        if normalise(k) == norm_f:
                            class_name = v
                            break

            if class_name is None:
                print(f"    [SKIP] Unmapped folder: {folder.name} (in {ds['subdir']})")
                continue

            if class_name not in class_to_idx:
                print(f"    [SKIP] Unknown class: {class_name}")
                continue

            idx = class_to_idx[class_name]
            images = [f for f in folder.rglob("*") if f.suffix in EXTS and f.is_file()]
            for img in images:
                all_samples.append((img, idx))
            per_class_counts[class_name] += len(images)

    # Summary
    print(f"\n[DATA] Total images collected: {len(all_samples)}")
    print(f"[DATA] Classes covered: {len(per_class_counts)}/{NUM_CLASSES}")
    missing = [c for c in CLASS_NAMES if per_class_counts[c] == 0]
    if missing:
        print(f"[WARN] Classes with 0 images ({len(missing)}): {missing[:5]}{'...' if len(missing)>5 else ''}")
    print("[DATA] Class distribution (top 5 / bottom 5):")
    sorted_counts = sorted(per_class_counts.items(), key=lambda x: -x[1])
    for nm, cnt in sorted_counts[:5]:
        print(f"       {nm}: {cnt}")
    print("       ...")
    for nm, cnt in sorted_counts[-5:]:
        print(f"       {nm}: {cnt}")

    return all_samples


def _find_image_root(base: Path) -> Path:
    """Walk until we find a directory with 3+ subdirs that contain images."""
    for root, dirs, _ in os.walk(base):
        if len(dirs) >= 3:
            root_path = Path(root)
            sample_dir = root_path / dirs[0]
            if any(sample_dir.rglob("*.jpg")) or any(sample_dir.rglob("*.png")):
                return root_path
    return base


# ═══════════════════════════════════════════════════════════════════════════ #
#  PyTorch Dataset + DataLoaders                                              #
# ═══════════════════════════════════════════════════════════════════════════ #
def build_loaders(all_samples: list[tuple[Path, int]]):
    import torch
    from torchvision import transforms
    from torch.utils.data import Dataset, DataLoader, WeightedRandomSampler
    from PIL import Image as PILImage
    import random

    # ── Augmentation ─────────────────────────────────────────────────── #
    train_tf = transforms.Compose([
        transforms.Resize((IMG_SIZE + 32, IMG_SIZE + 32)),
        transforms.RandomCrop(IMG_SIZE),
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.RandomVerticalFlip(p=0.2),
        transforms.RandomRotation(degrees=35),
        transforms.ColorJitter(brightness=0.35, contrast=0.35, saturation=0.35, hue=0.12),
        transforms.RandomGrayscale(p=0.05),
        # Field condition simulation
        transforms.GaussianBlur(kernel_size=3, sigma=(0.1, 1.5)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406],
                             std =[0.229, 0.224, 0.225]),
        transforms.RandomErasing(p=0.25, scale=(0.02, 0.18)),
    ])

    val_tf = transforms.Compose([
        transforms.Resize((IMG_SIZE, IMG_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406],
                             std =[0.229, 0.224, 0.225]),
    ])

    class CropDiseaseDataset(Dataset):
        def __init__(self, samples, transform):
            self.samples   = samples
            self.transform = transform

        def __len__(self): return len(self.samples)

        def __getitem__(self, idx):
            path, label = self.samples[idx]
            img = PILImage.open(path).convert("RGB")
            return self.transform(img), label

    # ── Stratified 85/15 split ────────────────────────────────────────── #
    import random
    random.seed(SEED)
    random.shuffle(all_samples)

    by_class: dict[int, list] = defaultdict(list)
    for item in all_samples:
        by_class[item[1]].append(item)

    train_samples, val_samples = [], []
    class_counts = [0] * NUM_CLASSES
    for cls_idx, cls_samples in by_class.items():
        split = max(1, int(len(cls_samples) * 0.85))
        train_samples.extend(cls_samples[:split])
        val_samples.extend(cls_samples[split:])
        class_counts[cls_idx] = len(cls_samples[:split])

    print(f"[DATA] Train: {len(train_samples)} | Val: {len(val_samples)}")

    # ── Class-weighted sampler (balances rare crops like Groundnut) ─── #
    sample_weights = [1.0 / max(class_counts[lbl], 1) for _, lbl in train_samples]
    sampler = WeightedRandomSampler(sample_weights, num_samples=len(train_samples), replacement=True)

    train_ds = CropDiseaseDataset(train_samples, train_tf)
    val_ds   = CropDiseaseDataset(val_samples,   val_tf)

    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, sampler=sampler,
                              num_workers=2, pin_memory=True)
    val_loader   = DataLoader(val_ds,   batch_size=BATCH_SIZE, shuffle=False,
                              num_workers=2, pin_memory=True)

    return train_loader, val_loader, class_counts


# ═══════════════════════════════════════════════════════════════════════════ #
#  Model — EfficientNetB3 with 60-class head                                  #
# ═══════════════════════════════════════════════════════════════════════════ #
def build_model():
    import torch.nn as nn
    from torchvision import models

    print(f"[MODEL] Loading EfficientNetB3 (ImageNet pre-trained, {NUM_CLASSES} output classes)...")
    model = models.efficientnet_b3(weights=models.EfficientNet_B3_Weights.IMAGENET1K_V1)

    in_features = model.classifier[1].in_features
    model.classifier = nn.Sequential(
        nn.Dropout(p=0.4, inplace=True),
        nn.Linear(in_features, 512),
        nn.SiLU(),
        nn.Dropout(p=0.3),
        nn.Linear(512, NUM_CLASSES),
    )

    # Freeze backbone for phase 1
    for p in model.features.parameters():
        p.requires_grad = False

    total     = sum(p.numel() for p in model.parameters())
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"[MODEL] Total params: {total:,} | Trainable (head): {trainable:,}")
    return model


def unfreeze_top_blocks(model, n: int = 3):
    blocks = list(model.features.children())
    for block in blocks[-n:]:
        for p in block.parameters():
            p.requires_grad = True
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"[MODEL] Unfroze last {n} feature blocks — {trainable:,} trainable params")


# ═══════════════════════════════════════════════════════════════════════════ #
#  Training + eval loops                                                      #
# ═══════════════════════════════════════════════════════════════════════════ #
def train_one_epoch(model, loader, criterion, optimizer, scaler, device):
    import torch
    model.train()
    total_loss, correct, total = 0.0, 0, 0

    for imgs, labels in loader:
        imgs, labels = imgs.to(device), labels.to(device)
        optimizer.zero_grad(set_to_none=True)

        with torch.autocast(device.type, enabled=(device.type == "cuda")):
            logits = model(imgs)
            loss   = criterion(logits, labels)

        scaler.scale(loss).backward()
        scaler.unscale_(optimizer)
        import torch.nn as nn
        nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        scaler.step(optimizer)
        scaler.update()

        total_loss += loss.item() * imgs.size(0)
        correct    += (logits.argmax(1) == labels).sum().item()
        total      += imgs.size(0)

    return total_loss / total, correct / total


def eval_one_epoch(model, loader, criterion, device):
    import torch
    model.eval()
    total_loss, correct, total = 0.0, 0, 0

    with torch.no_grad():
        for imgs, labels in loader:
            imgs, labels = imgs.to(device), labels.to(device)
            logits = model(imgs)
            loss   = criterion(logits, labels)
            total_loss += loss.item() * imgs.size(0)
            correct    += (logits.argmax(1) == labels).sum().item()
            total      += imgs.size(0)

    return total_loss / total, correct / total


# ═══════════════════════════════════════════════════════════════════════════ #
#  ONNX export + verification                                                 #
# ═══════════════════════════════════════════════════════════════════════════ #
def export_and_verify(model, device, out_path: Path) -> bool:
    import torch, onnx, onnxruntime as ort
    import numpy as np

    model.eval()
    dummy = torch.randn(1, 3, IMG_SIZE, IMG_SIZE, device=device)
    print(f"\n[ONNX] Exporting → {out_path}")

    torch.onnx.export(
        model, dummy, str(out_path),
        input_names=["input"],
        output_names=["output"],
        dynamic_axes={"input": {0: "batch"}, "output": {0: "batch"}},
        opset_version=17,
        export_params=True,
        do_constant_folding=True,
    )

    # ONNX structural check
    onnx.checker.check_model(onnx.load(str(out_path)))
    print(f"[ONNX] Structure OK  ({out_path.stat().st_size / 1e6:.1f} MB)")

    # Runtime test
    sess     = ort.InferenceSession(str(out_path), providers=["CPUExecutionProvider"])
    inp_name = sess.get_inputs()[0].name
    dummy_np = np.random.randn(1, 3, IMG_SIZE, IMG_SIZE).astype(np.float32)
    out_np   = sess.run(None, {inp_name: dummy_np})[0]
    assert out_np.shape == (1, NUM_CLASSES), f"Expected (1, {NUM_CLASSES}), got {out_np.shape}"
    print(f"[ONNX] Runtime test OK — output shape {out_np.shape}, argmax={out_np.argmax()} ✓")
    return True


# ═══════════════════════════════════════════════════════════════════════════ #
#  Main                                                                       #
# ═══════════════════════════════════════════════════════════════════════════ #
def main():
    import torch
    import torch.nn as nn

    global BATCH_SIZE

    parser = argparse.ArgumentParser(description="Train 60-class crop disease model")
    parser.add_argument("--data-dir",      type=Path, default=DATA_ROOT)
    parser.add_argument("--epochs-phase1", type=int,  default=5)
    parser.add_argument("--epochs-phase2", type=int,  default=15)
    parser.add_argument("--batch-size",    type=int,  default=BATCH_SIZE)
    parser.add_argument("--skip-download", action="store_true",
                        help="Datasets already downloaded, skip Kaggle")
    parser.add_argument("--lr1",           type=float, default=1e-3)
    parser.add_argument("--lr2",           type=float, default=2e-4)
    args = parser.parse_args()

    BATCH_SIZE = args.batch_size

    print("=" * 70)
    print("  CropGuard AI — Multi-Crop Disease Model Training")
    print(f"  {NUM_CLASSES} classes: PlantVillage + Rice, Wheat, Cotton, Sugarcane, Groundnut")
    print("=" * 70)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    gpu_note = " (GPU)" if device.type == "cuda" else " (CPU — consider Google Colab for speed)"
    print(f"\n[DEVICE] {device}{gpu_note}")
    torch.manual_seed(SEED)

    # ── 1. Download ──────────────────────────────────────────────────── #
    if not args.skip_download:
        print("\n[DOWNLOAD] Fetching all datasets from Kaggle...")
        kaggle_api = ensure_kaggle()
        for ds in DATASETS:
            dest = args.data_dir / ds["subdir"]
            download_dataset(kaggle_api, ds["slug"], dest)
    else:
        print("[DOWNLOAD] Skipped (--skip-download)")

    # ── 2. Collect samples ───────────────────────────────────────────── #
    print("\n[DATA] Scanning downloaded datasets...")
    adjusted_datasets = [{**ds, "__subdir_path": args.data_dir / ds["subdir"]} for ds in DATASETS]
    # Pass data_dir to collector
    all_samples = collect_samples(args.data_dir, DATASETS)

    if len(all_samples) < 1000:
        print(f"[ERROR] Only {len(all_samples)} images found. Check your data directory.")
        sys.exit(1)

    # ── 3. DataLoaders ───────────────────────────────────────────────── #
    train_loader, val_loader, class_counts = build_loaders(all_samples)

    # ── 4. Model ─────────────────────────────────────────────────────── #
    model = build_model().to(device)

    # Class-weighted loss — upweights rarer classes (Groundnut, Sugarcane)
    total_n       = sum(class_counts)
    class_weights = torch.tensor(
        [total_n / (NUM_CLASSES * max(c, 1)) for c in class_counts],
        dtype=torch.float32, device=device,
    )
    criterion = nn.CrossEntropyLoss(weight=class_weights, label_smoothing=0.1)
    scaler    = torch.amp.GradScaler(
        "cpu" if device.type == "cpu" else "cuda",
        enabled=(device.type == "cuda"),
    )

    best_val_acc = 0.0
    ckpt_path    = SCRIPT_DIR / "best_checkpoint.pt"

    # ── PHASE 1: Train head only ──────────────────────────────────────── #
    print(f"\n{'='*70}")
    print(f"[PHASE 1] Head-only training  |  {args.epochs_phase1} epochs  |  lr={args.lr1}")
    print(f"{'='*70}")

    opt1 = torch.optim.AdamW(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=args.lr1, weight_decay=1e-4,
    )
    sch1 = torch.optim.lr_scheduler.OneCycleLR(
        opt1, max_lr=args.lr1,
        steps_per_epoch=len(train_loader),
        epochs=args.epochs_phase1,
    )

    for ep in range(1, args.epochs_phase1 + 1):
        t0 = time.time()
        tr_loss, tr_acc = train_one_epoch(model, train_loader, criterion, opt1, scaler, device)
        vl_loss, vl_acc = eval_one_epoch(model, val_loader, criterion, device)
        sch1.step()
        elapsed = time.time() - t0
        marker  = " *** NEW BEST ***" if vl_acc > best_val_acc else ""
        print(f"  Ep {ep:2d}/{args.epochs_phase1} | "
              f"train acc={tr_acc:.4f} loss={tr_loss:.4f} | "
              f"val acc={vl_acc:.4f} loss={vl_loss:.4f} | "
              f"{elapsed:.0f}s{marker}")
        if vl_acc > best_val_acc:
            best_val_acc = vl_acc
            torch.save(model.state_dict(), ckpt_path)

    # ── PHASE 2: Unfreeze top 3 blocks and fine-tune ──────────────────── #
    print(f"\n{'='*70}")
    print(f"[PHASE 2] Fine-tuning top blocks  |  {args.epochs_phase2} epochs  |  lr={args.lr2}")
    print(f"{'='*70}")
    unfreeze_top_blocks(model, n=3)

    opt2 = torch.optim.AdamW(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=args.lr2, weight_decay=1e-4,
    )
    sch2 = torch.optim.lr_scheduler.CosineAnnealingWarmRestarts(
        opt2, T_0=args.epochs_phase2, eta_min=1e-6,
    )

    for ep in range(1, args.epochs_phase2 + 1):
        t0 = time.time()
        tr_loss, tr_acc = train_one_epoch(model, train_loader, criterion, opt2, scaler, device)
        vl_loss, vl_acc = eval_one_epoch(model, val_loader, criterion, device)
        sch2.step()
        elapsed = time.time() - t0
        marker  = " *** NEW BEST ***" if vl_acc > best_val_acc else ""
        print(f"  Ep {ep:2d}/{args.epochs_phase2} | "
              f"train acc={tr_acc:.4f} loss={tr_loss:.4f} | "
              f"val acc={vl_acc:.4f} loss={vl_loss:.4f} | "
              f"{elapsed:.0f}s{marker}")
        if vl_acc > best_val_acc:
            best_val_acc = vl_acc
            torch.save(model.state_dict(), ckpt_path)

    # ── Export best model ─────────────────────────────────────────────── #
    print(f"\n[EXPORT] Loading best checkpoint (val acc: {best_val_acc:.4f} = {best_val_acc*100:.1f}%)")
    model.load_state_dict(torch.load(ckpt_path, map_location=device))
    ENGINE_DIR.mkdir(exist_ok=True)

    if ONNX_OUT.exists():
        bak = ONNX_OUT.with_suffix(".onnx.bak")
        shutil.copy(ONNX_OUT, bak)
        print(f"[EXPORT] Backed up old model → {bak.name}")

    export_and_verify(model, device, ONNX_OUT)

    # Save canonical class list alongside model for reference
    class_idx_path = ENGINE_DIR / "class_names.json"
    with open(class_idx_path, "w") as f:
        json.dump(CLASS_NAMES, f, indent=2)
    print(f"[EXPORT] class_names.json saved → {class_idx_path}")

    # Cleanup checkpoint
    if ckpt_path.exists():
        ckpt_path.unlink()

    print("\n" + "=" * 70)
    print("  TRAINING COMPLETE")
    print(f"  Best val accuracy : {best_val_acc*100:.2f}%")
    print(f"  ONNX output       : {ONNX_OUT}")
    print(f"  Classes           : {NUM_CLASSES}")
    print()
    print("  To activate the new model, restart the backend:")
    print("    Ctrl+C  →  python -m uvicorn main:app --port 8000")
    print("=" * 70)


if __name__ == "__main__":
    check_deps()
    main()
