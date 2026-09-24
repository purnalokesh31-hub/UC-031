"""
disease_db.py
SQLite persistence layer for the CropCare Disease Detection module.

Tables:
  scan_logs    — every prediction run (image, result, confidence, feedback)
  model_stats  — snapshot of model performance over time

Usage:
  from database.disease_db import DiseaseDB
  db = DiseaseDB()
  db.init()
  scan_id = db.save_scan(...)
"""

import sqlite3
import os
import json
import hashlib
import shutil
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

# ── Paths ─────────────────────────────────────────────────────────────── #
BASE_DIR   = Path(__file__).parent.parent          # backend/
DB_PATH    = BASE_DIR / "data" / "disease_scans.db"
IMAGES_DIR = BASE_DIR / "data" / "scan_images"


# ── Connection helper ─────────────────────────────────────────────────── #
@contextmanager
def _get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        with conn:
            yield conn
    finally:
        conn.close()


# ── DiseaseDB class ───────────────────────────────────────────────────── #
class DiseaseDB:
    """
    All database operations for the disease detection module.
    Single responsibility — no business logic here.
    """

    # ── Setup ─────────────────────────────────────────────────────────── #
    def init(self):
        """Create tables and image directory on first run."""
        IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        with _get_conn() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS scan_logs (
                    id                INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp         DATETIME DEFAULT CURRENT_TIMESTAMP,
                    image_path        TEXT,
                    image_hash        TEXT UNIQUE,
                    predicted_class   TEXT NOT NULL,
                    telugu_name       TEXT,
                    english_name      TEXT,
                    confidence        REAL,
                    top_3_json        TEXT,
                    crop_type         TEXT,
                    is_healthy        INTEGER DEFAULT 0,
                    confidence_tier   TEXT,
                    user_feedback     TEXT,
                    corrected_class   TEXT,
                    used_local_model  INTEGER DEFAULT 0,
                    solution          TEXT,
                    fungicide         TEXT,
                    insecticide       TEXT
                );

                CREATE TABLE IF NOT EXISTS active_learning_queue (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    scan_id         INTEGER REFERENCES scan_logs(id),
                    image_path      TEXT,
                    predicted_class TEXT,
                    confidence      REAL,
                    corrected_class TEXT,
                    queued_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
                    status          TEXT DEFAULT 'pending'
                );

                CREATE TABLE IF NOT EXISTS model_stats (
                    id               INTEGER PRIMARY KEY AUTOINCREMENT,
                    snapshot_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
                    total_scans      INTEGER DEFAULT 0,
                    avg_confidence   REAL DEFAULT 0,
                    uncertain_count  INTEGER DEFAULT 0,
                    correction_count INTEGER DEFAULT 0,
                    model_version    TEXT DEFAULT 'v1_plantvill'
                );

                CREATE INDEX IF NOT EXISTS idx_scan_logs_timestamp
                    ON scan_logs(timestamp DESC);
                CREATE INDEX IF NOT EXISTS idx_scan_logs_disease
                    ON scan_logs(is_healthy, english_name);
                CREATE INDEX IF NOT EXISTS idx_active_learning_pending
                    ON active_learning_queue(status, queued_at DESC);
            """)
            conn.commit()
        print("[DiseaseDB] Initialised:", DB_PATH)

    # ── Image Storage ─────────────────────────────────────────────────── #
    def save_image(self, image_bytes: bytes) -> tuple[str, str]:
        """
        Save raw image bytes to disk. Returns (file_path, sha256_hash).
        Duplicate detection: if hash already exists, skip write.
        """
        sha256 = hashlib.sha256(image_bytes).hexdigest()
        fname  = f"{sha256[:16]}.jpg"
        fpath  = IMAGES_DIR / fname

        if not fpath.exists():
            with open(fpath, "wb") as f:
                f.write(image_bytes)

        return str(fpath), sha256

    # ── Scan CRUD ─────────────────────────────────────────────────────── #
    def check_duplicate(self, image_hash: str) -> Optional[Dict]:
        """Return previous scan result if exact same image was scanned before."""
        with _get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM scan_logs WHERE image_hash = ? ORDER BY timestamp DESC LIMIT 1",
                (image_hash,)
            ).fetchone()
            if row:
                return dict(row)
        return None

    def save_scan(
        self,
        image_path:      str,
        image_hash:      str,
        predicted_class: str,
        telugu_name:     str,
        english_name:    str,
        confidence:      float,
        top_3:           list,
        crop_type:       str,
        is_healthy:      bool,
        confidence_tier: str,
        used_local:      bool,
        solution:        str = "",
        fungicide:       str = "",
        insecticide:     str = "",
    ) -> int:
        """Insert a new scan record. Returns the new row ID."""
        with _get_conn() as conn:
            cur = conn.execute("""
                INSERT OR IGNORE INTO scan_logs
                  (image_path, image_hash, predicted_class, telugu_name, english_name,
                   confidence, top_3_json, crop_type, is_healthy, confidence_tier,
                   used_local_model, solution, fungicide, insecticide)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                image_path, image_hash, predicted_class, telugu_name, english_name,
                confidence, json.dumps(top_3), crop_type, int(is_healthy), confidence_tier,
                int(used_local), solution, fungicide, insecticide,
            ))
            conn.commit()
            # INSERT OR IGNORE may race with an identical concurrent scan.
            row = conn.execute('SELECT id FROM scan_logs WHERE image_hash = ?',
                               (image_hash,)).fetchone()
            return row['id']

    def save_feedback(self, scan_id: int, feedback: str, corrected_class: Optional[str] = None):
        """
        Record user feedback on a prediction.
        feedback: 'correct' | 'wrong'
        """
        with _get_conn() as conn:
            conn.execute(
                "UPDATE scan_logs SET user_feedback=?, corrected_class=? WHERE id=?",
                (feedback, corrected_class, scan_id)
            )
            # Queue for active learning if wrong
            if feedback == "wrong" and corrected_class:
                row = conn.execute(
                    "SELECT image_path, predicted_class, confidence FROM scan_logs WHERE id=?",
                    (scan_id,)
                ).fetchone()
                if row:
                    conn.execute("""
                        INSERT INTO active_learning_queue
                          (scan_id, image_path, predicted_class, confidence, corrected_class)
                        VALUES (?,?,?,?,?)
                    """, (scan_id, row["image_path"], row["predicted_class"],
                          row["confidence"], corrected_class))
            conn.commit()

    # ── History + Analytics ───────────────────────────────────────────── #
    def get_history(self, limit: int = 10) -> List[Dict]:
        """Return the last N scan results for the history panel."""
        with _get_conn() as conn:
            rows = conn.execute("""
                SELECT id, timestamp, english_name, telugu_name, confidence,
                       confidence_tier, is_healthy, crop_type, image_path,
                       user_feedback, top_3_json
                FROM scan_logs
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,)).fetchall()
            return [dict(r) for r in rows]

    def get_analytics(self) -> Dict[str, Any]:
        """Aggregate stats for the analytics dashboard."""
        with _get_conn() as conn:
            total = conn.execute("SELECT COUNT(*) FROM scan_logs").fetchone()[0]
            avg_conf = conn.execute(
                "SELECT AVG(confidence) FROM scan_logs WHERE confidence_tier != 'rejected'"
            ).fetchone()[0] or 0
            uncertain = conn.execute(
                "SELECT COUNT(*) FROM scan_logs WHERE confidence_tier = 'uncertain'"
            ).fetchone()[0]
            corrections = conn.execute(
                "SELECT COUNT(*) FROM active_learning_queue"
            ).fetchone()[0]
            healthy = conn.execute(
                "SELECT COUNT(*) FROM scan_logs WHERE is_healthy = 1"
            ).fetchone()[0]

            # Most common disease
            top_disease = conn.execute("""
                SELECT english_name, COUNT(*) as cnt
                FROM scan_logs
                WHERE is_healthy = 0
                GROUP BY english_name
                ORDER BY cnt DESC LIMIT 1
            """).fetchone()

            # 7-day scan trend (last 7 days, daily count)
            trend = conn.execute("""
                SELECT DATE(timestamp) as day, COUNT(*) as cnt
                FROM scan_logs
                WHERE timestamp >= DATE('now', '-7 days')
                GROUP BY day ORDER BY day
            """).fetchall()

        return {
            "total_scans":        total,
            "avg_confidence":     round(avg_conf, 1),
            "uncertain_count":    uncertain,
            "correction_count":   corrections,
            "healthy_count":      healthy,
            "most_common_disease": dict(top_disease) if top_disease else None,
            "weekly_trend":       [dict(r) for r in trend],
            "queue_size":         corrections,
            "fine_tune_ready":    corrections >= 50,
        }

    def get_active_learning_queue(self, limit: int = 100) -> List[Dict]:
        """Return pending corrections for fine-tuning."""
        with _get_conn() as conn:
            rows = conn.execute("""
                SELECT * FROM active_learning_queue
                WHERE status = 'pending'
                ORDER BY queued_at DESC LIMIT ?
            """, (limit,)).fetchall()
            return [dict(r) for r in rows]

    def mark_queue_processed(self, queue_ids: List[int]):
        with _get_conn() as conn:
            conn.execute(
                f"UPDATE active_learning_queue SET status='processed' WHERE id IN ({','.join('?'*len(queue_ids))})",
                queue_ids
            )
            conn.commit()
