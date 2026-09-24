# -*- coding: utf-8 -*-
"""
train.py
Phase 3: Trains both QuantumSVR and ClassicalSVR, logs metrics, saves models.

Usage:
    cd backend
    python training/train.py
"""

import sys, os, time, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from models.preprocessor  import CropPreprocessor
from models.quantum_model import QuantumSVR
from models.classical_model import ClassicalSVR

# ── Config ─────────────────────────────────────────────────────────────── #
DATA_PATH     = "data/crop_data.csv"
QUANTUM_TRAIN_SAMPLES = 120   # Kernel matrix is O(n²) — 120 samples = 7260 pairs (~8 min on CPU)
RANDOM_STATE  = 42
TEST_SIZE     = 0.2

def main():
    # Compatibility entry point: publish one complete, validated release.
    from training.train_validated import run
    return run()


if __name__ == "__main__":
    main()
