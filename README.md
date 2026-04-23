# 💾 DiskWatch — Disk Space Monitor
# Team Member 
* Diwanshu
* Vivek Kumar

A clean, real-time disk monitoring dashboard.  
Alerts you within **3 seconds** when disk usage hits warning/critical levels.

---

## 📁 Project Structure

```
diskwatch/
├── backend/
│   ├── app.py              ← Flask REST API + background polling
│   ├── requirements.txt    ← Python dependencies
│   └── diskwatch.db        ← SQLite database (auto-created on first run)
└── frontend/
    └── index.html          ← Complete dashboard (no build needed!)
```

---

## ⚡ Quick Start (5 Minutes)

### Step 1 — Set Up the Backend

Open a terminal and run:

```bash
# Go to the backend folder
cd diskwatch/backend

# Create a Python virtual environment (recommended)
python -m venv venv

# Activate it:
# macOS / Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the backend server
python app.py
```

You should see:
```
✅ Database initialized
🔄 Disk polling started (every 5s)
🚀 DiskWatch backend running on http://localhost:5000
```

---

### Step 2 — Open the Frontend

Simply open the file in your browser:

```
diskwatch/frontend/index.html
```

**Double-click** the file, or:
```bash
# macOS
open diskwatch/frontend/index.html

# Linux
xdg-open diskwatch/frontend/index.html

# Windows
start diskwatch/frontend/index.html
```

That's it! The dashboard will load and start polling the backend every 3 seconds.

---

## 🧪 Testing Alert System

To test alerts without waiting for a real disk to fill up:

1. Open the dashboard
2. Find a disk card
3. Set **Warning** to a value **below** the current usage (e.g., if disk is 40% used, set warning to 30)
4. Click **Set**
5. Within 3 seconds, you'll see:
   - 🟡 Yellow alert banner
   - Toast notification pop-up
   - Browser notification (if allowed)
   - Alert log entry

---

## 🔌 API Endpoints

| Method | Endpoint              | Description                      |
|--------|-----------------------|----------------------------------|
| GET    | `/api/disks`          | All disks with latest metrics    |
| GET    | `/api/status`         | Overall system status            |
| GET    | `/api/history/<id>`   | Last 50 records for a disk       |
| POST   | `/api/threshold`      | Set warning/critical thresholds  |
| GET    | `/api/health`         | Health check                     |

### Example: Set threshold
```bash
curl -X POST http://localhost:5000/api/threshold \
  -H "Content-Type: application/json" \
  -d '{"disk_id": 1, "warning_percent": 75, "critical_percent": 90}'
```

---

## 🏗️ How It Works

```
Backend (every 5s):
  df -k → parse partitions → store in SQLite → check thresholds → create alert record

Frontend (every 3s):
  GET /api/disks → render cards + chart → compare with prev status → show alerts
```

**Why 5s backend + 3s frontend?**  
The backend collects heavy system data every 5 seconds.  
The frontend polls every 3 seconds so the UI feels snappier — it just gets the latest cached value from the DB.

---

## 🎨 UI Features

- **Real-time disk cards** with animated progress bars
- **Color coding**: Green → Yellow → Red as usage rises
- **Usage history chart** (per disk, last 50 readings)
- **Alert banner** + toast notifications + browser notifications
- **Threshold editor** on each card
- **Dark/Light mode** toggle
- **Export to CSV** button
- **Skeleton loaders** while data loads

---

## 🗃️ Database Schema (SQLite)

```sql
-- disks: one row per detected partition
CREATE TABLE disks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    mount_path  TEXT UNIQUE NOT NULL,
    name        TEXT NOT NULL,
    created_at  TEXT DEFAULT (datetime('now'))
);

-- disk_metrics: time-series usage history
CREATE TABLE disk_metrics (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    disk_id        INTEGER NOT NULL REFERENCES disks(id),
    total_gb       REAL NOT NULL,
    used_gb        REAL NOT NULL,
    free_gb        REAL NOT NULL,
    usage_percent  REAL NOT NULL,
    status         TEXT NOT NULL DEFAULT 'normal',  -- normal / warning / critical
    recorded_at    TEXT DEFAULT (datetime('now'))
);

-- thresholds: per-disk alert levels
CREATE TABLE thresholds (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    disk_id          INTEGER UNIQUE NOT NULL REFERENCES disks(id),
    warning_percent  REAL NOT NULL DEFAULT 80.0,
    critical_percent REAL NOT NULL DEFAULT 90.0
);
```

---

## 🖥️ Platform Support

| OS      | Method Used            |
|---------|------------------------|
| Linux   | `df -k` command        |
| macOS   | `df -k` command        |
| Windows | PowerShell `Get-PSDrive` |

Falls back to Python's `shutil.disk_usage()` if system commands fail.

---

## 🔧 Configuration

Edit `backend/app.py` to change:

```python
POLL_INTERVAL = 5      # How often backend collects disk data (seconds)
MAX_HISTORY   = 50     # How many records to keep per disk
```

Edit `frontend/index.html` to change:

```javascript
const API     = 'http://localhost:5000/api';  // Backend URL
const POLL_MS = 3000;                          // Frontend poll interval (ms)
```

---

## 🐛 Troubleshooting

**"Cannot reach backend" error in UI**  
→ Make sure `python app.py` is running in the backend folder.

**No disks showing up**  
→ Wait 5–10 seconds for the first poll to complete.  
→ Check terminal for any error messages.

**CORS error in browser console**  
→ Make sure you installed `flask-cors` (`pip install -r requirements.txt`).

**Windows: No disk data**  
→ Run the terminal as Administrator if PowerShell commands fail.

---

## 📚 Tech Stack

| Layer     | Technology                      |
|-----------|---------------------------------|
| Backend   | Python 3.10+ · Flask · SQLite   |
| Frontend  | Vanilla HTML/CSS/JS · Chart.js  |
| Polling   | `threading.Thread` + `time.sleep` |
| DB ORM    | Raw `sqlite3` (stdlib, no deps) |

---

## 🎓 College Viva Explanation

**Q: How is real-time achieved without WebSockets?**  
A: The frontend polls the backend REST API every 3 seconds. The backend runs a background thread that collects disk data every 5 seconds and stores it in SQLite. The frontend always gets the freshest DB snapshot — maximum delay is 3 seconds from any change.

**Q: How are alerts triggered?**  
A: The backend compares each disk's usage_percent against stored thresholds. If exceeded, it writes the status as "warning" or "critical" in disk_metrics. The frontend detects a status change on the next poll and fires the alert UI immediately.

**Q: Why SQLite?**  
A: SQLite is file-based, requires zero configuration, and is perfect for a single-server monitoring tool with moderate write frequency. It ships with Python's standard library.
