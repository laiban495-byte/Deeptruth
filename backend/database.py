from pathlib import Path
from datetime import datetime, timezone
import json
import sqlite3

ROOT = Path(__file__).resolve().parents[1]
DB_DIR = ROOT / "database"
BACKUP_DIR = ROOT / "backups"
DB_PATH = DB_DIR / "deeptruth.db"


def get_connection():
    DB_DIR.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")

    return conn


def initialize_database():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                file_path TEXT,
                media_type TEXT NOT NULL,
                result_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_scans_created
            ON scans(created_at)
        """)


def save_scan(record):
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO scans
            (filename, file_path, media_type, result_json, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                record.get("filename", "unknown"),
                record.get("file_path"),
                record.get("media_type", "unknown"),
                json.dumps(
                    record.get("result", {}),
                    ensure_ascii=False,
                    default=str
                ),
                datetime.now(timezone.utc).isoformat()
            )
        )

        return cur.lastrowid


def _decode(row):
    if row is None:
        return None

    item = dict(row)

    try:
        item["result"] = json.loads(item.pop("result_json"))
    except Exception:
        item["result"] = {}

    return item


def get_history(limit=50):
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM scans
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,)
        ).fetchall()

    return [_decode(row) for row in rows]


def get_scan_by_id(scan_id):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM scans WHERE id = ?",
            (scan_id,)
        ).fetchone()

    return _decode(row)


def delete_scan(scan_id):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM scans WHERE id = ?",
            (scan_id,)
        ).fetchone()

        if row is None:
            return None

        item = _decode(row)

        conn.execute(
            "DELETE FROM scans WHERE id = ?",
            (scan_id,)
        )

        return item


def get_statistics():
    with get_connection() as conn:
        total = conn.execute(
            "SELECT COUNT(*) FROM scans"
        ).fetchone()[0]

        rows = conn.execute(
            """
            SELECT media_type, result_json
            FROM scans
            """
        ).fetchall()

    ai_count = 0
    real_count = 0
    by_media_type = {}

    for row in rows:
        media_type = row["media_type"]

        by_media_type[media_type] = (
            by_media_type.get(media_type, 0) + 1
        )

        try:
            result = json.loads(row["result_json"])
        except Exception:
            result = {}

        image = result.get("image_analysis", {})
        verdict = image.get("verdict")

        if verdict == "ai-generated":
            ai_count += 1

        elif verdict == "real":
            real_count += 1

    return {
        "total_scans": total,
        "ai_scans": ai_count,
        "real_scans": real_count,
        "total_reports": total,
        "by_media_type": by_media_type
    }


def create_backup():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    if not DB_PATH.exists():
        initialize_database()

    filename = (
        "deeptruth_"
        + datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        + ".db"
    )

    destination = BACKUP_DIR / filename

    source_conn = sqlite3.connect(DB_PATH)
    backup_conn = sqlite3.connect(destination)

    try:
        source_conn.backup(backup_conn)
    finally:
        backup_conn.close()
        source_conn.close()

    return str(destination.relative_to(ROOT))


def list_backups():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    return [
        {
            "filename": path.name,
            "size_bytes": path.stat().st_size,
            "modified_at": datetime.fromtimestamp(
                path.stat().st_mtime
            ).isoformat()
        }
        for path in sorted(
            BACKUP_DIR.glob("deeptruth_*.db"),
            key=lambda item: item.stat().st_mtime,
            reverse=True
        )
    ]