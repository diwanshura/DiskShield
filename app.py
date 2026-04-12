"""
DiskWatch Backend — Flask + SQLite
Polls disk usage every 5 seconds, stores history, serves REST API.
"""

import os
import platform
import subprocess
import sqlite3
import threading
import time
import shutil
from datetime import datetime
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS

# ─── App Setup ────────────────────────────────────────────────────────────────
app = Flask(__name__)
CORS(app)  # Allow frontend (different port) to call us

DB_PATH = os.path.join(os.path.dirname(__file__), "diskwatch.db")
POLL_INTERVAL = 5  # Backend polls every 5 seconds
MAX_HISTORY = 50   # Keep last 50 records per disk


# ─── Database ─────────────────────────────────────────────────────────────────

def get_db():
    """Get a database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Makes rows dict-like
    return conn


def init_db():
    """Create tables if they don't exist."""
    conn = get_db()
    c = conn.cursor()

    # disks table — one row per detected disk/partition
    c.execute("""
        CREATE TABLE IF NOT EXISTS disks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mount_path TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    # disk_metrics — time-series usage data
    c.execute("""
        CREATE TABLE IF NOT EXISTS disk_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            disk_id INTEGER NOT NULL,
            total_gb REAL NOT NULL,
            used_gb REAL NOT NULL,
            free_gb REAL NOT NULL,
            usage_percent REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'normal',
            recorded_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (disk_id) REFERENCES disks(id)
        )
    """)

    # thresholds — per-disk warning/critical levels
    c.execute("""
        CREATE TABLE IF NOT EXISTS thresholds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            disk_id INTEGER UNIQUE NOT NULL,
            warning_percent REAL NOT NULL DEFAULT 80.0,
            critical_percent REAL NOT NULL DEFAULT 90.0,
            FOREIGN KEY (disk_id) REFERENCES disks(id)
        )
    """)

    conn.commit()
    conn.close()
    print("✅ Database initialized")


# ─── Disk Collection ──────────────────────────────────────────────────────────

def collect_disk_usage():
    """
    Collect disk usage for all mounted partitions.
    Returns a list of dicts with disk info.
    Works on Linux, macOS, and Windows.
    """
    disks = []
    system = platform.system()

    try:
        if system in ("Linux", "Darwin"):
            # Use df to get disk usage (skip tmpfs, devtmpfs etc.)
            result = subprocess.run(
                ["df", "-k"],
                capture_output=True, text=True, timeout=10
            )
            lines = result.stdout.strip().split("\n")[1:]  # Skip header
            for line in lines:
                parts = line.split()
                if len(parts) < 6:
                    continue
                device = parts[0]
                mount = parts[5]

                # Filter out non-real filesystems
                skip_prefixes = ("tmpfs", "devtmpfs", "udev", "none", "overlay", "shm")
                if any(device.startswith(p) for p in skip_prefixes):
                    continue
                if mount.startswith(("/proc", "/sys", "/dev", "/run")):
                    continue

                try:
                    total_kb = int(parts[1])
                    used_kb = int(parts[2])
                    free_kb = int(parts[3])

                    if total_kb == 0:
                        continue

                    total_gb = round(total_kb / 1024 / 1024, 2)
                    used_gb = round(used_kb / 1024 / 1024, 2)
                    free_gb = round(free_kb / 1024 / 1024, 2)
                    percent = round((used_kb / total_kb) * 100, 1)

                    disks.append({
                        "name": device,
                        "mount_path": mount,
                        "total_gb": total_gb,
                        "used_gb": used_gb,
                        "free_gb": free_gb,
                        "usage_percent": percent,
                    })
                except (ValueError, ZeroDivisionError):
                    continue

        elif system == "Windows":
            import json
            result = subprocess.run(
                ["powershell", "-Command",
                 "Get-PSDrive -PSProvider FileSystem | "
                 "Select-Object Name,Used,Free | ConvertTo-Json"],
                capture_output=True, text=True, timeout=10
            )
            drives = json.loads(result.stdout)
            if isinstance(drives, dict):
                drives = [drives]
            for d in drives:
                used = (d.get("Used") or 0)
                free = (d.get("Free") or 0)
                total = used + free
                if total == 0:
                    continue
                disks.append({
                    "name": d["Name"] + ":",
                    "mount_path": d["Name"] + ":\\",
                    "total_gb": round(total / 1e9, 2),
                    "used_gb": round(used / 1e9, 2),
                    "free_gb": round(free / 1e9, 2),
                    "usage_percent": round(used / total * 100, 1),
                })

    except Exception as e:
        print(f"⚠️ Disk collection error: {e}")
        # Fallback: use shutil for at least the root disk
        try:
            usage = shutil.disk_usage("/")
            disks.append({
                "name": "/dev/sda1",
                "mount_path": "/",
                "total_gb": round(usage.total / 1e9, 2),
                "used_gb": round(usage.used / 1e9, 2),
                "free_gb": round(usage.free / 1e9, 2),
                "usage_percent": round(usage.used / usage.total * 100, 1),
            })
        except Exception:
            pass

    # Limit to max 3 disks for simplicity
    return disks[:3]


# ─── Database Helpers ─────────────────────────────────────────────────────────

def get_or_create_disk(conn, name, mount_path):
    """Get disk row, creating it if it doesn't exist."""
    c = conn.cursor()
    c.execute("SELECT id FROM disks WHERE mount_path = ?", (mount_path,))
    row = c.fetchone()
    if row:
        return row["id"]
    c.execute("INSERT INTO disks (name, mount_path) VALUES (?, ?)", (name, mount_path))
    conn.commit()
    return c.lastrowid


def get_threshold(conn, disk_id):
    """Get threshold for a disk (returns defaults if not set)."""
    c = conn.cursor()
    c.execute("SELECT * FROM thresholds WHERE disk_id = ?", (disk_id,))
    row = c.fetchone()
    if row:
        return dict(row)
    return {"warning_percent": 80.0, "critical_percent": 90.0}


def determine_status(percent, warning, critical):
    """Return 'normal', 'warning', or 'critical' based on percent."""
    if percent >= critical:
        return "critical"
    elif percent >= warning:
        return "warning"
    return "normal"


def store_metric(conn, disk_id, data, status):
    """Save a metric record and prune old ones."""
    c = conn.cursor()
    c.execute("""
        INSERT INTO disk_metrics (disk_id, total_gb, used_gb, free_gb, usage_percent, status)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (disk_id, data["total_gb"], data["used_gb"], data["free_gb"],
          data["usage_percent"], status))
    conn.commit()

    # Keep only last MAX_HISTORY records per disk
    c.execute("""
        DELETE FROM disk_metrics
        WHERE disk_id = ? AND id NOT IN (
            SELECT id FROM disk_metrics WHERE disk_id = ?
            ORDER BY id DESC LIMIT ?
        )
    """, (disk_id, disk_id, MAX_HISTORY))
    conn.commit()


# ─── Background Polling Thread ────────────────────────────────────────────────

polling_active = True

def poll_disks():
    """
    Background thread: runs every POLL_INTERVAL seconds.
    Collects disk data, checks thresholds, stores history.
    """
    print(f"🔄 Disk polling started (every {POLL_INTERVAL}s)")
    while polling_active:
        try:
            disks = collect_disk_usage()
            if not disks:
                time.sleep(POLL_INTERVAL)
                continue

            conn = get_db()
            for d in disks:
                disk_id = get_or_create_disk(conn, d["name"], d["mount_path"])
                threshold = get_threshold(conn, disk_id)
                status = determine_status(
                    d["usage_percent"],
                    threshold["warning_percent"],
                    threshold["critical_percent"]
                )
                store_metric(conn, disk_id, d, status)
            conn.close()

        except Exception as e:
            print(f"⚠️ Poll error: {e}")

        time.sleep(POLL_INTERVAL)


# ─── API Routes ───────────────────────────────────────────────────────────────

@app.route("/api/disks", methods=["GET"])
def api_disks():
    """
    GET /api/disks
    Returns all known disks with their latest metric and threshold.
    This is the main endpoint the frontend polls every 3 seconds.
    """
    conn = get_db()
    c = conn.cursor()

    # Get all disks
    c.execute("SELECT * FROM disks ORDER BY id")
    disks = [dict(row) for row in c.fetchall()]

    result = []
    for disk in disks:
        disk_id = disk["id"]

        # Latest metric for this disk
        c.execute("""
            SELECT * FROM disk_metrics WHERE disk_id = ?
            ORDER BY id DESC LIMIT 1
        """, (disk_id,))
        metric = c.fetchone()
        if not metric:
            continue  # No data yet, skip

        threshold = get_threshold(conn, disk_id)

        result.append({
            "id": disk_id,
            "name": disk["name"],
            "mount_path": disk["mount_path"],
            "total_gb": metric["total_gb"],
            "used_gb": metric["used_gb"],
            "free_gb": metric["free_gb"],
            "usage_percent": metric["usage_percent"],
            "status": metric["status"],
            "recorded_at": metric["recorded_at"],
            "threshold": {
                "warning_percent": threshold["warning_percent"],
                "critical_percent": threshold["critical_percent"],
            }
        })

    conn.close()
    return jsonify(result)


@app.route("/api/status", methods=["GET"])
def api_status():
    """
    GET /api/status
    Returns overall system status: 'normal', 'warning', or 'critical'.
    If ANY disk is critical → overall is critical. etc.
    """
    conn = get_db()
    c = conn.cursor()

    c.execute("""
        SELECT status FROM disk_metrics dm
        INNER JOIN (
            SELECT disk_id, MAX(id) as max_id FROM disk_metrics GROUP BY disk_id
        ) latest ON dm.id = latest.max_id
    """)
    rows = c.fetchall()
    conn.close()

    statuses = [r["status"] for r in rows]
    if "critical" in statuses:
        overall = "critical"
    elif "warning" in statuses:
        overall = "warning"
    else:
        overall = "normal"

    return jsonify({
        "overall_status": overall,
        "timestamp": datetime.utcnow().isoformat()
    })


@app.route("/api/history/<int:disk_id>", methods=["GET"])
def api_history(disk_id):
    """
    GET /api/history/<disk_id>
    Returns the last 50 metric records for a disk (for the chart).
    """
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT usage_percent, status, recorded_at
        FROM disk_metrics
        WHERE disk_id = ?
        ORDER BY id DESC LIMIT 50
    """, (disk_id,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    # Return in chronological order
    rows.reverse()
    return jsonify(rows)


@app.route("/api/threshold", methods=["POST"])
def api_set_threshold():
    """
    POST /api/threshold
    Body: { "disk_id": 1, "warning_percent": 75, "critical_percent": 90 }
    Creates or updates threshold for a disk.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON body"}), 400

    disk_id = data.get("disk_id")
    warning = float(data.get("warning_percent", 80))
    critical = float(data.get("critical_percent", 90))

    if not disk_id:
        return jsonify({"error": "disk_id required"}), 400
    if warning >= critical:
        return jsonify({"error": "warning must be less than critical"}), 400

    conn = get_db()
    c = conn.cursor()
    c.execute("""
        INSERT INTO thresholds (disk_id, warning_percent, critical_percent)
        VALUES (?, ?, ?)
        ON CONFLICT(disk_id) DO UPDATE SET
            warning_percent = excluded.warning_percent,
            critical_percent = excluded.critical_percent
    """, (disk_id, warning, critical))
    conn.commit()
    conn.close()

    return jsonify({"success": True, "disk_id": disk_id, "warning": warning, "critical": critical})


@app.route("/api/health", methods=["GET"])
def api_health():
    """Simple health check."""
    return jsonify({"status": "ok", "time": datetime.utcnow().isoformat()})


@app.route("/")
def serve_frontend():
    """Serve the frontend HTML file."""
    return send_file("index.html")


# ─── Start ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    init_db()

    # Start background polling thread (daemon = dies when main process exits)
    poll_thread = threading.Thread(target=poll_disks, daemon=True)
    poll_thread.start()

    print("🚀 DiskWatch backend running on http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
